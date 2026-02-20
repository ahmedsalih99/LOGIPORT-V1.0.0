from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from .base import Base

class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)

    __table_args__ = (UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),)

    def __repr__(self):
        return f"<RolePermission(id={self.id}, role_id={self.role_id})>"