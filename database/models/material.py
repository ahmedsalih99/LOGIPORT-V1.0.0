from sqlalchemy import (
    Column, Integer, String, ForeignKey, Numeric, DateTime, func, Index
)
from sqlalchemy.orm import relationship
from database.models import Base  # تأكد من المسار عندك

class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(64), nullable=False, unique=True, index=True)

    name_ar = Column(String(255), nullable=False)
    name_en = Column(String(255), nullable=True)
    name_tr = Column(String(255), nullable=True)

    material_type_id = Column(
        Integer, ForeignKey("material_types.id", ondelete="RESTRICT"), nullable=False
    )
    # سعر تقديري + العملة
    estimated_price = Column(Numeric(14, 4), nullable=True)
    currency_id = Column(
        Integer, ForeignKey("currencies.id", ondelete="RESTRICT"), nullable=True
    )

    # تدقيق
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # علاقات (اختيارية إن حاب تستخدمها في الواجهات)
    material_type = relationship("MaterialType", back_populates="materials", lazy="joined")
    currency = relationship("Currency", lazy="joined")
    created_by = relationship("User", foreign_keys=[created_by_id], lazy="joined")
    updated_by = relationship("User", foreign_keys=[updated_by_id], lazy="joined")

    def __repr__(self):
        return f"<Material(id={self.id}, name_en={self.name_en!r})>"

# فهارس إضافية مفيدة
Index("idx_materials_type", Material.material_type_id)
Index("idx_materials_currency", Material.currency_id)
