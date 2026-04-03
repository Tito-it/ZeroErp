#!/usr/bin/env bash
set -euo pipefail

source .venv/bin/activate

echo "=== Generazione docs DB e backend ==="
python scripts/gen_db_docs.py
python scripts/gen_bk_docs.py

echo "=== Build statico ==="
python scripts/build_docs_zensical.py

echo "=== Copia in /tmp/zeroerp-docs-preview ==="
rm -rf /tmp/zeroerp-docs-preview
cp -r site-zensical/ /tmp/zeroerp-docs-preview/

echo "=== Serve su http://127.0.0.1:8010 ==="
echo "    (Ctrl+C per fermare)"
python -m http.server 8010 -d /tmp/zeroerp-docs-preview
