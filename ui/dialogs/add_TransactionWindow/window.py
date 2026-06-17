from PySide6.QtCore import Qt, QDate, Signal, QSize, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QComboBox, QPushButton,
    QTabWidget, QFrame, QMessageBox, QSplitter, QLabel
)
from PySide6.QtGui import QShortcut, QKeySequence, QIcon
from ui.utils.font_utils import app_font, SM, BODY, MD, LG, XL2

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
    from ui.dialogs.mixins.general_tab import GeneralTabMixin
except Exception:
    class GeneralTabMixin:
        def _build_tab_general(self): pass
        def prefill_general(self, *_): pass
        def get_general_data(self) -> dict: return {}

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
class AddTransactionWindow(GeneralTabMixin, PartiesGeoTabMixin, ItemsTabMixin, DocumentsTabMixin, TransportTabMixin, BaseWindow):
    saved = Signal(int)

    def __init__(self, parent=None, current_user=None, transaction=None, copy_from_id=None):
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

        # ── اتجاه الواجهة حسب اللغة ──────────────────────────────────────────
        from PySide6.QtCore import Qt as _Qt
        self.setLayoutDirection(
            _Qt.RightToLeft if self._lang == "ar" else _Qt.LeftToRight
        )

        # حجم يراعي الشاشة — يأخذ 92% من المساحة المتاحة بحد أدنى ثابت
        try:
            from PySide6.QtWidgets import QApplication
            screen = QApplication.primaryScreen().availableGeometry()
            w = max(1200, int(screen.width()  * 0.92))
            h = max(800,  int(screen.height() * 0.92))
            self.resize(w, h)
        except Exception:
            self.resize(1400, 900)
        self.setMinimumSize(QSize(1200, 800))

        self._build_ui()
        self._setup_shortcuts()
        self._prefill_if_edit()

    # ── Type badge colors ──────────────────────────────────────────────────
    _TYPE_COLORS = {
        "export":  ("#065F46", "#D1FAE5"),
        "import":  ("#1E3A5F", "#DBEAFE"),
        "transit": ("#78350F", "#FEF3C7"),
    }
    _TYPE_ICONS = {
        "export": "📤",
        "import": "📥",
        "transit": "🔄",
    }

    def _build_ui(self):
        root = QWidget(self)
        root.setObjectName("transaction-dialog-root")
        self.setCentralWidget(root)

        main_lay = QVBoxLayout(root)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # ══ HEADER ═══════════════════════════════════════════════════════════
        self._header = self._build_header()
        main_lay.addWidget(self._header)

        # ══ GENERAL STRIP ════════════════════════════════════════════════════
        self.cmb_trx_type = QComboBox()
        general_strip = self._build_tab_general()
        main_lay.addWidget(general_strip)

        # ══ CONTENT (tabs + docs) ════════════════════════════════════════════
        h_splitter = QSplitter(Qt.Horizontal)
        h_splitter.setObjectName("content-splitter")

        self.tabs = QTabWidget()
        self.tabs.setObjectName("transaction-tabs")
        self.tabs.currentChanged.connect(self._on_tab_changed)

        try:
            self._build_parties_geo_tab()
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

        try:
            self._docs_side_panel = self.build_documents_panel()
            h_splitter.addWidget(self._docs_side_panel)
        except Exception:
            pass

        h_splitter.setStretchFactor(0, 3)
        h_splitter.setStretchFactor(1, 1)
        h_splitter.setSizes([900, 260])
        main_lay.addWidget(h_splitter, 1)

        # ══ TOAST ════════════════════════════════════════════════════════════
        self._toast = self._build_toast()
        # Toast يُوضع فوق كل شيء — يُحرَّك في resizeEvent
        self._toast.setParent(root)
        self._toast.raise_()
        self._toast.hide()

        # ربط نوع المعاملة بالـ badge في الـ header
        self.cmb_trx_type.currentIndexChanged.connect(
            lambda _: self._update_header_badge(self.cmb_trx_type.currentData() or "")
        )

        # Signals
        self.btn_cancel.clicked.connect(self.close)
        self.btn_save.clicked.connect(self._on_save_clicked)
        self.btn_generate_docs.clicked.connect(self._open_generate_docs)

        # حجب ScrollWheel
        try:
            from ui.utils.wheel_blocker import block_wheel_in
            block_wheel_in(root)
        except Exception:
            pass

    # ── Header ───────────────────────────────────────────────────────────────
    def _build_header(self) -> QWidget:
        """Header ثابت: عنوان + badge نوع المعاملة + أزرار."""
        hdr = QFrame()
        hdr.setObjectName("trx-dialog-header")
        hdr.setFixedHeight(56)

        lay = QHBoxLayout(hdr)
        lay.setContentsMargins(20, 0, 16, 0)
        lay.setSpacing(12)

        # عنوان النافذة
        self._hdr_title = QLabel(
            self._("edit_transaction") if self._is_edit else self._("add_transaction")
        )
        self._hdr_title.setObjectName("trx-header-title")
        self._hdr_title.setFont(app_font(LG, bold=True))

        # رقم المعاملة (يظهر عند التعديل)
        self._hdr_trx_no = QLabel("")
        self._hdr_trx_no.setObjectName("trx-header-no")
        self._hdr_trx_no.setFont(app_font(BODY))
        trx_no = getattr(self.transaction, "transaction_no", "") or ""
        if trx_no:
            self._hdr_trx_no.setText(f"  ·  {trx_no}")

        # badge نوع المعاملة
        self._hdr_badge = QLabel("")
        self._hdr_badge.setObjectName("trx-header-badge")
        self._hdr_badge.setFont(app_font(SM, bold=True))
        self._hdr_badge.setAlignment(Qt.AlignCenter)
        self._hdr_badge.setFixedHeight(26)
        self._hdr_badge.setMinimumWidth(80)

        lay.addWidget(self._hdr_title)
        lay.addWidget(self._hdr_trx_no)
        lay.addWidget(self._hdr_badge)
        lay.addStretch()

        # ── الأزرار ─────────────────────────────────────────────────────────
        self.btn_generate_docs = QPushButton("📄  " + self._("generate_documents"))
        self.btn_generate_docs.setObjectName("secondary-btn")
        self.btn_generate_docs.setFixedHeight(34)
        self.btn_generate_docs.setMinimumWidth(140)
        self.btn_generate_docs.setToolTip(self._("generate_documents") + " (Ctrl+G)")

        self.btn_save = QPushButton("💾  " + self._("save"))
        self.btn_save.setObjectName("primary-btn")
        self.btn_save.setFixedHeight(34)
        self.btn_save.setMinimumWidth(100)
        self.btn_save.setToolTip(self._("save") + " (Ctrl+S)")
        self.btn_save.setFont(app_font(BODY, bold=True))

        self.btn_cancel = QPushButton(self._("cancel"))
        self.btn_cancel.setObjectName("secondary-btn")
        self.btn_cancel.setFixedHeight(34)
        self.btn_cancel.setMinimumWidth(80)
        self.btn_cancel.setToolTip(self._("cancel") + " (Esc)")

        lay.addWidget(self.btn_generate_docs)
        lay.addWidget(self.btn_save)
        lay.addWidget(self.btn_cancel)

        return hdr

    def _update_header_badge(self, trx_type: str):
        """يُحدِّث badge نوع المعاملة في الـ Header."""
        if not hasattr(self, "_hdr_badge"):
            return
        icon  = self._TYPE_ICONS.get(trx_type, "•")
        label = self._(trx_type) if trx_type else ""
        fg, bg = self._TYPE_COLORS.get(trx_type, ("#374151", "#F3F4F6"))
        self._hdr_badge.setText(f"{icon}  {label}")
        self._hdr_badge.setStyleSheet(
            f"QLabel {{ background:{bg}; color:{fg}; border-radius:10px;"
            f"padding:2px 10px; font-weight:700; }}"
        )

    def _on_tab_changed(self, index: int):
        """يُحدِّث Tab titles عند تغيير التاب (للـ future use)."""
        pass

    # ── Toast notification ────────────────────────────────────────────────────
    def _build_toast(self) -> QLabel:
        toast = QLabel("")
        toast.setObjectName("trx-toast")
        toast.setAlignment(Qt.AlignCenter)
        toast.setFont(app_font(BODY))
        toast.setWordWrap(False)
        toast.setFixedHeight(40)
        toast.setAttribute(Qt.WA_TransparentForMouseEvents)
        return toast

    def _show_toast(self, message: str, kind: str = "success", duration_ms: int = 2800):
        """يعرض Toast notification في أسفل النافذة."""
        if not hasattr(self, "_toast"):
            return

        colors = {
            "success": ("#065F46", "#D1FAE5", "#6EE7B7"),
            "error":   ("#7F1D1D", "#FEE2E2", "#FCA5A5"),
            "info":    ("#1E3A5F", "#DBEAFE", "#93C5FD"),
        }
        fg, bg, border = colors.get(kind, colors["info"])
        icon = {"success": "✓", "error": "✗", "info": "ℹ"}.get(kind, "•")

        self._toast.setText(f"  {icon}  {message}  ")
        self._toast.setStyleSheet(
            f"QLabel {{ background:{bg}; color:{fg}; border:1px solid {border};"
            f"border-radius:8px; padding:0 16px; font-weight:600; }}"
        )

        # تحديد موضع Toast في أسفل المنتصف
        self._reposition_toast()
        self._toast.show()
        self._toast.raise_()

        # إخفاء تلقائي
        if hasattr(self, "_toast_timer"):
            self._toast_timer.stop()
        self._toast_timer = QTimer(self)
        self._toast_timer.setSingleShot(True)
        self._toast_timer.timeout.connect(self._toast.hide)
        self._toast_timer.start(duration_ms)

    def _reposition_toast(self):
        if not hasattr(self, "_toast"):
            return
        cw = self.centralWidget()
        if not cw:
            return
        w = min(480, cw.width() - 40)
        x = (cw.width() - w) // 2
        y = cw.height() - 60
        self._toast.setFixedWidth(w)
        self._toast.move(x, y)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_toast()

    def showEvent(self, event):
        """استعادة حجم النافذة بعد اكتمال بناء الـ UI"""
        super().showEvent(event)
        self._restore_geometry()

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
        """يعرض Toast بدل status bar."""
        self._show_toast(message, kind=message_type)

    def _hide_status(self):
        if hasattr(self, "_toast"):
            self._toast.hide()

    def _reset_save_btn(self):
        """يُعيد زر الحفظ لحالته الطبيعية."""
        if hasattr(self, "btn_save"):
            self.btn_save.setEnabled(True)
            self.btn_save.setText("💾  " + self._("save"))
            self.btn_save.setStyleSheet("")

    def _prefill_if_edit(self):
        if not self.transaction:
            try:
                self.txt_trx_no.setPlaceholderText(self._generate_placeholder_number())
            except Exception:
                pass
            self.txt_trx_no.clear()
            return

        try:
            self.prefill_general(self.transaction)
        except Exception:
            pass
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

        # زر الحفظ → حالة loading
        self.btn_save.setEnabled(False)
        self.btn_save.setText("⏳  " + self._("saving"))
        self._show_toast(self._("saving"), kind="info", duration_ms=5000)

        data = {}
        if hasattr(self, "get_general_data"):
            data.update(self.get_general_data() or {})
        if hasattr(self, "get_parties_data"):
            data.update(self.get_parties_data() or {})
        if hasattr(self, "get_geography_data"):
            data.update(self.get_geography_data() or {})
        # get_pricing_data: محجوزة للمستقبل — لا توجد حالياً
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

            # استعادة زر الحفظ بلون النجاح لـ 800ms
            self.btn_save.setText("✓  " + self._("saved"))
            self.btn_save.setStyleSheet(
                "QPushButton { background:#065F46; color:white; border-radius:6px; }"
            )
            QTimer.singleShot(800, self._reset_save_btn)
            self._show_toast(self._("transaction_saved_successfully"), kind="success")

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
                    f"{self._('generate_selected_documents_now')}",
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
                                            self._("doc_generation_error").format(error=doc_err))
            else:
                self._show_toast(self._("transaction_saved_successfully"), kind="success")

            self.close()

        except Exception as e:
            self.btn_save.setEnabled(True)
            self.btn_save.setText("💾  " + self._("save"))
            self.btn_save.setStyleSheet("")
            self._show_toast(f"{self._('save_failed')}: {e}", kind="error", duration_ms=4000)
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