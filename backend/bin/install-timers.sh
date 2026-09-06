#!/usr/bin/env bash
# Installa gli unit systemd dei processi headless svegliati dal backend.
#
# ⭐ CHE COSA INSTALLA NON STA PIU' QUI. L'elenco, la cadenza e cosa accendere
# si leggono da `backend/deploy/sveglie.json`, che dal 2026-09-06 e' la SEDE
# UNICA del dichiarato di deploy. Questo script lo rende; il backend lo legge
# con `apps.core.services.sveglie`. Due programmi, un file.
#
# ⛔ PERCHE' E' CAMBIATO. Fino al 2026-09-06 le cadenze erano cablate qui sotto
# in quattro chiamate `render_unit`, e la tolleranza di liveness degli stessi
# processi era un `WORKER_ATTIVO_SOGLIA_MINUTI = 10` in Python. Lo stesso fatto
# — «ogni quanto ci si aspetta questo processo» — scritto in due posti che non
# si conoscevano. Due scritture dissentono, e quella divergenza sarebbe stata
# muta: un pallino verde su un worker fermo.
#
# ⚠️ CHI ACCENDE E CHI NO lo dice il campo `abilita` del file, con la ragione
# scritta nella `nota` accanto. Le due corsie della fatturazione restano spente
# (emettono documenti — decisione di Tid, 2026-08-16) e cosi'
# `sync-auth-user-active` (ha un gemello pgAgent che fa lo stesso lavoro). I
# drainer e il listener si accendono: a coda vuota non fanno niente.
#
# Idempotente: riscrive gli unit a ogni run. Da eseguire come root:
#   sudo backend/bin/install-timers.sh
#
# Modalità validazione (usata dalla CI, niente root/systemctl): renderizza i
# template in una cartella e basta, per darli in pasto a `systemd-analyze verify`:
#   backend/bin/install-timers.sh --render-only <DIR>
#
# Convenzione: mirror di play-book-operativo-backend.md §15/§16/§17. Gli unit
# usano il wrapper bin/run-command.sh (env.sh) + EnvironmentFile=.env.systemd
# (segreti, incl. DB_SYSTEM_FATTURAZIONE_* per i job di sistema / la coda stampa).
#
# Fonte di verità UNICA degli unit: i template versionati in
# backend/deploy/systemd/*.service|*.timer (reviewabili in PR). Questo script NON
# li genera con heredoc inline: li renderizza sostituendo i placeholder per-host
# (__APP_DIR__, __APP_USER__, __ONCALENDAR__). Modifiche agli unit → si editano
# i template; modifiche alla cadenza o a cosa si accende → `sveglie.json`.
set -euo pipefail

# Modalità: install (default, scrive in /etc/systemd/system e abilita) oppure
# render-only (solo rendering in DIR, per la validazione CI).
#
# ⭐ `ZEROERP_SYSTEMD_DIR` sposta la DESTINAZIONE senza cambiare una riga di
#    logica: serve a `scripts/tests/test-install-timers.sh`, che con un
#    `systemctl` finto in testa al PATH esercita il ramo che ACCENDE — quello
#    dove viveva il difetto del 2026-09-06 e dove `--render-only` non arriva.
# ⛔ Non è una modalità di prova, ed è la differenza che conta: un `--dry-run`
#    che salta `systemctl` proverebbe il ramo che NON accende, cioè proprio
#    quello che non interessa. Qui le righe eseguite sono le stesse della
#    produzione; cambia solo dove atterrano e chi è `systemctl`.
RENDER_ONLY=0
DEST_DIR_REALE="/etc/systemd/system"
DEST_DIR="${ZEROERP_SYSTEMD_DIR:-$DEST_DIR_REALE}"
if [ "${1:-}" = "--render-only" ]; then
  RENDER_ONLY=1
  DEST_DIR="${2:?--render-only richiede una directory di output}"
fi
[ "$DEST_DIR" = "$DEST_DIR_REALE" ] || mkdir -p "$DEST_DIR"

