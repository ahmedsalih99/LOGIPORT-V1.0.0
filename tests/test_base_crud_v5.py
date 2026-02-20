# -*- coding: utf-8 -*-
"""
tests/test_base_crud_v5.py
============================
Tests for BaseCRUD_V5 core behaviours via CountriesCRUD (lightweight model).
Covers: add, get, get_all, update, delete, filter_by, count, stamping.
"""
import pytest
from unittest.mock import patch
from database.crud.countries_crud import CountriesCRUD

_PATCH = "database.crud.countries_crud.get_session_local"

_counter = [0]

def _add(crud):
    _counter[0] += 1
    n = _counter[0]
    return crud.add_country(
        name_ar=f"بلد {n}", name_en=f"Country {n}",
        name_tr=f"Ülke {n}", code=f"X{n:04d}"
    )

def _make_user(db_session, suffix=""):
    from database.models import Role, User
    from utils.auth_utils import hash_password
    role = Role(name=f"r_{suffix}", label_ar="ت", label_en="T")
    db_session.add(role)
    db_session.flush()
    user = User(username=f"u_{suffix}", password=hash_password("pw"),
                full_name="Test", role_id=role.id, is_active=True)
    db_session.add(user)
    db_session.flush()
    return user


# ── add ───────────────────────────────────────────────────────────────────────

class TestAdd:

    def test_returns_object_with_id(self, session_factory):
        with patch(_PATCH, session_factory):
            c = _add(CountriesCRUD())
        assert c.id is not None

    def test_persists_to_db(self, session_factory):
        with patch(_PATCH, session_factory):
            crud = CountriesCRUD()
            c = _add(crud)
            found = crud.get_country(c.id)
        assert found is not None

    def test_without_user_created_by_is_null(self, session_factory):
        with patch(_PATCH, session_factory):
            c = _add(CountriesCRUD())
        assert c.created_by is None

    def test_with_user_stamps_created_by(self, session_factory, db_session):
        user = _make_user(db_session, "add_stamp")
        with patch(_PATCH, session_factory):
            c = CountriesCRUD().add_country(
                name_ar="اختبار", name_en="Stamp Test", name_tr="Test",
                code="STMP1", user_id=user.id
            )
        assert c is not None
        assert c.created_by == user.id

    def test_multiple_adds_get_unique_ids(self, session_factory):
        with patch(_PATCH, session_factory):
            crud = CountriesCRUD()
            c1 = _add(crud)
            c2 = _add(crud)
        assert c1.id != c2.id


# ── get ───────────────────────────────────────────────────────────────────────

class TestGet:

    def test_get_existing(self, session_factory):
        with patch(_PATCH, session_factory):
            crud = CountriesCRUD()
            c = _add(crud)
            found = crud.get_country(c.id)
        assert found is not None
        assert found.id == c.id

    def test_get_nonexistent_returns_none(self, session_factory):
        with patch(_PATCH, session_factory):
            assert CountriesCRUD().get_country(99999) is None


# ── get_all ───────────────────────────────────────────────────────────────────

class TestGetAll:

    def test_empty_initially(self, session_factory):
        with patch(_PATCH, session_factory):
            assert CountriesCRUD().list_countries() == []

    def test_includes_added_items(self, session_factory):
        with patch(_PATCH, session_factory):
            crud = CountriesCRUD()
            _add(crud)
            _add(crud)
            items = crud.list_countries()
        assert len(items) >= 2


# ── update ────────────────────────────────────────────────────────────────────

class TestUpdate:

    def test_update_field(self, session_factory):
        with patch(_PATCH, session_factory):
            crud = CountriesCRUD()
            c = _add(crud)
            updated = crud.update_country(c.id, {"name_en": "CHANGED"})
        assert updated is not None
        assert updated.name_en == "CHANGED"

    def test_update_nonexistent_returns_none(self, session_factory):
        with patch(_PATCH, session_factory):
            assert CountriesCRUD().update_country(99999, {"name_en": "X"}) is None

    def test_update_with_user_stamps_updated_by(self, session_factory, db_session):
        user = _make_user(db_session, "upd_stamp")
        with patch(_PATCH, session_factory):
            crud = CountriesCRUD()
            c = _add(crud)
            updated = crud.update_country(c.id, {"name_en": "UPD"}, user_id=user.id)
        assert updated is not None
        assert updated.updated_by == user.id

    def test_update_does_not_corrupt_other_fields(self, session_factory):
        with patch(_PATCH, session_factory):
            crud = CountriesCRUD()
            c = crud.add_country(name_ar="عربي", name_en="Arabic Country",
                                  name_tr="Arapça", code="ARBC")
            crud.update_country(c.id, {"name_en": "ARABIC COUNTRY"})
            found = crud.get_country(c.id)
        assert found.name_ar == "عربي"

    def test_update_empty_payload_returns_object(self, session_factory):
        with patch(_PATCH, session_factory):
            crud = CountriesCRUD()
            c = _add(crud)
            result = crud.update_country(c.id, {})
        assert result is not None


# ── delete ────────────────────────────────────────────────────────────────────

class TestDelete:

    def test_delete_existing_returns_true(self, session_factory):
        with patch(_PATCH, session_factory):
            crud = CountriesCRUD()
            c = _add(crud)
            assert crud.delete_country(c.id) is True

    def test_delete_removes_record(self, session_factory):
        with patch(_PATCH, session_factory):
            crud = CountriesCRUD()
            c = _add(crud)
            crud.delete_country(c.id)
            assert crud.get_country(c.id) is None

    def test_delete_nonexistent_returns_false(self, session_factory):
        with patch(_PATCH, session_factory):
            assert CountriesCRUD().delete_country(99999) is False


# ── filter_by & count ─────────────────────────────────────────────────────────

class TestFilterAndCount:

    def test_count_zero_initially(self, session_factory):
        with patch(_PATCH, session_factory):
            assert CountriesCRUD().count() == 0

    def test_count_reflects_adds(self, session_factory):
        with patch(_PATCH, session_factory):
            crud = CountriesCRUD()
            _add(crud)
            _add(crud)
            _add(crud)
            assert crud.count() == 3

    def test_count_after_delete(self, session_factory):
        with patch(_PATCH, session_factory):
            crud = CountriesCRUD()
            c = _add(crud)
            _add(crud)
            crud.delete_country(c.id)
            assert crud.count() == 1

    def test_filter_by_specific_code(self, session_factory):
        with patch(_PATCH, session_factory):
            crud = CountriesCRUD()
            crud.add_country(name_ar="تركيا", name_en="Turkey", name_tr="Türkiye", code="TRKF")
            crud.add_country(name_ar="ألمانيا", name_en="Germany", name_tr="Almanya", code="DEUF")
            results = crud.filter_by(code="TRKF")
        assert len(results) == 1
        assert results[0].code == "TRKF"

    def test_filter_no_match_returns_empty(self, session_factory):
        with patch(_PATCH, session_factory):
            assert CountriesCRUD().filter_by(code="ZZZ_NONE") == []

    def test_count_matches_list_length(self, session_factory):
        with patch(_PATCH, session_factory):
            crud = CountriesCRUD()
            for _ in range(4):
                _add(crud)
            assert crud.count() == len(crud.list_countries()) == 4
