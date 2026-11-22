# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository dashboard configurabili (schema `ui`) — wrapper
#        `fn_resolve_dashboard_config` e CRUD preferenza utente
#        (`ui.dashboard_preferenza_utente`). Gemello di `UiRepository`
#        per le liste: tutta la logica di cascata/merge/permessi vive
#        nella fn DB, qui solo marshalling cursore.
#
#        Divergenza dalle liste (brief DB §3a): il widget e' GLOBALE
#        (`ui.widget`, codice unico) e la membership in una dashboard
#        vive in `ui.dashboard_widget`. Nessuna tabella permessi
#        dedicata (§3b): il filtro e' dentro la fn, sulle due mappe
#        dell'utente `script.fn_get_user_permissions_map` (area non
#        BLOCCATA) e `script.fn_get_user_actions_map` (azione abilitata),
#        lette una volta per chiamata.
# ------------------------------------------------------------

from __future__ import annotations

import json
from typing import Any

from django.db import DatabaseError, connection, transaction

from apps.core.db._helpers import jsonb_out
from apps.core.services.db_error_fields import diagnostica_db


class DashboardRepository:
    """Accesso DB per dashboard configurabili (schema `ui`)."""

    # Scopo: Risolve la configurazione effettiva di una dashboard per
    #        l'utente. Wrapper 1:1 di `ui.fn_resolve_dashboard_config`.
    #        La fn applica: cascata per chiave (preferenza, preset di base
    #        scelto da `ui.fn_preset_di_base`, catalogo del pool), merge
    #        widget nuovi, filtro permessi (area + azione). Veste corrente
    #        letta dentro la fn (`ui.fn_veste_corrente`).
    # Risultato: dict con `widget[]`, `dimensione_max`,
    #        `dimensione_max_standard` (la dimensione senza la preferenza),
    #        `origine` (`{widget, dimensione_max}` -> il livello da cui viene
    #        ogni chiave), `widget_nuovi`, `preset_aggiornato`,
    #        `preset_aggiornato_chiavi` (le chiavi cambiate, elenco),
    #        `preset_base` (`{id, ambito, contenuto_aggiornato_il}` del preset
    #        di base di oggi, la data del contenuto per chiave, o None) e
    #        `preset_base_cambiato`. Ogni widget porta
    #        codice/ordine/visibile + i campi freschi del catalogo
    #        (etichetta, etichetta_i18n_key, tipo_widget, deep_link,
    #        contatore_key, soglia). Il contratto e' la pagina
    #        `docs/it/dbzero/ui/manual/fn_resolve_dashboard_config.md`.
    def resolve_dashboard_config(
        self,
        dashboard_codice: str,
        auth_user_id: int,
        emittente_fiscale_id: int | None,
    ) -> dict[str, Any]:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT ui.fn_resolve_dashboard_config(%s, %s, %s)",
                [dashboard_codice, auth_user_id, emittente_fiscale_id],
            )
            row = cursor.fetchone()
        if not row or row[0] is None:
            # Caso difensivo: la fn solleva E_UI_DASHBOARD_NON_TROVATA via
            # fn_log_and_raise_error invece di tornare NULL.
            return {}
        # ⚠️ Come il gemello di `ui_repository`: la coercizione e' il BB
        #    `jsonb_out`, e non `coerce_jsonb_dict` — un ripiego a `{}` qui
        #    diventerebbe «dashboard non trovata» su una dashboard che c'e'.
        return jsonb_out(row[0])

    # Scopo: Restituisce `dashboard_definizione.id` dato il codice. None se
    #        inesistente o non attiva. Usato dai service di scrittura per
    #        un 404 parlante prima di toccare la preferenza.
    # ⭐ «Dashboard accesa per codice» ha una sede sola, il BB DB
    #    `ui.fn_dashboard_da_codice` (giro 5 di brief-db-revisione-ui, U34,
    #    BE17), lo stesso che legge `fn_resolve_dashboard_config`: qui non si
    #    riscrive il `WHERE codice … AND attivo`. Il BB rifiuta con
    #    `E_UI_DASHBOARD_NON_TROVATA`; chi vuole «niente» intercetta quel
    #    codice (Q23), dentro un savepoint, perche' la transazione del
    #    chiamante resti usabile. Ogni altro errore si propaga.
    def get_dashboard_id(self, dashboard_codice: str) -> int | None:
        try:
            with transaction.atomic(), connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM ui.fn_dashboard_da_codice(%s)",
                    [dashboard_codice],
                )
                row = cursor.fetchone()
        except DatabaseError as exc:
            if diagnostica_db(exc).codice == "E_UI_DASHBOARD_NON_TROVATA":
                return None
            raise
        return int(row[0]) if row and row[0] is not None else None

    # Scopo: Preferenza utente per (auth_user, dashboard). None se assente.
    #        Inclusi i metadati preset per il badge "preset aggiornato".
    def get_preferenza(
        self, auth_user_id: int, dashboard_id: int
    ) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id,
                       configurazione,
                       preset_base_id,
                       preset_base_contenuto_aggiornato_il,
                       data_insert,
                       data_update
                  FROM ui.dashboard_preferenza_utente
                 WHERE auth_user_id = %s
                   AND dashboard_id = %s
                """,
                [auth_user_id, dashboard_id],
            )
            row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            # Lettura per posizione: il jsonb arriva come testo.
            "configurazione": jsonb_out(row[1]),
            "preset_base_id": row[2],
            # Lo snapshot e' per chiave (`{chiave: data}`, giro 1b): jsonb.
            "preset_base_contenuto_aggiornato_il": jsonb_out(row[3]),
            "data_insert": row[4],
            "data_update": row[5],
        }

    # Scopo: UPSERT preferenza utente. Conflict target sulla UNIQUE
    #        (auth_user_id, dashboard_id).
    # ⭐ Lo snapshot lo scrive il trigger del DB, come per le liste
    #    (`UiRepository.upsert_preferenza`): `preset_base_id` resta nel SET
    #    perche' e' la colonna che fa scattare il riallineamento.
    # ⛔ `data_update` non si scrive: lo scrive `ui.trgfn_preferenza_data_update`
    #    (BE21, giro 5 di brief-db-revisione-ui, Q22).
    def upsert_preferenza(
        self,
        auth_user_id: int,
        dashboard_id: int,
        configurazione: dict[str, Any],
        preset_base_id: int | None,
    ) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO ui.dashboard_preferenza_utente (
                    auth_user_id,
                    dashboard_id,
                    preset_base_id,
                    configurazione,
                    data_insert
                )
                VALUES (%s, %s, %s, %s::jsonb, now())
                ON CONFLICT (auth_user_id, dashboard_id) DO UPDATE
                   SET configurazione          = EXCLUDED.configurazione,
                       preset_base_id          = EXCLUDED.preset_base_id
                RETURNING id
                """,
                [
                    auth_user_id,
                    dashboard_id,
                    preset_base_id,
                    json.dumps(configurazione),
                ],
            )
            row = cursor.fetchone()
        # RETURNING di INSERT/UPDATE garantisce sempre 1 riga.
        assert row is not None
        return int(row[0])

    # Scopo: «Ignora» del banner preset aggiornato: riallinea lo snapshot
    #        riscrivendo `preset_base_id` col valore che ha gia', come per
    #        le liste (`UiRepository.riallinea_snapshot_base`). Ritorna False
    #        se la preferenza non esiste (il service traduce in 404).
    def riallinea_snapshot_base(
        self, auth_user_id: int, dashboard_id: int
    ) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE ui.dashboard_preferenza_utente
                   SET preset_base_id = preset_base_id
                 WHERE auth_user_id = %s
                   AND dashboard_id = %s
                """,
                [auth_user_id, dashboard_id],
            )
            return cursor.rowcount > 0

    # Scopo: Elimina preferenza per (user, dashboard). Idempotente.
    def delete_preferenza(self, auth_user_id: int, dashboard_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM ui.dashboard_preferenza_utente
                 WHERE auth_user_id = %s
                   AND dashboard_id = %s
                """,
                [auth_user_id, dashboard_id],
            )
            return cursor.rowcount > 0
