from sqlalchemy import (
    Column, Integer, ForeignKey, Float, String, Text, Date, DateTime
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.models import Base
from sqlalchemy import Index

class EntryItem(Base):
    __tablename__ = "entry_items"

    id                = Column(Integer, primary_key=True)
    entry_id          = Column(Integer, ForeignKey("entries.id", ondelete="CASCADE"), nullable=False)
    material_id       = Column(Integer, ForeignKey("materials.id"), nullable=False)
    packaging_type_id = Column(Integer, ForeignKey("packaging_types.id"), nullable=True)
    count             = Column(Integer, default=0)
    net_weight_kg     = Column(Float, default=0.0)
    gross_weight_kg   = Column(Float, default=0.0)
    mfg_date          = Column(Date, nullable=True)
    exp_date          = Column(Date, nullable=True)
    origin_country_id = Column(Integer, ForeignKey("countries.id"), nullable=True)
    batch_no          = Column(String(100), nullable=True)
    notes             = Column(Text, nullable=True)

    # --- حقول الأدمن المطلوبة ---
    created_by_id     = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at        = Column(DateTime, server_default=func.now(), nullable=False)
    updated_by_id     = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at        = Column(DateTime, server_default=func.now(),
                               onupdate=func.now(), nullable=False)

    # --- علاقات مفيدة للعرض ---
    entry          = relationship("Entry", back_populates="items")
    material       = relationship("Material")
    packaging_type = relationship("PackagingType")
    origin_country = relationship("Country")
    created_by     = relationship("User", foreign_keys=[created_by_id])
    updated_by     = relationship("User", foreign_keys=[updated_by_id])

    def __repr__(self):
        return f"<EntryItem(id={self.id}, entry_id={self.entry_id})>"

Index("idx_entry_items_entry", EntryItem.entry_id)
Index("idx_entry_items_material", EntryItem.material_id)
Index("idx_entry_items_origin", EntryItem.origin_country_id)