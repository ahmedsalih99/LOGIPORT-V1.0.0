# -*- coding: utf-8 -*-
"""
tests/test_lookup_cruds.py
============================
Tests for lookup-table CRUDs: DeliveryMethods, PackagingTypes, MaterialTypes.
All share the same CRUD pattern (add / get / list / update / delete).
"""
import sys, os
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from database.crud.delivery_methods_crud  import DeliveryMethodsCRUD
from database.crud.packaging_types_crud   import PackagingTypesCRUD
from database.crud.material_types_crud    import MaterialTypesCRUD

_PATCH_DM  = "database.crud.delivery_methods_crud.get_session_local"
_PATCH_PT  = "database.crud.packaging_types_crud.get_session_local"
_PATCH_MT  = "database.crud.material_types_crud.get_session_local"


# ═════════════════════════════════════════════════════════════════════════════
# DeliveryMethodsCRUD
# ═════════════════════════════════════════════════════════════════════════════

class TestDeliveryMethodsCRUD:

    def test_add_basic(self, session_factory):
        with patch(_PATCH_DM, session_factory):
            dm = DeliveryMethodsCRUD().add_delivery_method(
                name_ar="بحري", name_en="Sea", name_tr="Deniz"
            )
        assert dm.id is not None
        assert dm.name_ar == "بحري"
        assert dm.name_en == "Sea"

    def test_get_existing(self, session_factory):
        with patch(_PATCH_DM, session_factory):
            crud = DeliveryMethodsCRUD()
            dm = crud.add_delivery_method(name_ar="جوي", name_en="Air", name_tr="Hava")
            found = crud.get_delivery_method(dm.id)
        assert found is not None
        assert found.name_en == "Air"

    def test_get_missing_returns_none(self, session_factory):
        with patch(_PATCH_DM, session_factory):
            assert DeliveryMethodsCRUD().get_delivery_method(99999) is None

    def test_list_includes_added(self, session_factory):
        with patch(_PATCH_DM, session_factory):
            crud = DeliveryMethodsCRUD()
            crud.add_delivery_method(name_ar="بري", name_en="Road", name_tr="Kara")
            items = crud.list_delivery_methods()
        assert any(d.name_en == "Road" for d in items)

    def test_update_name(self, session_factory):
        with patch(_PATCH_DM, session_factory):
            crud = DeliveryMethodsCRUD()
            dm = crud.add_delivery_method(name_ar="قديم", name_en="Old", name_tr="Eski")
            updated = crud.update_delivery_method(dm.id, {"name_en": "Updated"})
        assert updated.name_en == "Updated"

    def test_update_nonexistent_returns_none(self, session_factory):
        with patch(_PATCH_DM, session_factory):
            result = DeliveryMethodsCRUD().update_delivery_method(99999, {"name_en": "X"})
        assert result is None

    def test_delete_existing(self, session_factory):
        with patch(_PATCH_DM, session_factory):
            crud = DeliveryMethodsCRUD()
            dm = crud.add_delivery_method(name_ar="حذف", name_en="Delete Me", name_tr="Sil")
            assert crud.delete_delivery_method(dm.id) is True
            assert crud.get_delivery_method(dm.id) is None

    def test_delete_nonexistent_returns_false(self, session_factory):
        with patch(_PATCH_DM, session_factory):
            assert DeliveryMethodsCRUD().delete_delivery_method(99999) is False


# ═════════════════════════════════════════════════════════════════════════════
# PackagingTypesCRUD
# ═════════════════════════════════════════════════════════════════════════════

