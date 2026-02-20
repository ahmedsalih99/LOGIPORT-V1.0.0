# -*- coding: utf-8 -*-
"""
tests/test_users_crud.py
==========================
Integration tests for UsersCRUD using in-memory SQLite.
Qt is mocked at sys.modules level via conftest.
"""
import sys, os
from unittest.mock import MagicMock, patch

# ── Mock Qt BEFORE importing anything that touches core ────────────────────
for _mod in [
    "PySide6", "PySide6.QtCore", "PySide6.QtWidgets", "PySide6.QtGui",
    "PySide6.QtPrintSupport", "PySide6.QtNetwork", "PySide6.QtSvg",
]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

# Make Qt signals/slots no-ops
sys.modules["PySide6.QtCore"].Signal = MagicMock(return_value=MagicMock())
sys.modules["PySide6.QtCore"].QObject = object

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from database.crud.users_crud import UsersCRUD

_PATCH = "database.crud.users_crud.get_session_local"


def _make_role(db_session):
    from database.models import Role
    role = Role(name="admin_test", label_ar="مدير", label_en="Admin")
    db_session.add(role)
    db_session.flush()
    return role


# ── add_user ─────────────────────────────────────────────────────────────────

class TestAddUser:

    def test_add_basic(self, session_factory, db_session):
        role = _make_role(db_session)
        with patch(_PATCH, session_factory):
            user = UsersCRUD().add_user(username="ahmad", password="Secret123!", full_name="Ahmad Test", role_id=role.id)
        assert user.id is not None
        assert user.username == "ahmad"

    def test_password_is_hashed(self, session_factory, db_session):
        role = _make_role(db_session)
        with patch(_PATCH, session_factory):
            user = UsersCRUD().add_user(username="bob", password="plainpass", full_name="Bob Test", role_id=role.id)
        assert user.password != "plainpass"
        assert user.password.startswith("$2b$")

    def test_new_user_is_active(self, session_factory, db_session):
        role = _make_role(db_session)
        with patch(_PATCH, session_factory):
            user = UsersCRUD().add_user(username="active_u", password="pw", full_name="Active User", role_id=role.id)
        assert user.is_active is True

    def test_with_full_name(self, session_factory, db_session):
        role = _make_role(db_session)
        with patch(_PATCH, session_factory):
            user = UsersCRUD().add_user(
                username="sara", password="pw", role_id=role.id, full_name="Sara Ahmad"
            )
        assert user.full_name == "Sara Ahmad"

    def test_duplicate_username_raises(self, session_factory, db_session):
        role = _make_role(db_session)
        with patch(_PATCH, session_factory):
            crud = UsersCRUD()
            crud.add_user(username="dup", password="pw", full_name="Dup User", role_id=role.id)
            with pytest.raises(Exception):
                crud.add_user(username="dup", password="pw2", full_name="Dup User2", role_id=role.id)


# ── authenticate ─────────────────────────────────────────────────────────────

class TestAuthenticate:

    def test_correct_credentials(self, session_factory, db_session):
        role = _make_role(db_session)
        with patch(_PATCH, session_factory):
            crud = UsersCRUD()
            crud.add_user(username="login_u", password="MyPass123", full_name="Login User", role_id=role.id)
            result = crud.authenticate("login_u", "MyPass123")
        assert result is not None
        assert result.username == "login_u"

    def test_wrong_password_returns_none(self, session_factory, db_session):
        role = _make_role(db_session)
        with patch(_PATCH, session_factory):
            crud = UsersCRUD()
            crud.add_user(username="wpw", password="correct", full_name="Wrong PW", role_id=role.id)
            assert crud.authenticate("wpw", "wrong") is None

    def test_unknown_user_returns_none(self, session_factory):
        with patch(_PATCH, session_factory):
            assert UsersCRUD().authenticate("nobody", "pw") is None

    def test_inactive_user_cannot_authenticate(self, session_factory, db_session):
        role = _make_role(db_session)
        with patch(_PATCH, session_factory):
            crud = UsersCRUD()
            user = crud.add_user(username="inactive_u", password="pw123", full_name="Inactive", role_id=role.id)
            crud.toggle_active(user.id)
            assert crud.authenticate("inactive_u", "pw123") is None


