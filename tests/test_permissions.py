# -*- coding: utf-8 -*-
"""
tests/test_permissions.py
===========================
Tests for core/permissions.py — is_admin, has_perm, has_any_perm, has_all_perms.
Uses mock user objects — no DB or Qt needed.
"""
import sys, os
from unittest.mock import MagicMock, patch

# ── Qt Mock ──────────────────────────────────────────────────────────────────
for _m in ["PySide6","PySide6.QtCore","PySide6.QtWidgets","PySide6.QtGui",
           "PySide6.QtPrintSupport","PySide6.QtNetwork","PySide6.QtSvg"]:
    if _m not in sys.modules:
        sys.modules[_m] = MagicMock()
sys.modules["PySide6.QtCore"].Signal  = MagicMock(return_value=MagicMock())
sys.modules["PySide6.QtCore"].QObject = object

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from core.permissions import is_admin, has_perm, has_any_perm, has_all_perms


def _user(role_id=2, role_name=None):
    """Create a mock user object."""
    u = MagicMock()
    u.role_id = role_id
    if role_name:
        u.role = MagicMock()
        u.role.name = role_name
    else:
        u.role = None
    return u


# ── is_admin ──────────────────────────────────────────────────────────────────

class TestIsAdmin:

    def test_role_id_1_is_admin(self):
        assert is_admin(_user(role_id=1)) is True

    def test_role_id_2_not_admin(self):
        assert is_admin(_user(role_id=2)) is False

    def test_role_name_admin_is_admin(self):
        assert is_admin(_user(role_name="admin")) is True

    def test_role_name_Admin_uppercase_is_admin(self):
        assert is_admin(_user(role_name="Admin")) is True

    def test_role_name_ADMIN_uppercase_is_admin(self):
        assert is_admin(_user(role_name="ADMIN")) is True

    def test_role_name_viewer_not_admin(self):
        assert is_admin(_user(role_name="viewer")) is False

    def test_none_user_not_admin(self):
        assert is_admin(None) is False

    def test_dict_user_role_id_1(self):
        assert is_admin({"role_id": 1}) is True

    def test_dict_user_role_id_2(self):
        assert is_admin({"role_id": 2}) is False

    def test_dict_user_role_name_admin(self):
        assert is_admin({"role_id": 2, "role": "admin"}) is True

    def test_empty_dict_not_admin(self):
        assert is_admin({}) is False


# ── has_perm ──────────────────────────────────────────────────────────────────

class TestHasPerm:

    def test_admin_has_all_perms(self):
        admin = _user(role_id=1)
        # Admin short-circuits — no DB call needed
        assert has_perm(admin, "view_users") is True
        assert has_perm(admin, "delete_everything") is True

    def test_non_admin_delegates_to_permission_manager(self):
        user = _user(role_id=5)
        with patch("core.permissions.PermissionManager.has_permission", return_value=True) as m:
            result = has_perm(user, "view_clients")
        assert result is True
        m.assert_called_once_with(user, "view_clients")

    def test_non_admin_no_permission(self):
        user = _user(role_id=5)
        with patch("core.permissions.PermissionManager.has_permission", return_value=False):
            assert has_perm(user, "delete_client") is False

    def test_none_user_returns_false(self):
        assert has_perm(None, "view_users") is False


# ── has_any_perm ──────────────────────────────────────────────────────────────

class TestHasAnyPerm:

    def test_admin_has_any(self):
        admin = _user(role_id=1)
        assert has_any_perm(admin, ["view_x", "edit_y"]) is True

    def test_empty_codes_returns_false(self):
        assert has_any_perm(_user(), []) is False

    def test_none_user_returns_false(self):
        assert has_any_perm(None, ["view_x"]) is False

    def test_user_has_one_of_two(self):
        user = _user(role_id=3)
        with patch("core.permissions.PermissionManager.has_permission",
                   side_effect=lambda u, code: code == "view_clients"):
            result = has_any_perm(user, ["delete_client", "view_clients"])
        assert result is True

    def test_user_has_none(self):
        user = _user(role_id=3)
        with patch("core.permissions.PermissionManager.has_permission", return_value=False):
            assert has_any_perm(user, ["delete_all", "nuke_db"]) is False

    @pytest.mark.parametrize("codes", [
        ["view_clients"],
        ["view_clients", "edit_client"],
        ["a", "b", "c"],
    ])
    def test_admin_always_true_for_any_codes(self, codes):
        assert has_any_perm(_user(role_id=1), codes) is True


# ── has_all_perms ─────────────────────────────────────────────────────────────

class TestHasAllPerms:

    def test_admin_has_all(self):
        assert has_all_perms(_user(role_id=1), ["view_x", "edit_y", "delete_z"]) is True

    def test_empty_codes_returns_false(self):
        assert has_all_perms(_user(), []) is False

    def test_none_user_returns_false(self):
        assert has_all_perms(None, ["view_x"]) is False

    def test_user_has_all_required(self):
        user = _user(role_id=3)
        with patch("core.permissions.PermissionManager.has_permission", return_value=True):
            assert has_all_perms(user, ["view_clients", "edit_client"]) is True

    def test_user_missing_one_perm(self):
        user = _user(role_id=3)
        perms_granted = {"view_clients"}
        with patch("core.permissions.PermissionManager.has_permission",
                   side_effect=lambda u, code: code in perms_granted):
            result = has_all_perms(user, ["view_clients", "delete_client"])
        assert result is False

    def test_single_perm_check(self):
        user = _user(role_id=3)
        with patch("core.permissions.PermissionManager.has_permission", return_value=True):
            assert has_all_perms(user, ["view_clients"]) is True
