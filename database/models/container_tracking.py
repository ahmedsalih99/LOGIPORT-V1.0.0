"""
container_tracking.py — LOGIPORT v2
=====================================
تتبع شحنات البوليصة — يدوي بالكامل.

التغييرات v2:
  - إعادة هيكلة الحقول حسب الطلب:
      معلومات أساسية: bl_number, shipping_line, client_id, cargo_type,
                       quantity, origin_country, port_of_discharge
      التتبع:         docs_delivered (bool), cargo_tracking (text),
                       docs_received_date (date), containers_count, bl_status
      ملاحظات:        notes
  - حقل eta بقي (تاريخ وصول المينا)
  - حذف: container_no, vessel_name, voyage_no, port_of_loading,
          booking_no, final_destination, atd, ata, customs_date, delivery_date
  - جدول جديد ShipmentContainer: رقم الكونتينر + الرقم + المستلم
"""
from __future__ import annotations

from sqlalchemy import (
    Column, Integer, String, Date, Text, DateTime,
    ForeignKey, Boolean, func,
)
from sqlalchemy.orm import relationship
from database.models.base import Base


class ContainerTracking(Base):
    """
    بوليصة شحن (Bill of Lading) مع كونتينراتها.
    كل سجل = بوليصة واحدة، وترتبط بها كونتينرات متعددة عبر ShipmentContainer.
    """
    __tablename__ = "container_tracking"

    id             = Column(Integer, primary_key=True, autoincrement=True)

    # ── ربط بالمعاملة (اختياري) ──────────────────────────────────────────────
    transaction_id = Column(
        Integer, ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    # ── ربط بالزبون / صاحب البضاعة ────────────────────────────────────────────
    client_id = Column(
        Integer, ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    # ── ربط بالمكتب ───────────────────────────────────────────────────────────
    office_id = Column(
        Integer, ForeignKey("offices.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    # ── معلومات البوليصة الأساسية ──────────────────────────────────────────────
    bl_number         = Column(String(64),  nullable=False, index=True)   # رقم البوليصة *
    shipping_line     = Column(String(128), nullable=True)                # شركة الشحن
    cargo_type        = Column(String(128), nullable=True)                # نوع البضاعة
    quantity          = Column(String(64),  nullable=True)                # العدد / الكمية
    origin_country    = Column(String(128), nullable=True)                # الدولة المرسلة
    port_of_discharge = Column(String(128), nullable=True)                # ميناء الوصول
    containers_count  = Column(Integer,     nullable=True)                # عدد الكونتينرات

    # ── التتبع والوثائق ────────────────────────────────────────────────────────
    docs_delivered    = Column(Boolean,     nullable=False, default=False) # تسليم الاوراق
    cargo_tracking    = Column(Text,        nullable=True)                 # تتبع الكارجو (نص)
    docs_received_date = Column(Date,       nullable=True)                 # تاريخ استلام الاوراق
    bl_status         = Column(String(64),  nullable=True)                 # حالة البوليصة

    # ── تاريخ الوصول للميناء ───────────────────────────────────────────────────
    eta               = Column(Date,        nullable=True)                 # ETA

    # ── حالة السجل والملاحظات ─────────────────────────────────────────────────
    status            = Column(String(32),  nullable=False, default="booked", index=True)
    notes             = Column(Text,        nullable=True)

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # ── Relationships ─────────────────────────────────────────────────────────
    transaction = relationship(
        "Transaction", foreign_keys=[transaction_id],
        backref="container_trackings", lazy="joined",
    )
    client = relationship(
        "Client", foreign_keys=[client_id], lazy="joined",
    )
    office = relationship(
        "Office", foreign_keys=[office_id], lazy="joined",
    )
    containers = relationship(
        "ShipmentContainer",
        back_populates="shipment",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="ShipmentContainer.id",
    )

    def __repr__(self):
        return f"<ContainerTracking(bl={self.bl_number!r}, status={self.status!r})>"

    STATUSES = [
        "booked",
        "in_transit",
        "arrived",
        "customs",
        "delivered",
        "hold",
    ]

    # حالة البوليصة خيارات (bl_status)
    BL_STATUSES = [
        "original",
        "telex",
        "seaway",
        "surrendered",
    ]


class ShipmentContainer(Base):
    """
    كونتينر واحد ضمن بوليصة شحن.
    كل بوليصة (ContainerTracking) تحتوي على 1+ كونتينر.
    """
    __tablename__ = "shipment_containers"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    shipment_id  = Column(
        Integer, ForeignKey("container_tracking.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    container_no = Column(String(32),  nullable=True)   # رقم الكونتينر
    seal_no      = Column(String(32),  nullable=True)   # الرقم (رقم الختم/السيل)
    recipient    = Column(String(128), nullable=True)   # المستلم

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    shipment = relationship(
        "ContainerTracking", back_populates="containers",
    )

    def __repr__(self):
        return f"<ShipmentContainer(no={self.container_no!r})>"