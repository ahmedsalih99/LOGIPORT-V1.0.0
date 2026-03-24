"""
Theme Builder - LOGIPORT v3.0 ENHANCED
========================================

Enhanced with gradient backgrounds and new components.
"""

from .palettes import ColorPalette
from .semantic_colors import SemanticColors
from .typography import Typography
from .components import (
    buttons, forms, tables, dialogs, tabs,
    topbar, sidebar, cards, misc,
    transaction_styles,
    details_view,           # ← BaseDetailsView object names
    dashboard_profile,      # ← Dashboard / UserProfile / Notifications
)


class ThemeBuilder:
    """
    Build complete theme with RTL support and modern effects.

    Usage:
        >>> theme = ThemeBuilder("light", font_size=13, font_family="Tajawal")
        >>> stylesheet = theme.build()
        >>> app.setStyleSheet(stylesheet)
    """

    def __init__(
        self,
        theme_name: str = "light",
        font_size: int = 12,
        font_family: str = "Tajawal",
        rtl: bool = True
    ):
        """
        Initialize theme builder.

        Args:
            theme_name: 'light' or 'dark'
            font_size: Base font size in pixels
            font_family: Font family name
            rtl: Enable RTL support (default: True for Arabic)
        """
        self.theme_name = theme_name
        self.font_size = font_size
        self.font_family = font_family
        self.rtl = rtl

        # Get colors and typography
        self.colors = SemanticColors.get(theme_name)
        self.sizes = Typography.scale(font_size)
        self.palette = ColorPalette.get(theme_name)

    def build(self) -> str:
        """Build complete stylesheet with RTL support"""

        # Base styles (includes RTL)
        base_styles = self._get_base_styles()

        # Component styles
        component_styles = [
            buttons.get_styles(self),
            forms.get_styles(self),
            tables.get_styles(self),
            dialogs.get_styles(self),
            tabs.get_styles(self),
            topbar.get_styles(self),
            sidebar.get_styles(self),
            cards.get_styles(self),
            transaction_styles.get_styles(self),
            details_view.get_styles(self),      # ← BaseDetailsView styles
            dashboard_profile.get_styles(self), # ← Dashboard / Profile / Notifications
            misc.get_styles(self),              # misc آخر دايماً (scrollbar overrides)
        ]

        # Additional RTL fixes
        rtl_fixes = self._get_rtl_fixes() if self.rtl else ""

        # Final overrides — applied LAST to beat all component styles
        final_overrides = self._get_final_overrides()

        # Combine all
        parts = [base_styles, *component_styles]
        if rtl_fixes:
            parts.append(rtl_fixes)
        parts.append(final_overrides)

        return "\n\n".join(parts)

    def _get_final_overrides(self) -> str:
        """Overrides applied last — highest effective priority."""
        c = self.colors
        s = self.sizes
        return f"""
        /* ═══════════════════════════════════════════════════════════
           FINAL OVERRIDES — These run last and beat everything above
        ═══════════════════════════════════════════════════════════ */

        /* Selection Action Bar — force white on all children */
        QFrame#selection-action-bar,
        QFrame#selection-action-bar * {{
            color: #FFFFFF;
        }}
        QFrame#selection-action-bar {{
            background   : {c["primary"]};
            border       : none;
            border-radius: 8px;
        }}
        QFrame#selection-action-bar QLabel {{
            background: transparent;
            color     : #FFFFFF;
            font-weight: 600;
        }}
        QFrame#selection-action-bar QPushButton {{
            background   : rgba(255,255,255,0.15);
            color        : #FFFFFF;
            border       : 1px solid rgba(255,255,255,0.35);
            border-radius: 6px;
            padding      : 3px 12px;
            font-size    : {s["sm"]}px;
            font-weight  : 600;
        }}
        QFrame#selection-action-bar QPushButton:hover {{
            background  : rgba(255,255,255,0.28);
            border-color: rgba(255,255,255,0.6);
            color       : #FFFFFF;
        }}
        QFrame#selection-action-bar QPushButton:pressed {{
            background: rgba(255,255,255,0.38);
            color     : #FFFFFF;
        }}
        QFrame#selection-action-bar QPushButton#danger-btn {{
            background  : rgba(220,38,38,0.8);
            border-color: rgba(220,38,38,1.0);
            color       : #FFFFFF;
        }}
        QFrame#selection-action-bar QPushButton#danger-btn:hover {{
            background: rgba(220,38,38,1.0);
            color     : #FFFFFF;
        }}

        /* secondary-btn — visible gray background, not transparent */
        QPushButton#secondary-btn {{
            background   : {c["bg_disabled"]};
            color        : {c["text_secondary"]};
            border       : 1px solid {c["border"]};
        }}
        QPushButton#secondary-btn:hover {{
            background  : {c["bg_hover"]};
            color       : {c["primary"]};
            border-color: {c["primary"]};
        }}
        QPushButton#secondary-btn:pressed {{
            background: {c["bg_active"]};
            color     : {c["primary"]};
        }}

        /* Nav pill buttons — force text color explicitly */
        QToolButton#pill-tab-btn {{
            color    : {c["text_secondary"]};
            font-size: 9px;
        }}
        QToolButton#pill-tab-btn:hover {{
            color: {c["text_primary"]};
        }}
        QToolButton#pill-tab-btn:checked {{
            color: #FFFFFF;
        }}
        """

    def _get_base_styles(self) -> str:
        """Generate base application styles with RTL support and gradients"""
        c = self.colors
        s = self.sizes

        return f"""
        /* ========== BASE STYLES WITH GRADIENTS ========== */
        
        * {{
        }}
        
        QWidget {{
            background-color: {c["bg_main"]};
            color: {c["text_primary"]};
            font-size: {s["base"]}px;
            font-family: '{self.font_family}', 'Montserrat', 'Cairo', Arial, sans-serif;
        }}
        
        QMainWindow {{
            background: qlineargradient(
                x1: 0, y1: 0, x2: 1, y2: 1,
                stop: 0 {c["bg_main_gradient_start"]},
                stop: 0.5 {c["bg_main"]},
                stop: 1 {c["bg_main_gradient_end"]}
            );
        }}
        
        QWidget#main_widget {{
            background: qlineargradient(
                x1: 0, y1: 0, x2: 1, y2: 1,
                stop: 0 {c["bg_main"]},
                stop: 1 {c["bg_elevated"]}
            );
        }}
        
        QLabel {{
            color: {c["text_primary"]};
            background: transparent;
        }}
        
        QLabel#title {{
            font-size: {s["2xl"]}px;
            font-weight: 700;
            color: {c["text_primary"]};
        }}
        
        QLabel#subtitle {{
            font-size: {s["lg"]}px;
            font-weight: 600;
            color: {c["text_secondary"]};
        }}
        
        QLabel#muted {{
            color: {c["text_muted"]};
            font-size: {s["sm"]}px;
        }}
        
        /* Scrollbars - Basic (detailed in misc.py) */
        QScrollBar:vertical {{
            background: {c["bg_main"]};
            width: 12px;
            border: none;
        }}
        
        QScrollBar::handle:vertical {{
            background: {c["border_hover"]};
            border-radius: 6px;
            min-height: 30px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background: {c["text_muted"]};
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        
        QScrollBar:horizontal {{
            background: {c["bg_main"]};
            height: 12px;
            border: none;
        }}
        
        QScrollBar::handle:horizontal {{
            background: {c["border_hover"]};
            border-radius: 6px;
            min-width: 30px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background: {c["text_muted"]};
        }}
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
        """

    def _get_rtl_fixes(self) -> str:
        """Additional RTL-specific fixes (visual/alignment only — no qproperty-layoutDirection)"""
        c = self.colors

        return f"""
        /* ========== RTL SPECIFIC FIXES ========== */
        
        /* ComboBox - Arrow on left */
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: left center;
            width: 25px;
            border: none;
        }}
        
        QComboBox::down-arrow {{
            image: none;
            width: 0;
            height: 0;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid {c["text_secondary"]};
            margin-left: 8px;
        }}
        
        /* SpinBox - Buttons on left */
        QSpinBox::up-button, QDoubleSpinBox::up-button {{
            subcontrol-origin: border;
            subcontrol-position: left top;
            width: 18px;
            border-left: 1px solid {c["border"]};
            background: {c["bg_hover"]};
        }}
        
        QSpinBox::down-button, QDoubleSpinBox::down-button {{
            subcontrol-origin: border;
            subcontrol-position: left bottom;
            width: 18px;
            border-left: 1px solid {c["border"]};
            border-top: 1px solid {c["border"]};
            background: {c["bg_hover"]};
        }}
        
        QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
        QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
            background: {c["bg_active"]};
        }}
        
        QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
            image: none;
            width: 0;
            height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-bottom: 5px solid {c["text_secondary"]};
        }}
        
        QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
            image: none;
            width: 0;
            height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid {c["text_secondary"]};
        }}
        
        /* Tables - header alignment */
        QTableWidget::item, QTableView::item {{
            padding-right: 8px;
            padding-left: 8px;
        }}
        
        QHeaderView::section {{
            padding-right: 10px;
            padding-left: 10px;
        }}
        
        /* Lists/Trees alignment */
        QListWidget::item, QListView::item {{
            padding-right: 8px;
            padding-left: 8px;
        }}
        
        QTreeWidget::item, QTreeView::item {{
            padding-right: 4px;
            padding-left: 20px;
        }}
        
        /* Tabs */
        QTabBar::tab {{
            margin-left: 2px;
            margin-right: 0px;
        }}
        
        QTabBar::tab:first {{
            margin-left: 0px;
        }}
        
        /* Menus - Right aligned (RTL) */
        QMenu::item {{
            padding-right: 16px;
            padding-left : 20px;
            text-align   : right;
        }}

        QMenu::indicator {{
            left : auto;
            right: 8px;
        }}
        
        /* CheckBox & RadioButton - Indicator spacing */
        QCheckBox::indicator, QRadioButton::indicator {{
            margin-right: 0px;
            margin-left: 8px;
        }}
        """