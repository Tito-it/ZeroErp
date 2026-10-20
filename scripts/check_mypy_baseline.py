#!/usr/bin/env python3
# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: CANCELLO DEL TYPE CHECKER DEL BACKEND, a cricchetto (piano-be-type-
#        checker, L1, 2026-10-08). Lancia mypy sul perimetro di
#        `backend/mypy.ini` e confronta i rilievi con il registro
#        `backend/mypy.baseline.json`, che elenca l'arretrato accettato.
# Note: va lanciato con il Python della VENV DEL BACKEND (il plugin Django
#       importa settings e codice del progetto) e con l'ambiente Django
#       caricato (le variabili che le settings pretendono):
#           cd backend && set -a && . ./env.sh && set +a
#           .venv/bin/python ../scripts/check_mypy_baseline.py
#
# ROSSO in tre casi, e solo in quelli:
#   1. un rilievo NUOVO — il codice nuovo nasce pulito;
#   2. un rilievo del registro che NON C'E' PIU' — sanato e non tolto: il
#      registro deve scendere, non restare largo a coprire ricadute future.
#      `--aggiorna` lo riscrive togliendo le voci sanate, e SOLO togliendo;
#   3. un'uscita di mypy che lo script NON SA LEGGERE (crash, configurazione
#      rotta, riga non JSON): «verde perche' non ha capito niente» e' la forma
#      piu' pericolosa di verde.
#
# ⭐ LA CHIAVE E' PER NOME, NON PER RIGA: file + codice (`arg-type`) +
#    messaggio, con un conteggio. Un registro con i numeri di riga diventa rosso
#    per una riga vuota aggiunta sopra il punto, e chi lo riscrive per farlo
#    tacere riscrive anche i rilievi veri. Stesso principio di
#    `apps/core/tests/test_schema_openapi_registro.py`.
# ⚠️ LIMITE DICHIARATO: due rilievi identici nello stesso file sono la stessa
#    chiave col conteggio 2. Se uno si sana e un altro identico nasce altrove
#    nello stesso file, il conteggio non cambia e il cancello non lo vede.
#
# ⛔ `--rigenera` riscrive il registro DA ZERO, quindi anche aggiungendo. Si usa
#    solo con una decisione (la nascita del registro, un cambio di versione di
#    mypy o degli stub), e il diff del registro lo mostra a chi rivede.
# ------------------------------------------------------------
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
BACKEND = RADICE / "backend"
REGISTRO = BACKEND / "mypy.baseline.json"

# Le chiavi che ogni riga dell'uscita JSON di mypy deve avere: una che manca e'
# un'uscita che lo script non sa leggere (caso 3), non un rilievo da ignorare.
_CHIAVI_RIGA = ("file", "message", "code", "severity")

# Un riferimento di riga dentro il messaggio («already defined on line 45»)
# sposterebbe la chiave a ogni modifica sopra il punto.
_RIF_RIGA = re.compile(r"\bline \d+\b")

_SCOPO = (
    "Registro a cricchetto del type checker (mypy) del backend: i rilievi "
    "ACCETTATI, per file, chiave «[codice] messaggio» e conteggio. Deve solo "
    "scendere. Lo legge e lo riscrive scripts/check_mypy_baseline.py; il perche' "
    "sta in docs/it/dev/sicurezza-e-qualita-statica.md §mypy."
)


class UscitaIlleggibile(Exception):
    """mypy ha risposto qualcosa che non e' un elenco di rilievi."""


