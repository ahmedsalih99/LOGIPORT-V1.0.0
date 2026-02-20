"""
tests/test_transactions_crud.py
================================
Covers pure helper functions in transactions_crud.py — no DB required.

Functions under test:
  _norm_str()         — normalise string values
  _extract_manual_no()— extract transaction number from various dict shapes
"""
import pytest
from database.crud.transactions_crud import _norm_str, _extract_manual_no


# ══════════════════════════════════════════════════════════════════════════════
# _norm_str()
# ══════════════════════════════════════════════════════════════════════════════

class TestNormStr:

    def test_none_returns_empty(self):
        assert _norm_str(None) == ""

    @pytest.mark.parametrize("val", ["", "-", "—", "None", "null", "AUTO", "auto"])
    def test_placeholder_values_return_empty(self, val):
        assert _norm_str(val) == ""

    def test_normal_string_stripped(self):
        assert _norm_str("  TRX-001  ") == "TRX-001"

    def test_normal_string_preserved(self):
        assert _norm_str("260001") == "260001"

    def test_integer_converted(self):
        assert _norm_str(260001) == "260001"

    def test_zero_int(self):
        # 0 converts to "0" which is NOT in the placeholder set
        assert _norm_str(0) == "0"


# ══════════════════════════════════════════════════════════════════════════════
# _extract_manual_no()
# ══════════════════════════════════════════════════════════════════════════════

class TestExtractManualNo:

    # ── direct keys ───────────────────────────────────────────────────────────

    @pytest.mark.parametrize("key", [
        "transaction_no", "transactionNo", "trx_no", "trxNo",
        "no", "number", "doc_no", "docNo", "code",
    ])
    def test_all_direct_key_aliases(self, key):
        assert _extract_manual_no({key: "TRX-999"}) == "TRX-999"

    def test_empty_value_skipped(self):
        assert _extract_manual_no({"transaction_no": ""}) == ""

    def test_placeholder_value_skipped(self):
        assert _extract_manual_no({"transaction_no": "-"}) == ""

    def test_first_non_empty_wins(self):
        data = {"transaction_no": "", "no": "TRX-001"}
        assert _extract_manual_no(data) == "TRX-001"

    # ── nested dicts ──────────────────────────────────────────────────────────

    @pytest.mark.parametrize("nest_key", ["transaction", "trx", "header"])
    def test_nested_dict_keys(self, nest_key):
        data = {nest_key: {"transaction_no": "NESTED-42"}}
        assert _extract_manual_no(data) == "NESTED-42"

    def test_nested_empty_falls_through(self):
        data = {"transaction": {"transaction_no": ""}, "no": "DIRECT-1"}
        assert _extract_manual_no(data) == "DIRECT-1"

    # ── empty / missing ───────────────────────────────────────────────────────

    def test_empty_dict_returns_empty(self):
        assert _extract_manual_no({}) == ""

    def test_irrelevant_keys_return_empty(self):
        assert _extract_manual_no({"client_id": 5, "amount": 100}) == ""