# ⭐ IL ROOT SERVE A SCRIVERE NELLA SEDE REALE, non perché «siamo in modalità
#    install»: vincolarlo alla DESTINAZIONE dice il vero, legarlo alla modalità
#    era una coincidenza che reggeva finché le destinazioni erano due.
if [ "$DEST_DIR" = "$DEST_DIR_REALE" ] && [ "$(id -u)" -ne 0 ]; then
  echo "Esegui come root: sudo $0" >&2
  exit 1
fi

# APP_DIR = la cartella backend (questo script vive in backend/bin/).
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
# APP_USER = proprietario della cartella app (portabile fra host).
APP_USER="$(stat -c '%U' "$APP_DIR")"
WRAPPER="${APP_DIR}/bin/run-command.sh"
ENV_FILE="${APP_DIR}/.env.systemd"
TEMPLATE_DIR="${APP_DIR}/deploy/systemd"
SVEGLIE="${APP_DIR}/deploy/sveglie.json"

# Sanity: il wrapper (target degli ExecStart), i template e il dichiarato devono
# esistere. ⛔ Fail-loud: un dichiarato mancante installerebbe ZERO unit senza
# dirlo, ed e' il guasto-per-assenza che questo cantiere esiste per togliere.
[ -x "$WRAPPER" ] || { echo "Manca il wrapper eseguibile: $WRAPPER" >&2; exit 1; }
[ -d "$TEMPLATE_DIR" ] || { echo "Manca la cartella template: $TEMPLATE_DIR" >&2; exit 1; }
[ -f "$SVEGLIE" ] || { echo "Manca il dichiarato di deploy: $SVEGLIE" >&2; exit 1; }
command -v python3 >/dev/null || { echo "Serve python3 per leggere $SVEGLIE" >&2; exit 1; }
# L'env file è un segreto runtime per-host: richiesto solo per l'installazione
# reale, non per la validazione (la CI non ce l'ha e non ne ha bisogno).
if [ "$RENDER_ONLY" -eq 0 ]; then
  [ -f "$ENV_FILE" ] || { echo "Manca l'env file: $ENV_FILE" >&2; exit 1; }
fi

echo "APP_DIR=$APP_DIR  APP_USER=$APP_USER  DEST=$DEST_DIR  render_only=$RENDER_ONLY"

# Separatore di campo dell'estrattore: US (`\x1f`, "unit separator").
# 🔴 NON UN TAB, e la ragione è un difetto vero trovato il 2026-09-06. `read`
# tratta il TAB come **IFS-whitespace**, quindi collassa i delimitatori
# consecutivi: un campo VUOTO sparisce e tutti quelli dopo slittano di uno. Con
# `oncalendar` vuoto — che è il caso normale dei servizi sempre accesi —
# `zeroerp-listen-cambio-reparto` leggeva `abilita` = il testo della nota,
# finiva fra gli spenti e **non veniva acceso**. Un carattere non-whitespace nel
# valore di `IFS` non si collassa, e i campi vuoti sopravvivono.
# ⛔ E la CI non poteva vederlo: `--render-only` esce prima del ramo che
#    accende. Il difetto viveva esattamente dove la prova non arrivava.
SEP=$'\x1f'

