# -*- coding: utf-8 -*-
"""
utils/password_utils.py
=========================
Pure password utility functions — zero external dependencies.
"""


def password_strength(password: str) -> tuple:
    """
    Returns (label_key, color_hex) for password strength.

    Scoring:
      +1  length >= 8
      +1  has uppercase letter
      +1  has digit
      +1  has non-alphanumeric symbol

    0-1  → ("password_weak",   "#EF4444")
    2    → ("password_fair",   "#F59E0B")
    3    → ("password_good",   "#3B82F6")
    4    → ("password_strong", "#10B981")
    """
    if not password:
        return ("", "#94A3B8")

    score = sum([
        len(password) >= 8,
        any(c.isupper()  for c in password),
        any(c.isdigit()  for c in password),
        any(not c.isalnum() for c in password),
    ])

    if score <= 1: return ("password_weak",   "#EF4444")
    if score == 2: return ("password_fair",   "#F59E0B")
    if score == 3: return ("password_good",   "#3B82F6")
    return             ("password_strong", "#10B981")
