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

        # Combine all
        parts = [base_styles, *component_styles]
        if rtl_fixes:
            parts.append(rtl_fixes)

        return "\n\n".join(parts)

    def _get_base_styles(self) -> str:
        """Generate base application styles with RTL support and gradients"""
        c = self.colors
        s = self.sizes

        # RTL direction setting
        rtl_direction = "qproperty-layoutDirection: RightToLeft;" if self.rtl else ""

        return f"""
        /* ========== BASE STYLES WITH RTL & GRADIENTS ========== */
        
        * {{
            {rtl_direction}
        }}
        
        QWidget {{
            background-color: {c["bg_main"]};
            color: {c["text_primary"]};
            font-size: {s["base"]}px;
            font-family: '{self.font_family}', 'Montserrat', 'Cairo', Arial, sans-serif;
            {rtl_direction}
        }}
        
        QMainWindow {{
            background: qlineargradient(
                x1: 0, y1: 0, x2: 1, y2: 1,
                stop: 0 {c["bg_main_gradient_start"]},
                stop: 0.5 {c["bg_main"]},
                stop: 1 {c["bg_main_gradient_end"]}
            );
            {rtl_direction}
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
        """Additional RTL-specific fixes"""
        c = self.colors

        return f"""
        /* ========== RTL SPECIFIC FIXES ========== */
        
        /* Text Inputs - Right aligned */
        QLineEdit, QTextEdit, QPlainTextEdit {{
        }}
        
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
        QSpinBox, QDoubleSpinBox {{
        }}
        
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
        
        /* Tables - Right aligned */
        QTableWidget, QTableView {{
            qproperty-layoutDirection: RightToLeft;
        }}
        
        QTableWidget::item, QTableView::item {{
            text-align: right;
            padding-right: 8px;
            padding-left: 8px;
        }}
        
        QHeaderView::section {{
            text-align: right;
            padding-right: 10px;
            padding-left: 10px;
        }}
        
        /* Lists - Right aligned */
        QListWidget, QListView {{
            qproperty-layoutDirection: RightToLeft;
        }}
        
        QListWidget::item, QListView::item {{
            text-align: right;
            padding-right: 8px;
            padding-left: 8px;
        }}
        
        /* Trees - Right aligned */
        QTreeWidget, QTreeView {{
            qproperty-layoutDirection: RightToLeft;
        }}
        
        QTreeWidget::item, QTreeView::item {{
            text-align: right;
            padding-right: 4px;
            padding-left: 20px;
        }}
        
        /* Tabs - RTL order */
        QTabBar {{
            qproperty-layoutDirection: RightToLeft;
        }}
        
        QTabBar::tab {{
            margin-left: 2px;
            margin-right: 0px;
        }}
        
        QTabBar::tab:first {{
            margin-left: 0px;
        }}
        
        /* Menus - Right aligned */
        QMenu {{
            qproperty-layoutDirection: RightToLeft;
        }}
        
        QMenu::item {{
            text-align: right;
            padding-right: 12px;
            padding-left: 30px;
        }}
        
        QMenu::indicator {{
            left: auto;
            right: 8px;
        }}
        
        /* CheckBox & RadioButton - Indicator on right */
        QCheckBox, QRadioButton {{
            qproperty-layoutDirection: RightToLeft;
        }}
        
        QCheckBox::indicator, QRadioButton::indicator {{
            margin-right: 0px;
            margin-left: 8px;
        }}
        
        /* Buttons - Text alignment */
        QPushButton {{
            text-align: center;
        }}
        
        /* ToolBar - RTL layout */
        QToolBar {{
            qproperty-layoutDirection: RightToLeft;
        }}
        
        /* StatusBar - RTL layout */
        QStatusBar {{
            qproperty-layoutDirection: RightToLeft;
        }}
        """