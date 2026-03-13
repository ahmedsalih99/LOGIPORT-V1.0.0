"""
ui/widgets/custom_table.py
==========================
جدول بيانات موحّد للاستخدام في الديالوغات وأي مكان خارج BaseTab.

المعيار:
  - فونت Bold بحجم التطبيق من ThemeManager
  - ارتفاع صفوف افتراضي مع إمكانية التخصيص
  - عرض أعمدة يتناسب مع المحتوى تلقائياً، قابل للتعديل اليدوي
  - رأس جدول Bold ومرتفع بما يناسب الفونت
  - تحديث تلقائي عند تغيير الثيم أو اللغة
"""

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
)
from core.translator import TranslationManager

# ── ثوابت مشتركة (نفس قيم base_tab) ─────────────────────────────────────────
_ROW_HEIGHT_DEFAULT = 46
_ROW_HEIGHT_MIN     = 32


def _build_font(size_px: int | None = None, bold: bool = True) -> QFont:
    """ينشئ QFont يتناسق مع إعدادات التطبيق الحالية."""
    try:
        from core.theme_manager import ThemeManager
        tm = ThemeManager.get_instance()
        family = tm.get_current_font_family()
        if size_px is None:
            size_px = tm.get_current_font_size()
    except Exception:
        family = "Tajawal"
        if size_px is None:
            size_px = 12
    f = QFont(family, size_px)
    f.setBold(bold)
    return f


class CustomTable(QTableWidget):
    """
    جدول بيانات موحّد للديالوغات.

    المعاملات:
        rows        : عدد الصفوف الابتدائية
        columns     : عدد الأعمدة
        parent      : الـ widget الأب
        header_keys : مفاتيح الترجمة لعناوين الأعمدة (i18n)
        row_height  : ارتفاع الصف — None يستخدم القيمة الافتراضية (46px)
        select_rows : True = تحديد صف كامل (افتراضي) | False = تحديد خلية
        editable    : True = يسمح بالتحرير | False = للعرض فقط (افتراضي)

    مثال:
        tbl = CustomTable(0, 4, self,
                          header_keys=["col_no", "col_name", "col_qty", "col_unit"])
        tbl.set_row_height(52)          # تخصيص ارتفاع اختياري
    """

    def __init__(
        self,
        rows: int = 0,
        columns: int = 0,
        parent=None,
        header_keys: list | None = None,
        row_height: int | None = None,
        select_rows: bool = True,
        editable: bool = False,
    ):
        super().__init__(rows, columns, parent)

        self._      = TranslationManager.get_instance().translate
        self._hkeys = header_keys or []
        self._row_h = max(row_height or _ROW_HEIGHT_DEFAULT, _ROW_HEIGHT_MIN)

        self._build_table(select_rows, editable)

        # اشترك في تغيير الثيم واللغة
        try:
            from core.theme_manager import ThemeManager
            ThemeManager.get_instance().theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass
        TranslationManager.get_instance().language_changed.connect(self._retranslate)

        self._retranslate()

    # ─────────────────────────────────────────────────────────────────────
    # بناء الجدول
    # ─────────────────────────────────────────────────────────────────────

    def _build_table(self, select_rows: bool, editable: bool):
        self.setObjectName("custom-table")
        self.setAlternatingRowColors(True)

        # تحرير / قراءة فقط
        self.setEditTriggers(
            QAbstractItemView.AllEditTriggers
            if editable
            else QAbstractItemView.NoEditTriggers
        )

        # طريقة التحديد
        if select_rows:
            self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

        # رأس عمودي مخفي
        self.verticalHeader().setVisible(False)

        # ارتفاع الصفوف
        self._apply_row_height()

        # رأس الجدول: Bold + ارتفاع متناسب
        self._apply_header_style()

        # عرض الأعمدة: يبدأ بـ Stretch ثم Interactive (مرونة + تعديل يدوي)
        self._fit_columns()

    def _apply_row_height(self):
        vh = self.verticalHeader()
        vh.setDefaultSectionSize(self._row_h)
        vh.setMinimumSectionSize(_ROW_HEIGHT_MIN)

    def _apply_header_style(self):
        try:
            from core.theme_manager import ThemeManager
            fs = ThemeManager.get_instance().get_current_font_size()
        except Exception:
            fs = 12
        hdr_h = max(40, fs * 3 + 8)
        hdr = self.horizontalHeader()
        hdr.setMinimumHeight(hdr_h)
        hdr.setFont(_build_font(bold=True))

    def _fit_columns(self):
        """يضبط العرض حسب المحتوى ثم يتيح التعديل اليدوي."""
        hdr = self.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        QTimer.singleShot(
            0,
            lambda: hdr.setSectionResizeMode(QHeaderView.Interactive)
            if not self.isHidden() else None,
        )

    # ─────────────────────────────────────────────────────────────────────
    # API عام
    # ─────────────────────────────────────────────────────────────────────

    def set_row_height(self, height: int):
        """يعيّن ارتفاع مخصص للصفوف بعد الإنشاء."""
        self._row_h = max(height, _ROW_HEIGHT_MIN)
        self._apply_row_height()

    def make_item(self, text: str, bold: bool = True) -> QTableWidgetItem:
        """ينشئ QTableWidgetItem بفونت التطبيق (Bold افتراضياً)."""
        item = QTableWidgetItem(str(text) if text is not None else "")
        item.setFont(_build_font(bold=bold))
        return item

    def fit_columns(self):
        """استدعاء يدوي لإعادة ضبط عرض الأعمدة حسب المحتوى."""
        self._fit_columns()

    # ─────────────────────────────────────────────────────────────────────
    # معالجة تغيير الثيم / اللغة
    # ─────────────────────────────────────────────────────────────────────

    def _on_theme_changed(self, *_):
        """يُطبَّق تلقائياً عند تغيير الثيم أو حجم الخط."""
        self._apply_header_style()
        self._apply_row_height()
        # تحديث فونت الخلايا الموجودة
        font = _build_font()
        for r in range(self.rowCount()):
            for c in range(self.columnCount()):
                item = self.item(r, c)
                if item:
                    item.setFont(font)

    def _retranslate(self):
        """يُحدّث عناوين الأعمدة عند تغيير اللغة."""
        if self._hkeys and self.columnCount() == len(self._hkeys):
            self.setHorizontalHeaderLabels([self._(k) for k in self._hkeys])