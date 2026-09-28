"""
Qdrant (vector DB) connection setup. `ensure_collection()` is called
once on app startup (see main.py) so the collection always exists
before any endpoint tries to read/write vectors.
"""

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PayloadSchemaType, VectorParams

from app.core.config import settings

qdrant_client = QdrantClient(
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY,
)

# Search filter me use hone wale fields (int he; UUID he to KEYWORD use karo)
_INDEXED_FIELDS = {"user_id": PayloadSchemaType.KEYWORD, "document_id": PayloadSchemaType.INTEGER}


def ensure_collection() -> None:
    """Collection + payload indexes ensure karta he. Har startup par safe."""
    name = settings.QDRANT_COLLECTION

    existing = [c.name for c in qdrant_client.get_collections().collections]
    if name not in existing:
        qdrant_client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=settings.EMBEDDING_DIM, distance=Distance.COSINE),
        )

    info = qdrant_client.get_collection(name)

    # Purani collection ka vector size alag ho to saaf error de
    size = getattr(info.config.params.vectors, "size", None)
    if size is not None and size != settings.EMBEDDING_DIM:
        raise RuntimeError(
            f"Qdrant collection '{name}' ka vector size {size} he, but EMBEDDING_DIM="
            f"{settings.EMBEDDING_DIM} he. Collection delete karke restart karo "
            f"ya .env me sahi EMBEDDING_DIM daalo."
        )

    # Collection pehle se ho tab bhi missing indexes bana do
    indexed = info.payload_schema or {}
    for field_name, field_schema in _INDEXED_FIELDS.items():
        if field_name not in indexed:
            qdrant_client.create_payload_index(
                collection_name=name,
                field_name=field_name,
                field_schema=field_schema,
            )