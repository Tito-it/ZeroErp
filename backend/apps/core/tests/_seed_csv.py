# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La LETTURA UNICA dei CSV di seed di `80_data/sql/` per i test senza DB:
#        ogni cella arriva come la scrive il caricatore Liquibase del file,
#        `None` dove scrive NULL e `''` dove scrive la stringa vuota.
# Note: ⭐ LA REGOLA del caricatore sta in `scripts/_seed_csv_caricatori.py`,
#        condivisa col generatore dei seed delle liste (regola del 2, ok Tid
#        2026-11-13): `null` in ogni grafia e' NULL; la cella vuota e' `''`
#        sulla colonna `type: STRING`, il `defaultValue` dove c'e', NULL
#        altrove (brief-db-token-null-dei-seed §1).
#        ⛔ `nullValue:` NON ESISTE per Liquibase: la prima stesura di questo BB
#        lo leggeva come token per file (`token_nullo`, il descrittore `nullo`
#        di `CSV_SEED`), ed e' ritirata.
#        ⛔ Un `csv.DictReader` nudo da' `'NULL'`, che e' VERO in un test di
#        verita' (`if r["campo_sorgente"]`), e `''` dove il DB ha NULL
#        (2026-11-12, brief-db-lista-colonna-campo-sorgente-null §5.1).
#        ⭐ Estratto il 2026-11-12 (regola del 2, ok Tid): `_seed()` era scritta
#        in due test, il CSV delle liste si leggeva anche in linea, e due helper
#        fuori da `ui` (`_contratto_processi`, `test_event_codes_declared_guardrail`)
#        riconoscevano il token a mano, ognuno a modo suo. Riscritto sulla
#        regola vera il 2026-11-13 (brief-db-token-null-dei-seed §6).
# ------------------------------------------------------------

from __future__ import annotations

import csv
import importlib.util
from functools import lru_cache
from pathlib import Path
from types import ModuleType

from apps.core.tests._repo import repo_root

SEED_DIR = repo_root() / "db/changelog/migrations_v2/80_data/sql"
SEED_UI_DIR = SEED_DIR / "ui"

# La riga di un CSV di seed: `None` dove il caricatore scrive NULL.
RigaSeed = dict[str, "str | None"]

# Scopo: un modulo di `scripts/`, importato per percorso.
# ⚠️ Per percorso e non `from scripts...`: `scripts/` non e' un package e non
#    sta sul path del runner Django. I moduli sono senza stato (costanti e
#    funzioni pure, le cache sono per processo), quindi una istanza sola basta.
@lru_cache(maxsize=None)
def _modulo_script(nome: str) -> ModuleType:
    sorgente = repo_root() / "scripts" / f"{nome}.py"
    spec = importlib.util.spec_from_file_location(f"_script_{nome}", sorgente)
    if spec is None or spec.loader is None:
        raise AssertionError(f"{sorgente}: modulo non importabile")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


# Scopo: il generatore dei CSV di seed delle liste.
def generatore_seed_lista() -> ModuleType:
    return _modulo_script("gen_seed_lista")


# Scopo: la regola del caricatore, nella sua sede unica
#        (`scripts/_seed_csv_caricatori.py`, condivisa col generatore).
def caricatori_seed() -> ModuleType:
    return _modulo_script("_seed_csv_caricatori")


# Scopo: la cella vuota di ogni colonna dichiarata dai caricatori del file
#        (vedi `celle_vuote` nella sede unica: solleva se non c'e' una
#        risposta sola).
def celle_vuote(percorso: Path) -> dict[str, str | None]:
    return caricatori_seed().celle_vuote(percorso)


# Scopo: le righe di un CSV di seed come le scrive il suo caricatore: `None`
#        dove scrive NULL, `''` dove scrive la stringa vuota. `percorso` e'
#        relativo a `80_data/sql/` (`"dbops/processi.csv"`) o assoluto.
# ⚠️ Ogni chiamata rilegge il file e da' dict NUOVI: le righe non si mettono in
#    cache, perche' un consumatore che ne modifica una cambierebbe il seed
#    visto da tutti gli altri test del processo.
def seed_csv(percorso: str | Path) -> list[RigaSeed]:
    file = SEED_DIR / percorso
    vuote = celle_vuote(file)
    leggi = caricatori_seed().leggi_cella
    with file.open(newline="", encoding="utf-8") as fh:
        return [
            {campo: leggi(valore, vuote.get(campo)) for campo, valore in riga.items()}
            for riga in csv.DictReader(fh)
        ]


# Scopo: le righe di un CSV di seed delle liste configurabili (cartella `ui`).
def seed_ui(nome: str) -> list[RigaSeed]:
    return seed_csv(SEED_UI_DIR / nome)


# Scopo: id della lista dal suo codice, dal seed (il seed puo' rinumerare: chi
#        lo usa segue, invece di cablare un id).
def seed_lista_id(codice: str) -> str:
    for riga in seed_ui("lista_definizione.csv"):
        if riga["codice"] == codice and riga["id"] is not None:
            return riga["id"]
    raise AssertionError(f"lista '{codice}' assente da lista_definizione.csv")


# Scopo: colonne ATTIVE del catalogo di una lista. Le disattivate non arrivano a
#        video (`fn_resolve_lista_config` le esclude), quindi i loro flag non
#        dicono nulla sul contratto lista<->backend.
# ⭐ Spostate qui il 2026-11-12 da `test_liste_configurabili_seed`, dove erano
#    nomi privati importati da test di altre app.
def seed_colonne_attive(codice: str) -> list[RigaSeed]:
    lista_id = seed_lista_id(codice)
    return [
        r for r in seed_ui("lista_colonna.csv")
        if r["lista_id"] == lista_id and r["attivo"] == "t"
    ]
