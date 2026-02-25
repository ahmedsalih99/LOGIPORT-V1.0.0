"""
ui/utils/svg_icons.py
======================
SVG Icon helper — يحوّل SVG paths إلى QIcon ملوّنة تتكيف مع الـ theme.

يعمل بطريقتين:
- إذا PySide6.QtSvg متوفر: يرسم SVG مباشرة
- إذا غير متوفر: يرسم أيقونة نصية بديلة بـ QPainter

الاستخدام:
    from ui.utils.svg_icons import set_icon, refresh_icons
    set_icon(btn, "search")          # يضبط الأيقونة + الحجم
    refresh_icons(topbar)            # يعيد رسم كل الأيقونات
"""
from __future__ import annotations
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PySide6.QtCore import Qt, QSize, QByteArray, QRect

# محاولة استيراد QtSvg
try:
    from PySide6.QtSvg import QSvgRenderer
    _SVG_AVAILABLE = True
except ImportError:
    _SVG_AVAILABLE = False


# ─── SVG paths (24×24 viewBox — Heroicons/Lucide style) ───────────────────

_ICONS: dict[str, str] = {
    "settings": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="3"/>
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
    </svg>""",

    "language": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <line x1="2" y1="12" x2="22" y2="12"/>
        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
    </svg>""",

    "theme": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="5"/>
        <line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
        <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
    </svg>""",

    "info": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
    </svg>""",

    "search": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="11" cy="11" r="8"/>
        <line x1="21" y1="21" x2="16.65" y2="16.65"/>
    </svg>""",

    "logout": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
        <polyline points="16 17 21 12 16 7"/>
        <line x1="21" y1="12" x2="9" y2="12"/>
    </svg>""",

    "user": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
        <circle cx="12" cy="7" r="4"/>
    </svg>""",

    # ─── Sidebar icons ────────────────────────────────────────────────────────

    "dashboard": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="3" width="7" height="7" rx="1"/>
        <rect x="14" y="3" width="7" height="7" rx="1"/>
        <rect x="3" y="14" width="7" height="7" rx="1"/>
        <rect x="14" y="14" width="7" height="7" rx="1"/>
    </svg>""",

    "materials": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
        <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
        <line x1="12" y1="22.08" x2="12" y2="12"/>
    </svg>""",

    "clients": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
        <circle cx="9" cy="7" r="4"/>
        <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
        <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
    </svg>""",

    "companies": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
        <polyline points="9 22 9 12 15 12 15 22"/>
    </svg>""",

    "pricing": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <line x1="12" y1="1" x2="12" y2="23"/>
        <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
    </svg>""",

    "entries": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
        <line x1="12" y1="18" x2="12" y2="12"/>
        <line x1="9" y1="15" x2="15" y2="15"/>
    </svg>""",

    "transactions": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <rect x="2" y="7" width="20" height="14" rx="2"/>
        <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/>
        <line x1="12" y1="12" x2="12" y2="16"/>
        <line x1="10" y1="14" x2="14" y2="14"/>
    </svg>""",

    "documents": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
        <line x1="16" y1="13" x2="8" y2="13"/>
        <line x1="16" y1="17" x2="8" y2="17"/>
        <polyline points="10 9 9 9 8 9"/>
    </svg>""",

    "values": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <line x1="8" y1="6" x2="21" y2="6"/>
        <line x1="8" y1="12" x2="21" y2="12"/>
        <line x1="8" y1="18" x2="21" y2="18"/>
        <line x1="3" y1="6" x2="3.01" y2="6"/>
        <line x1="3" y1="12" x2="3.01" y2="12"/>
        <line x1="3" y1="18" x2="3.01" y2="18"/>
    </svg>""",

    "audit_trail": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
        <polyline points="9 12 11 14 15 10"/>
    </svg>""",

    "control_panel": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 20h9"/>
        <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
    </svg>""",

    "users_permissions": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
        <circle cx="12" cy="7" r="4"/>
        <circle cx="19" cy="8" r="3" fill="{color}" stroke="none"/>
        <line x1="19" y1="6.5" x2="19" y2="9.5" stroke="{bg}" stroke-width="1.5"/>
        <line x1="17.5" y1="8" x2="20.5" y2="8" stroke="{bg}" stroke-width="1.5"/>
    </svg>""",

    "menu_burger": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="3" y1="6" x2="21" y2="6"/>
        <line x1="3" y1="12" x2="21" y2="12"/>
        <line x1="3" y1="18" x2="21" y2="18"/>
    </svg>""",
}

