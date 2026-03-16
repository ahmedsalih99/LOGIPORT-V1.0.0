"""
parties_geo_tab.py — v3  (SearchableComboBox للعملاء والشركات)

التغيير الرئيسي:
  - cmb_client / cmb_exporter / cmb_importer / cmb_broker
    أصبحت SearchableComboBox بدل QComboBox عادية
  - باقي الـ API ثابت تماماً (get_parties_data / prefill_parties_geo ...)
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QFrame,
    QFormLayout, QComboBox, QLabel, QSizePolicy, QScrollArea
)
from PySide6.QtCore import Qt
from ui.utils.wheel_blocker import block_wheel_in

from database.models import get_session_local, Country, DeliveryMethod
from ui.widgets.searchable_combo import SearchableComboBox


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

        # ── SearchableComboBox: العميل ───────────────────────────────────────
        self.cmb_client = SearchableComboBox(parent=inner)
        self.cmb_client.setObjectName("client-combo")
        self.cmb_client.set_loader(
            loader=self._load_clients_search,
            display=self._client_display,
            value=lambda c: c.id,
        )

        # ── SearchableComboBox: شركة المُصدِّر ───────────────────────────────
        self.cmb_exporter = SearchableComboBox(parent=inner)
        self.cmb_exporter.setObjectName("exporter-combo")
        self.cmb_exporter.set_loader(
            loader=self._load_companies_search,
            display=self._company_display,
            value=lambda c: c.id,
        )

        # ── SearchableComboBox: شركة المُستورِد ──────────────────────────────
        self.cmb_importer = SearchableComboBox(parent=inner)
        self.cmb_importer.setObjectName("importer-combo")
        self.cmb_importer.set_loader(
            loader=self._load_companies_search,
            display=self._company_display,
            value=lambda c: c.id,
        )

        # ── QComboBox: نوع العلاقة (ثابت — لا يحتاج بحث) ────────────────────
        self.cmb_relationship = self._create_combo()
        self.cmb_relationship.setObjectName("relationship-combo")
        self.cmb_relationship.addItem(self._("direct"),    "direct")
        self.cmb_relationship.addItem(self._("via_broker"), "via_broker")
        self.cmb_relationship.currentIndexChanged.connect(self._on_relationship_changed)

        # ── SearchableComboBox: الوسيط ───────────────────────────────────────
        self.cmb_broker = SearchableComboBox(parent=inner)
        self.cmb_broker.setObjectName("broker-combo")
        self.cmb_broker.set_loader(
            loader=self._load_companies_search,
            display=self._company_display,
            value=lambda c: c.id,
        )

        left_form.addRow(self._sec_lbl(self._("parties_section")), None)
        left_form.addRow(self._fld_lbl(self._("client")),            self.cmb_client)
        left_form.addRow(self._fld_lbl(self._("exporter_company")),  self.cmb_exporter)
        left_form.addRow(self._fld_lbl(self._("importer_company")),  self.cmb_importer)
        left_form.addRow(self._fld_lbl(self._("relationship_type")), self.cmb_relationship)
        left_form.addRow(self._fld_lbl(self._("broker_company")),    self.cmb_broker)

        # ── العمود الأيمن: الجغرافيا والتسليم ─────────────────────────────
        right_card = QFrame()
        right_card.setObjectName("form-card")
        right_form = QFormLayout(right_card)
        right_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        right_form.setHorizontalSpacing(12)
        right_form.setVerticalSpacing(10)
        right_form.setContentsMargins(16, 16, 16, 16)

        self.cmb_origin_country  = self._create_combo()
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

        self._load_static_lists()
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

    def _create_section_label(self, text): return self._sec_lbl(text)
    def _create_form_label(self, text):    return self._fld_lbl(text)

    # ── loaders للـ SearchableComboBox ──────────────────────────────────────
    @staticmethod
    def _load_clients_search(q: str = "") -> list:
        try:
            from database.crud.clients_crud import ClientsCRUD
            all_clients = ClientsCRUD().list_clients()
            if not q:
                return all_clients[:60]
            q = q.casefold()
            return [
                c for c in all_clients
                if q in (getattr(c, "name_ar", "") or "").casefold()
                or q in (getattr(c, "name_en", "") or "").casefold()
                or q in (getattr(c, "name_tr", "") or "").casefold()
                or q in (getattr(c, "client_code", "") or "").casefold()
            ][:60]
        except Exception:
            return []

    @staticmethod
    def _load_companies_search(q: str = "") -> list:
        try:
            from database.models import get_session_local
            from database.models.company import Company
            from sqlalchemy import or_
            with get_session_local()() as s:
                qs = s.query(Company)
                if q:
                    qf = f"%{q}%"
                    qs = qs.filter(
                        or_(
                            Company.name_ar.ilike(qf),
                            Company.name_en.ilike(qf),
                            Company.name_tr.ilike(qf),
                        )
                    )
                results = qs.order_by(Company.id).limit(60).all()
                s.expunge_all()
                return results
        except Exception:
            return []

    def _client_display(self, c, lang: str) -> str:
        if lang.startswith("ar"):
            name = getattr(c, "name_ar", None) or getattr(c, "name_en", None) or getattr(c, "name_tr", None)
        elif lang.startswith("tr"):
            name = getattr(c, "name_tr", None) or getattr(c, "name_ar", None) or getattr(c, "name_en", None)
        else:
            name = getattr(c, "name_en", None) or getattr(c, "name_ar", None) or getattr(c, "name_tr", None)
        return (name or "").strip() or f"#{c.id}"

    def _company_display(self, c, lang: str) -> str:
        if lang.startswith("ar"):
            name = getattr(c, "name_ar", None) or getattr(c, "name_en", None) or getattr(c, "name_tr", None)
        elif lang.startswith("tr"):
            name = getattr(c, "name_tr", None) or getattr(c, "name_ar", None) or getattr(c, "name_en", None)
        else:
            name = getattr(c, "name_en", None) or getattr(c, "name_ar", None) or getattr(c, "name_tr", None)
        return (name or "").strip() or f"#{c.id}"

    # ── قوائم ثابتة (دول + طرق التسليم — قصيرة لا تحتاج بحث) ───────────────
    def _best_label(self, obj) -> str:
        """يعيد أفضل اسم للـ object حسب اللغة الحالية."""
        lang = getattr(self, "_lang", "ar") or "ar"
        for f in (f"name_{lang}", "name_ar", "name_en", "name_tr", "name"):
            if hasattr(obj, f) and getattr(obj, f):
                return str(getattr(obj, f))
        return str(getattr(obj, "id", "?"))

    def _fill_static_combo(self, combo, rows, *, map_store: dict):
        """يملأ QComboBox ثابتة (دول / طرق تسليم) ويبني خريطة للبحث بالنص."""
        combo.clear()
        combo.addItem(self._("select"), None)
        for r in rows:
            label = self._best_label(r)
            rid   = getattr(r, "id", None)
            combo.addItem(label, rid)
            map_store[label.strip().lower()] = rid

    def _load_static_lists(self):
        self._country_map  = {}
        self._delivery_map = {}

        SessionLocal = get_session_local()
        with SessionLocal() as s:
            countries = s.query(Country).order_by(Country.id).all()
            try:
                delivery_methods = s.query(DeliveryMethod).order_by(
                    DeliveryMethod.sort_order, DeliveryMethod.id
                ).all()
            except Exception:
                delivery_methods = []

        self._fill_static_combo(self.cmb_origin_country,  countries,        map_store=self._country_map)
        self._fill_static_combo(self.cmb_dest_country,    countries,        map_store=self._country_map)
        self._fill_static_combo(self.cmb_delivery_method, delivery_methods, map_store=self._delivery_map)

    # backward-compat: بعض الأماكن تستدعي _load_parties_geo_lists مباشرة
    def _load_parties_geo_lists(self):
        self._load_static_lists()

    # ── events ──────────────────────────────────────────────────────────────
    def _on_relationship_changed(self):
        rel       = self.cmb_relationship.currentData()
        is_broker = (rel == "via_broker")
        self.cmb_broker.setEnabled(is_broker)
        if not is_broker:
            self.cmb_broker.set_value(None, "")

    # ── data getters ────────────────────────────────────────────────────────
    def _id_from_static_combo(self, combo, *, delivery=False):
        """يجلب ID من QComboBox عادية (دول / طرق تسليم)."""
        val = combo.currentData()
        if val not in (None, ""):
            try:
                return int(val)
            except Exception:
                return val
        txt = (combo.currentText() or "").strip().lower()
        if not txt:
            return None
        if delivery:
            return self._delivery_map.get(txt)
        return self._country_map.get(txt)

    def get_parties_data(self):
        rel       = self.cmb_relationship.currentData()
        broker_id = self.cmb_broker.current_value() if rel == "via_broker" else None
        return {
            "client_id":           self.cmb_client.current_value(),
            "exporter_company_id": self.cmb_exporter.current_value(),
            "importer_company_id": self.cmb_importer.current_value(),
            "relationship_type":   rel or "direct",
            "broker_company_id":   broker_id,
            "delivery_method_id":  self._id_from_static_combo(self.cmb_delivery_method, delivery=True),
            "origin_country_id":   self._id_from_static_combo(self.cmb_origin_country),
            "dest_country_id":     self._id_from_static_combo(self.cmb_dest_country),
        }

    def get_parties_geo_data(self):
        return self.get_parties_data()

    # ── prefill ─────────────────────────────────────────────────────────────
    def _set_combo_by_id(self, combo, rid):
        """backward-compat للـ QComboBox العادية (دول / طرق تسليم)."""
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
            self._load_static_lists()
        except Exception:
            pass

        get = (lambda o, k, d=None: o.get(k, d) if isinstance(o, dict) else getattr(o, k, d))

        # SearchableComboBox — set_value بالـ ID والـ display text
        def _set_searchable(combo, record_id, display_fn, loader_fn):
            if not record_id:
                return
            try:
                objs = loader_fn("")
                obj  = next((o for o in objs if getattr(o, "id", None) == record_id), None)
                if obj:
                    lang = getattr(self, "_lang", "ar") or "ar"
                    text = display_fn(obj, lang)
                    combo.set_value(record_id, display_text=text)
            except Exception:
                pass

        _set_searchable(self.cmb_client,   get(trx, "client_id"),
                        self._client_display,  self._load_clients_search)
        _set_searchable(self.cmb_exporter, get(trx, "exporter_company_id"),
                        self._company_display, self._load_companies_search)
        _set_searchable(self.cmb_importer, get(trx, "importer_company_id"),
                        self._company_display, self._load_companies_search)
        _set_searchable(self.cmb_broker,   get(trx, "broker_company_id"),
                        self._company_display, self._load_companies_search)

        rel = get(trx, "relationship_type", "direct") or "direct"
        for i in range(self.cmb_relationship.count()):
            if self.cmb_relationship.itemData(i) == rel:
                self.cmb_relationship.setCurrentIndex(i)
                break
        self._on_relationship_changed()

        self._set_combo_by_id(self.cmb_delivery_method, get(trx, "delivery_method_id"))
        self._set_combo_by_id(self.cmb_origin_country,  get(trx, "origin_country_id"))
        self._set_combo_by_id(self.cmb_dest_country,    get(trx, "dest_country_id"))

    def refresh_language_parties_geo(self):
        self._load_static_lists()

    # ── combo factory (للـ QComboBox العادية فقط) ────────────────────────────
    def _create_combo(self, max_width=9999):
        combo = QComboBox()
        combo.setObjectName("form-combo")
        combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        if max_width < 9999:
            combo.setMaximumWidth(max_width)
        combo.setMinimumHeight(36)
        return combo