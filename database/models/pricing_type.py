from sqlalchemy import Column, Integer, String, Float, Boolean, Index
from sqlalchemy.orm import relationship
from database.models import Base

class PricingType(Base):
    __tablename__ = "pricing_types"

    id         = Column(Integer, primary_key=True)
    code       = Column(String, index=True)
    name_ar    = Column(String)
    name_en    = Column(String)
    name_tr    = Column(String)
    is_active  = Column(Integer, default=1)      # إبقها Integer إذا العمود موجود كـ INTEGER
    sort_order = Column(Integer, default=100)

    # الحقول الجديدة (منطق التسعير):
    compute_by = Column(String)   # 'QTY' | 'NET' | 'GROSS'
    price_unit = Column(String)   # 'UNIT' | 'KG'  | 'TON'
    divisor    = Column(Float)    # 1.0 أو 1000.0

    # ✅ لازم تتطابق مع back_populates في موديل Pricing
    prices = relationship(
        "Pricing",
        back_populates="pricing_type",
        lazy="selectin",                    # أداء أفضل في التحميل
        cascade="all, delete-orphan"       # غيّرها إذا ما بدك حذفًا متسلسلًا على مستوى ORM
    )

    # (اختياري) فهرس مساعد:
    # __table_args__ = (Index('ix_pricing_types_active_sort', 'is_active', 'sort_order'),)

    def __repr__(self):
        return f"<PricingType(id={self.id}, code={self.code!r})>"