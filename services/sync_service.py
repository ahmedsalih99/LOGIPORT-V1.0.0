"""
services/sync_service.py — LOGIPORT
=====================================
Two-way sync بين SQLite المحلي و Supabase.

إصلاحات بناءً على تحليل الـ error log:
  [A] synced_at: عمود قديم في SQLite — يُضاف لـ _LOCAL_ONLY_COLS_GLOBAL
  [B] doc_groups: بدون updated_at في SQLite — يُزال من _TABLES_WITH_UPDATED_AT
  [C] audit_log: timestamp بدل updated_at — mapping خاص + cursor على timestamp
  [D] جداول Supabase ناقصة updated_at — تُزال من pull/push قوائم الـ cursor
  [E] booking_no غير موجود في Supabase — يُضاف لـ LOCAL_ONLY_COLS
  [F] RLS violations — جداول محجوبة تُسقَط من TWO_WAY حتى يُحلّ الـ RLS
  [G] FK ordering — ترتيب Push صحيح: refs → clients → companies → entries → transactions
  [H] ping() بسيطة — True/False بدون exceptions
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text

from database.models import get_session_local
from services.supabase_client import SupabaseClient, SupabaseError, get_supabase_client

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# TABLE NAME MAPPING  (SQLite → Supabase)
# ─────────────────────────────────────────────────────────
_LOCAL_TO_REMOTE: Dict[str, str] = {
    "doc_groups": "document_groups",
}
_REMOTE_TO_LOCAL: Dict[str, str] = {v: k for k, v in _LOCAL_TO_REMOTE.items()}


def _remote(local_table: str) -> str:
    return _LOCAL_TO_REMOTE.get(local_table, local_table)


def _local(remote_table: str) -> str:
    return _REMOTE_TO_LOCAL.get(remote_table, remote_table)


# ─────────────────────────────────────────────────────────
# [A] أعمدة موجودة في SQLite فقط — لا تُرسل لـ Supabase أبداً
# ─────────────────────────────────────────────────────────

# أعمدة مشتركة بين كل الجداول (قديمة/محلية)
_GLOBAL_LOCAL_ONLY: set = {
    "synced_at",      # عمود قديم من نسخة سابقة
}

# أعمدة خاصة بجداول محددة — موجودة في SQLite لكن ليست في Supabase schema
# مبنية على مقارنة فعلية بين SQLite و Supabase
_LOCAL_ONLY_COLS: Dict[str, set] = {
    "documents": {
        "template_id", "totals_json", "totals_text", "data_json",
        "status", "file_path",
    },
    "container_tracking": {
        # أعمدة قديمة محذوفة من النموذج الجديد
        "booking_no", "container_no", "vessel_name", "voyage_no",
        "port_of_loading", "final_destination",
        "atd", "ata", "customs_date", "delivery_date",
    },
    # أعمدة في SQLite غير موجودة في Supabase
    "delivery_methods": {
        "code",           # Supabase ليس فيه code لـ delivery_methods
    },
    "pricing_types": {
        "compute_by", "price_unit", "divisor", "sort_order",
    },
    "roles": {
        "label_ar", "label_en", "label_tr",
    },
    "users": {
        "created_by", "updated_by",
    },
}

# أعمدة موجودة في Supabase فقط — لا تُكتب في SQLite
_REMOTE_ONLY_COLS: Dict[str, set] = {
    "documents": {
        "transaction_id", "doc_code", "doc_no", "file_size",
        "generated_at", "document_group_id", "doc_type_id", "lang",
    },
    "roles": {
        "name_ar", "name_en", "name_tr",
    },
    "audit_log": {
        "created_at",   # Supabase: created_at — SQLite: timestamp
    },
    # هذه الجداول ليس فيها created_at في SQLite — نتجاهله عند الـ pull
    "pricing_types": {
        "created_at",
    },
    "document_types": {
        "created_at",
    },
    "roles": {
        "name_ar", "name_en", "name_tr",
        "created_at",
    },
    "permissions": {
        "created_at",
    },
    "role_permissions": {
        "created_at",
    },
}

# ─────────────────────────────────────────────────────────
# COLUMN MAPPING  per-table  (SQLite col → Supabase col)
# ─────────────────────────────────────────────────────────
_COL_LOCAL_TO_REMOTE: Dict[str, Dict[str, str]] = {
    "documents": {
        "group_id":          "document_group_id",
        "language":          "lang",
        "document_type_id":  "doc_type_id",
    },
    "audit_log": {
        "timestamp": "created_at",   # [C] audit_log يستخدم timestamp بدل updated_at
    },
}

_COL_REMOTE_TO_LOCAL: Dict[str, Dict[str, str]] = {
    tbl: {v: k for k, v in cols.items()}
    for tbl, cols in _COL_LOCAL_TO_REMOTE.items()
}

# ─────────────────────────────────────────────────────────
# [C] جداول تستخدم عمود timestamp مختلف للـ cursor
# ─────────────────────────────────────────────────────────
_CURSOR_COLUMN: Dict[str, str] = {
    "audit_log": "timestamp",   # بدل updated_at
}

# ─────────────────────────────────────────────────────────
# قوائم الجداول — مُرتَّبة حسب FK dependencies
# ─────────────────────────────────────────────────────────

# ترتيب إرسال كامل — من لا يعتمد على شيء إلى من يعتمد على كل شيء
# هذا يضمن عدم FK violations في Supabase
PUSH_REF_ORDER: List[str] = [
    # ① مستقلة
    "countries",
    "currencies",
    "material_types",
    "packaging_types",
    "delivery_methods",
    "pricing_types",
    "document_types",
    "roles",
    "permissions",
    "role_permissions",
    "company_roles",
    "offices",
    # ② تعتمد على ①
    "materials",
    # ③ تعتمد على ①
    "clients",
    # ④ تعتمد على clients
    "companies",
    # ⑤ تعتمد على clients/offices — تُرسَل هنا عبر ALWAYS_FULL قبل entry_items
    "entries",
    "transactions",
]

# ترتيب Push الصحيح حسب FK chain الكامل
# الجداول المرجعية (countries, currencies, etc.) تُرسَل أولاً عبر PUSH_BEFORE_TABLES
# (local_table_name, has_office_filter)
TWO_WAY_TABLES: List[Tuple[str, bool]] = [
    # clients و companies يُرسَلان في PUSH_REF_ORDER — هنا للـ pull فقط
    ("clients",               False),
    ("companies",             False),
    # ── تعتمد على clients/companies ────────────────────────
    ("client_contacts",       False),
    ("company_banks",         False),
    ("company_role_links",    False),
    ("company_partner_links", False),
    # ── تعتمد على clients/offices ──────────────────────────
    ("entries",               True),
    ("entry_items",           False),
    ("transactions",          True),
    # ── تعتمد على entries/transactions ─────────────────────
    ("transaction_items",     False),
    ("transaction_entries",   False),
    ("transport_details",     False),
    ("doc_groups",            False),
    # ── كونتينرات ───────────────────────────────────────────
    ("container_tracking",    True),
    ("shipment_containers",   False),
    ("tasks",                 False),
]

PUSH_ONLY_TABLES: List[str] = [
    "audit_log",
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
    # permissions: بدون updated_at في Supabase — [D]
    # role_permissions: بدون updated_at في Supabase — [D]
    # company_roles: غير موجود في Supabase schema
]

# ─────────────────────────────────────────────────────────
# جداول بدون updated_at في Supabase — نجلبها بدون cursor filter
# مبني على نتيجة check_supabase_schema.sql الفعلية
_TABLES_NO_UPDATED_AT_REMOTE: set = {
    "audit_log",           # Supabase: بدون updated_at (عنده created_at فقط)
    "doc_groups",          # Supabase: بدون updated_at
    "permissions",         # Supabase: بدون updated_at
    "role_permissions",    # Supabase: بدون updated_at
    "transaction_entries", # Supabase: بدون updated_at
}

# جداول بدون id column — composite PK أو بدون PK
# _push_ref_table يتجاهل d.pop("id") بأمان لكن server_id generation تحتاج id
_TABLES_NO_ID: set = {
    "role_permissions",   # PK = (role_id, permission_id)
    "transaction_entries",  # PK = id لكن بعض DBs القديمة بدون id
}

# الجداول التي عندها server_id (بعد Migration SYNC-2 في bootstrap)
_TABLES_WITH_SERVER_ID: set = {
    # جداول البيانات
    "clients", "client_contacts", "companies", "company_banks",
    "company_role_links", "company_partner_links",
    "entries", "entry_items",
    "transactions", "transaction_items", "transaction_entries",
    "transport_details", "doc_groups", "documents",
    "audit_log", "users",
    "container_tracking", "shipment_containers", "tasks",
    # جداول مرجعية — أُضيف لها server_id في bootstrap
    "offices", "countries", "currencies",
    "material_types", "materials",
    "packaging_types", "delivery_methods", "pricing_types",
    "document_types", "roles", "permissions",
    "role_permissions", "company_roles",
}

# [B][C] الجداول التي عندها updated_at (أو timestamp بديل) في SQLite
_TABLES_WITH_UPDATED_AT: set = {
    # updated_at أصلي في SQLite
    "clients", "client_contacts", "companies", "company_banks",
    "company_role_links", "company_partner_links",
    "entries", "entry_items",
    "transactions", "transaction_items", "transport_details",
    "container_tracking", "tasks",
    "offices", "countries", "currencies", "delivery_methods",
    "material_types", "materials", "packaging_types",
    "pricing", "pricing_types", "document_types", "roles",
    "permissions", "role_permissions", "company_roles",
    "shipment_containers",
    # timestamp بديل — يُعامَل عبر _CURSOR_COLUMN
    "audit_log",
    # doc_groups: بدون updated_at في SQLite — مُزال
}

_EPOCH = "1970-01-01T00:00:00+00:00"

# ─────────────────────────────────────────────────────────
# on_conflict column لكل جدول في Supabase
# server_id: للجداول التي نُولِّد لها UUID (بعد migration)
# code/name/transaction_no: للجداول التي لها unique column طبيعي
# ─────────────────────────────────────────────────────────
_ON_CONFLICT: Dict[str, str] = {
    # جداول بـ unique code (في SQLite و Supabase)
    "countries":        "code",
    "currencies":       "code",
    "pricing_types":    "code",
    "document_types":   "code",
    "permissions":      "code",
    "company_roles":    "code",
    "offices":          "code",
    "materials":        "code",
    "clients":          "code",
    # جداول بـ unique name_ar — نستخدم id للحفاظ على IDs متطابقة مع SQLite
    # ضروري لأن FKs (packaging_type_id, etc.) تعتمد على id
    "material_types":   "id",
    "packaging_types":  "id",
    "delivery_methods": "id",
    "roles":            "id",
    # role_permissions: unique (role_id, permission_id)
    "role_permissions": "role_id,permission_id",
    # كل الباقي — server_id
}

def _conflict_col(table: str) -> str:
    """يرجع عمود الـ upsert conflict لجدول معين."""
    return _ON_CONFLICT.get(table, "server_id")


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


def _to_int(value) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _apply_col_mapping_to_remote(local_table: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """يحوّل أسماء أعمدة SQLite → Supabase ويُزيل الأعمدة المحلية."""
    mapping    = _COL_LOCAL_TO_REMOTE.get(local_table, {})
    local_only = _LOCAL_ONLY_COLS.get(local_table, set()) | _GLOBAL_LOCAL_ONLY
    result = {}
    for k, v in data.items():
        if k in local_only:
            continue
        result[mapping.get(k, k)] = v
    return result


def _apply_col_mapping_to_local(remote_table: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """يحوّل أسماء أعمدة Supabase → SQLite ويُزيل الأعمدة البعيدة."""
    local_table = _local(remote_table)
    mapping     = _COL_REMOTE_TO_LOCAL.get(local_table, {})
    remote_only = _REMOTE_ONLY_COLS.get(local_table, set())
    result = {}
    for k, v in data.items():
        if k in remote_only:
            continue
        result[mapping.get(k, k)] = v
    return result


def _cursor_col(local_table: str) -> str:
    """يرجع اسم عمود الـ cursor للجدول."""
    return _CURSOR_COLUMN.get(local_table, "updated_at")


# ─────────────────────────────────────────────────────────
# SyncResult
# ─────────────────────────────────────────────────────────

class SyncResult:
    def __init__(self):
        self.pushed:     Dict[str, int] = {}
        self.pulled:     Dict[str, int] = {}
        self.errors:     List[str]      = []
        self.is_offline: bool           = False
        self.started_at  = _now_iso()
        self.finished_at: Optional[str] = None

    @property
    def success(self) -> bool:
        return len(self.errors) == 0 and not self.is_offline

    @property
    def total_pushed(self) -> int:
        return sum(self.pushed.values())

    @property
    def total_pulled(self) -> int:
        return sum(self.pulled.values())

    def finish(self):
        self.finished_at = _now_iso()

    def summary(self) -> str:
        if self.is_offline:
            return "لا يوجد اتصال بالإنترنت — سيتم المحاولة لاحقاً"
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
    _RETRY_DELAYS = [10, 30, 60]

    def __init__(self):
        self._lock       = threading.Lock()
        self._running    = False
        self._timer:    Optional[threading.Timer] = None
        self._office_id: Optional[int] = None
        self._interval   = 5 * 60
        self._consecutive_failures = 0

    def configure(self, office_id: int, interval_seconds: int = 300):
        self._office_id = _to_int(office_id)
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
        self._schedule_next(delay=self._interval)
        logger.info("Sync: auto-sync started (interval=%ds)", self._interval)

    def stop_auto_sync(self):
        if self._timer:
            self._timer.cancel()
            self._timer = None
        logger.info("Sync: auto-sync stopped")

    def sync_now(self, callback=None) -> None:
        if not self.is_enabled():
            return
        if self._running:
            logger.warning("Sync: already running — skipped")
            return

        def _run():
            result = self._do_sync()
            if callback:
                try:
                    callback(result)
                except Exception as e:
                    logger.error("Sync callback error: %s", e)

        threading.Thread(target=_run, daemon=True, name="logiport-sync").start()

    # ── Scheduler ─────────────────────────────────────────

    def _schedule_next(self, delay: Optional[int] = None):
        self._timer = threading.Timer(delay or self._interval, self._auto_tick)
        self._timer.daemon = True
        self._timer.start()

    def _auto_tick(self):
        if self.is_enabled():
            result = self._do_sync()
            if result.is_offline or not result.success:
                self._consecutive_failures += 1
                idx   = min(self._consecutive_failures - 1, len(self._RETRY_DELAYS) - 1)
                delay = self._RETRY_DELAYS[idx]
                logger.info("Sync: retry in %ds (failure #%d)", delay, self._consecutive_failures)
                self._schedule_next(delay=delay)
                return
            self._consecutive_failures = 0
        self._schedule_next(delay=self._interval)

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

            # [H] ping() ترجع True/False — لا exceptions
            if not client.ping():
                result.is_offline = True
                logger.info("Sync: offline — will retry later")
                return result

            office_id = self._office_id or _to_int(self._get_office_id())
            if not office_id:
                result.errors.append("office_id not set")
                return result

            client.office_id = office_id

            # ── Push ──────────────────────────────────────
            # نرسل الجداول المرجعية أولاً (countries, currencies, etc.)
            # قبل TWO_WAY لأن clients تعتمد على countries
            for local_tbl in PUSH_REF_ORDER:
                try:
                    n = self._push_ref_table(client, office_id, local_tbl)
                    if n:
                        result.pushed[local_tbl] = n
                except (OSError, TimeoutError):
                    result.is_offline = True
                    return result
                except Exception as e:
                    logger.error("Sync: push ref %s: %s", local_tbl, e)
                    result.errors.append(f"push ref {local_tbl}: {e}")

            # ترتيب صحيح حسب FK chain
            for local_tbl, has_office in TWO_WAY_TABLES:
                try:
                    n = self._push_table(client, office_id, local_tbl, has_office)
                    if n:
                        result.pushed[local_tbl] = n
                except (OSError, TimeoutError):
                    result.is_offline = True
                    return result
                except Exception as e:
                    msg = f"push {local_tbl}: {e}"
                    logger.error("Sync: %s", msg)
                    result.errors.append(msg)

            for local_tbl in PUSH_ONLY_TABLES:
                try:
                    n = self._push_table(client, office_id, local_tbl, False)
                    if n:
                        result.pushed[local_tbl] = n
                except (OSError, TimeoutError):
                    result.is_offline = True
                    return result
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
                except (OSError, TimeoutError):
                    result.is_offline = True
                    return result
                except Exception as e:
                    msg = f"pull {local_tbl}: {e}"
                    logger.error("Sync: %s", msg)
                    result.errors.append(msg)

            for local_tbl in PULL_ONLY_TABLES:
                try:
                    n = self._pull_table(client, office_id, local_tbl)
                    if n:
                        result.pulled[local_tbl] = n
                except (OSError, TimeoutError):
                    result.is_offline = True
                    return result
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

        # إشعار
        try:
            from services.notification_service import NotificationService
            svc = NotificationService.get_instance()
            if not result.is_offline:
                if result.success:
                    svc.notify_sync(success=True,
                                    pushed=result.total_pushed,
                                    pulled=result.total_pulled)
                else:
                    svc.notify_sync(success=False,
                                    error=result.errors[0] if result.errors else "unknown")
        except Exception:
            pass

        return result

    # ── Push refs — الجداول المرجعية قبل كل شيء ─────────

    def _push_ref_table(self, client: SupabaseClient, office_id: int, local_table: str) -> int:
        """
        يرسل جدول مرجعي لـ Supabase.
        يستخدم updated_at إن وجد، وإلا يرسل الكل (الجداول المرجعية صغيرة).
        """
        remote_table = _remote(local_table)
        has_updated_at = local_table in _TABLES_WITH_UPDATED_AT
        has_server_id  = local_table in _TABLES_WITH_SERVER_ID

        # [FIX] هذه الجداول تُرسَل كاملةً دائماً بدون cursor
        # لضمان تطابق البيانات بعد أي reset في Supabase
        ALWAYS_FULL: set = {
            "countries", "currencies", "material_types", "packaging_types",
            "delivery_methods", "pricing_types", "document_types", "roles",
            "permissions", "company_roles", "offices", "materials",
            "clients", "companies",
            "entries", "transactions",   # تُرسَل كاملة لأن entry_items/transaction_items تعتمد عليها
        }

        SessionLocal = get_session_local()
        with SessionLocal() as s:
            if local_table in ALWAYS_FULL:
                # نرسل كل شيء — نتجاهل الـ cursor
                cursor = None
                rows = s.execute(
                    text(f"SELECT * FROM [{local_table}] LIMIT 1000"),
                ).mappings().all()
            elif has_updated_at:
                cursor = self._get_cursor(office_id, f"push_{local_table}")
                rows = s.execute(
                    text(f"SELECT * FROM [{local_table}] WHERE updated_at > :cursor"
                         f" ORDER BY updated_at LIMIT 500"),
                    {"cursor": cursor},
                ).mappings().all()
            else:
                cursor = None
                rows = s.execute(
                    text(f"SELECT * FROM [{local_table}] LIMIT 500"),
                ).mappings().all()

        if not rows:
            return 0

        dicts = [_row_to_dict(r) for r in rows]

        # توليد server_id إن لزم (فقط للجداول التي عندها id column)
        if has_server_id and local_table not in _TABLES_NO_ID:
            rows_need_sid = [d for d in dicts if not d.get("server_id")]
            if rows_need_sid:
                try:
                    SL2 = get_session_local()
                    with SL2() as s2:
                        for d in rows_need_sid:
                            row_id = d.get("id")
                            if not row_id:
                                continue
                            new_sid = str(uuid.uuid4())
                            s2.execute(
                                text(f"UPDATE [{local_table}] SET server_id = :sid WHERE id = :id"),
                                {"sid": new_sid, "id": row_id},
                            )
                            d["server_id"] = new_sid
                        s2.commit()
                except Exception as e:
                    # العمود server_id غير موجود بعد في SQLite — نكمل بدونه
                    # (bootstrap سيضيفه عند التشغيل التالي)
                    logger.warning("Sync: server_id not in SQLite for %s, sending without: %s", local_table, e)
                    for d in rows_need_sid:
                        d.pop("server_id", None)

        conflict_col = _conflict_col(local_table)

        remote_dicts = []
        seen_conflict_vals = set()
        for d in dicts:
            mapped = _apply_col_mapping_to_remote(local_table, d)
            # [FIX] نُبقي على id — Supabase SERIAL يقبل explicit id
            # هذا ضروري لأن FKs (owner_client_id, client_id, etc.) تعتمد على نفس الـ id
            # mapped.pop("id") كان يسبب mismatch بين SQLite IDs و Supabase IDs

            # حذف server_id=NULL من الـ payload
            if mapped.get("server_id") is None:
                mapped.pop("server_id", None)

            # تجاهل صفوف conflict_col=NULL
            c_val = mapped.get(conflict_col)
            if c_val is None:
                continue

            # إزالة المكررات داخل نفس الـ batch
            if c_val in seen_conflict_vals:
                continue
            seen_conflict_vals.add(c_val)

            remote_dicts.append(mapped)

        if not remote_dicts:
            return 0

        client.upsert(remote_table, remote_dicts, on_conflict=conflict_col)

        if has_updated_at and cursor is not None:
            latest = max(str(d.get("updated_at", _EPOCH)) for d in dicts)
            self._set_cursor(office_id, f"push_{local_table}", latest)

        logger.debug("Sync push_ref %s→%s: %d rows", local_table, remote_table, len(dicts))
        return len(dicts)

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
        cursor_col   = _cursor_col(local_table)   # [C]
        cursor       = self._get_cursor(office_id, f"push_{local_table}")

        SessionLocal = get_session_local()
        with SessionLocal() as s:
            where  = f"{cursor_col} > :cursor"
            params: Dict[str, Any] = {"cursor": cursor}
            if has_office:
                where += " AND (office_id = :oid OR office_id IS NULL)"
                params["oid"] = office_id

            rows = s.execute(
                text(f"SELECT * FROM [{local_table}] WHERE {where}"
                     f" ORDER BY {cursor_col} LIMIT 500"),
                params,
            ).mappings().all()

        if not rows:
            return 0

        dicts = [_row_to_dict(r) for r in rows]

        # توليد server_id تلقائياً
        if local_table not in _TABLES_NO_ID:
            rows_need_sid = [d for d in dicts if not d.get("server_id")]
            if rows_need_sid:
                try:
                    SessionLocal2 = get_session_local()
                    with SessionLocal2() as s2:
                        for d in rows_need_sid:
                            row_id = d.get("id")
                            if not row_id:
                                continue
                            new_sid = str(uuid.uuid4())
                            s2.execute(
                                text(f"UPDATE [{local_table}] SET server_id = :sid WHERE id = :id"),
                                {"sid": new_sid, "id": row_id},
                            )
                            d["server_id"] = new_sid
                        s2.commit()
                except Exception as e:
                    logger.warning("Sync: server_id not in SQLite for %s: %s", local_table, e)
                    for d in rows_need_sid:
                        d.pop("server_id", None)

        # [A] تطبيق الـ mapping وإزالة الأعمدة المحلية (بما فيها synced_at)
        cc = _conflict_col(local_table)
        seen = set()
        remote_dicts = []
        for d in dicts:
            mapped = _apply_col_mapping_to_remote(local_table, d)
            # [FIX] نُبقي على id — ضروري للـ FKs
            if mapped.get("server_id") is None:
                mapped.pop("server_id", None)
            cv = mapped.get(cc)
            if cv is None or cv in seen:
                continue
            seen.add(cv)
            remote_dicts.append(mapped)

        if not remote_dicts:
            return 0

        client.upsert(remote_table, remote_dicts, on_conflict=cc)

        # نحدث cursor بعد نجاح الـ upsert
        latest = max(str(d.get(cursor_col, _EPOCH)) for d in dicts)
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

        # [D] جداول بدون updated_at في Supabase — نجلب بـ select عادي بدون cursor filter
        if remote_table in _TABLES_NO_UPDATED_AT_REMOTE or local_table in _TABLES_NO_UPDATED_AT_REMOTE:
            return self._pull_table_no_cursor(client, local_table, remote_table)

        cursor = self._get_cursor(office_id, f"pull_{local_table}")

        try:
            rows = client.select(
                remote_table,
                filters={"updated_at": f"gt.{cursor}"},
                order="updated_at.asc",
                limit=500,
            )
        except SupabaseError as e:
            if e.status == 400 and "updated_at" in str(e.message):
                # [D] الجدول لا يملك updated_at في Supabase — نجلب بدون cursor
                logger.warning("Sync: %s has no updated_at in Supabase, fetching all", remote_table)
                return self._pull_table_no_cursor(client, local_table, remote_table)
            raise

        if not rows:
            return 0

        SessionLocal = get_session_local()
        with SessionLocal() as s:
            for row in rows:
                local_row = _apply_col_mapping_to_local(remote_table, row)
                self._upsert_local(s, local_table, local_row)
            s.commit()

        latest = max(r.get("updated_at", _EPOCH) for r in rows)
        self._set_cursor(office_id, f"pull_{local_table}", latest)

        logger.debug("Sync pull %s←%s: %d rows", local_table, remote_table, len(rows))
        return len(rows)

    def _pull_table_no_cursor(
        self,
        client: SupabaseClient,
        local_table: str,
        remote_table: str,
    ) -> int:
        """
        [D] يجلب الجدول كاملاً بدون cursor (للجداول بدون updated_at في Supabase).
        مناسب للجداول الصغيرة مثل company_role_links, permissions, إلخ.
        """
        try:
            rows = client.select(remote_table, limit=1000)
        except Exception as e:
            logger.warning("Sync: pull_no_cursor %s failed: %s", remote_table, e)
            return 0

        if not rows:
            return 0

        SessionLocal = get_session_local()
        with SessionLocal() as s:
            for row in rows:
                local_row = _apply_col_mapping_to_local(remote_table, row)
                self._upsert_local(s, local_table, local_row)
            s.commit()

        logger.debug("Sync pull(no-cursor) %s←%s: %d rows", local_table, remote_table, len(rows))
        return len(rows)

    def _get_local_cols(self, s, table: str) -> set:
        """يجلب أسماء أعمدة الجدول في SQLite — مع cache."""
        if not hasattr(self, '_col_cache'):
            self._col_cache: Dict[str, set] = {}
        if table not in self._col_cache:
            rows = s.execute(text(f"PRAGMA table_info({table})")).fetchall()
            self._col_cache[table] = {r[1] for r in rows}
        return self._col_cache[table]

    def _upsert_local(self, s, local_table: str, row: Dict[str, Any]):
        """يُدمج row من السيرفر في SQLite. last-write-wins."""
        server_id      = row.get("server_id")
        server_updated = row.get("updated_at", _EPOCH)

        if not server_id:
            self._upsert_reference(s, local_table, row)
            return

        existing = s.execute(
            text(f"SELECT id, updated_at FROM [{local_table}]"
                 f" WHERE server_id = :sid"),
            {"sid": server_id},
        ).mappings().first()

        # [FIX] نصفي data — نزيل الأعمدة غير الموجودة في SQLite
        local_cols = self._get_local_cols(s, local_table)
        data = {k: v for k, v in row.items() if k != "id" and k in local_cols}

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
            if not data:
                return
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
        # نصفي data — نزيل الأعمدة غير الموجودة في SQLite
        local_cols = self._get_local_cols(s, local_table)
        data = {k: v for k, v in row.items() if k != "id" and k in local_cols}
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
            if not data:
                return
            cols = ", ".join(data.keys())
            vals = ", ".join(f":{k}" for k in data.keys())
            s.execute(
                text(f"INSERT OR IGNORE INTO [{local_table}] ({cols}) VALUES ({vals})"),
                data,
            )

    # ── Cursor management ─────────────────────────────────

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
            val = SettingsManager.get_instance().get("sync_office_id", None)
            return _to_int(val)
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