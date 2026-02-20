from sqlalchemy import Column, Integer, Text, DateTime, Numeric, ForeignKey, Boolean, func, Index
from sqlalchemy.orm import relationship
from database.models import Base

class Pricing(Base):
    __tablename__ = "pricing"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Relations
    seller_company_id = Column(Integer, ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True)
    buyer_company_id  = Column(Integer, ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True)
    material_id       = Column(Integer, ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False, index=True)
    pricing_type_id   = Column(Integer, ForeignKey("pricing_types.id", ondelete="RESTRICT"), nullable=False, index=True)
    currency_id       = Column(Integer, ForeignKey("currencies.id", ondelete="RESTRICT"), nullable=False, index=True)

    # ✅ الحقل الصحيح (FK) — انتبه: أزلنا التعريف المكرر الذي كان بدون FK
    delivery_method_id = Column(Integer, ForeignKey("delivery_methods.id", ondelete="RESTRICT"), nullable=True)

    # Pricing
    price = Column(Numeric(12, 4), nullable=False)

    # Meta
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="1")

    # Audit
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at    = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships (joined for labels)
    seller_company = relationship("Company", foreign_keys=[seller_company_id], lazy="joined")
    buyer_company  = relationship("Company", foreign_keys=[buyer_company_id],  lazy="joined")
    material       = relationship("Material",   lazy="joined")
    currency       = relationship("Currency",   lazy="joined")
    pricing_type   = relationship("PricingType", back_populates="prices", lazy="joined")
    created_by     = relationship("User", foreign_keys=[created_by_id], lazy="joined")
    updated_by     = relationship("User", foreign_keys=[updated_by_id], lazy="joined")

    # ✅ اربط الطرفين مع DeliveryMethod
    delivery_method = relationship("DeliveryMethod", back_populates="prices", lazy="noload")

    def __repr__(self):
        return f"<Pricing(id={self.id})>"

# فهرس تجميعي للاستعلامات
Index(
    "idx_pricing_key",
    Pricing.seller_company_id, Pricing.buyer_company_id, Pricing.material_id,
    Pricing.pricing_type_id, Pricing.currency_id, Pricing.is_active
)
