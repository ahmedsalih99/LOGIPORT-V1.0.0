# -*- coding: utf-8 -*-
"""
utils/auth_utils.py
=====================
Pure authentication utilities — zero Qt, zero SQLAlchemy dependency.
Used by UsersCRUD and testable in isolation.
"""
from passlib.hash import bcrypt as _bcrypt


def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt."""
    return _bcrypt.hash(password)


def is_password_hashed(password: str) -> bool:
    """Return True if the value looks like a bcrypt hash."""
    return isinstance(password, str) and (
        password.startswith("$2b$") or password.startswith("$2y$")
    )


def check_password(plain: str, hashed: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    try:
        return _bcrypt.verify(plain, hashed)
    except Exception:
        return False
