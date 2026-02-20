# -*- coding: utf-8 -*-
"""
_view_helpers.py
================
دوال مشتركة لكل view_*_dialog.py
بدل تكرارها في كل ملف.
"""
from __future__ import annotations
from typing import Any, Optional


def _get(obj: Any, key: str, default=None):
    """يقرأ من dict أو ORM object."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _fmt_dt(dt) -> str:
    """يحوّل datetime أو نص لصيغة موحدة."""
    try:
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
