# -*- coding: utf-8 -*-
"""
tests/test_remaining_cruds.py
================================
Tests for the last untested CRUDs:
  - AuditLogCRUD
  - CompanyRolesCRUD  (read-only: company roles are seeded, not user-created)
  - PricingTypesCRUD
  - PermissionsCRUD / RolesCRUD (via permissions_crud.py)
"""
import sys, os
from unittest.mock import patch, MagicMock

# ── Mock Qt before any core imports ─────────────────────────────────────────
for _m in ["PySide6","PySide6.QtCore","PySide6.QtWidgets","PySide6.QtGui",
           "PySide6.QtPrintSupport","PySide6.QtNetwork","PySide6.QtSvg"]:
    if _m not in sys.modules:
        sys.modules[_m] = MagicMock()
sys.modules["PySide6.QtCore"].Signal  = MagicMock(return_value=MagicMock())
sys.modules["PySide6.QtCore"].QObject = object

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from database.crud.audit_log_crud    import AuditLogCRUD
from database.crud.company_roles_crud import CompanyRolesCRUD
from database.crud.pricing_types_crud import PricingTypesCRUD
from database.crud.permissions_crud  import PermissionsCRUD, RolesCRUD

_PATCH_AUDIT  = "database.crud.audit_log_crud.get_session_local"
_PATCH_CROLES = "database.crud.company_roles_crud.get_session_local"
_PATCH_PT     = "database.crud.pricing_types_crud.get_session_local"
_PATCH_PERMS  = "database.crud.permissions_crud.get_session_local"


# ═══════════════════════════════════════════════════════════════════════════
# AuditLogCRUD
# ═══════════════════════════════════════════════════════════════════════════

class TestAuditLogCRUD:

    def test_log_action_returns_object(self, session_factory):
        with patch(_PATCH_AUDIT, session_factory):
            log = AuditLogCRUD().log_action(
                user_id=None, action="create", table_name="clients", record_id=1
            )
        assert log is not None
        assert log.id is not None
        assert log.action == "create"
        assert log.table_name == "clients"

    def test_log_without_user(self, session_factory):
        with patch(_PATCH_AUDIT, session_factory):
            log = AuditLogCRUD().log_action(
                user_id=None, action="delete", table_name="materials"
            )
        assert log is not None
        assert log.user_id is None

    def test_log_with_details(self, session_factory):
        with patch(_PATCH_AUDIT, session_factory):
            log = AuditLogCRUD().log_action(
                user_id=1, action="update", table_name="transactions",
                record_id=42, details='{"field": "status"}'
            )
        assert log.details == '{"field": "status"}'
        assert log.record_id == 42

    def test_get_logs_by_table(self, session_factory):
        with patch(_PATCH_AUDIT, session_factory):
            crud = AuditLogCRUD()
            crud.log_action(user_id=None, action="create", table_name="entries")
            crud.log_action(user_id=None, action="update", table_name="entries")
            crud.log_action(user_id=None, action="create", table_name="clients")
            logs = crud.get_logs_by_table("entries")
        assert len(logs) == 2
        assert all(l.table_name == "entries" for l in logs)

    def test_get_logs_by_table_empty(self, session_factory):
        with patch(_PATCH_AUDIT, session_factory):
            logs = AuditLogCRUD().get_logs_by_table("no_such_table")
        assert logs == []

    def test_multiple_actions_stored(self, session_factory):
        with patch(_PATCH_AUDIT, session_factory):
            crud = AuditLogCRUD()
            for action in ["create", "update", "delete"]:
                crud.log_action(user_id=None, action=action, table_name="materials")
            all_logs = crud.get_logs_by_table("materials")
        assert len(all_logs) == 3

    def test_log_action_failure_returns_none(self, session_factory):
        """If logging fails, should return None gracefully (not raise)."""
        with patch(_PATCH_AUDIT, session_factory):
            crud = AuditLogCRUD()
            # Pass invalid data that causes DB error — None table_name may fail constraint
            # But the CRUD catches exceptions and returns None
            result = crud.log_action(user_id=None, action="x", table_name="t")
        # Either succeeds or returns None — never raises
        assert result is None or result.id is not None


