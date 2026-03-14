# -*- coding: utf-8 -*-
"""
view_container_dialog.py — LOGIPORT
=====================================
نافذة عرض تفاصيل الكونتينر (للقراءة فقط).
تعرض:
  - بيانات الكونتينر الكاملة
  - بيانات الشحنة (ميناء، باخرة، تواريخ)
  - الحالة كـ badge ملوّن
  - الزبون والمعاملة المرتبطة
  - الإدخالات المرتبطة في جدول
  - Audit section للأدمن
"""
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLabel,
)
from PySide6.QtCore import Qt

from core.base_dialog import BaseDialog
from core.base_details_view import BaseDetailsView
from core.translator import TranslationManager
from core.permissions import is_admin
from ._view_helpers import _get, _name_by_lang, _fmt_dt, _add_audit_section, build_dialog_table, make_bold_cell


# ── ألوان الحالة ──────────────────────────────────────────────────────────────
_STATUS_COLOR = {
    "booked":     "#6366F1",
    "loaded":     "#0891B2",
    "in_transit": "#2563EB",
    "arrived":    "#7C3AED",
    "customs":    "#D97706",
    "delivered":  "#059669",
    "hold":       "#DC2626",
}
_STATUS_ICON = {
    "booked":     "📋",
    "loaded":     "📦",
    "in_transit": "🚢",
    "arrived":    "⚓",
    "customs":    "🏛️",
    "delivered":  "✅",
    "hold":       "⚠️",
}


