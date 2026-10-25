#!/usr/bin/env bash
# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
#
# Scopo: distinguere in un secondo un pgTAP rosso NUOVO da uno gia' noto.
#
# IL PROBLEMA CHE RISOLVE. La suite pgTAP ha un blocco di rossi preesistenti
# (fixture rimaste indietro rispetto a guard entrati dopo). Chi esegue una
# batteria di regressione dopo una modifica vede quei rossi e, ogni volta, deve
# ri-verificare a mano se c'entrano con il proprio lavoro. E' successo piu'
# volte, e ogni verifica costa piu' del lavoro stesso.
#
# Peggio: una suite con molti rossi noti insegna a ignorare il rosso — che e'
# esattamente cio' che i test dovrebbero impedire.
#
# COME FUNZIONA. Un file di baseline committato elenca i rossi NOTI. Lo script
# riesegue la suite e confronta:
#   - un rosso presente in baseline  -> atteso, silenzio
#   - un rosso NON in baseline       -> REGRESSIONE, exit 1
#   - un file in baseline ora verde  -> RIENTRATO, va tolto dalla baseline
#
# ⚠️ La baseline NON e' una lista di eccezioni permanenti: e' un registro di
# debito, e deve calare. Ogni riga e' un file la cui copertura oggi vale ZERO
# (se fallisce nel fixture non esegue nessuna asserzione), non "parziale".
#
# ⚠️ E VALE SOLO SE E' STATA REGISTRATA COL MEDESIMO UTENTE. Un rosso puo'
# dipendere dal ruolo di connessione (permessi, RLS): confrontare una corsa da
# utente applicativo con una baseline presa da owner produce decine di finte
# regressioni. E' il difetto che ha originato il brief
# `brief-db-pgtap-runner-rls-baseline.md`. Da qui la prima riga del file di
# baseline, `# pgtap-runner: <owner|app>`, e il rifiuto di confrontare corse
# disomogenee.
#
# USO
#   scripts/pgtap-baseline.sh                  # confronta tutta la suite
#   scripts/pgtap-baseline.sh vendite config   # solo alcuni schemi (piu' veloce)
#   scripts/pgtap-baseline.sh --update         # rigenera la baseline
#   scripts/pgtap-baseline.sh --update vendite # rigenera solo quegli schemi
#   scripts/pgtap-baseline.sh --modificati     # solo i pgTAP toccati nell'albero
#   scripts/pgtap-baseline.sh --update --modificati   # rigenera solo le loro righe
#
#   --modificati prende i file `.sql` sotto db/pgtap/ che git vede cambiati
#   rispetto a HEAD (in staged o no) piu' quelli nuovi non ancora aggiunti; i
#   cancellati restano fuori. Il confronto guarda solo le righe di baseline di
#   quei file. Non si combina con gli schemi.
#   ⚠️ Dice se i TEST toccati sono verdi, non se il CODICE toccato ha rotto
#   altro: dopo un cambio a una funzione o a un trigger il perimetro giusto
#   resta lo schema (o la suite), perche' i test che la esercitano non sono
#   fra i file modificati.
#   ⚠️ Prende ogni `.sql` della suite, non solo i `test*.sql`: la suite esegue
#   anche i file di fixture (`create-*.sql`), e un perimetro piu' stretto
#   lascerebbe fuori proprio quelli.
#
#   PGTAP_RUNNER=app scripts/pgtap-baseline.sh vendite   # come gira l'applicazione
#
# ── TRE BASELINE, PERCHE' I METRI SONO TRE ────────────────────────────
#     db/pgtap/baseline-rossi.tsv          <- dbdev, dati veri (default)
#     db/pgtap/baseline-rossi-scratch.tsv  <- il database di scripts/ci-local.sh
#     db/pgtap/baseline-rossi-ci.tsv       <- la CI. LA SCRIVE LA CI.
#
#   Sullo scratch si lavora cosi', e servono DUE variabili:
#
#     PGTAP_ENV_FILE=db/internal.ruoli.env \
#     PGTAP_BASELINE=db/pgtap/baseline-rossi-scratch.tsv \
#       scripts/pgtap-baseline.sh --update
#
#   ⛔ E LO SCRATCH NON E' LA CI, per quanto ci somigli. Il 2026-09-09 la
#   baseline della CI e' stata riempita con una corsa sullo scratch, ed era
#   sbagliato: li' lo schema `django` e' una COPIA e non un migrate, il canale
#   di log dblink e' spento a mano, i privilegi arrivano da un provisioning
#   rilanciato a parte. Tre differenze note piu' quelle che non sappiamo.
#   ⇒ Un confronto CI contro un metro preso qui produce finte regressioni, che
#   e' lo stesso difetto — metro disomogeneo — per cui esistono piu' baseline.
#   ⭐ `baseline-rossi-ci.tsv` si prende dal LOG di una corsa vera: il passo
#   della suite, quando quel file non esiste, la genera e la stampa fra due
#   marcatori `----- 8< -----`. Si copia da li' e si committa.
#
#   ⛔ `PGDATABASE=zeroerp_ruoli` NON basta e non avvisa: l'env file viene
#   caricato con `set -a; source` e sovrascrive l'ambiente, quindi la corsa
#   finirebbe su SVILUPPO e i suoi rossi verrebbero scritti nella baseline
#   della CI. Si sceglie il FILE, non la variabile — vedi testpgtap.sh.
#   ⚠️ E il database scratch va preparato come la CI, o il metro non e' lo
#   stesso: `scripts/ci-local.sh --ci-apply` (senza `--ci-apply` mancano i
#   trigger di audit/tx_id/storico). Lo scratch e' `zeroerp_ruoli` (env file
#   db/internal.ruoli.env, owner zeroerp_owner); lo scratch classico
#   `zeroerp_ci` (--classico) e' stato ritirato il 2026-10-15.
#   ⭐ Dal 2026-09-09 la PRIMA delle due non e' piu' solo questa riga di prosa:
#   e' un cancello che ferma la corsa PRIMA di eseguirla (exit 2). La seconda
#   resta prosa — un ruolo senza diritti si riconosce dal primo rosso, una
#   passata di automazioni mancante no: da' rossi plausibili sui soli test che
#   asseriscono sui trigger generati, cioe' finte regressioni sparse.
#
# La scelta dell'utente sta in scripts/testpgtap.sh (variabile PGTAP_RUNNER e
# marcatore `-- pgtap-runner: owner` per i file che richiedono l'owner).
#
# EXIT CODE
#   0 = nessuna regressione (eventuali rientri sono solo segnalati)
#   1 = almeno un rosso nuovo
#   2 = la corsa NON e' partita. Tre cause, tutte di METRO:
#         · runner diverso da quello registrato in baseline;
#         · automazioni (`ci_apply`) non applicate su questo database;
#         · `--update` su `baseline-rossi-ci.tsv` fuori dalla CI — la scrive la
#           CI, e la valvola dichiarata e' PGTAP_BASELINE_CI_FORZA=1.
#       (piu' il perimetro inesistente, che non e' di metro).
#       ⭐ Si esce PRIMA di eseguire: scoprirlo dopo costerebbe i sette minuti
#       della suite e consegnerebbe finte regressioni.
#
# Tempo: ~1s per file. La suite intera (~400 file) richiede circa 7 minuti;
# restringere agli schemi toccati e' quasi sempre sufficiente.
# ------------------------------------------------------------

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
# ⚠️ Piu' baseline, e non e' un capriccio: sono POPOLAZIONI diverse. Quella di
#   default e' misurata sul DB di SVILUPPO, che ha dati veri; lo scratch e la CI
#   ricostruiscono il database da zero, quindi i test che dipendono da dati
#   preesistenti falliscono la' e non qui. Confrontarne una con l'altra produce
#   decine di finte regressioni — metro disomogeneo, lo stesso difetto che ha
#   originato questo brief. L'elenco delle tre e' in intestazione.
#   Si sceglie con PGTAP_BASELINE.
BASELINE="${PGTAP_BASELINE:-$ROOT_DIR/db/pgtap/baseline-rossi.tsv}"