# Scopo: ESTRAE da `sveglie.json` una riga per sveglia
# (unit, forma, oncalendar, abilita, nota). Solo stdlib: gira anche su un host
# senza venv e sul runner della CI.
#
# ⛔ NON VALIDA IL DICHIARATO, ed è una scelta corretta il 2026-09-06 dopo averlo
#    scritto sbagliato: la prima versione ri-scriveva qui le CINQUE regole di
#    forma che stanno già in `apps.core.services.sveglie`, con la scusa che «i
#    due lettori devono poter fallire da soli». Era la scusa classica: due copie
#    di una regola sono due regole, e divergono. Le regole hanno una sede sola,
#    presidiata in CI da `test_sveglie.py`.
# ⇒ Qui restano solo i controlli che servono a QUESTO programma nel punto in cui
#    gli servono — dentro `render_unit`, che senza una risposta non saprebbe
#    cosa scrivere. Non è la regola: è il ramo che la usa.
leggi_sveglie() {
  python3 - "$SVEGLIE" "$SEP" <<'PY'
import json, sys

sep = sys.argv[2]
with open(sys.argv[1], encoding="utf-8") as fh:
    dati = json.load(fh)

righe = dati.get("sveglie")
if not isinstance(righe, list) or not righe:
    sys.exit("sveglie.json: la chiave 'sveglie' manca o e' vuota")

for s in righe:
    # Una nota che contenesse il separatore, o un a capo, spezzerebbe la riga e
    # sposterebbe i campi: si normalizza a spazi prima di comporla.
    nota = " ".join(str(s.get("nota") or "").replace(sep, " ").split())
    print(sep.join([
        str(s.get("unit") or ""),
        str(s.get("forma") or ""),
        str(s.get("oncalendar") or ""),
        "1" if s.get("abilita") is True else "0",
        nota,
    ]))
PY
}

# Scopo: renderizza i template di una sveglia (sempre il .service; il .timer solo
# se è un timer) sostituendo i placeholder per-host, e li scrive in $DEST_DIR.
render_unit() {
  local name="$1" forma="$2" oncalendar="$3" kind tpl
  local kinds=("service")
  # ⛔ RAMO ESAUSTIVO, con l'`else` che si ferma. Non è la whitelist delle forme
  #    riscritta qui: è che questo programma DEVE sapere cosa scrivere, e su una
  #    forma che non conosce l'alternativa sarebbe renderizzare il solo
  #    `.service` e poi accenderlo — cioè trattare un timer come un servizio
  #    sempre acceso, in silenzio.
  case "$forma" in
    timer)
      # ⛔ Un timer senza cadenza produce un unit che systemd rifiuta, e lo
      #    scoprirebbe l'host. Il campo serve QUI, alla sostituzione.
      [ -n "$oncalendar" ] || { echo "$name: timer senza cadenza in $SVEGLIE" >&2; exit 1; }
      kinds+=("timer")
      ;;
    # ⭐ Un servizio sempre acceso NON ha un .timer, e pretenderlo farebbe
    #    fallire l'installazione di un unit perfettamente valido.
    servizio) ;;
    *) echo "$name: forma '$forma' sconosciuta in $SVEGLIE" >&2; exit 1 ;;
  esac
  for kind in "${kinds[@]}"; do
    tpl="${TEMPLATE_DIR}/${name}.${kind}"
    [ -f "$tpl" ] || { echo "Manca il template: $tpl" >&2; exit 1; }
    # '|' come delimitatore sed: APP_DIR è un path con '/'.
    sed -e "s|__APP_DIR__|${APP_DIR}|g" \
        -e "s|__APP_USER__|${APP_USER}|g" \
        -e "s|__ONCALENDAR__|${oncalendar}|g" \
        "$tpl" > "${DEST_DIR}/${name}.${kind}"
  done
  if [ "$forma" = "timer" ]; then
    echo "  scritto ${name}.service + ${name}.timer (OnCalendar=${oncalendar})"
  else
    echo "  scritto ${name}.service (servizio sempre acceso, nessun timer)"
  fi
}

echo "Rendering unit dal dichiarato ($SVEGLIE)..."
# ⛔ SI LEGGE IN UNA VARIABILE, NON IN UNA PROCESS SUBSTITUTION, ed è il punto.
#    Con `done < <(leggi_sveglie)` il codice d'uscita del lettore si PERDE: un
#    `sveglie.json` malformato darebbe zero righe e lo script proseguirebbe
#    installando NIENTE, con successo. Nell'assegnazione invece `set -e` ferma
#    tutto — ed è la stessa regola che questo cantiere applica al resto:
#    un guasto non si manifesta come assenza.
SVEGLIE_RIGHE="$(leggi_sveglie)"
[ -n "$SVEGLIE_RIGHE" ] || { echo "Nessuna sveglia dichiarata in $SVEGLIE" >&2; exit 1; }

