# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025 Tid (Michele Carlo Titini) 
#
# Rilasciato sotto GNU GPLv3 o versione successiva.
# Vedi LICENSE.md per il testo completo della licenza.
# ------------------------------------------------------------
cat > scripts/check-license.sh << 'EOF'
#!/usr/bin/env bash
set -euo pipefail

REQUIRED="Copyright (C)"
EXTS="\(py\|js\|vue\|ya?ml\)$"
EXCLUDE="^docs/"
STATUS=0

files=$(git diff --cached --name-only --diff-filter=ACM)

for f in $files; do
  [[ ! "$f" =~ $EXTS ]] && continue
  [[ "$f"    =~ $EXCLUDE ]] && continue
  if ! head -n 10 "$f" | grep -q "$REQUIRED"; then
    echo "✖ Errore: manca l’header di licenza in $f"
    STATUS=1
  fi
done

(( STATUS != 0 )) && {
  echo && echo "Commit annullato: aggiungi l’header di licenza ai file indicati."
  exit 1
}

exit 0
EOF
