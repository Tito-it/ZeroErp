#!/usr/bin/env bash
set -euo pipefail

source .venv/bin/activate
python scripts/gen_db_docs.py
python scripts/gen_bk_docs.py
python scripts/build_docs_zensical.py
zensical serve -f mkdocs.zensical.yml -a 127.0.0.1:8010 "$@"
