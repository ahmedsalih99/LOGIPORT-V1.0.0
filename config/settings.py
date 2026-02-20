"""
Settings Module - LOGIPORT
Central settings management for the application
"""
import logging

logger = logging.getLogger(__name__)

# Settings will be managed by core/settings_manager.py
# This file can be used for constants or default values

DEFAULT_SETTINGS = {

    "language": "ar",
    "theme": "light",
    "font_size": 12,
    "font_family": "Tajawal",
    "document_path": "documents/generated/",
    "documents_output_path": "",
    "backup_path": "backups/",
    "log_path": "logs/",
    "backup_interval_days": 7,
    "last_modified": "",
    "last_modified_by": "",
    "app_version": "1.0.0",
    "direction": "rtl",
    "documents_language": "ar"
}

logger.debug("Settings module loaded")