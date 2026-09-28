from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    file_hash: str
    file_size: int
    total_pages: int
    total_parent_chunks: int
    total_child_chunks: int
    status: str
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class UploadResponse(BaseModel):
    message: str
    document: DocumentOut