# database/models/entry.py
from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime, Boolean, ForeignKey,
    Numeric, func, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from database.models import Base

class Entry(Base):
    __tablename__ = "entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_no = Column(String(50), nullable=True, unique=True)
    entry_date = Column(Date, nullable=False)

    transport_unit_type = Column(String(16), nullable=True)
    transport_ref = Column(String(64), nullable=True)
    seal_no = Column(String(64), nullable=True)

    # أزلنا: warehouse, location_note, is_active

    owner_client_id = Column(Integer, ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False, index=True)

    notes = Column(Text, nullable=True)

    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at    = Column(DateTime, server_default=func.now(), nullable=False)
    updated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at    = Column(DateTime, server_default=func.now(), onupdate=func.now())

    owner_client = relationship("Client", lazy="joined")
    created_by   = relationship("User", foreign_keys=[created_by_id], lazy="joined")
    updated_by   = relationship("User", foreign_keys=[updated_by_id], lazy="joined")

    items = relationship(
        "EntryItem",
        back_populates="entry",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )


    def __repr__(self):
        return f"<Entry(id={self.id}, entry_number={self.entry_number!r})>"

Index("idx_entries_date", Entry.entry_date)
Index("idx_entries_transport", Entry.transport_unit_type, Entry.transport_ref)
# أزلنا: Index("idx_entries_owner_active", Entry.owner_client_id, Entry.is_active)