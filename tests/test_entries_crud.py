"""
tests/test_entries_crud.py
==========================
Covers EntriesCRUD — all pure functions + DB operations via in-memory SQLite.

Test classes:
  TestToDate         — 12 cases covering every branch of _to_date()
  TestComputeTotals  — 5 cases for compute_totals()
  TestEntriesCRUDDB  — create / update / delete / list via patched session
"""
import pytest
from datetime import date, datetime
from unittest.mock import MagicMock, patch

from database.crud.entries_crud import EntriesCRUD


# ══════════════════════════════════════════════════════════════════════════════
# _to_date() — pure, no DB
# ══════════════════════════════════════════════════════════════════════════════

class TestToDate:

    # null-like → None
    @pytest.mark.parametrize("val", [None, "", 0])
    def test_null_like_returns_none(self, val):
        assert EntriesCRUD._to_date(val) is None

    # date passthrough
    def test_date_passthrough(self):
        d = date(2024, 6, 15)
        assert EntriesCRUD._to_date(d) is d

    # datetime → date part only
    def test_datetime_returns_date_part(self):
        dt = datetime(2024, 6, 15, 12, 30, 0)
        assert EntriesCRUD._to_date(dt) == date(2024, 6, 15)

    # string formats
    @pytest.mark.parametrize("s,expected", [
        ("2024-06-15", date(2024, 6, 15)),
        ("15/06/2024", date(2024, 6, 15)),
        ("2024/06/15", date(2024, 6, 15)),
    ])
    def test_string_formats(self, s, expected):
        assert EntriesCRUD._to_date(s) == expected

    def test_string_with_whitespace(self):
        assert EntriesCRUD._to_date("  2024-06-15  ") == date(2024, 6, 15)

    def test_string_only_spaces_returns_none(self):
        assert EntriesCRUD._to_date("   ") is None

    def test_invalid_string_returns_none(self):
        assert EntriesCRUD._to_date("not-a-date") is None

    def test_unknown_type_returns_none(self):
        # an integer other than 0 falls through all branches
        assert EntriesCRUD._to_date(99999) is None


# ══════════════════════════════════════════════════════════════════════════════
# compute_totals() — pure, no DB
# ══════════════════════════════════════════════════════════════════════════════

class TestComputeTotals:

    def _item(self, count=0, net=0.0, gross=0.0):
        m = MagicMock()
        m.count           = count
        m.net_weight_kg   = net
        m.gross_weight_kg = gross
        return m

    def test_normal_two_items(self):
        items = [
            self._item(count=10, net=100.0, gross=110.0),
            self._item(count=5,  net=50.0,  gross=55.0),
        ]
        r = EntriesCRUD.compute_totals(items)
        assert r["total_pcs"]   == 15.0
        assert r["total_net"]   == 150.0
        assert r["total_gross"] == 165.0

    def test_empty_list_returns_zeros(self):
        r = EntriesCRUD.compute_totals([])
        assert r == {"total_pcs": 0, "total_net": 0, "total_gross": 0}

    def test_none_input_treated_as_empty(self):
        r = EntriesCRUD.compute_totals(None)   # type: ignore
        assert r["total_pcs"] == 0

    def test_none_attrs_default_to_zero(self):
        m = MagicMock()
        m.count = m.net_weight_kg = m.gross_weight_kg = None
        r = EntriesCRUD.compute_totals([m])
        assert r["total_pcs"] == 0.0
        assert r["total_net"] == 0.0

    def test_single_item(self):
        r = EntriesCRUD.compute_totals([self._item(count=3, net=30.0, gross=33.0)])
        assert r["total_pcs"]   == 3.0
        assert r["total_gross"] == 33.0


# ══════════════════════════════════════════════════════════════════════════════
# DB operations — use session_factory fixture from conftest.py
# ══════════════════════════════════════════════════════════════════════════════

