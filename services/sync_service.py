"""
services/sync_service.py — LOGIPORT
=====================================
Two-way sync بين SQLite المحلي و Supabase.

Strategy:
  - Push: يرسل كل rows التي تغيّرت (updated_at > last_cursor) للسيرفر
  - Pull: يجلب كل rows التي تغيّرت على السيرفر منذ آخر cursor
  - Conflict: last-write-wins بالاعتماد على updated_at

Table name mapping  (SQLite → Supabase):
  doc_groups          → document_groups
  local_sync_cursors  → sync_cursors   (لا يُزامَن — يُدار محلياً)

Column name mapping  (SQLite → Supabase) لجدول documents:
  group_id            → document_group_id
  language            → lang
  document_type_id    → doc_type_id
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
# TABLE NAME MAPPING  (SQLite local name → Supabase name)
# ─────────────────────────────────────────────────────────
_LOCAL_TO_REMOTE: Dict[str, str] = {
    "doc_groups": "document_groups",
}

_REMOTE_TO_LOCAL: Dict[str, str] = {v: k for k, v in _LOCAL_TO_REMOTE.items()}


def _remote(local_table: str) -> str:
    """يرجع اسم الجدول في Supabase."""
    return _LOCAL_TO_REMOTE.get(local_table, local_table)


def _local(remote_table: str) -> str:
    """يرجع اسم الجدول في SQLite."""
    return _REMOTE_TO_LOCAL.get(remote_table, remote_table)


# ─────────────────────────────────────────────────────────
# COLUMN MAPPING  per-table  (SQLite col → Supabase col)
# ─────────────────────────────────────────────────────────
_COL_LOCAL_TO_REMOTE: Dict[str, Dict[str, str]] = {
    "documents": {
        "group_id":        "document_group_id",
        "language":        "lang",
        "document_type_id": "doc_type_id",
    },
}

_COL_REMOTE_TO_LOCAL: Dict[str, Dict[str, str]] = {
    tbl: {v: k for k, v in cols.items()}
    for tbl, cols in _COL_LOCAL_TO_REMOTE.items()
}

# أعمدة موجودة في SQLite فقط ولا يجب إرسالها لـ Supabase
_LOCAL_ONLY_COLS: Dict[str, set] = {
    "documents": {"template_id", "totals_json", "totals_text", "data_json",
                  "status", "file_path"},
}

# أعمدة موجودة في Supabase فقط ولا نقبلها في SQLite
_REMOTE_ONLY_COLS: Dict[str, set] = {
    "documents":         {"transaction_id", "doc_code", "doc_no", "file_size",
                          "generated_at", "document_group_id", "doc_type_id", "lang"},
    "transport_details": {"vessel_name", "voyage_no", "bl_no", "etd", "eta",
                          "port_of_loading", "port_of_discharge"},
    "pricing":           {"valid_from", "valid_to", "unit_price"},
}


# ─────────────────────────────────────────────────────────
# جداول مع نوع المزامنة
# ─────────────────────────────────────────────────────────

# (local_table_name, has_office_filter)
TWO_WAY_TABLES: List[Tuple[str, bool]] = [
    ("clients",               False),
    ("client_contacts",       False),
    ("companies",             False),
    ("company_banks",         False),
    ("company_role_links",    False),
    ("company_partner_links", False),
    ("entries",               True),
    ("entry_items",           False),
    ("transactions",          True),
    ("transaction_items",     False),
    ("transaction_entries",   False),
    ("transport_details",     False),
    ("doc_groups",            False),   # → document_groups في Supabase
    ("container_tracking",    True),
    ("shipment_containers",   False),
    ("tasks",                 False),
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

# الجداول التي عندها server_id (تُستخدم للـ upsert)
_TABLES_WITH_SERVER_ID = {
    "clients", "client_contacts", "companies", "company_banks",
    "company_role_links", "company_partner_links",
    "entries", "entry_items",
    "transactions", "transaction_items", "transaction_entries",
    "transport_details", "doc_groups", "documents",
    "audit_log", "users",
    "container_tracking", "shipment_containers", "tasks",
}

# الجداول التي عندها updated_at (لازم للـ cursor)
_TABLES_WITH_UPDATED_AT = {
    "clients", "client_contacts", "companies", "company_banks",
    "company_role_links", "company_partner_links",
    "entries", "entry_items",
    "transactions", "transaction_items", "transport_details",
    "doc_groups", "documents", "audit_log",
    "container_tracking", "tasks",
    "offices", "countries", "currencies", "delivery_methods",
    "material_types", "materials", "packaging_types", "pricing_types",
    "pricing", "document_types", "roles", "permissions",
}

_EPOCH = "1970-01-01T00:00:00+00:00"


# ─────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────

def _row_to_dict(row) -> Dict[str, Any]:
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, datetime):
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            d[k] = v.isoformat()
        elif hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    return d


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _apply_col_mapping_to_remote(local_table: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """يحوّل أسماء أعمدة SQLite → Supabase."""
    mapping = _COL_LOCAL_TO_REMOTE.get(local_table, {})
    local_only = _LOCAL_ONLY_COLS.get(local_table, set())
    if not mapping and not local_only:
        return data
    result = {}
    for k, v in data.items():
        if k in local_only:
            continue   # لا نُرسل هذا العمود لـ Supabase
        result[mapping.get(k, k)] = v
    return result


def _apply_col_mapping_to_local(remote_table: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """يحوّل أسماء أعمدة Supabase → SQLite."""
    local_table = _local(remote_table)
    mapping = _COL_REMOTE_TO_LOCAL.get(local_table, {})
    remote_only = _REMOTE_ONLY_COLS.get(local_table, set())
    if not mapping and not remote_only:
        return data
    result = {}
    for k, v in data.items():
        if k in remote_only:
            continue   # لا نكتب هذا العمود في SQLite
        result[mapping.get(k, k)] = v
    return result


# ─────────────────────────────────────────────────────────
# SyncResult
# ─────────────────────────────────────────────────────────

class SyncResult:
    def __init__(self):
        self.pushed:      Dict[str, int] = {}
        self.pulled:      Dict[str, int] = {}
        self.errors:      List[str]      = []
        self.started_at   = _now_iso()
        self.finished_at: Optional[str]  = None

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
        self._timer:    Optional[threading.Timer] = None
        self._office_id: Optional[int] = None
        self._interval  = 5 * 60   # 5 دقائق

    def configure(self, office_id: int, interval_seconds: int = 300):
        self._office_id = office_id
        self._interval  = interval_seconds

    # ── Public API ────────────────────────────────────────

    def is_enabled(self) -> bool:
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
        if not self.is_enabled():
            logger.info("Sync: disabled — no credentials configured")
            return
        self._schedule_next()
        logger.info("Sync: auto-sync started (interval=%ds)", self._interval)

    def stop_auto_sync(self):
        if self._timer:
            self._timer.cancel()
            self._timer = None
        logger.info("Sync: auto-sync stopped")

    def sync_now(self, callback=None) -> Optional[SyncResult]:
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

    # ── Scheduler ─────────────────────────────────────────

    def _schedule_next(self):
        self._timer = threading.Timer(self._interval, self._auto_tick)
        self._timer.daemon = True
        self._timer.start()

    def _auto_tick(self):
        if self.is_enabled():
            self._do_sync()
        self._schedule_next()

    # ── Core sync ─────────────────────────────────────────

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
            for local_tbl, has_office in TWO_WAY_TABLES:
                try:
                    n = self._push_table(client, office_id, local_tbl, has_office)
                    if n:
                        result.pushed[local_tbl] = n
                except Exception as e:
                    msg = f"push {local_tbl}: {e}"
                    logger.error("Sync: %s", msg)
                    result.errors.append(msg)

            for local_tbl in PUSH_ONLY_TABLES:
                try:
                    n = self._push_table(client, office_id, local_tbl, False)
                    if n:
                        result.pushed[local_tbl] = n
                except Exception as e:
                    msg = f"push {local_tbl}: {e}"
                    logger.error("Sync: %s", msg)
                    result.errors.append(msg)

            # ── Pull ──────────────────────────────────────
            for local_tbl, _ in TWO_WAY_TABLES:
                try:
                    n = self._pull_table(client, office_id, local_tbl)
                    if n:
                        result.pulled[local_tbl] = n
                except Exception as e:
                    msg = f"pull {local_tbl}: {e}"
                    logger.error("Sync: %s", msg)
                    result.errors.append(msg)

            for local_tbl in PULL_ONLY_TABLES:
                try:
                    n = self._pull_table(client, office_id, local_tbl)
                    if n:
                        result.pulled[local_tbl] = n
                except Exception as e:
                    msg = f"pull ref {local_tbl}: {e}"
                    logger.error("Sync: %s", msg)
                    result.errors.append(msg)

            logger.info(
                "Sync complete: pushed=%d pulled=%d errors=%d",
                result.total_pushed, result.total_pulled, len(result.errors),
            )

        except Exception as e:
            logger.exception("Sync: unexpected error")
            result.errors.append(str(e))
        finally:
            result.finish()
            self._running = False

        # إشعار نتيجة المزامنة
        try:
            from services.notification_service import NotificationService
            svc = NotificationService.get_instance()
            if result.success:
                svc.notify_sync(
                    success=True,
                    pushed=result.total_pushed,
                    pulled=result.total_pulled,
                )
            else:
                svc.notify_sync(
                    success=False,
                    error=result.errors[0] if result.errors else "unknown",
                )
        except Exception:
            pass

        return result

    # ── Push — local → server ─────────────────────────────

    def _push_table(
        self,
        client: SupabaseClient,
        office_id: int,
        local_table: str,
        has_office: bool,
    ) -> int:
        if local_table not in _TABLES_WITH_SERVER_ID:
            return 0
        if local_table not in _TABLES_WITH_UPDATED_AT:
            return 0

        remote_table = _remote(local_table)
        cursor = self._get_cursor(office_id, f"push_{local_table}")

        SessionLocal = get_session_local()
        with SessionLocal() as s:
            where = "updated_at > :cursor"
            params: Dict[str, Any] = {"cursor": cursor}
            if has_office:
                where += " AND (office_id = :oid OR office_id IS NULL)"
                params["oid"] = office_id

            rows = s.execute(
                text(f"SELECT * FROM [{local_table}] WHERE {where}"
                     f" ORDER BY updated_at LIMIT 500"),
                params,
            ).mappings().all()

        if not rows:
            return 0

        dicts = [_row_to_dict(r) for r in rows]

        # تطبيق الـ column mapping وإزالة الأعمدة المحلية فقط
        remote_dicts = []
        for d in dicts:
            mapped = _apply_col_mapping_to_remote(local_table, d)
            mapped.pop("id", None)   # Supabase يولّد id خاص به
            remote_dicts.append(mapped)

        client.upsert(remote_table, remote_dicts, on_conflict="server_id")

        latest = max(d["updated_at"] for d in dicts)
        self._set_cursor(office_id, f"push_{local_table}", latest)

        logger.debug("Sync push %s→%s: %d rows", local_table, remote_table, len(dicts))
        return len(dicts)

    # ── Pull — server → local ─────────────────────────────

    def _pull_table(
        self,
        client: SupabaseClient,
        office_id: int,
        local_table: str,
    ) -> int:
        remote_table = _remote(local_table)
        cursor = self._get_cursor(office_id, f"pull_{local_table}")

        rows = client.select(
            remote_table,
            filters={"updated_at": f"gt.{cursor}"},
            order="updated_at.asc",
            limit=500,
        )

        if not rows:
            return 0

        SessionLocal = get_session_local()
        with SessionLocal() as s:
            for row in rows:
                # تحويل أسماء الأعمدة من Supabase → SQLite
                local_row = _apply_col_mapping_to_local(remote_table, row)
                self._upsert_local(s, local_table, local_row)
            s.commit()

        latest = max(r.get("updated_at", _EPOCH) for r in rows)
        self._set_cursor(office_id, f"pull_{local_table}", latest)

        logger.debug("Sync pull %s←%s: %d rows", local_table, remote_table, len(rows))
        return len(rows)

    def _upsert_local(self, s, local_table: str, row: Dict[str, Any]):
        """يُدمج row من السيرفر في SQLite. last-write-wins."""
        server_id      = row.get("server_id")
        server_updated = row.get("updated_at", _EPOCH)

        if not server_id:
            # جداول مرجعية بدون server_id — نستخدم code
            self._upsert_reference(s, local_table, row)
            return

        existing = s.execute(
            text(f"SELECT id, updated_at FROM [{local_table}]"
                 f" WHERE server_id = :sid"),
            {"sid": server_id},
        ).mappings().first()

        data = {k: v for k, v in row.items() if k != "id"}

        if existing:
            local_updated = existing["updated_at"]
            if local_updated and str(local_updated) >= str(server_updated):
                return  # النسخة المحلية أحدث

            set_parts = [f"{k} = :{k}" for k in data if k != "server_id"]
            if not set_parts:
                return
            s.execute(
                text(f"UPDATE [{local_table}]"
                     f" SET {', '.join(set_parts)}"
                     f" WHERE id = :_id"),
                {**data, "_id": existing["id"]},
            )
        else:
            data.pop("id", None)
            cols = ", ".join(data.keys())
            vals = ", ".join(f":{k}" for k in data.keys())
            s.execute(
                text(f"INSERT OR IGNORE INTO [{local_table}] ({cols}) VALUES ({vals})"),
                data,
            )

    def _upsert_reference(self, s, local_table: str, row: Dict[str, Any]):
        """جداول مرجعية بدون server_id — تعتمد على code."""
        code = row.get("code")
        if not code:
            return
        data = {k: v for k, v in row.items() if k != "id"}
        existing = s.execute(
            text(f"SELECT id FROM [{local_table}] WHERE code = :code"),
            {"code": code},
        ).mappings().first()

        if existing:
            set_parts = [f"{k} = :{k}" for k in data if k != "code"]
            if set_parts:
                s.execute(
                    text(f"UPDATE [{local_table}]"
                         f" SET {', '.join(set_parts)}"
                         f" WHERE id = :_id"),
                    {**data, "_id": existing["id"]},
                )
        else:
            data.pop("id", None)
            cols = ", ".join(data.keys())
            vals = ", ".join(f":{k}" for k in data.keys())
            s.execute(
                text(f"INSERT OR IGNORE INTO [{local_table}] ({cols}) VALUES ({vals})"),
                data,
            )

    # ── Cursor management ─────────────────────────────────
    # يستخدم local_sync_cursors في SQLite (لا يُزامَن مع Supabase)

    def _get_cursor(self, office_id: int, direction_key: str) -> str:
        try:
            SessionLocal = get_session_local()
            with SessionLocal() as s:
                row = s.execute(
                    text("SELECT last_cursor FROM local_sync_cursors"
                         " WHERE table_name = :t AND direction = :d"),
                    {"t": direction_key, "d": str(office_id)},
                ).mappings().first()
                return row["last_cursor"] if row else _EPOCH
        except Exception:
            return _EPOCH

    def _set_cursor(self, office_id: int, direction_key: str, cursor: str):
        try:
            SessionLocal = get_session_local()
            with SessionLocal() as s:
                s.execute(
                    text("""
                        INSERT INTO local_sync_cursors (table_name, direction, last_cursor)
                        VALUES (:t, :d, :c)
                        ON CONFLICT (table_name, direction)
                        DO UPDATE SET last_cursor = excluded.last_cursor
                    """),
                    {"t": direction_key, "d": str(office_id), "c": cursor},
                )
                s.commit()
        except Exception as e:
            logger.warning("Sync: set_cursor failed: %s", e)

    # ── Helpers ───────────────────────────────────────────

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