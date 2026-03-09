# hooks/runtime_i18n.py
# ========================
# PyInstaller runtime hook for LOGIPORT i18n
#
# Inside a frozen EXE, pkgutil.iter_modules() cannot discover
# core.i18n sub-modules automatically.
# This hook sets LOGIPORT_LANGUAGES so TranslationManager
# knows which languages are available without dynamic discovery.

import os

os.environ.setdefault("LOGIPORT_LANGUAGES", "ar,en,tr")