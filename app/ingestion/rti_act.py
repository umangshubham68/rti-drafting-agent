"""Ingest the RTI Act 2005 PDF into structured JSONL chunks.

Pipeline: download PDF → extract text → clean → parse into sections → write JSONL.
Each output chunk is one section of the Act, with metadata for retrieval.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx
from pypdf import PdfReader

logger = logging.getLogger(__name__)


# --- Constants ---

RTI_ACT_URL = "https://www.bis.gov.in/PDF/pdf/rti/RTI2005.pdf"
DEFAULT_PDF_PATH = Path("data/raw/rti_act.pdf")
DEFAULT_JSONL_PATH = Path("data/processed/rti_act.jsonl")


# --- Data model ---

@dataclass
class Chunk:
    """A retrievable unit — one section of the RTI Act."""

    chunk_id: str
    chapter: str | None
    section: str
    heading: str
    text: str
    source: str = "rti_act_2005"
    source_url: str = RTI_ACT_URL


# --- Regex patterns ---

# Chapter header: "CHAPTER I" or "CHAPTER I — Preliminary"
CHAPTER_RE = re.compile(
    r"^\s*(?:CHAPTER|Chapter)\s+([IVXLCDM]+)\b(?:\s*[—-]?\s*(.+))?\s*$"
)

# Section header: "1. Short title, extent and commencement.—"
# or with body on same line: "2. Definitions.—In this Act, unless..."
# Groups: 1=section number (allows "4A" after amendments), 2=heading, 3=body_first_line
SECTION_RE = re.compile(
    r"^\s*(\d+[A-Z]?)\.\s+([A-Z][^.]+?)\.\s*[—-]\s*(.*)$"
)

# Lines to strip: bare page numbers, repeated PDF headers/footers
NOISE_PATTERNS = [
    re.compile(r"^\s*\d+\s*$"),
    re.compile(r"^\s*Right to Information Act,?\s*2005\s*$", re.IGNORECASE),
    re.compile(r"^\s*Page\s+\d+(\s+of\s+\d+)?\s*$", re.IGNORECASE),
]


# --- Download ---

def download_pdf(url: str = RTI_ACT_URL, output_path: Path = DEFAULT_PDF_PATH,
                 force: bool = False) -> Path:
    """Download the PDF to output_path. Skips if already present unless force=True."""
    if output_path.exists() and not force:
        logger.info(f"{output_path} already exists — skipping download")
        return output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Downloading {url}")

    with httpx.Client(follow_redirects=True, timeout=60.0) as client:
        response = client.get(url)
        response.raise_for_status()
        output_path.write_bytes(response.content)

    size_kb = output_path.stat().st_size / 1024
    logger.info(f"Saved {output_path} ({size_kb:.1f} KB)")
    return output_path


# --- Extract ---

def extract_text(pdf_path: Path) -> str:
    """Extract all text from PDF, joined by newlines."""
    reader = PdfReader(str(pdf_path))
    pages = [page.extract_text() or "" for page in reader.pages]
    logger.info(f"Extracted {len(pages)} pages from {pdf_path}")
    return "\n".join(pages)


def clean_text(text: str) -> str:
    """Strip repeated PDF headers/footers, normalize whitespace."""
    kept = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            kept.append("")
            continue
        if any(pattern.match(stripped) for pattern in NOISE_PATTERNS):
            continue
        kept.append(stripped)
    return "\n".join(kept)


# --- Parse ---

def parse_chunks(text: str) -> list[Chunk]:
    """Walk text line by line, emit one Chunk per section detected."""
    current_chapter: str | None = None
    current_section: str | None = None
    current_heading: str = ""
    buffer: list[str] = []
    chunks: list[Chunk] = []

    def flush() -> None:
        if current_section is None:
            return
        body = "\n".join(buffer).strip()
        if not body:
            return
        chunks.append(
            Chunk(
                chunk_id=f"rti_act_s{current_section}",
                chapter=current_chapter,
                section=current_section,
                heading=current_heading,
                text=body,
            )
        )

    for line in text.split("\n"):
        chapter_match = CHAPTER_RE.match(line)
        if chapter_match:
            current_chapter = chapter_match.group(1)
            continue

        section_match = SECTION_RE.match(line)
        if section_match:
            flush()
            current_section = section_match.group(1)
            current_heading = section_match.group(2).strip()
            body_first = section_match.group(3).strip()
            buffer = [body_first] if body_first else []
            continue

        if current_section is not None:
            buffer.append(line)

    flush()
    logger.info(f"Parsed {len(chunks)} sections")
    return chunks


# --- Write ---

def write_jsonl(chunks: list[Chunk], output_path: Path) -> None:
    """Write chunks as JSONL — one JSON object per line."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")
    logger.info(f"Wrote {len(chunks)} chunks to {output_path}")


# --- Top-level pipeline ---

def ingest(
    pdf_path: Path = DEFAULT_PDF_PATH,
    output_path: Path = DEFAULT_JSONL_PATH,
    force_download: bool = False,
) -> list[Chunk]:
    """Full pipeline: download (if needed) → extract → clean → parse → write."""
    if not pdf_path.exists() or force_download:
        download_pdf(RTI_ACT_URL, pdf_path, force=force_download)

    raw = extract_text(pdf_path)
    cleaned = clean_text(raw)
    chunks = parse_chunks(cleaned)
    write_jsonl(chunks, output_path)
    return chunks


