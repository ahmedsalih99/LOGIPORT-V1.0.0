# -*- coding: utf-8 -*-
"""
tests/test_pricing_crud.py
============================
Tests for PricingCRUD — validation, add, list, update, delete, duplicate check.
"""
import pytest
from decimal import Decimal
from unittest.mock import patch
from database.crud.pricing_crud import PricingCRUD

_PATCH = "database.crud.pricing_crud.get_session_local"
_PATCH_SESSION = "database.crud.pricing_crud.PricingCRUD._SessionLocal"


def _setup(db_session, make_company, make_material, make_currency):
    """Create the minimum seed data needed for a Pricing record."""
    from database.models.pricing_type import PricingType

    seller = make_company(name_en="Seller Co")
    buyer  = make_company(name_en="Buyer Co")
    mat    = make_material(name_en="Iron")
    cur    = make_currency(code="US")

    pt = PricingType(name_ar="فوب", name_en="FOB", name_tr="FOB", code="FOB")
    db_session.add(pt)
    db_session.flush()

    return {
        "seller_company_id": seller.id,
        "buyer_company_id":  buyer.id,
        "material_id":       mat.id,
        "pricing_type_id":   pt.id,
        "currency_id":       cur.id,
        "price":             "150.00",
    }


# ── validation ────────────────────────────────────────────────────────────────

class TestValidation:

    def test_missing_seller_raises(self, session_factory, db_session, make_company, make_material, make_currency):
        data = _setup(db_session, make_company, make_material, make_currency)
        del data["seller_company_id"]
        with patch(_PATCH, session_factory), \
             patch(_PATCH_SESSION, return_value=session_factory):
            with pytest.raises(ValueError, match="seller_company_id"):
                PricingCRUD().add_pricing(data)

    def test_missing_price_raises(self, session_factory, db_session, make_company, make_material, make_currency):
        data = _setup(db_session, make_company, make_material, make_currency)
        del data["price"]
        with patch(_PATCH, session_factory), \
             patch(_PATCH_SESSION, return_value=session_factory):
            with pytest.raises(ValueError):
                PricingCRUD().add_pricing(data)

    def test_zero_price_raises(self, session_factory, db_session, make_company, make_material, make_currency):
        data = _setup(db_session, make_company, make_material, make_currency)
        data["price"] = "0"
        with patch(_PATCH, session_factory), \
             patch(_PATCH_SESSION, return_value=session_factory):
            with pytest.raises(ValueError, match="positive"):
                PricingCRUD().add_pricing(data)

    def test_negative_price_raises(self, session_factory, db_session, make_company, make_material, make_currency):
        data = _setup(db_session, make_company, make_material, make_currency)
        data["price"] = "-10"
        with patch(_PATCH, session_factory), \
             patch(_PATCH_SESSION, return_value=session_factory):
            with pytest.raises(ValueError):
                PricingCRUD().add_pricing(data)


# ── add_pricing ───────────────────────────────────────────────────────────────

class TestAddPricing:

    def test_add_basic(self, session_factory, db_session, make_company, make_material, make_currency):
        data = _setup(db_session, make_company, make_material, make_currency)
        with patch(_PATCH, session_factory), \
             patch(_PATCH_SESSION, return_value=session_factory):
            p = PricingCRUD().add_pricing(data)
        assert p.id is not None
        assert Decimal(str(p.price)) == Decimal("150.00")

    def test_price_stored_as_decimal(self, session_factory, db_session, make_company, make_material, make_currency):
        data = _setup(db_session, make_company, make_material, make_currency)
        data["price"] = "99.99"
        with patch(_PATCH, session_factory), \
             patch(_PATCH_SESSION, return_value=session_factory):
            p = PricingCRUD().add_pricing(data)
        assert float(p.price) == pytest.approx(99.99)

    def test_duplicate_raises(self, session_factory, db_session, make_company, make_material, make_currency):
        data = _setup(db_session, make_company, make_material, make_currency)
        with patch(_PATCH, session_factory), \
             patch(_PATCH_SESSION, return_value=session_factory):
            crud = PricingCRUD()
            crud.add_pricing(data)
            with pytest.raises(Exception):   # ValueError or IntegrityError
                crud.add_pricing(dict(data))


# ── list / get ────────────────────────────────────────────────────────────────

class TestListPricing:

    def test_list_after_add(self, session_factory, db_session, make_company, make_material, make_currency):
        data = _setup(db_session, make_company, make_material, make_currency)
        with patch(_PATCH, session_factory), \
             patch(_PATCH_SESSION, return_value=session_factory):
            crud = PricingCRUD()
            crud.add_pricing(data)
            rows = crud.list()
        assert len(rows) >= 1

    def test_list_empty_initially(self, session_factory):
        with patch(_PATCH, session_factory), \
             patch(_PATCH_SESSION, return_value=session_factory):
            rows = PricingCRUD().list()
        assert rows == []


# ── update_pricing ────────────────────────────────────────────────────────────

class TestUpdatePricing:

    def test_update_price(self, session_factory, db_session, make_company, make_material, make_currency):
        data = _setup(db_session, make_company, make_material, make_currency)
        with patch(_PATCH, session_factory), \
             patch(_PATCH_SESSION, return_value=session_factory):
            crud = PricingCRUD()
            p = crud.add_pricing(data)
            updated = crud.update_pricing(p.id, {"price": "200.00"})
        assert updated is not None
        assert float(updated.price) == pytest.approx(200.00)

    def test_update_nonexistent_returns_none(self, session_factory):
        with patch(_PATCH, session_factory), \
             patch(_PATCH_SESSION, return_value=session_factory):
            result = PricingCRUD().update_pricing(99999, {"price": "100"})
        assert result is None


# ── delete_pricing ────────────────────────────────────────────────────────────

class TestDeletePricing:

    def test_delete_existing(self, session_factory, db_session, make_company, make_material, make_currency):
        data = _setup(db_session, make_company, make_material, make_currency)
        with patch(_PATCH, session_factory), \
             patch(_PATCH_SESSION, return_value=session_factory):
            crud = PricingCRUD()
            p = crud.add_pricing(data)
            assert crud.delete_pricing(p.id) is True

    def test_delete_nonexistent_returns_false(self, session_factory):
        with patch(_PATCH, session_factory), \
             patch(_PATCH_SESSION, return_value=session_factory):
            assert PricingCRUD().delete_pricing(99999) is False
