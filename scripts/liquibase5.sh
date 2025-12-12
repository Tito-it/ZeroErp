#!/usr/bin/env bash
set -euo pipefail

LB5_HOME="/opt/liquibase5"

# --- root repo ---
git_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"

# --- trova il comando liquibase (primo argomento che non inizia con --) ---
cmd=""
for a in "$@"; do
  if [[ "$a" != --* ]]; then
    cmd="$a"
    break
  fi
done

# --- comandi che leggono changelog ---
needs_changelog=0
case "$cmd" in
  update|updateSQL|validate|status|history|tag|rollback*|diff* )
    needs_changelog=1
    ;;
esac

# --- rigenera SOLO se stai usando il master-v2 (evita rigenerazioni inutili) ---
uses_master_v2=0
for a in "$@"; do
  case "$a" in
    --changeLogFile=db/changelog/changelog-master-v2.yaml|--changeLogFile=./db/changelog/changelog-master-v2.yaml)
      uses_master_v2=1
      ;;
  esac
done

if [[ $needs_changelog -eq 1 && $uses_master_v2 -eq 1 && -n "$git_root" ]]; then
  py="${PYTHON:-python3}"

  script="$git_root/scripts/gen_master_autogen.py"
  root="$git_root/db/changelog/migrations_v2"
  out="$git_root/db/changelog/migrations_v2/changelog-autogen.yaml"
  base="$git_root/db/changelog"

  if [[ -f "$script" ]]; then
    echo "[liquibase5] Genero changelog-autogen.yaml..."
    "$py" "$script" \
      --root "$root" \
      --out  "$out"  \
      --base "$base" \
      --strict
  else
    echo "[liquibase5] WARNING: gen_master_autogen.py non trovato: $script" >&2
  fi
fi

exec "${LB5_HOME}/liquibase" "$@"
