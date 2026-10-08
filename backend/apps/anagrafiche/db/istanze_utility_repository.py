# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository SQL per istanze_utilities — lookup ricco riusabile
#        cross-dominio (preventivi prospect senza BA, future utility-aware
#        flows). Pattern simmetrico a BillingAccountRepository: ricerca
#        multi-campo (codice istanza, ragione sociale soggetto, indirizzo
#        normalizzato), filtro utility coerente (BA / IDP / clienti), filtro
#        soggetto, scope emittente fiscale via BA collegato.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import connection

from apps.core.db._helpers import row_to_dict, rows_to_list, pattern_contiene

# Scopo: Clausole WHERE condivise tra query count e query data del lookup
# istanze. Mantenere allineate le due query: qualsiasi nuovo filtro va aggiunto qui.
#
# Regole:
# - ricerca testuale ILIKE su codice istanza, ragione_sociale soggetto e
#   indirizzo_normalizzato (display friendly)
# - utility_id: strict (post Strategia C ogni istanza dichiara utility via
#   billing_account / istanze_dati_precontrattuali / clienti). Delega a
#   script.fn_check_utility_istanza_coerenza per single source of truth: se
#   la regola DB cambia (es. nuovi satelliti), il filtro lookup la segue
#   automaticamente. Stessa fn usata dal trigger DB
#   trgfn_preventivi_guard_utility_istanza_coerenza.
# - soggetto_id: filtro diretto su iu.soggetto_id
# - soggetto_ruolo_id: solo le istanze legate a quel ruolo via clienti
#   (combo ristretta alle forniture del cliente/BA selezionato — evita
#   l'aggancio errato a istanze del soggetto estranee al rapporto cliente)
# - scope emittente: catena via BA della stessa istanza, con visibilita' del
#   singolo BA delegata alla fn canonica script.fn_check_ba_visible_for_emittenti
#   (mapping specifico, oppure gestore default SOLO se il BA non ha alcun
#   mapping — fix 2026-07-13: il vecchio JOIN inline `... OR is_default=true`
#   era piu' lasco e col gestore default in scope mostrava anche istanze di BA
#   mappati ad altri emittenti). Le istanze totalmente orfane (no BA) restano
#   visibili solo ad admin globale / superuser.
# Scopo: clausola scope emittente dell'istanza, condivisa fra la ricerca e il
#        restore per id (regola del 2): un'istanza e' visibile se e' visibile
#        un suo BA. Richiede l'alias `iu`. 2 parametri posizionali:
#        emittente_ids, emittente_ids (NULL = bypass, admin globale/superuser).
# ⛔ Fino al 2026-10-08 il restore per id NON la applicava («l'autorizzazione
#    va gestita dall'endpoint chiamante») e l'endpoint, con `skip_area_check`,
#    non la gestiva: con un id si leggeva qualunque istanza di qualunque
#    emittente (D10-bis di migliorie-generali-BE-FE-da-test-valutazione).
# ⭐ Regola di modello (Tid, 2026-10-08): istanza e BA nascono INSIEME, sempre.
#    Un'istanza senza BA non e' un caso da rendere visibile: e' un dato fuori
#    regola (brief-db-istanza-nasce-col-ba).
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

_LOOKUP_WHERE = f"""
    WHERE (
            %s::text IS NULL
         OR iu.codice ILIKE %s
         OR s.ragione_sociale_completa ILIKE %s
         OR vid.indirizzo_normalizzato ILIKE %s
          )
      AND (
            %s::integer IS NULL
         OR script.fn_check_utility_istanza_coerenza(iu.id, %s)
          )
      AND (%s::uuid IS NULL OR iu.soggetto_id = %s)
      AND (
            %s::bigint IS NULL
         OR EXISTS (
              SELECT 1
                FROM anagrafiche.clienti cl
               WHERE cl.istanza_utility_id = iu.id
                 AND cl.soggetto_ruolo_id = %s
            )
          )
      AND {_SCOPE_EMITTENTE_SQL}
"""  # noqa: S608 — frammenti costanti di modulo, i valori viaggiano nei params

