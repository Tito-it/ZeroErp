# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per gestione clienti.
#        CRUD clienti, creazione istanza/BA, lista paginata.
#        Accesso DB-first via cursor e funzioni PostgreSQL.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import connection

from apps.anagrafiche.db._helpers import extract_paginated
from apps.core.db._helpers import row_to_dict, rows_to_list


_CLIENTI_ORDER_COLS = {
    "ragione_sociale_completa", "codice_fiscale", "soggetto_codice",
    "ba_codice", "utility_descrizione", "stato_descrizione",
    "data_attivazione", "data_chiusura",
}


class ClientiRepository:
    """Accesso DB per clienti, istanze utilities e billing account."""

    # =================================================================
    # Helpers condivisi (riusabili da service per singoli step)
    # =================================================================

    # Scopo: Restituisce l'id IVA di default da config.parameters (code='DEFAULT_IVA_ID').
    #        Usato come default per clienti creati senza iva_id esplicito.
    #        Delega al building block core ParameterService.
    def get_default_iva_id(self) -> int:
        from apps.core.services.parameter_service import ParameterService
        return ParameterService().get_parameter_int("DEFAULT_IVA_ID")

    # Scopo: Verifica se l'utility ammette creazione manuale (richiede_pdp = false).
    def get_utility(self, utility_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT id, descrizione, codice, richiede_pdp
              FROM config.utilities
             WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [utility_id])
            return row_to_dict(cursor)

    # Scopo: Ottiene o crea il ruolo CLIENTE per un soggetto.
    #        Delega alla funzione DB script.fn_get_or_create_soggetto_ruolo.
    def get_or_create_ruolo_cliente(self, soggetto_id: str) -> int:
        sql = "SELECT script.fn_get_or_create_soggetto_ruolo(%s, 'CL') AS ruolo_id"
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_id])
            row = cursor.fetchone()
            assert row is not None
            return row[0]

    # Scopo: Crea istanza utility fittizia (senza PDP).
    #        Nota: istanze_utilities non ha utility_id; l'utility viene propagata
    #        dal billing_account al cliente tramite trigger trgfn_clienti_sync_utility_from_ba.
    def create_istanza_fittizia(
        self, *, soggetto_id: str,
        indirizzo_dettaglio_id: int | None = None,
    ) -> int:
        sql = """
            INSERT INTO anagrafiche.istanze_utilities
                   (soggetto_id, fittizia, indirizzo_dettaglio_id)
            VALUES (%s, true, %s)
            RETURNING id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_id, indirizzo_dettaglio_id])
            row = cursor.fetchone()
            assert row is not None
            return row[0]

    # Scopo: Wrapper script.fn_check_user_can_create_ba. Vedi WIP refactor
    #        operatore-emittenti Q6 (la motivazione di dominio sta nel service).
    def check_user_can_create_ba(self, auth_user_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT script.fn_check_user_can_create_ba(%s)",
                [auth_user_id],
            )
            row = cursor.fetchone()
        return bool(row[0]) if row else False

    # Scopo: Crea billing account per un'istanza e un ruolo soggetto.
    #        Il codice viene generato dal trigger trgfn_billing_account_gen_codice.
    #        Il default di fatturazione_ordini e' gestito dal DB (CONFERMATO).
    #        L'auto-link BA -> emittente fiscale viene gestito dal trigger
    #        z90 trgfn_billing_account_link_ef leggendo la GUC
    #        app.current_user_id (settata da JwtAuditMiddleware).
    def create_billing_account(
        self, *, istanza_utility_id: int, soggetto_ruolo_id: int,
        utility_id: int, fatturazione_ordini: str | None = None,
        parent_account_id: int | None = None,
    ) -> int:
        # Costruzione dinamica: include fatturazione_ordini solo se esplicitamente fornito
        cols = ["istanza_utility_id", "soggetto_ruolo_id", "utility_id", "parent_account_id"]
        vals = [istanza_utility_id, soggetto_ruolo_id, utility_id, parent_account_id]
        if fatturazione_ordini is not None:
            cols.append("fatturazione_ordini")
            vals.append(fatturazione_ordini)
        placeholders = ", ".join(["%s"] * len(cols))
        sql = f"""
            INSERT INTO anagrafiche.billing_account ({", ".join(cols)})
            VALUES ({placeholders})
            RETURNING id
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            row = cursor.fetchone()
            assert row is not None
            return row[0]

    # Scopo: Crea record cliente con stato ATTIVO.
    #        I trigger DB gestiscono: sync_utility, set_periodo, sync_pdp, guard.
    #        Colonne NOT NULL senza default (iva_id) vengono incluse solo se valorizzate;
    #        il DB ha un default o trigger per i campi NOT NULL rimanenti.
    def create_cliente(self, **kwargs) -> int:
        # Colonne fisse (sempre presenti)
        cols = ["istanza_utility_id", "billing_account_id", "soggetto_ruolo_id",
                "stato_cliente_id", "data_attivazione"]
        vals: list = [kwargs["istanza_utility_id"], kwargs["billing_account_id"],
                      kwargs["soggetto_ruolo_id"]]
        # Espressioni speciali (non parametrizzate)
        special = {
            "stato_cliente_id": "(SELECT id FROM config.stati_cliente WHERE codice_interno = 'AT')",
            "data_attivazione": "CURRENT_DATE",
        }
        # Colonne opzionali: incluse solo se valorizzate (non None)
        _OPTIONAL = [
            "termine_pagamento_id", "modalita_pagamento_id", "iva_id",
            "tipo_gg_scadenza_ft", "nr_giorni_scadenza",
            "cliente_pa", "split_payment",
            "codice_cig", "codice_cup", "codice_commessa",
            "servizio_da_fatturare",
            "garanzia_tipo", "garanzia_importo",
        ]
        for col in _OPTIONAL:
            val = kwargs.get(col)
            if val is not None:
                cols.append(col)
                vals.append(val)
        placeholders = [special.get(c, "%s") for c in cols]
        sql = f"""
            INSERT INTO anagrafiche.clienti ({", ".join(cols)})
            VALUES ({", ".join(placeholders)})
            RETURNING id
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            row = cursor.fetchone()
            assert row is not None
            return row[0]

    # =================================================================
    # Validazione entita' esistenti
    # =================================================================

    # Scopo: Valida che un'istanza esista e appartenga al soggetto.
    def get_istanza(self, istanza_utility_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT id, soggetto_id, utility_id, fittizia, indirizzo_dettaglio_id
              FROM anagrafiche.istanze_utilities
             WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [istanza_utility_id])
            return row_to_dict(cursor)

    # Scopo: Valida che un billing account esista e appartenga all'istanza.
    def get_billing_account(self, billing_account_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT id, istanza_utility_id, soggetto_ruolo_id, utility_id, codice
              FROM anagrafiche.billing_account
             WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [billing_account_id])
            return row_to_dict(cursor)

    # =================================================================
    # Lista e dettaglio
    # =================================================================

    # Scopo: Lista paginata clienti con search e filtri.
    #        Join: clienti + istanza + BA + soggetto + utility + stato.
    #        Scope emittente fiscale: filtra i clienti i cui BA appartengono
    #        agli emittenti autorizzati per l'utente chiamante (refactor
    #        operatore-emittenti, follow-up BE-3.5). `emittente_ids=None`
    #        bypassa il filtro (superuser, admin globale, "0 emittenti");
    #        lista vuota ⇒ nessun risultato. Allineato al pattern del
    #        lookup BA: subquery EXISTS su `emittenti_fiscali_billing_account`
    #        con `is_default = true` come fallback (gestore globale).
    def list_clienti(
        self, *, search: str | None = None,
        utility_id: int | None = None,
        stato_cliente_id: int | None = None,
        emittente_ids: list[int] | None = None,
        limit: int = 25, offset: int = 0,
        order_by: str = "ragione_sociale_completa", order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        order_col = order_by if order_by in _CLIENTI_ORDER_COLS else "ragione_sociale_completa"
        direction = "DESC" if order_dir and order_dir.upper() == "DESC" else "ASC"
        search_pattern = f"%{search.strip()}%" if search and search.strip() else None
        sql = f"""
            SELECT cl.id,
                   cl.istanza_utility_id,
                   cl.soggetto_ruolo_id,
                   s.id AS soggetto_id,
                   s.codice AS soggetto_codice,
                   ba.codice AS ba_codice,
                   s.ragione_sociale_completa,
                   s.codice_fiscale,
                   s.partita_iva,
                   u.descrizione AS utility_descrizione,
                   u.id AS utility_id,
                   sc.descrizione_breve AS stato_descrizione,
                   sc.codice_interno AS stato_codice,
                   cl.data_attivazione,
                   cl.data_chiusura,
                   cl.data_sospensione,
                   cl.data_riattivazione,
                   COUNT(*) OVER () AS total_count
              FROM anagrafiche.clienti cl
              JOIN anagrafiche.istanze_utilities iu ON iu.id = cl.istanza_utility_id
              JOIN anagrafiche.soggetti s ON s.id = iu.soggetto_id
              JOIN anagrafiche.billing_account ba ON ba.id = cl.billing_account_id
              JOIN config.utilities u ON u.id = cl.utility_id
              JOIN config.stati_cliente sc ON sc.id = cl.stato_cliente_id
             WHERE (%s::text IS NULL OR (
                       s.ragione_sociale_completa ILIKE %s
                    OR s.codice_fiscale ILIKE %s
                    OR s.partita_iva ILIKE %s
                    OR ba.codice ILIKE %s
                    OR s.codice ILIKE %s
                   ))
               AND (%s::integer IS NULL OR cl.utility_id = %s)
               AND (%s::integer IS NULL OR cl.stato_cliente_id = %s)
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
             ORDER BY {order_col} {direction}, cl.id
             LIMIT %s OFFSET %s
        """  # noqa: S608
        params = [
            search_pattern, search_pattern, search_pattern,
            search_pattern, search_pattern, search_pattern,
            utility_id, utility_id,
            stato_cliente_id, stato_cliente_id,
            emittente_ids, emittente_ids,
            limit, offset,
        ]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return extract_paginated(cursor)

    # Scopo: Lista utility ammesse per creazione manuale (richiede_pdp = false, attivo).
    def list_utilities_manuali(self) -> list[dict[str, Any]]:
        sql = """
            SELECT id, codice, descrizione
              FROM config.utilities
             WHERE richiede_pdp = false
             ORDER BY descrizione
        """
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return rows_to_list(cursor)

    # Scopo: Dettaglio completo di un cliente con dati istanza, BA, soggetto e FK descrizioni.
    def get_cliente(self, cliente_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT cl.id,
                   cl.istanza_utility_id,
                   cl.billing_account_id,
                   cl.soggetto_ruolo_id,
                   cl.stato_cliente_id,
                   cl.utility_id,
                   cl.pdp_id,
                   cl.data_attivazione,
                   cl.data_sospensione,
                   cl.data_riattivazione,
                   cl.data_chiusura,
                   -- Pagamento
                   cl.tipo_gg_scadenza_ft,
                   cl.nr_giorni_scadenza,
                   cl.termine_pagamento_id,
                   cl.modalita_pagamento_id,
                   cl.iva_id,
                   cl.cliente_pa,
                   cl.split_payment,
                   cl.codice_cig,
                   cl.codice_cup,
                   cl.codice_commessa,
                   cl.servizio_da_fatturare,
                   -- Garanzia
                   cl.garanzia_tipo,
                   cl.garanzia_importo,
                   -- Soggetto
                   s.id AS soggetto_id,
                   s.ragione_sociale_completa,
                   s.codice_fiscale,
                   s.partita_iva,
                   s.tipo_soggetto_dettaglio_id,
                   -- Billing account
                   ba.codice AS ba_codice,
                   ba.fatturazione_ordini AS ba_fatturazione_ordini,
                   ba.parent_account_id AS ba_parent_account_id,
                   ba.valido_dal AS ba_valido_dal,
                   ba.valido_al AS ba_valido_al,
                   -- Istanza
                   iu.fittizia AS istanza_fittizia,
                   iu.indirizzo_dettaglio_id AS istanza_indirizzo_dettaglio_id,
                   iu.codice AS istanza_codice,
                   -- FK descrizioni
                   u.descrizione AS utility_descrizione,
                   sc.codice_interno AS stato_codice,
                   sc.descrizione_breve AS stato_descrizione,
                   iva.descrizione AS iva_descrizione,
                   mp.descrizione AS modalita_pagamento_descrizione,
                   tp.descrizione AS termine_pagamento_descrizione
              FROM anagrafiche.clienti cl
              JOIN anagrafiche.istanze_utilities iu ON iu.id = cl.istanza_utility_id
              JOIN anagrafiche.soggetti s ON s.id = iu.soggetto_id
              JOIN anagrafiche.billing_account ba ON ba.id = cl.billing_account_id
              JOIN config.utilities u ON u.id = cl.utility_id
              JOIN config.stati_cliente sc ON sc.id = cl.stato_cliente_id
              LEFT JOIN config.iva iva ON iva.id = cl.iva_id
              LEFT JOIN config.modalita_pagamento mp ON mp.id = cl.modalita_pagamento_id
              LEFT JOIN config.termini_pagamento tp ON tp.id = cl.termine_pagamento_id
             WHERE cl.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [cliente_id])
            return row_to_dict(cursor)

    # Campi editabili sul cliente (pagamento, PA, garanzia, servizio).
    _UPDATE_ALLOWED = {
        "iva_id", "modalita_pagamento_id", "termine_pagamento_id",
        "tipo_gg_scadenza_ft", "nr_giorni_scadenza",
        "cliente_pa", "split_payment",
        "codice_cig", "codice_cup", "codice_commessa",
        "servizio_da_fatturare",
        "garanzia_tipo", "garanzia_importo",
    }
    _UPDATE_NULLABLE = {
        "iva_id", "modalita_pagamento_id", "termine_pagamento_id",
        "codice_cig", "codice_cup", "codice_commessa",
    }

    # Scopo: Aggiorna campi editabili di un cliente (delta update).
    def update_cliente(self, cliente_id: int, data: dict[str, Any]) -> bool:
        # Normalizza stringhe vuote a None per campi nullable
        for k in self._UPDATE_NULLABLE:
            if k in data and isinstance(data[k], str) and not data[k].strip():
                data[k] = None
        fields = [(k, v) for k, v in data.items() if k in self._UPDATE_ALLOWED]
        if not fields:
            return False
        set_clause = ", ".join(f"{f[0]} = %s" for f in fields)
        values: list[Any] = [f[1] for f in fields]
        values.append(cliente_id)
        sql = f"UPDATE anagrafiche.clienti SET {set_clause} WHERE id = %s"  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, values)
            return cursor.rowcount > 0
