from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.models import Base

class DocumentGroup(Base):
    __tablename__ = "doc_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    doc_no = Column(Text, nullable=False, index=True)

    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)   # <-- جديد ومتوافق مع DB
    seq = Column(Integer, nullable=False)

    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    transaction = relationship("Transaction")
    created_by = relationship("User", foreign_keys=[created_by_id])
    documents = relationship("Document", back_populates="group", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("year", "month", "seq", name="uq_doc_groups_ym_seq"),  # <-- القيد الشهري
    )

    def __repr__(self):
        return f"<DocumentGroup(id={self.id}, code={self.code!r})>"