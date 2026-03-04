# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB per generazione cross-pratica.
#        Regole generazione, invocazione fn_genera_pratica_da_flusso,
#        lookup pratiche generate da un flusso.
# ------------------------------------------------------------

from typing import Any

from django.db import connection

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
            rows = cursor.fetchall()

        return [
            {
                "id": int(r[0]),
                "template_flusso_origine_id": int(r[1]),
                "tipo_prestazione_dest_id": int(r[2]),
                "template_flusso_dest_id": None if r[3] is None else int(r[3]),
                "esito_richiesto": r[4],
                "auto": bool(r[5]),
                "attivo": bool(r[6]),
                "descrizione": r[7],
                "meta": r[8] if isinstance(r[8], dict) else {},
            }
            for r in rows
        ]

    # Scopo: Restituisce le pratiche generate da un flusso (via flusso_origine_id).
    def get_pratiche_generate_da_flusso(self, flusso_id: int) -> list[PraticaRow]:
        sql = """
            SELECT
                p.id, p.emittente_fiscale_id, p.tipo_prestazione_id,
                p.soggetto_id, p.stato_id, p.priorita_id,
                p.risorsa_umana_id, p.unita_organizzativa_id,
                p.pratica_padre_id, p.flusso_origine_id,
                p.canale_origine_id, p.solo_interna,
                p.codice, p.descrizione, p.data_scadenza,
                p.meta, p.data_insert, p.user_insert
            FROM pratiche.pratiche p
            WHERE p.flusso_origine_id = %s
            ORDER BY p.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [flusso_id])
            rows = cursor.fetchall()

        # Riusa il mapper di PraticheRepository per coerenza.
        from apps.pratiche.db.pratiche_repository import PraticheRepository
        return [PraticheRepository._map_pratica_row(r) for r in rows]

    # Scopo: Invoca fn_genera_pratica_da_flusso per generazione manuale.
    # Obiettivo: generazione esplicita per regole con auto=false.
    # Risultato: ID della pratica generata.
    def genera_pratica_manuale(self, flusso_id: int, regola_id: int) -> int:
        ErrorManager.require(
            flusso_id > 0,
            code="E_INVALID_ID",
            message="flusso_id deve essere > 0",
        )
        assert flusso_id > 0
        ErrorManager.require(
            regola_id > 0,
            code="E_INVALID_ID",
            message="regola_id deve essere > 0",
        )
        assert regola_id > 0

        sql = """
            SELECT pratiche.fn_genera_pratica_da_flusso(%s, %s)
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [flusso_id, regola_id])
            row = cursor.fetchone()
            assert row is not None
        return int(row[0])
