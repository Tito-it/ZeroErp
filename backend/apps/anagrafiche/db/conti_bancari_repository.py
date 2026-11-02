# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per gestione conti bancari.
#        Registro IBAN, legami soggetto ↔ conto, legami ruolo ↔ conto,
#        lookup filiali bancarie. Accesso DB-first via cursor.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import connection

from apps.core.db._helpers import row_to_dict, rows_to_list, pattern_contiene
from apps.core.db.sql_write_helpers import sql_set_clause

# Colonne comuni per le query sui legami (soggetto e ruolo).
# Il blocco JOIN conto_bancari + bank_branches e' identico per tutte le liste.
_LEGAME_CONTO_COLS = """
                   cb.iban, cb.bic_swift, cb.intestatario_predefinito,
                   cb.paese, cb.attivo AS conto_attivo,
                   cb.bank_branch_id,
                   bb.name AS filiale_nome,
                   bb.bank_code, bb.branch_code"""

_LEGAME_CONTO_JOIN = """
              JOIN anagrafiche.conti_bancari cb
                ON cb.id = {alias}.conto_bancario_id
              LEFT JOIN anagrafiche.bank_branches bb
                ON bb.id = cb.bank_branch_id"""

# Colonne SCRIVIBILI dagli update dei legami (BB `sql_set_clause`, whitelist
# RIGIDA dal 2026-09-26: una colonna fuori lista e' `RuntimeError`).
# ⛔ Due liste e non una: `istanza_utility_id` esiste SOLO su
#    `soggetti_ruoli_conti_bancari`. Fino al 2026-09-26 la lista era unica
#    («il filtro avviene a livello service» — ma il service non filtrava): una
#    PATCH del legame SOGGETTO con `istanza_utility_id` componeva un UPDATE su
#    una colonna che non c'e', cioe' un 500 da PostgreSQL.
# ⚠️ Sono il perimetro del REPOSITORY; il contratto del payload lo valida
#    `ContiBancariService` (400), partendo da qui.
LEGAME_SOGGETTO_UPDATE_COLS: frozenset[str] = frozenset({
    "uso", "predefinito", "valido_dal", "valido_al",
    "intestazione_dichiarata", "verificato", "bloccato",
})
LEGAME_RUOLO_UPDATE_COLS: frozenset[str] = LEGAME_SOGGETTO_UPDATE_COLS | {"istanza_utility_id"}
_LEGAME_NULLABLE = {"valido_dal", "valido_al", "intestazione_dichiarata", "istanza_utility_id"}


# Scopo: Normalizza stringhe vuote a None sui campi nullable. Ritorna una
#        COPIA: `data` e' spesso `request.data`, non si muta l'input.
def _normalize_legame_data(data: dict[str, Any]) -> dict[str, Any]:
    valori = dict(data)
    for k in _LEGAME_NULLABLE:
        val = valori.get(k)
        if isinstance(val, str) and not val.strip():
            valori[k] = None
    return valori


# Scopo: UPDATE generico per legami conto bancario (soggetto o ruolo).
#        SET dal BB `sql_set_clause` (2026-09-26), il WHERE di ownership lo
#        scrive questo helper. `table`/`pk_col`/`owner_cast` sono LITERAL dei
#        metodi `update_conto_*`, mai input.
def _update_legame(
    table: str, pk_col: str,
    record_id: int, owner_id: Any, owner_cast: str,
    data: dict[str, Any], allowed: frozenset[str],
) -> bool:
    valori = _normalize_legame_data(data)
    if not valori:
        return False
    set_clause, values = sql_set_clause(valori, allowed=allowed)
    values.extend([record_id, owner_id])
    sql = (
        f"UPDATE {table} SET {set_clause} "  # noqa: S608 — table/pk_col/owner_cast literal dei metodi update_conto_*, SET da sql_set_clause (colonne in whitelist), valori come parametri
        f"WHERE id = %s AND {pk_col} = %s{owner_cast}"
    )
    with connection.cursor() as cursor:
        cursor.execute(sql, values)
        return cursor.rowcount > 0


