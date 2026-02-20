from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QFormLayout, QComboBox, QLabel
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSizePolicy
from database.models import get_session_local, Client, Company, Country, DeliveryMethod


class PartiesGeoTabMixin:

    # ------------------------ بناء التبويب ------------------------
    def _build_parties_geo_tab(self):
        self.tab_parties = QWidget(self)
        self.tab_parties.setObjectName("parties-tab")

        v = QVBoxLayout(self.tab_parties)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(12)

        # البطاقة الرئيسية
        card = QFrame(self.tab_parties)
        card.setObjectName("form-card")

        form = QFormLayout(card)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(12)
        form.setContentsMargins(20, 20, 20, 20)

        # ================= Combos =================
        self.cmb_client = self._create_combo()
        self.cmb_client.setObjectName("client-combo")

        self.cmb_exporter = self._create_combo()
        self.cmb_exporter.setObjectName("exporter-combo")

        self.cmb_importer = self._create_combo()
        self.cmb_importer.setObjectName("importer-combo")

        self.cmb_broker = self._create_combo()
        self.cmb_broker.setObjectName("broker-combo")

        self.cmb_delivery_method = self._create_combo()
        self.cmb_delivery_method.setObjectName("delivery-method-combo")

        self.cmb_origin_country = self._create_combo()
        self.cmb_origin_country.setObjectName("origin-country-combo")

        self.cmb_dest_country = self._create_combo()
        self.cmb_dest_country.setObjectName("dest-country-combo")

        self.cmb_relationship = self._create_combo(max_width=220)
        self.cmb_relationship.setObjectName("relationship-combo")
        self.cmb_relationship.addItem(self._("direct"), "direct")
        self.cmb_relationship.addItem(self._("via_broker"), "via_broker")
        self.cmb_relationship.currentIndexChanged.connect(self._on_relationship_changed)

        # ================= Form layout =================
        # Parties
        form.addRow(self._create_section_label(self._("parties_section")), None)
        form.addRow(self._create_form_label(self._("client")), self.cmb_client)
        form.addRow(self._create_form_label(self._("exporter_company")), self.cmb_exporter)
        form.addRow(self._create_form_label(self._("importer_company")), self.cmb_importer)
        form.addRow(self._create_form_label(self._("relationship_type")), self.cmb_relationship)
        form.addRow(self._create_form_label(self._("broker_company")), self.cmb_broker)

        # Spacer
        spacer = QLabel("")
        spacer.setFixedHeight(8)
        form.addRow(spacer, None)

        # Geography & delivery
        form.addRow(self._create_section_label(self._("geography_delivery")), None)
        form.addRow(self._create_form_label(self._("origin_country")), self.cmb_origin_country)
        form.addRow(self._create_form_label(self._("dest_country")), self.cmb_dest_country)
        form.addRow(self._create_form_label(self._("delivery_method")), self.cmb_delivery_method)

        v.addWidget(card)
        v.addStretch()

        self.tabs.addTab(self.tab_parties, self._("parties_and_geography"))

        # ================= Data =================
        self._load_parties_geo_lists()
        self.cmb_relationship.setCurrentIndex(0)
        self._on_relationship_changed()

    # ------------------------ UI Helpers ------------------------
    def _create_section_label(self, text: str) -> QLabel:
        """إنشاء label للقسم"""
        label = QLabel(text)
        label.setObjectName("section-label")
        return label

    def _create_form_label(self, text: str) -> QLabel:
        """إنشاء label للحقل"""
        label = QLabel(text)
        label.setObjectName("form-label")
        return label

    # ------------------------ تعبئة البيانات ------------------------
    def _load_parties_geo_lists(self):
        self._client_map = {}
        self._company_map = {}
        self._country_map = {}
        self._delivery_map = {}

        def best_label(obj):
            lang = getattr(self, "_lang", "ar") or "ar"
            for f in (f"name_{lang}", "name_ar", "name_en", "name_tr", "name"):
                if hasattr(obj, f) and getattr(obj, f):
                    return str(getattr(obj, f))
            return str(getattr(obj, "id", "?"))

        def fill_combo(combo: QComboBox, rows, *, map_store: dict):
            combo.clear()
            combo.addItem(self._("select"), None)
            for r in rows:
                label = best_label(r)
                rid = getattr(r, "id", None)
                combo.addItem(label, rid)
                map_store[label.strip().lower()] = rid

        SessionLocal = get_session_local()
        with SessionLocal() as s:
            clients = s.query(Client).order_by(Client.id).all()
            companies = s.query(Company).order_by(Company.id).all()
            countries = s.query(Country).order_by(Country.id).all()
            try:
                delivery_methods = s.query(DeliveryMethod).order_by(
                    DeliveryMethod.sort_order, DeliveryMethod.id
                ).all()
            except Exception:
                delivery_methods = []

        # لسهولة البحث بالاسم عبر جميع الشركات
        self._company_name_to_id = {}
        for c in companies:
            for f in ("name_ar", "name_en", "name_tr", "name"):
                v = getattr(c, f, None)
                if v:
                    self._company_name_to_id[str(v).strip().lower()] = getattr(c, "id", None)

        fill_combo(self.cmb_client, clients, map_store=self._client_map)
        fill_combo(self.cmb_exporter, companies, map_store=self._company_map)
        fill_combo(self.cmb_importer, companies, map_store=self._company_map)
        fill_combo(self.cmb_broker, companies, map_store=self._company_map)
        fill_combo(self.cmb_origin_country, countries, map_store=self._country_map)
        fill_combo(self.cmb_dest_country, countries, map_store=self._country_map)
        fill_combo(self.cmb_delivery_method, delivery_methods, map_store=self._delivery_map)

    # ------------------------ أحداث ------------------------
    def _on_relationship_changed(self):
        rel = self.cmb_relationship.currentData()
        is_broker = (rel == "via_broker")

        self.cmb_broker.setEnabled(is_broker)
        self.cmb_broker.setProperty("inactive", not is_broker)

        self.cmb_broker.style().unpolish(self.cmb_broker)
        self.cmb_broker.style().polish(self.cmb_broker)

        if not is_broker:
            self.cmb_broker.setCurrentIndex(0)

    # ------------------------ تجميع البيانات ------------------------
    def _id_or_map(self, combo: QComboBox, *, company=False, delivery=False) -> int | None:
        """أرجع currentData، وإن كان None حاول استنتاج الـ id من currentText عبر الخرائط."""
        val = combo.currentData()
        if val not in (None, ""):
            try:
                return int(val)
            except Exception:
                return val
        # fallback بالاسم
        txt = (combo.currentText() or "").strip().lower()
        if not txt:
            return None
        if company:
            return self._company_name_to_id.get(txt)
        if delivery:
            return self._delivery_map.get(txt)
        # عمومًا
        return self._client_map.get(txt) or self._country_map.get(txt)

    def get_parties_data(self) -> dict:
        rel = self.cmb_relationship.currentData()
        broker_id = self._id_or_map(self.cmb_broker, company=True) if rel == "via_broker" else None
        return {
            "client_id": self._id_or_map(self.cmb_client),
            "exporter_company_id": self._id_or_map(self.cmb_exporter, company=True),
            "importer_company_id": self._id_or_map(self.cmb_importer, company=True),
            "relationship_type": rel or "direct",
            "broker_company_id": broker_id,
            "delivery_method_id": self._id_or_map(self.cmb_delivery_method, delivery=True),
            "origin_country_id": self._id_or_map(self.cmb_origin_country),
            "dest_country_id": self._id_or_map(self.cmb_dest_country),
        }

    def get_parties_geo_data(self) -> dict:
        """Alias for compatibility"""
        return self.get_parties_data()

    def refresh_language_parties_geo(self):
        # إعادة تعبئة عند تبديل اللغة
        self._load_parties_geo_lists()

    def _set_combo_by_id(self, combo, rid):
        """حرّك الكومبوبوكس إلى الـ id المطلوب إن وُجد."""
        if rid in (None, ""):
            return
        for i in range(combo.count()):
            if combo.itemData(i) == rid:
                combo.setCurrentIndex(i)
                return

    def prefill_parties_geo(self, trx):
        """تعبئة تبويب الأطراف والجغرافيا من كائن/قاموس المعاملة."""
        if not trx:
            return
        # تأكد أن القوائم محمّلة
        try:
            self._load_parties_geo_lists()
        except Exception:
            pass

        get = (lambda o, k, d=None: o.get(k, d) if isinstance(o, dict) else getattr(o, k, d))

        self._set_combo_by_id(self.cmb_client, get(trx, "client_id"))
        self._set_combo_by_id(self.cmb_exporter, get(trx, "exporter_company_id"))
        self._set_combo_by_id(self.cmb_importer, get(trx, "importer_company_id"))

        # نوع العلاقة
        rel = get(trx, "relationship_type", "direct") or "direct"
        for i in range(self.cmb_relationship.count()):
            if self.cmb_relationship.itemData(i) == rel:
                self.cmb_relationship.setCurrentIndex(i)
                break
        self._on_relationship_changed()

        # الوسيط (يُفعّل فقط إن كانت العلاقة عبر وسيط)
        self._set_combo_by_id(self.cmb_broker, get(trx, "broker_company_id"))

        # طريقة التسليم
        self._set_combo_by_id(self.cmb_delivery_method, get(trx, "delivery_method_id"))
        # الدول
        self._set_combo_by_id(self.cmb_origin_country, get(trx, "origin_country_id"))
        self._set_combo_by_id(self.cmb_dest_country, get(trx, "dest_country_id"))

    def _create_combo(self, max_width=280):
        """إنشاء ComboBox مخصص"""
        combo = QComboBox()
        combo.setObjectName("form-combo")
        combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        combo.setMaximumWidth(max_width)
        combo.setMinimumHeight(36)  # ارتفاع أكبر قليلاً
        return combo
