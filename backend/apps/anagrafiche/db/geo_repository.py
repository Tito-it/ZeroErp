# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per entita' geografiche config:
#        toponomastica, comuni, province, regioni, stati.
#        Accesso DB-first via cursor.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.core.db._helpers import (
    RicercaFull,
    add_ricerca_full_condition,
    dynamic_update,
    fetch_paged_with_total,
    row_to_dict,
    rows_to_list,
    colonne_identita,
    sql_order_clause,
)

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
_STATI_ORDER_COLS = colonne_identita("descrizione", "codice_iso2", "codice_iso3", "continente")
_CODICI_POSTALI_ORDER_COLS = colonne_identita("codice", "comune_descrizione")

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


# Scopo: la lettura paginata comune alle sei liste: UNA relazione (alias `v`),
#        i filtri gia' composti dal chiamante, la ricerca dal catalogo, il
#        totale nella stessa valutazione (`fetch_paged_with_total`) con il
#        conteggio di ripiego sulla pagina oltre l'ultima.
# ⭐ Regola del 2: le sei query differivano solo per relazione, proiezione e
#    filtro — la forma (WHERE, ORDER BY, LIMIT, conteggio) era la stessa,
#    scritta sei volte.
# ⛔ `relazione` e `colonne` sono letterali di questo modulo, mai input: e' la
#    ragione per cui l'f-string qui sotto e' ammessa.
def _lista_geo(
    *, relazione: str, colonne: str, ricerca: RicercaFull, search: str | None,
    ordinamento: str, limit: int, offset: int,
    conditions: list[str] | None = None, params: list[Any] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    conditions = list(conditions or [])
    params = list(params or [])
    add_ricerca_full_condition(conditions, params, search, ricerca)
    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    from_where = f"FROM {relazione} v {where_clause}"
    return fetch_paged_with_total(
        f"""
        SELECT {colonne}, COUNT(*) OVER () AS total_count
          {from_where}
         ORDER BY {ordinamento}
         LIMIT %s OFFSET %s
        """,  # relazione/colonne letterali del modulo, ORDER BY da sql_order_clause su whitelist, WHERE da condizioni letterali + add_ricerca_full_condition, valori come parametri
        params + [limit, offset],
        fallback_count_sql=f"SELECT COUNT(*) {from_where}",  # stesso FROM/WHERE della pagina
        fallback_params=params,
        offset=offset,
    )


class GeoRepository:
    """Accesso DB per toponomastica, comuni, province, regioni, stati."""

    # =================================================================
    # Toponomastica
    # =================================================================

    # Scopo: Lista paginata toponomastica.
    def list_toponomastica(
        self, *, search: str | None = None, limit: int = 25, offset: int = 0,
        order_by: str = "descrizione", order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_TOPONOMASTICA_ORDER_COLS,
            default="descrizione",
            tiebreak="id",
        )
        return _lista_geo(
            relazione="config.toponomastica", colonne="v.id, v.descrizione, v.attivo",
            ricerca=_RICERCA_TOPONOMASTICA, search=search,
            ordinamento=ordinamento, limit=limit, offset=offset,
        )

    # Scopo: Dettaglio singolo toponomastica.
    def get_toponomastica(self, pk: int) -> dict[str, Any] | None:
        return self._get_by_id("config.toponomastica", pk, "id, descrizione, attivo")

    # Scopo: Crea tipo strada.
    def create_toponomastica(self, *, descrizione: str) -> dict[str, Any]:
        sql = """
            INSERT INTO config.toponomastica (descrizione) VALUES (%s)
            RETURNING id, descrizione, attivo
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [descrizione.strip()])
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # Scopo: Aggiorna tipo strada.
    def update_toponomastica(self, toponomastica_id: int, *, descrizione: str | None = None,
                             attivo: bool | None = None) -> bool:
        return dynamic_update("config.toponomastica", toponomastica_id,
                                    descrizione=descrizione, attivo=attivo)

    # =================================================================
    # Comuni
    # =================================================================

    # Scopo: Lista paginata comuni con provincia e regione.
    # ⭐ Legge la vista di lista `config.vw_comuni_lista` (§6.3 del brief
    #    liste-datatable-grezze): la proiezione e' la stessa contro cui il
    #    trigger del catalogo valida i `campo_sorgente`. Fino al 2026-09-27 i
    #    JOIN stavano qui, e la sigla della provincia usciva con gli spazi in
    #    coda (`character(n)`); la vista la da' con TRIM.
    def list_comuni(
        self, *, search: str | None = None, limit: int = 25, offset: int = 0,
        order_by: str = "descrizione", order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_COMUNI_ORDER_COLS,
            default="descrizione",
            tiebreak="id",
        )
        return _lista_geo(
            relazione="config.vw_comuni_lista",
            colonne=(
                "v.id, v.descrizione, v.provincia_id, v.provincia_sigla, "
                "v.provincia_descrizione, v.regione_id, v.regione_descrizione"
            ),
            ricerca=_RICERCA_COMUNI, search=search,
            ordinamento=ordinamento, limit=limit, offset=offset,
        )

    # Scopo: Dettaglio singolo provincia.
    def get_provincia(self, pk: int) -> dict[str, Any] | None:
        sql = """
            SELECT p.id, TRIM(p.descrizione) AS descrizione, TRIM(p.sigla) AS sigla,
                   p.regione_id, r.descrizione AS regione_descrizione
              FROM config.province p
              LEFT JOIN config.regioni r ON r.id = p.regione_id
             WHERE p.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [pk])
            return row_to_dict(cursor)

    # Scopo: Dettaglio singolo regione.
    def get_regione(self, pk: int) -> dict[str, Any] | None:
        sql = """
            SELECT r.id, r.descrizione, r.stato_id, s.descrizione AS stato_descrizione
              FROM config.regioni r
              LEFT JOIN config.stati s ON s.id = r.stato_id
             WHERE r.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [pk])
            return row_to_dict(cursor)

    # Scopo: Dettaglio singolo stato.
    def get_stato(self, pk: int) -> dict[str, Any] | None:
        return self._get_by_id("config.stati", pk,
            "id, descrizione, sigla_stato, codice_iso2, codice_iso3, codice_telefonico, continente")

    # Scopo: Crea comune.
    def create_comune(self, *, descrizione: str, provincia_id: int | None = None) -> dict[str, Any]:
        sql = """
            INSERT INTO config.comuni (descrizione, provincia_id) VALUES (%s, %s)
            RETURNING id, descrizione, provincia_id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [descrizione.strip(), provincia_id])
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # =================================================================
    # Codici Postali (CAP)
    # =================================================================

    # Scopo: Lista paginata codici postali con comune.
    # ⭐ Legge `config.vw_codici_postali_lista` (§6.3 del brief liste-datatable-
    #    grezze), non piu' il suo JOIN.
    # ⏳ La lista non porta ancora la provincia (due comuni omonimi non si
    #    distinguono): deciso che la mostri — richiesta al DB nel brief §9.2,
    #    poi `provincia_sigla` in proiezione, whitelist e `get_codice_postale`
    #    (§9.3).
    def list_codici_postali(
        self, *, search: str | None = None, comune_id: int | None = None,
        limit: int = 25, offset: int = 0,
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
            relazione="config.vw_codici_postali_lista",
            colonne="v.id, v.codice, v.comune_id, v.comune_descrizione",
            ricerca=_RICERCA_CODICI_POSTALI, search=search,
            ordinamento=ordinamento, limit=limit, offset=offset,
            conditions=conditions, params=params,
        )

    # Scopo: Dettaglio singolo codice postale.
    def get_codice_postale(self, pk: int) -> dict[str, Any] | None:
        sql = """
            SELECT cp.id, cp.codice, cp.comune_id, c.descrizione AS comune_descrizione
              FROM config.codici_postali cp
              JOIN config.comuni c ON c.id = cp.comune_id
             WHERE cp.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [pk])
            return row_to_dict(cursor)

    # Scopo: Crea codice postale.
    def create_codice_postale(self, *, codice: str, comune_id: int) -> dict[str, Any]:
        sql = """
            INSERT INTO config.codici_postali (codice, comune_id) VALUES (%s, %s)
            RETURNING id, codice, comune_id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [codice.strip(), comune_id])
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # Scopo: Aggiorna codice postale.
    def update_codice_postale(self, pk: int, *, codice: str | None = None,
                              comune_id: int | None = None) -> bool:
        return dynamic_update("config.codici_postali", pk,
                                    codice=codice, comune_id=comune_id)

    # =================================================================
    # Province
    # =================================================================

    # Scopo: Lista paginata province.
    # ⭐ Legge `config.vw_province_lista` (§6.3 del brief liste-datatable-
    #    grezze): descrizione e sigla escono gia' con TRIM, e la ricerca le
    #    confronta cosi' come si vedono.
    def list_province_paginated(
        self, *, search: str | None = None, regione_id: int | None = None,
        limit: int = 25, offset: int = 0,
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
            relazione="config.vw_province_lista",
            colonne="v.id, v.descrizione, v.sigla, v.regione_id, v.regione_descrizione",
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
        sql = """
            INSERT INTO config.province (descrizione, sigla, regione_id) VALUES (%s, %s, %s)
            RETURNING id, TRIM(descrizione) AS descrizione, TRIM(sigla) AS sigla, regione_id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [descrizione.strip(), sigla.strip().upper(), regione_id])
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # Scopo: Aggiorna provincia.
    def update_provincia(self, provincia_id: int, *, descrizione: str | None = None,
                         sigla: str | None = None, regione_id: int | None = None) -> bool:
        return dynamic_update("config.province", provincia_id,
                              descrizione=descrizione,
                              sigla=sigla.strip().upper() if sigla else sigla,
                              regione_id=regione_id)

    # =================================================================
    # Regioni
    # =================================================================

    # Scopo: Lista paginata regioni.
    # ⭐ Legge `config.vw_regioni_lista` (§6.3 del brief liste-datatable-
    #    grezze). ⚠️ La vista fa `JOIN` e non `LEFT JOIN` sullo stato: e' la
    #    stessa cosa, `regioni.stato_id` e' NOT NULL.
    def list_regioni(
        self, *, search: str | None = None, stato_id: int | None = None,
        limit: int = 25, offset: int = 0,
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
            relazione="config.vw_regioni_lista",
            colonne="v.id, v.descrizione, v.stato_id, v.stato_descrizione",
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
        sql = """
            INSERT INTO config.regioni (descrizione, stato_id) VALUES (%s, %s)
            RETURNING id, descrizione, stato_id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [descrizione.strip(), stato_id])
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # Scopo: Aggiorna regione.
    def update_regione(self, regione_id: int, *, descrizione: str | None = None,
                       stato_id: int | None = None) -> bool:
        return dynamic_update("config.regioni", regione_id,
                                    descrizione=descrizione, stato_id=stato_id)

    # =================================================================
    # Stati
    # =================================================================

    # Scopo: Lista paginata stati.
    def list_stati(
        self, *, search: str | None = None, limit: int = 25, offset: int = 0,
        order_by: str = "descrizione", order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_STATI_ORDER_COLS,
            default="descrizione",
            tiebreak="id",
        )
        return _lista_geo(
            relazione="config.stati",
            colonne=(
                "v.id, v.descrizione, v.sigla_stato, v.codice_iso2, v.codice_iso3, "
                "v.codice_telefonico, v.continente"
            ),
            ricerca=_RICERCA_STATI, search=search,
            ordinamento=ordinamento, limit=limit, offset=offset,
        )

    # Scopo: Lista stati per dropdown.
    def list_stati_lookup(self) -> list[dict[str, Any]]:
        sql = "SELECT id, descrizione, codice_iso2 FROM config.stati ORDER BY descrizione"
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return rows_to_list(cursor)

    # Scopo: Crea stato.
    def create_stato(self, *, descrizione: str, codice_iso2: str | None = None,
                     codice_iso3: str | None = None, sigla_stato: str | None = None,
                     codice_telefonico: str | None = None, continente: str | None = None) -> dict[str, Any]:
        sql = """
            INSERT INTO config.stati (descrizione, codice_iso2, codice_iso3,
                                      sigla_stato, codice_telefonico, continente)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, descrizione, codice_iso2, codice_iso3, sigla_stato,
                      codice_telefonico, continente
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                descrizione.strip(),
                codice_iso2.strip().upper() if codice_iso2 else None,
                codice_iso3.strip().upper() if codice_iso3 else None,
                sigla_stato.strip().upper() if sigla_stato else None,
                codice_telefonico.strip() if codice_telefonico else None,
                continente.strip() if continente else None,
            ])
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # Scopo: Aggiorna stato.
    def update_stato(self, stato_id: int, *, descrizione: str | None = None,
                     codice_iso2: str | None = None, codice_iso3: str | None = None,
                     sigla_stato: str | None = None, codice_telefonico: str | None = None,
                     continente: str | None = None) -> bool:
        return dynamic_update("config.stati", stato_id,
                              descrizione=descrizione,
                              codice_iso2=codice_iso2.strip().upper() if codice_iso2 else codice_iso2,
                              codice_iso3=codice_iso3.strip().upper() if codice_iso3 else codice_iso3,
                              sigla_stato=sigla_stato.strip().upper() if sigla_stato else sigla_stato,
                              codice_telefonico=codice_telefonico,
                              continente=continente)

    # =================================================================
    # Helper interni
    # =================================================================

    # Scopo: GET singolo record per id (helper generico per entita' semplici).
    def _get_by_id(self, table: str, pk: int, columns: str) -> dict[str, Any] | None:
        sql = f"SELECT {columns} FROM {table} WHERE id = %s"  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, [pk])
            return row_to_dict(cursor)