class ContiBancariRepository:
    """Accesso DB per conti bancari: registro, legami soggetto/ruolo, filiali."""

    # =================================================================
    # Registro IBAN (anagrafiche.conti_bancari)
    # =================================================================

    # Scopo: Ricerca IBAN nel registro per autocomplete frontend.
    #        Restituisce conti attivi con dati filiale e banca.
    def search_conti_bancari(
        self, search: str, limit: int = 10,
    ) -> list[dict[str, Any]]:
        search_pattern = pattern_contiene(search)
        sql = """
            SELECT cb.id, cb.iban, cb.bic_swift,
                   cb.intestatario_predefinito, cb.paese,
                   cb.bank_branch_id, cb.attivo, cb.verificato,
                   bb.name AS filiale_nome,
                   bb.bank_code, bb.branch_code
              FROM anagrafiche.conti_bancari cb
              LEFT JOIN anagrafiche.bank_branches bb
                ON bb.id = cb.bank_branch_id
             WHERE cb.attivo = true
               AND REPLACE(cb.iban, ' ', '') ILIKE REPLACE(%s, ' ', '')
             ORDER BY cb.iban
             LIMIT %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [search_pattern, limit])
            return rows_to_list(cursor)

    # Scopo: Dettaglio singolo conto bancario con dati filiale.
    def get_conto_bancario(self, conto_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT cb.id, cb.iban, cb.bic_swift,
                   cb.intestatario_predefinito, cb.paese,
                   cb.bank_branch_id, cb.attivo, cb.verificato,
                   bb.name AS filiale_nome,
                   bb.bank_code, bb.branch_code
              FROM anagrafiche.conti_bancari cb
              LEFT JOIN anagrafiche.bank_branches bb
                ON bb.id = cb.bank_branch_id
             WHERE cb.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [conto_id])
            return row_to_dict(cursor)

    # Scopo: Cerca un conto per IBAN normalizzato. Se non esiste lo crea.
    #        Il trigger DB normalizza IBAN (uppercase, strip spazi) e deriva paese.
    #        Restituisce (id, created).
    def get_or_create_conto_bancario(
        self, *, iban: str,
        bic_swift: str | None = None,
        bank_branch_id: int,
        intestatario_predefinito: str | None = None,
    ) -> tuple[int, bool]:
        iban_norm = iban.upper().replace(" ", "")
        sql_find = """
            SELECT id FROM anagrafiche.conti_bancari
             WHERE iban = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql_find, [iban_norm])
            row = cursor.fetchone()
            if row is not None:
                return int(row[0]), False

            sql_insert = """
                INSERT INTO anagrafiche.conti_bancari
                    (iban, bic_swift, bank_branch_id, intestatario_predefinito)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """
            cursor.execute(sql_insert, [
                iban, bic_swift, bank_branch_id,
                intestatario_predefinito,
            ])
            new_row = cursor.fetchone()
            assert new_row is not None
            return int(new_row[0]), True

    # =================================================================
    # Legame soggetto ↔ conto (anagrafiche.soggetti_conti_bancari)
    # =================================================================

    # Scopo: Lista conti bancari associati a un soggetto con dati registro e filiale.
    def list_conti_soggetto(self, soggetto_id: str) -> list[dict[str, Any]]:
        sql = f"""
            SELECT scb.id, scb.conto_bancario_id, scb.uso, scb.predefinito,
                   scb.valido_dal::text, scb.valido_al::text,
                   scb.intestazione_dichiarata,
                   scb.verificato, scb.bloccato,
                   {_LEGAME_CONTO_COLS}
              FROM anagrafiche.soggetti_conti_bancari scb
              {_LEGAME_CONTO_JOIN.format(alias='scb')}
             WHERE scb.soggetto_id = %s::uuid
             ORDER BY scb.uso, scb.predefinito DESC, scb.id
        """  # noqa: S608 — _LEGAME_CONTO_COLS/_JOIN costanti di modulo con alias letterale, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_id])
            return rows_to_list(cursor)

    # Scopo: Crea legame soggetto ↔ conto bancario.
    def create_conto_soggetto(
        self, soggetto_id: str, *,
        conto_bancario_id: int,
        uso: str = "GENERICO",
        predefinito: bool = False,
        valido_dal: str | None = None,
        valido_al: str | None = None,
        intestazione_dichiarata: str | None = None,
        verificato: bool = False,
        bloccato: bool = False,
    ) -> dict[str, Any]:
        sql = """
            INSERT INTO anagrafiche.soggetti_conti_bancari
                (soggetto_id, conto_bancario_id, uso, predefinito,
                 valido_dal, valido_al, intestazione_dichiarata,
                 verificato, bloccato)
            VALUES (%s::uuid, %s, %s, %s, %s::date, %s::date, %s, %s, %s)
            RETURNING id, conto_bancario_id, uso, predefinito,
                      valido_dal::text, valido_al::text,
                      intestazione_dichiarata, verificato, bloccato
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                soggetto_id, conto_bancario_id, uso, predefinito,
                valido_dal, valido_al, intestazione_dichiarata,
                verificato, bloccato,
            ])
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # Scopo: Aggiorna legame soggetto ↔ conto con ownership check.
    def update_conto_soggetto(
        self, conto_soggetto_id: int, soggetto_id: str,
        data: dict[str, Any],
    ) -> bool:
        return _update_legame(
            "anagrafiche.soggetti_conti_bancari", "soggetto_id",
            conto_soggetto_id, soggetto_id, "::uuid", data,
            LEGAME_SOGGETTO_UPDATE_COLS,
        )

    # Scopo: Elimina legame soggetto ↔ conto con ownership check.
    def delete_conto_soggetto(
        self, conto_soggetto_id: int, soggetto_id: str,
    ) -> bool:
        sql = """
            DELETE FROM anagrafiche.soggetti_conti_bancari
             WHERE id = %s AND soggetto_id = %s::uuid
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [conto_soggetto_id, soggetto_id])
            return cursor.rowcount > 0

    # =================================================================
    # Legame ruolo ↔ conto (anagrafiche.soggetti_ruoli_conti_bancari)
    # =================================================================

    # Scopo: Lista conti bancari associati a un ruolo con dati registro e filiale.
    #        Include istanza_utility_id per cascata 3 livelli.
    def list_conti_ruolo(self, soggetto_ruolo_id: int) -> list[dict[str, Any]]:
        sql = f"""
            SELECT srcb.id, srcb.conto_bancario_id, srcb.uso, srcb.predefinito,
                   srcb.valido_dal::text, srcb.valido_al::text,
                   srcb.intestazione_dichiarata,
                   srcb.verificato, srcb.bloccato,
                   srcb.istanza_utility_id,
                   (SELECT u.codice FROM config.utilities u
                    WHERE u.id = COALESCE(
                      (SELECT idp.utility_id FROM anagrafiche.istanze_dati_precontrattuali idp
                        WHERE idp.istanza_utility_id = srcb.istanza_utility_id LIMIT 1),
                      (SELECT ba.utility_id FROM anagrafiche.billing_account ba
                        WHERE ba.istanza_utility_id = srcb.istanza_utility_id LIMIT 1)
                    )) AS utility_codice,
                   {_LEGAME_CONTO_COLS}
              FROM anagrafiche.soggetti_ruoli_conti_bancari srcb
              {_LEGAME_CONTO_JOIN.format(alias='srcb')}
             WHERE srcb.soggetto_ruolo_id = %s
             ORDER BY srcb.uso, srcb.predefinito DESC, srcb.id
        """  # noqa: S608 — _LEGAME_CONTO_COLS/_JOIN costanti di modulo con alias letterale, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_ruolo_id])
            return rows_to_list(cursor)

    # Scopo: Lista conti ereditati dal livello soggetto per un dato ruolo.
    #        Utile per mostrare in UI i conti "fallback" (tag Ereditato).
    def list_conti_ereditati_ruolo(
        self, soggetto_ruolo_id: int,
    ) -> list[dict[str, Any]]:
        sql = f"""
            SELECT scb.id, scb.conto_bancario_id, scb.uso, scb.predefinito,
                   scb.valido_dal::text, scb.valido_al::text,
                   scb.intestazione_dichiarata,
                   scb.verificato, scb.bloccato,
                   {_LEGAME_CONTO_COLS}
              FROM anagrafiche.soggetti_conti_bancari scb
              {_LEGAME_CONTO_JOIN.format(alias='scb')}
              JOIN anagrafiche.soggetti_ruoli sr
                ON sr.soggetto_id = scb.soggetto_id
             WHERE sr.id = %s
             ORDER BY scb.uso, scb.predefinito DESC, scb.id
        """  # noqa: S608 — _LEGAME_CONTO_COLS/_JOIN costanti di modulo con alias letterale, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_ruolo_id])
            return rows_to_list(cursor)

    # Scopo: Crea legame ruolo ↔ conto bancario con istanza_utility_id opzionale.
    def create_conto_ruolo(
        self, soggetto_ruolo_id: int, *,
        conto_bancario_id: int,
        uso: str = "GENERICO",
        predefinito: bool = False,
        valido_dal: str | None = None,
        valido_al: str | None = None,
        intestazione_dichiarata: str | None = None,
        verificato: bool = False,
        bloccato: bool = False,
        istanza_utility_id: int | None = None,
    ) -> dict[str, Any]:
        sql = """
            INSERT INTO anagrafiche.soggetti_ruoli_conti_bancari
                (soggetto_ruolo_id, conto_bancario_id, uso, predefinito,
                 valido_dal, valido_al, intestazione_dichiarata,
                 verificato, bloccato, istanza_utility_id)
            VALUES (%s, %s, %s, %s, %s::date, %s::date, %s, %s, %s, %s)
            RETURNING id, conto_bancario_id, uso, predefinito,
                      valido_dal::text, valido_al::text,
                      intestazione_dichiarata, verificato, bloccato,
                      istanza_utility_id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                soggetto_ruolo_id, conto_bancario_id, uso, predefinito,
                valido_dal, valido_al, intestazione_dichiarata,
                verificato, bloccato, istanza_utility_id,
            ])
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # Scopo: Aggiorna legame ruolo ↔ conto con ownership check.
    def update_conto_ruolo(
        self, conto_ruolo_id: int, soggetto_ruolo_id: int,
        data: dict[str, Any],
    ) -> bool:
        return _update_legame(
            "anagrafiche.soggetti_ruoli_conti_bancari", "soggetto_ruolo_id",
            conto_ruolo_id, soggetto_ruolo_id, "", data,
            LEGAME_RUOLO_UPDATE_COLS,
        )

    # Scopo: Elimina legame ruolo ↔ conto con ownership check.
    def delete_conto_ruolo(
        self, conto_ruolo_id: int, soggetto_ruolo_id: int,
    ) -> bool:
        sql = """
            DELETE FROM anagrafiche.soggetti_ruoli_conti_bancari
             WHERE id = %s AND soggetto_ruolo_id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [conto_ruolo_id, soggetto_ruolo_id])
            return cursor.rowcount > 0

    # =================================================================
    # Lettura flag legame (soggetto o ruolo)
    # =================================================================

    # Scopo: Legge predefinito e bloccato di un legame conto (soggetto o ruolo).
    #        Usato dal service per validare coerenza predefinito/bloccato su update.
    def get_legame_flags_soggetto(self, record_id: int) -> dict[str, Any] | None:
        sql = "SELECT predefinito, bloccato FROM anagrafiche.soggetti_conti_bancari WHERE id = %s"
        with connection.cursor() as cursor:
            cursor.execute(sql, [record_id])
            return row_to_dict(cursor)

    def get_legame_flags_ruolo(self, record_id: int) -> dict[str, Any] | None:
        sql = "SELECT predefinito, bloccato FROM anagrafiche.soggetti_ruoli_conti_bancari WHERE id = %s"
        with connection.cursor() as cursor:
            cursor.execute(sql, [record_id])
            return row_to_dict(cursor)

    # =================================================================
    # Lookup filiali bancarie (anagrafiche.bank_branches)
    # =================================================================

    # Scopo: Ricerca filiali bancarie per autocomplete frontend.
    #        Cerca su nome filiale, codice banca, codice filiale e BIC.
    def search_bank_branches(
        self, search: str, limit: int = 10,
    ) -> list[dict[str, Any]]:
        search_pattern = pattern_contiene(search)
        sql = """
            SELECT bb.id, bb.name AS filiale_nome,
                   bb.bank_code, bb.branch_code,
                   bb.bic_swift, bb.attivo
              FROM anagrafiche.bank_branches bb
             WHERE bb.attivo = true
               AND (bb.name ILIKE %s
                 OR bb.bank_code ILIKE %s
                 OR bb.branch_code ILIKE %s
                 OR bb.bic_swift ILIKE %s)
             ORDER BY bb.name, bb.branch_code
             LIMIT %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                search_pattern, search_pattern,
                search_pattern, search_pattern,
                limit,
            ])
            return rows_to_list(cursor)
