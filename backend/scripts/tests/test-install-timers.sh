#!/usr/bin/env bash
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Bash
# Scopo: Prova il ramo di `bin/install-timers.sh` CHE ACCENDE gli unit — quello
#        che `--render-only` non attraversa e che nessuna prova toccava.
# ------------------------------------------------------------
#
# 🔴 PERCHE' ESISTE. Il 2026-09-06 `install-timers.sh` classificava
# `zeroerp-listen-cambio-reparto` (oggi `zeroerp-listen-permessi`) fra gli
# SPENTI per uno slittamento di campi
# (`read` con `IFS=$'\t'` collassa i TAB consecutivi, e un `oncalendar` vuoto —
# il caso normale di un servizio sempre acceso — faceva scalare `abilita` sul
# testo della nota). Il servizio veniva installato e mai avviato.
# ⛔ La CI renderizzava sette unit corretti e non poteva vederlo: `--render-only`
# esce PRIMA del ramo che accende. *Il difetto viveva esattamente dove la prova
# non arrivava.*
#
# ⭐ COME LO PROVA, e non con una modalità finta. Due cuciture, zero rami nuovi:
#   1. un `systemctl` FINTO in testa al `PATH` — lo script lo invoca senza
#      percorso assoluto, quindi la shell trova il nostro, che registra come è
#      stato chiamato invece di toccare il sistema;
#   2. `ZEROERP_SYSTEMD_DIR` sposta la destinazione in una cartella temporanea,
#      e con essa cade il requisito di root (che serve a scrivere in
#      `/etc/systemd/system`, non «perché è la modalità install»).
# ⇒ Le righe eseguite sono LE STESSE della produzione. Un `--dry-run` che salta
#   `systemctl` avrebbe provato il ramo che NON accende: inutile per questo bug.
#
# ⚠️ CHE COSA NON PROVA: che systemd accetti quegli unit. È l'altra metà, e ce
#   l'ha già `systemd-analyze verify` sui template renderizzati. Le due insieme
#   dicono «gli unit sono validi» E «si accendono quelli giusti»; finora c'era
#   solo la prima.
#
# ⭐ DAL 2026-09-14 PROVA ANCHE CHE LA RIGA DI COMANDO HA UNA SEDE SOLA (test 6
#   e 7): il template porta `__COMANDO__` e l'unit reso porta l'argv di
#   `sveglie.json`. È il prerequisito di «Esegui ora» (analisi-riavvio-processi-
#   da-interfaccia.md §4.1-bis): il pulsante lancia il comando letto dal JSON, e
#   se un template avesse ancora una riga cablata il timer e il pulsante
#   potrebbero eseguire due cose diverse — in silenzio, perché entrambe girano.
#
# Indice test (0..8):
#   0. il piano accende OGNI sveglia dichiarata, e niente altro (dal 2026-10-16
#      se un processo lavora lo decide il DB, non l'installer)
#   1. ogni `.service` reso porta l'`ExecCondition` della sua unit: e' il
#      cancello che chiede al DB se il processo e' acceso
#   2. si accende il `.timer` dei timer e il `.service` dei servizi sempre accesi
#   3. `daemon-reload` precede gli `enable`
#   4. REGRESSIONE: un campo vuoto non fa slittare i campi (il difetto del 06-09)
#   5. senza root e senza destinazione alternativa, si ferma
#   6. nessun template `.service` ha un `ExecStart` cablato: tutti `__COMANDO__`
#   7. l'unit reso esegue ESATTAMENTE l'argv di `sveglie.json`, senza residui
#   8. una SVEGLIA installata e non più dichiarata si spegne e si toglie (timer
#      prima del servizio, prima del daemon-reload), anche senza prefisso
#      `zeroerp-`, e così il `.timer` rimasto a un servizio dichiarato; un unit
#      che non è una sveglia (`zeroerp-gunicorn`, chi cita il wrapper in un
#      commento) e il resto non si toccano

