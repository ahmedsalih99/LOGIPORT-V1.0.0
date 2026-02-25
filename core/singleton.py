"""
singleton.py — LOGIPORT
========================
مصدر الحقيقة الوحيد لنمط Singleton في المشروع.

طريقتان فقط — حسب نوع الكلاس:

  ① QObjectSingletonMixin  ← لكل كلاس يرث من QObject
        class MyManager(QObject, QObjectSingletonMixin): ...
        MyManager.get_instance()

  ② SingletonMeta          ← للكلاسات العادية (لا تحتاج Qt)
        class MyService(metaclass=SingletonMeta): ...
        MyService()  # أو MyService.get_instance()

كلا الطريقتين:
  - Thread-safe بـ double-checked locking
  - تدعم clear_instance() و clear_all_instances() للاختبارات
  - تسجّل في logger عند الإنشاء والحذف
"""
from __future__ import annotations

import threading
import logging
from typing import Any, Dict, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ─────────────────────────────────────────────────────────────────────────────
# ① QObjectSingletonMixin — للكلاسات التي ترث QObject
# ─────────────────────────────────────────────────────────────────────────────

class QObjectSingletonMixin:
    """
    Mixin يُضيف get_instance() thread-safe لأي كلاس يرث QObject.

    لا يمكن استخدام metaclass مع QObject (تعارض مع shiboken/Qt metaclass).
    هذا الـ Mixin يحل المشكلة بطريقة نظيفة.

    الاستخدام:
        class MyManager(QObject, QObjectSingletonMixin):
            def __init__(self):
                super().__init__()
                # ... تهيئة الكلاس

        mgr = MyManager.get_instance()  # دائماً نفس الـ instance
        MyManager.clear_instance()      # للاختبارات فقط
    """

    _singleton_instances: Dict[type, Any] = {}
    _singleton_lock: threading.Lock = threading.Lock()

    @classmethod
    def get_instance(cls: Type[T]) -> T:
        """إرجاع الـ instance الوحيد، مع إنشائه إن لم يكن موجوداً."""
        if cls not in cls._singleton_instances:
            with cls._singleton_lock:
                if cls not in cls._singleton_instances:
                    instance = cls()
                    cls._singleton_instances[cls] = instance
                    logger.debug(f"[Singleton] Created: {cls.__name__}")
        return cls._singleton_instances[cls]

    @classmethod
    def clear_instance(cls) -> None:
        """حذف الـ instance (للاختبارات فقط)."""
        with cls._singleton_lock:
            if cls in cls._singleton_instances:
                del cls._singleton_instances[cls]
                logger.debug(f"[Singleton] Cleared: {cls.__name__}")

    @classmethod
    def clear_all_instances(cls) -> None:
        """حذف جميع الـ instances المسجّلة (للاختبارات فقط)."""
        with cls._singleton_lock:
            count = len(cls._singleton_instances)
            cls._singleton_instances.clear()
            logger.debug(f"[Singleton] Cleared all ({count} instances)")


# ─────────────────────────────────────────────────────────────────────────────
# ② SingletonMeta — للكلاسات العادية (لا ترث QObject)
# ─────────────────────────────────────────────────────────────────────────────

class SingletonMeta(type):
    """
    Metaclass يجعل أي كلاس عادي Singleton thread-safe.

    الاستخدام:
        class MyService(metaclass=SingletonMeta):
            def __init__(self):
                ...

        svc1 = MyService()
        svc2 = MyService()
        assert svc1 is svc2  # True دائماً

        # للاستخدام مع typing:
        svc = MyService.get_instance()  # مكافئ لـ MyService()
    """

    _instances: Dict[type, Any] = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance
                    logger.debug(f"[Singleton] Created: {cls.__name__}")
        return cls._instances[cls]

    def get_instance(cls, *args, **kwargs):
        """نفس سلوك __call__ — يوفّر واجهة موحّدة مع QObjectSingletonMixin."""
        return cls(*args, **kwargs)

    def clear_instance(cls) -> None:
        """حذف الـ instance (للاختبارات فقط)."""
        with cls._lock:
            if cls in cls._instances:
                del cls._instances[cls]
                logger.debug(f"[Singleton] Cleared: {cls.__name__}")

    def clear_all_instances(cls) -> None:
        """حذف جميع الـ instances (للاختبارات فقط)."""
        with cls._lock:
            count = len(cls._instances)
            cls._instances.clear()
            logger.debug(f"[Singleton] Cleared all ({count} instances)")


# ─────────────────────────────────────────────────────────────────────────────
# Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = ["QObjectSingletonMixin", "SingletonMeta"]