from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship
from .base import Base

class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True)
    code = Column(String(80), unique=True, nullable=False)  # رفعت السعة من 50 إلى 80 (اختياري)
    label_ar = Column(String(100))
    label_en = Column(String(100))
    label_tr = Column(String(100))
    description = Column(Text)

    roles = relationship(
        "Role",
        secondary="role_permissions",
        viewonly=True,
        lazy="raise_on_sql"  # اختياري: يمنع لود تلقائي غير مقصود
    )

    def __repr__(self):
        return f"<Permission(id={self.id}, name={self.name!r})>"