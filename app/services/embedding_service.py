from functools import lru_cache

from app.core.config import settings


@lru_cache
def _fastembed_model():
    from fastembed import TextEmbedding
    return TextEmbedding(model_name=settings.EMBEDDING_MODEL)


@lru_cache
def _openai_client():
    from openai import OpenAI
    return OpenAI(api_key=settings.EMBEDDING_API_KEY, base_url=settings.EMBEDDING_BASE_URL)


def embed_texts(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    if not texts:
        return []

    if settings.EMBEDDING_PROVIDER == "fastembed":
        return [v.tolist() for v in _fastembed_model().embed(texts, batch_size=batch_size)]

    if settings.EMBEDDING_PROVIDER == "openai_compatible":
        client = _openai_client()
        vectors: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            resp = client.embeddings.create(
                model=settings.EMBEDDING_MODEL, input=texts[i : i + batch_size]
            )
            vectors.extend(d.embedding for d in resp.data)
        return vectors

    raise ValueError(f"Unknown EMBEDDING_PROVIDER: {settings.EMBEDDING_PROVIDER}")