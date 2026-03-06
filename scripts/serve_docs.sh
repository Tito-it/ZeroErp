#!/usr/bin/env bash
set -euo pipefail

source .venv/bin/activate

# 1. Genera docs DB e backend
python scripts/gen_db_docs.py
python scripts/gen_bk_docs.py

# 2. Preprocessa docs (include-markdown, link rewrite) senza build statico
python scripts/build_docs_zensical.py --skip-build "$@"

# 3. Serve con live reload sulla directory preprocessata
zensical serve -f mkdocs.zensical.yml -a 127.0.0.1:8010
