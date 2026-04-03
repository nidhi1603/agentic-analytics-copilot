from pathlib import Path

from app.retrieval.loader import load_document_chunks
from app.retrieval.vector_store import index_chunks


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = PROJECT_ROOT / "data" / "docs"


if __name__ == "__main__":
    chunks = load_document_chunks(DOCS_ROOT)
    indexed_count = index_chunks(chunks)
    print(f"Indexed {indexed_count} chunks into ChromaDB.")