class ViewContainerDialog(BaseDialog):
    """نافذة عرض تفاصيل الكونتينر — قراءة فقط."""

    def __init__(self, container, current_user=None, parent=None, can_edit=None, can_delete=None):
        super().__init__(parent, user=current_user)
        self.container    = container
        self.current_user = current_user
        self._            = TranslationManager.get_instance().translate
        self._lang        = TranslationManager.get_instance().get_current_language()

        # الصلاحيات — إذا مُرِّرت من الخارج نستخدمها، وإلا نحسبها هنا
        from core.permissions import has_perm
        self._can_edit   = can_edit   if can_edit   is not None else (is_admin(current_user) or has_perm(current_user, "edit_transaction"))
        self._can_delete = can_delete if can_delete is not None else (is_admin(current_user) or has_perm(current_user, "delete_transaction"))

        self.setWindowTitle(
            f"🚢  {_get(container, 'container_no') or self._('container_details')}"
        )
        self.setMinimumWidth(780)
        self.resize(820, 600)
        self._init_ui()

    # ── بناء الواجهة ──────────────────────────────────────────────────────────

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        c    = self.container
        _    = self._
        lang = self._lang

        view = BaseDetailsView(self)

        # ── القسم الأول: بيانات الكونتينر الأساسية ───────────────────────────
        view.begin_section("container_info", icon="🚢")
        view.add_row("container_no_label",  _get(c, "container_no"),  icon="📋", copyable=True)
        view.add_row("bl_number_label",     _get(c, "bl_number"),     icon="📄", copyable=True)
        view.add_row("booking_no_label",    _get(c, "booking_no"),    icon="🔖", copyable=True)
        view.add_row("shipping_line_label", _get(c, "shipping_line"), icon="🏢")
        view.add_row("vessel_name_label",   _get(c, "vessel_name"),   icon="🚢")
        view.add_row("voyage_no_label",     _get(c, "voyage_no"),     icon="🔢", copyable=True)

        # الحالة كـ badge ملوّن
        status     = _get(c, "status") or "booked"
        status_lbl = _(f"container_status_{status}")
        status_ico = _STATUS_ICON.get(status, "•")
        view.add_row("status_label",
                     f"{status_ico}  {status_lbl}",
                     icon=status_ico,
                     is_badge=True)

        # ── القسم الثاني: المواني ─────────────────────────────────────────────
        view.begin_section("ports_section", icon="⚓")
        view.add_row("port_of_loading_label",   _get(c, "port_of_loading"),   icon="🟢")
        view.add_row("port_of_discharge_label", _get(c, "port_of_discharge"), icon="🔴")
        view.add_row("final_destination_label", _get(c, "final_destination"), icon="🏁")

        # ── القسم الثالث: التواريخ ────────────────────────────────────────────
        view.begin_section("dates_section", icon="📅")

        def _d(attr):
            val = _get(c, attr)
            return str(val) if val else "—"

        view.add_row("etd_label",          _d("etd"),           icon="🛫")
        view.add_row("eta_label",          _d("eta"),           icon="🛬")
        view.add_row("atd_label",          _d("atd"),           icon="✈️")
        view.add_row("ata_label",          _d("ata"),           icon="🏠")
        view.add_row("customs_date_label", _d("customs_date"),  icon="🏛️")
        view.add_row("delivery_date_label",_d("delivery_date"), icon="✅")

        # ── القسم الرابع: الربط ───────────────────────────────────────────────
        view.begin_section("links_section", icon="🔗")

        # الزبون
        client = _get(c, "client")
        if client:
            client_name = (_name_by_lang(client, lang)
                           or getattr(client, "name_ar", None)
                           or getattr(client, "name_en", None) or "")
            view.add_row("client_label", client_name, icon="👤")

        # المعاملة
        tx = _get(c, "transaction")
        if tx:
            tx_no = getattr(tx, "transaction_no", None) or str(_get(c, "transaction_id") or "")
            view.add_row("transaction_label", tx_no, icon="📑", copyable=True)

        # الملاحظات
        notes = _get(c, "notes")
        if notes:
            view.add_row("notes", notes, icon="📝", copyable=False)

        # ── Audit للأدمن ──────────────────────────────────────────────────────
        if is_admin(self.current_user):
            _add_audit_section(view, c, _, lang=lang)

        layout.addWidget(view)

        # ── Timeline مرئي لمراحل الكونتينر ───────────────────────────────────
        try:
            from ui.widgets.container_timeline import ContainerTimeline
            timeline = ContainerTimeline(c, parent=self)
            layout.addWidget(timeline)
        except Exception:
            pass

        # ── جدول الإدخالات المرتبطة ───────────────────────────────────────────

        btns = QHBoxLayout()
        btns.addStretch()

        # زر طباعة
        btn_print = QPushButton(f"🖨  {_('print')}")
        btn_print.setObjectName("secondary-btn")
        btn_print.clicked.connect(self._print_card)
        btns.addWidget(btn_print)

        # زر تعديل
        if self._can_edit:
            btn_edit = QPushButton(_("edit"))
            btn_edit.setObjectName("primary-btn")
            btn_edit.clicked.connect(self._open_edit)
            btns.addWidget(btn_edit)

        # زر حذف
        if self._can_delete:
            btn_delete = QPushButton(_("delete"))
            btn_delete.setObjectName("danger-btn")
            btn_delete.clicked.connect(self._delete_container)
            btns.addWidget(btn_delete)

        btn_close = QPushButton(_("close"))
        btn_close.setObjectName("secondary-btn")
        btn_close.clicked.connect(self.accept)
        btns.addWidget(btn_close)

        layout.addLayout(btns)

    # ── جدول الإدخالات ────────────────────────────────────────────────────────


    def _open_edit(self):
        from ui.dialogs.add_edit_container_dialog import AddEditContainerDialog
        from PySide6.QtWidgets import QDialog
        dlg = AddEditContainerDialog(
            parent=self,
            current_user=self.current_user,
            record=self.container,
        )
        if dlg.exec() == QDialog.Accepted:
            self.accept()

    def _delete_container(self):
        from PySide6.QtWidgets import QMessageBox
        from database.crud.container_tracking_crud import ContainerTrackingCRUD
        reply = QMessageBox.question(
            self,
            self._("delete_container"),
            self._("confirm_delete_container"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            ContainerTrackingCRUD().delete(self.container.id)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, self._("error"), str(e))

    # ── طباعة بطاقة الكونتينر ─────────────────────────────────────────────────

    def _print_card(self):
        from PySide6.QtWidgets import QMessageBox
        _ = self._
        try:
            from services.container_report_service import ContainerReportService
            svc = ContainerReportService()
            ok, path, err = svc.render_card(self.container, lang=self._lang)
            if not ok:
                QMessageBox.critical(self, _("error"), f"{_('pdf_error')}\n{err}")
                return
            # فتح المعاينة الداخلية
            try:
                from ui.widgets.pdf_preview_dialog import PdfPreviewDialog
                import os
                ext = os.path.splitext(path)[1].lower()
                if ext == ".pdf":
                    dlg = PdfPreviewDialog(pdf_path=path, title=_("container_card"), parent=self)
                else:
                    dlg = PdfPreviewDialog(html_path=path, title=_("container_card"), parent=self)
                dlg.exec()
            except Exception:
                # fallback: فتح خارجي
                import os, subprocess, sys
                if sys.platform == "win32":
                    os.startfile(path)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", path])
                else:
                    subprocess.Popen(["xdg-open", path])
        except Exception as e:
            QMessageBox.critical(self, _("error"), str(e))