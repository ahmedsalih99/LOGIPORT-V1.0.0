"""
NotificationService - LOGIPORT
================================

Real notification system built on AuditLog polling via QTimer.

Usage:
    svc = NotificationService.get_instance()
    svc.new_notification.connect(my_handler)
    svc.start()
"""

from __future__ import annotations
import logging
from datetime import datetime
from typing import List, Optional

from PySide6.QtCore import QObject, Signal, QTimer
from core.singleton import QObjectSingletonMixin
from core.translator import TranslationManager

logger = logging.getLogger(__name__)


class Notification:
    LEVEL_INFO    = "info"
    LEVEL_SUCCESS = "success"
    LEVEL_WARNING = "warning"
    LEVEL_DANGER  = "danger"

    ICONS = {
        "create":       ("➕", "success"),
        "insert":       ("➕", "success"),
        "update":       ("✏️",  "info"),
        "delete":       ("🗑️", "danger"),
        "import":       ("📥", "info"),
        "export":       ("📤", "info"),
        "print":        ("🖨️", "info"),
        "bulk_create":  ("📦", "success"),
        "bulk_insert":  ("📦", "success"),
        "bulk_delete":  ("🗑️", "danger"),
        "login":        ("🔓", "success"),
        "logout":       ("🔒", "info"),
        "sync_ok":      ("☁️",  "success"),
        "sync_error":   ("⚠️",  "warning"),
        "backup_ok":    ("💾", "success"),
        "backup_error": ("⚠️",  "warning"),
        "pdf":          ("📄", "info"),
        "manual":       ("📢", "info"),
    }

    TABLE_KEYS = {
        "transactions":       "table_transactions",
        "transaction_items":  "table_transaction_items",
        "materials":          "table_materials",
        "clients":            "table_clients",
        "client_contacts":    "table_client_contacts",
        "users":              "table_users",
        "documents":          "table_documents",
        "doc_groups":         "table_doc_groups",
        "entries":            "table_entries",
        "entry_items":        "table_entry_items",
        "companies":          "table_companies",
        "company_banks":      "table_company_banks",
        "pricing":            "table_pricing",
        "material_types":     "table_material_types",
        "currencies":         "table_currencies",
        "countries":          "table_countries",
        "delivery_methods":   "table_delivery_methods",
        "packaging_types":    "table_packaging_types",
        "offices":            "table_offices",
        "roles":              "table_roles",
        "transport_details":  "table_transport_details",
        "container_tracking": "table_container_tracking",
    }

    ACTION_KEYS = {
        "create":       "action_create",
        "insert":       "action_insert",
        "update":       "action_update",
        "delete":       "action_delete",
        "import":       "action_import",
        "export":       "action_export",
        "print":        "action_print",
        "bulk_create":  "action_bulk_create",
        "bulk_insert":  "action_bulk_insert",
        "bulk_delete":  "action_bulk_delete",
        "login":        "action_login",
        "logout":       "action_logout",
        "pdf":          "action_pdf",
    }

    @classmethod
    def _t(cls, key: str) -> str:
        """Get translated string for given key."""
        return TranslationManager.get_instance().translate(key)

    def __init__(self, notif_id, action, table_name, user_name, timestamp,
                 details=None, record_id=None):
        self.id         = notif_id
        self.action     = (action or "update").lower()
        self.table_name = table_name or ""
        self.user_name  = user_name or self._t("system_user")
        self.timestamp  = timestamp or datetime.now()
        self.details    = details
        self.record_id  = record_id
        self.is_read    = False

        icon_data       = self.ICONS.get(self.action, ("📝", "info"))
        self.icon       = icon_data[0]
        self.level      = icon_data[1]

    @property
    def table_ar(self):
        key = self.TABLE_KEYS.get(self.table_name)
        return self._t(key) if key else self.table_name

    @property
    def action_ar(self):
        key = self.ACTION_KEYS.get(self.action)
        return self._t(key) if key else self.action

    @property
    def message(self):
        return self._t("notification_msg").format(user=self.user_name, action=self.action_ar, table=self.table_ar)

    @property
    def time_ago(self):
        secs = int((datetime.now() - self.timestamp).total_seconds())
        if secs < 60:    return self._t("time_ago_now")
        if secs < 3600:  return self._t("time_ago_minutes").format(n=secs // 60)
        if secs < 86400: return self._t("time_ago_hours").format(n=secs // 3600)
        return self._t("time_ago_days").format(n=secs // 86400)


class NotificationService(QObject, QObjectSingletonMixin):
    """Singleton: polls AuditLog and emits Qt signals."""

    new_notification      = Signal(object)
    notifications_updated = Signal()
    unread_count_changed  = Signal(int)


    def __init__(self, parent=None):
        super().__init__(parent)
        self._notifications: List[Notification] = []
        self._last_id: int = 0
        self._max: int = 50
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)

    def start(self, poll_ms: int = 15000):
        self._load_initial()
        self._timer.start(poll_ms)
        logger.info("NotificationService started")

    def stop(self):
        self._timer.stop()

    @property
    def notifications(self) -> List[Notification]:
        return self._notifications

    @property
    def unread_count(self) -> int:
        return sum(1 for n in self._notifications if not n.is_read)

    def mark_all_read(self):
        for n in self._notifications:
            n.is_read = True
        self.unread_count_changed.emit(0)
        self.notifications_updated.emit()

    def mark_read(self, notif_id: int):
        for n in self._notifications:
            if n.id == notif_id:
                n.is_read = True
        self.unread_count_changed.emit(self.unread_count)

    def clear_all(self):
        self._notifications.clear()
        self.unread_count_changed.emit(0)
        self.notifications_updated.emit()

    def add_manual(self, message: str, level: str = "info", icon: str = "📢"):
        """Add a manual (non-DB) notification."""
        n = Notification(-len(self._notifications)-1, "manual", "", "", datetime.now())
        n.icon  = icon
        n.level = level
        n._msg  = message
        n.__class__ = _ManualNotif
        self._push(n)

    def notify_login(self, user_name: str = ""):
        _t = TranslationManager.get_instance().translate
        msg = _t("notif_login").format(name=user_name) if user_name else _t("notif_login_generic")
        self.add_manual(msg, level="success", icon="🔓")

    def notify_logout(self, user_name: str = ""):
        _t = TranslationManager.get_instance().translate
        msg = _t("notif_logout").format(name=user_name) if user_name else _t("notif_logout_generic")
        self.add_manual(msg, level="info", icon="🔒")

    def notify_sync(self, success: bool, pushed: int = 0, pulled: int = 0, error: str = ""):
        _t = TranslationManager.get_instance().translate
        if success:
            msg = _t("notif_sync_ok").format(pushed=pushed, pulled=pulled)
            self.add_manual(msg, level="success", icon="☁️")
        else:
            msg = _t("notif_sync_error").format(error=error)
            self.add_manual(msg, level="warning", icon="⚠️")

    def notify_backup(self, success: bool, path: str = "", error: str = ""):
        _t = TranslationManager.get_instance().translate
        if success:
            msg = _t("notif_backup_ok").format(path=path)
            self.add_manual(msg, level="success", icon="💾")
        else:
            msg = _t("notif_backup_error").format(error=error)
            self.add_manual(msg, level="warning", icon="⚠️")

    def notify_pdf(self, doc_name: str = ""):
        _t = TranslationManager.get_instance().translate
        msg = _t("notif_pdf").format(name=doc_name) if doc_name else _t("notif_pdf_generic")
        self.add_manual(msg, level="info", icon="📄")

    # ── private ─────────────────────────────────────────────────────────────

    def _load_initial(self):
        try:
            from database.models import get_session_local, AuditLog
            from sqlalchemy.orm import joinedload
            from sqlalchemy import desc

            with get_session_local()() as session:
                rows = (session.query(AuditLog)
                        .options(joinedload(AuditLog.user))
                        .order_by(desc(AuditLog.id))
                        .limit(30).all())

                if rows:
                    self._last_id = rows[0].id

                for row in reversed(rows):
                    n = self._to_notif(row)
                    if n:
                        n.is_read = True
                        self._notifications.insert(0, n)

                self._trim()
        except Exception as e:
            logger.warning(f"NotificationService init load: {e}")

    def _poll(self):
        try:
            from database.models import get_session_local, AuditLog
            from sqlalchemy.orm import joinedload

            with get_session_local()() as session:
                rows = (session.query(AuditLog)
                        .options(joinedload(AuditLog.user))
                        .filter(AuditLog.id > self._last_id)
                        .order_by(AuditLog.id).all())

                for row in rows:
                    n = self._to_notif(row)
                    if n:
                        self._push(n)
                        self._last_id = row.id
        except Exception as e:
            logger.debug(f"NotificationService poll: {e}")

    def _to_notif(self, row) -> Optional[Notification]:
        try:
            uname = ""
            if row.user:
                uname = getattr(row.user, "full_name", None) or getattr(row.user, "username", "") or ""
            return Notification(row.id, row.action, row.table_name, uname,
                                row.timestamp, row.details, row.record_id)
        except Exception:
            return None

    def _push(self, n: Notification):
        self._notifications.insert(0, n)
        self._trim()
        self.new_notification.emit(n)
        self.unread_count_changed.emit(self.unread_count)
        self.notifications_updated.emit()

    def _trim(self):
        if len(self._notifications) > self._max:
            self._notifications = self._notifications[:self._max]


class _ManualNotif(Notification):
    @property
    def message(self):
        return getattr(self, "_msg", self._t("notification_default"))