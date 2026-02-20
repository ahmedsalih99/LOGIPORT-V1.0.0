"""
services/exceptions.py
=======================
Re-exports service-layer exceptions from the root exceptions module.

Kept for backward compatibility — existing code that does:
    from services.exceptions import TemplateNotFound
will continue to work.
"""

from exceptions import (
    ServiceError       as ServicesError,      # legacy name
    ServiceError,
    DocumentError,
    TemplateNotFoundError,
    BuilderNotFoundError,
    HtmlRenderError,
    PdfRenderError,
    RuntimeDependencyError,
    NumberingError,
    BackupError,
)

# Legacy aliases used by older code (kept for backward compat)
TemplateNotFound = TemplateNotFoundError
BuilderNotFound  = BuilderNotFoundError

__all__ = [
    "ServicesError",
    "ServiceError",
    "DocumentError",
    "TemplateNotFound",
    "TemplateNotFoundError",
    "BuilderNotFound",
    "BuilderNotFoundError",
    "HtmlRenderError",
    "PdfRenderError",
    "RuntimeDependencyError",
    "NumberingError",
    "BackupError",
]