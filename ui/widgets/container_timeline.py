"""
ui/widgets/container_timeline.py — LOGIPORT
=============================================
ويدجت Timeline مرئي لمراحل الكونتينر.

الاستخدام:
    timeline = ContainerTimeline(container, parent=self)
    layout.addWidget(timeline)

يعرض المراحل السبع بشكل أفقي:
  ✓ مكتمل — لون كامل + ✓
  ● حالي  — لون كامل + أيقونة + حلقة خارجية
  ○ قادم  — رمادي شفاف
"""
from __future__ import annotations

from datetime import date as _date_type

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore    import Qt, QSize, QRectF, QPointF
from PySide6.QtGui     import QPainter, QColor, QPen, QBrush, QFont, QPainterPath

from core.translator import TranslationManager


# ── ترتيب المراحل وبياناتها ──────────────────────────────────────────────────

STAGES = [
    {"key": "booked",     "icon": "📋", "color": "#6366F1", "date_attr": None},
    {"key": "loaded",     "icon": "📦", "color": "#0891B2", "date_attr": "etd"},
    {"key": "in_transit", "icon": "🚢", "color": "#2563EB", "date_attr": "atd"},
    {"key": "arrived",    "icon": "⚓", "color": "#7C3AED", "date_attr": "ata"},
    {"key": "customs",    "icon": "🏛", "color": "#D97706", "date_attr": "customs_date"},
    {"key": "delivered",  "icon": "✅", "color": "#059669", "date_attr": "delivery_date"},
    {"key": "hold",       "icon": "⚠",  "color": "#DC2626", "date_attr": None},
]

_STATUS_ORDER = {s["key"]: i for i, s in enumerate(STAGES)}
# hold ليس في التسلسل الطبيعي — نعامله بشكل مستقل
_NORMAL_ORDER = ["booked", "loaded", "in_transit", "arrived", "customs", "delivered"]


def _days_label(d, _t) -> str:
    """نص التاريخ نسبةً لليوم (منذ X يوم / اليوم / بعد X يوم)."""
    if not d:
        return ""
    today = _date_type.today()
    try:
        delta = (d - today).days
    except Exception:
        return str(d)
    if delta == 0:
        return _t("container_today")
    if delta > 0:
        return _t("container_days_left").format(n=delta)
    return _t("container_days_ago").format(n=abs(delta))


# ── ويدجت مرحلة واحدة ────────────────────────────────────────────────────────

class _StageNode(QWidget):
    """دائرة + أيقونة + نص لمرحلة واحدة."""

    _NODE_R = 22          # نصف قطر الدائرة

    def __init__(self, stage: dict, state: str, date_val, parent=None):
        """
        state: "completed" | "current" | "pending"
        """
        super().__init__(parent)
        self._stage = stage
        self._state = state
        self._date  = date_val
        self._       = TranslationManager.get_instance().translate
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(90)
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(4, 4, 4, 4)
        v.setSpacing(2)
        v.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        # الدائرة (ويدجت رسم مخصص)
        circle = _CircleWidget(
            color   = self._stage["color"],
            icon    = self._stage["icon"],
            state   = self._state,
            radius  = self._NODE_R,
            parent  = self,
        )
        v.addWidget(circle, 0, Qt.AlignHCenter)

        # اسم المرحلة
        name_lbl = QLabel(self._(f"container_status_{self._stage['key']}"))
        name_lbl.setAlignment(Qt.AlignHCenter)
        name_font = QFont("Tajawal", 8)
        name_font.setBold(self._state == "current")
        name_lbl.setFont(name_font)
        if self._state == "pending":
            name_lbl.setStyleSheet("color: #9CA3AF;")
        elif self._state == "current":
            name_lbl.setStyleSheet(f"color: {self._stage['color']}; font-weight: bold;")
        v.addWidget(name_lbl)

        # التاريخ
        if self._date and self._state != "pending":
            date_lbl = QLabel(_days_label(self._date, self._))
            date_lbl.setAlignment(Qt.AlignHCenter)
            date_font = QFont("Tajawal", 7)
            date_lbl.setFont(date_font)
            date_lbl.setStyleSheet("color: #6B7280;")
            v.addWidget(date_lbl)


