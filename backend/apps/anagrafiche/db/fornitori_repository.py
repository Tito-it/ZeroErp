# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per gestione fornitori.
#        CRUD fornitori, lista paginata su vw_fornitori_dettaglio.
#        Accesso DB-first via cursor e funzioni PostgreSQL.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import connection

from apps.anagrafiche.db._helpers import get_or_create_soggetto_ruolo
from apps.core.db._helpers import extract_paginated, row_to_dict, sql_order_direction, sql_tiebreak_direction


# Whitelist colonne ammesse per ORDER BY: chiave = `campo_sorgente` del catalogo
# 'anagrafiche.fornitori', valore = colonna della vista `vw_fornitori_dettaglio`
# (alias `v`).
#
# `codice_fiscale`, `partita_iva` e `attivo` sono uscite il 2026-07-31: le prime
# due perche' le colonne omonime del catalogo sono state disattivate (l'id
# fiscale a video e' SEMPRE `id_fiscale_univoco_cf_piva`, che concatena CF e
# P.IVA quando differiscono, quindi e' un sovrainsieme), `attivo` perche' nessuna
# colonna del catalogo la espone.
_FORNITORI_ORDER_COLS: dict[str, str] = {
    "codice": "v.codice",
    "ragione_sociale_completa": "v.ragione_sociale_completa",
    "id_fiscale_univoco_cf_piva": "v.id_fiscale_univoco_cf_piva",
    "stato_descrizione": "v.stato_descrizione",
    "modalita_pagamento_desc": "v.modalita_pagamento_desc",
    "data_insert": "v.data_insert",
    "data_update": "v.data_update",
}


