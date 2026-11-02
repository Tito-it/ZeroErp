# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Helper condivisi per parametri SQL write con cast espliciti.
# ------------------------------------------------------------

from __future__ import annotations

import json
import re
from collections.abc import Collection, Mapping
from typing import Any
from uuid import UUID

from django.db import connection

from apps.core.db._helpers import row_to_dict

# Un nome di colonna che finisce interpolato nel testo SQL: minuscole, cifre e
# underscore, come ogni colonna del modello. E' il controllo che resta anche
# quando il chiamante dichiara `allowed=None` (chiavi letterali del metodo).
_IDENTIFICATORE = re.compile(r"^[a-z_][a-z0-9_]*$")

# Il nome di un TIPO che finisce interpolato come cast (`%s::<tipo>`): un
# identificatore, eventualmente qualificato dallo schema (`ui.tipo_colonna`),
# eventualmente ARRAY (`text[]`, dal 2026-09-26). E' un literal del chiamante,
# ma entra nel testo SQL: si verifica comunque, come i nomi di colonna.
_TIPO_QUALIFICATO = re.compile(r"^[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)?(\[\])?$")


# ⛔ `to_write_param`/`sql_placeholder` RITIRATI il 2026-09-26 (migrazione
#    D2): facevano sempre `json.dumps` su una colonna jsonb, quindi una
#    stringa diventava uno SCALARE stringa — l'opposto della regola unica qui
#    sotto, per cui una stringa su una colonna jsonb dichiarata e' TESTO JSON
#    (decisione Tid). Due regole nello stesso file davano allo stesso `meta`
#    due forme in due tabelle.


# Scopo: La regola UNICA con cui un valore Python diventa (segnaposto,
#        parametro) in una scrittura dinamica — la usano UPDATE, SET e INSERT
#        qui sotto, e sta in un posto solo perche' tre copie divergerebbero
#        alla prima colonna jsonb nuova.
#        - colonna in `casts` -> `%s::<tipo>` (enum e simili, es.
#          `ui.tipo_colonna`); il PARAMETRO segue le regole qui sotto
#          (dict/list serializzati, stringhe strip);
#        - dict/list  -> `%s::jsonb` + `json.dumps` (convenzione del BB UPDATE);
#        - colonna in `jsonb` -> `%s::jsonb` col valore COSI' COM'E': e' la
#          convenzione dei moduli che serializzano gia' nel service (pagamenti).
#          ⚠️ Una stringa li' e' testo JSON, non uno scalare stringa: se non e'
#          JSON valido PostgreSQL rifiuta — l'errore si vede, non si maschera;
#        - stringa -> `strip()`, SALVO le colonne in `letterali` (dal
#          2026-09-26): corpo di un template HTML/CSS, prefisso di una
#          numerazione — dove uno spazio ai bordi e' contenuto, non rumore;
#        - il resto -> `%s` invariato (None compreso: diventa NULL).
#        ⭐ Cast ARRAY (`casts={"destinatari_cc": "text[]"}`, dal 2026-09-26):
#        la lista passa COSI' COM'E' e psycopg la adatta ad array. Senza, una
#        lista sarebbe finita serializzata in JSON, cioe' nel tipo sbagliato.
def _segnaposto_e_parametro(
    col: str,
    val: Any,
    jsonb: Collection[str] = (),
    casts: Mapping[str, str] | None = None,
    letterali: Collection[str] = (),
) -> tuple[str, Any]:
    if casts and col in casts:
        if casts[col].endswith("[]"):
            return f"%s::{casts[col]}", val
        # Il parametro con le regole qui sotto (senza jsonb/casts: la colonna
        # non e' in `jsonb`, `_verifica_casts` lo garantisce).
        _, param = _segnaposto_e_parametro(col, val, letterali=letterali)
        return f"%s::{casts[col]}", param
    if isinstance(val, (dict, list)):
        return "%s::jsonb", json.dumps(val)
    if col in jsonb:
        return "%s::jsonb", val
    if isinstance(val, str) and col not in letterali:
        return "%s", val.strip()
    return "%s", val


