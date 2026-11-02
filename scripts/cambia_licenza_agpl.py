#!/usr/bin/env python3
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Passaggio delle intestazioni di licenza da GPL-3.0-or-later ad
#        AGPL-3.0-or-later (cambio di licenza del 2026-11-02).
# Note: Senza argomenti MISURA soltanto; con --applica scrive.
# ------------------------------------------------------------
#
# ⭐ Lavora SOLO sui file tracciati da git (`git ls-files`): node_modules,
#    site/, venv e simili restano fuori senza doverli elencare.
# ⭐ Lavora sui BYTE: fine riga CRLF, codifica e permessi restano intatti.
# ⛔ Salta i link simbolici: riscriverli li trasformerebbe in file normali.
# ⭐ Idempotente: le due sostituzioni non trovano piu' niente nei file gia'
#    passati (`GNU AGPLv3` non contiene `GNU GPLv3`).
#
# ✅ Sicuro sui changeSet Liquibase: verificato il 2026-11-02 che in tutti i
#    changelog YAML l'intestazione sta PRIMA di `databaseChangeLog:`, cioe' in
#    un commento che non entra nel checksum; i file SQL caricati con `sqlFile`
#    non hanno intestazione di licenza.

import os
import subprocess
import sys

SOSTITUZIONI = [
    (b"SPDX-License-Identifier: GPL-3.0-or-later", b"SPDX-License-Identifier: AGPL-3.0-or-later"),
    (b"GNU GPLv3", b"GNU AGPLv3"),
]

# I testi completi della licenza, la storia dei brief chiusi e questo script.
ESCLUSI_PREFISSI = ("docs/it/dev/work-done/",)
ESCLUSI_FILE = {
    "LICENSE",
    "docs/it/LICENSE.md",
    "docs/en/LICENSE.md",
    "docs/it/LICENSE-AGPL3.md",
    "scripts/cambia_licenza_agpl.py",
}


def file_tracciati() -> list[str]:
    out = subprocess.check_output(["git", "ls-files", "-z"])
    return [p for p in out.decode("utf-8").split("\0") if p]


def main() -> int:
    applica = "--applica" in sys.argv[1:]
    radice = subprocess.check_output(["git", "rev-parse", "--show-toplevel"]).decode().strip()
    os.chdir(radice)

    toccati = 0
    conteggi = [0] * len(SOSTITUZIONI)
    for percorso in file_tracciati():
        if percorso in ESCLUSI_FILE or percorso.startswith(ESCLUSI_PREFISSI):
            continue
        if os.path.islink(percorso) or not os.path.isfile(percorso):
            continue
        with open(percorso, "rb") as f:
            dati = f.read()
        if b"\0" in dati[:8192]:
            continue  # binario
        nuovi = dati
        for i, (vecchio, nuovo) in enumerate(SOSTITUZIONI):
            n = nuovi.count(vecchio)
            if n:
                conteggi[i] += n
                nuovi = nuovi.replace(vecchio, nuovo)
        if nuovi != dati:
            toccati += 1
            if applica:
                with open(percorso, "wb") as f:
                    f.write(nuovi)

    modo = "APPLICATO" if applica else "MISURA (nessun file scritto; --applica per scrivere)"
    print(f"{modo}: {toccati} file")
    for (vecchio, nuovo), n in zip(SOSTITUZIONI, conteggi, strict=True):
        print(f"  {n:6d} × {vecchio.decode()} → {nuovo.decode()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
