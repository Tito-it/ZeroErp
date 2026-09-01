#!/usr/bin/env bash
set -euo pipefail

source .venv/bin/activate
source "$(dirname "$0")/_docs_serve_banner.sh"

# ⚠️ Bind DICHIARATO, non implicito. `python -m http.server` senza `--bind`
#    ascolta gia' su 0.0.0.0: il comportamento non cambia, ma prima era una
#    scelta subita e non scritta — la documentazione finiva sulla rete locale
#    senza che nessuno l'avesse deciso. Ora e' esplicito, e il banner lo dice.
#    ⇒ Per limitarlo alla sola macchina: BIND=127.0.0.1
BIND="${BIND:-0.0.0.0}"
PORTA="${PORTA:-8010}"

echo "=== Generazione docs DB e backend ==="
python scripts/gen_db_docs.py
python scripts/gen_bk_docs.py

echo "=== Build statico ==="
python scripts/build_docs_zensical.py

echo "=== Copia in /tmp/zeroerp-docs-preview ==="
rm -rf /tmp/zeroerp-docs-preview
cp -r site-zensical/ /tmp/zeroerp-docs-preview/

docs_serve_banner "$BIND" "$PORTA"
python -m http.server "$PORTA" --bind "$BIND" -d /tmp/zeroerp-docs-preview
