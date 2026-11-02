# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per entita' geografiche config:
#        toponomastica, comuni, codici postali, province, regioni, stati.
#        Accesso DB-first via cursor.
# ------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
from typing import Any

from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.db._helpers import (
    RicercaFull,
    add_ricerca_full_condition,
    fetch_paged_with_total,
    row_to_dict,
    rows_to_list,
    colonne_identita,
    sql_order_clause,
)

from apps.core.db.sql_write_helpers import execute_dynamic_update
from django.db import connection


# ⚠️ Mappe e non insiemi, con le due meta' UGUALI apposta: su queste sei liste
#    il nome logico della colonna E' la sua espressione SQL — nessuna traduzione
#    da fare. E' la forma che `sql_order_clause` chiede a tutte le liste, e
#    scriverla esplicitamente evita che il prossimo lettore creda che qui manchi
#    qualcosa.
# ⭐ `set(_X_ORDER_COLS)` continua a dare le chiavi: i risolutori di whitelist
#    del presidio seed non cambiano.
_TOPONOMASTICA_ORDER_COLS = colonne_identita("descrizione", "attivo")
_COMUNI_ORDER_COLS = colonne_identita("descrizione", "provincia_sigla", "regione_descrizione")
_PROVINCE_ORDER_COLS = colonne_identita("descrizione", "sigla", "regione_descrizione")
_REGIONI_ORDER_COLS = colonne_identita("descrizione", "stato_descrizione")
# ⚠️ `codice_iso3` e' entrato il 2026-09-27 (brief-db-liste-datatable-grezze
#    §4.1 riga 9): il seed lo dichiara `ordinabile = t` e fino a quel giorno la
#    freccia ISO3 ripiegava in silenzio sull'ordine di default.
# ⚠️ `sigla_stato` (stati) e `provincia_sigla` (CAP) sono entrate il 2026-09-28
#    (§9 dello stesso brief): la prima e' una colonna del nucleo resa
#    ordinabile dal seed, la seconda la provincia che distingue due comuni
#    omonimi nella lista CAP (`vw_codici_postali_lista`, NULL se il comune non
#    ha provincia: ordina come il valore minimo).
_STATI_ORDER_COLS = colonne_identita(
    "descrizione", "sigla_stato", "codice_iso2", "codice_iso3", "continente",
)
_CODICI_POSTALI_ORDER_COLS = colonne_identita("codice", "comune_descrizione", "provincia_sigla")

# Cosa si PUO' cercare nelle sei liste geografiche; cosa si cerca, e da quanti
# caratteri, lo dice il catalogo (`add_ricerca_full_condition`, liste 91-96).
# ⭐ Forma a tupla: le sei leggono UNA relazione (la tabella, o la vista di
#    lista `config.vw_*_lista`) in cui il `campo_sorgente` E' la colonna —
#    come per l'ordinamento, nessuna traduzione. Si dichiarano tutte le colonne
#    TESTO che la lista mostra, non solo quelle accese oggi dal seed: e' una
#    capacita' che l'amministratore puo' accendere senza toccare il codice.
# ⛔ Fino al 2026-09-27 le ricerche erano scritte a mano, sei copie con sei
#    elenchi di colonne e nessuna soglia: il catalogo spegneva una colonna e
#    la lista continuava a cercarci.
_RICERCA_TOPONOMASTICA = RicercaFull("config.toponomastica", ("descrizione",))
_RICERCA_COMUNI = RicercaFull("config.comuni", (
    "descrizione", "provincia_sigla", "provincia_descrizione", "regione_descrizione",
))
_RICERCA_CODICI_POSTALI = RicercaFull("config.codici_postali", ("codice", "comune_descrizione"))
_RICERCA_PROVINCE = RicercaFull("config.province", ("sigla", "descrizione", "regione_descrizione"))
_RICERCA_REGIONI = RicercaFull("config.regioni", ("descrizione", "stato_descrizione"))
_RICERCA_STATI = RicercaFull("config.stati", (
    "descrizione", "codice_iso2", "codice_iso3", "sigla_stato", "continente",
))


