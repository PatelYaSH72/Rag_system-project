import uuid

from qdrant_client.models import FieldCondition, Filter, FilterSelector, MatchValue, PointStruct

from app.core.config import settings
from app.core.qdrant import qdrant_client
from app.services.chunking_service import ChildChunk


def upsert_chunks(
    *,
    document_id: int,
    user_id: int,
    filename: str,
    file_hash: str,
    chunks: list[ChildChunk],
    vectors: list[list[float]],
    batch_size: int = 100,
) -> None:
    points = [
        PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{document_id}:{c.hash}")),
            vector=vec,
            payload={
                "user_id": str(user_id),
                "document_id": document_id,
                "filename": filename,
                "file_hash": file_hash,
                "page": c.page,
                "chunk_hash": c.hash,
                "parent_id": c.parent_id,
                "text": c.text,
                "parent_text": c.parent_text,
            },
        )
        for c, vec in zip(chunks, vectors)
    ]

    for i in range(0, len(points), batch_size):
        qdrant_client.upsert(
            collection_name=settings.QDRANT_COLLECTION,
            points=points[i : i + batch_size],
            wait=True,
        )


def delete_document_vectors(document_id: int) -> None:
    qdrant_client.delete(
        collection_name=settings.QDRANT_COLLECTION,
        points_selector=FilterSelector(
            filter=Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
            )
        ),
        wait=True,
    )