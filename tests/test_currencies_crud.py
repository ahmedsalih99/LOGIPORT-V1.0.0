# -*- coding: utf-8 -*-
"""
tests/test_currencies_crud.py
================================
Tests for CurrenciesCRUD — add, get, list, get_by_code, update, delete.
"""
import pytest
from unittest.mock import patch
from database.crud.currencies_crud import CurrenciesCRUD

_PATCH = "database.crud.currencies_crud.get_session_local"


class TestAddCurrency:

    def test_add_basic(self, session_factory):
        with patch(_PATCH, session_factory):
            c = CurrenciesCRUD().add_currency(
                code="USD", name_ar="دولار", name_en="Dollar", name_tr="Dolar", symbol="$"
            )
        assert c.id is not None
        assert c.code == "USD"
        assert c.symbol == "$"

    def test_add_without_symbol(self, session_factory):
        with patch(_PATCH, session_factory):
            c = CurrenciesCRUD().add_currency(
                code="EUR", name_ar="يورو", name_en="Euro", name_tr="Euro"
            )
        assert c.code == "EUR"

    def test_add_with_lowercase_code(self, session_factory):
        """Currency code is stored as-is (no forced uppercase in CRUD)."""
        with patch(_PATCH, session_factory):
            c = CurrenciesCRUD().add_currency(
                code="gbp", name_ar="جنيه", name_en="Pound", name_tr="Pound"
            )
        assert c.code == "gbp"   # stored as provided


class TestGetCurrency:

    def test_get_by_id(self, session_factory):
        with patch(_PATCH, session_factory):
            crud = CurrenciesCRUD()
            c = crud.add_currency(code="JPY", name_ar="ين", name_en="Yen", name_tr="Yen")
            found = crud.get_currency(c.id)
        assert found is not None
        assert found.code == "JPY"

    def test_get_missing_returns_none(self, session_factory):
        with patch(_PATCH, session_factory):
            assert CurrenciesCRUD().get_currency(99999) is None

    def test_get_by_code(self, session_factory):
        with patch(_PATCH, session_factory):
            crud = CurrenciesCRUD()
            crud.add_currency(code="CHF", name_ar="فرنك", name_en="Franc", name_tr="Frank")
            found = crud.get_by_code("CHF")
        assert found is not None
        assert found.name_en == "Franc"

    def test_get_by_code_missing_returns_none(self, session_factory):
        with patch(_PATCH, session_factory):
            assert CurrenciesCRUD().get_by_code("XYZ") is None


class TestListCurrencies:

    def test_list_includes_added(self, session_factory):
        with patch(_PATCH, session_factory):
            crud = CurrenciesCRUD()
            crud.add_currency(code="TRY", name_ar="ليرة", name_en="Lira", name_tr="Lira")
            items = crud.list_currencies()
        assert any(c.code == "TRY" for c in items)

    def test_list_empty_initially(self, session_factory):
        with patch(_PATCH, session_factory):
            items = CurrenciesCRUD().list_currencies()
        assert items == []


class TestUpdateCurrency:

    def test_update_name(self, session_factory):
        with patch(_PATCH, session_factory):
            crud = CurrenciesCRUD()
            c = crud.add_currency(code="AAA", name_ar="قديم", name_en="Old", name_tr="Eski")
            updated = crud.update_currency(c.id, {"name_en": "Updated"})
        assert updated.name_en == "Updated"

    def test_update_symbol(self, session_factory):
        with patch(_PATCH, session_factory):
            crud = CurrenciesCRUD()
            c = crud.add_currency(code="BBB", name_ar="ب", name_en="B", name_tr="B")
            updated = crud.update_currency(c.id, {"symbol": "₿"})
        assert updated.symbol == "₿"

    def test_update_nonexistent_returns_none(self, session_factory):
        with patch(_PATCH, session_factory):
            assert CurrenciesCRUD().update_currency(99999, {"name_en": "X"}) is None


class TestDeleteCurrency:

    def test_delete_existing(self, session_factory):
        with patch(_PATCH, session_factory):
            crud = CurrenciesCRUD()
            c = crud.add_currency(code="DEL", name_ar="حذف", name_en="Delete", name_tr="Sil")
            assert crud.delete_currency(c.id) is True
            assert crud.get_currency(c.id) is None

    def test_delete_nonexistent_returns_false(self, session_factory):
        with patch(_PATCH, session_factory):
            assert CurrenciesCRUD().delete_currency(99999) is False
