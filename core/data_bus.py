"""
core/data_bus.py — LOGIPORT
=============================
نظام إشعار بين التابات (inter-tab refresh).

عندما يُعدِّل تاب بيانات معينة يُصدر signal على DataBus،
والتابات الأخرى المهتمة تستمع وتُحدِّث نفسها.

الاستخدام:
    # عند الإضافة/التعديل/الحذف في أي تاب:
    DataBus.get_instance().emit("clients")
    DataBus.get_instance().emit("transactions")

    # للاستماع في تاب آخر:
    DataBus.get_instance().subscribe("clients", self.reload_data)
"""
from __future__ import annotations
import logging
from typing import Callable, Dict, List

from PySide6.QtCore import QObject, Signal
from core.singleton import QObjectSingletonMixin

logger = logging.getLogger(__name__)

# الأحداث المدعومة — اسم الجدول/الكيان الذي تغيّر
ENTITIES = [
    "clients",
    "companies",
    "transactions",
    "entries",
    "containers",
    "tasks",
    "documents",
    "materials",
    "users",
    "offices",
    "pricing",
    "countries",
    "currencies",
    "packaging",
    "delivery_methods",
]


class DataBus(QObject, QObjectSingletonMixin):
    """
    Singleton يعمل كـ event bus بين التابات.
    أي تاب يُعدِّل بيانات يُصدر emit(entity)،
    والتابات المعنية تستمع وتُحدِّث نفسها تلقائياً.
    """

    # signal واحد عام — يحمل اسم الكيان الذي تغيّر
    data_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._subscribers: Dict[str, List[Callable]] = {}

    @classmethod
    def get_instance(cls) -> "DataBus":
        if not hasattr(cls, "_instance") or cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def emit(self, entity: str) -> None:
        """
        أصدر إشعار بأن بيانات entity تغيّرت.
        entity: اسم الكيان (clients, transactions, ...)
        """
        if entity not in ENTITIES:
            logger.debug("DataBus.emit: unknown entity '%s'", entity)
        logger.debug("DataBus: %s changed", entity)
        self.data_changed.emit(entity)
        # استدعاء المشتركين المباشرين
        for cb in list(self._subscribers.get(entity, [])):
            try:
                cb()
            except Exception as e:
                logger.warning("DataBus subscriber error (%s): %s", entity, e)
        # المشتركون على "all"
        for cb in list(self._subscribers.get("all", [])):
            try:
                cb()
            except Exception as e:
                logger.warning("DataBus all-subscriber error: %s", e)

    def subscribe(self, entity: str, callback: Callable) -> None:
        """
        سجّل callback ليُستدعى عند تغيّر entity.
        entity="all" يستقبل أي تغيير.
        """
        if entity not in self._subscribers:
            self._subscribers[entity] = []
        if callback not in self._subscribers[entity]:
            self._subscribers[entity].append(callback)

    def unsubscribe(self, entity: str, callback: Callable) -> None:
        """أزل callback من قائمة المشتركين."""
        if entity in self._subscribers:
            try:
                self._subscribers[entity].remove(callback)
            except ValueError:
                pass