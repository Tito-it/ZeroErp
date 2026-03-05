#!/usr/bin/env bash
set -euo pipefail

source .venv/bin/activate

PREVIEW_ROOT="/tmp/zeroerp-docs-preview"
DOCS_OUT="${PREVIEW_ROOT}/docs"
CFG_OUT="${PREVIEW_ROOT}/mkdocs.zensical.yml"
SITE_OUT="${PREVIEW_ROOT}/site"

rm -rf "${PREVIEW_ROOT}"
mkdir -p "${PREVIEW_ROOT}"

python scripts/build_docs_zensical.py \
  --docs-out "${DOCS_OUT}" \
  --config-out "${CFG_OUT}" \
  --site-dir "${SITE_OUT}"

echo "[docs] Avvio server locale su 127.0.0.1:8010 (root: ${SITE_OUT})"
python -m http.server 8010 --bind 127.0.0.1 --directory "${SITE_OUT}"
