"""CLI wrapper: run the full RTI Act ingestion pipeline."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path so we can import from `app`
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ingestion.rti_act import (  # noqa: E402
    DEFAULT_JSONL_PATH,
    DEFAULT_PDF_PATH,
    ingest,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
)
logger = logging.getLogger("ingest_rti_act")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest the RTI Act 2005 into JSONL chunks.")
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF_PATH,
                        help=f"Path to the PDF (default: {DEFAULT_PDF_PATH})")
    parser.add_argument("--output", type=Path, default=DEFAULT_JSONL_PATH,
                        help=f"Path to output JSONL (default: {DEFAULT_JSONL_PATH})")
    parser.add_argument("--force-download", action="store_true",
                        help="Redownload PDF even if it already exists")
    args = parser.parse_args()

    chunks = ingest(args.pdf, args.output, force_download=args.force_download)

    # Sanity print
    if chunks:
        print(f"\n{'=' * 60}")
        print(f"Ingestion complete — {len(chunks)} chunks")
        print(f"{'=' * 60}")
        print(f"Sections found: {[c.section for c in chunks]}")
        print(f"\nSample (Section {chunks[0].section}: {chunks[0].heading}):")
        print(chunks[0].text[:400] + "..." if len(chunks[0].text) > 400 else chunks[0].text)


if __name__ == "__main__":
    main()