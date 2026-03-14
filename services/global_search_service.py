"""
services/global_search_service.py
===================================
Global Search — يبحث في كل الكيانات الرئيسية بـ query واحد.

الكيانات: معاملات، عملاء، شركات، مواد، وثائق، إدخالات، كونتينرات
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List
import logging

logger = logging.getLogger(__name__)

LIMIT_PER_ENTITY = 8   # أقصى نتائج لكل كيان


@dataclass
class SearchResult:
    entity:      str
    entity_key:  str
    record_id:   int
    title:       str
    subtitle:    str = ""
    icon:        str = "📄"
    badge:       str = ""


def search_all(query: str, lang: str = "ar") -> List[SearchResult]:
    if not query or len(query.strip()) < 1:
        return []

    q = query.strip()
    results: List[SearchResult] = []

    try:
        from database.models.base import get_session_local
        with get_session_local()() as s:
            results += _search_transactions(s, q, lang)
            results += _search_containers(s, q, lang)
            results += _search_clients(s, q, lang)
            results += _search_companies(s, q, lang)
            results += _search_materials(s, q, lang)
            results += _search_entries(s, q, lang)
            results += _search_documents(s, q, lang)
    except Exception as e:
        logger.error(f"Global search error: {e}", exc_info=True)

    return results


def _name(obj, lang: str) -> str:
    for attr in (f"name_{lang}", "name_ar", "name_en", "name_tr", "name"):
        v = getattr(obj, attr, None)
        if v:
            return str(v)
    return str(getattr(obj, "id", ""))


def _like(col, q: str):
    return col.ilike(f"%{q}%")


def _search_transactions(s, q: str, lang: str) -> List[SearchResult]:
    try:
        from database.models.transaction import Transaction
        from sqlalchemy import or_
        rows = (
            s.query(Transaction)
            .filter(or_(
                _like(Transaction.transaction_no, q),
                _like(Transaction.transport_ref, q),
                _like(Transaction.notes, q),
            ))
            .limit(LIMIT_PER_ENTITY).all()
        )
        out = []
        for r in rows:
            status = getattr(r, "status", "active") or "active"
            status_icons = {"draft": "📝", "active": "🟢", "closed": "🔴", "archived": "📦"}
            trx_type = getattr(r, "transaction_type", "") or ""
            type_icons = {"export": "📤", "import": "📥", "transit": "🔄"}
            out.append(SearchResult(
                entity="transaction",
                entity_key="transactions",
                record_id=r.id,
                title=str(r.transaction_no or r.id),
                subtitle=f"{str(r.transaction_date or '')}  •  {trx_type}",
                icon=type_icons.get(trx_type, "📦"),
                badge=status_icons.get(status, ""),
            ))
        return out
    except Exception as e:
        logger.debug(f"Transaction search error: {e}")
        return []


def _search_containers(s, q: str, lang: str) -> List[SearchResult]:
    try:
        from database.models.container_tracking import ContainerTracking
        from sqlalchemy import or_
        rows = (
            s.query(ContainerTracking)
            .filter(or_(
                _like(ContainerTracking.container_no, q),
                _like(ContainerTracking.bl_number, q),
                _like(ContainerTracking.booking_no, q),
                _like(ContainerTracking.vessel_name, q),
                _like(ContainerTracking.shipping_line, q),
                _like(ContainerTracking.port_of_loading, q),
                _like(ContainerTracking.port_of_discharge, q),
                _like(ContainerTracking.notes, q),
            ))
            .limit(LIMIT_PER_ENTITY).all()
        )
        status_icons = {
            "booked": "📋", "loaded": "📦", "in_transit": "🚢",
            "arrived": "⚓", "customs": "🏛️", "delivered": "✅", "hold": "⚠️",
        }
        out = []
        for r in rows:
            status = r.status or "booked"
            parts = []
            if r.bl_number:
                parts.append(f"BL: {r.bl_number}")
            if r.eta:
                parts.append(f"ETA: {r.eta}")
            if r.shipping_line:
                parts.append(r.shipping_line)
            out.append(SearchResult(
                entity="container",
                entity_key="container_tracking",
                record_id=r.id,
                title=str(r.container_no or r.id),
                subtitle="  •  ".join(parts),
                icon="🚢",
                badge=status_icons.get(status, ""),
            ))
        return out
    except Exception as e:
        logger.debug(f"Container search error: {e}")
        return []


def _search_clients(s, q: str, lang: str) -> List[SearchResult]:
    try:
        from database.models.client import Client
        from sqlalchemy import or_
        rows = (
            s.query(Client)
            .filter(or_(
                _like(Client.name_ar, q),
                _like(Client.name_en, q),
                _like(Client.name_tr, q),
                _like(Client.code, q),
                _like(Client.phone, q),
                _like(Client.email, q),
            ))
            .limit(LIMIT_PER_ENTITY).all()
        )
        return [SearchResult(
            entity="client", entity_key="clients", record_id=r.id,
            title=_name(r, lang),
            subtitle=str(getattr(r, "phone", "") or getattr(r, "email", "") or ""),
            icon="👤",
        ) for r in rows]
    except Exception as e:
        logger.debug(f"Client search error: {e}")
        return []


def _search_companies(s, q: str, lang: str) -> List[SearchResult]:
    try:
        from database.models.company import Company
        from sqlalchemy import or_
        rows = (
            s.query(Company)
            .filter(or_(
                _like(Company.name_ar, q),
                _like(Company.name_en, q),
                _like(Company.name_tr, q),
                _like(Company.tax_id, q),
                _like(Company.phone, q),
            ))
            .limit(LIMIT_PER_ENTITY).all()
        )
        return [SearchResult(
            entity="company", entity_key="companies", record_id=r.id,
            title=_name(r, lang),
            subtitle=str(getattr(r, "city", "") or ""),
            icon="🏢",
        ) for r in rows]
    except Exception as e:
        logger.debug(f"Company search error: {e}")
        return []


def _search_materials(s, q: str, lang: str) -> List[SearchResult]:
    try:
        from database.models.material import Material
        from sqlalchemy import or_
        rows = (
            s.query(Material)
            .filter(or_(
                _like(Material.name_ar, q),
                _like(Material.name_en, q),
                _like(Material.name_tr, q),
                _like(Material.code, q),
            ))
            .limit(LIMIT_PER_ENTITY).all()
        )
        return [SearchResult(
            entity="material", entity_key="materials", record_id=r.id,
            title=_name(r, lang),
            subtitle=str(getattr(r, "code", "") or ""),
            icon="📦",
        ) for r in rows]
    except Exception as e:
        logger.debug(f"Material search error: {e}")
        return []


def _search_entries(s, q: str, lang: str) -> List[SearchResult]:
    try:
        from database.models.entry import Entry
        from sqlalchemy import or_
        rows = (
            s.query(Entry)
            .filter(or_(
                _like(Entry.entry_no, q),
                _like(Entry.transport_ref, q),
                _like(Entry.seal_no, q),
            ))
            .limit(LIMIT_PER_ENTITY).all()
        )
        return [SearchResult(
            entity="entry", entity_key="entries", record_id=r.id,
            title=str(getattr(r, "entry_no", "") or r.id),
            subtitle=str(getattr(r, "entry_date", "") or ""),
            icon="📋",
        ) for r in rows]
    except Exception as e:
        logger.debug(f"Entry search error: {e}")
        return []


def _search_documents(s, q: str, lang: str) -> List[SearchResult]:
    try:
        from database.models.document import Document
        from sqlalchemy import or_
        rows = (
            s.query(Document)
            .filter(or_(_like(Document.document_no, q)))
            .limit(LIMIT_PER_ENTITY).all()
        )
        return [SearchResult(
            entity="document", entity_key="documents", record_id=r.id,
            title=str(getattr(r, "document_no", "") or r.id),
            subtitle=str(getattr(r, "document_type", "") or ""),
            icon="📄",
        ) for r in rows]
    except Exception as e:
        logger.debug(f"Document search error: {e}")
        return []
