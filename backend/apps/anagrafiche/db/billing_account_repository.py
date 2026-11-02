# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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

from apps.core.db._helpers import rows_to_list, pattern_contiene

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
         OR script.fn_check_ba_visible_for_emittenti(ba.id, %s::bigint[])
          )
"""
# Scope emittente (ultimo AND sopra): delega alla fn canonica (mapping
# specifico, oppure gestore default SOLO se il BA non ha alcun mapping).
# La vecchia subquery inline era piu' lasca (`... OR efba.is_default = true`
# senza il guard "BA non mappato"): col gestore default in scope mostrava
# anche BA mappati ad altri emittenti (fix 2026-07-13; la RLS, che usa la
# stessa fn, gia' filtrava correttamente — qui e' defense-in-depth).

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
      LEFT JOIN anagrafiche.categorie_clienti cc
        ON cc.id = ba.categoria_cliente_id
      LEFT JOIN config.valute v
        ON v.id = ba.valuta_id
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
    ba.valido_al,
    ba.categoria_cliente_id,
    cc.codice AS categoria_cliente_codice,
    cc.descrizione AS categoria_cliente_descrizione,
    ba.valuta_id,
    v.codice AS valuta_codice,
    v.descrizione AS valuta_descrizione
"""


# Escape wildcard ILIKE centralizzato in core/db/_helpers.escape_ilike
# (regola del 2: era duplicato qui e in istanze_utility_repository).


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
        search_pattern = pattern_contiene(q)

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
        """

        data_sql = f"""
            SELECT
            {_LOOKUP_SELECT_COLUMNS}
            {_LOOKUP_FROM}
            {_LOOKUP_WHERE}
             ORDER BY srd.ragione_sociale_completa ASC NULLS LAST,
                      srd.id_fiscale_univoco_cf_piva ASC NULLS LAST,
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

    # Scopo: Wrapper anagrafiche.fn_get_emittente_fiscale_pk. Ritorna la PK
    #        reale (NON soggetto_ruolo_id, vedi memoria progetto
    #        feedback_emittente_pk_vs_soggetto_ruolo). None se "0 emittenti".
    def get_emittente_fiscale_id(self, billing_account_id: int) -> int | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT anagrafiche.fn_get_emittente_fiscale_pk(%s)",
                [billing_account_id],
            )
            row = cursor.fetchone()
        return int(row[0]) if row and row[0] is not None else None

    # Scopo: Esistenza BA per check 404 prima di scope/lookup.
    def exists(self, billing_account_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM anagrafiche.billing_account WHERE id = %s LIMIT 1",
                [billing_account_id],
            )
            return cursor.fetchone() is not None

    # Scopo: Risolve l'istanza_utility_id del BA (FK NOT NULL sulla tabella).
    #        Usato dai service di dominio per derivare l'istanza quando il
    #        payload specifica solo il BA (es. crea_preventivo).
    # Risultato: int (istanza) oppure None se BA non esiste.
    def get_istanza_utility_id(self, billing_account_id: int) -> int | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT istanza_utility_id FROM anagrafiche.billing_account "
                "WHERE id = %s LIMIT 1",
                [billing_account_id],
            )
            row = cursor.fetchone()
        return int(row[0]) if row and row[0] is not None else None

    # Scopo: Risolve il BA della coppia (istanza, utility). La coppia ne ha al
    #        piu' UNO per struttura (`uq_billing_instance_utility`): non e' una
    #        scelta fra candidati, e' la lettura di una chiave. Con la regola
    #        «l'istanza nasce col BA» (brief-db-istanza-nasce-col-ba, D-2) ogni
    #        utility dichiarata su un'istanza ha il suo BA.
    # Risultato: id del BA, oppure None se la coppia non ha BA (utility non
    #        dichiarata su quell'istanza) o il BA e' fuori dal perimetro RLS.
    def get_id_by_coppia(self, istanza_utility_id: int, utility_id: int) -> int | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM anagrafiche.billing_account "
                "WHERE istanza_utility_id = %s AND utility_id = %s",
                [istanza_utility_id, utility_id],
            )
            row = cursor.fetchone()
        return int(row[0]) if row else None

    # Scopo: Risolve la categoria_cliente_id del BA (FK NOT NULL sulla tabella).
    #        Usato dai gate L2 dei service di dominio (preventivi, contratti)
    #        per alimentare il livello "categoria_cliente" della cascata di
    #        risoluzione parametri (es. VENDITE_MAX_SCONTO_PCT puo' variare per
    #        categoria PREMIUM vs STANDARD, indipendentemente dall'operatore).
    # Risultato: int (categoria) oppure None se BA non esiste.
    def get_categoria_cliente_id(self, billing_account_id: int) -> int | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT categoria_cliente_id FROM anagrafiche.billing_account "
                "WHERE id = %s LIMIT 1",
                [billing_account_id],
            )
            row = cursor.fetchone()
        return int(row[0]) if row and row[0] is not None else None

    # Scopo: Risolve il `soggetti.id` del CLIENTE intestatario del BA, via
    #        `billing_account -> soggetti_ruoli -> soggetti`.
    # Perimetro: sola lettura, nessuno scope (l'id e' gia' noto; il cancello
    #        sta sull'endpoint che ci arriva).
    # Risultato: UUID del soggetto, oppure None se il BA non esiste.
    #
    # ⭐ Nasce il 2026-08-31 per il risolutore IVA, e la ragione e' un difetto
    #    MUTO: `vendite.fn_resolve_iva_riga` applica lo stadio B — i titoli
    #    documentati del soggetto, cioe' le dichiarazioni d'intento — solo se
    #    riceve INSIEME `p_soggetto_id` e `p_emittente_fiscale_id`, e il
    #    soggetto dal billing account NON lo deriva. Un chiamante che ha in
    #    mano il solo BA (il caso ordinario di un form) otterrebbe l'aliquota
    #    ordinaria senza che niente segnali che i titoli non sono stati
    #    nemmeno guardati.
    # ⚠️ E' la STESSA catena che `trgfn_fatture_righe_guard_normalize` percorre
    #    per derivare esigibilita e split payment (I5, `20260829-54`): la
    #    domanda fiscale e' del CLIENTE, non dell'emittente.
    def get_soggetto_id(self, billing_account_id: int) -> str | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT sr.soggetto_id
                  FROM anagrafiche.billing_account ba
                  JOIN anagrafiche.soggetti_ruoli sr
                    ON sr.id = ba.soggetto_ruolo_id
                 WHERE ba.id = %s
                 LIMIT 1
                """,
                [billing_account_id],
            )
            row = cursor.fetchone()
        return str(row[0]) if row and row[0] is not None else None

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
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [billing_account_id])
            rows = rows_to_list(cursor)
        return rows[0] if rows else None

    # Scopo: Risolve la valuta dell'emittente fiscale associato al BA via
    #        anagrafiche.fn_get_emittente_fiscale_pk (catena specifico ->
    #        default globale). Usato come fallback quando ba.valuta_id e' NULL.
    # Perimetro: sola lettura.
    # Risultato: dict {valuta_id, valuta_codice, valuta_descrizione} oppure
    #        dict vuoto se nessun emittente o emittente senza valuta.
    def get_emittente_valuta(self, billing_account_id: int) -> dict[str, Any]:
        sql = """
            SELECT
                ef.valuta_id,
                v.codice      AS valuta_codice,
                v.descrizione AS valuta_descrizione
              FROM anagrafiche.emittenti_fiscali ef
              LEFT JOIN config.valute v ON v.id = ef.valuta_id
             WHERE ef.id = anagrafiche.fn_get_emittente_fiscale_pk(%s)
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [billing_account_id])
            from apps.core.db._helpers import row_to_dict
            row = row_to_dict(cursor)
        if not row or row.get("valuta_id") is None:
            return {}
        return row

    # Scopo: Risolve i campi del cliente associato al BA tramite la tripletta
    #        UNIQUE (istanza_utility_id, soggetto_ruolo_id, utility_id) con
    #        join arricchiti su termini pagamento, IVA e modalita pagamento.
    #        Single point per consumi che vogliono i defaults commerciali del
    #        cliente (es. form-defaults preventivi).
    # Perimetro: sola lettura. Nessun raise: se nessun cliente coincide
    #        (es. BA fornitore o anagrafica gestita altrove) ritorna {}.
    # Risultato: dict con termine_pagamento_id/modalita_pagamento_id
    #        + descrizioni, oppure dict vuoto.
    # ⛔ `iva_id` NON c'e' piu' (2026-08-29, I0/D7-bis): la colonna e' stata
    #    rimossa da `anagrafiche.clienti`. Era l'unico consumatore vero di quella
    #    colonna in tutto il progetto — la restituiva a
    #    `/vendite/preventivi/form-defaults/`, dove il frontend la buttava via.
    def get_cliente_defaults(
        self,
        *,
        istanza_utility_id: int,
        soggetto_ruolo_id: int,
        utility_id: int,
    ) -> dict[str, Any]:
        sql = """
            SELECT
                cl.termine_pagamento_id,
                tp.codice      AS termine_pagamento_codice,
                tp.descrizione AS termine_pagamento_descrizione,
                cl.modalita_pagamento_id,
                mp.codice      AS modalita_pagamento_codice,
                mp.descrizione AS modalita_pagamento_descrizione
              FROM anagrafiche.clienti cl
              LEFT JOIN config.termini_pagamento tp ON tp.id = cl.termine_pagamento_id
              LEFT JOIN config.modalita_pagamento mp ON mp.id = cl.modalita_pagamento_id
             WHERE cl.istanza_utility_id = %s
               AND cl.soggetto_ruolo_id  = %s
               AND cl.utility_id         = %s
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(
                sql, [istanza_utility_id, soggetto_ruolo_id, utility_id],
            )
            from apps.core.db._helpers import row_to_dict
            row = row_to_dict(cursor)
        return row or {}