# ── get / lookup ──────────────────────────────────────────────────────────────

class TestGetUser:

    def test_get_by_id(self, session_factory, db_session):
        role = _make_role(db_session)
        with patch(_PATCH, session_factory):
            crud = UsersCRUD()
            user = crud.add_user(username="getbyid", password="pw", full_name="Get By ID", role_id=role.id)
            found = crud.get_by_id(user.id)
        assert found is not None
        assert found.username == "getbyid"

    def test_get_by_id_missing_returns_none(self, session_factory):
        with patch(_PATCH, session_factory):
            assert UsersCRUD().get_by_id(99999) is None

    def test_get_by_username(self, session_factory, db_session):
        role = _make_role(db_session)
        with patch(_PATCH, session_factory):
            crud = UsersCRUD()
            crud.add_user(username="byname", password="pw", full_name="By Name", role_id=role.id)
            found = crud.get_by_username("byname")
        assert found is not None

    def test_get_by_username_missing_returns_none(self, session_factory):
        with patch(_PATCH, session_factory):
            assert UsersCRUD().get_by_username("ghost_user") is None


# ── update_user ───────────────────────────────────────────────────────────────

class TestUpdateUser:

    def test_update_full_name(self, session_factory, db_session):
        role = _make_role(db_session)
        with patch(_PATCH, session_factory):
            crud = UsersCRUD()
            user = crud.add_user(username="upd_u", password="pw", full_name="Update User", role_id=role.id)
            updated = crud.update_user(user.id, {"full_name": "Updated Name"})
        assert updated.full_name == "Updated Name"

    def test_update_password_rehashes(self, session_factory, db_session):
        role = _make_role(db_session)
        with patch(_PATCH, session_factory):
            crud = UsersCRUD()
            user = crud.add_user(username="pw_upd", password="oldpass", full_name="PW Update", role_id=role.id)
            old_hash = user.password
            updated = crud.update_user(user.id, {"password": "newpass"})
        assert updated.password != old_hash
        assert UsersCRUD._check_password("newpass", updated.password)

    def test_update_nonexistent_returns_none(self, session_factory):
        with patch(_PATCH, session_factory):
            assert UsersCRUD().update_user(99999, {"full_name": "Ghost"}) is None


# ── delete & toggle ───────────────────────────────────────────────────────────

class TestDeleteAndToggle:

    def test_delete_existing(self, session_factory, db_session):
        role = _make_role(db_session)
        with patch(_PATCH, session_factory):
            crud = UsersCRUD()
            user = crud.add_user(username="to_del", password="pw", full_name="To Delete", role_id=role.id)
            assert crud.delete_user(user.id) is True
            assert crud.get_by_id(user.id) is None

    def test_delete_nonexistent_returns_false(self, session_factory):
        with patch(_PATCH, session_factory):
            assert UsersCRUD().delete_user(99999) is False

    def test_toggle_deactivates(self, session_factory, db_session):
        role = _make_role(db_session)
        with patch(_PATCH, session_factory):
            crud = UsersCRUD()
            user = crud.add_user(username="tog1", password="pw", full_name="Toggle 1", role_id=role.id)
            toggled = crud.toggle_active(user.id)
        assert toggled.is_active is False

    def test_toggle_reactivates(self, session_factory, db_session):
        role = _make_role(db_session)
        with patch(_PATCH, session_factory):
            crud = UsersCRUD()
            user = crud.add_user(username="tog2", password="pw", full_name="Toggle 2", role_id=role.id)
            crud.toggle_active(user.id)   # → inactive
            back = crud.toggle_active(user.id)  # → active
        assert back.is_active is True

    def test_toggle_nonexistent_returns_none(self, session_factory):
        with patch(_PATCH, session_factory):
            assert UsersCRUD().toggle_active(99999) is None
