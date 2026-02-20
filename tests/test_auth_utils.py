# -*- coding: utf-8 -*-
"""
tests/test_auth_utils.py
==========================
Tests for utils/auth_utils — pure bcrypt helpers, zero Qt dependency.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from utils.auth_utils import hash_password, is_password_hashed, check_password


class TestHashPassword:

    def test_returns_bcrypt_string(self):
        h = hash_password("secret123")
        assert h.startswith("$2b$") or h.startswith("$2y$")

    def test_hash_is_not_plain(self):
        assert hash_password("mypassword") != "mypassword"

    def test_different_salts_each_call(self):
        """bcrypt generates a new salt on every call."""
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2

    def test_empty_string_hashes(self):
        h = hash_password("")
        assert is_password_hashed(h)


class TestIsPasswordHashed:

    def test_bcrypt_hash_detected(self):
        h = hash_password("test")
        assert is_password_hashed(h) is True

    def test_plain_text_not_detected(self):
        assert is_password_hashed("plaintext") is False
        assert is_password_hashed("Password1!") is False

    def test_empty_string_not_detected(self):
        assert is_password_hashed("") is False

    def test_partial_prefix_not_detected(self):
        # "$2b$" alone starts with the prefix, so is_password_hashed returns True
        # (by design — it checks prefix only). Test values that clearly aren't hashes:
        assert is_password_hashed("2b$12$abc") is False    # missing leading $
        assert is_password_hashed("$sha256$abc") is False  # wrong prefix

    @pytest.mark.parametrize("non_hash", [
        "hello", "12345678", "abc!@#", "None", "$sha256$abc",
    ])
    def test_non_bcrypt_values(self, non_hash):
        assert is_password_hashed(non_hash) is False


class TestCheckPassword:

    def test_correct_password_returns_true(self):
        h = hash_password("mypass")
        assert check_password("mypass", h) is True

    def test_wrong_password_returns_false(self):
        h = hash_password("mypass")
        assert check_password("wrongpass", h) is False

    def test_empty_plain_wrong(self):
        h = hash_password("nonempty")
        assert check_password("", h) is False

    def test_hashed_as_plain_returns_false(self):
        """Passing the hash itself as plain text should fail gracefully."""
        h = hash_password("pw")
        assert check_password(h, h) is False

    def test_invalid_hash_returns_false(self):
        assert check_password("anything", "not-a-hash") is False

    @pytest.mark.parametrize("password", [
        "simple", "P@ssw0rd!", "arabic_test", "12345678", "a" * 50,
    ])
    def test_roundtrip(self, password):
        h = hash_password(password)
        assert check_password(password, h) is True