class TestPackagingTypesCRUD:

    def test_add_basic(self, session_factory):
        with patch(_PATCH_PT, session_factory):
            pt = PackagingTypesCRUD().add_packaging_type(
                name_ar="كرتون", name_en="Carton", name_tr="Karton"
            )
        assert pt.id is not None
        assert pt.name_ar == "كرتون"

    def test_get_existing(self, session_factory):
        with patch(_PATCH_PT, session_factory):
            crud = PackagingTypesCRUD()
            pt = crud.add_packaging_type(name_ar="صندوق", name_en="Box", name_tr="Kutu")
            found = crud.get_packaging_type(pt.id)
        assert found is not None
        assert found.name_en == "Box"

    def test_get_missing_returns_none(self, session_factory):
        with patch(_PATCH_PT, session_factory):
            assert PackagingTypesCRUD().get_packaging_type(99999) is None

    def test_list_not_empty_after_add(self, session_factory):
        with patch(_PATCH_PT, session_factory):
            crud = PackagingTypesCRUD()
            crud.add_packaging_type(name_ar="كيس", name_en="Bag", name_tr="Çanta")
            items = crud.list_packaging_types()
        assert len(items) >= 1

    def test_update(self, session_factory):
        with patch(_PATCH_PT, session_factory):
            crud = PackagingTypesCRUD()
            pt = crud.add_packaging_type(name_ar="قديم", name_en="OldPT", name_tr="Eski")
            updated = crud.update_packaging_type(pt.id, {"name_en": "NewPT"})
        assert updated.name_en == "NewPT"

    def test_update_nonexistent_returns_none(self, session_factory):
        with patch(_PATCH_PT, session_factory):
            assert PackagingTypesCRUD().update_packaging_type(99999, {"name_en": "X"}) is None

    def test_delete_existing(self, session_factory):
        with patch(_PATCH_PT, session_factory):
            crud = PackagingTypesCRUD()
            pt = crud.add_packaging_type(name_ar="محذوف", name_en="DelPT", name_tr="Sil")
            assert crud.delete_packaging_type(pt.id) is True

    def test_delete_nonexistent_returns_false(self, session_factory):
        with patch(_PATCH_PT, session_factory):
            assert PackagingTypesCRUD().delete_packaging_type(99999) is False


# ═════════════════════════════════════════════════════════════════════════════
# MaterialTypesCRUD
# ═════════════════════════════════════════════════════════════════════════════

class TestMaterialTypesCRUD:

    def test_add_basic(self, session_factory):
        with patch(_PATCH_MT, session_factory):
            mt = MaterialTypesCRUD().add_material_type(
                name_ar="معادن", name_en="Metals", name_tr="Metaller"
            )
        assert mt.id is not None
        assert mt.name_en == "Metals"

    def test_get_existing(self, session_factory):
        with patch(_PATCH_MT, session_factory):
            crud = MaterialTypesCRUD()
            mt = crud.add_material_type(name_ar="كيمياء", name_en="Chemicals", name_tr="Kimya")
            found = crud.get_material_type(mt.id)
        assert found is not None

    def test_get_missing_returns_none(self, session_factory):
        with patch(_PATCH_MT, session_factory):
            assert MaterialTypesCRUD().get_material_type(99999) is None

    def test_list_includes_added(self, session_factory):
        with patch(_PATCH_MT, session_factory):
            crud = MaterialTypesCRUD()
            crud.add_material_type(name_ar="بلاستيك", name_en="Plastics", name_tr="Plastik")
            items = crud.list_material_types()
        assert any(m.name_en == "Plastics" for m in items)

    def test_update_name(self, session_factory):
        with patch(_PATCH_MT, session_factory):
            crud = MaterialTypesCRUD()
            mt = crud.add_material_type(name_ar="قديم", name_en="OldMT", name_tr="Eski")
            updated = crud.update_material_type(mt.id, {"name_en": "NewMT"})
        assert updated.name_en == "NewMT"

    def test_delete_existing(self, session_factory):
        with patch(_PATCH_MT, session_factory):
            crud = MaterialTypesCRUD()
            mt = crud.add_material_type(name_ar="حذف", name_en="DelMT", name_tr="Sil")
            assert crud.delete_material_type(mt.id) is True

    def test_delete_nonexistent_returns_false(self, session_factory):
        with patch(_PATCH_MT, session_factory):
            assert MaterialTypesCRUD().delete_material_type(99999) is False
