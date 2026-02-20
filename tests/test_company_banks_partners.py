# -*- coding: utf-8 -*-
"""
tests/test_company_banks_partners.py
======================================
Tests for CompanyBanksCRUD and CompanyPartnersCRUD.
"""
import pytest
from unittest.mock import patch
from database.crud.companies_crud import CompanyBanksCRUD, CompanyPartnersCRUD


class TestCompanyBanksCRUD:

    @staticmethod
    def _patch(sf):
        return patch("database.crud.companies_crud.get_session_local", sf)

    def test_add_bank_basic(self, session_factory, make_company):
        company = make_company()
        with self._patch(session_factory):
            crud = CompanyBanksCRUD()
            bank = crud.add_bank(company.id, {
                "bank_name": "Test Bank",
                "iban": "TR123456789012",
                "swift_bic": "TESTTRXY",
            })
        assert bank.id is not None
        assert bank.bank_name == "TEST BANK"   # uppercased
        assert bank.iban == "TR123456789012"    # uppercased

    def test_add_bank_primary(self, session_factory, make_company):
        company = make_company()
        with self._patch(session_factory):
            crud = CompanyBanksCRUD()
            bank = crud.add_bank(company.id, {"bank_name": "Primary", "is_primary": True})
        assert bank.is_primary is True

    def test_add_two_banks_only_one_primary(self, session_factory, make_company):
        company = make_company()
        with self._patch(session_factory):
            crud = CompanyBanksCRUD()
            b1 = crud.add_bank(company.id, {"bank_name": "First",  "is_primary": True})
            b2 = crud.add_bank(company.id, {"bank_name": "Second", "is_primary": True})
            banks = crud.list_banks(company.id)
        primaries = [b for b in banks if b.is_primary]
        assert len(primaries) == 1
        assert primaries[0].id == b2.id

    def test_list_banks_empty(self, session_factory, make_company):
        company = make_company()
        with self._patch(session_factory):
            result = CompanyBanksCRUD().list_banks(company.id)
        assert result == []

    def test_list_banks_primary_first(self, session_factory, make_company):
        company = make_company()
        with self._patch(session_factory):
            crud = CompanyBanksCRUD()
            crud.add_bank(company.id, {"bank_name": "Regular"})
            crud.add_bank(company.id, {"bank_name": "Primary", "is_primary": True})
            banks = crud.list_banks(company.id)
        assert banks[0].is_primary is True

    def test_update_bank(self, session_factory, make_company):
        company = make_company()
        with self._patch(session_factory):
            crud = CompanyBanksCRUD()
            bank = crud.add_bank(company.id, {"bank_name": "Old"})
            updated = crud.update_bank(bank.id, {"bank_name": "New Bank"})
        assert updated is not None
        assert updated.bank_name == "NEW BANK"

    def test_update_bank_nonexistent_returns_none(self, session_factory):
        with self._patch(session_factory):
            result = CompanyBanksCRUD().update_bank(99999, {"bank_name": "Ghost"})
        assert result is None

    def test_delete_bank(self, session_factory, make_company):
        company = make_company()
        with self._patch(session_factory):
            crud = CompanyBanksCRUD()
            bank = crud.add_bank(company.id, {"bank_name": "ToDelete"})
            result = crud.delete_bank(bank.id)
            remaining = crud.list_banks(company.id)
        assert result is True
        assert len(remaining) == 0

    def test_delete_nonexistent_returns_false(self, session_factory):
        with self._patch(session_factory):
            assert CompanyBanksCRUD().delete_bank(99999) is False


class TestCompanyPartnersCRUD:

    @staticmethod
    def _patch(sf):
        return patch("database.crud.companies_crud.get_session_local", sf)

    def test_add_partner(self, session_factory, make_company, make_client):
        company = make_company()
        client  = make_client()
        with self._patch(session_factory):
            crud = CompanyPartnersCRUD()
            link = crud.add_partner(company.id, client.id, partner_role="CEO", share_percent=51.0)
        assert link.id is not None
        assert link.partner_role == "CEO"
        assert link.share_percent == 51.0
        assert link.is_active is True

    def test_list_partners_empty(self, session_factory, make_company):
        company = make_company()
        with self._patch(session_factory):
            result = CompanyPartnersCRUD().list_partners(company.id)
        assert result == []

    def test_list_partners_returns_active_only(self, session_factory, make_company, make_client):
        company = make_company()
        c1 = make_client(); c2 = make_client()
        with self._patch(session_factory):
            crud = CompanyPartnersCRUD()
            p1 = crud.add_partner(company.id, c1.id)
            p2 = crud.add_partner(company.id, c2.id)
            crud.update_partner(p2.id, {"is_active": False})
            result = crud.list_partners(company.id)
        assert len(result) == 1
        assert result[0].id == p1.id

    def test_update_partner(self, session_factory, make_company, make_client):
        company = make_company(); client = make_client()
        with self._patch(session_factory):
            crud = CompanyPartnersCRUD()
            link = crud.add_partner(company.id, client.id)
            updated = crud.update_partner(link.id, {"partner_role": "CFO", "share_percent": 25.0})
        assert updated is not None
        assert updated.partner_role == "CFO"

    def test_update_partner_nonexistent_returns_none(self, session_factory):
        with self._patch(session_factory):
            assert CompanyPartnersCRUD().update_partner(99999, {"partner_role": "X"}) is None

    def test_delete_partner(self, session_factory, make_company, make_client):
        company = make_company(); client = make_client()
        with self._patch(session_factory):
            crud = CompanyPartnersCRUD()
            link = crud.add_partner(company.id, client.id)
            result = crud.delete_partner(link.id)
            remaining = crud.list_partners(company.id)
        assert result is True
        assert len(remaining) == 0
