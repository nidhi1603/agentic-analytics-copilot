import os
from pathlib import Path

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.utils.embedding_functions.openai_embedding_function import (
    OpenAIEmbeddingFunction,
)

from app.core.config import get_settings
from app.retrieval.models import DocumentChunk


def get_chroma_client() -> chromadb.PersistentClient:
    chroma_path = Path(get_settings().chroma_path)
    chroma_path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(chroma_path))


def get_collection() -> Collection:
    settings = get_settings()
    client = get_chroma_client()
    if settings.openai_api_key:
        os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)

    embedding_function = OpenAIEmbeddingFunction(
        api_key_env_var="OPENAI_API_KEY",
        model_name=settings.openai_embedding_model,
    )

    return client.get_or_create_collection(
        name=settings.chroma_collection_name,
        embedding_function=embedding_function,
    )


def index_chunks(chunks: list[DocumentChunk]) -> int:
    collection = get_collection()
    if not chunks:
        return 0

    collection.upsert(
        ids=[chunk.chunk_id for chunk in chunks],
        documents=[chunk.content for chunk in chunks],
        metadatas=[
            {
                "source_path": chunk.source_path,
                "title": chunk.title,
                "doc_group": chunk.doc_group,
                "chunk_index": chunk.chunk_index,
            }
            for chunk in chunks
        ],
    )
    return len(chunks)


def query_chunks(query_text: str, limit: int = 4) -> list[dict]:
    collection = get_collection()
    results = collection.query(query_texts=[query_text], n_results=limit)

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    output = []
    for document, metadata, distance in zip(documents, metadatas, distances):
        output.append(
            {
                "content": document,
                "metadata": metadata,
                "distance": distance,
            }
        )

    return output
