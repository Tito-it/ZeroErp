#!/usr/bin/env bash
# ------------------------------------------------------------
# Scopo: installare Liquibase e il driver JDBC PostgreSQL nelle versioni
#   fissate in scripts/liquibase-versioni.env, dentro tools/liquibase/,
#   dove li cerca scripts/liquibase5.sh.
#
#   tools/liquibase/<versione>/              Liquibase Community
#   tools/liquibase/current -> <versione>    il collegamento letto dal wrapper
#   tools/liquibase/jdbc/postgresql-<v>.jar  il driver
#
# `tools/` non è nel repository (.gitignore): ogni macchina lo popola con
# questo script, dalle sorgenti ufficiali (release GitHub di Liquibase, Maven
# Central per il driver), e ogni file scaricato si verifica sullo SHA-256
# scritto in liquibase-versioni.env. Un file che non torna non si installa.
#
# Idempotente: ciò che c'è già nella versione giusta non si riscarica. Le
# versioni vecchie restano dove sono (non si cancella niente): il wrapper usa
# comunque quella fissata.
#
# Requisiti: bash, curl, tar, sha256sum. Java 17 serve per eseguire Liquibase,
# non per installarlo.
#
# Uso: scripts/installa-liquibase.sh
# ------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# shellcheck source=liquibase-versioni.env
source "$SCRIPT_DIR/liquibase-versioni.env"

DEST="$REPO_ROOT/tools/liquibase"
LB_DIR="$DEST/$LIQUIBASE_VERSION"
JDBC_DIR="$DEST/jdbc"
JDBC_JAR="$JDBC_DIR/postgresql-$PGJDBC_VERSION.jar"

LB_URL="https://github.com/liquibase/liquibase/releases/download/v$LIQUIBASE_VERSION/liquibase-$LIQUIBASE_VERSION.tar.gz"
JDBC_URL="https://repo1.maven.org/maven2/org/postgresql/postgresql/$PGJDBC_VERSION/postgresql-$PGJDBC_VERSION.jar"

for cmd in curl tar sha256sum; do
  command -v "$cmd" >/dev/null || { echo "❌ manca il comando: $cmd" >&2; exit 1; }
done

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Scopo: scaricare un file e verificarne lo SHA-256; esce con errore se non coincide.
scarica_verificato() {
  local url="$1" out="$2" atteso="$3"
  echo "↓ $url"
  curl -fsSL --retry 3 -o "$out" "$url"
  if ! echo "$atteso  $out" | sha256sum -c --quiet -; then
    echo "❌ SHA-256 non coincide per $url" >&2
    echo "   atteso:  $atteso" >&2
    echo "   trovato: $(sha256sum "$out" | cut -d' ' -f1)" >&2
    exit 1
  fi
}

mkdir -p "$DEST" "$JDBC_DIR"

# 1) Liquibase
if [[ -x "$LB_DIR/liquibase" ]]; then
  echo "✓ Liquibase $LIQUIBASE_VERSION già presente in $LB_DIR"
else
  scarica_verificato "$LB_URL" "$TMP/liquibase.tar.gz" "$LIQUIBASE_SHA256"
  mkdir -p "$TMP/lb"
  tar -xzf "$TMP/liquibase.tar.gz" -C "$TMP/lb"
  [[ -x "$TMP/lb/liquibase" ]] || { echo "❌ l'archivio non contiene l'eseguibile liquibase" >&2; exit 1; }
  mv "$TMP/lb" "$LB_DIR"
  echo "✓ Liquibase $LIQUIBASE_VERSION installato in $LB_DIR"
fi
ln -sfn "$LIQUIBASE_VERSION" "$DEST/current"

# 2) Driver JDBC
if [[ -f "$JDBC_JAR" ]] && echo "$PGJDBC_SHA256  $JDBC_JAR" | sha256sum -c --quiet - 2>/dev/null; then
  echo "✓ driver PostgreSQL $PGJDBC_VERSION già presente"
else
  scarica_verificato "$JDBC_URL" "$TMP/postgresql.jar" "$PGJDBC_SHA256"
  mv "$TMP/postgresql.jar" "$JDBC_JAR"
  echo "✓ driver PostgreSQL $PGJDBC_VERSION installato in $JDBC_DIR"
fi

# 3) Prova: la versione che risponde è quella fissata
if command -v java >/dev/null; then
  "$DEST/current/liquibase" --version 2>/dev/null | grep -i 'liquibase version' || true
else
  echo "⚠️ Java non trovato: Liquibase è installato, ma per eseguirlo serve Java 17"
fi
echo "Ora si usa sempre scripts/liquibase5.sh."
