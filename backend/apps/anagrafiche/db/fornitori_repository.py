# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per gestione fornitori.
#        CRUD fornitori, lista paginata su vw_fornitori_dettaglio.
#        Accesso DB-first via cursor e funzioni PostgreSQL.
# ------------------------------------------------------------

from __future__ import annotations

import json
from typing import Any

from django.db import connection

from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.db.sql_write_helpers import execute_dynamic_update
from apps.core.db._helpers import (
    RicercaFull,
    add_ricerca_full_condition,
    fetch_paged_with_total,
    row_to_dict,
    sql_order_clause,
)


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


# Cosa si PUO' cercare; cosa si cerca lo dice il catalogo (`add_ricerca_full_condition`).
# ⭐ L'id fiscale univoco e non CF e P.IVA separati (Tid, 2026-09-23): come le
#    liste di vendite.
_RICERCA_FORNITORI = RicercaFull(
    "anagrafiche.fornitori", ("codice", "ragione_sociale_completa", "id_fiscale_univoco_cf_piva"),
)


# Campi editabili sul fornitore (pagamento, fiscale, FE, rating, note).
# ⚠️ Whitelist RIGIDA del BB `execute_dynamic_update` (2026-09-26): e' anche la
#    base del contratto PATCH che `FornitoriService` valida (400).
FORNITORE_UPDATE_ALLOWED: frozenset[str] = frozenset({
    "stato_fornitore_id", "attivo",
    "valuta_id", "modalita_pagamento_id", "termine_pagamento_id",
    "giorni_pagamento", "fine_mese",
    "split_payment", "ritenuta_acconto", "ritenuta_aliquota",
    "regime_fiscale", "bollo_esente",
    "canale_fe", "pec_email",
    "rating", "qualifica_scadenza",
    "note",
})


class FornitoriRepository:
    """Accesso DB per fornitori."""

    # =================================================================
    # Creazione
    # =================================================================

    # Scopo: Crea il fornitore con la madre del DB `anagrafiche.fn_crea_fornitore`:
    #        ruolo FO (get_or_create), riga nello stato iniziale VE con i
    #        `campi` (assenti e null al DEFAULT: il codice lo genera
    #        `sistema_codici`), il contatto del ruolo se c'e' e gli indirizzi
    #        del ruolo (auto-clone degli obbligatori). Una chiave estranea la
    #        rifiuta il DB. Ritorna `(fornitore_id, soggetto_ruolo_id)`.
    # ⭐ Dal 2026-10-18 (2b-2, lotto 4): fino ad allora la saga stava nel
    #    service in quattro passi.
    def crea_fornitore(
        self,
        soggetto_id: str,
        campi: dict[str, Any],
        contatto: dict[str, Any] | None,
        indirizzi: list[dict[str, Any]],
    ) -> tuple[int, int]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT fornitore_id, soggetto_ruolo_id
                  FROM anagrafiche.fn_crea_fornitore(%s::uuid, %s::jsonb, %s::jsonb, %s::jsonb)
                """,
                [
                    soggetto_id,
                    json.dumps(campi, default=str),
                    json.dumps(contatto) if contatto is not None else None,
                    json.dumps(indirizzi, default=str),
                ],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0]), int(row[1])

    # =================================================================
    # Lista e dettaglio
    # =================================================================

    # Scopo: Lista paginata fornitori con search e filtri.
    #        Usa la vista vw_fornitori_dettaglio per join pre-calcolati.
    def list_fornitori(
        self, *, search: str | None = None,
        stato_fornitore_id: int | None = None,
        attivo: bool | None = None,
        limit: int = DEFAULT_LIMIT, offset: int = 0,
        order_by: str = "ragione_sociale_completa", order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_FORNITORI_ORDER_COLS,
            default=_FORNITORI_ORDER_COLS["ragione_sociale_completa"],
            tiebreak="v.id",
        )
        conditions: list[str] = [
            "(%s::integer IS NULL OR v.stato_fornitore_id = %s)",
            "(%s::boolean IS NULL OR v.attivo = %s)",
        ]
        params: list[Any] = [stato_fornitore_id, stato_fornitore_id, attivo, attivo]
        add_ricerca_full_condition(conditions, params, search, _RICERCA_FORNITORI, alias="v")
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
             WHERE {" AND ".join(conditions)}
             ORDER BY {ordinamento}
             LIMIT %s OFFSET %s
        """  # noqa: S608
        params.extend([limit, offset])
        return fetch_paged_with_total(sql, params, offset=offset)

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

    _UPDATE_NULLABLE = {
        "valuta_id", "modalita_pagamento_id", "termine_pagamento_id",
        "giorni_pagamento", "ritenuta_aliquota",
        "regime_fiscale", "canale_fe", "pec_email",
        "rating", "qualifica_scadenza", "note",
    }

    # Scopo: Aggiorna campi editabili di un fornitore (delta update).
    #        BB `execute_dynamic_update` (2026-09-26): whitelist RIGIDA
    #        `FORNITORE_UPDATE_ALLOWED`, le chiavi le valida prima il service (400).
    def update_fornitore(self, fornitore_id: int, data: dict[str, Any]) -> bool:
        # Copia: `data` e' `request.data`, non si muta l'input del chiamante.
        valori = dict(data)
        # Normalizza stringhe vuote a None per campi nullable
        for k in self._UPDATE_NULLABLE:
            val = valori.get(k)
            if isinstance(val, str) and not val.strip():
                valori[k] = None
        return execute_dynamic_update(
            "anagrafiche.fornitori", fornitore_id, valori,
            allowed=FORNITORE_UPDATE_ALLOWED,
        )
