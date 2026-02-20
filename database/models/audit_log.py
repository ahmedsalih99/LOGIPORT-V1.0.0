from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from .base import Base

class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(50), nullable=False)  # create | update | delete | import | export | print
    table_name = Column(String(50), nullable=False)
    record_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)
    before_data = Column(Text, nullable=True)   # JSON string (optional)
    after_data = Column(Text, nullable=True)    # JSON string (optional)
    timestamp = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="audit_logs")


    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action!r})>"