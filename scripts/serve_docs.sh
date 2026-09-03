#!/usr/bin/env bash
set -euo pipefail

source .venv/bin/activate
source "$(dirname "$0")/_docs_serve_banner.sh"

# ⚠️ Questo script lega la sola interfaccia LOCALE, ed e' una differenza
#    sostanziale rispetto a serve_docs_static.sh (che lega 0.0.0.0): da un
#    altro computer questo NON si raggiunge senza inoltro di porta. Il banner
#    lo dice, perche' prima entrambi stampavano lo stesso messaggio.
#    ⇒ Per esporlo sulla rete locale: BIND=0.0.0.0
BIND="${BIND:-127.0.0.1}"
PORTA="${PORTA:-8010}"

# 1. Genera docs DB e backend
python scripts/gen_db_docs.py
python scripts/gen_bk_docs.py

# 2. Preprocessa docs (include-markdown, link rewrite) senza build statico
python scripts/build_docs_zensical.py --skip-build "$@"

# 3. Serve con live reload sulla directory preprocessata
docs_serve_banner "$BIND" "$PORTA"
zensical serve -f mkdocs.zensical.yml -a "${BIND}:${PORTA}"
