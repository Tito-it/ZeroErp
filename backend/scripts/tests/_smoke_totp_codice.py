# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il codice del secondo fattore per gli smoke (`_smoke_secondo_fattore.sh`):
#        legge il segreto da SMOKE_TOTP_SECRET e stampa il codice di un passo
#        MAI usato da questi smoke.
# Note: ⭐ Il DB accetta un passo una volta sola (anti-replay, `fn_totp_registra_uso`):
#       due login nello stesso intervallo di 30 secondi avrebbero lo stesso
#       codice, e il secondo sarebbe rifiutato con E_TOTP_PASSO_GIA_USATO. Si
#       ricorda l'ultimo passo usato in un file (uno per segreto, sotto la
#       cartella temporanea, col lock) e, se serve, si ASPETTA il passo dopo.
#       Il periodo e il calcolo sono quelli di `apps.core.services.totp_service`
#       (pyotp, 30 s, 6 cifre): si importa da li', nessuna seconda sede.
#       Gira col python del venv del backend (pyotp e' una sua dipendenza).
# ------------------------------------------------------------

from __future__ import annotations

import fcntl
import hashlib
import os
import re
import sys
import tempfile
import time
from pathlib import Path

# Il backend sul path: `totp_service` e' puro (pyotp e segno, niente Django).
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pyotp

from apps.core.services.totp_service import CIFRE, PERIODO_SECONDI


# Scopo: Un avviso a chi guarda: sul terminale, perche' gli smoke lanciano il
#        login con `2>/dev/null` e lo standard error andrebbe perso.
def _avvisa(testo: str) -> None:
    try:
        with open("/dev/tty", "w", encoding="utf-8") as tty:
            print(testo, file=tty)
    except OSError:
        print(testo, file=sys.stderr)


# Scopo: Il codice di un passo nuovo per il segreto dato; aspetta se serve.
def codice_nuovo(segreto: str) -> str:
    impronta = hashlib.sha256(segreto.encode()).hexdigest()[:12]
    stato = Path(tempfile.gettempdir()) / f"zeroerp-smoke-totp-{impronta}.passo"
    with open(stato, "a+", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        letto = f.read().strip()
        ultimo = int(letto) if letto.isdigit() else -1
        passo = int(time.time() // PERIODO_SECONDI)
        if passo <= ultimo:
            attesa = (ultimo + 1) * PERIODO_SECONDI - time.time() + 0.5
            _avvisa(f"  (secondo fattore: attendo {attesa:.0f}s il codice nuovo)")
            time.sleep(max(attesa, 0))
            passo = ultimo + 1
        f.seek(0)
        f.truncate()
        f.write(str(passo))
        return pyotp.TOTP(segreto, digits=CIFRE, interval=PERIODO_SECONDI).generate_otp(passo)


# La chiave che la pagina Sicurezza mostra: `totp_service.nuovo_segreto`, 32
# caratteri base32 (160 bit). ⚠️ Una chiave TRONCATA pyotp la accetta e produce
# codici sbagliati, che il server rifiuta come «codice non valido»: si
# controlla la forma prima, e si dice cosa non va.
_FORMA_CHIAVE = re.compile(r"^[A-Z2-7]{32}$")


# Scopo: Perche' la chiave non e' quella della pagina Sicurezza, o None.
def difetto_della_chiave(segreto: str) -> str | None:
    if _FORMA_CHIAVE.match(segreto):
        return None
    if "-" in segreto:
        return "sembra un codice di recupero: serve la CHIAVE mostrata sotto il QR"
    if re.search(r"[^A-Z2-7]", segreto):
        return "contiene caratteri che una chiave non ha (solo lettere A-Z e cifre 2-7)"
    return f"e' lunga {len(segreto)} caratteri invece di 32: forse copiata a meta'"


if __name__ == "__main__":
    segreto = "".join(os.environ.get("SMOKE_TOTP_SECRET", "").split()).upper()
    if not segreto:
        _avvisa(
            "SMOKE_TOTP_SECRET assente: il login chiede il secondo fattore. Passa la "
            "chiave mostrata alla configurazione (pagina Sicurezza)."
        )
        sys.exit(2)
    difetto = difetto_della_chiave(segreto)
    if difetto:
        _avvisa(f"SMOKE_TOTP_SECRET non valida: {difetto}.")
        sys.exit(2)
    try:
        print(codice_nuovo(segreto))
    except Exception as exc:  # qualunque guasto va DETTO: gli smoke buttano lo stderr
        _avvisa(f"Codice del secondo fattore non calcolato: {exc!r}")
        sys.exit(2)
