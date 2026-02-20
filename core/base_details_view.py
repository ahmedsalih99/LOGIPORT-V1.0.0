# -*- coding: utf-8 -*-
"""
BaseDetailsView — نسخة محسّنة احترافية v2
==========================================
✅ نفس الـ API القديم (add_row, add_section_title, clear, ...)
✅ قيم قابلة للنسخ بنقرة (زر ⎘ عند Hover)
✅ Hover effect لكل صف
✅ أقسام قابلة للطي Collapsible
✅ Badges للحالة والنوع
✅ عرض المعلومات حسب الصلاحية
✅ تسليط ضوء مختلف للحقول المالية
✅ ترجمة فورية عند تغيير اللغة
✅ Object Names متوافقة مع ثيم المشروع

[v2 — التحسينات الجديدة]
✅ setLayoutDirection تلقائي حسب اللغة الحالية
✅ تحديث direction فوري عند تغيير اللغة
✅ _add_close_btn مُوحَّد — يُغني عن تكراره في كل dialog
✅ _add_action_bar — شريط أزرار مرن للـ view dialogs
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QToolButton, QApplication, QScrollArea,
    QSizePolicy, QPushButton
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor

from core.translator import TranslationManager


# ─────────────────────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────────────────────
def _is_rtl(lang: str) -> bool:
    """True للغات التي تُكتب من اليمين إلى اليسار."""
    return lang in ("ar",)


# ─────────────────────────────────────────────────────────────────────────────
# صف واحد: أيقونة | مفتاح | : | قيمة | [⎘]
# ─────────────────────────────────────────────────────────────────────────────
class _DetailRow(QWidget):
    """صف واحد قابل للـ hover والنسخ."""

    def __init__(
        self,
        key_text: str,
        value_text: str,
        *,
        icon: str = "",
        is_financial: bool = False,
        is_badge: bool = False,
        badge_value: str = "",
        alt: bool = False,
        copyable: bool = True,
        min_key_width: int = 150,
        parent=None,
    ):
        super().__init__(parent)
        self._value_str = value_text

        self.setObjectName("detail-row-alt" if alt else "detail-row")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setMinimumHeight(30)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 3, 6, 3)
        layout.setSpacing(6)

        # ── أيقونة ──
        if icon:
            icon_lbl = QLabel(icon)
            icon_lbl.setObjectName("detail-icon")
            icon_lbl.setFixedWidth(20)
            icon_lbl.setAlignment(Qt.AlignCenter)
            layout.addWidget(icon_lbl)

        # ── المفتاح ──
        self._key_lbl = QLabel(key_text)
        self._key_lbl.setObjectName(
            "detail-key-financial" if is_financial else "detail-key"
        )
        self._key_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._key_lbl.setMinimumWidth(min_key_width)
        self._key_lbl.setMaximumWidth(220)
        layout.addWidget(self._key_lbl)

        # ── فاصل ──
        sep = QLabel(":")
        sep.setObjectName("detail-sep")
        sep.setFixedWidth(10)
        sep.setAlignment(Qt.AlignCenter)
        layout.addWidget(sep)

        # ── القيمة ──
        if is_badge and badge_value:
            self._val_lbl = QLabel(value_text)
            self._val_lbl.setObjectName(f"badge-{badge_value}")
        else:
            display = "-" if value_text in (None, "", "None", "-") else value_text
            self._val_lbl = QLabel(display)
            self._val_lbl.setObjectName(
                "detail-value-financial" if is_financial else "detail-value"
            )

        self._val_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._val_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._val_lbl.setWordWrap(False)
        self._val_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(self._val_lbl, 1)

        # ── زر نسخ ──
        if copyable and value_text not in (None, "", "None", "-"):
            self._copy_btn = QToolButton()
            self._copy_btn.setText("⎘")
            self._copy_btn.setObjectName("copy-btn")
            self._copy_btn.setFixedSize(24, 24)
            self._copy_btn.setToolTip("نسخ")
            self._copy_btn.setVisible(False)
            self._copy_btn.clicked.connect(self._do_copy)
            layout.addWidget(self._copy_btn)

            self._toast = QLabel("✓")
            self._toast.setObjectName("copy-toast")
            self._toast.setVisible(False)
            layout.addWidget(self._toast)
        else:
            self._copy_btn = None
            self._toast = None

    # ── Hover ──
    def enterEvent(self, e):
        if self._copy_btn:
            self._copy_btn.setVisible(True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        if self._copy_btn:
            self._copy_btn.setVisible(False)
        if self._toast:
            self._toast.setVisible(False)
        super().leaveEvent(e)

    def _do_copy(self):
        QApplication.clipboard().setText(self._value_str)
        if self._copy_btn:
            self._copy_btn.setVisible(False)
        if self._toast:
            self._toast.setVisible(True)
            QTimer.singleShot(1400, lambda: (
                self._toast.setVisible(False) if self._toast else None
            ))

    def update_key(self, text: str):
        self._key_lbl.setText(text)


# ─────────────────────────────────────────────────────────────────────────────
# قسم قابل للطي
# ─────────────────────────────────────────────────────────────────────────────
class _Section(QWidget):
    def __init__(self, title_text: str, *, collapsed: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("details-section")
        self._collapsed = collapsed
        self._rows: list[_DetailRow] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 2, 0, 2)
        outer.setSpacing(0)

        # ── header ──
        self._hdr = QFrame()
        self._hdr.setObjectName("section-header")
        self._hdr.setCursor(QCursor(Qt.PointingHandCursor))
        hl = QHBoxLayout(self._hdr)
        hl.setContentsMargins(10, 6, 10, 6)
        hl.setSpacing(8)

        self._arrow = QLabel("▸" if collapsed else "▾")
        self._arrow.setObjectName("section-arrow")
        self._arrow.setFixedWidth(14)

        self._title_lbl = QLabel(title_text)
        self._title_lbl.setObjectName("section-title")

        self._badge = QLabel("")
        self._badge.setObjectName("section-count")
        self._badge.setVisible(False)

        hl.addWidget(self._arrow)
        hl.addWidget(self._title_lbl, 1)
        hl.addWidget(self._badge)

        self._hdr.mousePressEvent = lambda _e: self.toggle()
        outer.addWidget(self._hdr)

        # ── body ──
        self._body = QWidget()
        self._body.setObjectName("section-body")
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(4, 0, 0, 4)
        self._body_layout.setSpacing(0)

        if collapsed:
            self._body.setVisible(False)

        outer.addWidget(self._body)

    def add_row(self, row: _DetailRow):
        self._rows.append(row)
        self._body_layout.addWidget(row)
        n = len(self._rows)
        self._badge.setText(str(n))
        self._badge.setVisible(True)

    def toggle(self):
        self._collapsed = not self._collapsed
        self._arrow.setText("▸" if self._collapsed else "▾")
        self._body.setVisible(not self._collapsed)

    def set_title(self, text: str):
        self._title_lbl.setText(text)


# ─────────────────────────────────────────────────────────────────────────────
# BaseDetailsView — الكلاس الرئيسي
# ─────────────────────────────────────────────────────────────────────────────
class BaseDetailsView(QScrollArea):
    """
    Widget احترافي لعرض تفاصيل أي كيان.

    الـ API القديم محفوظ بالكامل:
        view.clear()
        view.add_section_title("general_info")
        view.add_row("client", "أحمد محمد")
        view.add_rows([("status", "active"), ...])
        view.add_from_dict(data, label_map, keys)
        view.add_from_model(model, fields, label_map)

    الـ API الجديد:
        # قسم قابل للطي
        s = view.begin_section("parties", icon="👤", collapsed=False)
        view.add_row("client", "أحمد", section=s, icon="🏢")

        # تحكم بالصلاحيات
        view.add_row("total_value", "5000$", required_perm="view_values",
                     is_financial=True)

        # badges — الـ CSS يطبق اللون حسب badge-{value}
        view.add_row("status", "active", is_badge=True)
        view.add_row("type",   "import", is_badge=True)

    أزرار مُوحَّدة (مُغنية عن تكرارها في كل dialog):
        view.add_close_btn(layout)
        view.add_action_bar(layout, extra_buttons=[...])

    Object Names (متوافقة مع الثيم):
        details-card, details-section, section-header, section-title,
        section-arrow, section-count, section-body,
        detail-row, detail-row-alt, detail-key, detail-value,
        detail-key-financial, detail-value-financial,
        detail-icon, detail-sep, copy-btn, copy-toast,
        badge-active, badge-inactive, badge-draft,
        badge-import, badge-export, badge-transit
    """

    def __init__(
        self,
        parent=None,
        *,
        min_key_width: int = 150,
        permissions: set | list | None = None,
        user=None,
    ):
        super().__init__(parent)

        self._tm = TranslationManager.get_instance()
        self._ = self._tm.translate
        self._tm.language_changed.connect(self._on_language_changed)  # [v2]

        self._min_key_width = min_key_width
        self._permissions: set = set(permissions or [])
        self._user = user or {}

        # تتبع للترجمة
        self._trans_section_titles: list[tuple[_Section, str]] = []
        self._trans_key_labels: list[tuple[_DetailRow, str]] = []
        self._sections: list[_Section] = []
        self._current_section: _Section | None = None
        self._row_index = 0

        # ── إعداد ScrollArea ──
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setObjectName("details-scroll")
        self.setFrameShape(QFrame.NoFrame)

        # ── container ──
        self._container = QWidget()
        self._container.setObjectName("details-container")
        self._root = QVBoxLayout(self._container)
        self._root.setContentsMargins(0, 0, 0, 12)
        self._root.setSpacing(4)

        # card رئيسية
        self.card = QFrame(self._container)
        self.card.setObjectName("details-card")
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(8, 8, 8, 8)
        self.card_layout.setSpacing(4)
        self._root.addWidget(self.card)
        self._root.addStretch()

        self.setWidget(self._container)

        # [v2] تطبيق الاتجاه الحالي فور الإنشاء
        self._apply_direction()

    # ─────────────────────────────────────────────
    # [v2] اتجاه التخطيط RTL / LTR
    # ─────────────────────────────────────────────
    def _apply_direction(self):
        """يضبط اتجاه التخطيط حسب اللغة الحالية."""
        lang = self._tm.get_current_language()
        direction = Qt.RightToLeft if _is_rtl(lang) else Qt.LeftToRight
        self.setLayoutDirection(direction)
        self._container.setLayoutDirection(direction)
        self.card.setLayoutDirection(direction)

    def _on_language_changed(self):
        """[v2] يُشغَّل عند تغيير اللغة — يُحدِّث الترجمة والاتجاه معاً."""
        self._ = self._tm.translate
        self._apply_direction()
        self.retranslate_ui()

    # ─────────────────────────────────────────────
    # صلاحيات
    # ─────────────────────────────────────────────
    def set_permissions(self, perms: set | list):
        self._permissions = set(perms)

    def has_perm(self, code: str) -> bool:
        return (not code) or (code in self._permissions)

    def can_view_values(self) -> bool:
        return "view_values" in self._permissions or "view_pricing" in self._permissions

    def can_view_audit(self) -> bool:
        return "view_audit_log" in self._permissions or "view_audit_trail" in self._permissions

    def can_view_clients(self) -> bool:
        return "view_clients" in self._permissions

    def can_view_companies(self) -> bool:
        return "view_companies" in self._permissions

    # ─────────────────────────────────────────────
    # clear
    # ─────────────────────────────────────────────
    def clear(self):
        """يمسح كل المحتوى."""
        while self.card_layout.count():
            item = self.card_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self._sections.clear()
        self._trans_section_titles.clear()
        self._trans_key_labels.clear()
        self._current_section = None
        self._row_index = 0

    # ─────────────────────────────────────────────
    # begin_section — قسم قابل للطي (API جديد)
    # ─────────────────────────────────────────────
    def begin_section(
        self,
        title_key: str,
        *,
        icon: str = "",
        collapsed: bool = False,
        required_perm: str = "",
    ) -> _Section | None:
        """
        ابدأ قسم جديد قابل للطي.
        الصفوف التالية تُضاف داخله تلقائياً.
        يرجع None إذا المستخدم ما عنده الصلاحية.
        """
        if required_perm and not self.has_perm(required_perm):
            self._current_section = None
            return None

        title_text = (icon + "  " if icon else "") + self._(title_key)
        sec = _Section(title_text, collapsed=collapsed, parent=self.card)
        self.card_layout.addWidget(sec)
        self._sections.append(sec)
        self._trans_section_titles.append((sec, title_key))
        self._current_section = sec
        return sec

    # ─────────────────────────────────────────────
    # add_section_title — API قديم
    # ─────────────────────────────────────────────
    def add_section_title(self, text_key: str, *, icon: str = ""):
        """[API قديم] متوافق مع الكود القديم تماماً."""
        self.begin_section(text_key, icon=icon, collapsed=False)

    # ─────────────────────────────────────────────
    # add_row
    # ─────────────────────────────────────────────
    def add_row(
        self,
        key_text_key: str,
        value_text,
        *,
        section: _Section | None = None,
        icon: str = "",
        is_financial: bool = False,
        is_badge: bool = False,
        required_perm: str = "",
        copyable: bool = True,
    ) -> _DetailRow | None:
        """
        أضف صف.
        - section: القسم المستهدف (None = القسم الحالي)
        - required_perm: يخفيه إذا المستخدم ما عنده الصلاحية
        - is_financial: يخفيه إذا ما عنده view_values
        - is_badge: يعرض القيمة كـ badge ملوّن
        """
        if required_perm and not self.has_perm(required_perm):
            return None
        if is_financial and not self.can_view_values():
            return None

        target = section or self._current_section
        val_str = "-" if value_text in (None, "", "None") else str(value_text)
        alt = self._row_index % 2 == 1

        row = _DetailRow(
            key_text=self._(key_text_key) if key_text_key else "",
            value_text=val_str,
            icon=icon,
            is_financial=is_financial,
            is_badge=is_badge,
            badge_value=val_str if is_badge else "",
            alt=alt,
            copyable=copyable and val_str != "-",
            min_key_width=self._min_key_width,
            parent=self.card,
        )

        if target:
            target.add_row(row)
        else:
            self.card_layout.addWidget(row)

        if key_text_key:
            self._trans_key_labels.append((row, key_text_key))

        self._row_index += 1
        return row

    # ─────────────────────────────────────────────
    # API قديم — محفوظ بالكامل
    # ─────────────────────────────────────────────
    def add_rows(self, items):
        """items: [(key_text_key, value), ...]"""
        for k, v in items:
            self.add_row(k, v)

    def add_from_dict(self, data: dict, label_map: dict = None, keys: list = None):
        label_map = label_map or {}
        keys = keys or list(data.keys())
        for k in keys:
            self.add_row(label_map.get(k, k), data.get(k))

    def add_from_model(self, model, fields: list, label_map: dict = None):
        label_map = label_map or {}
        for f in fields:
            self.add_row(label_map.get(f, f), getattr(model, f, None))

    # ─────────────────────────────────────────────
    # [v2] أزرار مُوحَّدة — تُغني عن تكرارها في كل dialog
    # ─────────────────────────────────────────────
    def add_close_btn(self, parent_layout: QVBoxLayout) -> QPushButton:
        """
        يضيف شريط زر إغلاق موحّد في أسفل الـ layout المُعطى.

        الاستخدام في view_*.py:
            layout = QVBoxLayout(self)
            layout.addWidget(view)
            view.add_close_btn(layout)       # بدل الـ 6 سطور المتكررة
        """
        bar = QHBoxLayout()
        bar.addStretch()
        btn = QPushButton(self._("close"))
        btn.setObjectName("secondary-btn")
        bar.addWidget(btn)
        parent_layout.addLayout(bar)
        return btn

    def add_action_bar(
        self,
        parent_layout: QVBoxLayout,
        *,
        extra_buttons: list[tuple[str, str]] | None = None,
        close_key: str = "close",
        close_object_name: str = "secondary-btn",
    ) -> dict[str, QPushButton]:
        """
        يضيف شريط أزرار مرن في أسفل الـ layout.

        المعاملات:
            extra_buttons: قائمة من (translation_key, object_name)
                           مثال: [("edit", "primary-btn"), ("delete", "danger-btn")]
            close_key:     مفتاح ترجمة زر الإغلاق (افتراضي "close")

        يرجع:
            dict مفاتيحه translation_key → QPushButton
            مثال: {"edit": <btn>, "delete": <btn>, "close": <btn>}

        الاستخدام:
            btns = view.add_action_bar(
                layout,
                extra_buttons=[("edit", "primary-btn")],
            )
            btns["edit"].clicked.connect(self._on_edit)
            btns["close"].clicked.connect(self.accept)
        """
        result: dict[str, QPushButton] = {}
        bar = QHBoxLayout()
        bar.addStretch()

        # الأزرار الإضافية أولاً (يسار ← يمين في RTL)
        for key, obj_name in (extra_buttons or []):
            btn = QPushButton(self._(key))
            btn.setObjectName(obj_name)
            bar.addWidget(btn)
            result[key] = btn

        # زر الإغلاق دايماً آخر
        close_btn = QPushButton(self._(close_key))
        close_btn.setObjectName(close_object_name)
        bar.addWidget(close_btn)
        result[close_key] = close_btn

        parent_layout.addLayout(bar)
        return result

    # ─────────────────────────────────────────────
    # تعبئة جاهزة — معاملة كاملة
    # ─────────────────────────────────────────────
    def load_transaction(self, trx):
        """
        تعبئة تفاصيل معاملة كاملة مع مراعاة الصلاحيات.
        trx: ORM object أو dict.
        """
        self.clear()
        g = lambda k, d=None: (
            trx.get(k, d) if isinstance(trx, dict) else getattr(trx, k, d)
        )

        # ══ 1. معلومات أساسية (للجميع) ══
        self.begin_section("general_info", icon="📋")
        self.add_row("transaction_no",   g("transaction_no"),   icon="🔖")
        self.add_row("transaction_date", g("transaction_date"), icon="📅")
        self.add_row("transaction_type", g("transaction_type"), icon="🔄", is_badge=True)
        self.add_row("status",           g("status"),           icon="🟢", is_badge=True)
        if g("notes"):
            self.add_row("notes", g("notes"), icon="📝", copyable=False)

        # ══ 2. الأطراف ══
        self.begin_section("parties", icon="👥")
        self.add_row("client",
                     g("client_name") or g("client_id"),
                     icon="👤", required_perm="view_clients")
        self.add_row("exporting_company",
                     g("exporter_name") or g("exporter_company_id"),
                     icon="🏭", required_perm="view_companies")
        self.add_row("importing_company",
                     g("importer_name") or g("importer_company_id"),
                     icon="🏢", required_perm="view_companies")
        self.add_row("broker",
                     g("broker_name") or g("broker_company_id"),
                     icon="🤝", required_perm="view_companies")
        self.add_row("relationship_type", g("relationship_type"),
                     icon="🔗", is_badge=True)

        # ══ 3. جغرافيا ونقل (للجميع) ══
        self.begin_section("geography_transport", icon="🌍")
        self.add_row("origin_country",
                     g("origin_country") or g("origin_country_id"), icon="📍")
        self.add_row("dest_country",
                     g("dest_country") or g("dest_country_id"), icon="🎯")
        self.add_row("delivery_method",
                     g("delivery_method") or g("delivery_method_id"), icon="🚚")
        self.add_row("transport_type",  g("transport_type"),  icon="🚛")
        self.add_row("transport_ref",   g("transport_ref"),   icon="🏷️")

        # ══ 4. المجاميع (للجميع) ══
        self.begin_section("totals", icon="📊")
        count = g("totals_count")
        gross = g("totals_gross_kg")
        net   = g("totals_net_kg")
        self.add_row("count",
                     f"{float(count):,.0f}" if count else None, icon="📦")
        self.add_row("gross_weight_kg",
                     f"{float(gross):,.2f} kg" if gross else None, icon="⚖️")
        self.add_row("net_weight_kg",
                     f"{float(net):,.2f} kg" if net else None, icon="⚖️")

        # ══ 5. مالي (view_values أو view_pricing) ══
        if self.can_view_values():
            self.begin_section("financial_info", icon="💰")
            sym = g("currency_symbol") or g("currency_name") or ""
            val = g("totals_value")
            self.add_row("currency",
                         g("currency_name"), icon="💵", is_financial=True)
            self.add_row("pricing_type",
                         g("pricing_type_name") or g("pricing_type_id"),
                         icon="📈", is_financial=True)
            self.add_row("total_value",
                         f"{float(val):,.2f} {sym}".strip() if val else None,
                         icon="💵", is_financial=True)

        # ══ 6. Audit (view_audit_log) — مطوي افتراضياً ══
        if self.can_view_audit():
            self.begin_section("audit_info", icon="🕐", collapsed=True)
            self.add_row("created_by",  g("created_by_name"), icon="👤", copyable=False)
            self.add_row("created_at",  g("created_at"),      icon="🕐", copyable=False)
            self.add_row("updated_by",  g("updated_by_name"), icon="👤", copyable=False)
            self.add_row("updated_at",  g("updated_at"),      icon="🕐", copyable=False)

    # ─────────────────────────────────────────────
    # ترجمة فورية
    # ─────────────────────────────────────────────
    def retranslate_ui(self):
        self._ = self._tm.translate
        for sec, key in self._trans_section_titles:
            sec.set_title(self._(key))
        for row, key in self._trans_key_labels:
            row.update_key(self._(key))