# Scopo: lancia mypy dalla cartella del backend (legge `mypy.ini` da li') e
#        ritorna i rilievi come Counter di (file, chiave). Solleva
#        UscitaIlleggibile su qualunque cosa non sia «zero o piu' rilievi».
def rileva() -> Counter[tuple[str, str]]:
    esito = subprocess.run(
        [sys.executable, "-m", "mypy", "--output", "json"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    # mypy: 0 = nessun rilievo, 1 = rilievi, 2 = errore suo (configurazione,
    # crash, import del plugin). Il 2 non e' «tanti rilievi»: e' «non ho guardato».
    if esito.returncode not in (0, 1):
        raise UscitaIlleggibile(
            f"mypy e' uscito con {esito.returncode}:\n{esito.stderr or esito.stdout}"
        )
    rilievi: Counter[tuple[str, str]] = Counter()
    for numero, riga in enumerate(esito.stdout.splitlines(), start=1):
        if not riga.strip():
            continue
        try:
            dato = json.loads(riga)
        except json.JSONDecodeError as exc:
            raise UscitaIlleggibile(f"riga {numero} non JSON: {riga!r}") from exc
        if not isinstance(dato, dict) or any(k not in dato for k in _CHIAVI_RIGA):
            raise UscitaIlleggibile(f"riga {numero} senza {_CHIAVI_RIGA}: {riga!r}")
        if dato["severity"] != "error":
            continue
        messaggio = _RIF_RIGA.sub("line N", str(dato["message"]))
        rilievi[(str(dato["file"]), f"[{dato['code']}] {messaggio}")] += 1
    # Exit 1 senza nessun rilievo letto: mypy ha detto «trovato qualcosa» e
    # noi non l'abbiamo visto. Non e' un verde.
    if esito.returncode == 1 and not rilievi:
        raise UscitaIlleggibile(
            f"mypy e' uscito con 1 ma nessun rilievo letto:\n{esito.stderr}"
        )
    return rilievi


def leggi_registro() -> Counter[tuple[str, str]]:
    if not REGISTRO.exists():
        return Counter()
    dati = json.loads(REGISTRO.read_text(encoding="utf-8"))
    registro: Counter[tuple[str, str]] = Counter()
    for file, voci in dati.get("rilievi", {}).items():
        for chiave, conteggio in voci.items():
            registro[(file, chiave)] = int(conteggio)
    return registro


def scrivi_registro(registro: Counter[tuple[str, str]]) -> None:
    per_file: dict[str, dict[str, int]] = {}
    for (file, chiave), conteggio in sorted(registro.items()):
        if conteggio > 0:
            per_file.setdefault(file, {})[chiave] = conteggio
    REGISTRO.write_text(
        json.dumps(
            {"_scopo": _SCOPO, "totale": sum(registro.values()), "rilievi": per_file},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _stampa(titolo: str, voci: Counter[tuple[str, str]]) -> None:
    print(f"\n{titolo} ({sum(voci.values())}):")
    for (file, chiave), conteggio in sorted(voci.items()):
        print(f"  {file}: {chiave}" + (f"  (x{conteggio})" if conteggio > 1 else ""))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    gruppo = parser.add_mutually_exclusive_group()
    gruppo.add_argument(
        "--aggiorna", action="store_true",
        help="toglie dal registro le voci sanate (solo togliere: mai aggiungere)",
    )
    gruppo.add_argument(
        "--rigenera", action="store_true",
        help="riscrive il registro DA ZERO con i rilievi di oggi (decisione esplicita)",
    )
    args = parser.parse_args()

    try:
        attuali = rileva()
    except UscitaIlleggibile as exc:
        print(f"ROSSO — uscita di mypy illeggibile, nessun giudizio possibile.\n{exc}")
        return 2

    if args.rigenera:
        scrivi_registro(attuali)
        print(f"Registro riscritto da zero: {sum(attuali.values())} rilievi in {REGISTRO}")
        return 0

    registro = leggi_registro()
    nuovi = attuali - registro
    sanati = registro - attuali

    if args.aggiorna:
        if nuovi:
            _stampa("ROSSO — rilievi NUOVI: --aggiorna non li accetta", nuovi)
            return 1
        scrivi_registro(registro - sanati)
        print(f"Registro aggiornato: tolte {sum(sanati.values())} voci sanate.")
        return 0

    rosso = False
    if nuovi:
        _stampa("ROSSO — rilievi NUOVI (il codice nuovo nasce pulito)", nuovi)
        rosso = True
    if sanati:
        _stampa(
            "ROSSO — rilievi SANATI ma ancora nel registro "
            "(togli le voci: scripts/check_mypy_baseline.py --aggiorna)",
            sanati,
        )
        rosso = True
    if rosso:
        return 1
    print(
        f"mypy: {sum(attuali.values())} rilievi, tutti nel registro "
        f"({REGISTRO.relative_to(RADICE)}). Nessuno nuovo, nessuno sanato da togliere."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
