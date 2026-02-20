"""
tests/test_clients.py
======================
Covers ClientsCRUD — DB operations via in-memory SQLite.

Test classes:
  TestGenerateNextClientCode — pure code-generation logic
  TestClientsCRUDDB          — add / get / update / delete via patched session
"""
import pytest
from unittest.mock import patch, MagicMock

from database.crud.clients_crud import ClientsCRUD


# ══════════════════════════════════════════════════════════════════════════════
# generate_next_client_code() — uses a real session but no side effects
# ══════════════════════════════════════════════════════════════════════════════

class TestGenerateNextClientCode:

    def test_first_client_gets_c0001(self, db_session):
        """Empty table → first code must be C0001."""
        code = ClientsCRUD.generate_next_client_code(db_session, prefix="C")
        assert code == "C0001"

    def test_increments_from_existing(self, db_session, make_client):
        from database.models.client import Client
        # insert a client with code C0003
        c = make_client(name_ar="عميل", name_en="Client")
        c.code = "C0003"
        db_session.flush()
        code = ClientsCRUD.generate_next_client_code(db_session, prefix="C")
        assert code == "C0004"

    def test_custom_prefix(self, db_session):
        code = ClientsCRUD.generate_next_client_code(db_session, prefix="V")
        assert code.startswith("V")
        assert code == "V0001"

    def test_code_zero_padded_to_4(self, db_session, make_client):
        c = make_client()
        c.code = "C0009"
        db_session.flush()
        code = ClientsCRUD.generate_next_client_code(db_session, prefix="C")
        assert code == "C0010"


# ══════════════════════════════════════════════════════════════════════════════
# DB operations — use session_factory fixture
# ══════════════════════════════════════════════════════════════════════════════

class TestClientsCRUDDB:

    @staticmethod
    def _patch(session_factory):
        return patch(
            "database.crud.clients_crud.get_session_local",
            return_value=session_factory,
        )

    # ── add_client ────────────────────────────────────────────────────────────

    def test_add_client_returns_client_object(self, session_factory):
        with self._patch(session_factory):
            client = ClientsCRUD().add_client(
                name_ar="شركة الاختبار",
                name_en="Test Company",
                user_id=1,
            )
        assert client is not None
        assert client.id is not None

    def test_add_client_name_uppercased(self, session_factory):
        """add_client normalises names to uppercase."""
        with self._patch(session_factory):
            client = ClientsCRUD().add_client(name_ar="شركة", name_en="test company")
        assert client.name_en == "TEST COMPANY"

    def test_add_client_auto_generates_code(self, session_factory):
        with self._patch(session_factory):
            client = ClientsCRUD().add_client(name_ar="شركة", name_en="X")
        assert client.code and client.code.startswith("C")

    def test_add_client_custom_code_kept(self, session_factory):
        with self._patch(session_factory):
            client = ClientsCRUD().add_client(
                name_ar="شركة", name_en="X", code="MYCODE"
            )
        assert client.code == "MYCODE"

    # ── get_client ────────────────────────────────────────────────────────────

    def test_get_client_existing(self, session_factory, make_client):
        existing = make_client(name_en="Fetch Me")
        with self._patch(session_factory):
            result = ClientsCRUD().get_client(existing.id)
        assert result is not None
        assert result.id == existing.id

    def test_get_client_nonexistent_returns_none(self, session_factory):
        with self._patch(session_factory):
            result = ClientsCRUD().get_client(99999)
        assert result is None

    # ── list_clients ──────────────────────────────────────────────────────────

    def test_list_clients_returns_list(self, session_factory, make_client):
        make_client()
        make_client(name_en="Second")
        with self._patch(session_factory):
            clients = ClientsCRUD().list_clients()
        assert isinstance(clients, list)
        assert len(clients) >= 2

    # ── update_client ─────────────────────────────────────────────────────────

    def test_update_client_existing(self, session_factory, make_client):
        c = make_client(name_en="Old Name")
        with self._patch(session_factory):
            result = ClientsCRUD().update_client(
                c.id, {"name_en": "New Name"}, user_id=1
            )
        assert result is not None

    def test_update_client_nonexistent_returns_none(self, session_factory):
        with self._patch(session_factory):
            result = ClientsCRUD().update_client(99999, {"name_en": "X"})
        assert result is None

    # ── delete_client ─────────────────────────────────────────────────────────

    def test_delete_client_existing_returns_true(self, session_factory, make_client):
        c = make_client()
        with self._patch(session_factory):
            result = ClientsCRUD().delete_client(c.id)
        assert result is True

    def test_delete_client_nonexistent_returns_false(self, session_factory):
        with self._patch(session_factory):
            result = ClientsCRUD().delete_client(99999)
        assert result is False