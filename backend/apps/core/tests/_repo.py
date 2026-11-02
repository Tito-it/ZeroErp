# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La root del repo per i test che leggono FILE del progetto (seed CSV,
#        sorgenti, template): si risale fino a `db/changelog` invece di contare
#        i livelli a mano. E, per gli stessi test, il sorgente RIPULITO DAI
#        COMMENTI: un presidio che cerca una stringa in un file si accende sulla
#        prosa che spiega il difetto, ed e' successo (2026-08-26,
#        `test_liste_configurabili_seed`).
# Note: ⛔ `parents[N]` si rompe in silenzio se il file si sposta: non fallisce,
#        trova zero file e il test passa **a vuoto** — il verde per sottrazione,
#        che su un presidio che deve accorgersi di cio' che MANCA e' il difetto
#        peggiore possibile. Risalire fino a un marcatore del repo non ha questo
#        modo di sbagliare: o lo trova, o solleva.
#        ⭐ Estratto il 2026-09-11 (regola del 2, superata da un pezzo): la
#        stessa funzione era scritta identica in OTTO file di test.
# ------------------------------------------------------------

from __future__ import annotations

import re
from pathlib import Path


# Scopo: sorgente senza le righe di commento — `#` (Python) e `--` (SQL dentro
#        le stringhe delle query), solo a inizio riga, che e' come sono scritte.
# ⭐ Estratta il 2026-09-13 (regola del 2, superata): viveva in TRE test in due
#    forme diverse — una toglieva solo `#`, e un test che scandisce repository
#    con SQL dentro si sarebbe acceso su un `-- commento` che cita la forma
#    vietata. Qui c'e' la forma larga, che per un file Python puro e' innocua.
def sorgente_senza_commenti(testo: str) -> str:
    senza_py = re.sub(r"^[ \t]*#.*$", "", testo, flags=re.M)
    return re.sub(r"^[ \t]*--.*$", "", senza_py, flags=re.M)


# Scopo: root del repo, o AssertionError se questo file non sta dentro al repo.
def repo_root() -> Path:
    for cartella in Path(__file__).resolve().parents:
        if (cartella / "db" / "changelog").is_dir():
            return cartella
    raise AssertionError("root del repo non trovata (nessun db/changelog risalendo)")
