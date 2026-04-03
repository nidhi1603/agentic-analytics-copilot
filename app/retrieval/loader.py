from pathlib import Path

from app.retrieval.chunker import chunk_markdown_document
from app.retrieval.models import DocumentChunk


def load_document_chunks(docs_root: Path) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []

    for file_path in sorted(docs_root.rglob("*.md")):
        if file_path.name in {"README.md", "catalog.md"}:
            continue
        chunks.extend(chunk_markdown_document(file_path))

    return chunks

