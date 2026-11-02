# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository SQL per istanze_utilities — lookup ricco riusabile
#        cross-dominio: la scelta del cliente per FORNITURA (preventivi,
#        pratiche). Una riga per billing account, cioe' per coppia (istanza,
#        utility). Ricerca multi-campo (codice istanza, ragione sociale
#        soggetto, indirizzo normalizzato), filtri utility / soggetto / ruolo,
#        scope emittente fiscale del BA della riga.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import connection

from apps.core.db._helpers import row_to_dict, rows_to_list, pattern_contiene

# ⭐ Modello (brief-db-istanza-nasce-col-ba, 2026-10-08): l'istanza nasce e vive
#    col suo billing account, uno per ogni utility dichiarata (D-2), e il BA e'
#    del ruolo CLIENTE del soggetto (D-3). Quindi:
#    - la riga del lookup e' il BA: un'istanza con due utility ha due righe, ed
#      e' cosi' che chi sceglie (la pratica, D-9) sceglie il cliente a grana
#      fine. Fino al 2026-10-08 la riga era l'istanza con un BA «campione»
#      (`LIMIT 1`): su un'istanza multi-utility mostrava il BA e la utility di
#      un'altra coppia, e il badge «Solo istanza» copriva le istanze senza BA;
#    - il ruolo si lega dal BA (`ba.soggetto_ruolo_id`), non da `clienti`: un
#      ruolo CL col BA e senza la riga cliente (la fase del preventivo) ha le
#      sue forniture, e un'istanza ha tanti clienti quanti BA (R-8).

# Scopo: clausola scope emittente dell'istanza, per il restore per id: un'istanza
#        e' visibile se e' visibile un suo BA (con R-7 tutti i suoi BA sono dello
#        stesso emittente, quindi «un suo BA» e' una risposta sola). Richiede
#        l'alias `iu`. 2 parametri posizionali: emittente_ids, emittente_ids
#        (NULL = bypass, admin globale/superuser).
# ⛔ Fino al 2026-10-08 il restore per id NON la applicava («l'autorizzazione
#    va gestita dall'endpoint chiamante») e l'endpoint, con `skip_area_check`,
#    non la gestiva: con un id si leggeva qualunque istanza di qualunque
#    emittente (D10-bis di migliorie-generali-BE-FE-da-test-valutazione).
_SCOPE_EMITTENTE_SQL = """(
            %s::bigint[] IS NULL
         OR EXISTS (
              SELECT 1
                FROM anagrafiche.billing_account ba_s
               WHERE ba_s.istanza_utility_id = iu.id
                 AND script.fn_check_ba_visible_for_emittenti(
                       ba_s.id, %s::bigint[])
            )
          )"""

# Scopo: Clausole WHERE condivise tra query count e query data del lookup
# (una riga per BA, alias `ba`). Mantenere allineate le due query: qualsiasi
# nuovo filtro va aggiunto qui.
# - ricerca testuale ILIKE su codice istanza, ragione_sociale soggetto e
#   indirizzo_normalizzato (display friendly);
# - utility_id: la utility della riga, cioe' del suo BA. ⚠️ Non
#   `script.fn_check_utility_istanza_coerenza(iu.id, …)`: quella risponde per
#   l'ISTANZA (ha un BA di quella utility?) e con una riga per BA lascerebbe
#   passare anche i BA delle altre utility della stessa istanza;
# - soggetto_id: filtro diretto su iu.soggetto_id;
# - soggetto_ruolo_id: i BA di quel ruolo (le forniture del cliente), dal BA;
# - scope emittente: la visibilita' del BA della riga, delegata alla fn
#   canonica script.fn_check_ba_visible_for_emittenti (mapping specifico,
#   oppure gestore default SOLO se il BA non ha alcun mapping).
_LOOKUP_WHERE = """
    WHERE (
            %s::text IS NULL
         OR iu.codice ILIKE %s
         OR s.ragione_sociale_completa ILIKE %s
         OR vid.indirizzo_normalizzato ILIKE %s
          )
      AND (%s::integer IS NULL OR ba.utility_id = %s)
      AND (%s::uuid IS NULL OR iu.soggetto_id = %s)
      AND (%s::bigint IS NULL OR ba.soggetto_ruolo_id = %s)
      AND (
            %s::bigint[] IS NULL
         OR script.fn_check_ba_visible_for_emittenti(ba.id, %s::bigint[])
          )
"""

