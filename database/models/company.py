from sqlalchemy import (
    Column, Integer, String, ForeignKey, Boolean, Text, DateTime, func, Index, Float, UniqueConstraint
)
from sqlalchemy.orm import relationship
from database.models import Base

# Re-export CompanyRole here so imports like
#   from database.models.company import CompanyRole
# keep working consistently across the app.
from .company_role import CompanyRole  # noqa: F401


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Names (multi-language)
    name_ar = Column(String(255), nullable=False)
    name_en = Column(String(255), nullable=True)
    name_tr = Column(String(255), nullable=True)

    # Owner (a Client record) — NOT NULL in DB
    owner_client_id = Column(Integer, ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False, index=True)

    # Location
    country_id = Column(Integer, ForeignKey("countries.id", ondelete="RESTRICT"), nullable=True)
    city = Column(String(128), nullable=True)

    # Addresses (multi-language) — DB currently has only the localized fields
    address_ar = Column(Text, nullable=True)
    address_en = Column(Text, nullable=True)
    address_tr = Column(Text, nullable=True)

    # Defaults & meta
    default_currency_id = Column(Integer, ForeignKey("currencies.id", ondelete="RESTRICT"), nullable=True)


    # Contacts
    phone = Column(String(64), nullable=True)
    email = Column(String(255), nullable=True)
    website = Column(String(255), nullable=True)

    # Tax & registration
    tax_id = Column(String(128), nullable=True)
    registration_number = Column(String(128), nullable=True)

    # Other
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="1")

    # Audit
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships (lazy joined for common lookups)
    owner_client = relationship("Client", foreign_keys=[owner_client_id], lazy="joined")
    country = relationship("Country", lazy="joined")
    default_currency = relationship("Currency", lazy="joined")
    created_by = relationship("User", foreign_keys=[created_by_id], lazy="joined")
    updated_by = relationship("User", foreign_keys=[updated_by_id], lazy="joined")

    # Links
    roles = relationship("CompanyRoleLink", back_populates="company", cascade="all, delete-orphan")
    partners = relationship("CompanyPartnerLink", back_populates="company", cascade="all, delete-orphan")
    banks = relationship("CompanyBank", back_populates="company", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Company(id={self.id}, name={self.name!r})>"

# Helpful indexes matching the DB
Index("idx_companies_owner", Company.owner_client_id)
Index("idx_companies_country", Company.country_id)
Index("idx_companies_active", Company.is_active)


class CompanyRoleLink(Base):
    __tablename__ = "company_role_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("company_roles.id", ondelete="CASCADE"), nullable=False, index=True)

    company = relationship("Company", back_populates="roles")
    role = relationship("CompanyRole", back_populates="links", lazy="joined")


class CompanyPartnerLink(Base):
    __tablename__ = "company_partner_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)

    partner_role = Column(String(128), nullable=True)
    share_percent = Column(Float, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="1")
    notes = Column(Text, nullable=True)

    company = relationship("Company", back_populates="partners")
    client = relationship("Client", lazy="joined")

    __table_args__ = (
        UniqueConstraint("company_id", "client_id", name="uq_company_partner"),
    )


class CompanyBank(Base):
    __tablename__ = "company_banks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    bank_name = Column(String(255), nullable=True)
    branch = Column(String(255), nullable=True)
    beneficiary_name = Column(String(255), nullable=True)
    iban = Column(String(64), nullable=True)
    swift_bic = Column(String(64), nullable=True)
    account_number = Column(String(64), nullable=True)

    bank_country_id = Column(Integer, ForeignKey("countries.id", ondelete="RESTRICT"), nullable=True)
    currency_id = Column(Integer, ForeignKey("currencies.id", ondelete="RESTRICT"), nullable=True)

    is_primary = Column(Boolean, nullable=False, server_default="0")
    notes = Column(Text, nullable=True)

    company = relationship("Company", back_populates="banks")
    bank_country = relationship("Country", lazy="joined", foreign_keys=[bank_country_id])
    currency = relationship("Currency", lazy="joined")


Index("idx_company_banks_company", CompanyBank.company_id)
