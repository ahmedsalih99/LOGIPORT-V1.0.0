"""
hooks/runtime_i18n.py — LOGIPORT
==================================
Runtime hook يُعالج مشكلة pkgutil.iter_modules داخل PyInstaller EXE.

المشكلة:
    TranslationManager._discover_languages() يستخدم pkgutil.iter_modules
    لاكتشاف اللغات في core.i18n — هذا لا يعمل داخل الـ EXE لأن الـ modules
    مضغوطة في archive.

الحل:
    نُعرّف قائمة اللغات مسبقاً عبر environment variable.
"""

import os
import sys

if getattr(sys, 'frozen', False):
    # داخل EXE — نُعرّف اللغات يدوياً
    os.environ.setdefault('LOGIPORT_LANGUAGES', 'ar,en,tr')