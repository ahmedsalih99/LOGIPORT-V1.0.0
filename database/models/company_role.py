from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from database.models import Base


class CompanyRole(Base):
    __tablename__ = "company_roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(64), nullable=False, unique=True, index=True)

    # Localized names
    name_ar = Column(String(255), nullable=False)
    name_en = Column(String(255), nullable=True)
    name_tr = Column(String(255), nullable=True)

    is_active = Column(Boolean, nullable=False, server_default="1")
    # Keep a stable ordering for UI (smaller first)
    sort_order = Column(Integer, nullable=False, server_default="100")

    # Links to companies via the association table
    links = relationship("CompanyRoleLink", back_populates="role", cascade="all, delete-orphan")


    def __repr__(self):
        return f"<CompanyRole(id={self.id}, code={self.code!r})>"