# fallback text للـ SVG إذا QtSvg غير متوفر
_FALLBACK_TEXT: dict[str, str] = {
    "settings": "⚙",
    "language": "⊕",
    "theme":    "◑",
    "info":     "i",
    "search":   "⌕",
    "logout":   "→",
    "user":     "◉",
}


def _get_icon_color() -> str:
    """يأخذ لون text_primary من الـ theme الحالي."""
    try:
        from core.theme_manager import ThemeManager
        from config.themes.semantic_colors import SemanticColors
        theme_name = ThemeManager.get_instance().get_current_theme()
        colors = SemanticColors.get(theme_name)
        return colors.get("text_primary", "#374151")
    except Exception:
        return "#374151"


def get_icon(name: str, size: int = 18, color: str | None = None) -> QIcon:
    """يُعيد QIcon من SVG path ملوّن بـ text_primary."""
    icon_color = color or _get_icon_color()

    if _SVG_AVAILABLE:
        return _icon_from_svg(name, size, icon_color)
    else:
        return _icon_from_text(name, size, icon_color)


def _icon_from_svg(name: str, size: int, color: str) -> QIcon:
    """يرسم الأيقونة من SVG."""
    svg_template = _ICONS.get(name, "")
    if not svg_template:
        return QIcon()

    svg_data = svg_template.replace("{color}", color)
    svg_bytes = QByteArray(svg_data.encode("utf-8"))

    renderer = QSvgRenderer(svg_bytes)
    if not renderer.isValid():
        return _icon_from_text(name, size, color)

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


def _icon_from_text(name: str, size: int, color: str) -> QIcon:
    """fallback: يرسم حرف/رمز كـ QIcon."""
    text = _FALLBACK_TEXT.get(name, "?")
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QColor(color))
    font = QFont("Segoe UI", int(size * 0.6), QFont.Bold)
    painter.setFont(font)
    painter.drawText(QRect(0, 0, size, size), Qt.AlignCenter, text)
    painter.end()
    return QIcon(pixmap)


def set_icon(btn, name: str, size: int = 18):
    """يضبط أيقونة SVG على زر مع الحجم المناسب."""
    btn.setIcon(get_icon(name, size))
    btn.setIconSize(QSize(size, size))


def refresh_icons(topbar) -> None:
    """يُعيد رسم كل أيقونات الـ topbar — استدعِها عند تغيير الـ theme."""
    icon_map = {
        "settings_btn": ("settings", 17),
        "lang_btn":     ("language", 17),
        "theme_btn":    ("theme",    17),
        "about_btn":    ("info",     17),
        "search_btn":   ("search",   17),
        "logout_btn":   ("logout",   17),
        "user_btn":     ("user",     16),
    }
    for attr, (icon_name, sz) in icon_map.items():
        btn = getattr(topbar, attr, None)
        if btn:
            set_icon(btn, icon_name, sz)


def get_sidebar_icon(key: str, size: int = 20, color: str | None = None) -> QIcon:
    """يُعيد QIcon لزر السايدبار حسب مفتاح التبويب."""
    return get_icon(key, size, color)


def refresh_sidebar_icons(sidebar) -> None:
    """يُعيد رسم أيقونات السايدبار بالألوان الجديدة — استدعِها عند تغيير الـ theme."""
    if not hasattr(sidebar, "buttons"):
        return
    color = _get_icon_color()
    btn_height = max(32, getattr(sidebar, "expanded_width", 210) * 16 // 100)
    icon_size = max(18, int(btn_height * 0.6))
    for key, btn in sidebar.buttons.items():
        icon = get_icon(key, icon_size, color)
        if not icon.isNull():
            btn.setIcon(icon)
            btn.setIconSize(QSize(icon_size, icon_size))
    # toggle button
    toggle = getattr(sidebar, "toggle_btn", None)
    if toggle:
        toggle_size = max(20, int(getattr(sidebar, "expanded_width", 210) * 0.19 * 0.6))
        icon = get_icon("menu_burger", toggle_size, color)
        if not icon.isNull():
            toggle.setIcon(icon)
            toggle.setIconSize(QSize(toggle_size, toggle_size))