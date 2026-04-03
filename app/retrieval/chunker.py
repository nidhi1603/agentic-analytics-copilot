from pathlib import Path

from app.retrieval.models import DocumentChunk


def chunk_markdown_document(
    file_path: Path,
    max_chars: int = 800,
    overlap_chars: int = 120,
) -> list[DocumentChunk]:
    raw_text = file_path.read_text(encoding="utf-8").strip()
    if not raw_text:
        return []

    sections = [section.strip() for section in raw_text.split("\n\n") if section.strip()]
    chunks: list[DocumentChunk] = []
    current = ""
    chunk_index = 0

    for section in sections:
        proposed = section if not current else f"{current}\n\n{section}"
        if len(proposed) <= max_chars:
            current = proposed
            continue

        if current:
            chunks.append(
                _build_chunk(
                    file_path=file_path,
                    content=current,
                    chunk_index=chunk_index,
                )
            )
            chunk_index += 1

            overlap = current[-overlap_chars:] if overlap_chars > 0 else ""
            current = f"{overlap}\n\n{section}".strip()
        else:
            chunks.append(
                _build_chunk(
                    file_path=file_path,
                    content=section[:max_chars],
                    chunk_index=chunk_index,
                )
            )
            chunk_index += 1
            current = section[max_chars - overlap_chars :].strip()

    if current:
        chunks.append(
            _build_chunk(
                file_path=file_path,
                content=current,
                chunk_index=chunk_index,
            )
        )

    return chunks


def _build_chunk(file_path: Path, content: str, chunk_index: int) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=f"{file_path.stem}-chunk-{chunk_index}",
        content=content.strip(),
        source_path=str(file_path),
        title=file_path.stem.replace("_", " ").title(),
        doc_group=file_path.parent.name,
        chunk_index=chunk_index,
    )

