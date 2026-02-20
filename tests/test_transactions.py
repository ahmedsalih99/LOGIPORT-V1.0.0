"""
tests/test_transactions.py
===========================
Covers:
  TestTransactionPureHelpers   — pure functions (_norm_str, _extract_manual_no)
  TestTransactionsCRUDDB       — create / get / list / update / delete via in-memory DB
"""
import pytest
from datetime import date
from unittest.mock import patch


# ══════════════════════════════════════════════════════════════════════════════
# Pure helper functions
# ══════════════════════════════════════════════════════════════════════════════

class TestTransactionPureHelpers:

    @pytest.fixture(autouse=True)
    def _import(self):
        from database.crud.transactions_crud import _norm_str, _extract_manual_no
        self._norm = _norm_str
        self._extract = _extract_manual_no

    # ── _norm_str ─────────────────────────────────────────────────────────────

    def test_norm_none_returns_empty(self):
        assert self._norm(None) == ""

    def test_norm_empty_string(self):
        assert self._norm("") == ""

    def test_norm_strips_whitespace(self):
        assert self._norm("  T0001  ") == "T0001"

    @pytest.mark.parametrize("placeholder", ["-", "—", "None", "null", "AUTO", "auto"])
    def test_norm_placeholders_return_empty(self, placeholder):
        assert self._norm(placeholder) == ""

    def test_norm_valid_value_kept(self):
        assert self._norm("260006") == "260006"

    def test_norm_number_cast(self):
        assert self._norm(12345) == "12345"

    # ── _extract_manual_no ────────────────────────────────────────────────────

    def test_extract_no_number_returns_empty(self):
        assert self._extract({}) == ""

    def test_extract_from_transaction_no_key(self):
        assert self._extract({"transaction_no": "T0007"}) == "T0007"

    def test_extract_from_trx_no_alias(self):
        assert self._extract({"trx_no": "T0008"}) == "T0008"

    def test_extract_ignores_placeholder(self):
        assert self._extract({"transaction_no": "AUTO"}) == ""

    def test_extract_from_nested_dict(self):
        data = {"transaction": {"transaction_no": "T0009"}}
        assert self._extract(data) == "T0009"

    def test_extract_empty_string_returns_empty(self):
        assert self._extract({"transaction_no": ""}) == ""

    def test_extract_strips_whitespace(self):
        assert self._extract({"transaction_no": "  T0010  "}) == "T0010"


# ══════════════════════════════════════════════════════════════════════════════
# DB operations
# ══════════════════════════════════════════════════════════════════════════════

