# -*- coding: utf-8 -*-
"""
tests/test_storage_service.py
================================
Tests for StorageService path generation — pure logic, uses tmp_path fixture.
"""
import re
import pytest
from pathlib import Path
from services.storage_service import StorageService, _safe_tx


# ── _safe_tx ─────────────────────────────────────────────────────────────────

class TestSafeTx:

    @pytest.mark.parametrize("inp, expected", [
        ("TXN-001",         "TXN-001"),
        ("TXN/001",         "TXN-001"),
        ("TXN\\001",        "TXN-001"),
        ("TXN 001",         "TXN-001"),
        ("TXN  /  001",     "TXN-001"),
        ("",                "UNKNOWN"),
        ("   ",             "UNKNOWN"),
        ("   /  \\  ",      "-"),    # slashes/spaces → dash, strip outer → "-"
        ("simple",          "simple"),
        ("2024/001/extra",  "2024-001-extra"),
    ])
    def test_safe_tx(self, inp, expected):
        assert _safe_tx(inp) == expected


# ── build_output_path ─────────────────────────────────────────────────────────

class TestBuildOutputPath:

    def test_returns_path_object(self, tmp_path):
        svc = StorageService(str(tmp_path))
        result = svc.build_output_path("TXN-001", "DOC-001", "ar", "invoice")
        assert isinstance(result, Path)

    def test_extension_in_filename(self, tmp_path):
        svc = StorageService(str(tmp_path))
        result = svc.build_output_path("TXN-001", "DOC-001", "en", "invoice", ext="html")
        assert result.name == "invoice.html"

    def test_language_lowercased_in_path(self, tmp_path):
        svc = StorageService(str(tmp_path))
        result = svc.build_output_path("TXN-001", "DOC-001", "AR", "invoice")
        assert "ar" in str(result)
        assert "AR" not in str(result)

    def test_directory_created(self, tmp_path):
        svc = StorageService(str(tmp_path))
        result = svc.build_output_path("TXN-001", "DOC-001", "ar", "invoice")
        assert result.parent.exists()

    def test_unsafe_chars_sanitized(self, tmp_path):
        svc = StorageService(str(tmp_path))
        result = svc.build_output_path("TXN/001", "DOC-001", "ar", "invoice")
        assert "/" not in str(result.parent.name)

    def test_doc_type_lowercased(self, tmp_path):
        svc = StorageService(str(tmp_path))
        result = svc.build_output_path("TXN-001", "DOC-001", "ar", "INVOICE")
        assert result.name.startswith("invoice")


# ── build_output_path_from_doc_no ─────────────────────────────────────────────

class TestBuildOutputPathFromDocNo:

    def test_extracts_year_month_from_doc_no(self, tmp_path):
        svc = StorageService(str(tmp_path))
        result = svc.build_output_path_from_doc_no(
            "TXN-001", "INV-202403-0042", "ar", "invoice"
        )
        assert "2024" in str(result)
        assert "03" in str(result)

    def test_fallback_when_no_date_in_doc_no(self, tmp_path):
        import datetime
        svc = StorageService(str(tmp_path))
        result = svc.build_output_path_from_doc_no(
            "TXN-001", "NODATEHERE", "ar", "invoice"
        )
        today = datetime.date.today()
        assert str(today.year) in str(result)

    def test_returns_path_object(self, tmp_path):
        svc = StorageService(str(tmp_path))
        result = svc.build_output_path_from_doc_no(
            "TXN-001", "INV-202501-0001", "en", "packing_list"
        )
        assert isinstance(result, Path)

    def test_doc_no_in_path(self, tmp_path):
        svc = StorageService(str(tmp_path))
        doc_no = "INV-202406-0099"
        result = svc.build_output_path_from_doc_no("TXN-001", doc_no, "ar", "invoice")
        assert doc_no in str(result)

    def test_custom_extension(self, tmp_path):
        svc = StorageService(str(tmp_path))
        result = svc.build_output_path_from_doc_no(
            "TXN-001", "INV-202403-0001", "ar", "invoice", ext="html"
        )
        assert result.suffix == ".html"

    def test_directory_created(self, tmp_path):
        svc = StorageService(str(tmp_path))
        result = svc.build_output_path_from_doc_no(
            "TXN-001", "INV-202403-0001", "ar", "invoice"
        )
        assert result.parent.exists()

    @pytest.mark.parametrize("doc_no,year,month", [
        ("PL-202312-0001", "2023", "12"),
        ("INV-202501-0099", "2025", "01"),
        ("DOC-202609-0007", "2026", "09"),
    ])
    def test_various_doc_no_formats(self, tmp_path, doc_no, year, month):
        svc = StorageService(str(tmp_path))
        result = svc.build_output_path_from_doc_no("TX-001", doc_no, "en", "invoice")
        assert year in str(result)
        assert f"/{month}/" in str(result)


# ── StorageService init ───────────────────────────────────────────────────────

class TestInit:

    def test_creates_root_directory(self, tmp_path):
        new_dir = tmp_path / "new_docs_root"
        assert not new_dir.exists()
        StorageService(str(new_dir))
        assert new_dir.exists()

    def test_root_attribute(self, tmp_path):
        svc = StorageService(str(tmp_path))
        assert svc.root == tmp_path
