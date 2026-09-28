import logging
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.services.chunking_service import build_parent_child_chunks, load_pdf
from app.services.embedding_service import embed_texts
from app.services.vector_store import delete_document_vectors, upsert_chunks
from app.utils.hashing import sha256_bytes

logger = logging.getLogger(__name__)


@dataclass
class UploadResult:
    document: Document
    replace_ids: list[int] = field(default_factory=list)   # purane versions jo hatane he
    skipped: bool = False


# ---------- helpers ----------
def _save_file(user_id: int, file_hash: str, content: bytes) -> str:
    folder = Path(settings.UPLOAD_DIR) / str(user_id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{file_hash}.pdf"
    path.write_bytes(content)
    return str(path)


def _get_by_hash(db: Session, user_id: int, file_hash: str) -> Document | None:
    return (
        db.query(Document)
        .filter(Document.user_id == user_id, Document.file_hash == file_hash)
        .first()
    )


# ---------- step 1: upload register (request ke andar, fast) ----------
def register_upload(db: Session, user_id: int, filename: str, content: bytes) -> UploadResult:
    file_hash = sha256_bytes(content)

    # Same content pehle se he? (failed ho to retry karenge)
    doc = _get_by_hash(db, user_id, file_hash)
    if doc and doc.status != DocumentStatus.FAILED:
        return UploadResult(document=doc, skipped=True)

    if doc is None:
        doc = Document(
            user_id=user_id,
            filename=filename,
            file_hash=file_hash,
            file_path=_save_file(user_id, file_hash, content),
            file_size=len(content),
            status=DocumentStatus.PENDING,
        )
        db.add(doc)
    else:  # pichhli baar fail hui thi -> retry
        doc.filename = filename
        doc.file_path = _save_file(user_id, file_hash, content)
        doc.status = DocumentStatus.PENDING
        doc.error_message = None

    try:
        db.commit()
    except IntegrityError:  # same file ki 2 requests ek saath aayi
        db.rollback()
        return UploadResult(document=_get_by_hash(db, user_id, file_hash), skipped=True)
    db.refresh(doc)

    # Same filename, alag content -> ye purana version he, naya ready hone ke baad hatega
    olds = (
        db.query(Document)
        .filter(Document.user_id == user_id, Document.filename == filename, Document.id != doc.id)
        .all()
    )
    return UploadResult(document=doc, replace_ids=[d.id for d in olds])


# ---------- step 2: background processing ----------
def _ingest(db: Session, document_id: int) -> None:
    doc = db.get(Document, document_id)
    if doc is None:
        return

    doc.status = DocumentStatus.PROCESSING
    db.commit()

    pages = load_pdf(doc.file_path)
    chunks, n_parents = build_parent_child_chunks(pages, doc.id)
    if not chunks:
        raise ValueError("PDF me readable text nahi mila (scanned PDF ho sakti he, OCR chahiye)")

    vectors = embed_texts([c.text for c in chunks])
    upsert_chunks(
        document_id=doc.id,
        user_id=doc.user_id,
        filename=doc.filename,
        file_hash=doc.file_hash,
        chunks=chunks,
        vectors=vectors,
    )

    doc.total_pages = len(pages)
    doc.total_parent_chunks = n_parents
    doc.total_child_chunks = len(chunks)
    doc.status = DocumentStatus.COMPLETED
    db.commit()


def _mark_failed(db: Session, document_id: int, error: str) -> None:
    doc = db.get(Document, document_id)
    if doc:
        doc.status = DocumentStatus.FAILED
        doc.error_message = error[:1000]
        db.commit()


def process_document(document_id: int, replace_ids: list[int] | None = None) -> None:
    """BackgroundTasks me chalta he, isliye apna DB session banata he."""
    db = SessionLocal()
    try:
        try:
            _ingest(db, document_id)
        except Exception as exc:
            logger.exception("Ingestion failed for document %s", document_id)
            db.rollback()
            try:
                delete_document_vectors(document_id)   # adhure vectors saaf
            except Exception:
                logger.exception("Vector cleanup failed for document %s", document_id)
            _mark_failed(db, document_id, str(exc))
            return  # fail hua to purana version safe rahega

        # Naya successfully add ho gaya -> ab purane versions hatao
        for old_id in replace_ids or []:
            try:
                delete_document(db, old_id)
            except Exception:
                logger.exception("Old document %s delete failed", old_id)
    finally:
        db.close()


# ---------- delete ----------
def delete_document(db: Session, document_id: int) -> None:
    doc = db.get(Document, document_id)
    if doc is None:
        return
    delete_document_vectors(doc.id)                      # Qdrant se chunks
    Path(doc.file_path).unlink(missing_ok=True)          # disk se file
    db.delete(doc)                                       # Postgres se row
    db.commit()