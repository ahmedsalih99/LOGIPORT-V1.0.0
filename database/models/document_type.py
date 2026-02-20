from __future__ import annotations
from sqlalchemy import Column, Integer, Text, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from database.models import Base


class DocumentType(Base):
    """
    ORM model for document_types.

    Columns:
      id, code, name_ar, name_en, name_tr, is_active,
      group_code, template_path, sort_order
    """
    __tablename__ = "document_types"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # كود فريد قصير (مثل: INV_PRO, INV_COM, PL_SIMPLE ...)
    code = Column(Text, nullable=False, index=True, unique=True)

    # أسماء للواجهة
    name_ar = Column(Text, nullable=True)
    name_en = Column(Text, nullable=True)
    name_tr = Column(Text, nullable=True)

    # مفعّل/معطّل
    is_active = Column(Integer, nullable=False, default=1)

    # === الحقول الجديدة ===
    # مفتاح منطقي يحدد نوع المستند ويربطه بالراوتر/البلدر (مثال: "invoice.proforma")
    group_code = Column(Text, nullable=True)  # index defined in __table_args__

    # مجلد القوالب ضمن documents/templates (مثال: "invoices/proforma")
    template_path = Column(Text, nullable=True)

    # لترتيب الظهور اختياري
    sort_order = Column(Integer, nullable=False, default=0)

    documents = relationship("Document", back_populates="document_type")

    __table_args__ = (
        # تأكيد فُرادة code عبر مستوى الجدول أيضاً
        UniqueConstraint("code", name="uq_document_types_code"),
        # فهرس مساعد للاستعلامات حسب المجموعة
        Index("ix_document_types_group_code", "group_code"),
    )

    # مساعد بسيط لإرجاع الاسم بلغة الواجهة
    def title(self, lang: str = "en") -> str:
        lang = (lang or "en").lower()
        if lang == "ar":
            return self.name_ar or self.name_en or self.name_tr or self.code
        if lang == "tr":
            return self.name_tr or self.name_en or self.name_ar or self.code
        return self.name_en or self.name_ar or self.name_tr or self.code

    def __repr__(self):
        return f"<DocumentType(id={self.id}, name_en={self.name_en!r})>"