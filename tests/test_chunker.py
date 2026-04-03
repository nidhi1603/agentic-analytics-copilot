from pathlib import Path

from app.retrieval.chunker import chunk_markdown_document


def test_chunk_markdown_document_splits_large_file(tmp_path: Path) -> None:
    file_path = tmp_path / "sample_doc.md"
    file_path.write_text(
        "# Title\n\n"
        + "Paragraph one. " * 30
        + "\n\n"
        + "Paragraph two. " * 30,
        encoding="utf-8",
    )

    chunks = chunk_markdown_document(file_path, max_chars=250, overlap_chars=40)

    assert len(chunks) >= 2
    assert chunks[0].source_path.endswith("sample_doc.md")
    assert chunks[0].doc_group == tmp_path.name