class FornitoriRepository:
    """Accesso DB per fornitori."""

    # =================================================================
    # Creazione
    # =================================================================

    # Scopo: Ottiene o crea il ruolo FORNITORE per un soggetto.
    #        Delega alla funzione DB script.fn_get_or_create_soggetto_ruolo.
    def get_or_create_ruolo_fornitore(self, soggetto_id: str) -> int:
        return get_or_create_soggetto_ruolo(soggetto_id, 'FO')

    # Scopo: Crea record fornitore.
    #        I trigger DB gestiscono: guard ruolo, normalize, audit, tx_id, storicizzazione.
    #        Il codice viene generato dal meccanismo centralizzato config.sistema_codici.
    def create_fornitore(self, **kwargs: Any) -> int:
        # Colonne fisse (sempre presenti)
        cols = ["soggetto_ruolo_id", "stato_fornitore_id"]
        vals: list[Any] = [kwargs["soggetto_ruolo_id"]]
        # Espressioni speciali (non parametrizzate)
        special = {
            "stato_fornitore_id": "(SELECT id FROM config.stati_fornitore WHERE codice_interno = 'VE')",
        }
        # Colonne opzionali: incluse solo se valorizzate (non None)
        _OPTIONAL = [
            "codice",
            "valuta_id", "modalita_pagamento_id", "termine_pagamento_id",
            "giorni_pagamento", "fine_mese",
            "split_payment", "ritenuta_acconto", "ritenuta_aliquota",
            "regime_fiscale", "bollo_esente",
            "canale_fe", "pec_email",
            "rating", "qualifica_scadenza",
            "note",
        ]
        for col in _OPTIONAL:
            val = kwargs.get(col)
            if val is not None:
                cols.append(col)
                vals.append(val)
        placeholders = [special.get(c, "%s") for c in cols]
        sql = f"""
            INSERT INTO anagrafiche.fornitori ({", ".join(cols)})
            VALUES ({", ".join(placeholders)})
            RETURNING id
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            row = cursor.fetchone()
            assert row is not None
            return row[0]

    # =================================================================
    # Lista e dettaglio
    # =================================================================

    # Scopo: Lista paginata fornitori con search e filtri.
    #        Usa la vista vw_fornitori_dettaglio per join pre-calcolati.
    def list_fornitori(
        self, *, search: str | None = None,
        stato_fornitore_id: int | None = None,
        attivo: bool | None = None,
        limit: int = 25, offset: int = 0,
        order_by: str = "ragione_sociale_completa", order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        order_col = _FORNITORI_ORDER_COLS.get(
            order_by, _FORNITORI_ORDER_COLS["ragione_sociale_completa"]
        )
        direction = sql_order_direction(order_dir)
        tiebreak_dir = sql_tiebreak_direction(direction)
        search_pattern = f"%{search.strip()}%" if search and search.strip() else None
        sql = f"""
            SELECT v.id,
                   v.soggetto_ruolo_id,
                   v.codice,
                   v.attivo,
                   v.stato_codice_interno,
                   v.stato_codice,
                   v.stato_descrizione,
                   v.blocca_ordini,
                   v.soggetto_id,
                   v.ragione_sociale_completa,
                   v.codice_fiscale,
                   v.partita_iva,
                   v.id_fiscale_univoco_cf_piva,
                   v.valuta_iso,
                   v.modalita_pagamento_codice,
                   v.modalita_pagamento_desc,
                   v.termine_pagamento_codice,
                   v.giorni_pagamento,
                   v.fine_mese,
                   v.split_payment,
                   v.ritenuta_acconto,
                   v.regime_fiscale,
                   v.rating,
                   v.qualifica_scadenza,
                   v.canale_fe,
                   v.pec_email,
                   v.data_insert,
                   v.data_update,
                   COUNT(*) OVER () AS total_count
              FROM anagrafiche.vw_fornitori_dettaglio v
             WHERE (%s::text IS NULL OR (
                       v.ragione_sociale_completa ILIKE %s
                    OR v.codice_fiscale ILIKE %s
                    OR v.partita_iva ILIKE %s
                    OR v.codice ILIKE %s
                   ))
               AND (%s::integer IS NULL OR v.stato_fornitore_id = %s)
               AND (%s::boolean IS NULL OR v.attivo = %s)
             ORDER BY {order_col} {direction}, v.id {tiebreak_dir}
             LIMIT %s OFFSET %s
        """  # noqa: S608
        params: list[Any] = [
            search_pattern, search_pattern, search_pattern,
            search_pattern, search_pattern,
            stato_fornitore_id, stato_fornitore_id,
            attivo, attivo,
            limit, offset,
        ]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return extract_paginated(cursor)

    # Scopo: Dettaglio completo di un fornitore con dati soggetto e FK descrizioni.
    def get_fornitore(self, fornitore_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT f.id,
                   f.uid,
                   f.codice,
                   f.attivo,
                   f.soggetto_ruolo_id,
                   f.stato_fornitore_id,
                   -- Soggetto
                   s.id                   AS soggetto_id,
                   s.ragione_sociale_completa,
                   s.codice_fiscale,
                   s.partita_iva,
                   -- Pagamento
                   f.valuta_id,
                   v.iso_code             AS valuta_iso,
                   f.modalita_pagamento_id,
                   mp.descrizione         AS modalita_pagamento_descrizione,
                   f.termine_pagamento_id,
                   tp.descrizione         AS termine_pagamento_descrizione,
                   f.giorni_pagamento,
                   f.fine_mese,
                   -- Fiscale
                   f.split_payment,
                   f.ritenuta_acconto,
                   f.ritenuta_aliquota,
                   f.regime_fiscale,
                   f.bollo_esente,
                   -- FE/SDI
                   f.canale_fe,
                   f.pec_email,
                   -- Rating
                   f.rating,
                   f.qualifica_scadenza,
                   -- Stato
                   sf.codice_interno      AS stato_codice_interno,
                   sf.codice              AS stato_codice,
                   sf.descrizione_breve   AS stato_descrizione,
                   sf.blocca_ordini,
                   -- Note e audit
                   f.note,
                   f.data_insert,
                   f.data_update
              FROM anagrafiche.fornitori f
              JOIN anagrafiche.soggetti_ruoli sr ON sr.id = f.soggetto_ruolo_id
              JOIN anagrafiche.soggetti s        ON s.id  = sr.soggetto_id
              LEFT JOIN config.stati_fornitore sf ON sf.id = f.stato_fornitore_id
              LEFT JOIN config.valute v           ON v.id  = f.valuta_id
              LEFT JOIN config.modalita_pagamento mp ON mp.id = f.modalita_pagamento_id
              LEFT JOIN config.termini_pagamento tp  ON tp.id = f.termine_pagamento_id
             WHERE f.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [fornitore_id])
            return row_to_dict(cursor)

    # Scopo: Risolve la descrizione breve di uno stato fornitore per id
    #        (DEF-1, header filtri leggibili nell'export). Lookup
    #        opportunistico senza cache: 1-2 chiamate per richiesta export.
    def get_stato_fornitore_descrizione(self, stato_id: int) -> str | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT descrizione_breve "
                "  FROM config.stati_fornitore WHERE id = %s",
                [stato_id],
            )
            row = cursor.fetchone()
            return row[0] if row else None

    # =================================================================
    # Aggiornamento
    # =================================================================

    # Campi editabili sul fornitore (pagamento, fiscale, FE, rating, note).
    _UPDATE_ALLOWED = {
        "stato_fornitore_id", "attivo",
        "valuta_id", "modalita_pagamento_id", "termine_pagamento_id",
        "giorni_pagamento", "fine_mese",
        "split_payment", "ritenuta_acconto", "ritenuta_aliquota",
        "regime_fiscale", "bollo_esente",
        "canale_fe", "pec_email",
        "rating", "qualifica_scadenza",
        "note",
    }
    _UPDATE_NULLABLE = {
        "valuta_id", "modalita_pagamento_id", "termine_pagamento_id",
        "giorni_pagamento", "ritenuta_aliquota",
        "regime_fiscale", "canale_fe", "pec_email",
        "rating", "qualifica_scadenza", "note",
    }

    # Scopo: Aggiorna campi editabili di un fornitore (delta update).
    def update_fornitore(self, fornitore_id: int, data: dict[str, Any]) -> bool:
        # Normalizza stringhe vuote a None per campi nullable
        for k in self._UPDATE_NULLABLE:
            if k in data and isinstance(data[k], str) and not data[k].strip():
                data[k] = None
        fields = [(k, v) for k, v in data.items() if k in self._UPDATE_ALLOWED]
        if not fields:
            return False
        set_clause = ", ".join(f"{f[0]} = %s" for f in fields)
        values: list[Any] = [f[1] for f in fields]
        values.append(fornitore_id)
        sql = f"UPDATE anagrafiche.fornitori SET {set_clause} WHERE id = %s"  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, values)
            return cursor.rowcount > 0
