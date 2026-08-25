from pathlib import Path

from pypdf import PdfReader
from sentence_transformers import SentenceTransformer


embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


def extract_text(filename: str, file_bytes: bytes) -> str:
    extension = Path(filename).suffix.lower()

    if extension == ".txt":
        return file_bytes.decode("utf-8")

    if extension == ".pdf":
        import io

        reader = PdfReader(io.BytesIO(file_bytes))

        pages = []

        for page in reader.pages:
            text = page.extract_text() or ""
            pages.append(text)

        return "\n".join(pages)

    raise ValueError("Only .txt and .pdf files are supported")


def create_chunks(text: str, chunk_size: int = 500, overlap: int = 50):
    text = text.strip()

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = end - overlap

    return chunks


def create_embeddings(chunks: list[str]):
    if not chunks:
        return []

    return embedding_model.encode(chunks).tolist()
import os
import numpy as np


def retrieve_relevant_chunks(query_embedding, chunks, top_k=None):
    """
    Return the most relevant document chunks for a query.
    """

    if top_k is None:
        top_k = int(os.getenv("RAG_TOP_K", "3"))

    if not chunks:
        return []

    query_vector = np.array(query_embedding, dtype=float)

    results = []

    for chunk in chunks:
        embedding = chunk.embedding

        if isinstance(embedding, str):
            import json
            embedding = json.loads(embedding)

        chunk_vector = np.array(embedding, dtype=float)

        similarity = np.dot(query_vector, chunk_vector) / (
            np.linalg.norm(query_vector) * np.linalg.norm(chunk_vector)
        )

        results.append((similarity, chunk))

    results.sort(key=lambda x: x[0], reverse=True)

    return results[:top_k]