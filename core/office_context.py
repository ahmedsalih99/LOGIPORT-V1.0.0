"""
core/office_context.py
=======================
OfficeContext — الحالة العالمية للمكتب الحالي خلال جلسة التطبيق.

يُستخدم في:
  - تعيين office_id تلقائياً عند إنشاء معاملة جديدة
  - عرض اسم المكتب في الـ TopBar
  - فلترة البيانات حسب المكتب

الاستخدام:
    # عند تسجيل الدخول:
    OfficeContext.set(user.office_id, user.office)

    # في أي مكان:
    office_id = OfficeContext.get_id()      # int | None
    office    = OfficeContext.get_office()  # Office | None
    name      = OfficeContext.get_name()    # str
"""
from __future__ import annotations
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from database.models.office import Office


class OfficeContext:
    """Singleton بسيط — بيانات المكتب الحالي لجلسة التطبيق."""

    _office_id: Optional[int]       = None
    _office:    Optional["Office"]  = None

    # ── Setters ──────────────────────────────────────────────────────────────

    @classmethod
    def set(cls, office_id: Optional[int], office: Optional["Office"] = None) -> None:
        """عيّن المكتب الحالي — يُستدعى بعد تسجيل الدخول مباشرةً."""
        cls._office_id = office_id
        cls._office    = office

    @classmethod
    def clear(cls) -> None:
        """امسح السياق — عند تسجيل الخروج."""
        cls._office_id = None
        cls._office    = None

    # ── Getters ──────────────────────────────────────────────────────────────

    @classmethod
    def get_id(cls) -> Optional[int]:
        """يُرجع office_id الحالي أو None."""
        return cls._office_id

    @classmethod
    def get_office(cls) -> Optional["Office"]:
        """يُرجع كائن Office الحالي أو None."""
        return cls._office

    @classmethod
    def get_name(cls, lang: str = "ar") -> str:
        """يُرجع اسم المكتب الحالي أو نص فارغ."""
        if cls._office:
            return cls._office.get_name(lang)
        return ""

    @classmethod
    def get_code(cls) -> str:
        """يُرجع كود المكتب الحالي أو نص فارغ."""
        return cls._office.code if cls._office else ""

    @classmethod
    def has_office(cls) -> bool:
        """True إذا كان المستخدم الحالي مرتبطاً بمكتب."""
        return cls._office_id is not None