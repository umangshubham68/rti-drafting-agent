"""Ingest the RTI ACT 2005 PDF into structured JSONL chunks.
Pipeline: Download pdf -> extract text -> clean -> parse into sections -> write JSONL.
Each output chunk is one section of the Act, with metadata for retrieval.
"""

from __future__ import annotations
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

import httpx
from pypdf import PdfReader

logger = logging.getLogger(__name__)

RTI_ACT_URL = "https://www.bis.gov.in/PDF/pdf/rti/RTI_2005.pdf"
DEFAULT_PDF_PATH = Path("data/raw/rti_act.pdf")
DEFAULT_JSONL_PATH = Path("data/processed/rti_act.jsonl")

@dataclass
class Chunk:
    """A retrievable unit - one section of the RTI Act."""

    chunk_id: str
    chapter: str | None
    section: str
    heading: str
    text: str
    source: str = "RTI Act 2005"
    source_url: str = RTI_ACT_URL