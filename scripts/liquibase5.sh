#!/usr/bin/env bash
set -euo pipefail

git_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"

if [[ -n "${LIQUIBASE_BIN:-}" ]]; then
  LB5_BIN="${LIQUIBASE_BIN}"
elif [[ -n "$git_root" && -x "$git_root/tools/liquibase/current/liquibase" ]]; then
  LB5_BIN="$git_root/tools/liquibase/current/liquibase"
else
  LB5_BIN="/opt/liquibase"
fi

LB5_HOME="$(dirname "$LB5_BIN")"
LB5_EXTRA_ARGS=()

# Se presente, aggancia automaticamente il driver JDBC PostgreSQL locale.
# Non sovrascrive un --classpath esplicito passato dal chiamante.
has_classpath_arg=0
for a in "$@"; do
  case "$a" in
    --classpath|--classpath=*)
      has_classpath_arg=1
      break
      ;;
  esac
done

if [[ $has_classpath_arg -eq 0 && -n "$git_root" ]]; then
  shopt -s nullglob
  for pgjdbc in "$git_root"/tools/liquibase/jdbc/postgresql-*.jar; do
    LB5_EXTRA_ARGS+=("--classpath=$pgjdbc")
    break
  done
  shopt -u nullglob
fi

# comando liquibase (primo argomento non --*)
cmd=""
for a in "$@"; do
  [[ "$a" == --* ]] && continue
  cmd="$a"
  break
done

needs_changelog=0
case "$cmd" in
  update|updateSQL|validate|status|history|tag|rollback*|diff* )
    needs_changelog=1
    ;;
esac

# 1) check argomento --changeLogFile
uses_master_v2=0
for a in "$@"; do
  case "$a" in
    --changeLogFile=*changelog-master-v2.yaml)
      uses_master_v2=1
      ;;
  esac
done

# 2) fallback: check liquibase.properties (cwd o repo)
if [[ $uses_master_v2 -eq 0 ]]; then
  for prop in "./liquibase.properties" "$git_root/liquibase.properties" "$git_root/db/liquibase.properties"; do
    if [[ -f "$prop" ]] && grep -Eq '^\s*changeLogFile\s*=\s*(changelog/)?changelog-master-v2\.yaml\s*$|^\s*changeLogFile\s*=\s*db/changelog/changelog-master-v2\.yaml\s*$' "$prop"; then
      uses_master_v2=1
      break
    fi
  done
fi

#echo "[liquibase] git_root=$git_root"
#echo "[liquibase] cmd=$cmd needs_changelog=$needs_changelog uses_master_v2=$uses_master_v2"
#echo "[liquibase] pwd=$(pwd)"


if [[ $needs_changelog -eq 1 && $uses_master_v2 -eq 1 && -n "$git_root" ]]; then
  py="${PYTHON:-python3}"
  script="$git_root/scripts/gen_master_autogen.py"
  root="$git_root/db/changelog/migrations_v2"
  out="$git_root/db/changelog/migrations_v2/changelog-autogen.yaml"

  if [[ -f "$script" ]]; then
    echo "[liquibase] Genero changelog-autogen.yaml..."
    "$py" "$script" \
      --root "$root" \
      --out  "$out"  \
      --strict
  else
    echo "[liquibase] WARNING: gen_master_autogen.py non trovato: $script" >&2
  fi
fi

exec "${LB5_BIN}" "${LB5_EXTRA_ARGS[@]}" "$@"
