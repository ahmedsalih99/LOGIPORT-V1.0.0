from sqlalchemy import (
    Column, Integer, String, ForeignKey, Text, DateTime, func, Index, Boolean
)
from sqlalchemy.orm import relationship
from database.models.base import Base


class Client(Base):
    __tablename__ = "clients"
    code = Column(String(32), nullable=False, unique=True, index=True)
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Names (multi-language)
    name_ar = Column(String(255), nullable=False)
    name_en = Column(String(255), nullable=True)
    name_tr = Column(String(255), nullable=True)

    # Location
    country_id = Column(Integer, ForeignKey("countries.id", ondelete="RESTRICT"), nullable=True)
    city = Column(String(128), nullable=True)

    # Addresses (new multi-language) + legacy single address for backward-compat
    address_ar = Column(Text, nullable=True)
    address_en = Column(Text, nullable=True)
    address_tr = Column(Text, nullable=True)
    address = Column(Text, nullable=True)  # legacy, keep nullable

    # Defaults & meta
    default_currency_id = Column(Integer, ForeignKey("currencies.id", ondelete="RESTRICT"), nullable=True)
    default_delivery_method_id = Column(Integer, ForeignKey("delivery_methods.id", ondelete="SET NULL"), nullable=True)
    default_packaging_type_id = Column(Integer, ForeignKey("packaging_types.id", ondelete="SET NULL"), nullable=True)

    # Contacts (quick fields)
    phone = Column(String(64), nullable=True)
    email = Column(String(255), nullable=True)
    website = Column(String(255), nullable=True)

    # Tax
    tax_id = Column(String(128), nullable=True)

    # Other
    notes = Column(Text, nullable=True)

    # Audit
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    country = relationship("Country", lazy="joined")
    default_currency = relationship("Currency", lazy="joined")
    default_delivery_method = relationship("DeliveryMethod", foreign_keys=[default_delivery_method_id], lazy="joined")
    default_packaging_type = relationship("PackagingType", foreign_keys=[default_packaging_type_id], lazy="joined")
    created_by = relationship("User", foreign_keys=[created_by_id], lazy="joined")
    updated_by = relationship("User", foreign_keys=[updated_by_id], lazy="joined")
    contacts = relationship("ClientContact", back_populates="client", cascade="all, delete-orphan")

    transactions = relationship(
        "Transaction",
        back_populates="client",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Client(id={self.id}, name_ar={self.name_ar!r})>"

Index("idx_clients_country", Client.country_id)
Index("idx_clients_currency", Client.default_currency_id)


class ClientContact(Base):
    __tablename__ = "client_contacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    role_title = Column(String(128), nullable=True)
    phone = Column(String(64), nullable=True)
    email = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    is_primary = Column(Boolean, nullable=False, server_default="0")

    client = relationship("Client", back_populates="contacts")

Index("idx_contacts_primary", ClientContact.is_primary)