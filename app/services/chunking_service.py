from dataclasses import dataclass

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings
from app.utils.hashing import chunk_hash


@dataclass
class ChildChunk:
    text: str
    hash: str
    page: int          # 1-based page number
    parent_id: str
    parent_text: str


def load_pdf(path: str):
    """PDF ko page-wise LangChain Documents me load karta he."""
    return PyPDFLoader(path).load()


def build_parent_child_chunks(pages, document_id: int) -> tuple[list[ChildChunk], int]:
    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.PARENT_CHUNK_SIZE,
        chunk_overlap=settings.PARENT_CHUNK_OVERLAP,
    )
    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHILD_CHUNK_SIZE,
        chunk_overlap=settings.CHILD_CHUNK_OVERLAP,
    )

    parents = parent_splitter.split_documents(pages)
    children: list[ChildChunk] = []
    seen: set[str] = set()

    for idx, parent in enumerate(parents):
        parent_id = f"{document_id}-p{idx}"
        page = int(parent.metadata.get("page", 0)) + 1

        for text in child_splitter.split_text(parent.page_content):
            text = text.strip()
            if len(text) < 20:                # noise / bahut chhote chunks skip
                continue
            h = chunk_hash(text)
            if h in seen:                     # duplicate chunk skip
                continue
            seen.add(h)
            children.append(
                ChildChunk(text=text, hash=h, page=page,
                           parent_id=parent_id, parent_text=parent.page_content)
            )

    return children, len(parents)