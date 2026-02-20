# -*- coding: utf-8 -*-
"""
tests/test_exceptions.py
==========================
Tests for the LOGIPORT hierarchical exception system.
All pure Python — no DB or Qt needed.
"""
import pytest
from exceptions import (
    LogiportError,
    DatabaseError, NotFoundError, DuplicateError,
    ValidationError, MissingFieldError, InvalidValueError,
    PermissionError as LPermissionError, AuthenticationError,
    ServiceError, DocumentError,
    TemplateNotFoundError, BuilderNotFoundError,
    NumberingError, BackupError,
    ConfigurationError,
)


# ── inheritance hierarchy ─────────────────────────────────────────────────────

class TestInheritance:

    def test_all_inherit_from_logiport_error(self):
        errs = [
            DatabaseError, NotFoundError, DuplicateError,
            ValidationError, MissingFieldError, InvalidValueError,
            LPermissionError, AuthenticationError,
            ServiceError, DocumentError,
            TemplateNotFoundError, BuilderNotFoundError,
            NumberingError, BackupError,
            ConfigurationError,
        ]
        for err_cls in errs:
            assert issubclass(err_cls, LogiportError), f"{err_cls} must inherit LogiportError"

    def test_database_errors_chain(self):
        assert issubclass(NotFoundError, DatabaseError)
        assert issubclass(DuplicateError, DatabaseError)

    def test_validation_errors_chain(self):
        assert issubclass(MissingFieldError, ValidationError)
        assert issubclass(InvalidValueError, ValidationError)

    def test_permission_errors_chain(self):
        assert issubclass(AuthenticationError, LPermissionError)

    def test_service_errors_chain(self):
        assert issubclass(DocumentError, ServiceError)
        assert issubclass(NumberingError, ServiceError)
        assert issubclass(BackupError, ServiceError)
        assert issubclass(TemplateNotFoundError, DocumentError)
        assert issubclass(BuilderNotFoundError, DocumentError)


# ── LogiportError attributes ──────────────────────────────────────────────────

class TestLogiportError:

    def test_message_stored(self):
        e = LogiportError("test message")
        assert e.message == "test message"
        assert str(e) == "test message"

    def test_code_stored(self):
        e = LogiportError("msg", code="ERR_001")
        assert e.code == "ERR_001"

    def test_detail_stored(self):
        e = LogiportError("msg", detail="extra info")
        assert e.detail == "extra info"

    def test_str_with_detail(self):
        e = LogiportError("main message", detail="detail info")
        s = str(e)
        assert "main message" in s
        assert "detail info" in s

    def test_str_without_detail(self):
        e = LogiportError("only message")
        assert str(e) == "only message"

    def test_defaults(self):
        e = LogiportError()
        assert e.message == ""
        assert e.code == ""
        assert e.detail == ""


# ── catchable as parent ────────────────────────────────────────────────────────

class TestCatchability:

    def test_not_found_caught_as_database_error(self):
        with pytest.raises(DatabaseError):
            raise NotFoundError("record missing")

    def test_not_found_caught_as_logiport_error(self):
        with pytest.raises(LogiportError):
            raise NotFoundError("record missing")

    def test_missing_field_caught_as_validation_error(self):
        with pytest.raises(ValidationError):
            raise MissingFieldError("field required")

    def test_template_not_found_caught_as_document_error(self):
        with pytest.raises(DocumentError):
            raise TemplateNotFoundError("tmpl.html")

    def test_template_not_found_caught_as_service_error(self):
        with pytest.raises(ServiceError):
            raise TemplateNotFoundError("tmpl.html")

    def test_authentication_caught_as_permission_error(self):
        with pytest.raises(LPermissionError):
            raise AuthenticationError("invalid credentials")

    def test_all_caught_as_exception(self):
        with pytest.raises(Exception):
            raise BackupError("backup failed")


# ── concrete error types ───────────────────────────────────────────────────────

class TestConcreteErrors:

    def test_not_found_is_exception(self):
        e = NotFoundError("user 42 not found")
        assert isinstance(e, Exception)
        assert "user 42" in str(e)

    def test_duplicate_error(self):
        e = DuplicateError("duplicate key", code="DUP_KEY")
        assert e.code == "DUP_KEY"

    def test_missing_field(self):
        e = MissingFieldError("price is required", detail="field=price")
        assert "price is required" in str(e)

    def test_invalid_value(self):
        e = InvalidValueError("price must be > 0", code="INVALID_PRICE")
        assert e.code == "INVALID_PRICE"

    def test_template_not_found(self):
        e = TemplateNotFoundError("invoice.html not found")
        assert isinstance(e, DocumentError)
        assert isinstance(e, ServiceError)

    def test_builder_not_found(self):
        e = BuilderNotFoundError("no builder for doc_code")
        assert isinstance(e, DocumentError)

    def test_numbering_error(self):
        e = NumberingError("counter overflow")
        assert isinstance(e, ServiceError)

    def test_backup_error(self):
        e = BackupError("disk full")
        assert isinstance(e, ServiceError)

    def test_configuration_error(self):
        e = ConfigurationError("missing config key")
        assert isinstance(e, LogiportError)
