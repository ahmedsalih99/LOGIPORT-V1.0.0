from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QMessageBox, QHeaderView
)

# CRUD
try:
    from database.crud.entries_crud import EntriesCRUD
except Exception:
    EntriesCRUD = None  # type: ignore

# ترجمة + صلاحيات
try:
    from core.translator import TranslationManager
    _T = TranslationManager.get_instance()
    _ = _T.translate
    get_lang = _T.get_current_language
except Exception:
    _ = lambda k: k
    get_lang = lambda: "ar"

try:
    from core.permissions import is_admin
except Exception:
    def is_admin(user):  # fallback
        return False


def _safe_str(val, fallback="") -> str:
    s = "" if val is None else str(val)
    if s.strip().lower() == "none":
        s = ""
    return s if s else fallback


def _fmt_num(x, digits=2):
    try:
        v = float(x)
        return f"{v:,.{digits}f}"
    except Exception:
        return "0"


def _pick(row: dict, *keys, default=None):
    """يرجع أول قيمة متاحة من بين مجموعة مفاتيح."""
    for k in keys:
        if k in row and row[k] not in (None, "", "None"):
            return row[k]
    return default


class EntriesPickerDialog(QDialog):
    """
    - عمود واحد لرقم الإدخال (يُعرض من transport_ref/entry_no).
    - عمود ID يظهر للأدمن فقط.
    - اختيار متعدّد عبر CheckBox في العمود الأول.
    """
    picked = Signal(list)  # [{entry_id, entry_no, items: [...]}]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("EntriesPickerDialog")
        self.setWindowTitle(_("select_entries"))
        self.resize(980, 620)
        self.current_user = getattr(parent, "current_user", None)

        # اتّجاه الواجهة حسب اللغة
        self.setLayoutDirection(Qt.RightToLeft if get_lang() == "ar" else Qt.LeftToRight)

        v = QVBoxLayout(self)

        # ===== الجدول =====
        # 5 أعمدة: [✔] [ID] [رقم الإدخال] [العميل] [إجمالي الوزن الصافي]
        self.tbl = QTableWidget(0, 5, self)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setWordWrap(False)
        self.tbl.setShowGrid(True)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl.setSelectionMode(QTableWidget.SingleSelection)
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl.setHorizontalHeaderLabels([
            "✔",
            _("id"),
            _("entry_no"),
            _("client"),
            _("total_net_weight")
        ])

        hh = self.tbl.horizontalHeader()
        hh.setStretchLastSection(True)
        for c in range(self.tbl.columnCount()):
            hh.setSectionResizeMode(c, QHeaderView.Stretch)
        self.tbl.setColumnWidth(0, 40)   # checkbox
        self.tbl.setColumnWidth(1, 80)   # id (قد يُخفى)

        v.addWidget(self.tbl)

        # ===== الأزرار =====
        foot = QHBoxLayout()
        foot.addStretch()
        self.btn_cancel = QPushButton(_("cancel"))
        self.btn_ok = QPushButton(_("add_selected"))
        foot.addWidget(self.btn_cancel)
        foot.addWidget(self.btn_ok)
        v.addLayout(foot)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok.clicked.connect(self._on_ok)

        # تحميل البيانات
        self._load()

        # إخفاء عمود الـ ID لغير الأدمن
        try:
            self.tbl.setColumnHidden(1, not is_admin(self.current_user))
        except Exception:
            pass

    # ---------------------- data loading ----------------------
    def _load(self):
        self.tbl.setRowCount(0)
        rows = []
        if EntriesCRUD:
            try:
                crud = EntriesCRUD()
                # يفضّل توفير list_for_picker في CRUD، وإلا استخدم list()
                if hasattr(crud, "list_for_picker"):
                    rows = crud.list_for_picker() or []
                else:
                    # fallback مبسّط من list()
                    entries = crud.list(limit=500) or []
                    for e in entries:
                        items = getattr(e, "items", []) or []
                        total_net = sum(float(getattr(it, "net_weight_kg", 0) or 0) for it in items)
                        rows.append({
                            "id": getattr(e, "id", None),
                            "transport_ref": getattr(e, "transport_ref", None),  # ← رقم الحاوية/اللوحة
                            "entry_no": getattr(e, "entry_no", None),
                            # قد يكون رقمًا قديمًا – سنُهمله إن وُجد transport_ref
                            "client_name": (
                                    getattr(getattr(e, "owner_client", None), "name_ar", None)
                                    or getattr(getattr(e, "owner_client", None), "name_en", None)
                                    or getattr(getattr(e, "owner_client", None), "name_tr", None)
                            ),
                            "total_net_kg": sum(
                                float(getattr(it, "net_weight_kg", 0) or 0) for it in (getattr(e, "items", []) or [])),
                        })

            except Exception:
                rows = []

        if not rows:
            QMessageBox.information(self, _("info"), _("no_entries_found"))
            return

        for r, row in enumerate(rows):
            self.tbl.insertRow(r)

            # checkbox
            chk = QTableWidgetItem("")
            chk.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)
            chk.setCheckState(Qt.Unchecked)
            self.tbl.setItem(r, 0, chk)

            # helpers
            def setc(c, val, align_center=True):
                it = QTableWidgetItem(_safe_str(val))
                it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                if align_center:
                    it.setTextAlignment(Qt.AlignCenter)
                self.tbl.setItem(r, c, it)

            eid = _pick(row, "id")
            # التوافق: entry_no ← transport_ref إن لزم
            eno = _pick(row, "transport_ref", "entry_no", default=f"E#{eid}")
            cname = _pick(row, "client_name", "name_ar", "name_en", "name_tr", default=f"#{eid}")
            net = _pick(row, "total_net_kg", default=0)

            setc(1, eid)
            setc(2, eno)
            setc(3, cname)
            setc(4, _fmt_num(net, 2))

    # ---------------------- selection ----------------------
    def _on_ok(self):
        selected = []
        for r in range(self.tbl.rowCount()):
            it = self.tbl.item(r, 0)
            if it and it.checkState() == Qt.Checked:
                entry_id = self.tbl.item(r, 1).text()
                entry_no = self.tbl.item(r, 2).text()
                items = []
                if EntriesCRUD:
                    try:
                        crud = EntriesCRUD()
                        if hasattr(crud, "get_items_for_entry") and str(entry_id).isdigit():
                            items = crud.get_items_for_entry(int(entry_id))
                    except Exception:
                        items = []
                selected.append({
                    "entry_id": int(entry_id) if str(entry_id).isdigit() else entry_id,
                    "entry_no": entry_no,
                    # تركنا هذا المفتاح للتوافق مع أي كود قديم يتوقعه
                    "truck_or_container_no": entry_no,
                    "items": items
                })

        if not selected:
            QMessageBox.information(self, _("info"), _("select_at_least_one"))
            return

        self.picked.emit(selected)
        self.accept()
