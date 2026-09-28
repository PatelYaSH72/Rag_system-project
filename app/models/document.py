from sqlalchemy import (
    Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func,
)

from app.core.database import Base
from sqlalchemy.dialects.postgresql import UUID


class DocumentStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("user_id", "file_hash", name="uq_documents_user_file_hash"),
        Index("ix_documents_user_filename", "user_id", "filename"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
            UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )

    filename = Column(String(255), nullable=False)
    file_hash = Column(String(64), nullable=False)          # SHA-256 of PDF bytes
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False)

    total_pages = Column(Integer, default=0, nullable=False)
    total_parent_chunks = Column(Integer, default=0, nullable=False)
    total_child_chunks = Column(Integer, default=0, nullable=False)

    status = Column(String(20), default=DocumentStatus.PENDING, nullable=False, index=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())