set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
INSTALLER="${APP_DIR}/bin/install-timers.sh"
SVEGLIE="${APP_DIR}/deploy/sveglie.json"
TEMPLATE_DIR="${APP_DIR}/deploy/systemd"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

FALLITI=0

# Scopo: segnala un test verde.
ok() { echo "  ✅ $1"; }

# Scopo: segnala un test rosso e alza il contatore (non ferma la corsa: si
#        vogliono vedere TUTTI i rossi, non solo il primo).
ko() { echo "  ❌ $1"; FALLITI=$((FALLITI + 1)); }

# Scopo: costruisce il `systemctl` finto. Registra ogni invocazione su
#        $REGISTRO, una riga per chiamata, e non tocca niente.
# ⚠️ Esce sempre 0: questa prova riguarda CHE COSA lo script decide di
#    accendere, non come reagisce a un `enable` fallito. Quel caso vuole uno
#    stub parametrico, ed è un test suo.
prepara_stub() {
  mkdir -p "$TMP/bin"
  cat > "$TMP/bin/systemctl" <<'STUB'
#!/usr/bin/env bash
echo "$*" >> "$SYSTEMCTL_REGISTRO"
STUB
  chmod +x "$TMP/bin/systemctl"
}

# Scopo: lancia l'installer in modalità INSTALL (quella vera) con lo stub al
#        posto di systemctl e la destinazione in una cartella temporanea.
#        Ritorna il percorso del registro delle chiamate.
esegui_installer() {
  local run="$1" dest="$TMP/$1/units" registro="$TMP/$1/systemctl.log"
  mkdir -p "$TMP/$run"
  : > "$registro"
  # ⛔ L'USCITA DELL'INSTALLER SI MOSTRA QUANDO FALLISCE, e non è un di più.
  #    L'output va in un file (il registro delle chiamate è quello che conta, e
  #    lo stdout sporcherebbe l'esito), il file lo cancella il `trap`, e con
  #    `set -e` la corsa muore prima di stampare qualsiasi cosa: in CI restava
  #    l'intestazione e `exit 1`, senza una riga che dicesse perché.
  # 🔴 È successo davvero: l'installer si fermava su un env file assente — che
  #    in un checkout non c'è mai — e la CI non aveva modo di dirlo.
  # ⚠️ `|| { … }` e non `set +e`: qui un installer che fallisce È il rosso, e
  #    proseguire vorrebbe dire misurare un registro vuoto e attribuire il
  #    guasto al primo controllo invece che alla causa.
  if ! PATH="$TMP/bin:$PATH" \
       SYSTEMCTL_REGISTRO="$registro" \
       ZEROERP_SYSTEMD_DIR="$dest" \
         bash "$INSTALLER" > "$TMP/$run/stdout.txt" 2>&1; then
    echo "  ❌ l'installer è uscito con errore ($run). Ecco cosa ha detto:" >&2
    sed 's/^/       /' "$TMP/$run/stdout.txt" >&2
    exit 1
  fi
  echo "$registro"
}

# Scopo: gli unit che l'installer accende — ogni sveglia dichiarata, col
#        suffisso giusto — letti dalla STESSA fonte dello script, non riscritti
#        qui.
# ⛔ Un elenco atteso scritto a mano sarebbe una seconda copia del dichiarato, e
#    proverebbe che due copie coincidono invece che il comportamento.
attesi() {
  python3 - "$SVEGLIE" <<'PY'
import json, sys
for s in json.load(open(sys.argv[1], encoding="utf-8"))["sveglie"]:
    kind = "timer" if s.get("forma") == "timer" else "service"
    print(f"{s['unit']}.{kind}")
PY
}

# Scopo: le sveglie di forma `servizio` (`oncalendar` vuoto), lette dalla
#        stessa fonte — vale la nota di `attesi()`. Dal 2026-10-05: prima il
#        nome del listener era scritto qui, e il suo rinomino
#        (`listen_permessi`) lo ha reso una seconda copia.
servizi_accesi() {
  python3 - "$SVEGLIE" <<'PY'
import json, sys
for s in json.load(open(sys.argv[1], encoding="utf-8"))["sveglie"]:
    if s.get("forma") == "servizio":
        print(s["unit"])
PY
}

