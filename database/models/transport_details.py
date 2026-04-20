"""
transport_details.py — LOGIPORT
================================
بيانات الشحن الإضافية المطلوبة لتوليد مستندَي CMR و Form A (EUR.1 / GSP).

العلاقة: one-to-one مع transactions (يمكن أن لا تكون موجودة إذا لم يحتجها المستخدم).

CMR يحتاج:    carrier_company_id, truck_plate, driver_name,
               loading_place, delivery_place, shipment_date,
               origin_country, dest_country
Form A يحتاج: certificate_no, issuing_authority, certificate_date,
               origin_country, dest_country
كلاهما يحتاج: shipment_date
"""
from __future__ import annotations

from sqlalchemy import (
    Column, Integer, String, Date, ForeignKey, DateTime, func, UniqueConstraint
)
from sqlalchemy.orm import relationship
from database.models.base import Base


class TransportDetails(Base):
    """
    تفاصيل الشحن الإضافية — اختيارية بالكامل.
    تُنشأ أو تُحدَّث عند حفظ المعاملة إذا أدخل المستخدم أي منها.
    """
    __tablename__ = "transport_details"
    __table_args__ = (
        UniqueConstraint("transaction_id", name="uq_transport_transaction"),
    )

    id             = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(
        Integer,
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # ── CMR fields ────────────────────────────────────────────────────────────
    carrier_company_id = Column(
        Integer,
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )
    truck_plate    = Column(String(32),  nullable=True)  # رقم لوحة الشاحنة
    driver_name    = Column(String(128), nullable=True)  # اسم السائق
    loading_place  = Column(String(255), nullable=True)  # مكان التحميل (المدينة/العنوان)
    delivery_place = Column(String(255), nullable=True)  # مكان التسليم (المدينة/العنوان)
    shipment_date  = Column(Date,        nullable=True)  # تاريخ الشحن الفعلي

    # ── CMR — Documents attached (Box 5) ─────────────────────────────────────
    attached_documents  = Column(String(512), nullable=True)  # الوثائق المرفقة — Box 5

    # ── Form A / EUR.1 fields ─────────────────────────────────────────────────
    # ── CMR Number ───────────────────────────────────────────────────────────
    cmr_no              = Column(String(64),  nullable=True)  # رقم CMR — يدوي أو تلقائي من النظام

    # ── CMR الثاني (اختياري) — الناقل + الشاحنة + السائق + رقم CMR فقط ──────
    cmr_second_label        = Column(String(128), nullable=True)  # اسم CMR الثاني (حر — مثال: التركي)
    cmr_no_2                = Column(String(64),  nullable=True)  # رقم CMR الثاني
    carrier_company_id_2    = Column(
        Integer,
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )
    truck_plate_2           = Column(String(32),  nullable=True)  # رقم لوحة الشاحنة الثانية
    driver_name_2           = Column(String(128), nullable=True)  # اسم السائق الثاني
    loading_place_2         = Column(String(255), nullable=True)  # مكان التحميل الثاني
    delivery_place_2        = Column(String(255), nullable=True)  # مكان التسليم الثاني
    shipment_date_2         = Column(Date,        nullable=True)  # تاريخ الشحن الثاني

    certificate_no      = Column(String(64),  nullable=True)  # رقم شهادة المنشأ
    issuing_authority   = Column(String(255), nullable=True)  # الجهة المُصدِرة للشهادة
    certificate_date    = Column(Date,        nullable=True)  # تاريخ إصدار الشهادة (Form A) — يدوي مستقل

    # ── Override نصي للدول (CMR / Form A) ────────────────────────────────────
    # يُسمح للمستخدم بتجاوز اسم الدولة المسحوب من المعاملة إذا احتاج صياغة مختلفة
    origin_country      = Column(String(128), nullable=True)  # override بلد المنشأ
    dest_country        = Column(String(128), nullable=True)  # override بلد الوجهة

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # ── Relationships ─────────────────────────────────────────────────────────
    transaction     = relationship("Transaction",  back_populates="transport_details")
    carrier_company  = relationship("Company", foreign_keys=[carrier_company_id],   lazy="joined")
    carrier_company2 = relationship("Company", foreign_keys=[carrier_company_id_2], lazy="joined")

    def __repr__(self):
        return f"<TransportDetails(transaction_id={self.transaction_id})>"

    def is_empty(self) -> bool:
        """يُرجع True إذا كانت كل الحقول فارغة — للتحقق قبل الحفظ."""
        return not any([
            self.carrier_company_id, self.truck_plate, self.driver_name,
            self.loading_place, self.delivery_place, self.shipment_date,
            self.attached_documents,
            self.cmr_no,
            self.cmr_second_label, self.cmr_no_2,
            self.carrier_company_id_2, self.truck_plate_2, self.driver_name_2,
            self.loading_place_2, self.delivery_place_2, self.shipment_date_2,
            self.certificate_no, self.issuing_authority, self.certificate_date,
            self.origin_country, self.dest_country,
        ])