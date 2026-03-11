"""
transport_tab.py — LOGIPORT
============================
Mixin يُضيف تبويب "معلومات الشحن والشهادة" لنافذة إنشاء/تعديل المعاملة.

الحقول اختيارية بالكامل — المستخدم يملؤها فقط عند الحاجة لتوليد CMR أو Form A.

يُضيف للـ Window:
  - _build_transport_tab()      → ينشئ التبويب ويضيفه لـ self.tabs
  - get_transport_data() → dict → يُعيد البيانات لحفظها
  - prefill_transport(trx)      → يملأ الحقول من معاملة موجودة
"""
from __future__ import annotations

from ui.widgets.searchable_combo import SearchableComboBox
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QDateEdit, QComboBox, QLabel,
    QFrame, QScrollArea, QSizePolicy, QPushButton,
)
from PySide6.QtCore import Qt, QDate

from database.models import get_session_local, Company


class TransportTabMixin:

    # ─────────────────────────────────────────────────────────────────────────
    # Build
    # ─────────────────────────────────────────────────────────────────────────

    def _build_transport_tab(self):
        """أنشئ التبويب وأضفه لـ self.tabs."""
        tab = QWidget()
        tab.setObjectName("transport-tab")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        inner = QWidget()
        inner.setObjectName("transport-inner")
        outer = QVBoxLayout(inner)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(16)

        # ── قسمان جنب بعض: CMR يسار | Form A يمين ──────────────────────────────
        cmr_card = self._transport_section_card(
            self._("cmr_section_title") if hasattr(self, "_") else "CMR — بيانات الشحن البري",
            self._build_cmr_fields,
        )

        forma_card = self._transport_section_card(
            self._("forma_section_title") if hasattr(self, "_") else "Form A — شهادة المنشأ",
            self._build_forma_fields,
        )

        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)
        cards_row.addWidget(cmr_card, stretch=1)
        cards_row.addWidget(forma_card, stretch=1)

        outer.addLayout(cards_row)
        outer.addStretch()

        scroll.setWidget(inner)

        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)

        label = self._("transport_tab_label") if hasattr(self, "_") else "🚛 الشحن"
        self.tabs.addTab(tab, label)
        self._transport_tab = tab

    def _transport_section_card(self, title: str, builder_fn) -> QFrame:
        """إطار بعنوان يحتوي على حقول."""
        card = QFrame()
        card.setObjectName("form-card")
        vlay = QVBoxLayout(card)
        vlay.setContentsMargins(16, 12, 16, 16)
        vlay.setSpacing(10)

        # عنوان القسم
        lbl_title = QLabel(title)
        lbl_title.setObjectName("form-section-title")
        vlay.addWidget(lbl_title)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("form-dialog-sep")
        vlay.addWidget(sep)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        form.setContentsMargins(0, 4, 0, 0)
        vlay.addLayout(form)

        builder_fn(form)
        vlay.addStretch()   # المحتوى يبقى بالأعلى
        return card

    # ─────────────────────────────────────────────────────────────────────────
    # CMR Fields
    # ─────────────────────────────────────────────────────────────────────────

    def _build_cmr_fields(self, form: QFormLayout):
        _ = self._ if hasattr(self, "_") else lambda k: k

        # رقم CMR — يدوي أو تلقائي
        cmr_row = QHBoxLayout()
        cmr_row.setSpacing(6)
        self.txt_cmr_no = QLineEdit()
        self.txt_cmr_no.setObjectName("form-input")
        self.txt_cmr_no.setPlaceholderText(_("cmr_no_placeholder"))
        cmr_row.addWidget(self.txt_cmr_no, 1)
        self._btn_gen_cmr_no = QPushButton("⚙ " + _("cmr_no_auto"))
        self._btn_gen_cmr_no.setObjectName("secondary-btn")
        self._btn_gen_cmr_no.setFixedHeight(32)
        self._btn_gen_cmr_no.setCursor(Qt.PointingHandCursor)
        self._btn_gen_cmr_no.setToolTip(_("cmr_no_auto_tooltip"))
        self._btn_gen_cmr_no.clicked.connect(self._generate_cmr_no)
        cmr_row.addWidget(self._btn_gen_cmr_no)
        form.addRow(_("cmr_no_label"), cmr_row)

        # شركة الناقل — SearchableComboBox
        self.cmb_carrier = SearchableComboBox(parent=self)
        self.cmb_carrier.setObjectName("carrier-combo")
        self.cmb_carrier.set_loader(
            loader=self._search_carrier_companies,
            display=self._carrier_display,
            value=lambda c: c.id,
        )
        form.addRow(_("carrier_company"), self.cmb_carrier)

        # رقم الشاحنة
        self.txt_truck_plate = QLineEdit()
        self.txt_truck_plate.setObjectName("truck-plate-input")
        self.txt_truck_plate.setPlaceholderText(_("truck_plate_placeholder"))
        form.addRow(_("truck_plate"), self.txt_truck_plate)

        # اسم السائق
        self.txt_driver_name = QLineEdit()
        self.txt_driver_name.setObjectName("driver-name-input")
        self.txt_driver_name.setPlaceholderText(_("driver_name_placeholder"))
        form.addRow(_("driver_name"), self.txt_driver_name)

        # مكان التحميل
        self.txt_loading_place = QLineEdit()
        self.txt_loading_place.setObjectName("loading-place-input")
        self.txt_loading_place.setPlaceholderText(_("loading_place_placeholder"))
        form.addRow(_("loading_place"), self.txt_loading_place)

        # مكان التسليم
        self.txt_delivery_place = QLineEdit()
        self.txt_delivery_place.setObjectName("delivery-place-input")
        self.txt_delivery_place.setPlaceholderText(_("delivery_place_placeholder"))
        form.addRow(_("delivery_place"), self.txt_delivery_place)

        # الوثائق المرفقة — Box 5
        self.txt_attached_docs = QLineEdit()
        self.txt_attached_docs.setObjectName("attached-docs-input")
        self.txt_attached_docs.setPlaceholderText(
            _("attached_docs_placeholder") if hasattr(self, "_") else "e.g. Invoice, Packing List, Certificate..."
        )
        form.addRow(
            _("attached_documents") if hasattr(self, "_") else "Documents Attached",
            self.txt_attached_docs,
        )

        # تاريخ الشحن
        self.dt_shipment = QDateEdit()
        self.dt_shipment.setObjectName("shipment-date-input")
        self.dt_shipment.setCalendarPopup(True)
        self.dt_shipment.setSpecialValueText(_("not_specified"))
        self.dt_shipment.setDate(QDate())          # فارغ
        self.dt_shipment.setMinimumDate(QDate(2000, 1, 1))
        self._shipment_date_set = False             # flag: هل المستخدم حدّد تاريخاً؟
        self.dt_shipment.dateChanged.connect(self._on_shipment_date_changed)
        form.addRow(_("shipment_date"), self.dt_shipment)

    def _on_shipment_date_changed(self, qdate: QDate):
        self._shipment_date_set = qdate.isValid() and qdate != QDate()

    def _generate_cmr_no(self):
        """يولّد رقم CMR تلقائياً بالصيغة: CMR-YYYYMMDD-XXXX"""
        from datetime import date as _date
        import random, string
        today  = _date.today()
        suffix = "".join(random.choices(string.digits, k=4))
        auto   = f"CMR-{today.strftime('%Y%m%d')}-{suffix}"
        self.txt_cmr_no.setText(auto)

    # ─────────────────────────────────────────────────────────────────────────
    # Form A Fields
    # ─────────────────────────────────────────────────────────────────────────

    def _build_forma_fields(self, form: QFormLayout):
        _ = self._ if hasattr(self, "_") else lambda k: k

        # رقم الشهادة
        self.txt_certificate_no = QLineEdit()
        self.txt_certificate_no.setObjectName("certificate-no-input")
        self.txt_certificate_no.setPlaceholderText(_("certificate_no_placeholder"))
        form.addRow(_("certificate_no"), self.txt_certificate_no)

        # الجهة المُصدِرة
        self.txt_issuing_authority = QLineEdit()
        self.txt_issuing_authority.setObjectName("issuing-authority-input")
        self.txt_issuing_authority.setPlaceholderText(_("issuing_authority_placeholder"))
        form.addRow(_("issuing_authority"), self.txt_issuing_authority)

    # ─────────────────────────────────────────────────────────────────────────
    # Data loading
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _search_carrier_companies(q: str = "") -> list:
        """loader للـ SearchableComboBox."""
        try:
            from sqlalchemy import or_
            with get_session_local()() as s:
                qs = s.query(Company).filter_by(is_active=True)
                if q:
                    qf = f"%{q}%"
                    qs = qs.filter(
                        or_(
                            Company.name_ar.ilike(qf),
                            Company.name_en.ilike(qf),
                            Company.name_tr.ilike(qf),
                        )
                    )
                results = qs.order_by(Company.name_ar).limit(60).all()
                s.expunge_all()
                return results
        except Exception:
            return []

    def _carrier_display(self, c, lang: str) -> str:
        name = (
            getattr(c, f"name_{lang}", None)
            or c.name_ar or c.name_en or getattr(c, "name_tr", None) or str(c.id)
        )
        return name

    # ─────────────────────────────────────────────────────────────────────────
    # Get data
    # ─────────────────────────────────────────────────────────────────────────

    def get_transport_data(self) -> dict:
        """
        يُعيد dict ببيانات التبويب.
        القيم الفارغة موجودة كـ None — المنطق في الـ CRUD يتجاهلها إذا كلها None.
        """
        if not hasattr(self, "cmb_carrier"):
            return {}

        # تاريخ الشحن
        shipment_date = None
        if getattr(self, "_shipment_date_set", False):
            qd = self.dt_shipment.date()
            if qd.isValid():
                from datetime import date as _date
                shipment_date = _date(qd.year(), qd.month(), qd.day())

        return {
            "transport": {
                "carrier_company_id": self.cmb_carrier.current_value(),
                "truck_plate":        self.txt_truck_plate.text().strip() or None,
                "driver_name":        self.txt_driver_name.text().strip() or None,
                "loading_place":      self.txt_loading_place.text().strip() or None,
                "delivery_place":     self.txt_delivery_place.text().strip() or None,
                "shipment_date":      shipment_date,
                "attached_documents": self.txt_attached_docs.text().strip() or None,
                "cmr_no":             self.txt_cmr_no.text().strip() or None,
                "certificate_no":     self.txt_certificate_no.text().strip() or None,
                "issuing_authority":  self.txt_issuing_authority.text().strip() or None,
            }
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Prefill (عند تعديل معاملة موجودة)
    # ─────────────────────────────────────────────────────────────────────────

    def prefill_transport(self, trx):
        """يملأ الحقول من كائن معاملة أو TransportDetails."""
        if not hasattr(self, "cmb_carrier"):
            return

        # اجلب TransportDetails من الـ ORM أو من DB مباشرة
        td = None
        if hasattr(trx, "transport_details"):
            td = trx.transport_details
        elif hasattr(trx, "id"):
            try:
                from database.models.transport_details import TransportDetails
                with get_session_local()() as s:
                    td = s.query(TransportDetails).filter_by(
                        transaction_id=trx.id
                    ).first()
            except Exception:
                pass

        if not td:
            return

        _g = lambda attr: getattr(td, attr, None)

        # شركة الناقل
        carrier_id = _g("carrier_company_id")
        if carrier_id:
            companies = self._search_carrier_companies("")
            obj = next((c for c in companies if getattr(c, "id", None) == carrier_id), None)
            if obj:
                lang = getattr(self, "_lang", "ar")
                self.cmb_carrier.set_value(carrier_id, display_text=self._carrier_display(obj, lang))

        # حقول نصية
        for attr, widget in [
            ("cmr_no",             self.txt_cmr_no),
            ("truck_plate",        self.txt_truck_plate),
            ("driver_name",        self.txt_driver_name),
            ("loading_place",      self.txt_loading_place),
            ("delivery_place",     self.txt_delivery_place),
            ("attached_documents", self.txt_attached_docs),
            ("certificate_no",     self.txt_certificate_no),
            ("issuing_authority",  self.txt_issuing_authority),
        ]:
            v = _g(attr)
            if v:
                widget.setText(str(v))

        # تاريخ الشحن
        shipment_date = _g("shipment_date")
        if shipment_date:
            try:
                self.dt_shipment.setDate(
                    QDate(shipment_date.year, shipment_date.month, shipment_date.day)
                )
                self._shipment_date_set = True
            except Exception:
                pass