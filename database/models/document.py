from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from database.models import Base


class Document(Base):
    """ORM model for documents table.

    Columns (from DB):
      id, group_id, document_type_id, language, template_id, status,
      file_path, totals_json, totals_text, data_json,
      created_by_id, created_at, updated_by_id, updated_at
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)

    group_id = Column(Integer, ForeignKey("doc_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    document_type_id = Column(Integer, ForeignKey("document_types.id", ondelete="RESTRICT"), nullable=False, index=True)
    language = Column(Text, nullable=False)

    template_id = Column(Integer, ForeignKey("document_templates.id", ondelete="SET NULL"), nullable=True)

    status = Column(Text, nullable=False, default="draft")
    file_path = Column(Text, nullable=True)

    totals_json = Column(Text, nullable=True)
    totals_text = Column(Text, nullable=True)
    data_json = Column(Text, nullable=True)

    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime, nullable=True)

    # Relationships
    group = relationship("DocumentGroup", back_populates="documents")
    document_type = relationship("DocumentType", back_populates="documents")
    template = relationship("DocumentTemplate")

    def __repr__(self):
        return f"<Document(id={self.id}, document_number={self.document_number!r})>"

class DocumentTemplate(Base):
    __tablename__ = "document_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_type_id = Column(Integer, ForeignKey("document_types.id", ondelete="CASCADE"), nullable=False)
    language = Column(Text, nullable=False)
    version = Column(Text, nullable=False, default="v1")
    storage_path = Column(Text, nullable=True)
    is_active = Column(Integer, nullable=False, default=1)

    document_type = relationship("DocumentType")