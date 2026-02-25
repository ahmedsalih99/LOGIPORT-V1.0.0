import logging
import importlib
import pkgutil
from typing import Dict, Optional, Set
from PySide6.QtCore import QObject, Signal
from core.singleton import QObjectSingletonMixin

logger = logging.getLogger(__name__)

DEFAULT_LANGUAGE = "ar"


class TranslationManager(QObject, QObjectSingletonMixin):

    language_changed = Signal()

    def __init__(self):
        super().__init__()
        self._current_language = DEFAULT_LANGUAGE
        self._translations: Dict[str, str] = {}
        self._loading = False
        self._supported_languages = self._discover_languages()
        self._load_translations()

    # ==============================
    # Public API
    # ==============================

    def set_language(self, language_code: str) -> bool:
        if not language_code:
            return False

        lang = language_code.strip().lower()

        if lang not in self._supported_languages:
            logger.warning(f"Unsupported language: {lang}")
            return False

        if lang == self._current_language:
            return True

        old_lang = self._current_language
        self._current_language = lang

        if not self._load_translations():
            self._current_language = old_lang
            return False

        self.language_changed.emit()
        logger.info(f"Language changed to {lang}")
        return True

    def translate(self, key: str, fallback: Optional[str] = None) -> str:
        if not key:
            return fallback or ""

        value = self._translations.get(key)

        if value is not None:
            return value

        logger.debug(f"Missing translation key: {key}")
        return fallback if fallback is not None else key

    def get_current_language(self) -> str:
        return self._current_language

    def get_supported_languages(self) -> Set[str]:
        return self._supported_languages.copy()

    def reload_translations(self) -> bool:
        return self._load_translations()

    # ==============================
    # Internal Logic
    # ==============================

    def _discover_languages(self) -> Set[str]:
        """
        Automatically discover available languages inside core.i18n package.
        Inside a PyInstaller EXE, pkgutil.iter_modules doesn't work —
        we fall back to LOGIPORT_LANGUAGES env var set by runtime_i18n.py hook.
        """
        import os, sys

        # PyInstaller EXE — runtime hook sets this
        if getattr(sys, 'frozen', False):
            env_langs = os.environ.get('LOGIPORT_LANGUAGES', 'ar,en,tr')
            languages = {lang.strip() for lang in env_langs.split(',') if lang.strip()}
            logger.info(f"Languages (frozen): {languages}")
            return languages

        # Normal Python — discover dynamically
        try:
            import core.i18n

            languages = set()
            for module in pkgutil.iter_modules(core.i18n.__path__):
                languages.add(module.name)

            logger.info(f"Discovered languages: {languages}")
            return languages

        except Exception as e:
            logger.error(f"Language discovery failed: {e}")
            return {DEFAULT_LANGUAGE}

    def _load_translations(self) -> bool:
        if self._loading:
            return False

        self._loading = True

        try:
            module_path = f"core.i18n.{self._current_language}"
            module = importlib.import_module(module_path)

            if not hasattr(module, "translations"):
                logger.error(f"{module_path} has no 'translations' dict")
                self._translations = {}
                return False

            translations = getattr(module, "translations")

            if not isinstance(translations, dict):
                logger.error(f"'translations' in {module_path} must be dict")
                self._translations = {}
                return False

            self._translations = translations
            logger.info(
                f"Loaded {len(translations)} translations "
                f"for {self._current_language}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to load translations "
                f"for {self._current_language}: {e}",
                exc_info=True
            )
            self._translations = {}
            return False

        finally:
            self._loading = False


# ==============================
# Convenience wrappers
# ==============================

def get_translation_manager() -> TranslationManager:
    return TranslationManager.get_instance()


def translate(key: str, fallback: Optional[str] = None) -> str:
    return TranslationManager.get_instance().translate(key, fallback)


def set_language(language_code: str) -> bool:
    return TranslationManager.get_instance().set_language(language_code)


def get_current_language() -> str:
    return TranslationManager.get_instance().get_current_language()


def t(key: str, fallback: Optional[str] = None) -> str:
    return translate(key, fallback)