# Scopo: COSA si legge di un'entita' geografica: la relazione (la tabella, o
#        la vista di lista `config.vw_*_lista`) e le colonne della riga.
# ⭐ Regola del 2 (2026-09-28): la stessa proiezione era scritta due o tre
#    volte per entita' — nella lista, nel dettaglio e nel `RETURNING` della
#    create — e il dettaglio di province e regioni rifaceva a mano il JOIN
#    della vista. Lista, dettaglio e riga restituita dalla create leggono ora
#    la stessa sorgente: una colonna aggiunta alla vista si aggiunge qui, una
#    volta, e la riga da cui si apre il drawer e' quella che il drawer legge.
# ⛔ `relazione` e `colonne` sono letterali di questo modulo, mai input: e' la
#    ragione per cui le f-string di `_lista_geo` e `_dettaglio_geo` sono ammesse.
@dataclass(frozen=True)
class _SorgenteGeo:
    relazione: str
    colonne: tuple[str, ...]

    # Scopo: la lista delle colonne per la SELECT, con l'alias se dato.
    def proiezione(self, alias: str | None = None) -> str:
        prefisso = f"{alias}." if alias else ""
        return ", ".join(prefisso + c for c in self.colonne)


_TOPONOMASTICA = _SorgenteGeo("config.toponomastica", ("id", "descrizione", "attivo"))
_COMUNI = _SorgenteGeo("config.vw_comuni_lista", (
    "id", "descrizione", "provincia_id", "provincia_sigla",
    "provincia_descrizione", "regione_id", "regione_descrizione",
))
_CODICI_POSTALI = _SorgenteGeo("config.vw_codici_postali_lista", (
    "id", "codice", "comune_id", "comune_descrizione", "provincia_id", "provincia_sigla",
))
_PROVINCE = _SorgenteGeo("config.vw_province_lista", (
    "id", "descrizione", "sigla", "regione_id", "regione_descrizione",
))
_REGIONI = _SorgenteGeo("config.vw_regioni_lista", (
    "id", "descrizione", "stato_id", "stato_descrizione",
))
_STATI = _SorgenteGeo("config.stati", (
    "id", "descrizione", "sigla_stato", "codice_iso2", "codice_iso3",
    "codice_telefonico", "continente",
))


# Scopo: la riga di un'entita' geografica per id, dalla sua sorgente.
def _dettaglio_geo(sorgente: _SorgenteGeo, pk: int) -> dict[str, Any] | None:
    sql = f"SELECT {sorgente.proiezione()} FROM {sorgente.relazione} WHERE id = %s"  # noqa: S608 — sorgente letterale del modulo, l'id come parametro
    with connection.cursor() as cursor:
        cursor.execute(sql, [pk])
        return row_to_dict(cursor)


# Scopo: esegue un INSERT ... RETURNING id e restituisce la riga appena creata
#        riletta dalla sorgente, cioe' come la mostrano lista e dettaglio.
# ⛔ Fino al 2026-09-28 la create restituiva il suo `RETURNING`: i campi della
#    tabella senza le descrizioni dei JOIN (un CAP senza comune ne' provincia,
#    una provincia senza regione), cioe' una riga piu' povera del dettaglio.
def _crea_geo(sorgente: _SorgenteGeo, sql_insert: str, params: list[Any]) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(sql_insert, params)
        creato = row_to_dict(cursor)
    assert creato is not None
    riga = _dettaglio_geo(sorgente, creato["id"])
    assert riga is not None
    return riga


