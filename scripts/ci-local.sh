#!/usr/bin/env bash
# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Riproduce IN LOCALE la passata di migrate della CI, su un database SCRATCH.
#   Copyright (C) 2026 Tid (Michele Carlo Titini)
#
# A COSA SERVE, in una riga:
#   «trovare il prossimo changeSet che rompe un database ricostruito da zero,
#    senza aspettare un giro di GitHub Actions».
#
# ── ⭐ IL GUADAGNO VERO NON E' LA VELOCITA': E' L'INCREMENTALITA' ──────
#   GitHub ricostruisce il container a ogni corsa, quindi ogni volta ripercorre
#   tutti i changeSet dall'inizio. Qui il database scratch RESTA: dopo una
#   costruzione completa, una ri-esecuzione applica solo cio' che manca.
#   ⇒ Il ciclo «correggo → provo» passa da una corsa intera a pochi secondi.
#
#   ⚠️ E vale finche' si lavora sulla FRONTIERA. Se una correzione tocca un
#   changeSet gia' applicato, l'incrementale non la vede: li' serve `--fresh`.
#
# ── ⛔ COSA NON RIPRODUCE, E PERCHE' E' UNA SCELTA ─────────────────────
#   * la passata `--contexts=ci_apply` gira solo con `--ci-apply`, sapendo
#     cosa si sta facendo (vedi «LE PASSATE» qui sotto);
#   * i test Django e la build della documentazione: non c'entrano col migrate.
#   ⇒ Copre la passata `--contexts="!provision and !dati_macchina"`, che e' dove il migrate si
#   ferma ogni volta.
#   ⭐ Il ruolo batch `zeroerp_batch_fatturazione` (BYPASSRLS), il suo
#   provisioning e il ponte che lo teneva in piedi qui sono stati ritirati il
#   2026-10-15 (brief-db-ruoli-di-sistema, fase 4): il backend non lo usa dal
#   2026-09-05.
#
# ── ⭐ LE PASSATE, E SONO QUATTRO — nello stesso ordine di ci-validate.yaml ──
#     1. provision PRE   (superuser) · changelog-provision-pre.yaml
#     2. principale      (zeroerp_owner) · `!provision and !dati_macchina`
#     3. provision POST  (superuser)     · changelog-provision-post.yaml
#     4. automazioni     (zeroerp_owner) · `ci_apply` — solo con `--ci-apply`
#   ⚠️ La 3 e' arrivata il 2026-09-09, e mancava: contiene i changeSet
#   `context: provision` che la passata principale (`!provision`) non vede MAI
#   — fra cui quello che da a `postgres` l'owner delle sei funzioni dichiarate
#   in `dbops.sec_functions_owner`. Senza, `dblink` le rifiuta e il canale del
#   giornale dei job TACE. Dettaglio accanto al passo.
#   ⛔ La 4 resta dietro un flag: `--fresh` NON la comprende, e uno scratch
#   senza automazioni non e' confrontabile con la CI — dal 2026-09-09 lo dice
#   un cancello in scripts/pgtap-baseline.sh invece di una riga di prosa.
#
# ── ⚠️ ISOLAMENTO DAL DATABASE DI SVILUPPO ────────────────────────────
#   I ruoli PostgreSQL sono di cluster, i database no. Percio' qui:
#     * i ruoli di sistema NON si ricreano se esistono, e la loro password non
#       si tocca (provision_zeroerp.sql);
#     * le loro GUC si impostano con `ALTER ROLE … IN DATABASE <scratch>`, mai
#       globalmente — altrimenti si riscriverebbe la configurazione con cui
#       lavora il database di sviluppo;
#     * lo script RIFIUTA di operare sul database nominato in `db/internal.env`.
#
# USO:
#   scripts/ci-local.sh              # incrementale: riprende da dove si era fermato
#   scripts/ci-local.sh --fresh      # ricostruisce il database scratch da zero
#   scripts/ci-local.sh --ci-apply   # + la passata delle automazioni (vedi sopra)
#   CI_DB=altro_nome scripts/ci-local.sh
#   La password del superuser: da ~/.pgpass, o chiesta al terminale (vedi
#   «L'utenza admin» piu' sotto). PGPASSWORD_POSTGRES resta, ma va in history.
#
# ── ⭐ E PREPARA LO SCRATCH ANCHE PER I pgTAP, sempre e da solo ────────
#   Il migrate costruisce lo schema, ma la suite pretende altre tre cose che in
#   CI fanno tre passi separati dopo Liquibase. Qui si fanno in fondo, sempre,
#   e sono tutte e tre idempotenti:
#
#     1. l'estensione `pgtap` — non la crea nessun changelog. Senza, ogni file
#        muore su `SELECT plan(N)`;
#     2. lo schema `django`, COPIATO da `$DEV_DB` — lo costruisce
#        `manage.py migrate`, che su questa macchina non c'e'. Sedici
#        funzioni plpgsql scrivono e leggono `django.auth_user`.
#        ⛔ SENZA le ACL (`pg_dump --no-acl`), ed e' il punto: su dev quelle
#        tabelle portano `zeroerp_app=arwd/titodb` dato A MANO, che nessuno
#        script concedeva. Copiandolo, lo scratch aveva un privilegio che la
#        CI non ha, e 23 file (fra cui ogni pgTAP che crea un operatore)
#        erano verdi qui e «permission denied for table auth_user» la' —
#        47 volte nel log Postgres della corsa 34723456630 (12-09), tutti in
#        baseline come ERRORE_FIXTURE senza che la causa fosse letta;
#     3. i privilegi di `zeroerp_app` (la fase post di provision_zeroerp.sql) —
#        senza, ogni rosso e' un permesso e non un difetto. DOPO la copia di
#        `django`, come in ci-validate.yaml sta dopo `manage.py migrate`: il
#        `GRANT … ON ALL TABLES` e' una fotografia, e deve vedere anche le
#        tabelle del secondo migratore. Dal 2026-09-13 `django` e' nella
#        whitelist del provisioning: e' li' che il privilegio e' dichiarato.
#
#   ⚠️ Nessun flag: una preparazione che dipende da cosa uno si ricorda non
#   sopravvive a un `--fresh`. E' la lezione del `GRANT USAGE` su `maintenance`,
#   che esisteva solo su dbdev perche' era stato dato a mano — e per questo un
#   pgTAP era verde qui e rosso su ogni installazione nuova. Il punto 2 e' la
#   stessa lezione una seconda volta, con un aggravante: qui il privilegio a
#   mano NON restava su dev, lo si COPIAVA, e lo scratch smetteva di essere
#   un metro.
#   ⛔ Lo schema `django` si COPIA: e' fedele oggi, e invecchia in silenzio il
#   giorno in cui arriva una migration Django nuova. La strada fedele resta
#   lanciare `manage.py migrate` DAL SERVER BACKEND puntando a questo host.
#
# PREREQUISITI: `sudo -u postgres` (per creare il database) e `db/internal.env`
#   per host/porta.
# ⚠️ Liquibase si invoca SEMPRE via `scripts/liquibase5.sh`, mai un binario nel
#   PATH: dal 02-09-2026 nel PATH non ce n'e' piu' nessuno (l'installazione di
#   sistema `/opt/liquibase-5.0.2` e i suoi symlink sono stati rimossi), cosi'
#   un `liquibase` nudo fallisce subito invece di far girare in silenzio una
#   versione vecchia e senza driver. Il wrapper prende
#   `tools/liquibase/current` (5.0.4, la stessa della CI) e il driver JDBC
#   versionato nel repo (`tools/liquibase/jdbc/postgresql-42.7.10.jar`).
# ------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

