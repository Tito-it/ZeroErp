# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB per generazione cross-pratica.
#        Regole generazione, invocazione fn_genera_pratica_da_flusso,
#        lookup pratiche generate da un flusso.
# ------------------------------------------------------------

from typing import cast

from django.db import connection

from apps.core.db._helpers import rows_to_list
from apps.core.services.error_manager import ErrorManager
from apps.pratiche.types import PraticaRow, RegolaGenerazioneRow


class GenerazioneRepository:

    # Scopo: Restituisce le regole di generazione configurate per un template flusso.
    def list_regole_generazione(
        self, template_flusso_id: int,
    ) -> list[RegolaGenerazioneRow]:
        sql = """
            SELECT
                rg.id, rg.template_flusso_origine_id,
                rg.tipo_prestazione_dest_id, rg.template_flusso_dest_id,
                rg.esito_richiesto, rg.auto, rg.attivo,
                rg.descrizione, rg.meta
            FROM pratiche.regole_generazione rg
            WHERE rg.template_flusso_origine_id = %s
              AND rg.attivo = true
            ORDER BY rg.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [template_flusso_id])
            return cast("list[RegolaGenerazioneRow]", rows_to_list(cursor))

    # Scopo: Restituisce le pratiche generate da un flusso (via flusso_origine_id).
    def get_pratiche_generate_da_flusso(self, flusso_id: int) -> list[PraticaRow]:
        from apps.pratiche.db.pratiche_repository import PraticheRepository
        sql = f"""
            SELECT {PraticheRepository.pratica_select_sql()}
            FROM pratiche.pratiche p
            {PraticheRepository.pratica_joins_sql()}
            WHERE p.flusso_origine_id = %s
            ORDER BY p.id
        """  # noqa: S608 — proiezione/join dalle costanti di PraticheRepository, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [flusso_id])
            return cast("list[PraticaRow]", rows_to_list(cursor))

    # Scopo: Invoca fn_genera_pratica_da_flusso per generazione manuale.
    # Obiettivo: generazione esplicita per regole con auto=false.
    # Risultato: ID della pratica generata.
    def genera_pratica_manuale(self, flusso_id: int, regola_id: int) -> int:
        ErrorManager.require(
            flusso_id > 0,
            code="E_INVALID_ID",
            message="flusso_id deve essere > 0",
        )
        ErrorManager.require(
            regola_id > 0,
            code="E_INVALID_ID",
            message="regola_id deve essere > 0",
        )

        sql = """
            SELECT pratiche.fn_genera_pratica_da_flusso(%s, %s)
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [flusso_id, regola_id])
            row = cursor.fetchone()
            ErrorManager.require(
                row is not None,
                code="E_GENERAZIONE_PRATICA",
                message="Errore generazione pratica da flusso",
            )
            assert row is not None
        return int(row[0])
