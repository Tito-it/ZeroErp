#!/usr/bin/env bash
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Scopo: Esegue in sequenza la suite pgTAP fatturazione/log.
# ------------------------------------------------------------

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$ROOT_DIR/scripts/testpgtap.sh"

TESTS=(
  "db/pgtap/vendite/test-fn-get-or-create-lotto-emittente.sql"
  "db/pgtap/vendite/test-lotto-segnalazioni-summary-v2.sql"
  "db/pgtap/vendite/test-sync-lotto-fatture-stato.sql"
  "db/pgtap/vendite/test-fatture-log-trigger-sync.sql"
  "db/pgtap/vendite/test-logs-guard-delete.sql"
  "db/pgtap/vendite/test-event-log-function-v1.sql"
)

if [[ ! -x "$RUNNER" ]]; then
  echo "Errore: runner non eseguibile o assente: $RUNNER" >&2
  exit 1
fi

echo "Suite pgTAP fatturazione/log"
echo "Runner: $RUNNER"
echo

passed=0
failed=0

for test_file in "${TESTS[@]}"; do
  echo "------------------------------------------------------------"
  echo "Eseguo: $test_file"
  echo "------------------------------------------------------------"

  if "$RUNNER" "$test_file"; then
    passed=$((passed + 1))
    echo "OK  - $test_file"
  else
    failed=$((failed + 1))
    echo "KO  - $test_file" >&2
  fi
  echo
done

echo "==================== Riepilogo ===================="
echo "Totale: ${#TESTS[@]}"
echo "Passati: $passed"
echo "Falliti: $failed"

if [[ $failed -gt 0 ]]; then
  exit 1
fi

exit 0
