from core.base_dialog import BaseDialog
from core.translator import TranslationManager

from PySide6.QtWidgets import (
    QVBoxLayout, QLabel, QLineEdit, QTextEdit, QComboBox,
    QCheckBox, QMessageBox, QTabWidget, QScrollArea, QWidget,
    QGridLayout, QDialogButtonBox
)
from PySide6.QtGui import QGuiApplication
try:
    from database.models import get_session_local
except Exception:
    get_session_local = None
from database.crud.delivery_methods_crud import DeliveryMethodsCRUD


def _name_by_lang(obj, lang: str) -> str:
    if not obj:
        return ""
    if lang == "ar" and getattr(obj, "name_ar", None):
        return obj.name_ar
    if lang == "tr" and getattr(obj, "name_tr", None):
        return obj.name_tr
    return getattr(obj, "name_en", None) or getattr(obj, "name_ar", None) or getattr(obj, "name_tr", None) or ""


class AddPricingDialog(BaseDialog):
    """Add/Edit Pricing dialog — أسلوب تبويب قابل للتمرير مثل AddClientDialog."""

    def __init__(self, parent=None, pricing=None, *, sellers=None, buyers=None, materials=None, currencies=None, pricing_types=None):
        super().__init__(parent)
        self._ = TranslationManager.get_instance().translate
        self._lang = TranslationManager.get_instance().get_current_language()

        self.pricing = pricing
        self.sellers = sellers or []
        self.buyers = buyers or []
        self.materials = materials or []
        self.currencies = currencies or []
        self.pricing_types = pricing_types or []

        self.set_translated_title("add_pricing" if pricing is None else "edit_pricing")
        self.init_ui()

    def init_ui(self):
        self.setSizeGripEnabled(True)
        screen_rect = QGuiApplication.primaryScreen().availableGeometry()
        self.setMaximumHeight(int(screen_rect.height() * 0.9))
        self.setMaximumWidth(int(screen_rect.width() * 0.9))

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        tabs = QTabWidget(self)

        # ---------- General ----------
        general = self._make_form_tab()
        r = 0

        # Combos
        self.cmb_seller = QComboBox(); self._fill_companies(self.cmb_seller, self.sellers)
        self._add_row(general, r, "seller_company", self.cmb_seller); r += 1

        self.cmb_buyer  = QComboBox(); self._fill_companies(self.cmb_buyer, self.buyers)
        self._add_row(general, r, "buyer_company", self.cmb_buyer); r += 1

        self.cmb_material = QComboBox(); self._fill_materials()
        self._add_row(general, r, "material", self.cmb_material); r += 1

        self.cmb_ptype = QComboBox(); self._fill_pricing_types()
        self._add_row(general, r, "pricing_type", self.cmb_ptype); r += 1

        self.txt_price = QLineEdit(); self.txt_price.setPlaceholderText("0.0000")
        self._add_row(general, r, "price", self.txt_price); r += 1

        self.cmb_currency = QComboBox(); self._fill_currencies()
        self._add_row(general, r, "currency", self.cmb_currency); r += 1

        # طريقة التسليم اختيارية — نعرض "غير محدد"
        self.cmb_delivery = QComboBox(); self._fill_delivery_methods()
        self._add_row(general, r, "delivery_method", self.cmb_delivery); r += 1

        self.is_active = QCheckBox(self._("active")); self.is_active.setChecked(True)
        self._add_row(general, r, "is_active", self.is_active); r += 1

        self.notes = QTextEdit(); self.notes.setFixedHeight(64)
        self._add_row(general, r, "notes", self.notes); r += 1

        tabs.addTab(general["scroll"], self._tab_title("tab_general", self._("tab_general")))

        root.addWidget(tabs)

        # Prefill
        if self.pricing:
            g = self._get
            self._set_current(self.cmb_seller, g("seller_company_id"))
            self._set_current(self.cmb_buyer,  g("buyer_company_id"))
            self._set_current(self.cmb_material, g("material_id"))
            self._set_current(self.cmb_ptype, g("pricing_type_id"))
            self._set_current(self.cmb_currency, g("currency_id"))
            self._set_current(self.cmb_delivery, g("delivery_method_id"), allow_none=True)

            self.txt_price.setText(str(g("price", "") or ""))
            self.is_active.setChecked(bool(g("is_active", True)))
            self.notes.setText(g("notes", "") or "")

        # Footer
        btn_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, parent=self)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        root.addWidget(btn_box)

    # ---- helpers ----
    def _tab_title(self, key: str, fallback: str) -> str:
        t = self._(key)
        return t if t and t != key else fallback

    def _make_form_tab(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        form = QWidget()
        grid = QGridLayout(form)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        grid.setContentsMargins(8, 8, 8, 8)
        scroll.setWidget(form)
        return {"scroll": scroll, "form": form, "grid": grid}

    def _add_row(self, tab_dict, row_index: int, label_key: str, widget):
        lbl = QLabel(self._(label_key))
        tab_dict["grid"].addWidget(lbl, row_index, 0)
        tab_dict["grid"].addWidget(widget, row_index, 1)

    def _fill_companies(self, combo: QComboBox, companies):
        combo.clear()
        combo.addItem(self._("not_set"), None)
        for c in companies:
            cid = getattr(c, "id", None) if not isinstance(c, dict) else c.get("id")
            lbl = _name_by_lang(c, self._lang)
            combo.addItem(lbl or f"#{cid}", cid)

    def _fill_materials(self):
        self.cmb_material.clear()
        self.cmb_material.addItem(self._("not_set"), None)
        for m in self.materials:
            mid = getattr(m, "id", None) if not isinstance(m, dict) else m.get("id")
            lbl = _name_by_lang(m, self._lang)
            self.cmb_material.addItem(lbl or f"#{mid}", mid)

    def _fill_currencies(self):
        self.cmb_currency.clear()
        self.cmb_currency.addItem(self._("not_set"), None)
        for c in self.currencies:
            cid = getattr(c, "id", None) if not isinstance(c, dict) else c.get("id")
            code = getattr(c, "code", None) if not isinstance(c, dict) else c.get("code")
            symbol = getattr(c, "symbol", None) if not isinstance(c, dict) else c.get("symbol")
            label = (code or "") + (f" ({symbol})" if symbol else "")
            self.cmb_currency.addItem(label or f"#{cid}", cid)

    def _fill_pricing_types(self):
        self.cmb_ptype.clear()
        self.cmb_ptype.addItem(self._("not_set"), None)
        for pt in (self.pricing_types or []):
            pid = getattr(pt, "id", None) if not isinstance(pt, dict) else pt.get("id")
            # عرض الاسم بالترجمة، وإلا الكود
            name = _name_by_lang(pt, self._lang)
            code = getattr(pt, "code", None) if not isinstance(pt, dict) else pt.get("code")
            label = name or code or f"#{pid}"
            self.cmb_ptype.addItem(label, pid)

    def _fill_delivery_methods(self):
        """Fill delivery methods combo from CRUD with ORM fallback + i18n + edit preselect."""
        # تأمين وجود الكومبو
        if not hasattr(self, "cmb_delivery"):
            from PySide6.QtWidgets import QComboBox
            self.cmb_delivery = QComboBox()

        # تفريغ وتعريب أول خيار
        self.cmb_delivery.clear()
        self.cmb_delivery.addItem(self._("not_set"), None)

        methods = None

        # 1) جرّب CRUD
        try:
            from database.crud.delivery_methods_crud import DeliveryMethodsCRUD
            crud = DeliveryMethodsCRUD()
            # إذا الـBaseCRUD يدعم order_by، هي بتشتغل
            methods = crud.get_all(order_by=["sort_order", "id"]) or []
        except Exception:
            methods = None

        # 2) Fallback: ORM مباشر إذا ما رجعت بيانات
        if not methods:
            try:
                from database.models import get_session_local
                from database.models.delivery_method import DeliveryMethod
                SessionLocal = get_session_local()
                with SessionLocal() as s:
                    q = s.query(DeliveryMethod)
                    # فلترة الفعّالين إذا العمود موجود
                    if hasattr(DeliveryMethod, "is_active"):
                        q = q.filter(DeliveryMethod.is_active == True)  # noqa: E712
                    # ترتيب منطقي
                    orders = []
                    if hasattr(DeliveryMethod, "sort_order"):
                        orders.append(DeliveryMethod.sort_order.asc())
                    orders.append(DeliveryMethod.id.asc())
                    q = q.order_by(*orders)
                    methods = q.all()
            except Exception:
                methods = []

        # 3) إذا ما في ولا طريقة، ضيف رسالة ثابتة وخَلّص
        if not methods:
            idx = self.cmb_delivery.count()
            self.cmb_delivery.addItem(self._("no_delivery_methods_defined"), None)
            # خليه disabled حتى ما ينحفظ None بالغلط
            try:
                self.cmb_delivery.model().item(idx).setEnabled(False)
            except Exception:
                pass
            return

        # 4) تعبئة القائمة حسب اللغة
        lang = getattr(self, "_lang", "ar")

        def _label(m):
            nar = getattr(m, "name_ar", None)
            nen = getattr(m, "name_en", None)
            ntr = getattr(m, "name_tr", None)
            return (nar if lang == "ar" and nar else
                    ntr if lang == "tr" and ntr else
                    (nen or nar or ntr or f"#{getattr(m, 'id', '')}"))

        for m in methods:
            self.cmb_delivery.addItem(_label(m), getattr(m, "id", None))

        # 5) بوضع التعديل: اختَر القيمة الحالية إذا موجودة
        sel_id = None
        try:
            sel_id = getattr(getattr(self, "pricing", None), "delivery_method_id", None)
        except Exception:
            sel_id = None

        if sel_id:
            idx = self.cmb_delivery.findData(sel_id)
            if idx != -1:
                self.cmb_delivery.setCurrentIndex(idx)

    def _set_current(self, combo: QComboBox, value, *, allow_none=False):
        if value is None and allow_none:
            combo.setCurrentIndex(0)
            return
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i); return

    def _get(self, key, default=None):
        if isinstance(self.pricing, dict):
            return self.pricing.get(key, default)
        return getattr(self.pricing, key, default)

    # ---- data & validation ----
    def get_data(self):
        return {
            "seller_company_id": self.cmb_seller.currentData(),
            "buyer_company_id":  self.cmb_buyer.currentData(),
            "material_id":       self.cmb_material.currentData(),
            "pricing_type_id":   self.cmb_ptype.currentData(),
            "price":             (self.txt_price.text() or "").strip(),
            "currency_id":       self.cmb_currency.currentData(),
            "delivery_method_id": self.cmb_delivery.currentData(),  # None مسموح
            "notes":             (self.notes.toPlainText() or "").strip(),
            "is_active":         self.is_active.isChecked(),
        }

    def accept(self):
        d = self.get_data()
        errors = []

        # required combos
        req = {
            "seller_company_id": "seller_company",
            "buyer_company_id":  "buyer_company",
            "material_id":       "material",
            "pricing_type_id":   "pricing_type",
            "currency_id":       "currency",
        }
        for k, lbl in req.items():
            if not d.get(k):
                errors.append(self._(lbl) + " " + self._("is_required"))

        # price
        try:
            price = float(d.get("price", "0").replace(",", "."))
            if price <= 0:
                raise ValueError
            d["price"] = price
        except Exception:
            errors.append(self._("price") + " " + self._("must_be_positive"))

        if errors:
            QMessageBox.warning(self, self._("invalid_data"), "\n".join(errors))
            return

        # خزّن النتيجة (قد تحتاجها الجهة المستدعية)
        self._result = d
        super().accept()

    def get_result(self):
        return getattr(self, "_result", {})