# Scopo: per ogni unit dichiarata, la riga `ExecStart=` che l'unit reso DEVE
#        avere: il wrapper di questo checkout più l'argv di `sveglie.json`,
#        unito da spazi come fa l'installer. Letto dalla stessa fonte, non
#        riscritto qui — vale la nota di `attesi()`.
exec_start_attesi() {
  python3 - "$SVEGLIE" "$APP_DIR" <<'PY'
import json, sys
app_dir = sys.argv[2]
for s in json.load(open(sys.argv[1], encoding="utf-8"))["sveglie"]:
    argv = " ".join(str(x) for x in s["comando"])
    print(f"{s['unit']}\tExecStart={app_dir}/bin/run-command.sh {argv}")
PY
}

echo "== install-timers: il ramo che accende =="
prepara_stub
REGISTRO="$(esegui_installer principale)"
UNITS_RESI="$TMP/principale/units"

# ── 0. accende ogni sveglia dichiarata, e niente altro ───────────────────
ACCESI="$(grep '^enable --now ' "$REGISTRO" | sed 's/^enable --now //' | sort)"
ATTESI="$(attesi | sort)"
if [ "$ACCESI" = "$ATTESI" ]; then
  ok "accese tutte e sole le sveglie dichiarate (${ATTESI//$'\n'/, })"
else
  ko "accesi != dichiarati"
  diff <(echo "$ATTESI") <(echo "$ACCESI") | sed 's/^/       /' || true
fi

# ── 1. ogni .service reso porta il cancello della SUA unit ───────────────
# ⭐ Dal 2026-10-16 l'installer accende tutto, e uno spento salta solo perche'
#    l'`ExecCondition` lo chiede al DB. Una sveglia senza cancello lavorerebbe
#    anche a processo spento: in silenzio, perche' girerebbe e basta.
SENZA_CANCELLO=""
while read -r u; do
  [ -n "$u" ] || continue
  u="${u%.*}"
  grep -Fxq "ExecCondition=${APP_DIR}/bin/run-command.sh e_dovuto ${u}" "$UNITS_RESI/${u}.service" \
    || SENZA_CANCELLO="$SENZA_CANCELLO $u"
done <<< "$(attesi)"
if [ -z "$SENZA_CANCELLO" ]; then
  ok "ogni sveglia resa chiede al DB se il processo e' acceso (ExecCondition e_dovuto <unit>)"
else
  ko "sveglie senza il cancello dell'accensione:$SENZA_CANCELLO"
fi

# ── 2. suffisso giusto per forma ─────────────────────────────────────────
# Un servizio sempre acceso si abilita come `.service`: non ha un `.timer`, e
# accenderne uno inesistente fallirebbe sull'host.
# ⛔ Senza servizi dichiarati la prova non prova niente: rosso, non verde.
SERVIZI="$(servizi_accesi)"
SUFFISSO_ERRATO=""
while read -r u; do
  [ -n "$u" ] || continue
  if ! grep -Fxq "enable --now ${u}.service" "$REGISTRO" \
     || grep -q "${u}.timer" "$REGISTRO"; then
    SUFFISSO_ERRATO="$SUFFISSO_ERRATO $u"
  fi
done <<< "$SERVIZI"
if [ -z "$SERVIZI" ]; then
  ko "nessun servizio sempre acceso dichiarato: i test 2 e 4 non provano niente"
elif [ -z "$SUFFISSO_ERRATO" ]; then
  ok "i servizi sempre accesi si abilitano come .service, mai come .timer (${SERVIZI//$'\n'/, })"
else
  ko "suffisso sbagliato per il servizio sempre acceso:$SUFFISSO_ERRATO"
fi

