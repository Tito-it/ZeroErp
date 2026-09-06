#!/usr/bin/env bash
# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Bash
# Scopo: Prova il ramo di `bin/install-timers.sh` CHE ACCENDE gli unit — quello
#        che `--render-only` non attraversa e che nessuna prova toccava.
# ------------------------------------------------------------
#
# 🔴 PERCHE' ESISTE. Il 2026-09-06 `install-timers.sh` classificava
# `zeroerp-listen-cambio-reparto` fra gli SPENTI per uno slittamento di campi
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
# Indice test (0..5):
#   0. il piano accende ESATTAMENTE gli unit dichiarati `abilita: true`
#   1. gli unit dichiarati `abilita: false` non vengono accesi
#   2. si accende il `.timer` dei timer e il `.service` dei servizi sempre accesi
#   3. `daemon-reload` precede gli `enable`
#   4. REGRESSIONE: un campo vuoto non fa slittare i campi (il difetto del 06-09)
#   5. senza root e senza destinazione alternativa, si ferma

set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
INSTALLER="${APP_DIR}/bin/install-timers.sh"
SVEGLIE="${APP_DIR}/deploy/sveglie.json"
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
  PATH="$TMP/bin:$PATH" \
  SYSTEMCTL_REGISTRO="$registro" \
  ZEROERP_SYSTEMD_DIR="$dest" \
    bash "$INSTALLER" > "$TMP/$run/stdout.txt" 2>&1
  echo "$registro"
}

# Scopo: gli unit che il dichiarato marca `abilita`, con il suffisso giusto —
#        letti dalla STESSA fonte dello script, non riscritti qui.
# ⛔ Un elenco atteso scritto a mano sarebbe una seconda copia del dichiarato, e
#    proverebbe che due copie coincidono invece che il comportamento.
attesi() {
  local vogliamo="$1"   # true | false
  python3 - "$SVEGLIE" "$vogliamo" <<'PY'
import json, sys
vogliamo = sys.argv[2] == "true"
for s in json.load(open(sys.argv[1], encoding="utf-8"))["sveglie"]:
    if bool(s.get("abilita")) is vogliamo:
        kind = "timer" if s.get("forma") == "timer" else "service"
        print(f"{s['unit']}.{kind}")
PY
}

echo "== install-timers: il ramo che accende =="
prepara_stub
REGISTRO="$(esegui_installer principale)"

# ── 0. accende esattamente i dichiarati `abilita: true` ──────────────────
ACCESI="$(grep '^enable --now ' "$REGISTRO" | sed 's/^enable --now //' | sort)"
ATTESI="$(attesi true | sort)"
if [ "$ACCESI" = "$ATTESI" ]; then
  ok "accesi esattamente gli unit dichiarati (${ATTESI//$'\n'/, })"
else
  ko "accesi != dichiarati"
  diff <(echo "$ATTESI") <(echo "$ACCESI") | sed 's/^/       /' || true
fi

# ── 1. i dichiarati `abilita: false` restano spenti ──────────────────────
SPENTI_ACCESI=""
while read -r u; do
  [ -n "$u" ] || continue
  grep -Fxq "enable --now $u" "$REGISTRO" && SPENTI_ACCESI="$SPENTI_ACCESI $u"
done <<< "$(attesi false)"
if [ -z "$SPENTI_ACCESI" ]; then
  ok "nessun unit dichiarato spento è stato acceso"
else
  ko "acceso un unit che doveva restare spento:$SPENTI_ACCESI"
fi

# ── 2. suffisso giusto per forma ─────────────────────────────────────────
# Un servizio sempre acceso si abilita come `.service`: non ha un `.timer`, e
# accenderne uno inesistente fallirebbe sull'host.
if grep -Fxq "enable --now zeroerp-listen-cambio-reparto.service" "$REGISTRO" \
   && ! grep -q "zeroerp-listen-cambio-reparto.timer" "$REGISTRO"; then
  ok "il servizio sempre acceso si abilita come .service, mai come .timer"
else
  ko "suffisso sbagliato per il servizio sempre acceso"
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
# ⭐ È il test che vale: `zeroerp-listen-cambio-reparto` è l'unica voce con
#    `oncalendar` vuoto, e con la vecchia lettura a TAB `abilita` diventava il
#    testo della nota — quindi il servizio finiva fra gli spenti. Se un giorno
#    il separatore tornasse a essere IFS-whitespace, questo diventa rosso.
if grep -Fxq "enable --now zeroerp-listen-cambio-reparto.service" "$REGISTRO"; then
  ok "campo vuoto: il listener è acceso (nessuno slittamento di campi)"
else
  ko "REGRESSIONE dello slittamento campi: il listener NON è stato acceso"
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

echo
if [ "$FALLITI" -eq 0 ]; then
  echo "ESITO: OK"
else
  echo "ESITO: FALLITO ($FALLITI)"
fi
exit "$FALLITI"
