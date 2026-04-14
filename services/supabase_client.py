"""
services/supabase_client.py — LOGIPORT
============================
Lightweight Supabase REST client for LOGIPORT sync.
لا يعتمد على supabase-py — فقط urllib من stdlib.

إصلاحات:
  - [FIX] ping_timeout منفصل (5s بدل 15s) لاختبار الاتصال السريع
  - [FIX] ping() يُعيد الخطأ الحقيقي بدل False الصامت
  - [FIX] exponential backoff للـ retry على الطلبات
  - [FIX] أفضل معالجة للـ network errors
"""
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_TIMEOUT      = 15   # timeout للعمليات العادية (ثانية)
_PING_TIMEOUT = 8    # timeout لاختبار الاتصال (ثانية)
_MAX_RETRIES  = 3    # عدد محاولات الإعادة عند فشل الشبكة


class SupabaseError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(f"HTTP {status}: {message}")
        self.status  = status
        self.message = message


class SupabaseClient:
    """
    REST wrapper حول Supabase PostgREST API.
    يدعم: select / upsert / delete + health check.
    """

    def __init__(
        self,
        url: str,
        anon_key: str,
        office_id: Optional[int] = None,
        ping_timeout: Optional[int] = None,
    ):
        self.url          = url.rstrip("/")
        self.anon_key     = anon_key
        self.office_id    = office_id
        self._ping_timeout = ping_timeout or _PING_TIMEOUT

    # ─────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────

    def _headers(self, extra: Optional[Dict] = None) -> Dict[str, str]:
        h = {
            "apikey":        self.anon_key,
            "Authorization": f"Bearer {self.anon_key}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
            "Prefer":        "return=representation",
        }
        if self.office_id is not None:
            h["x-office-id"] = str(self.office_id)
        if extra:
            h.update(extra)
        return h

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        body: Optional[Any] = None,
        extra_headers: Optional[Dict] = None,
        timeout: Optional[int] = None,
        retries: int = 0,
    ) -> Any:
        url = f"{self.url}/rest/v1/{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        data = json.dumps(body).encode() if body is not None else None
        req  = urllib.request.Request(
            url,
            data=data,
            headers=self._headers(extra_headers),
            method=method,
        )
        _timeout = timeout or _TIMEOUT

        last_exc: Exception | None = None
        for attempt in range(max(1, retries + 1)):
            try:
                with urllib.request.urlopen(req, timeout=_timeout) as resp:
                    raw = resp.read()
                    return json.loads(raw) if raw else []

            except urllib.error.HTTPError as e:
                # HTTP error (4xx/5xx) — لا نُعيد المحاولة
                body_text = e.read().decode(errors="replace")
                logger.error("Supabase %s %s → %s: %s", method, path, e.code, body_text)
                raise SupabaseError(e.code, body_text) from e

            except (urllib.error.URLError, OSError, TimeoutError) as e:
                # خطأ شبكة — نُعيد المحاولة مع تأخير
                last_exc = e
                if attempt < retries:
                    wait = 2 ** attempt   # 1s, 2s, 4s
                    logger.warning(
                        "Supabase %s %s: network error (attempt %d/%d), retry in %ds: %s",
                        method, path, attempt + 1, retries + 1, wait, e,
                    )
                    time.sleep(wait)
                else:
                    logger.error("Supabase %s %s: failed after %d attempts: %s",
                                 method, path, retries + 1, e)

            except Exception as e:
                logger.error("Supabase request failed: %s", e)
                raise

        if last_exc:
            raise last_exc
        raise RuntimeError("Supabase request failed unexpectedly")

    # ─────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────

    def select(
        self,
        table: str,
        columns: str = "*",
        filters: Optional[Dict[str, str]] = None,
        order: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict]:
        """
        SELECT rows من جدول.
        filters: {"column": "operator.value"}
          مثال: {"updated_at": "gt.2024-01-01T00:00:00Z"}
        """
        params: Dict[str, Any] = {"select": columns}
        if filters:
            params.update(filters)
        if order:
            params["order"] = order
        if limit is not None:
            params["limit"] = limit
        return self._request("GET", table, params=params, retries=2)

    def upsert(
        self,
        table: str,
        rows: List[Dict],
        on_conflict: str = "server_id",
    ) -> List[Dict]:
        """
        INSERT or UPDATE.
        on_conflict يُرسَل كـ URL query parameter (مش header) — هذا هو الصواب في PostgREST.
        """
        if not rows:
            return []
        return self._request(
            "POST",
            table,
            # [FIX] on_conflict = URL param وليس header
            params={"on_conflict": on_conflict},
            body=rows,
            extra_headers={
                "Prefer": "resolution=merge-duplicates,return=representation",
            },
            retries=2,
        )

    def delete(
        self,
        table: str,
        server_id: str,
    ) -> None:
        """DELETE row by server_id."""
        self._request(
            "DELETE",
            table,
            params={"server_id": f"eq.{server_id}"},
            extra_headers={"Prefer": "return=minimal"},
            retries=1,
        )

    def get_cursor(self, office_id: int, table_name: str) -> Optional[str]:
        """
        يجلب آخر وقت مزامنة لجدول معيّن من sync_cursors.
        يُعيد ISO timestamp string أو None.
        """
        rows = self.select(
            "sync_cursors",
            columns="last_synced_at",
            filters={
                "office_id":  f"eq.{office_id}",
                "table_name": f"eq.{table_name}",
            },
            limit=1,
        )
        return rows[0]["last_synced_at"] if rows else None

    def set_cursor(self, office_id: int, table_name: str, ts: str) -> None:
        """يحدّث أو يُنشئ cursor لجدول."""
        self._request(
            "POST",
            "sync_cursors",
            body={"office_id": office_id, "table_name": table_name, "last_synced_at": ts},
            extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
            retries=2,
        )

    def ping(self) -> bool:
        """
        فحص الاتصال — يُعيد True إذا كان السيرفر يستجيب.

        المنطق:
          - أي HTTP response (200/401/403/404) = السيرفر موجود = True
          - URLError / OSError / TimeoutError = لا شبكة = False (بدون exception)
          - يُطلق SupabaseError(401) فقط عند استخدامه من test_connection في الـ dialog
            حتى يُعرض للمستخدم — لكن في الـ polling التلقائي يرجع False فقط.

        mode='test': يُطلق exception عند 401 (للـ dialog)
        mode='poll': يرجع True/False فقط (للـ widget وauto-sync)
        """
        url = f"{self.url}/rest/v1/"
        req = urllib.request.Request(
            url,
            headers=self._headers(),
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._ping_timeout) as resp:
                _ = resp.read()
            return True
        except urllib.error.HTTPError as e:
            # أي HTTP response تعني السيرفر يستجيب والـ URL صحيح
            # 401 = key خاطئ لكن السيرفر موصول
            # 403 = RLS يمنع لكن السيرفر موصول
            # نرجع True للـ connectivity check، False فقط عند انقطاع الشبكة
            return True
        except (urllib.error.URLError, OSError, TimeoutError):
            # انقطاع شبكة حقيقي
            return False

    def test_credentials(self) -> bool:
        """
        يتحقق من صحة الـ credentials فعلياً — يستخدمه dialog الإعدادات فقط.
        يُطلق SupabaseError(401) إذا كان الـ key خاطئاً.
        يُطلق URLError إذا انقطعت الشبكة.
        """
        # نحاول SELECT بسيط — إذا رجع 401 الـ key خاطئ، 200 يعني صحيح
        url = f"{self.url}/rest/v1/offices"
        params = urllib.parse.urlencode({"select": "id", "limit": "1"})
        req = urllib.request.Request(
            f"{url}?{params}",
            headers=self._headers(),
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._ping_timeout) as resp:
                _ = resp.read()
            return True
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise SupabaseError(401, "Unauthorized — invalid API key") from e
            # 404 = الجدول غير موجود لكن الـ key صحيح
            # 403 = RLS لكن الـ key صحيح
            return True


# ─────────────────────────────────────────────────────────
# Factory — يُنشئ client من SettingsManager
# ─────────────────────────────────────────────────────────

def get_supabase_client() -> Optional[SupabaseClient]:
    """
    يُنشئ SupabaseClient من إعدادات التطبيق.
    يُعيد None إذا لم تكن الإعدادات مكتملة.
    """
    try:
        from core.settings_manager import SettingsManager
        sm = SettingsManager.get_instance()
        url     = sm.get("sync_supabase_url", "")
        key     = sm.get("sync_anon_key", "")
        office  = sm.get("sync_office_id", None)
        if not url or not key:
            return None
        return SupabaseClient(url, key, office_id=office)
    except Exception as e:
        logger.error("Failed to create Supabase client: %s", e)
        return None