# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso in LETTURA alle edizioni di workflow versionate
#        (pratiche.workflow_definizioni) + drift (vw_definizioni_drift),
#        per la UI admin (Fase 2 Slice 1a). Letture gia' sbloccate a DB
#        (GRANT SELECT). Le azioni write (fork/nuova-versione/pubblica)
#        arrivano in lockstep con la conversione SECURITY DEFINER delle fn
#        DB — vedi brief-db-accesso-be-definizioni-workflow.md §P1.
# ------------------------------------------------------------
from __future__ import annotations

from typing import Any

from django.db import connection


class DefinizioniRepository:
    """Read-only sulle edizioni workflow. Nessuna scrittura qui: le fn azione
    (fork/nuova-versione/pubblica) sono ancora SECURITY INVOKER e verranno esposte
    dal service quando il DB le convertira' in DEFINER (lockstep col gate app)."""

    # Scopo: elenco edizioni per (tipo [, emittente]) con drift. Preset =
    # emittente_fiscale_id NULL; il drift e' valorizzato solo per le edizioni
    # forkate (vista vuota finche' non esistono fork → LEFT JOIN → NULL).
    def list_definizioni(
        self,
        *,
        tipo_prestazione_id: int | None = None,
        emittente_fiscale_id: int | None = None,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT
                wd.id,
                wd.tipo_prestazione_id,
                tp.descrizione                       AS tipo_prestazione_descrizione,
                wd.emittente_fiscale_id,
                ef.descrizione                       AS emittente_display,
                wd.versione,
                wd.stato,
                wd.descrizione,
                wd.preset_origine_id,
                wd.versione_origine,
                drift.versioni_indietro,
                drift.preset_corrente_id,
                drift.versione_preset_corrente
            FROM pratiche.workflow_definizioni wd
            JOIN pratiche.tipi_prestazione tp ON tp.id = wd.tipo_prestazione_id
            LEFT JOIN anagrafiche.emittenti_fiscali ef ON ef.id = wd.emittente_fiscale_id
            LEFT JOIN pratiche.vw_definizioni_drift drift ON drift.definizione_id = wd.id
            WHERE (%(tipo)s IS NULL OR wd.tipo_prestazione_id = %(tipo)s)
              AND (%(emittente)s IS NULL OR wd.emittente_fiscale_id = %(emittente)s)
            ORDER BY wd.tipo_prestazione_id,
                     wd.emittente_fiscale_id NULLS FIRST,
                     wd.versione DESC,
                     wd.id
        """
        with connection.cursor() as cursor:
            cursor.execute(
                sql,
                {"tipo": tipo_prestazione_id, "emittente": emittente_fiscale_id},
            )
            cols = [c[0] for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    # --- Azioni ciclo di vita (Slice 1b) --------------------------------------
    # Wrapper 1:1 sulle fn DB (che restano l'unica sede di logica/validazione).
    # Nota lockstep: finché le fn sono SECURITY INVOKER la DML interna su
    # workflow_definizioni fallisce col ruolo web (permesso negato) → il DB deve
    # convertirle a SECURITY DEFINER (brief-db-accesso-be-definizioni-workflow §P1).

    def _call_scalar(self, sql: str, params: list) -> int:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return int(cursor.fetchone()[0])

    # Scopo: crea l'edizione BOZZA di un emittente da una definizione (di solito il
    # preset), con provenance per il drift. Ritorna l'id della nuova BOZZA.
    def fork_definizione(self, definizione_id: int, emittente_fiscale_id: int) -> int:
        return self._call_scalar(
            "SELECT pratiche.fn_fork_definizione(%s, %s)",
            [definizione_id, emittente_fiscale_id],
        )

    # Scopo: crea una nuova versione BOZZA dello stesso scope di una definizione.
    def nuova_versione_definizione(self, definizione_id: int) -> int:
        return self._call_scalar(
            "SELECT pratiche.fn_nuova_versione_definizione(%s)",
            [definizione_id],
        )

    # Scopo: pubblica una BOZZA (→ PUBBLICATA; la precedente dello scope → RITIRATA).
    def pubblica_definizione(self, definizione_id: int) -> int:
        return self._call_scalar(
            "SELECT pratiche.fn_pubblica_definizione(%s)",
            [definizione_id],
        )