# ⭐ Il MODELLO DEI RUOLI DI SISTEMA (brief-db-ruoli-di-sistema): migra
#   `zeroerp_owner`, i ruoli e il database li crea scripts/sql/provision_zeroerp.sql,
#   e in coda si VERIFICA che l'owner sia uno solo. Lo scratch curato e'
#   `zeroerp_ruoli`, le password in $ZEROERP_RUOLI_ENV (sotto).
#   ⚠️ Il modo vecchio (`--classico`: migratore `zeroerp`/`secret`, database
#   `zeroerp_ci`) e' stato ritirato il 2026-10-15, dopo la prima corsa della CI
#   di GitHub sul modello con i pgTAP verdi (fase 4).
CI_DB="${CI_DB:-zeroerp_ruoli}"
FRESH=false
CI_APPLY=false
for a in "$@"; do
  case "$a" in
    --fresh)    FRESH=true ;;
    --ci-apply) CI_APPLY=true ;;
    # ⚠️ Il numero di riga finale si CALCOLA, non si scrive: inchiodato a 73
    #   l'aiuto troncava in silenzio la coda dell'intestazione ogni volta che
    #   qualcuno la allungava — successo il 2026-09-09 aggiungendo l'elenco
    #   delle quattro passate, che ha spinto fuori i PREREQUISITI.
    -h|--help)  sed -n "2,$(($(grep -n '^set -euo pipefail' "$0" | head -1 | cut -d: -f1) - 1))p" "$0"; exit 0 ;;
    *) echo "Opzione sconosciuta: $a" >&2; exit 1 ;;
  esac