# Scopo: Verifica la mappa `casts` (colonna -> tipo) PRIMA di comporre: il
#        nome del tipo entra nel testo SQL, quindi dev'essere un identificatore
#        (qualificato dallo schema o no). Una colonna dichiarata sia in `jsonb`
#        sia in `casts` avrebbe due risposte alla stessa domanda: rifiutata.
#        Si verifica l'INTERA mappa, anche le colonne che il payload di questa
#        chiamata non porta: e' un contratto del chiamante, e un errore li'
#        deve emergere alla prima chiamata, non alla prima che usa la colonna.
def _verifica_casts(
    casts: Mapping[str, str] | None, jsonb: Collection[str], chi: str
) -> None:
    if not casts:
        return
    non_validi = sorted(
        f"{c}::{t}" for c, t in casts.items()
        if not _IDENTIFICATORE.match(c) or not _TIPO_QUALIFICATO.match(t)
    )
    if non_validi:
        raise RuntimeError(f"{chi}: cast non ammessi: {', '.join(non_validi)}")
    doppi = sorted(c for c in casts if c in jsonb)
    if doppi:
        raise RuntimeError(f"{chi}: colonne sia in jsonb sia in casts: {', '.join(doppi)}")


# Scopo: Rifiuta i nomi di colonna che non possono entrare nel testo SQL.
# ⛔ RIFIUTA, non scarta: un nome fuori whitelist in una SCRITTURA e' un errore
#    di programmazione o di contratto (il service ha gia' validato le chiavi del
#    payload), e scartarlo in silenzio farebbe un salvataggio che «riesce» senza
#    aver scritto il campo — il difetto che non da' errore. `RuntimeError`, non
#    `ValueError`: e' un invariante interno, non un errore che l'operatore puo'
#    causare, e `ErrorTranslator` traduce OGNI `ValueError` in un 400
#    `E_VALIDATION_INPUT` loggato senza stack («dato errato» a chi non ha
#    sbagliato niente). `RuntimeError` diventa `E_GENERICO`, 500 col traceback:
#    l'allarme tecnico che un errore di programmazione deve far scattare.
def _verifica_colonne(
    colonne: Collection[str], allowed: Collection[str] | None, chi: str
) -> None:
    fuori = sorted(
        c for c in colonne
        if not _IDENTIFICATORE.match(c) or (allowed is not None and c not in allowed)
    )
    if fuori:
        raise RuntimeError(f"{chi}: colonne non ammesse: {', '.join(fuori)}")


# Scopo: La clausola SET di un UPDATE dinamico, per chi il WHERE lo scrive da
#        se' (perimetro del padre, `UPDATE ... FROM`): i casi che
#        `execute_dynamic_update` — WHERE id = %s e basta — non copre.
#        Estratto 2026-09-26 (regola del 2: `listini_repository.
#        _prepare_update_parts` e `pagamenti_repository._set_clause` erano due
#        copie della stessa composizione, con due politiche diverse).
#        ⛔ Whitelist RIGIDA (`_verifica_colonne`): una colonna fuori lista e'
#        `RuntimeError`, mai uno scarto silenzioso. `allowed=None` va DETTO: vuol
#        dire «le chiavi sono letterali del chiamante».
#        `casts`: colonna -> tipo (`%s::<tipo>`, es. gli enum), vedi
#        `_verifica_casts`. `letterali`: colonne le cui stringhe NON si
#        strippano (vedi `_segnaposto_e_parametro`).
#        `values` vuoto -> `RuntimeError`: un UPDATE senza SET non e' SQL, e il
#        «niente da aggiornare» lo decide il chiamante prima di chiamare.
#        Ritorna (clausola senza la parola SET, parametri).
def sql_set_clause(
    values: Mapping[str, Any],
    *,
    allowed: Collection[str] | None,
    jsonb: Collection[str] = (),
    casts: Mapping[str, str] | None = None,
    letterali: Collection[str] = (),
) -> tuple[str, list[Any]]:
    if not values:
        raise RuntimeError("sql_set_clause: nessuna colonna da aggiornare")
    _verifica_colonne(values.keys(), allowed, "sql_set_clause")
    _verifica_casts(casts, jsonb, "sql_set_clause")
    assegnazioni: list[str] = []
    params: list[Any] = []
    for col, val in values.items():
        segnaposto, param = _segnaposto_e_parametro(col, val, jsonb, casts, letterali)
        assegnazioni.append(f"{col} = {segnaposto}")
        params.append(param)
    return ", ".join(assegnazioni), params


