from sqlalchemy import (
    Column, Integer, String, Date, DateTime, Boolean, ForeignKey,
    Numeric, Float, Text, UniqueConstraint, Index, func
)
from sqlalchemy.orm import relationship
from database.models import Base

# ✨ استخدم تعريف TransactionItem الموحّد (بدون unit_label) من ملفه المخصص
try:
    # إذا كان transaction.py و transaction_item.py ضمن نفس الحزمة
    from .transaction_item import TransactionItem
except ImportError:  # مسار بديل لو هيكل المشروع مختلف
    from database.models.transaction_item import TransactionItem


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Header / identity
    transaction_no = Column(String(32), unique=True, nullable=False, index=True)
    transaction_date = Column(Date, nullable=False)
    transaction_type = Column(String(16), nullable=False, default="export")
    status = Column(String(16), nullable=False, default="active")  # بقيت لأجل التوافق مع الـ DB

    # Parties
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False)
    exporter_company_id = Column(Integer, ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    importer_company_id = Column(Integer, ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)

    # Relationship (store as code for flexibility: direct / intermediary / by_request / on_behalf)
    relationship_type = Column(String(32), nullable=True)
    broker_company_id = Column(Integer, ForeignKey("companies.id", ondelete="RESTRICT"), nullable=True)

    # Parties relationships
    client = relationship("Client", back_populates="transactions")

    exporter_company = relationship(
        "Company",
        foreign_keys=[exporter_company_id]
    )

    importer_company = relationship(
        "Company",
        foreign_keys=[importer_company_id]
    )

    broker_company = relationship(
        "Company",
        foreign_keys=[broker_company_id]
    )

    # Geography
    origin_country_id = Column(Integer, ForeignKey("countries.id", ondelete="RESTRICT"), nullable=True)
    dest_country_id = Column(Integer, ForeignKey("countries.id", ondelete="RESTRICT"), nullable=True)

    # Pricing defaults
    currency_id = Column(Integer, ForeignKey("currencies.id", ondelete="RESTRICT"), nullable=True)
    pricing_type_id = Column(Integer, ForeignKey("pricing_types.id", ondelete="RESTRICT"), nullable=True)
    delivery_method_id = Column(Integer, ForeignKey("delivery_methods.id", ondelete="RESTRICT"), nullable=True)

    # Logistics
    transport_type = Column(String(16), nullable=True)  # road/sea/air/rail (code)
    transport_ref = Column(String(64), nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    # Cached totals (optional)
    totals_count = Column(Float, nullable=True)
    totals_gross_kg = Column(Float, nullable=True)
    totals_net_kg = Column(Float, nullable=True)
    totals_value = Column(Numeric(12, 4), nullable=True)

    # Audit
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp(), nullable=False)
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False)

    # Relationships
    items = relationship("TransactionItem", back_populates="transaction", cascade="all, delete-orphan")
    entry_links = relationship("TransactionEntry", back_populates="transaction", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Transaction(id={self.id}, transaction_no ={self.transaction_no!r})>"

class TransactionEntry(Base):
    __tablename__ = "transaction_entries"
    __table_args__ = (
        UniqueConstraint("transaction_id", "entry_id", name="uq_transaction_entry"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    entry_id = Column(Integer, ForeignKey("entries.id", ondelete="RESTRICT"), nullable=False, index=True)

    transaction = relationship("Transaction", back_populates="entry_links")