class _CircleWidget(QWidget):
    """دائرة مرسومة بـ QPainter."""

    def __init__(self, color: str, icon: str, state: str, radius: int, parent=None):
        super().__init__(parent)
        self._color  = QColor(color)
        self._icon   = icon
        self._state  = state
        self._radius = radius
        size = radius * 2 + 10
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        cx = self.width()  / 2
        cy = self.height() / 2
        r  = self._radius

        if self._state == "pending":
            # دائرة رمادية فارغة
            p.setPen(QPen(QColor("#D1D5DB"), 2))
            p.setBrush(QBrush(QColor("#F9FAFB")))
            p.drawEllipse(QPointF(cx, cy), r, r)
        elif self._state == "completed":
            # دائرة ممتلئة بلون المرحلة
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(self._color))
            p.drawEllipse(QPointF(cx, cy), r, r)
            # علامة ✓
            p.setPen(QPen(QColor("white"), 2.5, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(
                QPointF(cx - r * 0.35, cy),
                QPointF(cx - r * 0.05, cy + r * 0.35),
            )
            p.drawLine(
                QPointF(cx - r * 0.05, cy + r * 0.35),
                QPointF(cx + r * 0.38, cy - r * 0.30),
            )
        else:  # current
            # حلقة خارجية متوهجة
            glow = QColor(self._color)
            glow.setAlpha(60)
            p.setPen(QPen(glow, 4))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(cx, cy), r + 4, r + 4)
            # دائرة ممتلئة
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(self._color))
            p.drawEllipse(QPointF(cx, cy), r, r)
            # أيقونة نصية
            p.setPen(QPen(QColor("white")))
            f = QFont("Segoe UI Emoji", int(r * 0.65))
            p.setFont(f)
            p.drawText(
                QRectF(cx - r, cy - r, r * 2, r * 2),
                Qt.AlignCenter,
                self._icon,
            )

        p.end()


# ── خط الوصل بين المراحل ─────────────────────────────────────────────────────

class _ConnectorLine(QWidget):
    """خط أفقي يصل بين مرحلتين."""

    def __init__(self, completed: bool, color: str, parent=None):
        super().__init__(parent)
        self._completed = completed
        self._color     = QColor(color)
        self.setFixedHeight(90)
        self.setFixedWidth(32)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cy = self.height() // 2 - 12      # محاذاة مع مركز الدائرة
        if self._completed:
            p.setPen(QPen(self._color, 3))
        else:
            p.setPen(QPen(QColor("#D1D5DB"), 2, Qt.DashLine))
        p.drawLine(0, cy, self.width(), cy)
        p.end()


# ── الويدجت الرئيسي ──────────────────────────────────────────────────────────

class ContainerTimeline(QWidget):
    """
    Timeline مرئي أفقي لمراحل الكونتينر.

    الاستخدام:
        tl = ContainerTimeline(container, parent=dialog)
        layout.addWidget(tl)
    """

    def __init__(self, container, parent=None):
        super().__init__(parent)
        self._container = container
        self._ = TranslationManager.get_instance().translate
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 4)
        root.setSpacing(4)

        # العنوان
        title = QLabel(self._("container_timeline_title"))
        tf = QFont("Tajawal", 10)
        tf.setBold(True)
        title.setFont(tf)
        title.setObjectName("section-title")
        root.addWidget(title)

        # الحالة الحالية
        current_status = getattr(self._container, "status", "booked") or "booked"

        # هل الكونتينر موقوف؟
        is_hold = current_status == "hold"

        # مراحل العرض — إذا hold نعرضه منفصلاً
        display_stages = STAGES[:-1]   # بدون hold
        if is_hold:
            active_stages = display_stages   # كلها pending
        else:
            active_stages = display_stages

        # نحدد index الحالة الحالية في التسلسل الطبيعي
        try:
            current_idx = _NORMAL_ORDER.index(current_status)
        except ValueError:
            current_idx = 0

        # صف المراحل
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        for i, stage in enumerate(display_stages):
            # تحديد state
            stage_idx = _NORMAL_ORDER.index(stage["key"])
            if is_hold:
                state = "pending"
            elif stage_idx < current_idx:
                state = "completed"
            elif stage_idx == current_idx:
                state = "current"
            else:
                state = "pending"

            # قيمة التاريخ
            date_attr = stage.get("date_attr")
            date_val  = getattr(self._container, date_attr, None) if date_attr else None

            node = _StageNode(stage, state, date_val, self)
            row.addWidget(node, 1)

            # خط وصل (ما عدا بعد آخر مرحلة)
            if i < len(display_stages) - 1:
                line_completed = (not is_hold) and stage_idx < current_idx
                line_color     = stage["color"] if line_completed else "#D1D5DB"
                connector = _ConnectorLine(line_completed, line_color, self)
                row.addWidget(connector, 0)

        root.addLayout(row)

        # إذا hold — نضيف تنبيه
        if is_hold:
            hold_lbl = QLabel(f"⚠️  {self._('container_status_hold')}")
            hold_lbl.setStyleSheet(
                "color: #DC2626; background: #FEE2E2; border-radius: 6px;"
                "padding: 6px 12px; font-weight: bold;"
            )
            hold_lbl.setAlignment(Qt.AlignCenter)
            root.addWidget(hold_lbl)