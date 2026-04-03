from dataclasses import dataclass


@dataclass
class DocumentChunk:
    chunk_id: str
    content: str
    source_path: str
    title: str
    doc_group: str
    chunk_index: int