done

# --- Chi migra: `zeroerp_owner`, con la password presa da un file FUORI dal
#     repo (D-3: nessun default). Il file contiene, una per riga:
#       ZEROERP_OWNER_PASSWORD=…
#       ZEROERP_JOB_PASSWORD=…
#     ⚠️ Servono solo a CREARE i due ruoli la prima volta: i ruoli sono di
#     cluster, e di un ruolo che esiste lo script non tocca la password. Dalla
#     seconda corsa in poi la password di zeroerp_owner serve a Liquibase per
#     collegarsi, quindi deve restare quella.
ZEROERP_RUOLI_ENV="${ZEROERP_RUOLI_ENV:-$HOME/.config/zeroerp/ruoli-sviluppo.env}"
if [[ ! -f "$ZEROERP_RUOLI_ENV" ]]; then
  cat >&2 <<MSG
⛔ Manca il file delle password dei ruoli di sistema: $ZEROERP_RUOLI_ENV
   Va creato a mano, fuori dal repo, con permessi 600:
     mkdir -p "$(dirname "$ZEROERP_RUOLI_ENV")"
     printf 'ZEROERP_OWNER_PASSWORD=%s\nZEROERP_JOB_PASSWORD=%s\n' '<pwd owner>' '<pwd job>' > "$ZEROERP_RUOLI_ENV"
     chmod 600 "$ZEROERP_RUOLI_ENV"
MSG
  exit 1
fi
# shellcheck disable=SC1090
set -a; . "$ZEROERP_RUOLI_ENV"; set +a
: "${ZEROERP_OWNER_PASSWORD:?manca ZEROERP_OWNER_PASSWORD in $ZEROERP_RUOLI_ENV}"
: "${ZEROERP_JOB_PASSWORD:?manca ZEROERP_JOB_PASSWORD in $ZEROERP_RUOLI_ENV}"
MIGR=zeroerp_owner
MIGR_PWD="$ZEROERP_OWNER_PASSWORD"

# --- Host/porta dal file env del progetto (NON il nome del database)
[[ -f db/internal.env ]] || { echo "Manca db/internal.env" >&2; exit 1; }
# shellcheck disable=SC1091
set -a; . db/internal.env; set +a
PGHOST="${PGHOST:-${DB_HOST:-localhost}}"
PGPORT="${PGPORT:-${DB_PORT:-5432}}"
DEV_DB="${DB_NAME:-zeroerp}"

# ⛔ Il cancello che rende questo script sicuro: non si tocca il database di
#    sviluppo, per nessuna ragione e con nessuna variabile d'ambiente.
if [[ "$CI_DB" == "$DEV_DB" ]]; then
  echo "⛔ RIFIUTO: CI_DB ('$CI_DB') e' il database di sviluppo. Scegline un altro." >&2
  exit 1
fi

export PGHOST PGPORT
psql_admin() { sudo -u postgres psql --no-psqlrc -v ON_ERROR_STOP=1 -X -q "$@"; }

# --- L'utenza admin per Liquibase (provision pre/post): serve un SUPERUSER,
#     perche' quei changeSet creano estensioni (postgis, pgtap, plpgsql_check,
#     dblink) che non sono «trusted».
ADMIN_USER="${CI_ADMIN_USER:-postgres}"
ADMIN_PWD="${PGPASSWORD_POSTGRES:-}"