# Scopo: JOIN comuni a count e data del lookup istanze.
# - soggetti: ragione sociale per display + ricerca
# - vw_indirizzi_dettaglio: indirizzo_normalizzato per ricerca + display
# - pdp: codice punto di prelievo (se istanza ne ha uno); nullable
# - ba_first (LATERAL): codice BA campione per badge UI; istanze totalmente
#   orfane (no BA) hanno tutti i campi ba_first.* a NULL → il FE le mostra
#   col badge "Solo istanza".
_LOOKUP_FROM = """
      FROM anagrafiche.istanze_utilities iu
      LEFT JOIN anagrafiche.soggetti s
        ON s.id = iu.soggetto_id
      LEFT JOIN anagrafiche.vw_indirizzi_dettaglio vid
        ON vid.indirizzo_dettaglio_id = iu.indirizzo_dettaglio_id
      LEFT JOIN anagrafiche.pdp p
        ON p.id = iu.pdp_id
      LEFT JOIN LATERAL (
            SELECT ba.id AS ba_id, ba.codice AS ba_codice, ba.utility_id AS ba_utility_id
              FROM anagrafiche.billing_account ba
             WHERE ba.istanza_utility_id = iu.id
             ORDER BY ba.id
             LIMIT 1
           ) ba_first ON true
      LEFT JOIN config.utilities u_first
        ON u_first.id = ba_first.ba_utility_id
"""

# Scopo: Proiezione SELECT condivisa tra search_lookup (lista) e
# get_lookup_by_id (restore). Mantenere allineati i campi esposti al
# frontend (componente IstanzaUtilityLookup).
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
    ba_first.ba_id          AS billing_account_id,
    ba_first.ba_codice      AS billing_account_codice,
    ba_first.ba_utility_id  AS utility_id,
    u_first.codice          AS utility_codice,
    u_first.descrizione     AS utility_descrizione
"""


# Escape wildcard ILIKE centralizzato in core/db/_helpers.escape_ilike
# (regola del 2: era duplicato qui e in billing_account_repository).


class IstanzeUtilityRepository:
    """Repository istanze_utilities: lookup autocomplete e restore per edit."""

    # Scopo: Cerca istanze_utilities per autocomplete con JOIN ricchi
    #        (soggetto, indirizzo, BA campione). Applica filtri: ricerca testuale,
    #        utility (coerente con BA/IDP/clienti), soggetto, scope emittente
    #        fiscale via BA collegato. Ordinamento alfabetico ragione sociale.
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
        # Layout (post refactor con fn_check_utility_istanza_coerenza):
        #   guardia + 3 ILIKE + 2 utility_id (cast IS NULL + fn arg)
        #   + 2 soggetto + 2 soggetto_ruolo + 2 scope
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
                      iu.id ASC
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
    #        Usato in edit quando il form ha solo l'id e deve ricostruire il _obj
    #        dell'AutoComplete senza doppio round-trip.
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
            {_LOOKUP_FROM}
             WHERE iu.id = %s
               AND {_SCOPE_EMITTENTE_SQL}
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [istanza_utility_id, emittente_ids, emittente_ids])
            row = row_to_dict(cursor)
        return row or None

    # Scopo: Wrapper su script.fn_check_utility_istanza_coerenza per pre-validazione
    #        coerenza coppia (istanza, utility) prima dell'INSERT preventivo.
    #        Migliore UX: errore parlante prima del trigger DB. Defense-in-depth:
    #        il trigger _a10_guard_utility_istanza_coerenza_ins_upd applica la
    #        stessa regola in DB.
    # Risultato: True se coerente, False altrimenti.
    def check_utility_istanza_coerenza(
        self, istanza_utility_id: int, utility_id: int,
    ) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT script.fn_check_utility_istanza_coerenza(%s, %s)",
                [istanza_utility_id, utility_id],
            )
            row = cursor.fetchone()
        return bool(row and row[0])