UPDATE=0
MODIFICATI=0
SCHEMI=()
for arg in "$@"; do
  case "$arg" in
    --update) UPDATE=1 ;;
    --modificati) MODIFICATI=1 ;;
    # ⚠️ L'ultima riga si CALCOLA. Inchiodata a 81 l'aiuto troncava in silenzio
    #   la coda dell'intestazione ogni volta che qualcuno la allungava — e
    #   l'intestazione e' cresciuta due volte oggi. Stessa correzione fatta in
    #   scripts/ci-local.sh, per lo stesso motivo.
    -h|--help) sed -n "2,$(($(grep -n '^set -uo pipefail' "${BASH_SOURCE[0]}" | head -1 | cut -d: -f1) - 1))p" "${BASH_SOURCE[0]}" | sed 's/^# \?//'; exit 0 ;;
    -*) echo "Opzione sconosciuta: $arg" >&2; exit 2 ;;
    *) SCHEMI+=("$arg") ;;
  esac
done

if [ "$MODIFICATI" -eq 1 ] && [ ${#SCHEMI[@]} -gt 0 ]; then
  echo "--modificati non si combina con gli schemi: scegli un perimetro solo." >&2; exit 2
fi

# Perimetro intero = ne' schemi ne' --modificati. Solo una corsa intera puo'
# ribaselinare con un runner nuovo e far scattare il cancello «rossi tutti».
perimetro_intero() { [ ${#SCHEMI[@]} -eq 0 ] && [ "$MODIFICATI" -eq 0 ]; }

# Perimetro: tutta la suite, gli schemi richiesti, o i file modificati.
if [ "$MODIFICATI" -eq 1 ]; then
  # Cambiati rispetto a HEAD (staged e non) + nuovi non tracciati, solo quelli
  # che esistono ancora: un file cancellato non si esegue.
  FILES=$(
    { git -C "$ROOT_DIR" diff --name-only HEAD -- db/pgtap
      git -C "$ROOT_DIR" ls-files --others --exclude-standard -- db/pgtap
    } | grep -E '^db/pgtap/[^/]+/.+\.sql$' | sort -u |
    while IFS= read -r p; do [ -f "$ROOT_DIR/$p" ] && echo "$ROOT_DIR/$p"; done
  )
  if [ -z "$FILES" ]; then
    echo "Nessun pgTAP modificato nell'albero (db/pgtap/, rispetto a HEAD): niente da misurare." >&2
    exit 2
  fi
elif perimetro_intero; then
  # ⚠️ `find` e non `ls .../*/*.sql`: il glob a un livello solo lasciava fuori
  #   dalla baseline le sottocartelle di schema — al 2026-08-24 erano 16 file
  #   (vendite/offerte_commerciali, vendite/contratti), di cui 12 ROSSI da
  #   settimane senza che nessuno li vedesse. Un presidio che non guarda in un
  #   ramo non dice «tutto a posto»: dice «non ho guardato».
  FILES=$(find "$ROOT_DIR/db/pgtap" -mindepth 2 -name '*.sql' 2>/dev/null | sort)
else
  FILES=""
  for sc in "${SCHEMI[@]}"; do
    if [ ! -d "$ROOT_DIR/db/pgtap/$sc" ]; then
      echo "Schema inesistente: $sc (cerca in db/pgtap/)" >&2; exit 2
    fi
    # Idem per lo schema singolo: si scende anche nelle sottocartelle.
    FILES="$FILES"$'\n'"$(find "$ROOT_DIR/db/pgtap/$sc" -name '*.sql' 2>/dev/null | sort)"
  done
  FILES=$(echo "$FILES" | grep -v '^$')
fi

# Il perimetro a file, in forma di baseline (`db/pgtap/...`), per filtrare le
# righe in confronto e in aggiornamento. E gli argomenti che lo ripetono, per i
# comandi suggeriti.
PERIM_REL=$(mktemp)
trap 'rm -f "$PERIM_REL"' EXIT
if [ "$MODIFICATI" -eq 1 ]; then
  echo "$FILES" | sed "s#^$ROOT_DIR/##" > "$PERIM_REL"
  PERIM_ARGS=(--modificati)
  PERIM_NOME="i file modificati"
else
  PERIM_ARGS=("${SCHEMI[@]}")
  PERIM_NOME="${SCHEMI[*]}"
fi

# ⚠️ Nessun default QUI: lo si chiede a testpgtap.sh, che e' l'unico posto
#   in cui il default vive. Averne uno proprio significa che il giorno in
#   cui si commuta il runner questo script etichetta la baseline con
#   l'utente sbagliato — ed e' successo.
RUNNER="${PGTAP_RUNNER:-$("$SCRIPT_DIR/testpgtap.sh" --print-runner)}"
export PGTAP_RUNNER="$RUNNER"

# Utente registrato nella baseline. Prima riga `# pgtap-runner: <x>`; le
# baseline scritte prima dell'introduzione del marcatore non ce l'hanno e sono
# tutte da owner, che era l'unico modo di girare la suite.
baseline_runner() {
  local r
  r=$(grep -m1 -E '^# pgtap-runner:' "$BASELINE" 2>/dev/null | sed -E 's/^# pgtap-runner:[[:space:]]*//')
  echo "${r:-owner}"
}
# Righe vere della baseline (senza intestazione).
baseline_righe() { grep -v '^#' "$BASELINE" 2>/dev/null; }

# ⛔ OGNI COMANDO SUGGERITO PORTA IL PROPRIO CONTESTO, e non e' una gentilezza.
#   Un suggerimento scritto nudo — «scripts/pgtap-baseline.sh --update dbops» —
#   si copia e si incolla, e chi lo incolla NON sta piu' nel contesto in cui e'
#   stato stampato: senza `PGTAP_ENV_FILE` la corsa va sul database di SVILUPPO,
#   e senza `PGTAP_BASELINE` riscrive la baseline di sviluppo con i risultati di
#   un'altra popolazione. Due metri mescolati in un file solo, cioe' esattamente
#   il difetto per cui esistono due baseline.
#   ⚠️ Segnalato da Tid il 2026-09-09 guardando la riga dei RIENTRATI: «si
#   potrebbe essere portati a ricopiarli e si applica sul db sbagliato».
#   ⇒ Il comando si ricompone dalle variabili VERE di questa corsa.
invocazione() {
  local pre=""
  [ -n "${PGTAP_ENV_FILE:-}" ] && pre="${pre}PGTAP_ENV_FILE=$PGTAP_ENV_FILE "
  if [ "$BASELINE" != "$ROOT_DIR/db/pgtap/baseline-rossi.tsv" ]; then
    pre="${pre}PGTAP_BASELINE=${BASELINE#"$ROOT_DIR"/} "
  fi
  echo "${pre}scripts/pgtap-baseline.sh $*"
}

# Metro omogeneo, verificato PRIMA di eseguire: un confronto fra utenti diversi
# non dice niente sulle regressioni, dice solo che i due utenti hanno permessi
# diversi. Il controllo sta qui e non in fondo perche' scoprirlo dopo costerebbe
# l'intera corsa (~7 minuti sulla suite).
# L'unico caso in cui un metro nuovo e' legittimo e' la ribaselinatura INTERA.
if [ -f "$BASELINE" ]; then
  PRECED=$(baseline_runner)
  RIBASE_INTERA=$([ "$UPDATE" -eq 1 ] && perimetro_intero && echo 1 || echo 0)
  if [ "$PRECED" != "$RUNNER" ] && [ "$RIBASE_INTERA" -eq 0 ]; then
    echo "❌ La baseline e' registrata con runner '$PRECED', questa corsa gira con '$RUNNER'." >&2
    if [ "$UPDATE" -eq 1 ]; then
      echo "   Un aggiornamento parziale mescolerebbe due metri nello stesso file." >&2
    else
      echo "   Un rosso puo' dipendere dal ruolo (permessi, RLS): il confronto" >&2
      echo "   produrrebbe finte regressioni." >&2
    fi
    echo "   O si gira con PGTAP_RUNNER=$PRECED, o si ribaselina l'INTERA suite:" >&2
    echo "      PGTAP_RUNNER=$RUNNER $(invocazione --update)" >&2
    exit 2
  fi
fi

# Metro omogeneo, SECONDA FACCIA: le AUTOMAZIONI.
# ⛔ Il migrate costruisce lo schema; i trigger di audit, tx_id, storico,
#   lock-columns e require_attivo li GENERA il framework nella seconda
#   invocazione di Liquibase (`--contexts=ci_apply`). Un database senza quella
#   passata ha lo schema giusto e i presidi a meta': i test che asseriscono su
#   quei trigger diventano rossi, e sono rossi che NON dicono niente sul codice.
#
# ⚠️ Perche' serviva un cancello e non la riga di prosa che c'era gia' (in cima
#   a questo file: «il database scratch va preparato come la CI»). Il
#   2026-09-09 `scripts/ci-local.sh --fresh` — senza `--ci-apply`, che e' un
#   flag SEPARATO — ha prodotto uno scratch a cui mancavano tre dei cinque
#   guard `require_attivo` su ogni `*_righe_componenti`: quattro finte
#   regressioni, scoperte dopo sette minuti di corsa e un'indagine. La CI di
#   GitHub la passata la fa sempre, quindi la' erano verdi: due metri diversi,
#   che e' lo stesso difetto per cui esistono due baseline.
#
# ⭐ La domanda si fa a testpgtap.sh, che e' l'unico posto che sa come si
#   raggiunge il database bersaglio (env file, mapping, utente). Qui si legge
#   solo la risposta.
# ⚠️ Nessun `set +e`/`set -e` attorno: questo script gira con `set -uo pipefail`
#   e NON con `-e`. Riaccenderlo qui lo lascerebbe acceso per tutto il resto del
#   file, cambiando il comportamento di ogni comando che segue.
AUTOMAZIONI=0
"$SCRIPT_DIR/testpgtap.sh" --check-automazioni || AUTOMAZIONI=$?
if [ "$AUTOMAZIONI" -eq 1 ]; then
  echo "❌ Su questo database la passata delle AUTOMAZIONI non e' stata eseguita." >&2
  echo "   I trigger generati (audit, tx_id, storico, lock-columns, require_attivo)" >&2
  echo "   non ci sono: i test che li asseriscono sarebbero rossi per l'ambiente," >&2
  echo "   non per il codice — finte regressioni." >&2
  echo "   Se e' lo scratch locale:" >&2
  echo "      scripts/ci-local.sh --ci-apply" >&2
  echo "   (\`--fresh\` NON la comprende: sono due flag distinti.)" >&2
  exit 2
elif [ "$AUTOMAZIONI" -eq 3 ]; then
  # ⚠️ Non si blocca: se il database non risponde, la corsa lo dira' da sola al
  #   primo file e con un messaggio piu' preciso di questo. Un cancello che
  #   ferma tutto su «non ho potuto chiedere» nasce rosso e viene spento.
  echo "⚠️  Non ho potuto verificare la passata delle automazioni (database non raggiungibile?)." >&2
fi

# ⛔ LA BASELINE DELLA CI LA MISURA LA CI — e adesso e' un cancello.
#   `baseline-rossi-ci.tsv` e' il registro dei rossi della CORSA DI GITHUB. Un
#   `--update` fatto altrove ci scrive dentro la misura di un ALTRO database, e
#   ogni file verde qui e rosso la' sparisce dal registro: alla corsa successiva
#   torna come «regressione», e non perche' si sia rotto qualcosa.
#
# ⚠️ NON E' UN ERRORE DI CHI LO LANCIA: fino al 2026-09-09 era questo script a
#   suggerirlo. Sulla riga dei RIENTRATI stampava «vanno tolti dalla baseline»
#   e consegnava il comando gia' pronto — su un database che quella baseline non
#   la misura. Successo tre volte in un giorno: prima un file, poi la sua
#   re-inserzione, poi dodici insieme.
#
# ⭐ Il discriminante e' DIRETTO: `GITHUB_ACTIONS` lo imposta il runner di
#   GitHub, e dice cio' che serve sapere — «questa corsa E' la CI». ⛔ Non si
#   indovina dal nome del database o dell'env file: sono convenzioni, e una
#   convenzione la si rispetta finche' non la si dimentica.
#   ⚠️ E il perche' i due database non coincidono e' misurato: lo schema
#   `django` in CI lo costruisce `manage.py migrate`, sullo scratch locale e'
#   una COPIA di `dbdev` (`ci-local.sh` lo dichiara: «e' fedele oggi, e
#   invecchia in silenzio»). Sono i dodici file su utenti/identita'/profili.
#
# La valvola c'e', ed e' esplicita: chi rigenera di proposito sa cosa sta
# facendo e lo scrive.
if [ "$UPDATE" -eq 1 ] \
   && [ "$(basename "$BASELINE")" = "baseline-rossi-ci.tsv" ] \
   && [ "${GITHUB_ACTIONS:-}" != "true" ] \
   && [ "${PGTAP_BASELINE_CI_FORZA:-}" != "1" ]; then
  echo "❌ La baseline della CI si aggiorna DALLA CI, non da qui." >&2
  echo "   Questo file registra i rossi della corsa di GitHub: riscriverlo con" >&2
  echo "   la misura di un altro database toglie le righe che qui sono verdi e" >&2
  echo "   la' no, e alla corsa successiva tornano come finte regressioni." >&2
  echo >&2
  echo "   Se un file e' RIENTRATO davvero, lo dira' la CI: la sua corsa lo" >&2
  echo "   elenca, e le righe le toglie scripts/pgtap-baseline-ci-rientrati.sh" >&2
  echo "   leggendo QUEL log (o a mano da $BASELINE)." >&2
  echo "   Per rigenerarla per intero: cancella il file e lascia che la CI la" >&2
  echo "   stampi (il passo della suite la genera fra due marcatori 8<)." >&2
  echo >&2
  echo "   So cosa sto facendo: PGTAP_BASELINE_CI_FORZA=1" >&2
  exit 2
fi

TOT=$(echo "$FILES" | grep -c '' )
echo "pgTAP baseline — $TOT file da eseguire (~$((TOT))s) — runner: $RUNNER"
echo

CORRENTE=$(mktemp)
PRIMO_ROSSO=$(mktemp)
# ⭐ Il MOTIVO di ogni ERRORE_FIXTURE (la prima riga «ERRORE:/ERROR:» del suo
#   output), file per file. Fino al 2026-09-21 si conservava per intero solo il
#   PRIMO rosso, e solo per il cancello «rossi tutti»: un ERRORE_FIXTURE che
#   compariva in una corsa e non si riproduceva da solo (anagrafiche/
#   create-cliente, due volte in due giorni) non lasciava NIENTE da leggere.
#   L'etichetta dice che il file non ha misurato; il motivo dice perche'.
MOTIVI=$(mktemp)
trap 'rm -f "$CORRENTE" "$PRIMO_ROSSO" "$PERIM_REL"' EXIT

n=0
while IFS= read -r f; do
  [ -z "$f" ] && continue
  n=$((n+1))
  rel="${f#"$ROOT_DIR"/db/pgtap/}"
  printf '\r  %d/%d  %-58.58s' "$n" "$TOT" "$rel" >&2

  out=$(timeout 90 "$SCRIPT_DIR/testpgtap.sh" "db/$rel" 2>&1)
  esito=$?
  echo "$out" | grep -q "Result: PASS" && continue

  # Il primo rosso si conserva per intero: se alla fine sono rossi TUTTI, e'
  # l'unica cosa che spiega perche' (vedi il cancello dopo il ciclo).
  [ -s "$PRIMO_ROSSO" ] || printf 'db/pgtap/%s\n\n%s\n' "$rel" "$out" > "$PRIMO_ROSSO"

  # Classificazione della causa: serve a triagiare senza riaprire ogni file.
  #
  # ⛔ IL PREFISSO DELL'ERRORE psql E' TRADOTTO, e per un mese questo ramo e'
  #   stato irraggiungibile in CI. Il messaggio lo scrive il SERVER secondo il
  #   proprio `lc_messages`: il database di sviluppo e' `it_IT.UTF-8` e dice
  #   «ERRORE:», il container della CI (`postgis/postgis:18-3.6`) parla inglese
  #   e dice «ERROR:». Con la sola forma italiana, in CI nessun rosso poteva
  #   finire in ERRORE_FIXTURE: uscivano tutti ASSERZIONE.
  # ⚠️ Misurato il 2026-09-08 sulla corsa 34259315648 (push su Tito-dev): 411
  #   rossi su 599 file, e **411 su 411** etichettati ASSERZIONE. Un file che
  #   non esegue nemmeno un'asserzione veniva registrato come se ne avesse
  #   fallita una — cioe' la baseline dichiarava una copertura parziale dove la
  #   copertura valeva zero.
  # ⭐ Perche' conta: e' il §4-bis della guida sui presidi. Un'etichetta
  #   rassicurante e' piu' pericolosa di un errore, perche' la si legge una
  #   volta e poi ci si fida. Qui l'etichetta sbagliata non l'avrebbe scritta
  #   una persona: la produceva lo strumento, in silenzio, solo fuori da una
  #   macchina italiana.
  # ⛔ IL TIMEOUT VA CHIESTO A `timeout`, NON DEDOTTO DALL'OUTPUT — ed e' il
  #   terzo esito, non un rosso. `timeout` esce **124** quando uccide il figlio,
  #   e fino al 2026-09-10 quell'exit code non lo leggeva nessuno: si guardava
  #   solo se l'output conteneva «Result: PASS». Un file ucciso a meta' non ce
  #   l'ha, quindi finiva fra i rossi — e siccome non contiene nemmeno
  #   «ERRORE:», usciva etichettato **ASSERZIONE**.
  #
  # ⚠️ Cioe' esattamente il difetto che il commento qui sopra descrive per
  #   `lc_messages`, per una causa che quel commento non copre: *un file che non
  #   ha eseguito nemmeno un'asserzione registrato come se ne avesse fallita
  #   una*. La sua copertura vale **zero**, non «una in meno».
  #
  # ⭐ E il danno vero e' l'INSTABILITA': un file che gira attorno alla soglia
  #   entra ed esce dall'elenco a seconda del carico della macchina, quindi
  #   compare come «regressione nuova» in una corsa e sparisce in quella dopo.
  #   Successo davvero (2026-09-10): `vendite/test-documento-lineage-v1.sql`
  #   passa in 111 s da solo — `Result: PASS` — e in baseline veniva ucciso a
  #   90 s e contato fra i rossi. Non era in nessuna delle due baseline, quindi
  #   ogni corsa lo vedeva come regressione mai vista prima.
  #
  # ⛔ Un TIMEOUT non si mette a tacere registrandolo in baseline come gli
  #   altri: un test che non finisce va reso economico o va alzata la soglia
  #   **per decisione**. L'etichetta serve a far vedere QUALE delle due domande
  #   si ha davanti. Stessa forma del terzo esito `SENZA_MATERIA` degli smoke.
  if [ "$esito" -eq 124 ]; then
    causa="TIMEOUT"
  elif echo "$out" | grep -q "key_selector"; then
    causa="SORGENTE_POLIMORFA"
  elif echo "$out" | grep -qE "(ERRORE|ERROR):"; then
    causa="ERRORE_FIXTURE"
    printf 'db/pgtap/%s\t%s\n' "$rel" \
      "$(echo "$out" | grep -m1 -E "(ERRORE|ERROR):" | sed -E 's/^psql:[^:]*:[0-9]+: //' | cut -c1-200)" >> "$MOTIVI"
  else
    causa="ASSERZIONE"
  fi
  printf 'db/pgtap/%s\t%s\n' "$rel" "$causa" >> "$CORRENTE"
done <<< "$FILES"
printf '\r%*s\r' 70 '' >&2

sort -o "$CORRENTE" "$CORRENTE"
ROSSI=$(grep -c '' "$CORRENTE" || true)

# ── ⛔ IL CANCELLO CHE MANCAVA: SE SONO ROSSI TUTTI, NON SI E' MISURATO NIENTE ──
#
#   Non e' una soglia arbitraria, ed e' per questo che il numero e' esattamente
#   «tutti»: se NON PASSA NEMMENO UN FILE, la corsa non ha misurato la suite —
#   ha misurato l'AMBIENTE. Estensione `pgtap` assente, ruolo senza privilegi,
#   database sbagliato, server giu': la causa cambia, la conclusione no.
#
#   ⚠️ Il danno sta tutto in `--update`, e sarebbe permanente: la baseline
#   verrebbe riscritta con OGNI file marcato «rosso noto», cioe' un registro che
#   dichiara l'intera suite come debito accettato. Da quel momento il confronto
#   non puo' piu' trovare nessuna regressione — il cancello resterebbe verde per
#   sempre, e nessuno saprebbe perche'.
#
#   ⭐ Successo davvero, il 2026-09-09, alla prima corsa sul database scratch
#   della replica CI: «Baseline aggiornata: (600 rossi noti)» su 600 file. La
#   causa era una riga sola — `CREATE EXTENSION pgtap` mai eseguita su quel
#   database, quindi `SELECT plan(18)` moriva con «la funzione plan(integer) non
#   esiste» in ogni singolo file. Lo script l'ha scritta come se fosse una
#   misura.
#
#   ⭐ E' il §6 punto 5 della guida sui presidi applicato a questo script:
#   *«fai fallire il controllo quando non puo' misurare. Un cancello che passa
#   perche' non ha misurato niente e' peggio di un cancello assente: da' la
#   sensazione della copertura senza averla»*.
#   ⚠️ Vale sulla suite INTERA, non su un sottoinsieme: uno schema piccolo puo'
#   essere tutto rosso per ragioni sue, e li' il divieto sarebbe un falso
#   allarme. Con gli schemi indicati si avvisa e si prosegue.
if [ "$ROSSI" -eq "$TOT" ] && [ "$TOT" -gt 0 ] && ! perimetro_intero; then
  echo "⚠️  Tutti e $TOT i file di $PERIM_NOME sono rossi: se non te l'aspettavi," >&2
  echo "   guarda l'ambiente (estensione pgtap, privilegi, database) prima di fidarti." >&2
  echo >&2
fi
if [ "$ROSSI" -eq "$TOT" ] && [ "$TOT" -gt 0 ] && perimetro_intero; then
  echo "⛔ ROSSI TUTTI E $TOT: la corsa non ha misurato la suite, ha misurato l'ambiente." >&2
  echo "   La baseline NON e' stata scritta: un registro con dentro tutto" >&2
  echo "   disarmerebbe il confronto per sempre." >&2
  echo >&2
  echo "   Cause tipiche, in ordine di frequenza:" >&2
  echo "     * estensione pgtap assente sul database bersaglio" >&2
  echo "         psql -U postgres -d <db> -c 'CREATE EXTENSION IF NOT EXISTS pgtap;'" >&2
  echo "     * il ruolo applicativo non ha privilegi (scripts/sql/provision_zeroerp.sql, fase post)" >&2
  echo "     * si sta puntando al database sbagliato (PGTAP_ENV_FILE)" >&2
  echo >&2
  echo "── output completo del primo file rosso, che di solito lo dice ──" >&2
  sed 's/^/   /' "$PRIMO_ROSSO" >&2
  exit 2
fi

# --- modalita' aggiornamento -------------------------------------------------
if [ "$UPDATE" -eq 1 ]; then
  TMP=$(mktemp)
  if perimetro_intero; then
    cp "$CORRENTE" "$TMP"
  elif [ "$MODIFICATI" -eq 1 ]; then
    # Si sostituiscono SOLO le righe dei file eseguiti.
    baseline_righe | awk -F'\t' 'NR==FNR { dentro[$0]=1; next } !($1 in dentro)' "$PERIM_REL" - > "$TMP"
    cat "$CORRENTE" >> "$TMP"
    sort -o "$TMP" "$TMP"
  else
    # Aggiornamento parziale: si sostituiscono SOLO le righe degli schemi
    # eseguiti, lasciando intatto il resto della baseline.
    #
    # L'omogeneita' del metro e' gia' stata verificata prima della corsa.
    baseline_righe > "$TMP"
    for sc in "${SCHEMI[@]}"; do
      grep -v "^db/pgtap/$sc/" "$TMP" > "$TMP.f" && mv "$TMP.f" "$TMP"
    done
    cat "$CORRENTE" >> "$TMP"
    sort -o "$TMP" "$TMP"
  fi
  { echo "# pgtap-runner: $RUNNER"; cat "$TMP"; } > "$BASELINE"
  rm -f "$TMP"
  echo "Baseline aggiornata: $BASELINE ($(baseline_righe | grep -c '') rossi noti, runner: $RUNNER)"
  exit 0
fi

# --- modalita' confronto -----------------------------------------------------
if [ ! -f "$BASELINE" ]; then
  echo "Baseline assente ($BASELINE)." >&2
  echo "Generala con: $(invocazione --update)" >&2
  exit 2
fi

# Confronto sulla sola colonna file: la causa e' informativa, non identitaria
# (lo stesso file puo' cambiare causa restando rosso — non e' una regressione).
NOTI=$(mktemp); ATTUALI=$(mktemp)
trap 'rm -f "$CORRENTE" "$NOTI" "$ATTUALI" "$MOTIVI" "$PERIM_REL" "$PRIMO_ROSSO"' EXIT
if perimetro_intero; then
  baseline_righe | cut -f1 | sort > "$NOTI"
elif [ "$MODIFICATI" -eq 1 ]; then
  baseline_righe | cut -f1 | grep -F -x -f "$PERIM_REL" | sort > "$NOTI"
else
  pat=$(printf 'db/pgtap/%s/\n' "${SCHEMI[@]}" | paste -sd'|')
  baseline_righe | cut -f1 | grep -E "^($pat)" | sort > "$NOTI"
fi
cut -f1 "$CORRENTE" | sort > "$ATTUALI"

NUOVI=$(comm -13 "$NOTI" "$ATTUALI")
RIENTRATI=$(comm -23 "$NOTI" "$ATTUALI")

echo "Rossi ora: $ROSSI su $TOT   |   noti in baseline (perimetro): $(grep -c '' "$NOTI")"
echo

if [ -n "$RIENTRATI" ]; then
  # ⛔ IL SUGGERIMENTO SI ADATTA AL BERSAGLIO, e non e' una sfumatura: e' la
  #   riga che ha causato il difetto tre volte. Su `baseline-rossi-ci.tsv`
  #   misurata fuori dalla CI, «ora verdi» vuol dire «verdi QUI»: consegnare il
  #   comando di aggiornamento invita a scrivere la misura di questo database
  #   nel registro di un altro.
  if [ "$(basename "$BASELINE")" = "baseline-rossi-ci.tsv" ] \
     && [ "${GITHUB_ACTIONS:-}" != "true" ]; then
    echo "ℹ️  Verdi QUI, e questa non e' la CI — potrebbero essere rossi la':"
    echo "$RIENTRATI" | sed 's/^/   /'
    echo "   ⛔ Non si aggiorna da qui: $(basename "$BASELINE") registra i rossi"
    echo "      della corsa di GitHub. Se sono rientrati davvero, lo dira' la CI:"
    echo "      → scripts/pgtap-baseline-ci-rientrati.sh   (legge il log della corsa)"
  else
    echo "✅ RIENTRATI — ora verdi, vanno tolti dalla baseline:"
    echo "$RIENTRATI" | sed 's/^/   /'
    echo "   → $(invocazione --update "${PERIM_ARGS[@]}")"
  fi
  echo
fi

if [ -n "$NUOVI" ]; then
  # ⛔ Stessa regola dei RIENTRATI: il registro della CI letto fuori dalla CI
  #   non sa giudicare QUESTO database. Il 14-09, tolto dal registro della CI
  #   `rls/test-role-batch-fatturazione-postura` (verde la', rientrato), lo
  #   scratch lo ha stampato come «REGRESSIONE»: la' era rosso per costruzione
  #   (il batch riceveva DML su tutto) e il suo registro e'
  #   baseline-rossi-scratch.tsv. Lo stesso giorno ci-local.sh ha imparato a
  #   rilanciare il provisioning vero del batch; la regola resta: tre metri,
  #   tre registri, e questo blocco si limita a dirlo.
  if [ "$(basename "$BASELINE")" = "baseline-rossi-ci.tsv" ] \
     && [ "${GITHUB_ACTIONS:-}" != "true" ]; then
    echo "❌ Rossi QUI che la CI non conosce — e questa non e' la CI:"
  else
    echo "❌ REGRESSIONI — rossi NUOVI, non erano in baseline:"
  fi
  while IFS= read -r nf; do
    [ -z "$nf" ] && continue
    causa=$(grep -F "$nf"$'\t' "$CORRENTE" | cut -f2)
    printf '   %-62s %s\n' "$nf" "$causa"
    # ⭐ Un ERRORE_FIXTURE si LEGGE: la riga d'errore sta qui, non va cercata.
    motivo=$(grep -F "$nf"$'\t' "$MOTIVI" | cut -f2)
    [ -n "$motivo" ] && printf '   %-62s   ↳ %s\n' "" "$motivo"
  done <<< "$NUOVI"
  echo
  if [ "$(basename "$BASELINE")" = "baseline-rossi-ci.tsv" ] \
     && [ "${GITHUB_ACTIONS:-}" != "true" ]; then
    echo "   Possono essere regressioni vere o rossi di QUESTO database (lo scratch"
    echo "   non e' la CI: django copiato, dblink spento, ...). Si giudicano sul"
    echo "   registro di questo metro: PGTAP_BASELINE=db/pgtap/baseline-rossi-scratch.tsv"
  else
    echo "Sono da guardare: tutto il resto era gia' rosso prima."
  fi
  exit 1
fi

echo "✅ Nessuna regressione: ogni rosso era gia' noto."
exit 0