# Scopo: JOIN comuni a count e data del lookup: la riga e' il BA, l'istanza e
#        il resto la vestono.
# - soggetti: ragione sociale per display + ricerca
# - vw_indirizzi_dettaglio: indirizzo_normalizzato per ricerca + display
# - pdp: codice punto di prelievo (se istanza ne ha uno); nullable
_LOOKUP_FROM = """
      FROM anagrafiche.billing_account ba
      JOIN anagrafiche.istanze_utilities iu
        ON iu.id = ba.istanza_utility_id
      JOIN config.utilities u
        ON u.id = ba.utility_id
      LEFT JOIN anagrafiche.soggetti s
        ON s.id = iu.soggetto_id
      LEFT JOIN anagrafiche.vw_indirizzi_dettaglio vid
        ON vid.indirizzo_dettaglio_id = iu.indirizzo_dettaglio_id
      LEFT JOIN anagrafiche.pdp p
        ON p.id = iu.pdp_id
"""

# Scopo: Proiezione SELECT condivisa tra search_lookup (una riga per BA) e
# get_lookup_by_id (l'istanza; alias `ba`/`u` dal BA unico, se c'e'). Mantenere
# allineati i campi esposti al frontend (componente IstanzaUtilityLookup).
# `id` resta l'id dell'ISTANZA (e' cio' che i form scrivono in
# istanza_utility_id); il BA della riga e' `billing_account_id`.
_LOOKUP_SELECT_COLUMNS = """
    iu.id,
    iu.codice,
    iu.fittizia,
    iu.soggetto_id,
    s.ragione_sociale_completa,
    s.id_fiscale_univoco_cf_piva AS id_fiscale,
    iu.indirizzo_dettaglio_id,
    vid.indirizzo_normalizzato AS indirizzo_display,
    iu.pdp_id,
    p.pdp                   AS pdp_codice,
    ba.id                   AS billing_account_id,
    ba.codice               AS billing_account_codice,
    ba.utility_id           AS utility_id,
    u.codice                AS utility_codice,
    u.descrizione           AS utility_descrizione
"""

# Scopo: FROM del restore per id: l'ISTANZA, col BA solo se e' UNO. Un'istanza
#        con piu' utility ha piu' BA, e il restore — che conosce solo l'id
#        dell'istanza — non ha modo di sceglierne uno: mai un `LIMIT 1`, che
#        risponderebbe con la coppia sbagliata senza dirlo.
_RESTORE_FROM = """
      FROM anagrafiche.istanze_utilities iu
      LEFT JOIN LATERAL (
            SELECT b.id, b.codice, b.utility_id
              FROM anagrafiche.billing_account b
             WHERE b.istanza_utility_id = iu.id
               AND NOT EXISTS (
                     SELECT 1
                       FROM anagrafiche.billing_account b2
                      WHERE b2.istanza_utility_id = iu.id
                        AND b2.id <> b.id
                   )
           ) ba ON true
      LEFT JOIN config.utilities u
        ON u.id = ba.utility_id
      LEFT JOIN anagrafiche.soggetti s
        ON s.id = iu.soggetto_id
      LEFT JOIN anagrafiche.vw_indirizzi_dettaglio vid
        ON vid.indirizzo_dettaglio_id = iu.indirizzo_dettaglio_id
      LEFT JOIN anagrafiche.pdp p
        ON p.id = iu.pdp_id
"""


# Escape wildcard ILIKE centralizzato in core/db/_helpers.escape_ilike
# (regola del 2: era duplicato qui e in billing_account_repository).


