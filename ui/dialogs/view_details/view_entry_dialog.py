# -*- coding: utf-8 -*-
"""
view_entry_dialog.py — محسَّن
المشاكل المُصلَحة:
  - يرث BaseDialog بدل QDialog
  - يستخدم BaseDetailsView للتفاصيل
  - يستخدم _view_helpers بدل دوال مكررة
  - جدول البنود محافظ كما هو (منطق جيد)
  - is_active كـ badge
"""
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLabel
)
from PySide6.QtCore import Qt

from core.base_dialog import BaseDialog
from core.base_details_view import BaseDetailsView
from core.translator import TranslationManager
from core.permissions import is_admin
from ._view_helpers import _get, _name_by_lang, _fmt_dt, _user_to_text, _add_audit_section


class ViewEntryDialog(BaseDialog):
    """حوار عرض تفاصيل الإدخال مع جدول العناصر."""

    def __init__(self, entry, current_user=None, parent=None):
        super().__init__(parent, user=current_user)
        self.entry = entry
        self.current_user = current_user
        self._ = TranslationManager.get_instance().translate
        self._lang = TranslationManager.get_instance().get_current_language()
        self.setWindowTitle(self._("entry_details"))
        self.setMinimumWidth(840)
        self.resize(880, 580)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # ══ تفاصيل الإدخال ══
        view = BaseDetailsView(self)
        lang = self._lang

        owner = _get(self.entry, "owner_client")
        owner_label = _name_by_lang(owner, lang) if owner else ""

        view.begin_section("entry_info", icon="📋")
        view.add_row("entry_no",             _get(self.entry, "entry_no"),             icon="🔖")
        view.add_row("entry_date",           _get(self.entry, "entry_date"),           icon="📅")
        view.add_row("owner_client",         owner_label,                              icon="👤")
        view.add_row("transport_ref",        _get(self.entry, "transport_ref"),        icon="🚛")
        view.add_row("transport_unit_type",  _get(self.entry, "transport_unit_type"),  icon="📦")
        view.add_row("seal_no",              _get(self.entry, "seal_no"),              icon="🔒")

        # status badge
        is_active = _get(self.entry, "is_active", True)
        view.add_row("status",
                     self._("active") if is_active else self._("inactive"),
                     icon="🟢" if is_active else "🔴",
                     is_badge=True)

        notes = _get(self.entry, "notes")
        if notes:
            view.add_row("notes", notes, icon="📝", copyable=False)

        # ── audit للأدمن ──
        if is_admin(self.current_user):
            _add_audit_section(view, self.entry, self._)

        layout.addWidget(view)

        # ══ جدول البنود ══
        items_label = QLabel(self._("items"))
        items_label.setObjectName("section-title")
        layout.addWidget(items_label)

        self._tbl = self._build_items_table()
        layout.addWidget(self._tbl)

        # ── أزرار ──
        btns = QHBoxLayout()
        btns.addStretch()
        btn = QPushButton(self._("close"))
        btn.setObjectName("secondary-btn")
        btn.clicked.connect(self.accept)
        btns.addWidget(btn)
        layout.addLayout(btns)

    # ─── جدول البنود ───────────────────────────────────────────────────────
    def _build_items_table(self) -> QTableWidget:
        _ = self._
        lang = self._lang

        cols = [
            _("material"), _("packaging_type"), _("count"),
            _("gross_weight_kg"), _("net_weight_kg"),
            _("mfg_date"), _("exp_date"), _("origin_country"),
        ]
        tbl = QTableWidget(0, len(cols))
        tbl.setObjectName("entries-table")
        tbl.setHorizontalHeaderLabels(cols)
        tbl.verticalHeader().setVisible(False)
        tbl.setAlternatingRowColors(True)
        tbl.setSelectionMode(QTableWidget.NoSelection)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

        items = getattr(self.entry, "items", []) or []
        total_count = total_gross = total_net = 0.0

        for it in items:
            r = tbl.rowCount()
            tbl.insertRow(r)

            mat   = _name_by_lang(_get(it, "material"),       lang)
            pack  = _name_by_lang(_get(it, "packaging_type"), lang)
            orig  = _name_by_lang(_get(it, "origin_country"), lang)

            count = self._to_float(_get(it, "count") or _get(it, "quantity"))
            gross = self._to_float(_get(it, "gross_weight_kg") or _get(it, "gross_weight"))
            net   = self._to_float(_get(it, "net_weight_kg")   or _get(it, "net_weight"))

            total_count += count
            total_gross += gross
            total_net   += net

            mfg = str(_get(it, "mfg_date") or "")
            exp = str(_get(it, "exp_date") or _get(it, "expiry_date") or "")

            row_data = [
                mat,
                pack,
                f"{count:,.0f}",
                f"{gross:,.3f}",
                f"{net:,.3f}",
                mfg,
                exp,
                orig,
            ]
            for cidx, val in enumerate(row_data):
                cell = QTableWidgetItem(val)
                cell.setTextAlignment(Qt.AlignCenter)
                cell.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                tbl.setItem(r, cidx, cell)

        # ── صف الإجمالي ──
        if items:
            r = tbl.rowCount()
            tbl.insertRow(r)
            totals_data = [
                _("totals"), "", f"{total_count:,.0f}",
                f"{total_gross:,.3f}", f"{total_net:,.3f}",
                "", "", "",
            ]
            for cidx, val in enumerate(totals_data):
                cell = QTableWidgetItem(val)
                cell.setTextAlignment(Qt.AlignCenter)
                fnt = cell.font()
                fnt.setBold(True)
                cell.setFont(fnt)
                cell.setFlags(Qt.ItemIsEnabled)
                tbl.setItem(r, cidx, cell)

        return tbl

    @staticmethod
    def _to_float(val) -> float:
        try:
            return float(val or 0)
        except Exception:
            return 0.0