# ── 3. daemon-reload prima degli enable ──────────────────────────────────
# Abilitare un unit che systemd non ha ancora riletto è la ragione classica di
# un «Unit file ... does not exist» su un host appena aggiornato.
RIGA_RELOAD="$(grep -n '^daemon-reload$' "$REGISTRO" | head -1 | cut -d: -f1 || true)"
RIGA_ENABLE="$(grep -n '^enable --now ' "$REGISTRO" | head -1 | cut -d: -f1 || true)"
if [ -n "$RIGA_RELOAD" ] && [ -n "$RIGA_ENABLE" ] && [ "$RIGA_RELOAD" -lt "$RIGA_ENABLE" ]; then
  ok "daemon-reload invocato prima del primo enable"
else
  ko "daemon-reload mancante o dopo gli enable (reload=$RIGA_RELOAD enable=$RIGA_ENABLE)"
fi

# ── 4. REGRESSIONE: il campo vuoto non fa slittare i campi ───────────────
# ⭐ I servizi sono le voci con `oncalendar` vuoto, e con la vecchia lettura a
#    TAB il campo dopo slittava: fino al 2026-10-16 era `abilita`, e il servizio
#    finiva fra gli spenti. Oggi `abilita` non c'e' piu', ma il separatore resta
#    la regola dell'estrattore: se tornasse IFS-whitespace i campi dopo un
#    vuoto scalerebbero di nuovo, e questa prova resta il suo presidio sul ramo
#    che accende.
SPENTI_PER_SLITTAMENTO=""
while read -r u; do
  [ -n "$u" ] || continue
  grep -Fxq "enable --now ${u}.service" "$REGISTRO" \
    || SPENTI_PER_SLITTAMENTO="$SPENTI_PER_SLITTAMENTO $u"
done <<< "$SERVIZI"
if [ -n "$SERVIZI" ] && [ -z "$SPENTI_PER_SLITTAMENTO" ]; then
  ok "campo vuoto: i servizi sempre accesi sono accesi (nessuno slittamento di campi)"
else
  ko "REGRESSIONE dello slittamento campi: NON acceso:${SPENTI_PER_SLITTAMENTO:- nessun servizio dichiarato}"
fi

# ── 5. senza root e senza destinazione alternativa, si ferma ─────────────
# Il guard sul root non è sparito con la cucitura: è legato alla destinazione.
if [ "$(id -u)" -ne 0 ]; then
  if PATH="$TMP/bin:$PATH" SYSTEMCTL_REGISTRO="$TMP/mai.log" \
       bash "$INSTALLER" > "$TMP/senza-root.txt" 2>&1; then
    ko "senza root ha proseguito verso /etc/systemd/system"
  else
    grep -q "Esegui come root" "$TMP/senza-root.txt" \
      && ok "senza root e senza override: si ferma nominando il motivo" \
      || ko "si è fermato, ma non per il motivo giusto"
  fi
else
  echo "  ⏭️  test 5 saltato: la suite gira come root"
fi

