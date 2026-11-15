# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: COME IL CARICATORE LIQUIBASE SCRIVE UNA CELLA di un CSV di seed, in un
#        posto solo: lo leggono i test senza DB (il BB `seed_csv`,
#        `backend/apps/core/tests/_seed_csv.py`) e il generatore dei seed delle
#        liste (`scripts/gen_seed_lista.py`, che confronta CSV e DB).
# Note: ⭐ LA REGOLA (Liquibase 5.0.4, misurata il 2026-11-12 sul bytecode e col
#        render offline: brief-db-token-null-dei-seed §1):
#        * la cella che in minuscolo vale `null` (anche fra virgolette) e' NULL
#          su ogni colonna e in ogni file;
#        * la cella vuota e' `''` sulla colonna dichiarata `type: STRING`, il
#          `defaultValue` se la colonna ne dichiara uno, NULL su ogni altra
#          colonna, dichiarata o no.
#        ⛔ `nullValue:` NON ESISTE per Liquibase: lo ignora senza errore. Il
#        token e' uno solo; cio' che cambia da colonna a colonna e' la
#        DICHIARAZIONE nel caricatore, e si legge da li'.
#        ⭐ Estratto il 2026-11-13 (regola del 2, ok Tid): la stessa lettura
#        serviva al BB dei test e a `confronta()` del generatore, che
#        confrontava le celle come stringhe e su un token diverso fra CSV e DB
#        avrebbe dato ogni riga per divergente.
#        ⚠️ Senza dipendenze dagli altri moduli di `scripts/` e da Django: lo
#        caricano per percorso sia il backend (dove `scripts/` non e' sul path)
#        sia il generatore, che a sua volta il backend carica per percorso.
# ------------------------------------------------------------

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG_DIR = ROOT / "db/changelog"

# Il token dell'assenza che i CSV scrivono (la convenzione: maiuscolo). Il
# caricatore riconosce ogni grafia, chi scrive usa questa.
NULLO = "NULL"

# Le dichiarazioni di un caricatore: coppie (intestazione, cella vuota),
# ordinate per intestazione.
Dichiarazioni = tuple[tuple[str, "str | None"], ...]


# Scopo: la cella vuota di UNA colonna dichiarata in `columns:`, e la sua
#        intestazione nel CSV (`header`, se c'e', altrimenti `name`).
def vuota_della_colonna(colonna: dict) -> tuple[str, str | None]:
    intestazione = str(colonna.get("header") or colonna.get("name"))
    if "defaultValue" in colonna:
        return intestazione, str(colonna["defaultValue"])
    if str(colonna.get("type", "")).upper() == "STRING":
        return intestazione, ""
    return intestazione, None


# Scopo: per ogni caricatore (`loadData` / `loadUpdateData`) che legge
#        `percorso`, le sue dichiarazioni. Si parsano solo gli YAML che
#        nominano il file; una scansione per file e per processo.
@lru_cache(maxsize=None)
def caricatori(percorso: Path) -> tuple[Dichiarazioni, ...]:
    trovati: set[Dichiarazioni] = set()

    def visita(nodo: object, changelog: Path) -> None:
        if isinstance(nodo, dict):
            for chiave, valore in nodo.items():
                if chiave in ("loadData", "loadUpdateData") and isinstance(valore, dict):
                    file = valore.get("file")
                    if file and valore.get("relativeToChangelogFile"):
                        letto = (changelog.parent / file).resolve()
                    else:
                        letto = (CHANGELOG_DIR / str(file)).resolve()
                    if letto == percorso:
                        colonne = [
                            vuota_della_colonna(voce["column"])
                            for voce in (valore.get("columns") or ())
                            if isinstance(voce, dict) and isinstance(voce.get("column"), dict)
                        ]
                        trovati.add(tuple(sorted(colonne, key=lambda c: c[0])))
                visita(valore, changelog)
        elif isinstance(nodo, list):
            for elemento in nodo:
                visita(elemento, changelog)

    for changelog in CHANGELOG_DIR.rglob("*.yaml"):
        testo = changelog.read_text(encoding="utf-8")
        if percorso.name in testo:
            visita(yaml.safe_load(testo), changelog)
    return tuple(sorted(trovati, key=repr))


# Scopo: la cella vuota di ogni colonna dichiarata da almeno un caricatore di
#        `percorso`; una colonna che nessuno dichiara ha la vuota NULL.
# ⛔ SOLLEVA dove non c'e' una risposta sola: nessun caricatore, o due
#    caricatori che danno alla cella vuota della stessa colonna un valore
#    diverso. Chi NON dichiara una colonna le da' la vuota NULL: se un altro
#    caricatore la dichiara STRING, la stessa cella vuota diventa NULL o `''`
#    secondo chi e' passato per ultimo, e qui non si sceglie al posto loro.
def celle_vuote(percorso: Path) -> dict[str, str | None]:
    percorso = percorso.resolve()
    dichiarazioni = caricatori(percorso)
    if not dichiarazioni:
        raise AssertionError(f"{percorso}: nessun caricatore Liquibase lo legge")
    nomi = {n for colonne in dichiarazioni for n, _ in colonne}
    per_colonna: dict[str, set[str | None]] = {n: set() for n in nomi}
    for colonne in dichiarazioni:
        dichiarate = dict(colonne)
        for nome in nomi:
            per_colonna[nome].add(dichiarate.get(nome))
    in_disaccordo = {n: v for n, v in per_colonna.items() if len(v) > 1}
    if in_disaccordo:
        dettaglio = {n: sorted(map(repr, v)) for n, v in sorted(in_disaccordo.items())}
        raise AssertionError(
            f"{percorso}: i caricatori non dicono la stessa cosa sulla cella "
            f"vuota di {sorted(in_disaccordo)} ({dettaglio}). "
            "Si allineano le dichiarazioni `columns:` dei caricatori."
        )
    return {n: next(iter(v)) for n, v in per_colonna.items()}


# Scopo: una cella come la scrive il caricatore, data la vuota della colonna
#        (`None` se la colonna non e' dichiarata).
def leggi_cella(valore: str | None, vuota: str | None) -> str | None:
    # `None` e' la cella che manca alla riga corta (`csv.DictReader`).
    if valore is None or valore.lower() == "null":
        return None
    if valore == "":
        return vuota
    return valore