# ⭐ La password del superuser NON si scrive sulla riga di comando (finirebbe
#   nella history della shell). Se PGPASSWORD_POSTGRES e' vuota la si prende
#   dalla riga di ~/.pgpass (o $PGPASSFILE) per host, porta e utente admin;
#   se manca anche li', e c'e' un terminale, la si chiede senza eco.
#   ⚠️ Serve leggerla a mano: Liquibase usa JDBC, che ~/.pgpass non lo legge.
#   Le regole del file sono quelle di libpq: `*` vale per tutto, `\:` e `\\`
#   sono i caratteri letterali, vince la prima riga che combacia.
pgpass_password() {   # host porta database utente → stampa la password, o niente
  local f="${PGPASSFILE:-$HOME/.pgpass}" riga campo c i
  local -a campi
  [[ -r "$f" ]] || return 0
  while IFS= read -r riga || [[ -n "$riga" ]]; do
    [[ -z "$riga" || "$riga" == \#* ]] && continue
    campi=(); campo=""
    for (( i = 0; i < ${#riga}; i++ )); do
      c="${riga:i:1}"
      if [[ "$c" == '\' ]]; then (( i++ )); campo+="${riga:i:1}"
      elif [[ "$c" == ':' && ${#campi[@]} -lt 4 ]]; then campi+=("$campo"); campo=""
      else campo+="$c"
      fi
    done
    campi+=("$campo")
    (( ${#campi[@]} == 5 )) || continue
    [[ "${campi[0]}" == '*' || "${campi[0]}" == "$1" ]] || continue
    [[ "${campi[1]}" == '*' || "${campi[1]}" == "$2" ]] || continue
    [[ "${campi[2]}" == '*' || "${campi[2]}" == "$3" ]] || continue
    [[ "${campi[3]}" == '*' || "${campi[3]}" == "$4" ]] || continue
    printf '%s' "${campi[4]}"
    return 0
  done < "$f"
}
if [[ -z "$ADMIN_PWD" ]]; then
  ADMIN_PWD="$(pgpass_password "$PGHOST" "$PGPORT" postgres "$ADMIN_USER")"
  [[ -n "$ADMIN_PWD" ]] && echo "── password di '$ADMIN_USER' presa da ${PGPASSFILE:-~/.pgpass}"
fi
if [[ -z "$ADMIN_PWD" && -t 0 ]]; then
  read -r -s -p "Password di '$ADMIN_USER' (per Liquibase, non viene mostrata): " ADMIN_PWD
  echo
fi

# ⛔ PRE-VOLO. Liquibase si connette via TCP, non col socket: `sudo -u postgres`
#   qui non aiuta, serve una PASSWORD. Meglio scoprirlo adesso, in due secondi,
#   che dopo aver creato il database e macinato meta' provisioning.
# ⚠️ Si PROVA la connessione invece di pretendere una password: se il cluster ha
#   `trust` sul TCP locale, una password non serve — e un controllo sulla
#   variabile vuota direbbe di no a un caso che funziona.
if ! PGPASSWORD="$ADMIN_PWD" psql -X -q -A -t -w \
      -h "$PGHOST" -p "$PGPORT" -U "$ADMIN_USER" -d postgres \
      -c "SELECT 1" >/dev/null 2>&1; then
  cat >&2 <<MSG
⛔ Non riesco a connettermi via TCP come '$ADMIN_USER'.
   Liquibase usa JDBC, quindi il socket e 'sudo -u postgres' non bastano: i passi
   di provisioning creano ESTENSIONI (postgis, pgtap, plpgsql_check, dblink), che
   richiedono un superuser con password.

   Due strade:
     1) se il ruolo '$ADMIN_USER' ha gia' una password, mettila in ~/.pgpass
        (permessi 600), che lo script legge da solo:
          $PGHOST:$PGPORT:*:$ADMIN_USER:<password>
        oppure lancia lo script da un terminale: la chiede senza mostrarla.
     2) se hai un ALTRO superuser con password, usalo, con la sua riga in ~/.pgpass:
          CI_ADMIN_USER=<ruolo> CI_DB=$CI_DB $0 ${*:-}
   (PGPASSWORD_POSTGRES='<password>' funziona ancora, ma resta nella history.)

   ⚠️ Assegnare una password a 'postgres' e' una modifica al CLUSTER, quindi
   condivisa col database di sviluppo: falla solo se sai di volerla.
MSG
  exit 1
fi
echo "── admin per il provisioning: $ADMIN_USER (connessione TCP verificata)"

# ⛔ Il ruolo batch ritirato (2026-10-15) non deve esistere nel cluster: la
#   preCondition di 20260729-05 conta i ruoli batch con la postura sbagliata, e
#   il ponte che la aggirava qui e' stato tolto con lui. Meglio dirlo adesso che
#   a meta' migrate. Solo con --fresh: sullo scratch esistente quel changeSet e'
#   gia' passato.
if $FRESH && psql_admin -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='zeroerp_batch_fatturazione'" | grep -q 1; then
  echo "⛔ Il ruolo zeroerp_batch_fatturazione esiste ancora nel cluster: va ritirato prima." >&2
  echo "   scripts/ritira_ruoli_dismessi.sh zeroerp_batch_fatturazione   (prova a vuoto, poi --esegui)" >&2
  exit 1
fi

echo "── database scratch: $CI_DB   (sviluppo: $DEV_DB, intoccato)"

if $FRESH; then
  echo "── ricostruisco da zero"
  psql_admin -d postgres -c "DROP DATABASE IF EXISTS \"$CI_DB\" WITH (FORCE);"
fi

# ⭐ I ruoli di sistema e il database con owner zeroerp_owner: li crea lo
#   script del modello (fase ruoli), sul database `postgres`. Dallo STDIN,
#   come le altre fasi: `postgres` non attraversa /home/tid.
APP_PWD_MODELLO="$(awk -F: -v db="$DEV_DB" '$3==db && $4=="zeroerp_app" {print $5; exit}' ~/.pgpass 2>/dev/null || true)"
echo "── ruoli di sistema e database $CI_DB (provision_zeroerp.sql, fase ruoli)"
psql_admin -d postgres -v fase=ruoli -v db_name="$CI_DB" \
  -v owner_password="$ZEROERP_OWNER_PASSWORD" -v job_password="$ZEROERP_JOB_PASSWORD" \
  -v app_password="$APP_PWD_MODELLO" \
  < scripts/sql/provision_zeroerp.sql >/dev/null
# ⚠️ Il canale dblink del migratore resta VUOTO, come in CI: la stringa di
#   connessione con la password finirebbe in pg_db_role_setting, che ogni
#   ruolo puo' leggere. fn_get_or_create_session_tx_id prende il ramo della
#   sentinella, avvisa e prosegue.
psql_admin -d "$CI_DB" <<SQL
ALTER ROLE zeroerp_owner IN DATABASE "$CI_DB" SET myapp.user_language = 'it';
ALTER ROLE zeroerp_owner IN DATABASE "$CI_DB" SET myapp.dblink_log_connection = '';
SQL

# --- L'autogen, come in CI: l'ordine dei changeSet e' generato, non versionato
echo "── rigenero changelog-autogen.yaml (--strict)"
python3 scripts/gen_master_autogen.py \
  --root db/changelog/migrations_v2 \
  --out  db/changelog/migrations_v2/changelog-autogen.yaml \
  --strict

URL_CI="jdbc:postgresql://${PGHOST}:${PGPORT}/${CI_DB}?options=-c%20myapp.env%3Dci"
URL_APP="jdbc:postgresql://${PGHOST}:${PGPORT}/${CI_DB}?options=-c%20myapp.log_with_dblink%3Doff"

# ⛔ DIFESA 1 — un defaults-file VUOTO.
#   `db/liquibase.properties` contiene `url=…/zeroerp` e `username=titodb`,
#   cioe' il database di sviluppo. Gli argomenti espliciti hanno la precedenza
#   sul file, ma qui non si vuole dipendere da una regola di precedenza: si
#   toglie di mezzo il file. Con un defaults-file vuoto NESSUN properties puo'
#   iniettare un url, nemmeno se qualcuno ne aggiungesse uno domani nella
#   directory da cui si lancia.
DEFAULTS_VUOTO="$(mktemp)"
trap 'rm -f "$DEFAULTS_VUOTO"' EXIT

# ⛔ DIFESA 2 — il TESTIMONE sul database di sviluppo.
#   Non si dichiara «non lo tocco»: si misura. Si legge lo stato del
#   `databasechangelog` di sviluppo PRIMA e DOPO, e se cambia lo script grida.
#   ⚠️ E' l'unica forma di garanzia che non dipende dal fatto che io abbia
#   letto bene la documentazione di Liquibase.
testimone_dev() {
  PGPASSWORD="${PGPASSWORD:-${DB_PASSWORD:-}}" psql -X -A -t \
    -U "${PGUSER:-${DB_USER:-}}" -d "$DEV_DB" \
    -c "SELECT count(*)||'/'||COALESCE(max(dateexecuted)::text,'-') FROM databasechangelog" 2>/dev/null || echo "?"
}
DEV_PRIMA="$(testimone_dev)"
echo "── testimone su $DEV_DB (prima): $DEV_PRIMA"

LB="$SCRIPT_DIR/liquibase5.sh"
echo "── $("$LB" --version 2>/dev/null | grep -i '^Liquibase Version' || echo 'Liquibase: versione?')"

echo "── provision pre"
"$LB" --defaults-file="$DEFAULTS_VUOTO" --url="$URL_CI" --username="$ADMIN_USER" --password="$ADMIN_PWD" \
  --changeLogFile=db/changelog/changelog-provision-pre.yaml update --contexts=provision

# ⛔ LA FASE PRE VA QUI, DOPO IL PROVISION-PRE — e l'ordine e' tutto.
#   Il provision-pre gira come SUPERUSER e crea `public.databasechangelog`; la
#   passata principale gira come zeroerp_owner, che su una tabella creata da un
#   altro ruolo non ha nessun diritto. Il passaggio di proprieta' fotografa le
#   tabelle CHE ESISTONO: farlo prima non copre una tabella che nascera' dopo.
#   ⚠️ Il sintomo, se lo si mette prima, non parla di permessi in modo
#   riconoscibile: Liquibase muore su una sua query interna di checksum —
#   «Error executing SQL SELECT MD5SUM FROM public.databasechangelog … :
#   permesso negato» — e sembra un problema di MD5.
# ⭐ Niente GRANT di raccordo: cio' che il provision-pre ha creato da superuser
#   (tabelle di Liquibase, `internal`) passa a zeroerp_owner, e `pgagent` riceve
#   i diritti per owner e job. E' la fase pre dello script del modello.
echo "── proprieta' a zeroerp_owner e diritti su pgagent (provision_zeroerp.sql, fase pre)"
psql_admin -d "$CI_DB" -v fase=pre < scripts/sql/provision_zeroerp.sql >/dev/null

# ── ⚠️ pgAgent: qui la fase 85_pgagent GIRA DAVVERO, in CI no ─────────
#   I changeSet di `85_pgagent` sono protetti da `onFail: MARK_RAN` + «esiste
#   l'estensione pgagent»: sull'immagine della CI l'estensione non c'e' e
#   vengono saltati, qui girano. I diritti di zeroerp_owner sullo schema
#   `pgagent` li da' la fase pre (sopra).

echo "── passata principale  (--contexts=\"!provision and !dati_macchina\")"
echo "   ⭐ e' qui che il migrate si ferma: guarda il numero 'Run:' salire"
"$LB" --defaults-file="$DEFAULTS_VUOTO" --url="$URL_APP" --username="$MIGR" --password="$MIGR_PWD" \
  --changeLogFile=db/changelog/changelog-master-v2.yaml update --contexts="!provision and !dati_macchina"

# ⛔ PROVISION *POST*, e mancava. Il passo gemello di ci-validate.yaml
#   («Liquibase admin (provision - post)») gira come SUPERUSER DOPO la passata
#   principale, e non e' un doppione del provision-pre: `changelog-provision-post.yaml`
#   contiene cio' che si puo' fare solo quando lo schema esiste GIA' — fra
#   l'altro `90_end/20251123-12`, che da a `postgres` l'owner di
#   `dbops.fn_sync_functions_owner()` e poi la esegue per allineare le SEI
#   funzioni dichiarate in `dbops.sec_functions_owner`.
#   ⚠️ Quel changeSet dichiara `context: provision`: la passata principale gira
#   con `!provision` e quindi NON lo vede mai. Senza questo passo le sei
#   funzioni restano del migratore, che non e' superuser — e `dblink` rifiuta la
#   connessione a un non-superuser senza password.
#   🔴 Il sintomo, misurato il 2026-09-09: `maintenance/test-job-run-log-failure-out-of-tx.sql`
#   rosso al test 2 («l'owner della funzione e' un superuser») sullo scratch e
#   verde in CI. Non contaminazione: una preparazione mancante.
#   ⛔ E il danno vero non e' il test: e' che il canale fuori transazione TACE
#   (emette un WARNING e tira dritto), quindi un job fallito non lascerebbe
#   traccia — che e' esattamente il difetto per cui quel canale e' nato.
echo "── provision post  (come il passo 'Liquibase admin (provision - post)' di ci-validate.yaml)"
"$LB" --defaults-file="$DEFAULTS_VUOTO" --url="$URL_CI" --username="$ADMIN_USER" --password="$ADMIN_PWD" \
  --changeLogFile=db/changelog/changelog-provision-post.yaml update --contexts=provision

if $CI_APPLY; then
  echo "── automazioni  (--contexts=ci_apply)"
  "$LB" --defaults-file="$DEFAULTS_VUOTO" --url="$URL_CI" --username="$MIGR" --password="$MIGR_PWD" \
    --changeLogFile=db/changelog/changelog-master-v2.yaml update --contexts=ci_apply
fi

# ══════════════════════════════════════════════════════════════════════
# Preparazione al collaudo: cio' che serve ai pgTAP e che il migrate non fa.
# Tutte e tre idempotenti: a regime non stampano niente e non cambiano niente.
# ══════════════════════════════════════════════════════════════════════

# 0. ⛔ IL CANALE DI LOG dblink, SPENTO PER QUESTO DATABASE.
#    Il cluster ha un default `myapp.dblink_log_connection` che punta al
#    database di SVILUPPO come `titodb` e senza password. Su `zeroerp` non si
#    vede, perche' li' un override per-database lo copre con
#    `service=zeroerp_log`; su uno scratch appena creato quel default affiora.
#    ⇒ Ogni funzione che solleva un errore prova a scriverlo via dblink, e come
#    ruolo applicativo muore su «password or GSSAPI delegated credentials
#    required» — un 2F003 al posto del P0001 del dominio.
#    ⚠️ Misurato il 2026-09-09: 151 dei 194 file di `vendite` che fallivano nel
#    fixture riportavano QUEL messaggio invece del proprio. Non un rosso in
#    piu': un rosso che MENTE sulla causa, e che avrebbe mandato il triage a
#    inseguire un fantasma.
#    ⭐ Svuotarlo e' cio' che rende lo scratch simile alla CI, dove quella GUC
#    non e' impostata affatto: `fn_get_or_create_session_tx_id` prende il ramo
#    della sentinella, avvisa e prosegue.
#    ⚠️ zeroerp_owner ha un `ALTER ROLE ... IN DATABASE` suo, impostato piu'
#    sopra, che ha la precedenza: anche lui vuoto, come in CI.
psql_admin -d postgres -c \
  "ALTER DATABASE \"$CI_DB\" SET myapp.dblink_log_connection = '';" >/dev/null

# 1. L'estensione pgtap. In CI la crea il passo della suite; qui nessuno.
if ! psql_admin -d "$CI_DB" -tAc "SELECT 1 FROM pg_extension WHERE extname='pgtap'" | grep -q 1; then
  echo "── installo l'estensione pgtap su $CI_DB"
  psql_admin -d "$CI_DB" -c "CREATE EXTENSION IF NOT EXISTS pgtap;" >/dev/null
fi

# 2. Lo schema django, copiato da $DEV_DB. ⚠️ E' una COPIA, non un migrate: il
#    DDL e' quello che Django ha prodotto la', quindi fedele oggi. Si carica
#    come il migratore cosi' le tabelle le possiede lui — i pgTAP marcati
#    `pgtap-runner: owner` girano con quel ruolo e ci scrivono dentro.
#    ⚠️ `django_migrations` resta vuota: e' dichiarato in intestazione.
#    ⛔ `--no-acl`: il DDL si', i privilegi NO. Su dev quelle tabelle hanno
#    `zeroerp_app=arwd/titodb` dato a mano, e `pg_dump --schema-only` lo
#    emette come GRANT: copiandolo, lo scratch aveva un privilegio che nessuno
#    script concede e che in CI non c'e'. I privilegi li da' il passo 3, che
#    per questo sta DOPO.
if ! psql_admin -d "$CI_DB" -tAc \
       "SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
         WHERE n.nspname='django' AND c.relname='auth_user'" | grep -q 1; then
  if psql_admin -d "$DEV_DB" -tAc \
       "SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
         WHERE n.nspname='django' AND c.relname='auth_user'" | grep -q 1; then
    echo "── copio lo schema django da $DEV_DB (sola lettura di la')"
    # -T token_blacklist: quelle due tabelle su CI_DB le ha gia' create Liquibase.
    # Si toglie `CREATE SCHEMA` (lo schema c'e' gia'). `--no-acl` lascia fuori
    # sia i GRANT sia le ALTER DEFAULT PRIVILEGES di dev: i privilegi arrivano
    # dal provisioning, come in CI.
    sudo -u postgres pg_dump -d "$DEV_DB" --schema-only --no-owner --no-acl \
         -n django -T 'django.token_blacklist_*' \
      | sed -e '/^CREATE SCHEMA django;$/d' \
      | PGPASSWORD="$MIGR_PWD" psql --no-psqlrc -h "$PGHOST" -p "$PGPORT" -U "$MIGR" -d "$CI_DB" \
          -X -q -v ON_ERROR_STOP=1 >/dev/null
    # ⛔ Il dump porta con se' anche gli indici che su dev ha creato LIQUIBASE
    #    sulle tabelle di Django (`ix_*`, 90_end con onFail CONTINUE). In CI non
    #    esistono: Liquibase gira prima di `manage.py migrate`, il changeSet
    #    salta e non si registra. Copiati, lo scratch aveva l'indice SENZA la
    #    riga in databasechangelog, e un pgTAP che sceglie il ramo dal registro
    #    finiva in ERRORE_FIXTURE (2026-09-26, test-credenziale-email-unica-v1:
    #    ix_auth_user_email_lower_unique). Si tolgono: lo scratch torna com'e'
    #    in CI.
    PGPASSWORD="$MIGR_PWD" psql --no-psqlrc -h "$PGHOST" -p "$PGPORT" -U "$MIGR" -d "$CI_DB" \
        -X -q -v ON_ERROR_STOP=1 >/dev/null <<'SQL'
DO $$
DECLARE r record;
BEGIN
    FOR r IN SELECT i.relname FROM pg_class i
               JOIN pg_namespace n ON n.oid = i.relnamespace
              WHERE n.nspname = 'django' AND i.relkind = 'i' AND i.relname LIKE 'ix\_%'
    LOOP
        EXECUTE format('DROP INDEX django.%I', r.relname);
    END LOOP;
END $$;
SQL
  else
    echo "⚠️  django.auth_user non c'e' nemmeno su $DEV_DB: niente da copiare." >&2
    echo "    Lancia 'manage.py migrate' dal server backend puntando a questo host." >&2
  fi
fi

# 3. I privilegi del ruolo applicativo: li da' la fase post (passo 5), che
#    gira DOPO tutto — come in ci-validate.yaml, dove sta dopo `ci_apply` e
#    dopo `manage.py migrate`. ⛔ E si rilancia SEMPRE: `GRANT … ON ALL TABLES
#    IN SCHEMA` e' una FOTOGRAFIA, e le shadow `storico.*` nascono con
#    `ci_apply`, cioe' piu' tardi (successo il 2026-09-09 con un guard «salta se
#    i grant ci sono gia'»: quattro shadow senza SELECT e
#    db/pgtap/dbops/test-audit-sources-seed.sql rosso).
#    Era scripts/sql/provision_db_roles.sql, unificato in provision_zeroerp.sql
#    il 2026-10-15: niente piu' password di zeroerp_app da ~/.pgpass, qui.

# 5. ⭐ Il modello dei ruoli: la postura di zeroerp_app (passo 3), EXECUTE di
#    zeroerp_job sulle procedure dei job, la
#    proprieta' ripassata a zeroerp_owner (cio' che e' nato dopo la fase pre), e
#    la VERIFICA «un owner solo»: se un oggetto del progetto non e' suo — fuori
#    da dbops.sec_functions_owner — lo script si ferma e lo nomina.
#    ⭐ E l'AMBIENTE (dal 2026-10-16, brief-db-processi-accensione-per-ambiente
#    R-2): lo scratch e' SVILUPPO. Si scrive una volta e non cambia; nelle
#    corse dopo la prima il parametro deve solo coincidere.
echo "── ruoli di sistema: fase post — postura di zeroerp_app, zeroerp_job, ambiente SVILUPPO, «un owner solo» (provision_zeroerp.sql)"
psql_admin -d "$CI_DB" -v fase=post -v ambiente=SVILUPPO < scripts/sql/provision_zeroerp.sql

DEV_DOPO="$(testimone_dev)"
echo "── testimone su $DEV_DB (dopo):  $DEV_DOPO"
if [[ "$DEV_PRIMA" != "$DEV_DOPO" ]]; then
  echo "🔴 ALLARME: il databasechangelog di '$DEV_DB' e' CAMBIATO durante la corsa." >&2
  echo "   prima: $DEV_PRIMA" >&2
  echo "   dopo : $DEV_DOPO"  >&2
  echo "   Qualcosa ha scritto sul database di sviluppo: fermarsi e capire." >&2
  exit 2
fi
echo "✅ il database di sviluppo '$DEV_DB' non e' stato toccato (testimone invariato)"

echo "──────────────────────────────────────────────"
echo "✅ passata completata su $CI_DB"
echo "   la prossima esecuzione e' INCREMENTALE: riapplica solo cio' che manca."
echo "   ⚠️ se hai corretto un changeSet GIA' applicato, serve --fresh."
