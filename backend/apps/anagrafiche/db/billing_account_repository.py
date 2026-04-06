# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository SQL per billing_account — lookup ricco riusabile cross-dominio
#        (righe listini, preventivi, ordini, fatture, pratiche).
#        Ricerca multi-campo (codice, ragione sociale, id fiscale, PDP) con JOIN
#        a istanze_utilities/pdp e vw_soggetti_ruoli_dettaglio, filtro utility,
#        filtro validita' temporale e scope emittente fiscale.
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from typing import Any

from django.db import connection

from apps.core.db._helpers import rows_to_list

# Scopo: Clausole WHERE condivise tra query count e query data del lookup BA.
# Mantenere allineate le due query: qualsiasi nuovo filtro va aggiunto qui.
_LOOKUP_WHERE = """
    WHERE (
            ba.codice ILIKE %s
         OR srd.ragione_sociale_completa ILIKE %s
         OR srd.id_fiscale_univoco_cf_piva ILIKE %s
         OR p.pdp ILIKE %s
          )
      AND (%s::integer IS NULL OR ba.utility_id = %s)
      AND (
            %s::date IS NULL
         OR (
              (ba.valido_dal IS NULL OR ba.valido_dal <= %s::date)
              AND (ba.valido_al IS NULL OR ba.valido_al >= %s::date)
            )
          )
      AND (
            %s::bigint[] IS NULL
         OR EXISTS (
              SELECT 1
                FROM anagrafiche.emittenti_fiscali_billing_account efba
               WHERE efba.emittente_soggetto_ruolo_id = ANY(%s::bigint[])
                 AND (
                       efba.billing_account_id = ba.id
                    OR efba.is_default = true
                     )
            )
          )
"""

# Scopo: JOIN comuni a count e data del lookup BA.
_LOOKUP_FROM = """
      FROM anagrafiche.billing_account ba
      JOIN anagrafiche.istanze_utilities iu
        ON iu.id = ba.istanza_utility_id
      LEFT JOIN anagrafiche.pdp p
        ON p.id = iu.pdp_id
      JOIN config.utilities u
        ON u.id = ba.utility_id
      LEFT JOIN anagrafiche.vw_soggetti_ruoli_dettaglio srd
        ON srd.soggetto_ruolo_id = ba.soggetto_ruolo_id
      LEFT JOIN anagrafiche.billing_account parent
        ON parent.id = ba.parent_account_id
"""

# Scopo: Proiezione SELECT condivisa tra search_lookup (lista) e get_lookup_by_id (restore).
# Mantenere allineati i campi esposti al frontend (componente BillingAccountLookup).
_LOOKUP_SELECT_COLUMNS = """
    ba.id,
    ba.codice,
    ba.parent_account_id,
    parent.codice AS parent_codice,
    ba.utility_id,
    u.codice AS utility_codice,
    u.descrizione AS utility_descrizione,
    ba.soggetto_ruolo_id,
    srd.ragione_sociale_completa,
    srd.id_fiscale_univoco_cf_piva AS id_fiscale,
    ba.istanza_utility_id,
    iu.fittizia AS istanza_fittizia,
    p.pdp AS pdp,
    ba.valido_dal,
    ba.valido_al
"""


# Scopo: Effettua l'escape dei caratteri wildcard ILIKE (\, %, _) per evitare
# match indesiderati quando l'utente cerca stringhe contenenti tali caratteri
# (es. "BA_123" o "50%"). L'escape di backslash va fatto per primo.
def _escape_ilike(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class BillingAccountRepository:
    """Repository billing_account: lookup autocomplete e restore per edit."""

    # Scopo: Cerca billing_account per autocomplete con JOIN ricchi (soggetto, pdp, utility).
    #        Applica filtri: ricerca testuale multi-campo, utility, validita' temporale,
    #        scope emittente fiscale. Ordinamento alfabetico su ragione sociale poi id fiscale.
    # Perimetro: sola lettura. Il cap risultati e' gestito dal chiamante.
    # Risultato: tuple (list[dict], total_count) per gestione UI "affina ricerca".
    def search_lookup(
        self,
        *,
        q: str,
        utility_id: int | None,
        solo_validi: bool,
        valid_at: date | None,
        emittente_ids: list[int] | None,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        # Pattern ILIKE su 4 colonne in OR per ricerca testuale.
        # Escape wildcard per evitare match indesiderati su '%' e '_' nei dati utente.
        search_pattern = f"%{_escape_ilike(q)}%"

        # Scope emittente: lista di ruoli emittente autorizzati, None = bypass (superuser).
        # Una lista vuota significa "operatore senza emittenti autorizzati": in quel caso
        # passiamo l'array vuoto al filtro (nessun BA matcha), NON None (che farebbe bypass).
        scope_array = emittente_ids if emittente_ids is not None else None

        # valid_at e' applicato solo se solo_validi=True.
        effective_valid_at: date | None = valid_at if solo_validi else None

        # Parametri condivisi tra count e data query (stessa clausola WHERE).
        where_params = [
            search_pattern, search_pattern, search_pattern, search_pattern,
            utility_id, utility_id,
            effective_valid_at, effective_valid_at, effective_valid_at,
            scope_array, scope_array,
        ]

        count_sql = f"""
            SELECT COUNT(*)
            {_LOOKUP_FROM}
            {_LOOKUP_WHERE}
        """  # noqa: S608

        data_sql = f"""
            SELECT
            {_LOOKUP_SELECT_COLUMNS}
            {_LOOKUP_FROM}
            {_LOOKUP_WHERE}
             ORDER BY srd.ragione_sociale_completa ASC NULLS LAST,
                      srd.id_fiscale_univoco_cf_piva ASC NULLS LAST,
                      ba.id ASC
             LIMIT %s
        """  # noqa: S608

        with connection.cursor() as cursor:
            cursor.execute(count_sql, where_params)
            row = cursor.fetchone()
            assert row is not None
            total_count = int(row[0])

            cursor.execute(data_sql, where_params + [limit])
            rows = rows_to_list(cursor)

        return rows, total_count

    # Scopo: Restituisce il singolo billing_account arricchito per restore lato client.
    #        Usato in edit quando il form ha solo l'id e deve ricostruire il _obj
    #        dell'AutoComplete senza doppio round-trip.
    # Perimetro: sola lettura. Non applica scope emittente (l'id e' gia' noto e
    #        l'autorizzazione va gestita dall'endpoint chiamante).
    # Risultato: dict con gli stessi campi di search_lookup, o None se non trovato.
    def get_lookup_by_id(self, billing_account_id: int) -> dict[str, Any] | None:
        sql = f"""
            SELECT
            {_LOOKUP_SELECT_COLUMNS}
            {_LOOKUP_FROM}
             WHERE ba.id = %s
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, [billing_account_id])
            rows = rows_to_list(cursor)
        return rows[0] if rows else None
