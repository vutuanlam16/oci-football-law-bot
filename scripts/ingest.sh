#!/usr/bin/env sh
set -e
python scripts/ingest_folder.py --pdf-dir "${PDF_DIR:-/data/raw}" --doc-type "${1:-laws}"