# ── 6. nessun template `.service` con un ExecStart cablato ───────────────
# ⛔ Un template che porta ancora la riga scritta a mano è la SECONDA sede del
#    comando: il timer eseguirebbe quella, «Esegui ora» quella del JSON, e
#    nessuna delle due fallirebbe. Ogni `.service` deve portare `__COMANDO__`
#    nell'`ExecStart`, e uno solo.
CABLATI=""
for tpl in "$TEMPLATE_DIR"/*.service; do
  n_exec="$(grep -c '^ExecStart=' "$tpl" || true)"
  if [ "$n_exec" -ne 1 ] \
     || ! grep -Fxq 'ExecStart=__APP_DIR__/bin/run-command.sh __COMANDO__' "$tpl"; then
    CABLATI="$CABLATI $(basename "$tpl")"
  fi
done
if [ -z "$CABLATI" ]; then
  ok "ogni template .service porta 'ExecStart=… run-command.sh __COMANDO__' (una sede sola)"
else
  ko "template con ExecStart cablato o non standard:$CABLATI"
fi

# ── 7. l'unit reso esegue esattamente l'argv del dichiarato ──────────────
# È la prova dell'altra metà: il segnaposto è stato SOSTITUITO con l'argv del
# JSON — non lasciato lì (systemd lancerebbe un comando chiamato `__COMANDO__`)
# e non con un'altra cosa. Si confronta la riga intera, non una sottostringa.
DIVERGENTI=""
while IFS=$'\t' read -r unit atteso; do
  [ -n "$unit" ] || continue
  reso="$UNITS_RESI/${unit}.service"
  if [ ! -f "$reso" ]; then
    DIVERGENTI="$DIVERGENTI ${unit}(non-reso)"
  elif ! grep -Fxq "$atteso" "$reso"; then
    DIVERGENTI="$DIVERGENTI ${unit}"
  fi
done <<< "$(exec_start_attesi)"
if grep -l '__COMANDO__' "$UNITS_RESI"/* >/dev/null 2>&1; then
  DIVERGENTI="$DIVERGENTI (residuo __COMANDO__ in un unit reso)"
fi
if [ -z "$DIVERGENTI" ]; then
  ok "ogni unit reso esegue l'argv dichiarato in sveglie.json"
else
  ko "unit resi che non eseguono l'argv dichiarato:$DIVERGENTI"
fi

# ── 8. il ritiro di ciò che non è più dichiarato ─────────────────────────
# ⭐ Dal 2026-10-05: prima l'installer solo aggiungeva, e un unit rinominato
#    (`zeroerp-listen-cambio-reparto` → `zeroerp-listen-permessi`) restava
#    acceso accanto al nuovo. Si semina la destinazione con un orfano (coppia
#    timer + servizio), un file che non è di questo programma e un dichiarato
#    già installato; poi si guarda che cosa l'installer ha spento e tolto.
# ⚠️ Nella corsa principale la destinazione è vuota: nessun `disable` atteso.
if grep -q '^disable ' "$REGISTRO"; then
  ko "destinazione pulita, eppure l'installer ha spento qualcosa: $(grep '^disable ' "$REGISTRO" | tr '\n' ' ')"
fi
SEMINA="$TMP/ritiro/units"
mkdir -p "$SEMINA"
# L'orfano porta la firma delle sveglie (il wrapper); `zeroerp-gunicorn` no.
# 🔴 È il caso del 2026-10-05: la prima versione cancellò il backend del dbdev.
printf '[Service]\nExecStart=%s/bin/run-command.sh comando_ritirato\n' "$APP_DIR" \
  > "$SEMINA/zeroerp-vecchio.service"
printf '[Timer]\nOnCalendar=daily\n' > "$SEMINA/zeroerp-vecchio.timer"
printf '[Service]\nExecStart=%s/bin/start-gunicorn.sh\n' "$APP_DIR" \
  > "$SEMINA/zeroerp-gunicorn.service"
touch "$SEMINA/altro.service"
# Una sveglia che non si chiama `zeroerp-*`: decide la firma, non il nome.
printf '[Service]\nExecStart=%s/bin/run-command.sh altro_comando\n' "$APP_DIR" \
  > "$SEMINA/senza-prefisso.service"
# Un estraneo che CITA il wrapper in un commento: non è una sveglia.
printf '[Service]\n# ExecStart=%s/bin/run-command.sh finto\nExecStart=/bin/true\n' "$APP_DIR" \
  > "$SEMINA/zeroerp-cita-il-wrapper.service"
# Il `.timer` rimasto a un servizio DICHIARATO (sveglia passata da timer a
# servizio): il suo `.service` è una sveglia, quindi il timer si ritira.
UN_SERVIZIO="$(servizi_accesi | head -1)"
printf '[Service]\nExecStart=%s/bin/run-command.sh x\n' "$APP_DIR" > "$SEMINA/${UN_SERVIZIO}.service"
printf '[Timer]\nOnCalendar=daily\n' > "$SEMINA/${UN_SERVIZIO}.timer"
UN_DICHIARATO="$(attesi true | head -1)"
touch "$SEMINA/$UN_DICHIARATO"
REG_RITIRO="$(esegui_installer ritiro)"
SBAGLI_RITIRO=""
RIGA_T="$(grep -nFx 'disable --now zeroerp-vecchio.timer' "$REG_RITIRO" | cut -d: -f1 || true)"
RIGA_S="$(grep -nFx 'disable --now zeroerp-vecchio.service' "$REG_RITIRO" | cut -d: -f1 || true)"
RIGA_R="$(grep -n '^daemon-reload$' "$REG_RITIRO" | head -1 | cut -d: -f1 || true)"
if [ -z "$RIGA_T" ] || [ -z "$RIGA_S" ]; then
  SBAGLI_RITIRO="$SBAGLI_RITIRO orfano-non-spento"
elif [ "$RIGA_T" -gt "$RIGA_S" ] || [ -z "$RIGA_R" ] || [ "$RIGA_S" -gt "$RIGA_R" ]; then
  SBAGLI_RITIRO="$SBAGLI_RITIRO ordine(timer=$RIGA_T,service=$RIGA_S,reload=$RIGA_R)"
fi
[ -e "$SEMINA/zeroerp-vecchio.service" ] && SBAGLI_RITIRO="$SBAGLI_RITIRO service-non-tolto"
[ -e "$SEMINA/zeroerp-vecchio.timer" ] && SBAGLI_RITIRO="$SBAGLI_RITIRO timer-non-tolto"
[ -e "$SEMINA/altro.service" ] || SBAGLI_RITIRO="$SBAGLI_RITIRO tolto-un-file-non-zeroerp"
[ -e "$SEMINA/zeroerp-gunicorn.service" ] || SBAGLI_RITIRO="$SBAGLI_RITIRO TOLTO-GUNICORN"
grep -q 'zeroerp-gunicorn' "$REG_RITIRO" && SBAGLI_RITIRO="$SBAGLI_RITIRO SPENTO-GUNICORN"
grep -q 'ESTRANEO zeroerp-gunicorn.service' "$TMP/ritiro/stdout.txt" \
  || SBAGLI_RITIRO="$SBAGLI_RITIRO estraneo-non-nominato"
[ -e "$SEMINA/$UN_DICHIARATO" ] || SBAGLI_RITIRO="$SBAGLI_RITIRO tolto-un-dichiarato"
grep -Fxq 'disable --now senza-prefisso.service' "$REG_RITIRO" \
  || SBAGLI_RITIRO="$SBAGLI_RITIRO sveglia-senza-prefisso-non-ritirata"
grep -q 'zeroerp-cita-il-wrapper' "$REG_RITIRO" \
  && SBAGLI_RITIRO="$SBAGLI_RITIRO ritirato-chi-cita-il-wrapper-in-un-commento"
[ -e "$SEMINA/zeroerp-cita-il-wrapper.service" ] || SBAGLI_RITIRO="$SBAGLI_RITIRO tolto-chi-cita-il-wrapper"
grep -Fxq "disable --now ${UN_SERVIZIO}.timer" "$REG_RITIRO" \
  || SBAGLI_RITIRO="$SBAGLI_RITIRO timer-vecchio-di-un-servizio-dichiarato-non-ritirato"
grep -Fxq "disable --now ${UN_SERVIZIO}.service" "$REG_RITIRO" \
  && SBAGLI_RITIRO="$SBAGLI_RITIRO SPENTO-UN-SERVIZIO-DICHIARATO"
# Attesi: vecchio.timer, <servizio>.timer, vecchio.service, senza-prefisso.service.
N_DISABLE="$(grep -c '^disable ' "$REG_RITIRO" || true)"
[ "$N_DISABLE" -eq 4 ] || SBAGLI_RITIRO="$SBAGLI_RITIRO disable-attesi-4-avuti-$N_DISABLE"
if [ -z "$SBAGLI_RITIRO" ]; then
  ok "l'orfano si spegne (timer prima del servizio, prima del reload) e si toglie; gunicorn e il resto non si toccano"
else
  ko "ritiro degli unit non dichiarati:$SBAGLI_RITIRO"
fi

echo
if [ "$FALLITI" -eq 0 ]; then
  echo "ESITO: OK"
else
  echo "ESITO: FALLITO ($FALLITI)"
fi
exit "$FALLITI"
