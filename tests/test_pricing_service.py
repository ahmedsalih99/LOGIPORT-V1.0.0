# -*- coding: utf-8 -*-
"""
tests/test_pricing_service.py
================================
Tests for PricingService.find_best_price():
  - exact match found
  - fallback (ignore delivery_method) when no exact match
  - returns None when no match at all
"""
import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from services.pricing_service import PricingService

_PATCH = "database.crud.pricing_crud.get_session_local"
_PATCH_SESSION = "database.crud.pricing_crud.PricingCRUD._SessionLocal"


def _seed_pricing(db_session, make_company, make_material, make_currency, price="100.00",
                  delivery_method_id=None):
    """Helper: insert a Pricing row and return its key IDs."""
    from database.models.pricing_type import PricingType
    from database.models.pricing import Pricing

    seller = make_company(name_en="Seller")
    buyer  = make_company(name_en="Buyer")
    mat    = make_material(name_en="Steel")
    cur    = make_currency(code="US")

    pt = PricingType(name_ar="فوب", name_en="FOB", name_tr="FOB", code="FOB_S")
    db_session.add(pt)
    db_session.flush()

    p = Pricing(
        seller_company_id=seller.id,
        buyer_company_id=buyer.id,
        material_id=mat.id,
        pricing_type_id=pt.id,
        currency_id=cur.id,
        delivery_method_id=delivery_method_id,
        price=Decimal(price),
        is_active=True,
    )
    db_session.add(p)
    db_session.flush()

    return {
        "seller": seller, "buyer": buyer, "mat": mat, "cur": cur, "pt": pt, "pricing": p
    }


class TestFindBestPrice:

    def test_exact_match_returned(self, session_factory, db_session, make_company, make_material, make_currency):
        seed = _seed_pricing(db_session, make_company, make_material, make_currency)
        with patch(_PATCH, session_factory), \
             patch(_PATCH_SESSION, return_value=session_factory):
            result = PricingService().find_best_price(
                seller_company_id=seed["seller"].id,
                buyer_company_id=seed["buyer"].id,
                material_id=seed["mat"].id,
                pricing_type_id=seed["pt"].id,
                currency_id=seed["cur"].id,
            )
        assert result is not None
        assert float(result.price) == pytest.approx(100.0)

    def test_returns_none_when_no_match(self, session_factory):
        with patch(_PATCH, session_factory), \
             patch(_PATCH_SESSION, return_value=session_factory):
            result = PricingService().find_best_price(
                seller_company_id=9999,
                buyer_company_id=9998,
                material_id=9997,
                pricing_type_id=9996,
                currency_id=9995,
            )
        assert result is None

    def test_mock_exact_match(self):
        """Unit test using mock — no DB needed."""
        mock_pricing = MagicMock()
        mock_pricing.price = Decimal("250.00")

        mock_crud = MagicMock()
        mock_crud.list.return_value = [mock_pricing]

        svc = PricingService()
        svc.crud = mock_crud

        result = svc.find_best_price(
            seller_company_id=1, buyer_company_id=2,
            material_id=3, pricing_type_id=4, currency_id=5,
        )
        assert result is mock_pricing
        assert mock_crud.list.call_count == 1

    def test_mock_fallback_when_delivery_method_not_found(self):
        """Fallback: if no match with delivery_method, retries without it."""
        fallback_pricing = MagicMock()
        fallback_pricing.price = Decimal("180.00")

        mock_crud = MagicMock()
        # First call (with delivery_method) → empty; second call (without) → match
        mock_crud.list.side_effect = [[], [fallback_pricing]]

        svc = PricingService()
        svc.crud = mock_crud

        result = svc.find_best_price(
            seller_company_id=1, buyer_company_id=2,
            material_id=3, pricing_type_id=4, currency_id=5,
            delivery_method_id=7,
        )
        assert result is fallback_pricing
        assert mock_crud.list.call_count == 2

    def test_mock_no_fallback_without_delivery_method(self):
        """If no delivery_method provided and no match, returns None without second call."""
        mock_crud = MagicMock()
        mock_crud.list.return_value = []

        svc = PricingService()
        svc.crud = mock_crud

        result = svc.find_best_price(
            seller_company_id=1, buyer_company_id=2,
            material_id=3, pricing_type_id=4, currency_id=5,
            delivery_method_id=None,
        )
        assert result is None
        assert mock_crud.list.call_count == 1  # no second call

    def test_mock_returns_first_when_multiple(self):
        """Returns the first item when multiple prices match."""
        p1 = MagicMock(price=Decimal("100"))
        p2 = MagicMock(price=Decimal("200"))
        mock_crud = MagicMock()
        mock_crud.list.return_value = [p1, p2]

        svc = PricingService()
        svc.crud = mock_crud

        result = svc.find_best_price(
            seller_company_id=1, buyer_company_id=2,
            material_id=3, pricing_type_id=4, currency_id=5,
        )
        assert result is p1
