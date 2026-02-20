"""
LOGIPORT – Production PDF Renderer

Primary engine:
    - Playwright (Chromium headless)

Fallback:
    - WeasyPrint (only if full stack available)

Design goals:
    - Stable on Windows
    - Cross-platform (Linux ready)
    - Minimal complexity
    - Clear failure behavior
"""

from __future__ import annotations

import os
import re
import traceback
from pathlib import Path
from typing import Optional, Dict, Tuple


# ---------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------

def _safe_import(name: str):
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


# ---------------------------------------------------------------------
# Engine Detection
# ---------------------------------------------------------------------

def _has_weasyprint_stack() -> bool:
    weasy = _safe_import("weasyprint")
    cairo = _safe_import("cairocffi") or _safe_import("cairo")
    return weasy and cairo


def detect_engines() -> Dict[str, bool]:
    return {
        "playwright": _safe_import("playwright"),
        "weasyprint_stack": _has_weasyprint_stack(),
    }


# ---------------------------------------------------------------------
# Playwright (Primary)
# ---------------------------------------------------------------------

def _try_playwright(html: str, out_path: str, base_url: Optional[str]) -> Tuple[bool, Dict]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        return False, {"engine": "playwright", "error": f"Not installed: {e}"}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox"]
            )

            page = browser.new_page()

            html2 = _inject_base_tag(html, base_url)
            page.set_content(html2, wait_until="load")

            page.pdf(
                path=out_path,
                format="A4",
                print_background=True,
            )

            browser.close()

        return True, {"engine": "playwright"}

    except Exception as e:
        return False, {
            "engine": "playwright",
            "error": f"{type(e).__name__}: {e}",
            "trace": traceback.format_exc(),
        }


# ---------------------------------------------------------------------
# WeasyPrint (Fallback)
# ---------------------------------------------------------------------

def _try_weasyprint(html: str, out_path: str, base_url: Optional[str]) -> Tuple[bool, Dict]:
    if not _has_weasyprint_stack():
        return False, {"engine": "weasyprint", "error": "Stack incomplete"}

    try:
        from weasyprint import HTML
        HTML(string=html, base_url=base_url).write_pdf(out_path)
        return True, {"engine": "weasyprint"}
    except Exception as e:
        return False, {
            "engine": "weasyprint",
            "error": f"{type(e).__name__}: {e}",
            "trace": traceback.format_exc(),
        }


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------

def render_html_to_pdf(
    html: str,
    out_path: str,
    base_url: Optional[str] = None,
    prefer: Optional[str] = "playwright",
) -> Tuple[bool, Dict]:
    """
    Render HTML to PDF using:
        1) Playwright (default)
        2) WeasyPrint (fallback)

    Returns:
        (ok: bool, info: dict)
    """

    assert isinstance(html, str) and html.strip(), "HTML must be non-empty string"

    out_dir = os.path.dirname(os.path.abspath(out_path)) or "."
    os.makedirs(out_dir, exist_ok=True)

    engines = detect_engines()

    attempts = []

    # Determine order
    order = []

    if prefer == "playwright":
        order = ["playwright", "weasyprint"]
    elif prefer == "weasyprint":
        order = ["weasyprint", "playwright"]
    else:
        order = ["playwright", "weasyprint"]

    for engine in order:

        if engine == "playwright" and engines["playwright"]:
            ok, info = _try_playwright(html, out_path, base_url)

        elif engine == "weasyprint" and engines["weasyprint_stack"]:
            ok, info = _try_weasyprint(html, out_path, base_url)

        else:
            continue

        attempts.append(info)

        if ok:
            return True, {
                "engine": info.get("engine"),
                "path": os.path.abspath(out_path),
                "attempts": attempts,
            }

    return False, {
        "error": "No available PDF engine succeeded",
        "path": os.path.abspath(out_path),
        "attempts": attempts,
    }
