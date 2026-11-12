# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La LETTURA UNICA dei CSV di seed di `80_data/sql/` per i test senza DB:
#        ogni cella che il loader Liquibase di quel file scrive come NULL
#        arriva qui come `None`, non come la stringa del token.
# Note: ⛔ Il token NON e' lo stesso per tutti i file (`nullValue: "NULL"` o
#        `nullValue: ""`). Un `csv.DictReader` nudo da' `'NULL'`, che e' VERO in
#        un test di verita' (`if r["campo_sorgente"]`): un presidio cosi' cerca
#        il campo `NULL` nella riga, prende `'NULL'` per un formato o per una
#        data. E' successo il 2026-11-12, quando `lista_colonna.csv` e' passato
#        al token (brief-db-lista-colonna-campo-sorgente-null §5.1, K-1 … K-3).
#        ⛔ E la cella vuota NON e' NULL dove il token e' `"NULL"`: il loader la
#        scrive come stringa vuota, e un lettore che le confonde crede che a DB
#        ci sia NULL dove c'e' `''` (il difetto che il guardrail `nullvalue-vuoto`
#        caccia lato DB). Qui arriva `''`, come la vede il database.
#        ⭐ Il token si legge dal `nullValue` del CARICATORE del file (gli YAML
#        sotto `db/changelog`), che e' la fonte vera. Un file con piu'
#        caricatori e token diversi (oggi `lista_colonna.csv`: il seed del
#        2026-05 con `""`, il mirror con `"NULL"`) si decide col descrittore
#        `CSV_SEED` di `scripts/gen_seed_lista.py`, la sede di chi SCRIVE i CSV
#        delle liste; fuori da li' il BB solleva, invece di indovinare.
#        ⭐ Estratto il 2026-11-12 (regola del 2, ok Tid): `_seed()` era scritta
#        in due test, il CSV delle liste si leggeva anche in linea, e due helper
#        fuori da `ui` (`_contratto_processi`, `test_event_codes_declared_guardrail`)
#        riconoscevano il token a mano, ognuno a modo suo.
# ------------------------------------------------------------

from __future__ import annotations

import csv
import importlib.util
from functools import lru_cache
from pathlib import Path
from types import ModuleType

import yaml

from apps.core.tests._repo import repo_root

SEED_DIR = repo_root() / "db/changelog/migrations_v2/80_data/sql"
SEED_UI_DIR = SEED_DIR / "ui"

# La riga di un CSV di seed: `None` dove il loader scrive NULL.
RigaSeed = dict[str, "str | None"]

# Un caricatore senza `nullValue`: non si assume il default di Liquibase.
_TOKEN_ASSENTE = object()


# Scopo: il generatore dei CSV di seed delle liste, importato per percorso.
# ⚠️ Per percorso e non `from scripts...`: `scripts/` non e' un package e non
#    sta sul path del runner Django. Il modulo e' senza stato (costanti e
#    funzioni pure), quindi una istanza sola per processo basta.
@lru_cache(maxsize=1)
def generatore_seed_lista() -> ModuleType:
    sorgente = repo_root() / "scripts" / "gen_seed_lista.py"
    spec = importlib.util.spec_from_file_location("_gen_seed_lista", sorgente)
    if spec is None or spec.loader is None:
        raise AssertionError(f"{sorgente}: generatore dei seed non importabile")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


# Scopo: i `nullValue` dei caricatori (`loadData` / `loadUpdateData`) che
#        leggono `percorso`, come insieme (`_TOKEN_ASSENTE` per chi non lo
#        dichiara). Si parsano solo gli YAML che nominano il file.
@lru_cache(maxsize=None)
def _token_dei_caricatori(percorso: Path) -> frozenset[object]:
    trovati: set[object] = set()

    def visita(nodo: object, changelog: Path) -> None:
        if isinstance(nodo, dict):
            for chiave, valore in nodo.items():
                if chiave in ("loadData", "loadUpdateData") and isinstance(valore, dict):
                    file = valore.get("file")
                    if file and valore.get("relativeToChangelogFile"):
                        letto = (changelog.parent / file).resolve()
                    else:
                        letto = (repo_root() / "db/changelog" / str(file)).resolve()
                    if letto == percorso:
                        trovati.add(valore.get("nullValue", _TOKEN_ASSENTE))
                visita(valore, changelog)
        elif isinstance(nodo, list):
            for elemento in nodo:
                visita(elemento, changelog)

    for changelog in (repo_root() / "db/changelog").rglob("*.yaml"):
        testo = changelog.read_text(encoding="utf-8")
        if percorso.name in testo:
            visita(yaml.safe_load(testo), changelog)
    return frozenset(trovati)


# Scopo: il token che il loader di `percorso` interpreta come NULL.
# ⛔ SOLLEVA dove non c'e' una risposta sola: nessun caricatore, un caricatore
#    senza `nullValue`, piu' caricatori in disaccordo senza un descrittore che
#    decida. Indovinare il token e' esattamente il difetto che questo modulo
#    chiude.
def token_nullo(percorso: Path) -> str:
    percorso = percorso.resolve()
    dei_caricatori = _token_dei_caricatori(percorso)
    if not dei_caricatori:
        raise AssertionError(f"{percorso}: nessun caricatore Liquibase lo legge")
    descrittori = generatore_seed_lista().CSV_SEED
    if percorso.parent == SEED_UI_DIR.resolve() and percorso.name in descrittori:
        dichiarato: str = descrittori[percorso.name]["nullo"]
        # Il descrittore del generatore e i caricatori devono dire la stessa
        # cosa: se divergono, il generatore scrive celle che il mirror legge
        # in un altro modo.
        if dichiarato not in dei_caricatori:
            raise AssertionError(
                f"{percorso.name}: `CSV_SEED` dichiara il token {dichiarato!r}, "
                f"che nessun caricatore usa ({sorted(map(repr, dei_caricatori))})"
            )
        return dichiarato
    if len(dei_caricatori) > 1 or _TOKEN_ASSENTE in dei_caricatori:
        raise AssertionError(
            f"{percorso}: il token NULL non ha una risposta sola nei caricatori "
            f"({sorted(map(repr, dei_caricatori))}). Si dichiara `nullValue` nel "
            "caricatore, o si aggiunge un descrittore che decida."
        )
    (token,) = dei_caricatori
    # ⛔ Un `nullValue:` senza valore e' `None` per YAML, non un token: non si
    #    confronta con le celle, si rifiuta.
    if not isinstance(token, str):
        raise AssertionError(
            f"{percorso}: `nullValue` del caricatore non e' una stringa ({token!r})"
        )
    return token


# Scopo: le righe di un CSV di seed, con `None` al posto del token NULL del suo
#        loader. `percorso` e' relativo a `80_data/sql/` (`"dbops/processi.csv"`)
#        o assoluto.
# ⚠️ Ogni chiamata rilegge il file e da' dict NUOVI: le righe non si mettono in
#    cache, perche' un consumatore che ne modifica una cambierebbe il seed
#    visto da tutti gli altri test del processo.
def seed_csv(percorso: str | Path) -> list[RigaSeed]:
    file = SEED_DIR / percorso
    nullo = token_nullo(file)
    with file.open(newline="", encoding="utf-8") as fh:
        return [
            {campo: (None if valore == nullo else valore) for campo, valore in riga.items()}
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
