from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from .base import Base

class MaterialType(Base):
    __tablename__ = "material_types"
    id = Column(Integer, primary_key=True)
    name_ar = Column(String(128), nullable=False)
    name_en = Column(String(128), nullable=False)
    name_tr = Column(String(128), nullable=False)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_by_user = relationship("User", foreign_keys=[created_by])
    updated_by_user = relationship("User", foreign_keys=[updated_by])

    materials = relationship(
        "Material",
        back_populates="material_type",
        lazy="selectin",
        passive_deletes=True,  # مع FK RESTRICT يخلي المنع من DB بدون كاسكيد
    )

    def __repr__(self):
        return f"<MaterialType(id={self.id}, name_en={self.name_en!r})>"