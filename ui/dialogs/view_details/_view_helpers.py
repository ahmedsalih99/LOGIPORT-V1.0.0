# -*- coding: utf-8 -*-
"""
_view_helpers.py
================
دوال مشتركة لكل view_*_dialog.py
بدل تكرارها في كل ملف.
"""
from __future__ import annotations
from typing import Any, Optional


def build_dialog_table(cols: list[str], parent=None, *,
                       object_name: str = "entries-table",
                       select_rows: bool = False) -> "QTableWidget":
    """
    ينشئ QTableWidget موحّد للديالوغات:
    - فونت Bold بحجم التطبيق الحالي (من ThemeManager)
    - ارتفاع صفوف متناسب مع الخط
    - عرض أعمدة تلقائي حسب المحتوى ثم Interactive
    - رأس جدول Bold ومرتفع بما يناسب الخط
    - يتحدث تلقائياً عند تغيير الثيم

    الاستخدام:
        tbl = build_dialog_table([_("col_a"), _("col_b")], self)
    """
    from PySide6.QtWidgets import QTableWidget, QHeaderView, QAbstractItemView
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QFont

    def _get_theme():
        try:
            from core.theme_manager import ThemeManager
            tm = ThemeManager.get_instance()
            return tm.get_current_font_family(), tm.get_current_font_size()
        except Exception:
            return "Tajawal", 12

    tbl = QTableWidget(0, len(cols), parent)
    tbl.setObjectName(object_name)
    tbl.setHorizontalHeaderLabels(cols)
    tbl.setAlternatingRowColors(True)
    tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
    tbl.verticalHeader().setVisible(False)

    if select_rows:
        tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
    else:
        tbl.setSelectionMode(QAbstractItemView.NoSelection)

    def _apply_style(*_):
        fam, fs = _get_theme()
        row_h = max(32, fs * 3 + 6)
        hdr_h = max(40, fs * 3 + 8)
        hdr_f = QFont(fam, fs); hdr_f.setBold(True)
        tbl.verticalHeader().setDefaultSectionSize(row_h)
        tbl.verticalHeader().setMinimumSectionSize(32)
        tbl.horizontalHeader().setMinimumHeight(hdr_h)
        tbl.horizontalHeader().setFont(hdr_f)
        # تحديث خلايا موجودة
        cell_f = QFont(fam, fs); cell_f.setBold(True)
        for r in range(tbl.rowCount()):
            for c in range(tbl.columnCount()):
                item = tbl.item(r, c)
                if item:
                    item.setFont(cell_f)

    def _fit_columns():
        hdr = tbl.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        QTimer.singleShot(
            0,
            lambda: hdr.setSectionResizeMode(QHeaderView.Interactive)
            if not tbl.isHidden() else None
        )
        tbl.horizontalHeader().setStretchLastSection(True)

    _apply_style()
    _fit_columns()

    # ربط بتغيير الثيم
    try:
        from core.theme_manager import ThemeManager
        ThemeManager.get_instance().theme_changed.connect(_apply_style)
    except Exception:
        pass

    # حفظ الدالتين للاستخدام لاحقاً
    tbl._apply_style  = _apply_style
    tbl._fit_columns  = _fit_columns

    return tbl


def make_bold_cell(text: str, align=None) -> "QTableWidgetItem":
    """
    ينشئ QTableWidgetItem بفونت Bold بحجم التطبيق الحالي.
    استخدام:
        tbl.setItem(r, c, make_bold_cell("some text"))
    """
    from PySide6.QtWidgets import QTableWidgetItem
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont
    try:
        from core.theme_manager import ThemeManager
        tm = ThemeManager.get_instance()
        f  = QFont(tm.get_current_font_family(), tm.get_current_font_size())
    except Exception:
        f = QFont("Tajawal", 12)
    f.setBold(True)
    item = QTableWidgetItem(str(text) if text is not None else "")
    item.setFont(f)
    if align is not None:
        item.setTextAlignment(align)
    else:
        from PySide6.QtCore import Qt
        item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
    return item


def _get(obj: Any, key: str, default=None):
    """يقرأ من dict أو ORM object."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _fmt_dt(dt) -> str:
    """يحوّل datetime أو نص لصيغة موحدة — بالتوقيت المحلي."""
    from database.db_utils import format_local_dt
    try:
        import datetime
        if isinstance(dt, datetime.datetime):
            return format_local_dt(dt)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(dt or "")


def _user_to_text(val: Any, fallback_id: Optional[int] = None) -> str:
    """يحوّل ORM/dict/int لنص: full_name أو username أو id."""
    if val is None:
        return "" if fallback_id is None else str(fallback_id)
    if isinstance(val, dict):
        return (val.get("full_name") or val.get("username") or
                (str(val.get("id")) if val.get("id") is not None else ""))
    full_name = getattr(val, "full_name", None)
    username  = getattr(val, "username",  None)
    if full_name:
        return full_name
    if username:
        return username
    try:
        return str(int(val))
    except Exception:
        return str(val)


def _name_by_lang(obj, lang: str) -> str:
    """يرجع الاسم المترجم من كائن يحوي name_ar/name_en/name_tr."""
    if not obj:
        return ""
    if lang == "ar" and getattr(obj, "name_ar", None):
        return obj.name_ar
    if lang == "tr" and getattr(obj, "name_tr", None):
        return obj.name_tr
    return (getattr(obj, "name_en", None) or
            getattr(obj, "name_ar", None) or
            getattr(obj, "name_tr", None) or "")


def _add_audit_section(view, obj, _, *, lang: str = "ar"):
    """
    يضيف قسم Audit (ID, created_by/at, updated_by/at) لأي view.
    استخدام:
        _add_audit_section(view, self.obj, self._, lang=self._lang)
    """
    view.begin_section("more_details", icon="🕐", collapsed=True)
    view.add_row("id",
                 str(_get(obj, "id", "")),
                 icon="🔢", copyable=True)
    view.add_row("created_by",
                 _user_to_text(_get(obj, "created_by"), _get(obj, "created_by_id")),
                 icon="👤", copyable=False)
    view.add_row("created_at",
                 _fmt_dt(_get(obj, "created_at")),
                 icon="🕐", copyable=False)
    view.add_row("updated_by",
                 _user_to_text(_get(obj, "updated_by"), _get(obj, "updated_by_id")),
                 icon="👤", copyable=False)
    view.add_row("updated_at",
                 _fmt_dt(_get(obj, "updated_at")),
                 icon="🕐", copyable=False)