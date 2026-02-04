#!/usr/bin/env bash
set -euo pipefail

source .venv/bin/activate
python scripts/gen_db_docs.py
python scripts/gen_bk_docs.py
mkdocs serve
