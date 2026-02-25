"""
parties_geo_tab.py — v2  (تصميم عمودين جنب بعض)

التغيير الرئيسي:
  العمود الأيسر  : الأطراف  (client, exporter, importer, relationship, broker)
  العمود الأيمن : الجغرافيا والتسليم  (origin, dest, delivery_method)

باقي الـ API ثابت تماماً.
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QFrame,
    QFormLayout, QComboBox, QLabel, QSizePolicy, QScrollArea
)
from PySide6.QtCore import Qt
from database.models import get_session_local, Client, Company, Country, DeliveryMethod


class PartiesGeoTabMixin:

    def _build_parties_geo_tab(self):
        self.tab_parties = QWidget()
        self.tab_parties.setObjectName("parties-tab")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("parties-scroll")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        inner = QWidget()
        inner.setObjectName("parties-inner")
        outer_lay = QVBoxLayout(inner)
        outer_lay.setContentsMargins(16, 16, 16, 16)
        outer_lay.setSpacing(12)

        cols_row = QHBoxLayout()
        cols_row.setSpacing(16)

        # ── العمود الأيسر: الأطراف ──────────────────────────────────────────
        left_card = QFrame()
        left_card.setObjectName("form-card")
        left_form = QFormLayout(left_card)
        left_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        left_form.setHorizontalSpacing(12)
        left_form.setVerticalSpacing(10)
        left_form.setContentsMargins(16, 16, 16, 16)

        self.cmb_client = self._create_combo()
        self.cmb_client.setObjectName("client-combo")

        self.cmb_exporter = self._create_combo()
        self.cmb_exporter.setObjectName("exporter-combo")

        self.cmb_importer = self._create_combo()
        self.cmb_importer.setObjectName("importer-combo")

        self.cmb_relationship = self._create_combo()
        self.cmb_relationship.setObjectName("relationship-combo")
        self.cmb_relationship.addItem(self._("direct"),    "direct")
        self.cmb_relationship.addItem(self._("via_broker"), "via_broker")
        self.cmb_relationship.currentIndexChanged.connect(self._on_relationship_changed)

        self.cmb_broker = self._create_combo()
        self.cmb_broker.setObjectName("broker-combo")

        left_form.addRow(self._sec_lbl(self._("parties_section")), None)
        left_form.addRow(self._fld_lbl(self._("client")),           self.cmb_client)
        left_form.addRow(self._fld_lbl(self._("exporter_company")), self.cmb_exporter)
        left_form.addRow(self._fld_lbl(self._("importer_company")), self.cmb_importer)
        left_form.addRow(self._fld_lbl(self._("relationship_type")),self.cmb_relationship)
        left_form.addRow(self._fld_lbl(self._("broker_company")),   self.cmb_broker)

        # ── العمود الأيمن: الجغرافيا والتسليم ─────────────────────────────
        right_card = QFrame()
        right_card.setObjectName("form-card")
        right_form = QFormLayout(right_card)
        right_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        right_form.setHorizontalSpacing(12)
        right_form.setVerticalSpacing(10)
        right_form.setContentsMargins(16, 16, 16, 16)

        self.cmb_origin_country = self._create_combo()
        self.cmb_origin_country.setObjectName("origin-country-combo")

        self.cmb_dest_country = self._create_combo()
        self.cmb_dest_country.setObjectName("dest-country-combo")

        self.cmb_delivery_method = self._create_combo()
        self.cmb_delivery_method.setObjectName("delivery-method-combo")

        right_form.addRow(self._sec_lbl(self._("geography_delivery")), None)
        right_form.addRow(self._fld_lbl(self._("origin_country")),     self.cmb_origin_country)
        right_form.addRow(self._fld_lbl(self._("dest_country")),       self.cmb_dest_country)
        right_form.addRow(self._fld_lbl(self._("delivery_method")),    self.cmb_delivery_method)

        cols_row.addWidget(left_card,  stretch=1)
        cols_row.addWidget(right_card, stretch=1)

        outer_lay.addLayout(cols_row)
        outer_lay.addStretch()

        scroll.setWidget(inner)

        tab_lay = QVBoxLayout(self.tab_parties)
        tab_lay.setContentsMargins(0, 0, 0, 0)
        tab_lay.addWidget(scroll)

        self.tabs.addTab(self.tab_parties, self._("parties_and_geography"))

        self._load_parties_geo_lists()
        self.cmb_relationship.setCurrentIndex(0)
        self._on_relationship_changed()

    # ── label helpers ───────────────────────────────────────────────────────
    def _sec_lbl(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("section-label")
        return lbl

    def _fld_lbl(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("form-label")
        return lbl

    # backward-compat aliases
    def _create_section_label(self, text): return self._sec_lbl(text)
    def _create_form_label(self, text):    return self._fld_lbl(text)

    # ── data loading ────────────────────────────────────────────────────────
    def _load_parties_geo_lists(self):
        self._client_map   = {}
        self._company_map  = {}
        self._country_map  = {}
        self._delivery_map = {}

        def best_label(obj):
            lang = getattr(self, "_lang", "ar") or "ar"
            for f in (f"name_{lang}", "name_ar", "name_en", "name_tr", "name"):
                if hasattr(obj, f) and getattr(obj, f):
                    return str(getattr(obj, f))
            return str(getattr(obj, "id", "?"))

        def fill_combo(combo, rows, *, map_store):
            combo.clear()
            combo.addItem(self._("select"), None)
            for r in rows:
                label = best_label(r)
                rid   = getattr(r, "id", None)
                combo.addItem(label, rid)
                map_store[label.strip().lower()] = rid

        SessionLocal = get_session_local()
        with SessionLocal() as s:
            clients   = s.query(Client).order_by(Client.id).all()
            companies = s.query(Company).order_by(Company.id).all()
            countries = s.query(Country).order_by(Country.id).all()
            try:
                delivery_methods = s.query(DeliveryMethod).order_by(
                    DeliveryMethod.sort_order, DeliveryMethod.id
                ).all()
            except Exception:
                delivery_methods = []

        self._company_name_to_id = {}
        for c in companies:
            for f in ("name_ar", "name_en", "name_tr", "name"):
                v = getattr(c, f, None)
                if v:
                    self._company_name_to_id[str(v).strip().lower()] = getattr(c, "id", None)

        fill_combo(self.cmb_client,          clients,          map_store=self._client_map)
        fill_combo(self.cmb_exporter,        companies,        map_store=self._company_map)
        fill_combo(self.cmb_importer,        companies,        map_store=self._company_map)
        fill_combo(self.cmb_broker,          companies,        map_store=self._company_map)
        fill_combo(self.cmb_origin_country,  countries,        map_store=self._country_map)
        fill_combo(self.cmb_dest_country,    countries,        map_store=self._country_map)
        fill_combo(self.cmb_delivery_method, delivery_methods, map_store=self._delivery_map)

    # ── events ──────────────────────────────────────────────────────────────
    def _on_relationship_changed(self):
        rel       = self.cmb_relationship.currentData()
        is_broker = (rel == "via_broker")
        self.cmb_broker.setEnabled(is_broker)
        self.cmb_broker.setProperty("inactive", not is_broker)
        self.cmb_broker.style().unpolish(self.cmb_broker)
        self.cmb_broker.style().polish(self.cmb_broker)
        if not is_broker:
            self.cmb_broker.setCurrentIndex(0)

    # ── data getters ────────────────────────────────────────────────────────
    def _id_or_map(self, combo, *, company=False, delivery=False):
        val = combo.currentData()
        if val not in (None, ""):
            try:
                return int(val)
            except Exception:
                return val
        txt = (combo.currentText() or "").strip().lower()
        if not txt:
            return None
        if company:
            return self._company_name_to_id.get(txt)
        if delivery:
            return self._delivery_map.get(txt)
        return self._client_map.get(txt) or self._country_map.get(txt)

    def get_parties_data(self):
        rel       = self.cmb_relationship.currentData()
        broker_id = self._id_or_map(self.cmb_broker, company=True) if rel == "via_broker" else None
        return {
            "client_id":           self._id_or_map(self.cmb_client),
            "exporter_company_id": self._id_or_map(self.cmb_exporter,  company=True),
            "importer_company_id": self._id_or_map(self.cmb_importer,  company=True),
            "relationship_type":   rel or "direct",
            "broker_company_id":   broker_id,
            "delivery_method_id":  self._id_or_map(self.cmb_delivery_method, delivery=True),
            "origin_country_id":   self._id_or_map(self.cmb_origin_country),
            "dest_country_id":     self._id_or_map(self.cmb_dest_country),
        }

    def get_parties_geo_data(self):
        return self.get_parties_data()

    # ── prefill ─────────────────────────────────────────────────────────────
    def _set_combo_by_id(self, combo, rid):
        if rid in (None, ""):
            return
        for i in range(combo.count()):
            if combo.itemData(i) == rid:
                combo.setCurrentIndex(i)
                return

    def prefill_parties_geo(self, trx):
        if not trx:
            return
        try:
            self._load_parties_geo_lists()
        except Exception:
            pass

        get = (lambda o, k, d=None: o.get(k, d) if isinstance(o, dict) else getattr(o, k, d))

        self._set_combo_by_id(self.cmb_client,   get(trx, "client_id"))
        self._set_combo_by_id(self.cmb_exporter,  get(trx, "exporter_company_id"))
        self._set_combo_by_id(self.cmb_importer,  get(trx, "importer_company_id"))

        rel = get(trx, "relationship_type", "direct") or "direct"
        for i in range(self.cmb_relationship.count()):
            if self.cmb_relationship.itemData(i) == rel:
                self.cmb_relationship.setCurrentIndex(i)
                break
        self._on_relationship_changed()

        self._set_combo_by_id(self.cmb_broker,          get(trx, "broker_company_id"))
        self._set_combo_by_id(self.cmb_delivery_method, get(trx, "delivery_method_id"))
        self._set_combo_by_id(self.cmb_origin_country,  get(trx, "origin_country_id"))
        self._set_combo_by_id(self.cmb_dest_country,    get(trx, "dest_country_id"))

    def refresh_language_parties_geo(self):
        self._load_parties_geo_lists()

    # ── combo factory ────────────────────────────────────────────────────────
    def _create_combo(self, max_width=9999):
        combo = QComboBox()
        combo.setObjectName("form-combo")
        combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        if max_width < 9999:
            combo.setMaximumWidth(max_width)
        combo.setMinimumHeight(36)
        return combo