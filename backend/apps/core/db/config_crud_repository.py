# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository CRUD generico per le tabelle del pannello «Gestione
#        tabelle» (`config.tabelle_gestibili` con `pannello`).
#        Lettura: SQL costruito dai metadata. Scrittura: SOLO il verbo
#        `config.fn_pannello_scrivi` (dal 2026-09-25, brief-db-pannello-config-
#        verbo-generico), che chiede il livello TUTTO sull'OGGETTO della
#        tabella e rifiuta i campi che non si scrivono.
# ------------------------------------------------------------

from __future__ import annotations

import json
from typing import Any

from django.db import connection

from apps.core.db._helpers import jsonb_out, row_to_dict
from apps.core.db.config_metadata_repository import ConfigMetadataRepository
from apps.core.db.tabelle_gestibili_repository import TabelleGestibiliRepository

_metadata = ConfigMetadataRepository()


class ConfigCrudRepository:
    """CRUD generico per le tabelle del pannello di configurazione."""

    # Scopo: Dettaglio singolo record con tutti i campi gestibili.
    def get_record(self, schema: str, table: str, record_id: int) -> dict[str, Any] | None:
        cols = _metadata.get_all_column_names(schema, table)
        if not cols:
            return None
        col_list = ", ".join(cols)
        sql = f"SELECT {col_list} FROM {schema}.{table} WHERE id = %s"  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, [record_id])
            # Le colonne della SELECT sono `cols`: il BB le rilegge dal cursore.
            return row_to_dict(cursor)

    # Scopo: Scrive una riga col verbo del pannello: `record_id` None = nuova,
    # altrimenti modifica per id. Ritorna la riga scritta (senza audit).
    # ⛔ Niente filtro dei campi qui: fino al 2026-09-25 un campo che non era
    # una colonna si scartava in silenzio, e un payload tutto sconosciuto
    # diventava un «successo» vuoto. Ora lo rifiuta il DB
    # (`E_PANNELLO_CAMPO_NON_AMMESSO`, col campo; `E_PANNELLO_DATI_VUOTI`), e la
    # riga che non c'e' e' `E_PANNELLO_RIGA_NON_TROVATA`.
    # ⚠️ I valori li converte PostgreSQL sul tipo di ogni colonna
    # (`jsonb_populate_record`): viaggiano come JSON, non come parametri.
    def scrivi_record(
        self, rel: str, record_id: int | None, data: dict[str, Any],
    ) -> dict[str, Any]:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT config.fn_pannello_scrivi(%s, %s, %s::jsonb)",
                [rel, record_id, json.dumps(data)],
            )
            row = cursor.fetchone()
        assert row is not None
        return jsonb_out(row[0])

    # Scopo: Le tabelle del pannello, dalla lista a DB (`pannello`).
    @staticmethod
    def list_available_tables() -> list[dict[str, str]]:
        return [
            {"schema": v["schema"], "table": v["table"], "rel": v["rel"]}
            for v in TabelleGestibiliRepository().voci_pannello()
        ]