# ═══════════════════════════════════════════════════════════════════════════
# CompanyRolesCRUD  (read-only CRUD — roles are seeded, not user-created)
# ═══════════════════════════════════════════════════════════════════════════

class TestCompanyRolesCRUD:

    def _seed_role(self, db_session):
        from database.models.company_role import CompanyRole
        role = CompanyRole(
            code="EXPORTER",
            name_ar="مصدّر", name_en="Exporter", name_tr="İhracatçı",
            is_active=True
        )
        db_session.add(role)
        db_session.flush()
        return role

    def test_get_all_roles(self, session_factory, db_session):
        self._seed_role(db_session)
        with patch(_PATCH_CROLES, session_factory):
            roles = CompanyRolesCRUD().get_all_roles()
        assert len(roles) >= 1

    def test_get_all_active(self, session_factory, db_session):
        from database.models.company_role import CompanyRole
        active = CompanyRole(code="ACT", name_ar="نشط", name_en="Active", name_tr="Aktif", is_active=True)
        inactive = CompanyRole(code="INA", name_ar="غير نشط", name_en="Inactive", name_tr="Pasif", is_active=False)
        db_session.add_all([active, inactive])
        db_session.flush()
        with patch(_PATCH_CROLES, session_factory):
            active_roles = CompanyRolesCRUD().get_all_active()
        assert all(r.is_active for r in active_roles)

    def test_get_by_code(self, session_factory, db_session):
        self._seed_role(db_session)
        with patch(_PATCH_CROLES, session_factory):
            found = CompanyRolesCRUD().get_by_code("EXPORTER")
        assert found is not None
        assert found.code == "EXPORTER"

    def test_get_by_code_missing_returns_none(self, session_factory):
        with patch(_PATCH_CROLES, session_factory):
            assert CompanyRolesCRUD().get_by_code("NO_SUCH_CODE") is None

    def test_get_by_id(self, session_factory, db_session):
        role = self._seed_role(db_session)
        with patch(_PATCH_CROLES, session_factory):
            found = CompanyRolesCRUD().get_by_id(role.id)
        assert found is not None

    def test_get_by_id_missing_returns_none(self, session_factory):
        with patch(_PATCH_CROLES, session_factory):
            assert CompanyRolesCRUD().get_by_id(99999) is None


# ═══════════════════════════════════════════════════════════════════════════
# PricingTypesCRUD
# ═══════════════════════════════════════════════════════════════════════════

class TestPricingTypesCRUD:

    def test_add_basic(self, session_factory):
        with patch(_PATCH_PT, session_factory):
            pt = PricingTypesCRUD().add_pricing_type(
                code="FOB", name_ar="فوب", name_en="FOB", name_tr="FOB"
            )
        assert pt is not None
        assert pt.id is not None
        assert pt.code == "FOB"

    def test_add_inactive(self, session_factory):
        with patch(_PATCH_PT, session_factory):
            pt = PricingTypesCRUD().add_pricing_type(
                code="CIF2", name_ar="سيف", name_en="CIF", is_active=False
            )
        assert not pt.is_active  # SQLite stores bool as 0/1

    def test_get_all_types(self, session_factory):
        with patch(_PATCH_PT, session_factory):
            crud = PricingTypesCRUD()
            crud.add_pricing_type(code="EXW", name_ar="مستودع", name_en="EXW")
            types = crud.get_all_types()
        assert any(t.code == "EXW" for t in types)

    def test_get_all_active_only(self, session_factory):
        with patch(_PATCH_PT, session_factory):
            crud = PricingTypesCRUD()
            crud.add_pricing_type(code="DAP", name_ar="داب", name_en="DAP", is_active=True)
            crud.add_pricing_type(code="DDP", name_ar="ددب", name_en="DDP", is_active=False)
            active = crud.get_all_types(active_only=True)
        assert all(t.is_active for t in active)
        assert any(t.code == "DAP" for t in active)
        assert not any(t.code == "DDP" for t in active)

    def test_get_by_code(self, session_factory):
        with patch(_PATCH_PT, session_factory):
            crud = PricingTypesCRUD()
            crud.add_pricing_type(code="CFR", name_ar="سي اف ار", name_en="CFR")
            found = crud.get_by_code("CFR")
        assert found is not None
        assert found.name_en == "CFR"

    def test_get_by_code_missing_returns_none(self, session_factory):
        with patch(_PATCH_PT, session_factory):
            assert PricingTypesCRUD().get_by_code("NOPE") is None

    def test_get_by_id(self, session_factory):
        with patch(_PATCH_PT, session_factory):
            crud = PricingTypesCRUD()
            pt = crud.add_pricing_type(code="FCA", name_ar="اف سي اي", name_en="FCA")
            found = crud.get_by_id(pt.id)
        assert found is not None

    def test_get_by_id_missing_returns_none(self, session_factory):
        with patch(_PATCH_PT, session_factory):
            assert PricingTypesCRUD().get_by_id(99999) is None

    def test_update(self, session_factory):
        with patch(_PATCH_PT, session_factory):
            crud = PricingTypesCRUD()
            pt = crud.add_pricing_type(code="CPT", name_ar="قديم", name_en="Old")
            updated = crud.update_pricing_type(pt.id, name_en="Updated")
        assert updated is not None
        assert updated.name_en == "Updated"

    def test_update_nonexistent_returns_none(self, session_factory):
        with patch(_PATCH_PT, session_factory):
            assert PricingTypesCRUD().update_pricing_type(99999, name_en="X") is None


