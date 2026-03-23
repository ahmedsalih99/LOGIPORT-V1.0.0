"""
services/supabase_client.py
============================
Lightweight Supabase REST client for LOGIPORT sync.
لا يعتمد على supabase-py — فقط urllib من stdlib.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_TIMEOUT = 15  # seconds


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

    def __init__(self, url: str, anon_key: str, office_id: Optional[int] = None):
        self.url      = url.rstrip("/")
        self.anon_key = anon_key
        self.office_id = office_id

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
            # يُرسل لـ RLS policy على Supabase
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
        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else []
        except urllib.error.HTTPError as e:
            body_text = e.read().decode(errors="replace")
            logger.error("Supabase %s %s → %s: %s", method, path, e.code, body_text)
            raise SupabaseError(e.code, body_text) from e
        except Exception as e:
            logger.error("Supabase request failed: %s", e)
            raise

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
        return self._request("GET", table, params=params)

    def upsert(
        self,
        table: str,
        rows: List[Dict],
        on_conflict: str = "server_id",
    ) -> List[Dict]:
        """
        INSERT or UPDATE — يستخدم server_id كمفتاح للتمييز.
        """
        if not rows:
            return []
        return self._request(
            "POST",
            table,
            body=rows,
            extra_headers={
                "Prefer": "resolution=merge-duplicates,return=representation",
                "on_conflict": on_conflict,
            },
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
        )

    def ping(self) -> bool:
        """فحص الاتصال — يُعيد True إذا كان الـ API يستجيب."""
        try:
            self._request("GET", "offices", params={"select": "id", "limit": "1"})
            return True
        except Exception:
            return False


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