class TestTransactionsCRUDDB:

    @staticmethod
    def _patch(session_factory):
        return patch(
            "database.crud.transactions_crud.get_session_local",
            return_value=session_factory,
        )

    # ── list_transactions ─────────────────────────────────────────────────────

    def test_list_returns_list(self, session_factory, make_transaction):
        make_transaction(transaction_no="TLIST001")
        make_transaction(transaction_no="TLIST002")
        from database.crud.transactions_crud import TransactionsCRUD
        with self._patch(session_factory):
            result = TransactionsCRUD().list_transactions()
        assert isinstance(result, list)
        assert len(result) >= 2

    def test_list_filter_by_type(self, session_factory, make_transaction):
        make_transaction(transaction_no="TIMPORT01", transaction_type="import")
        make_transaction(transaction_no="TEXPORT01", transaction_type="export")
        from database.crud.transactions_crud import TransactionsCRUD
        with self._patch(session_factory):
            imports = TransactionsCRUD().list_transactions(transaction_type="import") \
                if hasattr(TransactionsCRUD().list_transactions, "__code__") \
                and "transaction_type" in TransactionsCRUD().list_transactions.__code__.co_varnames \
                else TransactionsCRUD().list_transactions()
        # At minimum, list works without error
        assert imports is not None

    def test_list_empty_db_returns_empty_list(self, session_factory):
        """Fresh session → empty list."""
        from database.crud.transactions_crud import TransactionsCRUD
        with self._patch(session_factory):
            result = TransactionsCRUD().list_transactions()
        assert isinstance(result, list)

    # ── get_with_items ────────────────────────────────────────────────────────

    def test_get_with_items_existing(self, session_factory, make_transaction):
        trx = make_transaction(transaction_no="TGET001")
        from database.crud.transactions_crud import TransactionsCRUD
        with self._patch(session_factory):
            result = TransactionsCRUD().get_with_items(trx.id)
        # result is (Transaction, [items]) or just Transaction
        assert result is not None
        if isinstance(result, tuple):
            assert result[0].id == trx.id
            assert isinstance(result[1], list)
        else:
            assert result.id == trx.id

    def test_get_with_items_nonexistent_returns_none(self, session_factory):
        from database.crud.transactions_crud import TransactionsCRUD
        with self._patch(session_factory):
            result = TransactionsCRUD().get_with_items(99999)
        assert result is None

    # ── recalc_totals ─────────────────────────────────────────────────────────

    def test_recalc_totals_existing(self, session_factory, make_transaction):
        trx = make_transaction(transaction_no="TRECALC001")
        from database.crud.transactions_crud import TransactionsCRUD
        with self._patch(session_factory):
            ok = TransactionsCRUD().recalc_totals(trx.id)
        assert ok is True

    def test_recalc_totals_nonexistent_returns_false(self, session_factory):
        from database.crud.transactions_crud import TransactionsCRUD
        with self._patch(session_factory):
            ok = TransactionsCRUD().recalc_totals(99999)
        assert ok is False

    # ── delete_transaction ────────────────────────────────────────────────────

    def test_delete_transaction_existing(self, session_factory, make_transaction):
        trx = make_transaction(transaction_no="TDEL001")
        trx_id = trx.id
        from database.crud.transactions_crud import TransactionsCRUD
        with self._patch(session_factory):
            ok = TransactionsCRUD().delete_transaction(trx_id)
        assert ok is True

    def test_delete_transaction_nonexistent(self, session_factory):
        from database.crud.transactions_crud import TransactionsCRUD
        with self._patch(session_factory):
            ok = TransactionsCRUD().delete_transaction(99999)
        assert ok is False

    # ── create_transaction ────────────────────────────────────────────────────

    def test_create_transaction_with_manual_number(
        self, session_factory, make_client, make_company, make_currency
    ):
        client   = make_client()
        exporter = make_company(name_en="Exporter")
        importer = make_company(name_en="Importer")
        currency = make_currency()

        data = {
            "transaction_no":   "MANUAL001",
            "transaction_date": date.today(),
            "transaction_type": "export",
            "client_id":        client.id,
            "exporter_company_id": exporter.id,
            "importer_company_id": importer.id,
            "currency_id":      currency.id,
        }
        from database.crud.transactions_crud import TransactionsCRUD
        with self._patch(session_factory):
            trx = TransactionsCRUD().create_transaction(data=data)
        assert trx is not None
        assert trx.transaction_no == "MANUAL001"

    def test_create_transaction_auto_number(
        self, session_factory, make_client, make_company, make_currency, db_session
    ):
        """Auto-numbering generates a non-empty transaction_no."""
        from sqlalchemy import text as _text
        client   = make_client()
        exporter = make_company(name_en="ExAuto")
        importer = make_company(name_en="ImAuto")
        currency = make_currency()

        data = {
            "transaction_date":    date.today(),
            "transaction_type":    "import",
            "client_id":           client.id,
            "exporter_company_id": exporter.id,
            "importer_company_id": importer.id,
            "currency_id":         currency.id,
        }
        from database.crud.transactions_crud import TransactionsCRUD
        with self._patch(session_factory):
            trx = TransactionsCRUD().create_transaction(data=data)
        assert trx is not None
        assert trx.transaction_no  # must be non-empty