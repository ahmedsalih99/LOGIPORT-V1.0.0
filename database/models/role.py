from sqlalchemy import Column, Integer, String, Text, Table, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base
from .role_permission import RolePermission

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String(30), unique=True, nullable=False)
    label_ar = Column(String(50))
    label_en = Column(String(50))
    label_tr = Column(String(50))
    description = Column(Text)

    # NEW: علاقة مباشرة بالصلاحيات عبر جدول الربط role_permissions
    permissions = relationship(
        "Permission",
        secondary=RolePermission.__table__,
        lazy="joined"  # eager load مناسب لـ PermissionsService
    )

    users = relationship("User", back_populates="role")

    def __repr__(self):
        """String representation of Role"""
        return f"<Role(id={self.id}, name={self.name!r})>"