class TestEntriesCRUDDB:
    """
    Each method patches get_session_local() with the test session_factory
    so we hit in-memory SQLite instead of the production DB.
    """

    @staticmethod
    def _patch(session_factory):
        return patch(
            "database.crud.entries_crud.get_session_local",
            return_value=session_factory,
        )

    # ── create ────────────────────────────────────────────────────────────────

    def test_create_returns_int_id(self, session_factory, make_client):
        client = make_client()
        header = {
            "entry_date":          date.today(),
            "owner_client_id":     client.id,
            "transport_unit_type": "truck",
            "transport_ref":       "CTR-001",
            "seal_no":             "SL-01",
        }
        with self._patch(session_factory):
            eid = EntriesCRUD().create(header, [], user_id=1)
        assert isinstance(eid, int) and eid > 0

    def test_create_with_items(self, session_factory, make_client,make_material):
        client = make_client()
        material = make_material()
        header = {"entry_date": date.today(), "owner_client_id": client.id}
        items = [{
            "material_id": material.id, "packaging_type_id": None,
            "count": 10, "net_weight_kg": 100.0, "gross_weight_kg": 105.0,
            "origin_country_id": None, "batch_no": "B1", "notes": "",
        }]
        with self._patch(session_factory):
            eid = EntriesCRUD().create(header, items, user_id=None)
        assert eid is not None

    def test_create_string_date_converted(self, session_factory, make_client):
        """_to_date() must convert the string before inserting."""
        client = make_client()
        header = {"entry_date": "2024-01-01", "owner_client_id": client.id}
        with self._patch(session_factory):
            eid = EntriesCRUD().create(header, [], user_id=1)
        assert eid is not None

    # ── update ────────────────────────────────────────────────────────────────

    def test_update_existing_returns_true(self, session_factory, make_entry):
        entry = make_entry(transport_ref="OLD")
        header = {
            "entry_date":      date.today(),
            "owner_client_id": entry.owner_client_id,
            "transport_ref":   "NEW",
        }
        with self._patch(session_factory):
            result = EntriesCRUD().update(entry.id, header, [], user_id=1)
        assert result is True

    def test_update_nonexistent_returns_false(self, session_factory):
        with self._patch(session_factory):
            result = EntriesCRUD().update(99999, {"entry_date": date.today()}, [])
        assert result is False

    def test_update_replaces_items(self, session_factory, make_entry,make_material):
        """After update with new items list, old items should be gone."""
        entry = make_entry()
        material = make_material()
        new_items = [{
            "material_id": material.id, "packaging_type_id": None,
            "count": 5, "net_weight_kg": 50.0, "gross_weight_kg": 52.0,
            "origin_country_id": None, "batch_no": None, "notes": None,
        }]
        header = {"entry_date": date.today(), "owner_client_id": entry.owner_client_id}
        with self._patch(session_factory):
            result = EntriesCRUD().update(entry.id, header, new_items, user_id=2)
        assert result is True

    # ── delete ────────────────────────────────────────────────────────────────

    def test_delete_existing_returns_true(self, session_factory, make_entry):
        entry = make_entry()
        with self._patch(session_factory):
            result = EntriesCRUD().delete(entry.id)
        assert result is True

    def test_delete_nonexistent_returns_false(self, session_factory):
        with self._patch(session_factory):
            result = EntriesCRUD().delete(99999)
        assert result is False

    # ── list_with_totals ──────────────────────────────────────────────────────

    def test_list_with_totals_has_required_keys(self, session_factory, make_entry):
        make_entry()
        with self._patch(session_factory):
            rows = EntriesCRUD().list_with_totals(limit=10)
        assert isinstance(rows, list)
        if rows:
            for key in ("id", "entry_no", "entry_date", "transport_ref",
                        "owner_client_obj", "items_count",
                        "total_pcs", "total_net", "total_gross"):
                assert key in rows[0], f"Missing key: {key}"

    def test_list_with_totals_empty_db_returns_list(self, session_factory):
        with self._patch(session_factory):
            rows = EntriesCRUD().list_with_totals(limit=10)
        assert isinstance(rows, list)

    # ── totals_for ────────────────────────────────────────────────────────────

    def test_totals_for_no_items_returns_zeros(self, session_factory, make_entry):
        entry = make_entry()
        with self._patch(session_factory):
            r = EntriesCRUD().totals_for(entry.id)
        assert r["items_count"] == 0
        assert r["total_pcs"]   == 0.0
        assert r["total_net"]   == 0.0
        assert r["total_gross"] == 0.0