# Scopo: INSERT dinamico condiviso, fratello di `execute_dynamic_update`
#        (estratto 2026-09-26, regola del 2 — il blocco `cols`/`vals` + dict
#        `optional` era copiato identico in `create_ddt`/`create_ordine`/
#        `create_reso`, e `listini_repository._prepare_insert_parts` e
#        `pagamenti_repository.create_ente_incasso` lo riscrivevano).
#        Stesse convenzioni dell'UPDATE: `table` e `returning` sono LITERAL del
#        chiamante (mai input), dict/list -> `::jsonb`, stringhe strip.
#        `allowed`: whitelist delle colonne, OBBLIGATORIA da dichiarare —
#        `None` solo quando le chiavi sono nomi letterali scritti nel metodo.
#        ⛔ Politica RIGIDA, la stessa dell'UPDATE e del SET: una colonna
#        fuori lista e' `RuntimeError` (vedi `_verifica_colonne`).
#        `skip_none=True`: i None si OMETTONO, cosi' il DEFAULT del DB (o il
#        trigger BEFORE INSERT) resta attivo — la semantica dei `create_*` dei
#        documenti vendita. Default False: None scrive NULL.
#        `jsonb`: colonne da castare anche quando il valore arriva gia'
#        serializzato (vedi `_segnaposto_e_parametro`).
#        `casts`: colonna -> tipo (`%s::<tipo>`, es. gli enum), vedi
#        `_verifica_casts`. `letterali`: colonne le cui stringhe NON si
#        strippano.
#        `espressioni` (dal 2026-09-26): colonna -> espressione SQL LETTERALE
#        del chiamante (`fn_data_operativa()`, una sottoquery su un codice fisso), il
#        gemello di `extra_set` dell'UPDATE. Mai input: entra nel testo SQL.
#        La colonna passa la stessa whitelist dei valori, e una colonna sia in
#        `values` sia in `espressioni` e' `RuntimeError` (due risposte alla
#        stessa domanda).
#        Ritorna la riga di `RETURNING` come dict.
def execute_dynamic_insert(
    table: str,
    values: Mapping[str, Any],
    *,
    allowed: Collection[str] | None,
    skip_none: bool = False,
    jsonb: Collection[str] = (),
    casts: Mapping[str, str] | None = None,
    letterali: Collection[str] = (),
    espressioni: Mapping[str, str] | None = None,
    returning: str = "id",
) -> dict[str, Any]:
    chi = f"execute_dynamic_insert({table})"
    espressioni = espressioni or {}
    # Si verificano TUTTE le chiavi, anche quelle che `skip_none` omette: una
    # chiave fuori contratto e' un errore qualunque valore porti.
    _verifica_colonne([*values.keys(), *espressioni.keys()], allowed, chi)
    _verifica_casts(casts, jsonb, chi)
    doppie = sorted(set(values) & set(espressioni))
    if doppie:
        raise RuntimeError(f"{chi}: colonne sia in values sia in espressioni: {', '.join(doppie)}")
    colonne = [c for c, v in values.items() if not (skip_none and v is None)]
    if not colonne and not espressioni:
        raise RuntimeError(f"{chi}: nessuna colonna da inserire")
    segnaposti: list[str] = []
    params: list[Any] = []
    for col in colonne:
        segnaposto, param = _segnaposto_e_parametro(col, values[col], jsonb, casts, letterali)
        segnaposti.append(segnaposto)
        params.append(param)
    colonne += list(espressioni)
    segnaposti += list(espressioni.values())
    sql = (
        f"INSERT INTO {table} ({', '.join(colonne)}) "  # noqa: S608 — table/returning/espressioni literal del chiamante, colonne verificate da _verifica_colonne, cast da _verifica_casts, valori come parametri
        f"VALUES ({', '.join(segnaposti)}) RETURNING {returning}"
    )
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        riga = row_to_dict(cursor)
    if riga is None:
        raise RuntimeError(f"execute_dynamic_insert({table}): RETURNING senza riga")
    return riga


