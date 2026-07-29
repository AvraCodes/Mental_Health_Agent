"""
Ingest research paper PDFs into ChromaDB using Google embeddings.

Usage:
    python scripts/ingest_papers.py

Set GOOGLE_API_KEY in your environment before running.
"""

import os
import hashlib
from pathlib import Path
from pypdf import PdfReader
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import (
    DATA_DIR,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    GOOGLE_API_KEY,
)
from backend.rag import add_documents


def extract_text_from_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def main():
    if not GOOGLE_API_KEY:
        print("ERROR: GOOGLE_API_KEY environment variable not set.")
        print("Set it before running: $env:GOOGLE_API_KEY='your-key'")
        sys.exit(1)

    pdf_dir = Path(__file__).resolve().parent.parent
    pdf_files = list(pdf_dir.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in {pdf_dir}")
        sys.exit(0)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for pdf_path in pdf_files:
        print(f"Processing: {pdf_path.name} ...")
        text = extract_text_from_pdf(pdf_path)
        chunks = chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
        print(f"  Extracted {len(text)} chars -> {len(chunks)} chunks")

        docs = []
        for i, chunk in enumerate(chunks):
            chunk_id = hashlib.md5(f"{pdf_path.name}_{i}".encode()).hexdigest()
            docs.append({
                "id": chunk_id,
                "text": chunk,
                "source": pdf_path.name,
                "page": str(i + 1),
            })

        add_documents(docs)
        print(f"  Ingested {len(docs)} chunks into ChromaDB.")

    print("\nDone. All papers ingested.")


if __name__ == "__main__":
    main()