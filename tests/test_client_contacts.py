# -*- coding: utf-8 -*-
"""
tests/test_client_contacts.py
===============================
Tests for ClientContactsCRUD — list, add, update, delete, primary.
"""
import pytest
from unittest.mock import patch
from database.crud.clients_crud import ClientContactsCRUD


class TestClientContactsCRUD:

    @staticmethod
    def _patch(sf):
        """Patch session_factory used by ClientContactsCRUD."""
        return patch("database.crud.clients_crud.get_session_local", sf)

    # ── add_contact ──────────────────────────────────────────────────────────

    def test_add_contact_basic(self, session_factory, make_client):
        client = make_client()
        with self._patch(session_factory):
            crud = ClientContactsCRUD()
            c = crud.add_contact(
                client_id=client.id,
                name="John Doe",
                role_title="Manager",
                phone="0501234567",
                email="john@example.com",
            )
        assert c.id is not None
        assert c.name == "JOHN DOE"          # uppercased
        assert c.email == "john@example.com" # lowercase

    def test_add_contact_primary(self, session_factory, make_client):
        client = make_client()
        with self._patch(session_factory):
            crud = ClientContactsCRUD()
            c = crud.add_contact(
                client_id=client.id,
                name="Primary Person",
                is_primary=True,
            )
        assert c.is_primary is True

    def test_add_two_contacts_only_one_primary(self, session_factory, make_client):
        client = make_client()
        with self._patch(session_factory):
            crud = ClientContactsCRUD()
            c1 = crud.add_contact(client_id=client.id, name="First",  is_primary=True)
            c2 = crud.add_contact(client_id=client.id, name="Second", is_primary=True)
            contacts = crud.list_contacts(client.id)
        primaries = [c for c in contacts if c.is_primary]
        # After adding second primary, first should be cleared
        primary_ids = {c.id for c in primaries}
        assert c2.id in primary_ids
        assert c1.id not in primary_ids

    # ── list_contacts ────────────────────────────────────────────────────────

    def test_list_contacts_empty(self, session_factory, make_client):
        client = make_client()
        with self._patch(session_factory):
            crud = ClientContactsCRUD()
            result = crud.list_contacts(client.id)
        assert result == []

    def test_list_contacts_ordered_primary_first(self, session_factory, make_client):
        client = make_client()
        with self._patch(session_factory):
            crud = ClientContactsCRUD()
            crud.add_contact(client_id=client.id, name="Regular",   is_primary=False)
            crud.add_contact(client_id=client.id, name="Primary",   is_primary=True)
            contacts = crud.list_contacts(client.id)
        assert len(contacts) == 2
        assert contacts[0].is_primary is True  # primary comes first

    def test_list_contacts_different_clients_isolated(self, session_factory, make_client):
        c1 = make_client()
        c2 = make_client()
        with self._patch(session_factory):
            crud = ClientContactsCRUD()
            crud.add_contact(client_id=c1.id, name="Alice")
            crud.add_contact(client_id=c2.id, name="Bob")
            res1 = crud.list_contacts(c1.id)
            res2 = crud.list_contacts(c2.id)
        assert len(res1) == 1 and res1[0].name == "ALICE"
        assert len(res2) == 1 and res2[0].name == "BOB"

    # ── update_contact ───────────────────────────────────────────────────────

    def test_update_contact_name(self, session_factory, make_client):
        client = make_client()
        with self._patch(session_factory):
            crud = ClientContactsCRUD()
            c = crud.add_contact(client_id=client.id, name="Old Name")
            updated = crud.update_contact(c.id, name="New Name")
        assert updated is not None
        assert updated.name == "NEW NAME"

    def test_update_contact_nonexistent_returns_none(self, session_factory):
        with self._patch(session_factory):
            crud = ClientContactsCRUD()
            result = crud.update_contact(99999, name="Ghost")
        assert result is None

    def test_update_contact_email_lowercased(self, session_factory, make_client):
        client = make_client()
        with self._patch(session_factory):
            crud = ClientContactsCRUD()
            c = crud.add_contact(client_id=client.id, name="Test")
            updated = crud.update_contact(c.id, email="UPPER@EXAMPLE.COM")
        assert updated.email == "upper@example.com"

    def test_update_set_primary_clears_old(self, session_factory, make_client):
        client = make_client()
        with self._patch(session_factory):
            crud = ClientContactsCRUD()
            c1 = crud.add_contact(client_id=client.id, name="First",  is_primary=True)
            c2 = crud.add_contact(client_id=client.id, name="Second", is_primary=False)
            crud.update_contact(c2.id, is_primary=True)
            contacts = crud.list_contacts(client.id)
        by_id = {c.id: c for c in contacts}
        assert by_id[c2.id].is_primary is True
        assert by_id[c1.id].is_primary is False

    # ── delete_contact ───────────────────────────────────────────────────────

    def test_delete_contact_existing(self, session_factory, make_client):
        client = make_client()
        with self._patch(session_factory):
            crud = ClientContactsCRUD()
            c = crud.add_contact(client_id=client.id, name="ToDelete")
            result = crud.delete_contact(c.id)
            remaining = crud.list_contacts(client.id)
        assert result is True
        assert len(remaining) == 0

    def test_delete_contact_nonexistent_returns_false(self, session_factory):
        with self._patch(session_factory):
            crud = ClientContactsCRUD()
            result = crud.delete_contact(99999)
        assert result is False