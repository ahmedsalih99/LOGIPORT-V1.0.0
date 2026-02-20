"""
exceptions.py
=============
LOGIPORT — Hierarchical Exception System

All application exceptions inherit from LogiportError so callers
can catch the full hierarchy with a single except clause when needed.

Structure
---------
LogiportError
├── DatabaseError
│   ├── NotFoundError
│   ├── DuplicateError
│   └── IntegrityError
├── ValidationError
│   ├── MissingFieldError
│   └── InvalidValueError
├── PermissionError
│   └── AuthenticationError
├── ServiceError
│   ├── DocumentError
│   │   ├── TemplateNotFoundError
│   │   └── BuilderNotFoundError
│   ├── NumberingError
│   └── BackupError
└── ConfigurationError
"""


# ─── Root ────────────────────────────────────────────────────────────────────

class LogiportError(Exception):
    """Base exception for all LOGIPORT errors."""

    def __init__(self, message: str = "", *, code: str = "", detail: str = ""):
        super().__init__(message)
        self.message = message
        self.code = code          # machine-readable code e.g. "TRX_NOT_FOUND"
        self.detail = detail      # extra context for logging

    def __str__(self) -> str:
        if self.detail:
            return f"{self.message} | {self.detail}"
        return self.message


# ─── Database ────────────────────────────────────────────────────────────────

class DatabaseError(LogiportError):
    """Raised when a database operation fails unexpectedly."""


class NotFoundError(DatabaseError):
    """Raised when a requested record does not exist in the database."""

    def __init__(self, entity: str = "", id_value=None, **kwargs):
        if entity and id_value is not None:
            message = f"{entity} with id={id_value} not found"
        elif entity:
            message = f"{entity} not found"
        else:
            message = kwargs.pop("message", "Record not found")
        super().__init__(message, **kwargs)
        self.entity = entity
        self.id_value = id_value


class DuplicateError(DatabaseError):
    """Raised when a unique constraint is violated."""

    def __init__(self, entity: str = "", field: str = "", value=None, **kwargs):
        if entity and field:
            message = f"{entity} with {field}={value!r} already exists"
        else:
            message = kwargs.pop("message", "Duplicate record")
        super().__init__(message, **kwargs)
        self.entity = entity
        self.field = field
        self.value = value


class IntegrityError(DatabaseError):
    """Raised when a foreign-key or other integrity constraint fails."""


# ─── Validation ──────────────────────────────────────────────────────────────

class ValidationError(LogiportError):
    """Raised when user-provided data fails validation."""

    def __init__(self, message: str = "", *, field: str = "", **kwargs):
        super().__init__(message, **kwargs)
        self.field = field


class MissingFieldError(ValidationError):
    """Raised when a required field is empty or None."""

    def __init__(self, field: str, **kwargs):
        super().__init__(f"Required field is missing: '{field}'", field=field, **kwargs)


class InvalidValueError(ValidationError):
    """Raised when a field value is out of range or has an invalid format."""

    def __init__(self, field: str, value=None, reason: str = "", **kwargs):
        msg = f"Invalid value for field '{field}'"
        if value is not None:
            msg += f": {value!r}"
        if reason:
            msg += f" — {reason}"
        super().__init__(msg, field=field, **kwargs)
        self.value = value
        self.reason = reason


# ─── Permission ──────────────────────────────────────────────────────────────

class PermissionError(LogiportError):
    """Raised when the current user lacks the required permission."""

    def __init__(self, permission_code: str = "", message: str = "", **kwargs):
        if not message:
            message = (
                f"Permission denied: '{permission_code}' required"
                if permission_code
                else "Permission denied"
            )
        super().__init__(message, **kwargs)
        self.permission_code = permission_code


class AuthenticationError(PermissionError):
    """Raised when login credentials are invalid."""

    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message=message, **kwargs)


# ─── Service ─────────────────────────────────────────────────────────────────

class ServiceError(LogiportError):
    """Base for errors raised by the service layer."""


class DocumentError(ServiceError):
    """Raised when document generation or rendering fails."""


class TemplateNotFoundError(DocumentError):
    """Raised when a Jinja2 template file cannot be located."""

    def __init__(self, doc_code: str = "", lang: str = "", **kwargs):
        msg = f"Template not found for doc_code='{doc_code}' lang='{lang}'"
        super().__init__(msg, **kwargs)
        self.doc_code = doc_code
        self.lang = lang


class BuilderNotFoundError(DocumentError):
    """Raised when no builder is registered for a given doc_code."""

    def __init__(self, doc_code: str = "", **kwargs):
        super().__init__(f"No builder registered for doc_code='{doc_code}'", **kwargs)
        self.doc_code = doc_code


class HtmlRenderError(DocumentError):
    """Raised when Jinja2 template rendering fails."""


class PdfRenderError(DocumentError):
    """Raised when PDF conversion (WeasyPrint / wkhtmltopdf) fails."""


class RuntimeDependencyError(DocumentError):
    """Raised when a required runtime library (Cairo, Pango, etc.) is missing."""


class NumberingError(ServiceError):
    """Raised when transaction or document numbering fails."""


class BackupError(ServiceError):
    """Raised when a backup operation fails."""


# ─── Configuration ───────────────────────────────────────────────────────────

class ConfigurationError(LogiportError):
    """Raised when the application configuration is invalid or incomplete."""


# ─── Backward-compat aliases (services/exceptions.py used these names) ───────
# Keep these so existing imports from services.exceptions still work
# (services/exceptions.py re-exports them too, but direct importers are safe)

ServicesError = ServiceError           # legacy alias