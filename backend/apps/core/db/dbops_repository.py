# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository generico per funzioni dbops cross-schema (lookup, utility,
#        task registry multi-dominio, audit log).
# ------------------------------------------------------------

# Accesso SQL a funzioni dello schema dbops riusabili da tutti i domini applicativi.

import json

from django.db import connection

from apps.core.services.service_errors import ServiceError
from apps.core.types import (
    AuditLogRow,
    DominioTaskRow,
    TaskRegistryImplRow,
    TaskRegistryRow,
)

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


# Cap massimo righe sorgente per la CTE lookup. Il dataset atteso è molto più piccolo
# (tabelle config con poche decine/centinaia di record); il cap è una guardia di sicurezza.
LOOKUP_MAX_SOURCE_ROWS = 10_000


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
            # Il limit interno (LOOKUP_MAX_SOURCE_ROWS) è una guardia; il filtro è applicato sul risultato.
            cursor.execute(
                """
                WITH base AS (
                    SELECT id, codice, descrizione
                      FROM dbops.fn_get_lookup_codici(
                               %s::regclass,
                               %s,
                               %s,
                               %s,
                               %s,
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
                    LOOKUP_MAX_SOURCE_ROWS,
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

    # ------------------------------------------------------------------
    # Task Registry multi-dominio (dbops.domini_task, pipeline_task_registry,
    # pipeline_task_registry_impl)
    # ------------------------------------------------------------------

    # Scopo: Restituisce la lista dei domini task attivi con filtro opzionale.
    # Perimetro: sola lettura su dbops.domini_task.
    def list_domini_task(
        self,
        *,
        attivo_only: bool = True,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[DominioTaskRow], int]:
        search_pattern = f"%{search.strip()}%" if search and search.strip() else None
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, codice, descrizione, attivo,
                       COUNT(*) OVER () AS total_count
                  FROM dbops.domini_task
                 WHERE (%s IS FALSE OR attivo = true)
                   AND (%s::text IS NULL
                        OR codice ILIKE %s
                        OR descrizione ILIKE %s)
                 ORDER BY codice
                 LIMIT %s OFFSET %s
                """,
                [attivo_only, search_pattern, search_pattern, search_pattern,
                 limit, offset],
            )
            rows = cursor.fetchall()

        if not rows:
            return [], 0

        total_count: int = rows[0][4]
        results: list[DominioTaskRow] = [
            DominioTaskRow(
                id=r[0], codice=r[1], descrizione=r[2], attivo=r[3],
            )
            for r in rows
        ]
        return results, total_count

    # Scopo: Restituisce i task registrati per un dominio, con codice dominio in join.
    # Perimetro: sola lettura su pipeline_task_registry + domini_task.
    def list_task_registry(
        self,
        *,
        dominio_codice: str | None = None,
        attivo_only: bool = True,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[TaskRegistryRow], int]:
        search_pattern = f"%{search.strip()}%" if search and search.strip() else None
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT r.id, r.dominio_id, d.codice AS dominio_codice,
                       r.task_code, r.descrizione, r.attivo,
                       COUNT(*) OVER () AS total_count
                  FROM dbops.pipeline_task_registry r
                  JOIN dbops.domini_task d ON d.id = r.dominio_id
                 WHERE (%s IS FALSE OR r.attivo = true)
                   AND (%s::text IS NULL OR d.codice = %s)
                   AND (%s::text IS NULL
                        OR r.task_code ILIKE %s
                        OR r.descrizione ILIKE %s)
                 ORDER BY d.codice, r.task_code
                 LIMIT %s OFFSET %s
                """,
                [attivo_only, dominio_codice, dominio_codice,
                 search_pattern, search_pattern, search_pattern,
                 limit, offset],
            )
            rows = cursor.fetchall()

        if not rows:
            return [], 0

        total_count: int = rows[0][6]
        results: list[TaskRegistryRow] = [
            TaskRegistryRow(
                id=r[0], dominio_id=r[1], dominio_codice=r[2],
                task_code=r[3], descrizione=r[4], attivo=r[5],
            )
            for r in rows
        ]
        return results, total_count

    # Scopo: Restituisce le implementazioni di un task con dettaglio handler.
    # Perimetro: sola lettura su pipeline_task_registry_impl + pipeline_task_registry.
    def list_task_implementations(
        self,
        *,
        task_code: str | None = None,
        dominio_codice: str | None = None,
        attivo_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[TaskRegistryImplRow], int]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT i.id, i.task_registry_id, r.task_code,
                       i.implementation_key, i.handler_code,
                       i.is_default, i.attivo,
                       COUNT(*) OVER () AS total_count
                  FROM dbops.pipeline_task_registry_impl i
                  JOIN dbops.pipeline_task_registry r ON r.id = i.task_registry_id
                  JOIN dbops.domini_task d ON d.id = r.dominio_id
                 WHERE (%s IS FALSE OR i.attivo = true)
                   AND (%s::text IS NULL OR r.task_code = %s)
                   AND (%s::text IS NULL OR d.codice = %s)
                 ORDER BY r.task_code, i.implementation_key
                 LIMIT %s OFFSET %s
                """,
                [attivo_only, task_code, task_code,
                 dominio_codice, dominio_codice,
                 limit, offset],
            )
            rows = cursor.fetchall()

        if not rows:
            return [], 0

        total_count: int = rows[0][7]
        results: list[TaskRegistryImplRow] = [
            TaskRegistryImplRow(
                id=r[0], task_registry_id=r[1], task_code=r[2],
                implementation_key=r[3], handler_code=r[4],
                is_default=r[5], attivo=r[6],
            )
            for r in rows
        ]
        return results, total_count

    # ------------------------------------------------------------------
    # Audit Log (dbops.audit_log)
    # ------------------------------------------------------------------

    # Scopo: Restituisce le righe audit log con filtri opzionali su status, function_name e
    # intervallo temporale. Ordinamento cronologico decrescente.
    # Perimetro: sola lettura; paginazione esterna.
    def list_audit_logs(
        self,
        *,
        status: str | None = None,
        function_name: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLogRow], int]:
        search_pattern = f"%{search.strip()}%" if search and search.strip() else None
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, function_name, executed_by, executed_at::text,
                       status, message, duration_ms, tx_id::text,
                       exec_mode, rule_type, dry_run, rows_affected,
                       params, result,
                       COUNT(*) OVER () AS total_count
                  FROM dbops.audit_log
                 WHERE (%s::text IS NULL OR status = %s)
                   AND (%s::text IS NULL OR function_name ILIKE %s)
                   AND (%s::text IS NULL OR executed_at >= %s::timestamptz)
                   AND (%s::text IS NULL OR executed_at <= %s::timestamptz + interval '1 day')
                   AND (%s::text IS NULL
                        OR function_name ILIKE %s
                        OR message ILIKE %s)
                 ORDER BY executed_at DESC
                 LIMIT %s OFFSET %s
                """,
                [
                    status, status,
                    function_name, f"%{function_name}%" if function_name else None,
                    date_from, date_from,
                    date_to, date_to,
                    search_pattern, search_pattern, search_pattern,
                    limit, offset,
                ],
            )
            rows = cursor.fetchall()

        if not rows:
            return [], 0

        total_count: int = rows[0][14]
        results: list[AuditLogRow] = [
            AuditLogRow(
                id=r[0], function_name=r[1], executed_by=r[2],
                executed_at=r[3], status=r[4], message=r[5],
                duration_ms=r[6], tx_id=r[7], exec_mode=r[8],
                rule_type=r[9], dry_run=r[10], rows_affected=r[11],
                params=r[12] if isinstance(r[12], dict) else (json.loads(r[12]) if r[12] else None),
                result=r[13] if isinstance(r[13], dict) else (json.loads(r[13]) if r[13] else None),
            )
            for r in rows
        ]
        return results, total_count
