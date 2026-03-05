from PySide6.QtCore import Qt, QDate, Signal, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QDateEdit, QComboBox, QTextEdit, QPushButton,
    QTabWidget, QFrame, QMessageBox, QSplitter, QLabel
)
from PySide6.QtGui import QShortcut, QKeySequence, QIcon

# ---- App core (guarded) -------------------------------------------------
try:
    from core.base_window import BaseWindow
except Exception:
    from PySide6.QtWidgets import QMainWindow as BaseWindow

try:
    from core.translator import TranslationManager
except Exception:
    class _DummyT:
        @staticmethod
        def get_instance():
            return _DummyT()

        def translate(self, x):
            return x

        def get_current_language(self):
            return "ar"


    TranslationManager = _DummyT

try:
    from core.settings_manager import SettingsManager
except Exception:
    class _DummyS:
        @staticmethod
        def get_instance():
            return _DummyS()

        def get(self, *_a, **_k):
            return None


    SettingsManager = _DummyS

# ---- Mixins --------------------------------------------------------------
try:
    from ui.dialogs.mixins.parties_geo_tab import PartiesGeoTabMixin
except Exception:
    class PartiesGeoTabMixin:
        def _build_parties_geo_tab(self): pass

        def prefill_parties_geo(self, *_): pass

        def get_parties_geo_data(self) -> dict: return {}

try:
    from ui.dialogs.mixins.items_tab import ItemsTabMixin
except Exception:
    class ItemsTabMixin:
        def _build_items_tab(self): pass

        def prefill_items(self, *_): pass

        def get_items_data(self) -> list: return []

try:
    from ui.dialogs.mixins.transport_tab import TransportTabMixin
except Exception:
    class TransportTabMixin:
        def _build_transport_tab(self): pass
        def get_transport_data(self) -> dict: return {}
        def prefill_transport(self, *_): pass

try:
    from ui.dialogs.mixins.documents_tab import DocumentsTabMixin
except Exception:
    class DocumentsTabMixin:
        def _build_documents_tab(self): pass
        def build_documents_panel(self):
            from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
            w = QWidget(); lay = QVBoxLayout(w)
            lay.addWidget(QLabel("⚠ docs panel unavailable"))
            return w
        def prefill_documents(self, *_): pass
        def get_documents_data(self) -> list: return []
        def get_documents_codes(self) -> list: return []



from typing import Any, Optional, Tuple, List
from database.crud.transactions_crud import TransactionsCRUD
import re


