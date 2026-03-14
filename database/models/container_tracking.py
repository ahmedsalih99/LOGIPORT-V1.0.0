"""
container_tracking.py — LOGIPORT
==================================
تتبع الكونتينرات — يدوي بالكامل.
الموظفة تُدخل بيانات الشحنة من أوراق الشحن وتُحدّث الحالة يدوياً.

العلاقات:
  - many-to-one  مع transactions (اختياري)
  - many-to-one  مع clients     (صاحب البضاعة — اختياري)
  - many-to-many مع entries     (الإدخالات المرتبطة)
"""
from __future__ import annotations

from sqlalchemy import Column, Integer, String, Date, Text, DateTime, ForeignKey, Table, func
from sqlalchemy.orm import relationship
from database.models.base import Base


# ── جدول الربط الوسيط (many-to-many) ─────────────────────────────────────────
container_entry_links = Table(
    "container_entry_links",
    Base.metadata,
    Column("container_id", Integer, ForeignKey("container_tracking.id", ondelete="CASCADE"),  primary_key=True),
    Column("entry_id",     Integer, ForeignKey("entries.id",            ondelete="CASCADE"),  primary_key=True),
)


class ContainerTracking(Base):
    """
    تتبع الكونتينرات — يدوي.
    كل سجل يمثّل كونتينر واحد مع كامل بيانات رحلته.
    """
    __tablename__ = "container_tracking"

    id             = Column(Integer, primary_key=True, autoincrement=True)

    # ── ربط بالمعاملة (اختياري) ──────────────────────────────────────────────
    transaction_id = Column(
        Integer,
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── ربط بالزبون / صاحب البضاعة (اختياري) ────────────────────────────────
    client_id = Column(
        Integer,
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── ربط بالمكتب (للفلترة في بيئة multi-office) ───────────────────────────
    office_id = Column(
        Integer,
        ForeignKey("offices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── بيانات الكونتينر الأساسية ─────────────────────────────────────────────
    container_no   = Column(String(32),  nullable=False, index=True)
    bl_number      = Column(String(64),  nullable=True)
    booking_no     = Column(String(64),  nullable=True)

    # ── شركة الشحن والباخرة ───────────────────────────────────────────────────
    shipping_line  = Column(String(128), nullable=True)
    vessel_name    = Column(String(128), nullable=True)
    voyage_no      = Column(String(32),  nullable=True)

    # ── المواني ───────────────────────────────────────────────────────────────
    port_of_loading    = Column(String(128), nullable=True)
    port_of_discharge  = Column(String(128), nullable=True)
    final_destination  = Column(String(128), nullable=True)

    # ── التواريخ ──────────────────────────────────────────────────────────────
    etd            = Column(Date, nullable=True)
    eta            = Column(Date, nullable=True)
    atd            = Column(Date, nullable=True)
    ata            = Column(Date, nullable=True)
    customs_date   = Column(Date, nullable=True)
    delivery_date  = Column(Date, nullable=True)

    # ── الحالة ────────────────────────────────────────────────────────────────
    status         = Column(String(32), nullable=False, default="booked", index=True)

    # ── ملاحظات ───────────────────────────────────────────────────────────────
    notes          = Column(Text, nullable=True)

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # ── Relationships ─────────────────────────────────────────────────────────
    transaction = relationship(
        "Transaction",
        foreign_keys=[transaction_id],
        backref="container_trackings",
        lazy="joined",
    )

    client = relationship(
        "Client",
        foreign_keys=[client_id],
        lazy="joined",
    )

    office = relationship(
        "Office",
        foreign_keys=[office_id],
        lazy="joined",
    )

    entries = relationship(
        "Entry",
        secondary=container_entry_links,
        backref="containers",
        lazy="selectin",
    )

    def __repr__(self):
        return f"<ContainerTracking(no={self.container_no!r}, status={self.status!r})>"

    STATUSES = [
        "booked",
        "loaded",
        "in_transit",
        "arrived",
        "customs",
        "delivered",
        "hold",
    ]