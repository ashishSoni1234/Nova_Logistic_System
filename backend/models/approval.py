from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True, index=True)
    workflow_run_id = Column(Integer, ForeignKey("workflow_runs.id"), nullable=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    title = Column(String(500), nullable=False, default="Approval Required")
    description = Column(Text, nullable=True)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_role = Column(String(50), nullable=True)
    status = Column(SAEnum(ApprovalStatus), default=ApprovalStatus.PENDING)
    comment = Column(Text, nullable=True)
    amount = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    workflow_run = relationship("WorkflowRun", back_populates="approvals")
    assignee = relationship("User", back_populates="approvals")
