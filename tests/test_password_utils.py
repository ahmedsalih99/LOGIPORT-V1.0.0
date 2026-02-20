# -*- coding: utf-8 -*-
"""
tests/test_password_utils.py
===============================
Tests for utils.password_utils — pure functions, zero Qt dependency.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from utils.password_utils import password_strength


class TestPasswordStrength:

    def test_empty_password(self):
        key, color = password_strength("")
        assert key == ""
        assert color == "#94A3B8"

    def test_short_only_lower(self):
        key, color = password_strength("abc")
        assert key == "password_weak"
        assert color == "#EF4444"

    def test_long_only_lower(self):
        # length >= 8 = 1 point only → weak
        key, _ = password_strength("abcdefghij")
        assert key == "password_weak"

    def test_length_plus_digit(self):
        # length + digit = 2 → fair
        key, color = password_strength("abcde123")
        assert key == "password_fair"
        assert color == "#F59E0B"

    def test_length_digit_upper(self):
        # length + upper + digit = 3 → good
        key, color = password_strength("Abcde123")
        assert key == "password_good"
        assert color == "#3B82F6"

    def test_strong_all_criteria(self):
        key, color = password_strength("Abcde123!")
        assert key == "password_strong"
        assert color == "#10B981"

    def test_only_digits_long(self):
        # length + digit = 2 → fair
        key, _ = password_strength("12345678")
        assert key == "password_fair"

    def test_only_symbols_long(self):
        # length + symbol = 2 → fair
        key, _ = password_strength("!@#$%^&*")
        assert key == "password_fair"

    def test_single_char(self):
        key, _ = password_strength("x")
        assert key == "password_weak"

    @pytest.mark.parametrize("pw,expected_key", [
        ("password",    "password_weak"),    # only length
        ("Password1",   "password_good"),    # length + upper + digit
        ("P@ssword1",   "password_strong"),  # all 4
        ("x",           "password_weak"),    # nothing
        ("UPPERCASE1!", "password_strong"),  # all 4
        ("abc123",      "password_weak"),    # digit only, no length
        ("Abc12345",    "password_good"),    # length + upper + digit
        ("abc12345",    "password_fair"),    # length + digit
    ])
    def test_parametrize(self, pw, expected_key):
        key, _ = password_strength(pw)
        assert key == expected_key

    def test_returns_tuple_of_two(self):
        result = password_strength("anything")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_color_is_hex(self):
        for pw in ["", "a", "password1A!", "abc"]:
            _, color = password_strength(pw)
            assert color.startswith("#"), f"Expected hex color, got {color!r}"
