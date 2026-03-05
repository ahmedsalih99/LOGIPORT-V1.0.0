"""
database/models/office.py
==========================
نموذج المكاتب — Office Model

كل مكتب له:
  - كود فريد (TR-01, SY-01, SY-02 ...)
  - اسم بالعربي والإنجليزي والتركي
  - البلد
  - حالة نشاط
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from sqlalchemy.orm import relationship
from .base import Base


class Office(Base):
    __tablename__ = "offices"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    code        = Column(String(20),  unique=True,  nullable=False, index=True)  # TR-01, SY-01
    name_ar     = Column(String(100), nullable=False)   # مكتب تركيا
    name_en     = Column(String(100), nullable=True)    # Turkey Office
    name_tr     = Column(String(100), nullable=True)    # Türkiye Ofisi
    country     = Column(String(5),   nullable=True)    # TR / SY / LB ...
    city        = Column(String(100), nullable=True)    # Istanbul / Damascus
    is_active   = Column(Boolean,     default=True,     nullable=False)
    sort_order  = Column(Integer,     default=0,        nullable=False)
    notes       = Column(String(500), nullable=True)
    created_at  = Column(DateTime, server_default=func.now())
    updated_at  = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # ── Relationships ────────────────────────────────────────────────────────
    users        = relationship("User",        back_populates="office",
                                foreign_keys="User.office_id")
    transactions = relationship("Transaction", back_populates="office",
                                foreign_keys="Transaction.office_id")

    def get_name(self, lang: str = "ar") -> str:
        """يُرجع الاسم حسب اللغة مع fallback للعربي."""
        return getattr(self, f"name_{lang}", None) or self.name_ar or self.code

    def __repr__(self):
        return f"<Office(id={self.id}, code={self.code!r}, name_ar={self.name_ar!r})>"