class IstanzeUtilityRepository:
    """Repository istanze_utilities: lookup autocomplete e restore per edit."""

    # Scopo: Cerca le forniture per autocomplete: una riga per BA, cioe' per
    #        coppia (istanza, utility), vestita con soggetto, indirizzo e PDP
    #        dell'istanza. Filtri: ricerca testuale, utility del BA, soggetto,
    #        ruolo del BA, scope emittente del BA. Ordinamento alfabetico
    #        ragione sociale, poi istanza e utility.
    # Perimetro: sola lettura. Cap risultati gestito dal chiamante.
    # Risultato: tuple (list[dict], total_count) per gestione UI "affina ricerca".
    def search_lookup(
        self,
        *,
        q: str,
        utility_id: int | None,
        soggetto_id: str | None,
        soggetto_ruolo_id: int | None = None,
        emittente_ids: list[int] | None,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        # Pattern ILIKE su 3 colonne (codice, ragione sociale, indirizzo).
        # ⛔ `None` quando q e' vuota (ammessa col perimetro, vedi il service):
        #    senza la guardia `%s::text IS NULL` del WHERE diventerebbe
        #    `ILIKE NULL`, cioe' ZERO righe — la tendina del drawer pratiche
        #    vuota con un 200 (2026-09-26, era `%%` = tutte prima di
        #    `pattern_contiene`).
        search_pattern = pattern_contiene(q)

        # Scope emittente: lista sr_ids autorizzati, None = bypass (superuser/admin globale).
        scope_array = emittente_ids if emittente_ids is not None else None

        # Parametri condivisi tra count e data query (stessa clausola WHERE).
        # Layout: guardia + 3 ILIKE + 2 utility + 2 soggetto + 2 ruolo + 2 scope.
        where_params = [
            search_pattern, search_pattern, search_pattern, search_pattern,
            utility_id, utility_id,
            soggetto_id, soggetto_id,
            soggetto_ruolo_id, soggetto_ruolo_id,
            scope_array, scope_array,
        ]

        count_sql = f"""
            SELECT COUNT(*)
            {_LOOKUP_FROM}
            {_LOOKUP_WHERE}
        """

        data_sql = f"""
            SELECT
            {_LOOKUP_SELECT_COLUMNS}
            {_LOOKUP_FROM}
            {_LOOKUP_WHERE}
             ORDER BY s.ragione_sociale_completa ASC NULLS LAST,
                      iu.codice ASC,
                      iu.id ASC,
                      u.codice ASC,
                      ba.id ASC
             LIMIT %s
        """

        with connection.cursor() as cursor:
            cursor.execute(count_sql, where_params)
            row = cursor.fetchone()
            assert row is not None
            total_count = int(row[0])

            cursor.execute(data_sql, where_params + [limit])
            rows = rows_to_list(cursor)

        return rows, total_count

    # Scopo: Esistenza istanza per check 404 prima di scope/lookup.
    def exists(self, istanza_utility_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM anagrafiche.istanze_utilities WHERE id = %s LIMIT 1",
                [istanza_utility_id],
            )
            return cursor.fetchone() is not None

    # Scopo: Restituisce la singola istanza arricchita per restore lato client.
    #        Usato quando il form ha solo l'id dell'istanza (il preventivo
    #        aperto da una pratica senza BA) e deve ricostruire il _obj
    #        dell'AutoComplete. I campi del BA ci sono solo se l'istanza ne ha
    #        UNO (`_RESTORE_FROM`).
    # Perimetro: sola lettura, con lo STESSO scope emittente della ricerca
    #        (`_SCOPE_EMITTENTE_SQL`): il restore risponde solo su cio' che la
    #        ricerca avrebbe potuto proporre. `emittente_ids` e' obbligatorio
    #        di proposito — None e' il bypass, e va detto dal chiamante.
    # Risultato: dict con gli stessi campi di search_lookup, o None se non
    #        trovato O fuori scope (indistinguibili per chi chiama: un id
    #        fuori perimetro non rivela di esistere).
    def get_lookup_by_id(
        self, istanza_utility_id: int, *, emittente_ids: list[int] | None,
    ) -> dict[str, Any] | None:
        sql = f"""
            SELECT
            {_LOOKUP_SELECT_COLUMNS}
            {_RESTORE_FROM}
             WHERE iu.id = %s
               AND {_SCOPE_EMITTENTE_SQL}
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [istanza_utility_id, emittente_ids, emittente_ids])
            row = row_to_dict(cursor)
        return row or None
