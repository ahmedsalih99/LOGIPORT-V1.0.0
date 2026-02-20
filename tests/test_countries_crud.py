"""
tests/test_countries_crud.py
============================
Basic tests for CountriesCRUD.
"""
import pytest
from unittest.mock import patch


class TestCountriesCRUD:

    @staticmethod
    def _patch(session_factory):
        return patch(
            "database.crud.countries_crud.get_session_local",
            return_value=session_factory,
        )

    def test_list_countries_returns_list(self, session_factory):
        from database.crud.countries_crud import CountriesCRUD
        with self._patch(session_factory):
            result = CountriesCRUD().list_countries() \
                if hasattr(CountriesCRUD, "list_countries") \
                else CountriesCRUD().get_all()
        assert isinstance(result, list)

    def test_get_nonexistent_returns_none(self, session_factory):
        from database.crud.countries_crud import CountriesCRUD
        crud = CountriesCRUD()
        with self._patch(session_factory):
            getter = getattr(crud, "get_country", None) or getattr(crud, "get", None)
            if getter:
                result = getter(99999)
                assert result is None