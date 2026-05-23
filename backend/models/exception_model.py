from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class Severity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Exception(Base):
    __tablename__ = "exceptions"

    id = Column(Integer, primary_key=True, index=True)
    workflow_run_id = Column(Integer, ForeignKey("workflow_runs.id"), nullable=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    exception_type = Column(String(100), nullable=False, default="general")
    reason = Column(Text, nullable=False)
    severity = Column(SAEnum(Severity), default=Severity.MEDIUM)
    details = Column(Text, nullable=True)
    resolved = Column(Boolean, default=False)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    workflow_run = relationship("WorkflowRun", back_populates="exceptions")
