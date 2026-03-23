from .base import Base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    role_id   = Column(Integer, ForeignKey("roles.id",   ondelete="SET NULL"), nullable=True)
    office_id = Column(Integer, ForeignKey("offices.id", ondelete="SET NULL"), nullable=True)
    is_active    = Column(Boolean, default=True)
    avatar_path  = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    role   = relationship("Role",   back_populates="users")
    office = relationship("Office", back_populates="users", foreign_keys="[User.office_id]")
    audit_logs = relationship("AuditLog", back_populates="user")

    def __repr__(self):
        """String representation of User"""
        return f"<User(id={self.id}, username={self.username!r})>"