# Scopo: la lettura paginata comune alle sei liste: UNA relazione (alias `v`),
#        i filtri gia' composti dal chiamante, la ricerca dal catalogo, il
#        totale nella stessa valutazione (`fetch_paged_with_total`) con il
#        conteggio di ripiego sulla pagina oltre l'ultima.
# ⭐ Regola del 2: le sei query differivano solo per relazione, proiezione e
#    filtro — la forma (WHERE, ORDER BY, LIMIT, conteggio) era la stessa,
#    scritta sei volte.
def _lista_geo(
    *, sorgente: _SorgenteGeo, ricerca: RicercaFull, search: str | None,
    ordinamento: str, limit: int, offset: int,
    conditions: list[str] | None = None, params: list[Any] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    conditions = list(conditions or [])
    params = list(params or [])
    add_ricerca_full_condition(conditions, params, search, ricerca)
    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    from_where = f"FROM {sorgente.relazione} v {where_clause}"
    return fetch_paged_with_total(
        f"""
        SELECT {sorgente.proiezione("v")}, COUNT(*) OVER () AS total_count
          {from_where}
         ORDER BY {ordinamento}
         LIMIT %s OFFSET %s
        """,  # sorgente letterale del modulo, ORDER BY da sql_order_clause su whitelist, WHERE da condizioni letterali + add_ricerca_full_condition, valori come parametri
        params + [limit, offset],
        fallback_count_sql=f"SELECT COUNT(*) {from_where}",  # stesso FROM/WHERE della pagina
        fallback_params=params,
        offset=offset,
    )


# Chi chiede lo stato proposto per la tendina degli stati (`p_chi` di
# `script.fn_stato_proposto_id`). ⚠️ Oggi il lettore lo passa anche come nome
# di FUNZIONE al lettore dei parametri (R-BE-13), quindi un override per
# funzione dipende da questo valore: chi rilegge lo stato proposto per
# confrontarlo con la tendina usa questa costante.
CHI_STATI_LOOKUP = "anagrafiche.stati_lookup"


class GeoRepository:
    """Accesso DB per toponomastica, comuni, province, regioni, stati."""

    # =================================================================
    # Toponomastica
    # =================================================================

    # Scopo: Lista paginata toponomastica.
    def list_toponomastica(
        self, *, search: str | None = None, limit: int = DEFAULT_LIMIT, offset: int = 0,
        order_by: str = "descrizione", order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_TOPONOMASTICA_ORDER_COLS,
            default="descrizione",
            tiebreak="id",
        )
        return _lista_geo(
            sorgente=_TOPONOMASTICA,
            ricerca=_RICERCA_TOPONOMASTICA, search=search,
            ordinamento=ordinamento, limit=limit, offset=offset,
        )

    # Scopo: Dettaglio singolo toponomastica.
    def get_toponomastica(self, pk: int) -> dict[str, Any] | None:
        return _dettaglio_geo(_TOPONOMASTICA, pk)

    # Scopo: Crea tipo strada.
    def create_toponomastica(self, *, descrizione: str) -> dict[str, Any]:
        return _crea_geo(
            _TOPONOMASTICA,
            "INSERT INTO config.toponomastica (descrizione) VALUES (%s) RETURNING id",
            [descrizione.strip()],
        )

    # Scopo: Aggiorna tipo strada.
    # ⚠️ `campi` li legge il service per PRESENZA (`campi_per_presenza`): un
    #    `None` qui e' un campo da svuotare, non «non toccare».
    def update_toponomastica(self, toponomastica_id: int, campi: Mapping[str, Any]) -> bool:
        return execute_dynamic_update(
            "config.toponomastica", toponomastica_id, campi, allowed=("descrizione", "attivo"),
        )

    # =================================================================
    # Comuni
    # =================================================================

    # Scopo: Lista paginata comuni con provincia e regione.
    # ⭐ Legge la vista di lista `config.vw_comuni_lista` (§6.3 del brief
    #    liste-datatable-grezze): la proiezione e' la stessa contro cui il
    #    trigger del catalogo valida i `campo_sorgente`. Fino al 2026-09-27 i
    #    JOIN stavano qui, e la sigla della provincia usciva con gli spazi in
    #    coda (`character(n)`). Dal `20261010-26` sigla e descrizione sono
    #    `varchar` a DB, e la vista le da' come sono (brief character-n).
    def list_comuni(
        self, *, search: str | None = None, limit: int = DEFAULT_LIMIT, offset: int = 0,
        order_by: str = "descrizione", order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_COMUNI_ORDER_COLS,
            default="descrizione",
            tiebreak="id",
        )
        return _lista_geo(
            sorgente=_COMUNI,
            ricerca=_RICERCA_COMUNI, search=search,
            ordinamento=ordinamento, limit=limit, offset=offset,
        )

    # Scopo: Dettaglio singolo provincia (la stessa vista della lista).
    def get_provincia(self, pk: int) -> dict[str, Any] | None:
        return _dettaglio_geo(_PROVINCE, pk)

    # Scopo: Dettaglio singolo regione (la vista di lista).
    # ⚠️ La vista fa `JOIN` sullo stato dove il vecchio dettaglio faceva
    #    `LEFT JOIN`: e' la stessa cosa, `regioni.stato_id` e' NOT NULL.
    def get_regione(self, pk: int) -> dict[str, Any] | None:
        return _dettaglio_geo(_REGIONI, pk)

    # Scopo: Dettaglio singolo stato.
    def get_stato(self, pk: int) -> dict[str, Any] | None:
        return _dettaglio_geo(_STATI, pk)

    # Scopo: Crea comune.
    def create_comune(self, *, descrizione: str, provincia_id: int | None = None) -> dict[str, Any]:
        return _crea_geo(
            _COMUNI,
            "INSERT INTO config.comuni (descrizione, provincia_id) VALUES (%s, %s) RETURNING id",
            [descrizione.strip(), provincia_id],
        )

    # =================================================================
    # Codici Postali (CAP)
    # =================================================================

    # Scopo: Lista paginata codici postali con comune.
    # ⭐ Legge `config.vw_codici_postali_lista` (§6.3 del brief liste-datatable-
    #    grezze), non piu' il suo JOIN.
    # ⭐ Porta la sigla della provincia del comune (§9.2-9.3): due comuni
    #    omonimi in province diverse non escono piu' identici.
    def list_codici_postali(
        self, *, search: str | None = None, comune_id: int | None = None,
        limit: int = DEFAULT_LIMIT, offset: int = 0,
        order_by: str = "codice", order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_CODICI_POSTALI_ORDER_COLS,
            default="codice",
            tiebreak="id",
        )
        conditions: list[str] = []
        params: list[Any] = []
        if comune_id is not None:
            conditions.append("v.comune_id = %s")
            params.append(comune_id)
        return _lista_geo(
            sorgente=_CODICI_POSTALI,
            ricerca=_RICERCA_CODICI_POSTALI, search=search,
            ordinamento=ordinamento, limit=limit, offset=offset,
            conditions=conditions, params=params,
        )

    # Scopo: Dettaglio singolo codice postale.
    # ⭐ Legge la stessa sorgente della lista (§9.3): il dettaglio porta la
    #    provincia come la riga da cui si apre.
    def get_codice_postale(self, pk: int) -> dict[str, Any] | None:
        return _dettaglio_geo(_CODICI_POSTALI, pk)

    # Scopo: Crea codice postale.
    def create_codice_postale(self, *, codice: str, comune_id: int) -> dict[str, Any]:
        return _crea_geo(
            _CODICI_POSTALI,
            "INSERT INTO config.codici_postali (codice, comune_id) VALUES (%s, %s) RETURNING id",
            [codice.strip(), comune_id],
        )

    # Scopo: Aggiorna codice postale.
    # ⚠️ `campi` li legge il service per PRESENZA (`campi_per_presenza`): un
    #    `None` qui e' un campo da svuotare, non «non toccare».
    def update_codice_postale(self, pk: int, campi: Mapping[str, Any]) -> bool:
        return execute_dynamic_update(
            "config.codici_postali", pk, campi, allowed=("codice", "comune_id"),
        )

    # =================================================================
    # Province
    # =================================================================

    # Scopo: Lista paginata province.
    # ⭐ Legge `config.vw_province_lista` (§6.3 del brief liste-datatable-
    #    grezze): descrizione e sigla escono come sono (`varchar` a DB dal
    #    `20261010-26`, niente piu' TRIM), e la ricerca le confronta cosi' come
    #    si vedono.
    def list_province_paginated(
        self, *, search: str | None = None, regione_id: int | None = None,
        limit: int = DEFAULT_LIMIT, offset: int = 0,
        order_by: str = "descrizione", order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_PROVINCE_ORDER_COLS,
            default="descrizione",
            tiebreak="id",
        )
        conditions: list[str] = []
        params: list[Any] = []
        if regione_id is not None:
            conditions.append("v.regione_id = %s")
            params.append(regione_id)
        return _lista_geo(
            sorgente=_PROVINCE,
            ricerca=_RICERCA_PROVINCE, search=search,
            ordinamento=ordinamento, limit=limit, offset=offset,
            conditions=conditions, params=params,
        )

    # Scopo: Lista province per dropdown.
    def list_province(self) -> list[dict[str, Any]]:
        sql = """
            SELECT p.id, p.sigla, p.descrizione, r.descrizione AS regione_descrizione
              FROM config.province p
              LEFT JOIN config.regioni r ON r.id = p.regione_id
             ORDER BY p.descrizione
        """
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return rows_to_list(cursor)

    # Scopo: Crea provincia.
    def create_provincia(self, *, descrizione: str, sigla: str,
                         regione_id: int | None = None) -> dict[str, Any]:
        return _crea_geo(
            _PROVINCE,
            "INSERT INTO config.province (descrizione, sigla, regione_id) VALUES (%s, %s, %s) RETURNING id",
            [descrizione.strip(), sigla.strip().upper(), regione_id],
        )

    # Scopo: Aggiorna provincia.
    # ⚠️ `campi` li legge il service per PRESENZA (`campi_per_presenza`): un
    #    `None` qui e' un campo da svuotare, non «non toccare».
    def update_provincia(self, provincia_id: int, campi: Mapping[str, Any]) -> bool:
        return execute_dynamic_update(
            "config.province", provincia_id, campi, allowed=("descrizione", "sigla", "regione_id"),
        )

    # =================================================================
    # Regioni
    # =================================================================

    # Scopo: Lista paginata regioni.
    # ⭐ Legge `config.vw_regioni_lista` (§6.3 del brief liste-datatable-
    #    grezze). ⚠️ La vista fa `JOIN` e non `LEFT JOIN` sullo stato: e' la
    #    stessa cosa, `regioni.stato_id` e' NOT NULL.
    def list_regioni(
        self, *, search: str | None = None, stato_id: int | None = None,
        limit: int = DEFAULT_LIMIT, offset: int = 0,
        order_by: str = "descrizione", order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_REGIONI_ORDER_COLS,
            default="descrizione",
            tiebreak="id",
        )
        conditions: list[str] = []
        params: list[Any] = []
        if stato_id is not None:
            conditions.append("v.stato_id = %s")
            params.append(stato_id)
        return _lista_geo(
            sorgente=_REGIONI,
            ricerca=_RICERCA_REGIONI, search=search,
            ordinamento=ordinamento, limit=limit, offset=offset,
            conditions=conditions, params=params,
        )

    # Scopo: Lista regioni per dropdown.
    def list_regioni_lookup(self, stato_id: int | None = None) -> list[dict[str, Any]]:
        sql = """
            SELECT id, descrizione, stato_id FROM config.regioni
             WHERE (%s::integer IS NULL OR stato_id = %s)
             ORDER BY descrizione
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [stato_id, stato_id])
            return rows_to_list(cursor)

    # Scopo: Crea regione.
    def create_regione(self, *, descrizione: str, stato_id: int | None = None) -> dict[str, Any]:
        return _crea_geo(
            _REGIONI,
            "INSERT INTO config.regioni (descrizione, stato_id) VALUES (%s, %s) RETURNING id",
            [descrizione.strip(), stato_id],
        )

    # Scopo: Aggiorna regione.
    # ⚠️ `campi` li legge il service per PRESENZA (`campi_per_presenza`): un
    #    `None` qui e' un campo da svuotare, non «non toccare».
    def update_regione(self, regione_id: int, campi: Mapping[str, Any]) -> bool:
        return execute_dynamic_update(
            "config.regioni", regione_id, campi, allowed=("descrizione", "stato_id"),
        )

    # =================================================================
    # Stati
    # =================================================================

    # Scopo: Lista paginata stati.
    def list_stati(
        self, *, search: str | None = None, limit: int = DEFAULT_LIMIT, offset: int = 0,
        order_by: str = "descrizione", order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_STATI_ORDER_COLS,
            default="descrizione",
            tiebreak="id",
        )
        return _lista_geo(
            sorgente=_STATI,
            ricerca=_RICERCA_STATI, search=search,
            ordinamento=ordinamento, limit=limit, offset=offset,
        )

    # Scopo: Lista stati per dropdown. Due colonne in piu' (2026-10-18, D-1 e
    #        D-2 di Tid, brief-db-processi-accensione-per-ambiente §6.11):
    #        - `catalogo_comuni_completo`: la FORMA dell'indirizzo libero in
    #          quello stato (acceso: comune e CAP dall'elenco; spento: la
    #          localita'). Il form la legge da qui, non la ricalcola;
    #        - `proposto`: lo stato da preselezionare, da
    #          `script.fn_stato_proposto_id` (parametro STATO_PROPOSTO_ISO2), lo
    #          stesso lettore dei trigger che lo scrivono quando manca. Valida e
    #          non ripiega: un parametro sbagliato e' un errore, non un 'IT'.
    def list_stati_lookup(self) -> list[dict[str, Any]]:
        sql = """
            SELECT s.id, s.descrizione, s.codice_iso2, s.catalogo_comuni_completo,
                   (s.id = p.stato_id) AS proposto
              FROM config.stati s
             CROSS JOIN (SELECT script.fn_stato_proposto_id(%s) AS stato_id) p
             ORDER BY s.descrizione
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [CHI_STATI_LOOKUP])
            return rows_to_list(cursor)

    # Scopo: Crea stato.
    def create_stato(self, *, descrizione: str, codice_iso2: str | None = None,
                     codice_iso3: str | None = None, sigla_stato: str | None = None,
                     codice_telefonico: str | None = None, continente: str | None = None) -> dict[str, Any]:
        sql = """
            INSERT INTO config.stati (descrizione, codice_iso2, codice_iso3,
                                      sigla_stato, codice_telefonico, continente)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        return _crea_geo(_STATI, sql, [
            descrizione.strip(),
            codice_iso2.strip().upper() if codice_iso2 else None,
            codice_iso3.strip().upper() if codice_iso3 else None,
            sigla_stato.strip().upper() if sigla_stato else None,
            codice_telefonico.strip() if codice_telefonico else None,
            continente.strip() if continente else None,
        ])

    # Scopo: Aggiorna stato.
    # ⚠️ `campi` li legge il service per PRESENZA (`campi_per_presenza`): un
    #    `None` qui e' un campo da svuotare, non «non toccare».
    def update_stato(self, stato_id: int, campi: Mapping[str, Any]) -> bool:
        return execute_dynamic_update(
            "config.stati", stato_id, campi,
            allowed=("descrizione", "codice_iso2", "codice_iso3", "sigla_stato",
                     "codice_telefonico", "continente"),
        )

