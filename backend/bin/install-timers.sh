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
# ⭐ E dal 2026-09-11 la TOLLERANZA non sta nemmeno nel JSON: e' il contratto
# del processo e vive in `dbops.processi.tolleranza_minuti` (brief
# `brief-db-quattro-processi-senza-presidio.md` D5). Qui resta la CADENZA, che e'
# come il deploy onora quel contratto — e questo script non la legge nemmeno.
#
# ⭐ SI ACCENDE OGNI SVEGLIA (dal 2026-10-16). Fino ad allora lo decideva il
# campo `abilita` del file, un booleano uguale su ogni host. Se un processo
# lavora e' un fatto del processo e dell'installazione, e sta nel database
# (brief-db-processi-accensione-per-ambiente): il default per ambiente e i
# processi che non si spengono in `dbops.processi`, la scelta a mano in
# `dbops.processi_accensione`. Ogni `.service` porta
# `ExecCondition=… e_dovuto <unit>`, che lo chiede al DB a ogni sveglia: uno
# spento salta senza errore. Le due corsie della fatturazione, per esempio,
# sono installate e accese qui, e saltano finche' il processo e' spento.
# ⛔ `sync-auth-user-active` NON c'e' piu' (2026-09-07): il suo processo di
# catalogo e' ritirato a favore del gemello pgAgent `sync_auth_user_expired_daily`,
# e unit, voce e costante sono spariti INSIEME — vedi `_ritirate` in sveglie.json.
#
# ⭐ DAL 2026-10-05 RITIRA CIO' CHE NON E' PIU' DICHIARATO (decisione di Tid). Una
# sveglia installata sull'host (un unit il cui `ExecStart` lancia
# `run-command.sh` di questo checkout) e assente da `sveglie.json` si spegne e
# si toglie: e' lo specchio sull'host di
# `test_nessun_template_orfano`. ⛔ Solo le sveglie: `zeroerp-gunicorn` e gli
# altri unit del play-book non si toccano (il difetto del primo giro, sotto). Prima
# l'installer solo aggiungeva, e il rinomino `listen-cambio-reparto` →
# `listen-permessi` avrebbe lasciato DUE listener accesi, uno dei quali muto
# per il panorama (si presenta con un codice ritirato).
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
# (__APP_DIR__, __APP_USER__, __ONCALENDAR__) e, dal 2026-09-14, __COMANDO__ —
# l'argv dopo run-command.sh, che sta in `sveglie.json` (campo `comando`) e non
# più cablato nell'ExecStart del template: è la stessa riga che «Esegui ora»
# lancia dall'interfaccia, e una sede sola non può divergere. Modifiche agli
# unit → si editano i template; modifiche alla cadenza, al comando o a cosa si
# accende → `sveglie.json`.
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
# L'env file è un segreto runtime per-host: è nel .gitignore, e in un checkout
# non c'è MAI.
#
# ⭐ IL REQUISITO È DELLA DESTINAZIONE, non della modalità — è la stessa
#    correzione già fatta sopra per il root, e per la stessa ragione: l'env file
#    serve perché quegli unit gireranno DAVVERO su questa macchina. Se la
#    destinazione è altrove, non serve.
# 🔴 Legato alla modalità era una coincidenza che ha smesso di reggere il giorno
#    in cui le corse sono diventate tre invece di due. `--render-only` non lo
#    chiedeva; l'installazione vera sì; e la prova del ramo CHE ACCENDE — che
#    non è né l'una né l'altra, perché deve attraversare `systemctl` scrivendo
#    in una cartella temporanea — ci cadeva dentro. In CI il test moriva al
#    primo passo, in zero secondi.
# ⚠️ E il file non viene nemmeno LETTO: l'unit lo cita come percorso
#    (`EnvironmentFile=`), questo è solo un controllo di pre-volo.
if [ "$DEST_DIR" = "$DEST_DIR_REALE" ]; then
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
# (unit, forma, comando, oncalendar). Solo stdlib: gira anche su
# un host senza venv e sul runner della CI.
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

