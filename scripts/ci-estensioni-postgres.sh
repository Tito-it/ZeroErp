#!/usr/bin/env bash
# Installa nel container Postgres della CI le estensioni che l'immagine non porta:
# postgis (+ topology), pgtap, plpgsql_check. Lo usano i due workflow che
# applicano le migrazioni (ci.yaml, ci-validate.yaml): la sede e' questa.
#
# Uso:  scripts/ci-estensioni-postgres.sh <id-container>  [database]
#       (nei workflow: ${{ job.services.postgres.id }})
#
# ⭐ Perche' apt e non un'immagine con postgis dentro: dal 21-11-2026 dbdev e' su
#   PostgreSQL 19 e postgis/postgis non ha ancora un tag 19 definitivo (solo
#   19rcN). L'immagine e' `postgres:<major>` ufficiale, che ha gia' il repo PGDG:
#   le estensioni vengono dalla STESSA fonte di dbdev, quindi con le stesse
#   versioni (postgis segue PGDG, btree_gist & co. vengono col contrib della major).
#
# ⭐ La major si legge dal SERVER, non dal nome dell'immagine: il numero di
#   versione sta in un posto solo, l'`image:` del workflow.
#
# ⚠️ Si installa nel container del service, non sul runner: postgres gira li'
#   dentro e le estensioni le carica dal SUO filesystem.
#
# ⚠️ Riavvio OBBLIGATORIO dopo l'apt-get. Le dipendenze possono tirare su la
#   minor PGDG piu' recente della major, che sovrascrive i .so in
#   /usr/lib/postgresql/<major>/lib mentre il postmaster della minor
#   dell'immagine e' ancora in piedi: il primo backend che carica plpgsql.so
#   muore con «undefined symbol» (12-11-2026, immagine 18.6, apt 18.7:
#   heap_datum_update_type). Il riavvio allinea binario e librerie; pacchetti e
#   dati restano, perche' restart non ricrea il container.
#
# ℹ️ pgagent resta fuori, come prima: la CI non lo ha mai avuto, e il changeSet
#   001-01-02 lo salta (preCondition su pg_available_extensions). Su PGDG il
#   pacchetto `pgagent` 4.2.3 non porta ancora i file per la 19.
set -euo pipefail

CID="${1:?uso: $0 <id-container> [database]}"
DB="${2:-zeroerp}"

q() { docker exec "$CID" psql -U postgres -d "$DB" -X -tAc "$1"; }
attendi() {
  for _ in $(seq 1 60); do
    docker exec "$CID" pg_isready -U postgres -d "$DB" -q && return 0
    sleep 1
  done
  docker exec "$CID" pg_isready -U postgres -d "$DB"
}

attendi
MAJOR="$(( $(q 'SHOW server_version_num') / 10000 ))"
echo "── server: $(q 'SELECT version()')"
echo "── installo le estensioni per la major $MAJOR"

# `apt-get update` e' il pezzo lento: un solo giro per tutti i pacchetti.
# `-scripts` si nomina esplicito: e' quello che porta i .control di postgis.
docker exec "$CID" bash -euo pipefail -c "
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
    postgresql-$MAJOR-postgis-3 postgresql-$MAJOR-postgis-3-scripts \
    postgresql-$MAJOR-pgtap postgresql-$MAJOR-plpgsql-check >/dev/null
"

docker restart "$CID" >/dev/null
attendi
echo "── dopo il riavvio: $(q 'SELECT version()')"

# Verifica che postgres le veda davvero: senza, i changeSet condizionali
# verrebbero saltati e un guardrail fallirebbe piu' tardi con un messaggio
# meno chiaro di questo.
ATTESE="btree_gist dblink pg_trgm pgcrypto pgtap plpgsql_check postgis postgis_topology unaccent uuid-ossp"
manca=0
for e in $ATTESE; do
  v="$(q "SELECT default_version FROM pg_available_extensions WHERE name = '$e'")"
  if [[ -z "$v" ]]; then
    echo "::error::estensione '$e' non disponibile nel container"
    manca=1
  else
    printf '   %-18s %s\n' "$e" "$v"
  fi
done
exit "$manca"
