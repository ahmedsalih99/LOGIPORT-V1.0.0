# database/models/delivery_method.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from sqlalchemy.orm import relationship
from database.models import Base

class DeliveryMethod(Base):
    __tablename__ = "delivery_methods"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name_ar = Column(String(255), nullable=False)
    name_en = Column(String(255), nullable=True)
    name_tr = Column(String(255), nullable=True)

    is_active = Column(Boolean, nullable=False, server_default="1")
    sort_order = Column(Integer, nullable=False, server_default="100")

    # حسب نمط مشروعك؛ أبقيتها كما هي لتفادي هجرة إضافية الآن
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # علاقة عكسية مع التسعير
    prices = relationship("Pricing", back_populates="delivery_method")

    def __repr__(self):
        return f"<DeliveryMethod(id={self.id}, name_en={self.name_en!r})>"