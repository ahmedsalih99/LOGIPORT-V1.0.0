from sqlalchemy import (
    Column, Integer, Float, Numeric, Boolean, String, Text, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.models import Base


class TransactionItem(Base):
    __tablename__ = "transaction_items"
    __table_args__ = (
        Index("ix_trx_items_trx", "transaction_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Ownership
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False)

    # Optional links to source entry/item
    entry_id = Column(Integer, ForeignKey("entries.id", ondelete="SET NULL"), nullable=True)
    entry_item_id = Column(Integer, ForeignKey("entry_items.id", ondelete="SET NULL"), nullable=True)

    # Product / packaging
    material_id = Column(Integer, ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False)
    packaging_type_id = Column(Integer, ForeignKey("packaging_types.id", ondelete="RESTRICT"), nullable=True)

    # Quantities & weights
    quantity = Column(Float, nullable=False, default=0)
    gross_weight_kg = Column(Float, nullable=True, default=0)
    net_weight_kg = Column(Float, nullable=True, default=0)

    # Pricing (row-level overrides allowed)
    pricing_type_id = Column(Integer, ForeignKey("pricing_types.id", ondelete="RESTRICT"), nullable=True)
    unit_price = Column(Numeric(12, 4), nullable=False, default=0)
    currency_id = Column(Integer, ForeignKey("currencies.id", ondelete="RESTRICT"), nullable=True)
    line_total = Column(Numeric(12, 4), nullable=True)

    # Extra meta
    origin_country_id = Column(Integer, ForeignKey("countries.id", ondelete="RESTRICT"), nullable=True)
    source_type = Column(String(16), nullable=True, default="entry")  # entry / manual
    is_manual = Column(Boolean, nullable=False, default=False)
    notes = Column(Text, nullable=True)

    # 🚚 Transport / Container reference
    # هذا العمود يستخدم لحفظ رقم الكونتينر أو رقم الشاحنة للمواد اليدوية (أو المحدثة يدوياً)
    transport_ref = Column(Text, nullable=True)

    # Audit
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships (lazy='select' by default)
    transaction = relationship("Transaction", back_populates="items")
    entry = relationship("Entry", lazy="selectin")
    entry_item = relationship("EntryItem")
    material = relationship("Material")
    packaging_type = relationship("PackagingType")
    pricing_type = relationship("PricingType")
    currency = relationship("Currency")
    origin_country = relationship("Country")
    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])

    def __repr__(self):
        return f"<TransactionItem id={self.id}, material_id={self.material_id}, transport_ref={self.transport_ref}>"