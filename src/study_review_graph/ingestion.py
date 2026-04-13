"""Document ingestion and normalization utilities."""

from __future__ import annotations

import re
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from study_review_graph.state import NormalizedDocument, RawDocument

SUPPORTED_SUFFIXES = {".pdf", ".md", ".txt"}


def discover_source_files(input_dir: Path) -> list[Path]:
    """Return supported source files under the provided input directory."""

    if not input_dir.exists():
        return []

    return sorted(
        path
        for path in input_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )


def load_raw_documents(input_dir: Path) -> list[RawDocument]:
    """Load supported documents from disk into raw document records."""

    raw_docs: list[RawDocument] = []
    for path in discover_source_files(input_dir):
        if path.suffix.lower() == ".pdf":
            text = _read_pdf(path)
            media_type = "application/pdf"
        else:
            text = path.read_text(encoding="utf-8")
            media_type = "text/markdown" if path.suffix.lower() == ".md" else "text/plain"

        raw_docs.append(
            RawDocument(
                document_id=str(uuid5(NAMESPACE_URL, str(path.resolve()))),
                source_path=str(path),
                media_type=media_type,
                text=text,
                metadata={"filename": path.name},
            )
        )

    return raw_docs


def normalize_documents(raw_docs: list[RawDocument]) -> list[NormalizedDocument]:
    """Normalize whitespace and capture section-like headings."""

    normalized_docs: list[NormalizedDocument] = []
    for raw_doc in raw_docs:
        content = re.sub(r"\n{3,}", "\n\n", raw_doc.text).strip()
        sections = _extract_sections(content)
        normalized_docs.append(
            NormalizedDocument(
                document_id=raw_doc.document_id,
                source_path=raw_doc.source_path,
                content=content,
                sections=sections,
                metadata=raw_doc.metadata,
            )
        )

    return normalized_docs


def _extract_sections(content: str) -> list[str]:
    """Capture likely headings to seed concept and content mapping."""

    sections = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            sections.append(stripped.lstrip("# ").strip())
        elif stripped.endswith(":") and len(stripped.split()) <= 8:
            sections.append(stripped[:-1])
    return sections


def _read_pdf(path: Path) -> str:
    """Read PDF pages into a single string."""

    try:
        from langchain_community.document_loaders import PyPDFLoader
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "PDF support requires langchain-community to be installed."
        ) from exc

    loader = PyPDFLoader(str(path))
    pages = loader.load()
    return "\n\n".join(page.page_content for page in pages)
