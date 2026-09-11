# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La root del repo per i test che leggono FILE del progetto (seed CSV,
#        sorgenti, template): si risale fino a `db/changelog` invece di contare
#        i livelli a mano.
# Note: ⛔ `parents[N]` si rompe in silenzio se il file si sposta: non fallisce,
#        trova zero file e il test passa **a vuoto** — il verde per sottrazione,
#        che su un presidio che deve accorgersi di cio' che MANCA e' il difetto
#        peggiore possibile. Risalire fino a un marcatore del repo non ha questo
#        modo di sbagliare: o lo trova, o solleva.
#        ⭐ Estratto il 2026-09-11 (regola del 2, superata da un pezzo): la
#        stessa funzione era scritta identica in OTTO file di test.
# ------------------------------------------------------------

from __future__ import annotations

from pathlib import Path


# Scopo: root del repo, o AssertionError se questo file non sta dentro al repo.
def repo_root() -> Path:
    for cartella in Path(__file__).resolve().parents:
        if (cartella / "db" / "changelog").is_dir():
            return cartella
    raise AssertionError("root del repo non trovata (nessun db/changelog risalendo)")
