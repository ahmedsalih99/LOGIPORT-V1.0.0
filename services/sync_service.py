"""
services/sync_service.py — LOGIPORT
=====================================
Two-way sync بين SQLite المحلي و Supabase.

Strategy:
  - Push: يرسل كل rows التي تغيّرت (updated_at > last_cursor) للسيرفر
  - Pull: يجلب كل rows التي تغيّرت على السيرفر منذ آخر cursor
  - Conflict: last-write-wins بالاعتماد على updated_at
  - Trigger: تلقائي كل 5 دقائق + يدوي من الـ UI

الجداول المُزامَنة:
  Priority 1 (two-way): transactions, transaction_items,
                         entries, entry_items,
                         clients, companies, users
  Priority 2 (push-only): audit_log, documents
  Reference (pull-only):  materials, packaging_types,
                          countries, currencies, offices, ...
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text

from database.models import get_session_local
from services.supabase_client import SupabaseClient, SupabaseError, get_supabase_client

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# جداول مع نوع المزامنة لكل منها
# ─────────────────────────────────────────────────────────

# (table_name, local_columns_csv, pk_col, has_office_filter)
TWO_WAY_TABLES: List[Tuple[str, bool]] = [
    ("clients",           False),   # مشترك بين المكاتب
    ("client_contacts",   False),
    ("companies",         False),
    ("company_banks",     False),
    ("company_role_links",False),
    ("company_partner_links", False),
    ("entries",           True),    # يُفلتر بـ office_id
    ("entry_items",       False),   # يتبع entries
    ("transactions",      True),
    ("transaction_items", False),
    ("transaction_entries", False),
    ("transport_details", False),
    ("document_groups",   False),
    ("users",             False),
]

PUSH_ONLY_TABLES: List[str] = [
    "audit_log",
    "documents",
]

PULL_ONLY_TABLES: List[str] = [
    "offices",
    "countries",
    "currencies",
    "delivery_methods",
    "material_types",
    "materials",
    "packaging_types",
    "pricing_types",
    "pricing",
    "document_types",
    "roles",
    "permissions",
    "role_permissions",
    "company_roles",
]

# Epoch افتراضي عند غياب الـ cursor
_EPOCH = "1970-01-01T00:00:00+00:00"


# ─────────────────────────────────────────────────────────
# Helper — serialise SQLAlchemy row → dict
# ─────────────────────────────────────────────────────────

def _row_to_dict(row) -> Dict[str, Any]:
    """يحوّل صف SQLAlchemy MappingResult → dict قابل للـ JSON."""
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, datetime):
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            d[k] = v.isoformat()
        elif hasattr(v, "isoformat"):          # Date
            d[k] = v.isoformat()
    return d


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────────────────────────────────────
# SyncResult
# ─────────────────────────────────────────────────────────

class SyncResult:
    def __init__(self):
        self.pushed: Dict[str, int] = {}   # table → count
        self.pulled: Dict[str, int] = {}
        self.errors: List[str]      = []
        self.started_at  = _now_iso()
        self.finished_at: Optional[str] = None

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    @property
    def total_pushed(self) -> int:
        return sum(self.pushed.values())

    @property
    def total_pulled(self) -> int:
        return sum(self.pulled.values())

    def finish(self):
        self.finished_at = _now_iso()

    def summary(self) -> str:
        if not self.success:
            return f"فشلت المزامنة: {'; '.join(self.errors[:2])}"
        return (
            f"تمت المزامنة — "
            f"↑ {self.total_pushed} سطر  "
            f"↓ {self.total_pulled} سطر"
        )


# ─────────────────────────────────────────────────────────
# SyncService
# ─────────────────────────────────────────────────────────

class SyncService:
    """
    يُدير المزامنة بين SQLite المحلي و Supabase.
    thread-safe — يمنع تشغيل sync متوازي.
    """

    def __init__(self):
        self._lock      = threading.Lock()
        self._running   = False
        self._timer: Optional[threading.Timer] = None
        self._office_id: Optional[int] = None
        self._interval  = 5 * 60          # 5 دقائق بالثواني

    # ─────────────────────────────────────────────
    # Configuration
    # ─────────────────────────────────────────────

    def configure(self, office_id: int, interval_seconds: int = 300):
        self._office_id = office_id
        self._interval  = interval_seconds

    # ─────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────

    def is_enabled(self) -> bool:
        """هل الـ sync مفعّل (عنده credentials)."""
        try:
            from core.settings_manager import SettingsManager
            sm  = SettingsManager.get_instance()
            url = sm.get("sync_supabase_url", "")
            key = sm.get("sync_anon_key", "")
            return bool(url and key)
        except Exception:
            return False

    def is_running(self) -> bool:
        return self._running

    def start_auto_sync(self):
        """يبدأ الـ timer للـ sync التلقائي."""
        if not self.is_enabled():
            logger.info("Sync: disabled — no credentials configured")
            return
        self._schedule_next()
        logger.info("Sync: auto-sync started (interval=%ds)", self._interval)

    def stop_auto_sync(self):
        """يوقف الـ timer."""
        if self._timer:
            self._timer.cancel()
            self._timer = None
        logger.info("Sync: auto-sync stopped")

    def sync_now(self, callback=None) -> Optional[SyncResult]:
        """
        يُشغّل sync فوري في thread منفصل.
        callback(result: SyncResult) يُستدعى عند الانتهاء.
        """
        if not self.is_enabled():
            logger.info("Sync: skipped — not configured")
            return None

        if self._running:
            logger.warning("Sync: already running — skipped")
            return None

        def _run():
            result = self._do_sync()
            if callback:
                try:
                    callback(result)
                except Exception as e:
                    logger.error("Sync callback error: %s", e)

        t = threading.Thread(target=_run, daemon=True, name="logiport-sync")
        t.start()
        return None

    # ─────────────────────────────────────────────
    # Internal — scheduler
    # ─────────────────────────────────────────────

    def _schedule_next(self):
        self._timer = threading.Timer(self._interval, self._auto_tick)
        self._timer.daemon = True
        self._timer.start()

    def _auto_tick(self):
        if self.is_enabled():
            self._do_sync()
        self._schedule_next()

    # ─────────────────────────────────────────────
    # Internal — core sync logic
    # ─────────────────────────────────────────────

    def _do_sync(self) -> SyncResult:
        result = SyncResult()

        with self._lock:
            if self._running:
                result.errors.append("sync already in progress")
                return result
            self._running = True

        try:
            client = get_supabase_client()
            if not client:
                result.errors.append("Supabase client not configured")
                return result

            if not client.ping():
                result.errors.append("Supabase server unreachable")
                return result

            office_id = self._office_id or self._get_office_id()
            if not office_id:
                result.errors.append("office_id not set")
                return result

            client.office_id = office_id

            # ── Push ──────────────────────────────────────
            for table, has_office in TWO_WAY_TABLES:
                try:
                    n = self._push_table(client, office_id, table, has_office)
                    if n:
                        result.pushed[table] = n
                except Exception as e:
                    msg = f"push {table}: {e}"
                    logger.error("Sync: %s", msg)
                    result.errors.append(msg)

            for table in PUSH_ONLY_TABLES:
                try:
                    n = self._push_table(client, office_id, table, True)
                    if n:
                        result.pushed[table] = n
                except Exception as e:
                    msg = f"push {table}: {e}"
                    logger.error("Sync: %s", msg)
                    result.errors.append(msg)

            # ── Pull ──────────────────────────────────────
            for table, has_office in TWO_WAY_TABLES:
                try:
                    n = self._pull_table(client, office_id, table)
                    if n:
                        result.pulled[table] = n
                except Exception as e:
                    msg = f"pull {table}: {e}"
                    logger.error("Sync: %s", msg)
                    result.errors.append(msg)

            for table in PULL_ONLY_TABLES:
                try:
                    n = self._pull_table(client, office_id, table)
                    if n:
                        result.pulled[table] = n
                except Exception as e:
                    msg = f"pull ref {table}: {e}"
                    logger.error("Sync: %s", msg)
                    result.errors.append(msg)

            logger.info(
                "Sync complete: pushed=%d pulled=%d errors=%d",
                result.total_pushed, result.total_pulled, len(result.errors)
            )

        except Exception as e:
            logger.exception("Sync: unexpected error")
            result.errors.append(str(e))
        finally:
            result.finish()
            self._running = False

        return result

    # ─────────────────────────────────────────────
    # Push — local → server
    # ─────────────────────────────────────────────

    def _push_table(
        self,
        client: SupabaseClient,
        office_id: int,
        table: str,
        has_office: bool,
    ) -> int:
        """
        يرسل كل rows المحلية التي updated_at > last_cursor للسيرفر.
        يستخدم upsert على server_id.
        """
        # الجداول بدون server_id (reference tables / audit) نتجاهلها من push
        if not self._table_has_server_id(table):
            return 0

        cursor = client.get_cursor(office_id, f"push_{table}") or _EPOCH

        SessionLocal = get_session_local()
        with SessionLocal() as s:
            # نبني SQL ديناميكي آمن
            where = f"updated_at > :cursor"
            if has_office:
                where += " AND (office_id = :oid OR office_id IS NULL)"

            params: Dict[str, Any] = {"cursor": cursor}
            if has_office:
                params["oid"] = office_id

            rows = s.execute(
                text(f"SELECT * FROM {table} WHERE {where} ORDER BY updated_at LIMIT 500"),
                params,
            ).mappings().all()

        if not rows:
            return 0

        dicts = [_row_to_dict(r) for r in rows]
        # نحذف حقول SQLite-only التي ليست في Supabase schema
        for d in dicts:
            d.pop("id", None)   # server يولّد id خاص به — نستخدم server_id

        client.upsert(table, dicts, on_conflict="server_id")

        # نحدّث cursor
        latest = max(d["updated_at"] for d in dicts)
        client.set_cursor(office_id, f"push_{table}", latest)

        logger.debug("Sync push %s: %d rows (cursor=%s)", table, len(dicts), latest)
        return len(dicts)

    # ─────────────────────────────────────────────
    # Pull — server → local
    # ─────────────────────────────────────────────

    def _pull_table(
        self,
        client: SupabaseClient,
        office_id: int,
        table: str,
    ) -> int:
        """
        يجلب rows التي updated_at > last_cursor من السيرفر
        ويُدمجها في SQLite المحلي (last-write-wins).
        """
        cursor = client.get_cursor(office_id, f"pull_{table}") or _EPOCH

        rows = client.select(
            table,
            filters={"updated_at": f"gt.{cursor}"},
            order="updated_at.asc",
            limit=500,
        )

        if not rows:
            return 0

        SessionLocal = get_session_local()
        with SessionLocal() as s:
            for row in rows:
                self._upsert_local(s, table, row)
            s.commit()

        latest = max(r["updated_at"] for r in rows)
        client.set_cursor(office_id, f"pull_{table}", latest)

        logger.debug("Sync pull %s: %d rows (cursor=%s)", table, len(rows), latest)
        return len(rows)

    def _upsert_local(self, s, table: str, row: Dict[str, Any]):
        """
        يُدمج row من السيرفر في SQLite المحلي.
        Last-write-wins: إذا كان server_updated_at > local_updated_at → يحدّث.
        يتجاهل id السيرفر ويبحث بـ server_id.
        """
        server_id      = row.get("server_id")
        server_updated = row.get("updated_at", _EPOCH)

        if not server_id:
            return

        # نتحقق من وجود الـ row محلياً وتاريخ تعديله
        if not self._table_has_server_id(table):
            # reference table — نستخدم code أو id مباشرة
            self._upsert_reference(s, table, row)
            return

        existing = s.execute(
            text(f"SELECT id, updated_at FROM {table} WHERE server_id = :sid"),
            {"sid": server_id},
        ).mappings().first()

        # تحضير البيانات — نحذف server id ونحتفظ بباقي الأعمدة
        data = {k: v for k, v in row.items() if k != "id"}

        if existing:
            local_updated = existing["updated_at"]
            # last-write-wins
            if local_updated and str(local_updated) >= str(server_updated):
                return   # النسخة المحلية أحدث — لا نحدّث

            # نبني UPDATE ديناميكي
            set_clause = ", ".join(f"{k} = :{k}" for k in data if k != "server_id")
            if not set_clause:
                return
            s.execute(
                text(f"UPDATE {table} SET {set_clause} WHERE id = :_id"),
                {**data, "_id": existing["id"]},
            )
        else:
            # INSERT — نحذف id لأن SQLite يولّده تلقائياً
            data.pop("id", None)
            cols   = ", ".join(data.keys())
            vals   = ", ".join(f":{k}" for k in data.keys())
            s.execute(
                text(f"INSERT OR IGNORE INTO {table} ({cols}) VALUES ({vals})"),
                data,
            )

    def _upsert_reference(self, s, table: str, row: Dict[str, Any]):
        """للجداول المرجعية بدون server_id — نستخدم code كمفتاح."""
        code = row.get("code")
        if not code:
            return
        data = {k: v for k, v in row.items() if k != "id"}
        existing = s.execute(
            text(f"SELECT id FROM {table} WHERE code = :code"),
            {"code": code},
        ).mappings().first()

        if existing:
            set_clause = ", ".join(f"{k} = :{k}" for k in data if k != "code")
            if set_clause:
                s.execute(
                    text(f"UPDATE {table} SET {set_clause} WHERE id = :_id"),
                    {**data, "_id": existing["id"]},
                )
        else:
            data.pop("id", None)
            cols = ", ".join(data.keys())
            vals = ", ".join(f":{k}" for k in data.keys())
            s.execute(
                text(f"INSERT OR IGNORE INTO {table} ({cols}) VALUES ({vals})"),
                data,
            )

    # ─────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────

    @staticmethod
    def _table_has_server_id(table: str) -> bool:
        tables_with_server_id = {
            "clients", "client_contacts", "companies", "company_banks",
            "company_role_links", "company_partner_links",
            "entries", "entry_items",
            "transactions", "transaction_items", "transaction_entries",
            "transport_details", "document_groups", "documents",
            "users", "audit_log",
        }
        return table in tables_with_server_id

    def _get_office_id(self) -> Optional[int]:
        try:
            from core.settings_manager import SettingsManager
            return SettingsManager.get_instance().get("sync_office_id", None)
        except Exception:
            return None


# ─────────────────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────────────────

_instance: Optional[SyncService] = None
_instance_lock = threading.Lock()


def get_sync_service() -> SyncService:
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = SyncService()
    return _instance