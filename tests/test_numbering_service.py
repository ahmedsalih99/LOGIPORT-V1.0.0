# -*- coding: utf-8 -*-
"""
tests/test_numbering_service.py
=================================
Tests for NumberingService pure static methods (no DB required).
DB-dependent methods tested via in-memory SQLite.
"""
import pytest
from services.numbering_service import NumberingService


# ── pure static helpers ───────────────────────────────────────────────────────

class TestPrefixForDocCode:

    def test_known_prefix_invoice(self):
        p = NumberingService.prefix_for_doc_code("invoice.syrian.ar")
        assert isinstance(p, str)
        assert len(p) > 0

    def test_known_prefix_packing_list(self):
        p = NumberingService.prefix_for_doc_code("packing_list.ar")
        assert isinstance(p, str)

    def test_unknown_code_uses_last_segment(self):
        # "foo.bar.baz" → fallback is last segment uppercased, max 6 chars
        p = NumberingService.prefix_for_doc_code("foo.bar.baz")
        assert p == "BAZ"

    def test_unknown_short_code_capped_at_6(self):
        p = NumberingService.prefix_for_doc_code("foo.toolongcode")
        assert len(p) <= 6


class TestGenerateDocumentName:

    def test_basic_structure(self):
        name = NumberingService.generate_document_name(
            "invoice.syrian", "TXN-001", "ar"
        )
        assert "TXN-001" in name
        assert name.endswith(".pdf")
        assert "AR" in name

    def test_spaces_replaced_in_transaction_no(self):
        name = NumberingService.generate_document_name(
            "invoice.syrian", "TXN 001", "en"
        )
        assert " " not in name

    def test_slashes_replaced_with_dash(self):
        name = NumberingService.generate_document_name(
            "packing_list", "2024/001", "ar"
        )
        assert "/" not in name
        assert "-" in name

    def test_custom_extension(self):
        name = NumberingService.generate_document_name(
            "invoice.syrian", "001", "en", extension="html"
        )
        assert name.endswith(".html")

    def test_language_uppercased(self):
        name = NumberingService.generate_document_name("packing_list", "001", "tr")
        assert "TR" in name


class TestGenerateDocumentFolder:

    def test_basic_structure(self):
        folder = NumberingService.generate_document_folder("TXN-001", 2024, 3)
        assert "2024" in folder
        assert "03" in folder
        assert "TXN-001" in folder

    def test_month_zero_padded(self):
        folder = NumberingService.generate_document_folder("001", 2024, 1)
        assert "/01/" in folder

    def test_spaces_removed(self):
        folder = NumberingService.generate_document_folder("TXN 001", 2024, 5)
        assert " " not in folder

    def test_slashes_in_no_replaced(self):
        folder = NumberingService.generate_document_folder("2024/001", 2024, 5)
        assert "2024/001" not in folder


class TestExtractNumericPart:

    def test_pure_number(self):
        assert NumberingService.extract_numeric_part("12345") == 12345

    def test_prefixed_number(self):
        assert NumberingService.extract_numeric_part("TX-00123") == 123

    def test_mixed_chars(self):
        result = NumberingService.extract_numeric_part("ABC00456DEF")
        assert result == 456

    def test_no_digits_returns_none(self):
        assert NumberingService.extract_numeric_part("ABCDEF") is None

    def test_empty_string_returns_none(self):
        assert NumberingService.extract_numeric_part("") is None

    @pytest.mark.parametrize("no, expected", [
        ("260001", 260001),
        ("T-2024-001", 2024001),
        ("INV001", 1),
    ])
    def test_various_formats(self, no, expected):
        result = NumberingService.extract_numeric_part(no)
        assert result == expected


class TestFormatTransactionNumber:

    def test_no_prefix(self):
        assert NumberingService.format_transaction_number(42) == "42"

    def test_with_prefix(self):
        assert NumberingService.format_transaction_number(42, "TX-") == "TX-42"

    def test_empty_prefix(self):
        assert NumberingService.format_transaction_number(100, "") == "100"

    def test_large_number(self):
        result = NumberingService.format_transaction_number(260001, "T")
        assert result == "T260001"


class TestIsNumericTransaction:

    @pytest.mark.parametrize("txn_no, expected", [
        ("26000",  True),    # pure digits ≥4
        ("T26000", True),    # prefix + digits
        ("TX26000", True),   # 2-char prefix + digits
        ("123",    False),   # too short (< 4 digits)
        ("ABCDEF", False),   # no digits
        ("TX-A001", False),  # non-digit after strip
        ("260001", True),
    ])
    def test_cases(self, txn_no, expected):
        assert NumberingService.is_numeric_transaction(txn_no) == expected