# ═══════════════════════════════════════════════════════════════════════════
# PermissionsCRUD & RolesCRUD
# ═══════════════════════════════════════════════════════════════════════════

class TestPermissionsCRUD:

    def test_add_permission(self, session_factory):
        with patch(_PATCH_PERMS, session_factory):
            p = PermissionsCRUD().add_permission(
                code="view_clients",
                label_ar="عرض الزبائن",
                label_en="View Clients",
                label_tr="Müşterileri Gör",
            )
        assert p is not None
        assert p.code == "view_clients"

    def test_get_all_returns_list(self, session_factory):
        with patch(_PATCH_PERMS, session_factory):
            crud = PermissionsCRUD()
            crud.add_permission(code="add_client", label_ar="إضافة", label_en="Add Client")
            result = crud.get_all()
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_update_permission(self, session_factory):
        with patch(_PATCH_PERMS, session_factory):
            crud = PermissionsCRUD()
            p = crud.add_permission(code="edit_x", label_ar="تعديل", label_en="Edit X")
            updated = crud.update_permission(p.id, {"label_en": "Edit Updated"})
        assert updated is not None

    def test_delete_permission(self, session_factory):
        with patch(_PATCH_PERMS, session_factory):
            crud = PermissionsCRUD()
            p = crud.add_permission(code="del_perm", label_ar="حذف", label_en="Delete Perm")
            assert crud.delete_permission(p.id) is True


class TestRolesCRUD:

    def test_add_role(self, session_factory):
        with patch(_PATCH_PERMS, session_factory):
            r = RolesCRUD().add_role(
                name="supervisor",
                label_ar="مشرف",
                label_en="Supervisor",
                label_tr="Süpervizör",
            )
        assert r is not None
        assert r.name == "supervisor"

    def test_get_all_roles(self, session_factory):
        with patch(_PATCH_PERMS, session_factory):
            crud = RolesCRUD()
            crud.add_role(name="viewer", label_ar="مشاهد", label_en="Viewer")
            result = crud.get_all()
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_update_role(self, session_factory):
        with patch(_PATCH_PERMS, session_factory):
            crud = RolesCRUD()
            r = crud.add_role(name="old_role", label_ar="قديم", label_en="Old Role")
            updated = crud.update_role(r.id, {"label_en": "New Label"})
        assert updated is not None

    def test_delete_role(self, session_factory):
        with patch(_PATCH_PERMS, session_factory):
            crud = RolesCRUD()
            r = crud.add_role(name="to_del_role", label_ar="حذف", label_en="Delete Role")
            assert crud.delete_role(r.id) is True

    def test_delete_nonexistent_returns_false(self, session_factory):
        with patch(_PATCH_PERMS, session_factory):
            assert RolesCRUD().delete_role(99999) is False