DA_ACCENDERE=()
DA_LASCIARE_SPENTI=()
while IFS="$SEP" read -r unit forma oncalendar abilita nota; do
  [ -n "$unit" ] || continue
  render_unit "$unit" "$forma" "$oncalendar"
  # Si abilita il .timer dove c'è, il .service dove il processo è sempre acceso.
  if [ "$forma" = "timer" ]; then target="${unit}.timer"; else target="${unit}.service"; fi
  if [ "$abilita" = "1" ]; then
    DA_ACCENDERE+=("$target")
  else
    # La ragione dello spento viaggia CON l'unit: vedi il blocco finale.
    DA_LASCIARE_SPENTI+=("${target}${SEP}${nota}")
  fi
done <<< "$SVEGLIE_RIGHE"

# ⭐ IL PIANO SI STAMPA IN ENTRAMBE LE MODALITA', e non è cosmesi.
# 🔴 Il difetto del 2026-09-06 — `listen-cambio-reparto` classificato «spento»
#    per uno slittamento di campi — viveva **solo** nel ramo che accende, cioè
#    esattamente dove `--render-only` non arrivava: la CI renderizzava sette
#    unit corretti e non poteva vedere che uno sarebbe stato installato e non
#    acceso. ⇒ La classificazione si dichiara PRIMA di separarsi, così la stessa
#    corsa che la CI già fa la mostra, e `--render-only` diventa una prova del
#    piano oltre che dei file.
echo
echo "Piano (dal dichiarato):"
for u in ${DA_ACCENDERE[@]+"${DA_ACCENDERE[@]}"}; do
  echo "  ACCENDI  $u"
done
for riga in ${DA_LASCIARE_SPENTI[@]+"${DA_LASCIARE_SPENTI[@]}"}; do
  IFS="$SEP" read -r u _nota <<< "$riga"
  echo "  SPENTO   $u"
done

# In render-only (CI) ci si ferma qui: niente daemon-reload né enable.
if [ "$RENDER_ONLY" -eq 1 ]; then
  echo "OK render-only: unit in $DEST_DIR"
  exit 0
fi

systemctl daemon-reload

# Si accende ciò che il dichiarato marca `abilita: true`. Un host nuovo deve
# partire con lo stesso assetto di quello in esercizio, non con metà worker da
# accendere a mano.
if [ ${#DA_ACCENDERE[@]} -gt 0 ]; then
  for u in "${DA_ACCENDERE[@]}"; do
    systemctl enable --now "$u"
  done
  echo
  echo "OK, abilitati: ${DA_ACCENDERE[*]}"
fi

# ⛔ Ciò che resta spento si DICE, con la SUA ragione accanto.
# ⚠️ Fino al 2026-09-06 qui c'era una riga fissa sul prerequisito
#    `DB_SYSTEM_FATTURAZIONE_*`, stampata per OGNI unit spento — anche per
#    `sync-auth-user-active`, che con la fatturazione non c'entra niente. Un
#    messaggio operativo che vale per un caso e viene mostrato per tutti manda a
#    cercare la cosa sbagliata. ⇒ Ogni spento porta la propria `nota`, che è già
#    scritta una volta sola in `sveglie.json`.
if [ ${#DA_LASCIARE_SPENTI[@]} -gt 0 ]; then
  echo
  echo "Installati ma NON attivi:"
  for riga in "${DA_LASCIARE_SPENTI[@]}"; do
    IFS="$SEP" read -r u nota <<< "$riga"
    echo "  systemctl enable --now $u"
    [ -n "$nota" ] && echo "      ↳ $nota"
  done
fi
echo
systemctl list-timers 'zeroerp-*' --all --no-pager || true