# ---- Window --------------------------------------------------------------
class AddTransactionWindow(PartiesGeoTabMixin, ItemsTabMixin, DocumentsTabMixin, TransportTabMixin, BaseWindow):
    saved = Signal(int)

    def __init__(self, parent=None, current_user=None, transaction=None):
        super().__init__(parent)
        tm = TranslationManager.get_instance()
        self._ = tm.translate
        self._lang = tm.get_current_language()

        self.current_user = current_user or SettingsManager.get_instance().get("user")

        if isinstance(transaction, (int, str)):
            self.transaction = self._load_transaction_by_id(transaction)
        else:
            self.transaction = transaction

        self._is_edit = bool(getattr(self.transaction, "id", None))
        self.setObjectName("AddTransactionWindow")
        self.setWindowTitle(self._("edit_transaction") if self._is_edit else self._("add_transaction"))

        # ✨ تحسين: حجم النافذة الافتراضي أكبر
        self.resize(1400, 900)  # كان صغير جداً
        self.setMinimumSize(QSize(1200, 800))

        self._build_ui()
        self._setup_shortcuts()
        self._prefill_if_edit()

    def _build_ui(self):
        root = QWidget(self)
        root.setObjectName("transaction-dialog-root")
        self.setCentralWidget(root)

        splitter = QSplitter(Qt.Vertical, root)
        splitter.setObjectName("main-splitter")

        top = QWidget()
        top.setObjectName("top-section")
        top_layout = QVBoxLayout(top)
        # ✨ تحسين: margins أكبر للتنفس
        top_layout.setContentsMargins(16, 8, 16, 8)  # ✅ أقل من 20
        top_layout.setSpacing(8)

        bottom = QWidget()
        bottom.setObjectName("bottom-section")
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(8, 8, 8, 8)
        bottom_layout.setSpacing(0)

        # Top actions
        actions = QHBoxLayout()
        actions.setSpacing(12)  # ✨ مسافة أكبر بين الأزرار

        self.btn_save = QPushButton(self._("save"))
        self.btn_save.setObjectName("primary-btn")
        self.btn_save.setToolTip(self._("save") + " (Ctrl+S)")
        # ✨ تحسين: حجم أكبر للأزرار
        self.btn_save.setMinimumHeight(40)
        self.btn_save.setMinimumWidth(120)
        try:
            self.btn_save.setIcon(QIcon.fromTheme("document-save"))
        except:
            pass

        self.btn_cancel = QPushButton(self._("cancel"))
        self.btn_cancel.setObjectName("secondary-btn")
        self.btn_cancel.setToolTip(self._("cancel") + " (Esc)")
        self.btn_cancel.setMinimumHeight(40)
        self.btn_cancel.setMinimumWidth(120)
        try:
            self.btn_cancel.setIcon(QIcon.fromTheme("dialog-cancel"))
        except:
            pass

        self.btn_generate_docs = QPushButton(self._("generate_documents"))
        self.btn_generate_docs.setObjectName("secondary-btn")
        self.btn_generate_docs.setToolTip(self._("generate_documents") + " (Ctrl+G)")
        self.btn_generate_docs.setMinimumHeight(40)
        self.btn_generate_docs.setMinimumWidth(150)
        try:
            self.btn_generate_docs.setIcon(QIcon.fromTheme("document-new"))
        except:
            pass

        actions.addStretch()
        actions.addWidget(self.btn_save)
        actions.addWidget(self.btn_generate_docs)
        actions.addWidget(self.btn_cancel)
        top_layout.addLayout(actions)

        # Status bar
        self.status_bar = QWidget()
        self.status_bar.setObjectName("status-bar")
        status_layout = QHBoxLayout(self.status_bar)
        status_layout.setContentsMargins(12, 12, 12, 12)
        self.status_label = QLabel("")
        self.status_label.setObjectName("status-label")
        self.status_label.setMinimumHeight(32)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        self.status_bar.setVisible(False)
        top_layout.addWidget(self.status_bar)

        # General card
        card = QFrame(top)
        card.setObjectName("general-info-card")
        form = QFormLayout(card)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(8)  # ✅ أقل من 16
        form.setContentsMargins(16, 12, 16, 12)

        self.txt_trx_no = QLineEdit()
        self.txt_trx_no.setObjectName("transaction-number-input")
        self.txt_trx_no.setMinimumHeight(40)
        try:
            self.txt_trx_no.setPlaceholderText(self._generate_placeholder_number())
        except Exception:
            pass

        self.dt_trx_date = QDateEdit()
        self.dt_trx_date.setObjectName("transaction-date-input")
        self.dt_trx_date.setMinimumHeight(40)
        self.dt_trx_date.setDisplayFormat("yyyy-MM-dd")
        self.dt_trx_date.setCalendarPopup(True)
        self.dt_trx_date.setDate(QDate.currentDate())

        self.cmb_trx_type = QComboBox()
        self.cmb_trx_type.setObjectName("transaction-type-combo")
        self.cmb_trx_type.setMinimumHeight(40)
        self._fill_trx_types()

        self.txt_notes = QTextEdit()
        self.txt_notes.setObjectName("transaction-notes-input")
        self.txt_notes.setFixedHeight(56)  # ✅ ثابت 56px — سطرين تقريباً
        self.txt_notes.setPlaceholderText(self._("enter_notes_optional"))

        form.addRow(self._("transaction_no"), self.txt_trx_no)
        form.addRow(self._("transaction_date"), self.dt_trx_date)
        form.addRow(self._("transaction_type"), self.cmb_trx_type)
        form.addRow(self._("notes"), self.txt_notes)
        top_layout.addWidget(card)

        # ── Horizontal splitter: tabs (يسار/وسط) + docs panel (يمين) ──────────
        h_splitter = QSplitter(Qt.Horizontal)
        h_splitter.setObjectName("content-splitter")

        # التبويبات (Parties, Pricing, Items)
        self.tabs = QTabWidget()
        self.tabs.setObjectName("transaction-tabs")
        try:
            self._build_parties_geo_tab()
        except Exception:
            pass
        try:
            self._build_pricing_tab()
        except Exception:
            pass
        try:
            self._build_items_tab()
        except Exception:
            pass
        try:
            self._build_transport_tab()
        except Exception:
            pass

        h_splitter.addWidget(self.tabs)

        # ── Docs side panel ──────────────────────────────────────────────────
        try:
            self._docs_side_panel = self.build_documents_panel()
            h_splitter.addWidget(self._docs_side_panel)
        except Exception:
            pass

        # نسب: التبويبات تأخذ ~75% والـ panel ~25%
        h_splitter.setStretchFactor(0, 3)
        h_splitter.setStretchFactor(1, 1)
        h_splitter.setSizes([900, 260])

        bottom_layout.addWidget(h_splitter)

        splitter.addWidget(top)
        splitter.addWidget(bottom)
        splitter.setStretchFactor(0, 0)  # ✅ top لا يتمدد أبداً
        splitter.setStretchFactor(1, 1)  # ✅ bottom يأخذ كل المساحة الزائدة
        splitter.setSizes([300, 600])

        lay = QVBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(splitter)

        # Signals
        self.btn_cancel.clicked.connect(self.close)
        self.btn_save.clicked.connect(self._on_save_clicked)
        self.btn_generate_docs.clicked.connect(self._open_generate_docs)

    def _setup_shortcuts(self):
        save_shortcut = QShortcut(QKeySequence.Save, self)
        save_shortcut.activated.connect(self._on_save_clicked)

        cancel_shortcut = QShortcut(QKeySequence.Cancel, self)
        cancel_shortcut.activated.connect(self.close)

        generate_shortcut = QShortcut(QKeySequence("Ctrl+G"), self)
        generate_shortcut.activated.connect(self._open_generate_docs)

        next_tab = QShortcut(QKeySequence.NextChild, self)
        next_tab.activated.connect(self._next_tab)

        prev_tab = QShortcut(QKeySequence.PreviousChild, self)
        prev_tab.activated.connect(self._prev_tab)

    def _next_tab(self):
        if hasattr(self, 'tabs'):
            current = self.tabs.currentIndex()
            next_idx = (current + 1) % self.tabs.count()
            self.tabs.setCurrentIndex(next_idx)

    def _prev_tab(self):
        if hasattr(self, 'tabs'):
            current = self.tabs.currentIndex()
            prev_idx = (current - 1) % self.tabs.count()
            self.tabs.setCurrentIndex(prev_idx)

    def _show_status(self, message: str, message_type: str = "info"):
        if hasattr(self, 'status_label') and hasattr(self, 'status_bar'):
            self.status_label.setText(message)
            self.status_label.setProperty("message_type", message_type)
            self.status_label.style().unpolish(self.status_label)
            self.status_label.style().polish(self.status_label)
            self.status_bar.setVisible(True)

    def _hide_status(self):
        if hasattr(self, 'status_bar'):
            self.status_bar.setVisible(False)

    def _fill_trx_types(self):
        self.cmb_trx_type.clear()
        for label, code in ((self._("import"), "import"), (self._("export"), "export"), (self._("transit"), "transit")):
            self.cmb_trx_type.addItem(label, code)

    def _prefill_if_edit(self):
        if not self.transaction:
            try:
                self.txt_trx_no.setPlaceholderText(self._generate_placeholder_number())
            except Exception:
                pass
            self.txt_trx_no.clear()
            return

        get = (lambda o, k, d=None: o.get(k, d) if isinstance(o, dict) else getattr(o, k, d))
        no = get(self.transaction, "transaction_no", "") or ""
        if no:
            self.txt_trx_no.setText(str(no))
        try:
            dt = get(self.transaction, "transaction_date", None)
            if dt:
                if hasattr(dt, "year"):
                    self.dt_trx_date.setDate(QDate(dt.year, dt.month, dt.day))
                else:
                    from datetime import datetime
                    dt_obj = datetime.fromisoformat(str(dt))
                    self.dt_trx_date.setDate(QDate(dt_obj.year, dt_obj.month, dt_obj.day))
        except Exception:
            pass
        tt = get(self.transaction, "transaction_type", None)
        if tt:
            for i in range(self.cmb_trx_type.count()):
                if self.cmb_trx_type.itemData(i) == tt:
                    self.cmb_trx_type.setCurrentIndex(i)
                    break

        self.txt_notes.setPlainText(str(get(self.transaction, "notes", "") or ""))

        try:
            self.prefill_parties_geo(self.transaction)
        except Exception:
            pass
        try:
            self.prefill_items(self.transaction)
        except Exception:
            pass
        try:
            self.prefill_documents(self.transaction)
        except Exception:
            pass
        try:
            self.prefill_transport(self.transaction)
        except Exception:
            pass

    @staticmethod
    def _load_transaction_by_id(trx_id):
        try:
            tid = int(trx_id)
        except Exception:
            return None
        try:
            crud = TransactionsCRUD()
            got = crud.get_with_items(tid)
            if isinstance(got, tuple) and got[0] is not None:
                return got[0]
            return crud.get(tid)
        except Exception:
            return None

    def _generate_placeholder_number(self) -> str:
        """
        يعرض الرقم التالي المتوقع من NumberingService بدل XXXX.
        يستخدم session مؤقتة للقراءة فقط — لا يحجز الرقم ولا يحفظه.
        إذا فشل الاستعلام لأي سبب يرجع إلى صيغة آمنة.
        """
        try:
            from services.numbering_service import NumberingService
            from database.models import get_session_local
            from sqlalchemy import text as _text
            with get_session_local()() as session:
                prefix = NumberingService._get_prefix(session)
                row = session.execute(
                    _text("SELECT value FROM app_settings WHERE key = 'transaction_last_number'")
                ).fetchone()
                settings_num = int(row[0]) if row and row[0] else 0
                db_max = NumberingService._get_db_max_numeric(session, prefix)
                last = max(settings_num, db_max)
                next_num = NumberingService._find_next_available(session, last + 1, prefix)
                preview = f"{prefix}{next_num}" if prefix else str(next_num)
                return f"{preview} (auto)"
        except Exception:
            try:
                prefix = SettingsManager.get_instance().get("trx_prefix", "T") or "T"
            except Exception:
                prefix = "T"
            return f"{prefix}... (auto)"

    def _normalize_manual_number(self, s: str) -> str:
        s = (s or "").strip()
        if not s:
            return ""
        try:
            prefix = SettingsManager.get_instance().get("trx_prefix", "T")
        except Exception:
            prefix = "T"
        if re.fullmatch(rf"{re.escape(prefix)}X+", s, flags=re.IGNORECASE):
            return ""
        if s.upper() in {"AUTO", "NULL", "NONE", "-", "—"}:
            return ""
        return s

    def get_all_data(self) -> dict:
        from datetime import date as _pydate
        qd = self.dt_trx_date.date()
        general = {
            "transaction_no": self._normalize_manual_number(self.txt_trx_no.text()),
            "transaction_date": _pydate(qd.year(), qd.month(), qd.day()),
            "transaction_type": self.cmb_trx_type.currentData(),
            "notes": (self.txt_notes.toPlainText() or "").strip(),
        }
        parties_geo = {}
        items = []
        docs = []
        try:
            parties_geo = self.get_parties_geo_data()
        except Exception:
            pass
        try:
            items = self.get_items_data()
        except Exception:
            pass
        try:
            docs = self.get_documents_data()
        except Exception:
            pass
        data = {}
        data.update(general)
        data.update(parties_geo)
        data["items"] = items
        data["document_type_ids"] = docs
        return data

    def _on_save_clicked(self):
        from datetime import date as _pydate

        self._show_status(self._("saving"), "info")

        data = {}
        if hasattr(self, "get_general_data"):
            data.update(self.get_general_data() or {})
        if hasattr(self, "get_parties_data"):
            data.update(self.get_parties_data() or {})
        if hasattr(self, "get_geography_data"):
            data.update(self.get_geography_data() or {})
        if hasattr(self, "get_pricing_data"):
            data.update(self.get_pricing_data() or {})
        transport_data = {}
        if hasattr(self, "get_transport_data"):
            transport_data = self.get_transport_data().get("transport", {})
        if transport_data:
            data["transport"] = transport_data

        if hasattr(self, "dt_trx_date") and self.dt_trx_date:
            qd = self.dt_trx_date.date()
            data["transaction_date"] = _pydate(qd.year(), qd.month(), qd.day())

        data.setdefault("transaction_type",
                        self.cmb_trx_type.currentData() if hasattr(self, "cmb_trx_type") else "import")

        items = []
        if hasattr(self, "get_items_data"):
            try:
                items = list(self.get_items_data() or [])
            except Exception:
                items = []
        entry_ids = list(data.pop("entry_ids", []) or [])
        if not entry_ids:
            try:
                entry_ids = sorted({int(i.get("entry_id")) for i in items if i.get("entry_id")})
            except Exception:
                entry_ids = []

        required_labels = {
            "delivery_method_id": self._("delivery_method"),
            "client_id": self._("client"),
            "exporter_company_id": self._("exporting_company"),
            "importer_company_id": self._("importing_company"),
        }
        missing = [lbl for k, lbl in required_labels.items() if not data.get(k)]
        if missing:
            self._hide_status()
            QMessageBox.warning(self, self._("invalid_data"),
                                self._("please_fill_required_fields") + ":\n- " + "\n- ".join(missing))
            return

        manual_no = self._normalize_manual_number(self.txt_trx_no.text() if hasattr(self, "txt_trx_no") else "")
        if manual_no:
            data["transaction_no"] = manual_no
        else:
            data.pop("transaction_no", None)

        if hasattr(self, "txt_notes"):
            data["notes"] = (self.txt_notes.toPlainText() or "").strip()

        try:
            prefix = SettingsManager.get_instance().get("trx_prefix", "T")
            user = self.current_user
            user_id = user.get("id") if isinstance(user, dict) else getattr(user, "id", None)
            crud = TransactionsCRUD()

            if self._is_edit and getattr(self.transaction, "id", None):
                trx = crud.update_transaction_with_items(
                    self.transaction.id,
                    data=data,
                    items=items,
                    entry_ids=entry_ids,
                    user_id=user_id,
                )
            else:
                trx = crud.create_transaction(
                    data=data,
                    items=items,
                    entry_ids=entry_ids,
                    user_id=user_id,
                    number_prefix=prefix,
                )

            trx_id_saved = int(getattr(trx, "id", 0) or 0)
            trx_no_saved = str(getattr(trx, "transaction_no", "") or "").strip()

            self._show_status(self._("transaction_saved_successfully"), "success")

            # جمع المستندات المختارة من الـ side panel
            selected_doc_ids: List[int] = []
            selected_doc_codes: List[str] = []
            try:
                selected_doc_ids   = list(self.get_documents_data() or [])
                selected_doc_codes = list(self.get_documents_codes() or [])
            except Exception:
                pass

            try:
                self.saved.emit(trx_id_saved)
            except Exception:
                pass

            # إذا اختار المستخدم مستندات → اسأله مباشرة (بدون dialog مفاجئ)
            if selected_doc_ids:
                answer = QMessageBox.question(
                    self,
                    self._("generate_documents"),
                    f"{self._('transaction_saved_successfully')}: {trx_no_saved}\n\n"
                    f"{self._('generate_selected_documents_now') if self._('generate_selected_documents_now') != 'generate_selected_documents_now' else 'هل تريد توليد المستندات المختارة الآن؟'}",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )
                if answer == QMessageBox.Yes:
                    try:
                        from ui.dialogs.generate_document_dialog import GenerateDocumentDialog
                        dlg = GenerateDocumentDialog(
                            transaction_id=trx_id_saved,
                            transaction_no=trx_no_saved,
                            parent=self,
                            preselected_doc_types=selected_doc_ids,
                            preselected_doc_codes=selected_doc_codes,
                        )
                        dlg.exec()
                    except Exception as doc_err:
                        QMessageBox.warning(self, self._("warning"),
                                            f"(توليد المستندات: {doc_err})")
            else:
                QMessageBox.information(self, self._("success"), self._("transaction_saved_successfully"))

            self.close()

        except Exception as e:
            self._show_status(f"{self._('save_failed')}: {e}", "error")
            QMessageBox.critical(self, self._("error"), f"{self._('save_failed')}: {e}")

    def _open_generate_docs(self):
        try:
            trx_id = int(getattr(self.transaction, "id", 0) or 0)
        except Exception:
            trx_id = 0
        if not trx_id:
            QMessageBox.warning(self, self._("warning"), self._("please_save_transaction_first"))
            return

        trx_no = ""
        try:
            trx_no = str(getattr(self.transaction, "transaction_no", "") or "").strip()
        except Exception:
            trx_no = ""
        if not trx_no:
            try:
                trx_no = self._normalize_manual_number(self.txt_trx_no.text()) or ""
            except Exception:
                trx_no = ""

        try:
            from ui.dialogs.generate_document_dialog import GenerateDocumentDialog
        except Exception as e:
            QMessageBox.critical(self, self._("error"), f"{self._('cannot_open_generator')}: {e}")
            return

        dlg = GenerateDocumentDialog(transaction_id=trx_id, transaction_no=trx_no, parent=self)
        dlg.exec()