# ⛔ Niente `nota` (dal 2026-10-16): serviva a dire PERCHE' uno spento restava
#    spento, e l'installer non sa piu' chi e' spento (lo dice il DB). Un campo
#    estratto e mai letto e' una colonna in piu' da far slittare.
for s in righe:
    # Il comando è una LISTA di token; qui diventa la riga dell'`ExecStart`,
    # cioè i token separati da spazio. È un join sicuro perché i token non
    # possono contenere spazi né metacaratteri: lo impone `carica_sveglie`
    # (`_ARGOMENTO_AMMESSO`), che la CI prova su questo stesso file. Non si
    # ri-valida qui, per la stessa ragione scritta sopra.
    comando = " ".join(str(x) for x in (s.get("comando") or []))
    print(sep.join([
        str(s.get("unit") or ""),
        str(s.get("forma") or ""),
        comando,
        str(s.get("oncalendar") or ""),
    ]))
PY
}

# Scopo: renderizza i template di una sveglia (sempre il .service; il .timer solo
# se è un timer) sostituendo i placeholder per-host, e li scrive in $DEST_DIR.
render_unit() {
  local name="$1" forma="$2" comando="$3" oncalendar="$4" kind tpl
  local kinds=("service")
  # ⛔ Un `.service` senza comando è un unit con `ExecStart=… run-command.sh `
  #    e basta: systemd lo rifiuta, e lo scoprirebbe l'host. Il campo serve
  #    QUI, alla sostituzione — stesso criterio della cadenza qui sotto.
  [ -n "$comando" ] || { echo "$name: voce senza 'comando' in $SVEGLIE" >&2; exit 1; }
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
        -e "s|__COMANDO__|${comando}|g" \
        "$tpl" > "${DEST_DIR}/${name}.${kind}"
  done
  if [ "$forma" = "timer" ]; then
    echo "  scritto ${name}.service + ${name}.timer (OnCalendar=${oncalendar}; comando: ${comando})"
  else
    echo "  scritto ${name}.service (servizio sempre acceso, nessun timer; comando: ${comando})"
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
# I FILE che il dichiarato produce (`.service`, più il `.timer` dei timer): è
# l'insieme contro cui si cercano gli orfani sull'host, qui sotto.
DICHIARATI=" "
while IFS="$SEP" read -r unit forma comando oncalendar; do
  [ -n "$unit" ] || continue
  render_unit "$unit" "$forma" "$comando" "$oncalendar"
  DICHIARATI+="${unit}.service "
  [ "$forma" = "timer" ] && DICHIARATI+="${unit}.timer "
  # Si abilita il .timer dove c'è, il .service dove la sveglia è un servizio.
  if [ "$forma" = "timer" ]; then target="${unit}.timer"; else target="${unit}.service"; fi
  # Ogni sveglia si accende: se lavora lo decide l'`ExecCondition` col DB.
  DA_ACCENDERE+=("$target")
done <<< "$SVEGLIE_RIGHE"

# Scopo: dice se un `.service` installato è una SVEGLIA di questo checkout: il
# suo `ExecStart` COMINCIA col wrapper delle sveglie (`$WRAPPER`), che è la
# firma che ogni template porta (test 6 di `test-install-timers.sh`).
# ⛔ Si legge la sola riga `ExecStart=`, dall'inizio: cercare il testo in tutto
#    il file prenderebbe per sveglia un unit estraneo che CITA il wrapper in un
#    commento — e lo ritirerebbe.
e_una_sveglia() {
  awk -v firma="ExecStart=${WRAPPER} " \
    'index($0, firma) == 1 { trovata = 1 } END { exit !trovata }' "$1"
}

# Scopo: le SVEGLIE installate in $DEST_DIR che il dichiarato non produce più.
# Si spengono e si tolgono (vedi header).
#
# 🔴 IL PREFISSO NON BASTA, ed è un difetto vero del 2026-10-05: la prima
#    versione ritirava ogni `zeroerp-*` non dichiarato, e al primo giro sul
#    dbdev ha spento e cancellato `zeroerp-gunicorn.service` — il backend, che
#    è `zeroerp-` ma non è una sveglia (lo installa il play-book §8, non
#    questo script). ⇒ DECIDE LA FIRMA (`e_una_sveglia`), non il nome: si
#    guardano tutti i `.service` della destinazione, perché nessuna regola
#    obbliga una sveglia a chiamarsi `zeroerp-*`.
# ⭐ Un `.timer` non dichiarato si ritira se il suo `.service` omonimo è una
#    sveglia, DICHIARATA o no: copre anche la sveglia passata da `timer` a
#    `servizio`, il cui `.service` resta dichiarato e il cui `.timer` vecchio
#    continuerebbe a rilanciarlo. Un timer senza `.service` sveglia è estraneo.
# ⭐ I `.timer` PRIMA dei `.service`: spegnere prima il servizio lascerebbe al
#    timer ancora acceso l'occasione di rilanciarlo.
# ℹ️ ESTRANEI: i soli `zeroerp-*` non dichiarati e senza firma. È un'etichetta
#    del piano, per chi legge, non un criterio: non decide niente.
dichiarato() { case "$DICHIARATI" in *" $1 "*) return 0 ;; esac; return 1; }
RIT_TIMER=()
RIT_SERVICE=()
ESTRANEI=()
for f in "$DEST_DIR"/*.service; do
  [ -f "$f" ] || continue   # glob senza corrispondenze: resta il letterale
  nome="$(basename "$f")"
  dichiarato "$nome" && continue
  if e_una_sveglia "$f"; then
    RIT_SERVICE+=("$nome")
  else
    case "$nome" in zeroerp-*) ESTRANEI+=("$nome") ;; esac
  fi
done
for f in "$DEST_DIR"/*.timer; do
  [ -f "$f" ] || continue
  nome="$(basename "$f")"
  dichiarato "$nome" && continue
  servizio="${DEST_DIR}/${nome%.timer}.service"
  if [ -f "$servizio" ] && e_una_sveglia "$servizio"; then
    RIT_TIMER+=("$nome")
  else
    case "$nome" in zeroerp-*) ESTRANEI+=("$nome") ;; esac
  fi
done
DA_RITIRARE=(${RIT_TIMER[@]+"${RIT_TIMER[@]}"} ${RIT_SERVICE[@]+"${RIT_SERVICE[@]}"})

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
for u in ${DA_RITIRARE[@]+"${DA_RITIRARE[@]}"}; do
  echo "  RITIRA   $u (installato, non più dichiarato)"
done
for u in ${ESTRANEI[@]+"${ESTRANEI[@]}"}; do
  echo "  ESTRANEO $u (non lancia $(basename "$WRAPPER"): non è una sveglia, non si tocca)"
done

# In render-only (CI) ci si ferma qui: niente daemon-reload né enable.
if [ "$RENDER_ONLY" -eq 1 ]; then
  echo "OK render-only: unit in $DEST_DIR"
  exit 0
fi

# Il ritiro viene PRIMA del daemon-reload: `disable --now` vuole il file ancora
# presente, e il reload dopo la cancellazione fa dimenticare l'unit a systemd.
# ⛔ Niente `|| true` sul `disable`: se lo spegnimento fallisce ci si ferma. Il
#    file cancellato con il processo ancora vivo nasconderebbe il guasto
#    peggiore, un processo acceso che nessun file descrive più.
if [ ${#DA_RITIRARE[@]} -gt 0 ]; then
  for u in "${DA_RITIRARE[@]}"; do
    systemctl disable --now "$u"
    rm -f "${DEST_DIR}/${u}"
  done
  echo
  echo "OK, ritirati: ${DA_RITIRARE[*]}"
fi

systemctl daemon-reload

# Si accende ogni sveglia dichiarata. Un host nuovo parte con lo stesso
# assetto di quello in esercizio; quali processi lavorano lo dice il DB.
if [ ${#DA_ACCENDERE[@]} -gt 0 ]; then
  for u in "${DA_ACCENDERE[@]}"; do
    systemctl enable --now "$u"
  done
  echo
  echo "OK, abilitati: ${DA_ACCENDERE[*]}"
fi

# ⭐ Chi è spento non si stampa qui: non lo sa l'installer. Lo dice il drawer
#    dei processi (stato effettivo e da dove viene) e il panorama (`SPENTO`).
echo
systemctl list-timers 'zeroerp-*' --all --no-pager || true