# Scopo: UPDATE dinamico per-id condiviso (BB estratto 2026-07-13, regola del
#        2 — era copiato in 8+ metodi update_* di ddt/ordini/preventivi/resi/
#        componenti/email): costruisce il SET dai valori (dict/list -> ::jsonb
#        + json.dumps, stringhe strip) e aggiorna la riga per id.
#        `table` DEVE essere un literal del chiamante (mai input utente).
#        ⛔ `allowed` = whitelist RIGIDA delle colonne (dal 2026-09-26, decisione
#        Tid): una chiave fuori lista e' `RuntimeError`, come nei fratelli
#        `execute_dynamic_insert`/`sql_set_clause` — fino a quel giorno veniva
#        SCARTATA IN SILENZIO, cioe' un salvataggio che «riesceva» senza aver
#        scritto il campo. `allowed=None` solo quando le chiavi sono nomi
#        LETTERALI scritti nel metodo chiamante (resta il controllo
#        d'identificatore). ⚠️ Il default `None` sopravvive per il solo
#        delegatore `_helpers.dynamic_update` (kwargs letterali dei metodi
#        geo/indirizzi): ogni chiamante diretto lo DICHIARA.
#        `extra_set` = clausola SET aggiuntiva literal (es. "data_update =
#        now()"); `skip_none` = True per i CRUD "kwargs espliciti" dove None
#        significa "non toccare" (default False: nei PATCH whitelisted None
#        AZZERA il campo nullable). `jsonb`/`casts`/`letterali` come nei
#        fratelli.
#        Ritorna False se non c'e' nulla da aggiornare, altrimenti
#        rowcount > 0.
def execute_dynamic_update(
    table: str,
    # `int` o UUID (anche come testo): passa come parametro SQL, la PK la decide la tabella.
    row_id: int | str | UUID,
    values: Mapping[str, Any],
    *,
    allowed: Collection[str] | None = None,
    extra_set: str | None = None,
    skip_none: bool = False,
    jsonb: Collection[str] = (),
    casts: Mapping[str, str] | None = None,
    letterali: Collection[str] = (),
) -> bool:
    chi = f"execute_dynamic_update({table})"
    _verifica_colonne(values.keys(), allowed, chi)
    _verifica_casts(casts, jsonb, chi)
    fields: list[str] = []
    params: list[Any] = []
    for col, val in values.items():
        if skip_none and val is None:
            continue
        segnaposto, param = _segnaposto_e_parametro(col, val, jsonb, casts, letterali)
        fields.append(f"{col} = {segnaposto}")
        params.append(param)
    if not fields:
        return False
    if extra_set:
        fields.append(extra_set)
    params.append(row_id)
    sql = f"UPDATE {table} SET {', '.join(fields)} WHERE id = %s"  # noqa: S608 — table/extra_set literal del chiamante, colonne verificate da _verifica_colonne, cast da _verifica_casts, valori come parametri
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.rowcount > 0
