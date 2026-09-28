import os

from fastapi import (
    APIRouter, BackgroundTasks, Depends, File, HTTPException, Response, UploadFile, status,
)
from sqlalchemy.orm import Session

from app.utils.deps import get_current_user    # <- apne project ke hisaab se path badlo
from app.core.config import settings
from app.core.database import get_db
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentOut, UploadResponse
from app.services import ingestion_service

router = APIRouter(prefix="/documents", tags=["Documents"])


def _get_user_doc(db: Session, document_id: int, user_id: int) -> Document:
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == user_id)
        .first()
    )
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document nahi mila")
    return doc


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
def upload_pdf(
    background_tasks: BackgroundTasks,
    response: Response,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filename = os.path.basename(file.filename or "")
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Sirf PDF file allowed he")

    content = file.file.read()
    if len(content) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            f"File {settings.MAX_UPLOAD_MB}MB se badi he")
    if not content.startswith(b"%PDF"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ye valid PDF nahi he")

    result = ingestion_service.register_upload(db, current_user.id, filename, content)
    doc_out = DocumentOut.model_validate(result.document)

    if result.skipped:
        response.status_code = status.HTTP_200_OK
        return UploadResponse(
            message="Ye PDF (same content) pehle se added he, dobara process nahi ki", document=doc_out
        )

    background_tasks.add_task(
        ingestion_service.process_document, result.document.id, result.replace_ids
    )
    msg = (
        "Naya version processing me he, ready hote hi purana replace ho jayega"
        if result.replace_ids
        else "Upload ho gayi, processing background me chal rahi he"
    )
    return UploadResponse(message=msg, document=doc_out)


@router.get("", response_model=list[DocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .all()
    )


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_user_doc(db, document_id, current_user.id)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = _get_user_doc(db, document_id, current_user.id)
    ingestion_service.delete_document(db, doc.id)