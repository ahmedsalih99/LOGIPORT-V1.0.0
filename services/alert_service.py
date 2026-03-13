"""
alert_service.py — LOGIPORT
=============================
AlertService: يراقب قاعدة البيانات ويُصدر تنبيهات ذكية عبر NotificationService.

التنبيهات:
  1. كونتينرات ETA متأخرة (ETA < اليوم، الحالة لا تزال نشطة)
  2. كونتينرات ETA اليوم أو غداً (تحذير مسبق)
  3. معاملات draft أكثر من X أيام بدون تحديث

الاستخدام:
    svc = AlertService.get_instance()
    svc.start()          # يبدأ الفحص كل ساعة
    svc.check_now()      # فحص فوري
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Set

from PySide6.QtCore import QObject, QTimer

from core.singleton import QObjectSingletonMixin
from core.translator import TranslationManager

logger = logging.getLogger(__name__)

# الحالات التي تعني أن الكونتينر لا يزال في الطريق
_ACTIVE_STATUSES = {"booked", "loaded", "in_transit", "arrived", "customs"}

# كم يوم يبقى المعاملة draft قبل التنبيه
_DRAFT_DAYS_THRESHOLD = 7


class AlertService(QObject, QObjectSingletonMixin):
    """
    Singleton يفحص DB ويُرسل تنبيهات عبر NotificationService.
    لا يُطلق signals خاصة به — يستخدم add_manual() من NotificationService.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # نحفظ الـ IDs التي أرسلنا تنبيهاً عنها في هذه الجلسة
        # حتى لا نكرر التنبيه عند كل فحص
        self._alerted_containers: Set[int] = set()
        self._alerted_drafts:     Set[int] = set()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.check_now)

    def start(self, interval_ms: int = 3_600_000):
        """يبدأ الفحص الدوري (افتراضي: كل ساعة). يُجري فحصاً فورياً أيضاً."""
        self.check_now()
        self._timer.start(interval_ms)
        logger.info("AlertService started (interval=%dms)", interval_ms)

    def stop(self):
        self._timer.stop()

    def check_now(self):
        """فحص فوري لكل التنبيهات."""
        try:
            self._check_containers()
        except Exception as e:
            logger.warning("AlertService._check_containers: %s", e)

        try:
            self._check_draft_transactions()
        except Exception as e:
            logger.warning("AlertService._check_draft_transactions: %s", e)

    # ── فحص الكونتينرات ───────────────────────────────────────────────────────

    def _check_containers(self):
        from database.models import get_session_local
        from database.models.container_tracking import ContainerTracking

        today = date.today()
        tomorrow = today + timedelta(days=1)

        with get_session_local()() as session:
            containers = (
                session.query(ContainerTracking)
                .filter(
                    ContainerTracking.eta.isnot(None),
                    ContainerTracking.status.in_(_ACTIVE_STATUSES),
                )
                .all()
            )

            for c in containers:
                if c.id in self._alerted_containers:
                    continue

                eta: date = c.eta
                no  = c.container_no or f"#{c.id}"

                if eta < today:
                    # متأخر
                    days_late = (today - eta).days
                    self._send(
                        key="alert_container_overdue",
                        kwargs={"no": no, "days": days_late},
                        level="danger",
                        icon="🚨",
                    )
                    self._alerted_containers.add(c.id)

                elif eta == today:
                    # يصل اليوم
                    self._send(
                        key="alert_container_today",
                        kwargs={"no": no},
                        level="warning",
                        icon="⏰",
                    )
                    self._alerted_containers.add(c.id)

                elif eta == tomorrow:
                    # يصل غداً
                    self._send(
                        key="alert_container_tomorrow",
                        kwargs={"no": no},
                        level="warning",
                        icon="📅",
                    )
                    self._alerted_containers.add(c.id)

    # ── فحص المعاملات المعلقة ─────────────────────────────────────────────────

    def _check_draft_transactions(self):
        from database.models import get_session_local
        from database.models.transaction import Transaction

        threshold = datetime.now() - timedelta(days=_DRAFT_DAYS_THRESHOLD)

        with get_session_local()() as session:
            drafts = (
                session.query(Transaction)
                .filter(
                    Transaction.status == "draft",
                    Transaction.updated_at < threshold,
                )
                .all()
            )

            for tx in drafts:
                if tx.id in self._alerted_drafts:
                    continue

                days_old = (datetime.now() - tx.updated_at).days
                tx_no = getattr(tx, "transaction_no", None) or f"#{tx.id}"

                self._send(
                    key="alert_draft_old",
                    kwargs={"no": tx_no, "days": days_old},
                    level="warning",
                    icon="📋",
                )
                self._alerted_drafts.add(tx.id)

    # ── مساعد ────────────────────────────────────────────────────────────────

    def _send(self, key: str, kwargs: dict, level: str, icon: str):
        """يُرسل تنبيهاً عبر NotificationService."""
        try:
            from services.notification_service import NotificationService
            _t = TranslationManager.get_instance().translate
            msg = _t(key).format(**kwargs)
            NotificationService.get_instance().add_manual(msg, level=level, icon=icon)
            logger.info("Alert sent: [%s] %s", level, msg)
        except Exception as e:
            logger.warning("AlertService._send: %s", e)
