# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository generico per funzioni dbops cross-schema (lookup, utility).
# ------------------------------------------------------------

# Accesso SQL a funzioni dello schema dbops riusabili da tutti i domini applicativi.

from django.db import connection

from apps.core.services.service_errors import ServiceError

# Whitelist relazioni consentite per la lookup generica.
# Include tutte le tabelle config con struttura id/codice/descrizione.
# La funzione DB fn_get_lookup_codici valida ulteriormente la struttura delle colonne.
_REL_CONSENTITE: frozenset[str] = frozenset(
    {
        "config.ambiti",
        "config.aspetti_beni",
        "config.assets_ownership",
        "config.categoria_accisa",
        "config.causali_trasporto",
        "config.classi_utenze",
        "config.conti_contabili",
        "config.forme_giuridiche",
        "config.iva",
        "config.iva_assoggettamenti",
        "config.iva_natura",
        "config.lingue",
        "config.modalita_addebito_trasporto",
        "config.modalita_pagamento",
        "config.note_stili",
        "config.qualifiche",
        "config.sistema_codici",
        "config.sorgenti",
        "config.stati",
        "config.stati_assets",
        "config.stati_cliente",
        "config.stati_doc_contratti",
        "config.stati_doc_ddt",
        "config.stati_doc_fiscale",
        "config.stati_doc_ordini",
        "config.stati_doc_preventivi",
        "config.stati_pdp",
        "config.stati_flussi_pratiche",
        "config.stati_pratiche",
        "config.stati_sdi",
        "config.termini_pagamento",
        "config.tipi_attivita",
        "config.tipi_contatti",
        "config.tipi_doc_fiscale",
        "config.tipi_documenti",
        "config.tipi_evento_assets",
        "config.tipi_indirizzi",
        "config.tipi_ruoli",
        "config.tipi_soggetto_dettaglio",
        "config.tipi_ubicazione",
        "config.tipi_utenze",
        "config.canali_pratiche",
        "config.priorita_pratiche",
        "config.unita_organizzative",
        "config.utilities",
        "config.valute",
    }
)


class DbopsRepository:
    """Repository per funzioni generiche dbops (lookup codici, utility)."""

    # Scopo: Restituisce la lista dei valori lookup per una relazione config con filtro ILIKE
    # e paginazione. Chiama dbops.fn_get_lookup_codici con limit ampio per ottenere tutti i
    # record attivi e applica il filtro testo e la paginazione esternamente via SQL wrapper.
    # Obiettivo: evitare di modificare la funzione DB generica mantenendo la logica di ricerca
    # lato Python/SQL.
    # Perimetro: sola lettura; solleva ServiceError se la relazione non è in whitelist.
    # Risultato: tuple (list[dict], total_count) con campi id, codice, descrizione.
    def list_lookup_codici(
        self,
        *,
        rel: str,
        search: str | None = None,
        order_col: str = "descrizione",
        order_dir: str = "ASC",
        attivo_only: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        if rel not in _REL_CONSENTITE:
            raise ServiceError(
                code="E_CORE_VALIDATION",
                message="Relazione non consentita.",
                detail=f"rel '{rel}' non è nella whitelist delle lookup consentite.",
            )

        # Normalizzazione: search None o stringa vuota => nessun filtro.
        search_pattern = f"%{search.strip()}%" if search and search.strip() else None

        with connection.cursor() as cursor:
            # Wrappa fn_get_lookup_codici in una CTE con filtro ILIKE e paginazione esterna.
            # Il limit interno è alto (10000) perché il filtro viene applicato sul risultato.
            cursor.execute(
                """
                WITH base AS (
                    SELECT id, codice, descrizione
                      FROM dbops.fn_get_lookup_codici(
                               %s::regclass,
                               %s,
                               %s,
                               %s,
                               10000,
                               0
                           )
                )
                SELECT
                    id,
                    codice,
                    descrizione,
                    COUNT(*) OVER () AS total_count
                  FROM base
                 WHERE (
                     %s::text IS NULL
                     OR codice ILIKE %s
                     OR descrizione ILIKE %s
                 )
                 LIMIT %s OFFSET %s
                """,
                [
                    rel,
                    order_col,
                    order_dir,
                    attivo_only,
                    search_pattern,
                    search_pattern,
                    search_pattern,
                    limit,
                    offset,
                ],
            )
            rows = cursor.fetchall()

        if not rows:
            return [], 0

        total_count = rows[0][3]
        results = [
            {
                "id": row[0],
                "codice": row[1],
                "descrizione": row[2],
            }
            for row in rows
        ]
        return results, total_count

    # Scopo: Verifica esistenza di un record attivo in una tabella config whitelisted per ID.
    def check_lookup_id_exists(self, *, rel: str, record_id: int) -> bool:
        if rel not in _REL_CONSENTITE:
            raise ServiceError(
                code="E_CORE_VALIDATION",
                message="Relazione non consentita.",
                detail=f"rel '{rel}' non e` nella whitelist delle lookup consentite.",
            )
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT EXISTS(SELECT 1 FROM {rel} WHERE id = %s AND attivo = true)",
                [record_id],
            )
            row = cursor.fetchone()
            return bool(row and row[0])
