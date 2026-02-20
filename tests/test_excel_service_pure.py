# -*- coding: utf-8 -*-
"""
tests/test_excel_service_pure.py
==================================
Tests for pure helper functions in services/excel_service.py.
No Qt, no DB required.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest


# ── Import pure helpers directly ────────────────────────────────────────────

def _import_helpers():
    """Import module-level pure helpers, skipping Qt/DB side effects."""
    import importlib
    spec = importlib.util.spec_from_file_location(
        "excel_service",
        os.path.join(os.path.dirname(os.path.dirname(__file__)),
                     "services", "excel_service.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


try:
    _mod = _import_helpers()
    _s    = _mod._s
    _rel  = _mod._rel
    _ts   = _mod._ts
    _hdr  = _mod._hdr
    _wid  = _mod._wid
    HAS_MOD = True
except Exception as e:
    HAS_MOD = False
    _SKIP_REASON = str(e)


@pytest.mark.skipif(not HAS_MOD, reason="excel_service not importable")
class TestStringHelper:
    """Tests for _s() — safe string conversion."""

    def test_none_returns_empty(self):
        assert _s(None) == ""

    def test_string_passthrough(self):
        assert _s("hello") == "hello"

    def test_int(self):
        assert _s(42) == "42"

    def test_float(self):
        assert _s(3.14) == "3.14"

    def test_empty_string(self):
        assert _s("") == ""

    def test_zero(self):
        assert _s(0) == "0"

    def test_false(self):
        assert _s(False) == "False"


@pytest.mark.skipif(not HAS_MOD, reason="excel_service not importable")
class TestRelHelper:
    """Tests for _rel() — get human-readable name from ORM object or None."""

    class _Obj:
        """Mock ORM object with multilingual name attrs."""
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    def test_none_returns_empty(self):
        assert _rel(None) == ""

    def test_name_en(self):
        obj = self._Obj(name_en="English")
        assert _rel(obj, "en") == "English"

    def test_falls_back_to_name_en_when_lang_missing(self):
        obj = self._Obj(name_en="English")
        assert _rel(obj, "ar") == "English"  # name_ar missing → fallback to name_en

    def test_name_ar(self):
        obj = self._Obj(name_ar="عربي", name_en="English")
        assert _rel(obj, "ar") == "عربي"

    def test_name_tr(self):
        obj = self._Obj(name_tr="Türkçe", name_en="English")
        assert _rel(obj, "tr") == "Türkçe"

    def test_falls_back_to_code(self):
        obj = self._Obj(code="USD")
        assert _rel(obj) == "USD"

    def test_plain_string(self):
        # Objects with no name attrs get str() representation
        assert _rel("plain") == "plain"

    def test_name_priority_over_code(self):
        obj = self._Obj(name_en="Dollars", code="USD")
        assert _rel(obj, "en") == "Dollars"


@pytest.mark.skipif(not HAS_MOD, reason="excel_service not importable")
class TestTimestampHelper:
    """Tests for _ts() — timestamp string."""

    def test_format(self):
        ts = _ts()
        assert len(ts) == 15                   # YYYYMMDD_HHMMSS
        assert ts[8] == "_"
        assert ts[:8].isdigit()
        assert ts[9:].isdigit()

    def test_uniqueness(self):
        import time
        t1 = _ts()
        time.sleep(1.1)
        t2 = _ts()
        # After 1 second the seconds digit should differ
        assert t1 != t2


@pytest.mark.skipif(not HAS_MOD, reason="excel_service not importable")
class TestColumnHelpers:
    """Tests for _hdr() and _wid() — column definition helpers.
    
    Column tuple format: (key, ar_label, en_label, tr_label, width)
    _LANG_IDX = {"ar": 1, "en": 2, "tr": 3}
    """

    def test_hdr_ar(self):
        col = ("title_key", "العنوان", "Title", "Başlık", 20)
        assert _hdr(col, "ar") == "العنوان"

    def test_hdr_en(self):
        col = ("title_key", "العنوان", "Title", "Başlık", 20)
        assert _hdr(col, "en") == "Title"

    def test_hdr_tr(self):
        col = ("title_key", "العنوان", "Title", "Başlık", 20)
        assert _hdr(col, "tr") == "Başlık"

    def test_hdr_unknown_lang_falls_back_to_en(self):
        col = ("key", "اسم", "Name", "Ad", 15)
        # unknown lang → index 2 (en)
        assert _hdr(col, "fr") == "Name"

    def test_wid(self):
        col = ("title_key", "العنوان", "Title", "Başlık", 20)
        assert _wid(col) == 20

    def test_wid_different_value(self):
        col = ("key", "اسم", "Name", "Ad", 35)
        assert _wid(col) == 35
