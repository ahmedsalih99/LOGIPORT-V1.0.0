"""
LOGIPORT – PDF Renderer
========================
Primary engine : PySide6 QtWebEngine  (printToPdf)
Fallback        : WeasyPrint

Thread safety:
  QWebEnginePage.printToPdf MUST run on the main Qt thread.
  render_html_to_pdf() detects whether it is on the main thread:
    - Main thread  → renders directly via QEventLoop
    - Worker thread → dispatches to main thread via QMetaObject (blocking)
"""

from __future__ import annotations

import logging
import os
import re
import traceback
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────

def _safe_import(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False


def _ensure_file_url(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    if re.match(r"^[a-zA-Z]+://", path):
        return path.rstrip("/")
    try:
        return Path(path).resolve().as_uri().rstrip("/")
    except Exception:
        return path.rstrip("/")


def _inject_base_tag(html: str, base_url: Optional[str]) -> str:
    if not base_url:
        return html
    href = _ensure_file_url(base_url)
    if not href:
        return html
    base_tag = f'<base href="{href}/">'
    m = re.search(r"<head[^>]*>", html, re.IGNORECASE)
    if m:
        i = m.end()
        return html[:i] + base_tag + "\n" + html[i:]
    return "<!doctype html><html><head>" + base_tag + "</head><body>" + html + "</body></html>"


# ─────────────────────────────────────────────────────────────────────────────
# Engine Detection
# ─────────────────────────────────────────────────────────────────────────────

def _has_qtwebengine() -> bool:
    try:
        from PySide6.QtWebEngineCore import QWebEnginePage  # noqa
        return True
    except Exception:
        return False


def _has_weasyprint_stack() -> bool:
    return _safe_import("weasyprint") and (
        _safe_import("cairocffi") or _safe_import("cairo")
    )


def _get_qapp():
    try:
        from PySide6.QtWidgets import QApplication
        return QApplication.instance()
    except Exception:
        return None


def _is_main_thread() -> bool:
    try:
        from PySide6.QtCore import QThread, QCoreApplication
        app = QCoreApplication.instance()
        if not app:
            return False
        return QThread.currentThread() is app.thread()
    except Exception:
        return False


def detect_engines() -> Dict[str, bool]:
    return {
        "qtwebengine":      _has_qtwebengine(),
        "weasyprint_stack": _has_weasyprint_stack(),
        "playwright":       False,   # removed — kept for backward compat
    }


# ─────────────────────────────────────────────────────────────────────────────
# QtWebEngine — core render (must be called from main thread)
# ─────────────────────────────────────────────────────────────────────────────

def _qtwebengine_on_main_thread(
    html: str,
    out_path: str,
    base_url: Optional[str],
) -> Tuple[bool, Dict]:
    """Direct render — call ONLY from main thread."""
    try:
        from PySide6.QtCore import QEventLoop, QMarginsF, QUrl
        from PySide6.QtGui import QPageLayout, QPageSize
        from PySide6.QtWebEngineCore import QWebEnginePage

        html_with_base = _inject_base_tag(html, base_url)

        page_layout = QPageLayout(
            QPageSize(QPageSize.PageSizeId.A4),
            QPageLayout.Orientation.Portrait,
            QMarginsF(10.0, 10.0, 10.0, 10.0),
            QPageLayout.Unit.Millimeter,
        )

        loop     = QEventLoop()
        result   = {"ok": False, "error": ""}
        web_page = QWebEnginePage()

        def _on_load(ok: bool):
            if not ok:
                result["error"] = "Page failed to load"
                loop.quit()
                return

            def _on_pdf_done(pdf_path: str):
                result["ok"] = bool(pdf_path)
                if not pdf_path:
                    result["error"] = "printToPdf returned empty path"
                loop.quit()

            web_page.pdfPrintingFinished.connect(_on_pdf_done)
            web_page.printToPdf(out_path, page_layout)

        web_page.loadFinished.connect(_on_load)

        if base_url:
            base_qurl = QUrl.fromLocalFile(str(Path(base_url).resolve()) + "/")
            web_page.setHtml(html_with_base, base_qurl)
        else:
            web_page.setHtml(html_with_base)

        loop.exec()
        web_page.deleteLater()

        if result["ok"]:
            return True, {"engine": "qtwebengine"}
        return False, {"engine": "qtwebengine", "error": result["error"]}

    except Exception as e:
        return False, {
            "engine": "qtwebengine",
            "error":  f"{type(e).__name__}: {e}",
            "trace":  traceback.format_exc(),
        }


# ─────────────────────────────────────────────────────────────────────────────
# QtWebEngine — thread-safe wrapper
# ─────────────────────────────────────────────────────────────────────────────

def _try_qtwebengine(
    html: str,
    out_path: str,
    base_url: Optional[str],
) -> Tuple[bool, Dict]:
    """
    Thread-safe entry point.
    - If called from main thread: renders directly.
    - If called from worker thread: dispatches to main thread via
      QMetaObject.invokeMethod (BlockingQueuedConnection) and waits.
    """
    if not _has_qtwebengine():
        return False, {"engine": "qtwebengine", "error": "QtWebEngineCore not available"}

    if not _get_qapp():
        return False, {"engine": "qtwebengine", "error": "No QApplication instance"}

    if _is_main_thread():
        return _qtwebengine_on_main_thread(html, out_path, base_url)

    # ── Worker thread path: dispatch to main thread and wait ──────────────
    try:
        from PySide6.QtCore import QMetaObject, Qt, QObject, Signal, Slot
        import threading

        event   = threading.Event()
        outcome = {}

        class _Dispatcher(QObject):
            trigger = Signal(str, str, str)   # html, out_path, base_url

            def __init__(self):
                super().__init__()
                # Move to main thread so slot runs there
                app = _get_qapp()
                if app:
                    self.moveToThread(app.thread())
                self.trigger.connect(self._do_render, Qt.ConnectionType.QueuedConnection)

            @Slot(str, str, str)
            def _do_render(self, h: str, p: str, b: str):
                ok, info = _qtwebengine_on_main_thread(h, p, b or None)
                outcome["ok"]   = ok
                outcome["info"] = info
                event.set()

        dispatcher = _Dispatcher()
        dispatcher.trigger.emit(html, out_path, base_url or "")
        event.wait(timeout=60)   # 60s max
        dispatcher.deleteLater()

        if not outcome:
            return False, {"engine": "qtwebengine", "error": "Render timed out (60s)"}

        return outcome["ok"], outcome["info"]

    except Exception as e:
        return False, {
            "engine": "qtwebengine",
            "error":  f"Dispatch failed: {type(e).__name__}: {e}",
            "trace":  traceback.format_exc(),
        }


# ─────────────────────────────────────────────────────────────────────────────
# WeasyPrint (Fallback)
# ─────────────────────────────────────────────────────────────────────────────

def _try_weasyprint(
    html: str,
    out_path: str,
    base_url: Optional[str],
) -> Tuple[bool, Dict]:
    if not _has_weasyprint_stack():
        return False, {"engine": "weasyprint", "error": "Stack incomplete"}
    try:
        from weasyprint import HTML
        HTML(string=html, base_url=base_url).write_pdf(out_path)
        return True, {"engine": "weasyprint"}
    except Exception as e:
        return False, {
            "engine": "weasyprint",
            "error":  f"{type(e).__name__}: {e}",
            "trace":  traceback.format_exc(),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def render_html_to_pdf(
    html: str,
    out_path: str,
    base_url: Optional[str] = None,
    prefer: Optional[str] = "qtwebengine",
) -> Tuple[bool, Dict]:
    """
    Render HTML to PDF. Thread-safe — can be called from any thread.

    Engine order:
        1. QtWebEngine (dispatches to main thread if needed)
        2. WeasyPrint  (fallback)

    Returns: (ok: bool, info: dict)
    """
    assert isinstance(html, str) and html.strip(), "HTML must be non-empty"

    out_dir = os.path.dirname(os.path.abspath(out_path)) or "."
    os.makedirs(out_dir, exist_ok=True)

    engines  = detect_engines()
    attempts = []

    order = (
        ["qtwebengine", "weasyprint"]
        if prefer != "weasyprint"
        else ["weasyprint", "qtwebengine"]
    )

    for engine in order:
        if engine == "qtwebengine" and engines["qtwebengine"]:
            ok, info = _try_qtwebengine(html, out_path, base_url)
        elif engine == "weasyprint" and engines["weasyprint_stack"]:
            ok, info = _try_weasyprint(html, out_path, base_url)
        else:
            continue

        attempts.append(info)

        if ok:
            logger.info(f"PDF rendered via {info['engine']}: {out_path}")
            return True, {
                "engine":   info["engine"],
                "path":     os.path.abspath(out_path),
                "attempts": attempts,
            }

        logger.warning(f"Engine '{engine}' failed: {info.get('error')}")

    logger.error(f"All PDF engines failed: {out_path}")
    return False, {
        "error":    "No available PDF engine succeeded",
        "path":     os.path.abspath(out_path),
        "attempts": attempts,
    }