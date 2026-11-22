# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per schema `ui` — wrapper `fn_resolve_lista_config`,
#        lettura catalogo colonne (`ui.lista_colonna`) e CRUD preferenza
#        utente (`ui.lista_preferenza_utente`). Tutta la logica di
#        cascata/permessi vive nella fn DB: il repository fa solo
#        marshalling cursore.
# ------------------------------------------------------------

from __future__ import annotations

import json
from typing import Any

from django.db import connection

from apps.core.db._helpers import (
    colonne_ricerca_accese,
    fetchone_scalar,
    jsonb_out,
    rows_to_list,
    utente_di_sessione,
)



class UiRepository:
    """Accesso DB per personalizzazioni liste (schema `ui`).

    Le funzioni di scope/cascata sono interamente lato DB. Il repository
    si occupa solo di passare gli argomenti corretti e materializzare i
    risultati come dict/JSONB.
    """

    # Scopo: Risolve la configurazione effettiva di una lista per l'utente.
    #        Wrapper 1:1 di `ui.fn_resolve_lista_config`. La fn applica:
    #        cascata preferenza/preset, merge nuove colonne, normalizzazione
    #        obbligatorie, filtro autorizzativo. Veste corrente letta dalla
    #        GUC `app.ruolo_applicativo` dentro la fn (post DB-4).
    def resolve_lista_config(
        self,
        lista_codice: str,
        auth_user_id: int,
        emittente_fiscale_id: int | None,
    ) -> dict[str, Any]:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT ui.fn_resolve_lista_config(%s, %s, %s)",
                [lista_codice, auth_user_id, emittente_fiscale_id],
            )
            row = cursor.fetchone()
        if not row or row[0] is None:
            # Caso difensivo: la fn solleva E_UI_LISTA_NON_TROVATA via
            # fn_log_and_raise_error invece di tornare NULL. Se mai arriva
            # NULL, il service lo traduce in E_UI_LISTA_NON_TROVATA.
            return {}
        # ⚠️ Il driver NON decodifica i jsonb fuori dall'ORM: su un cursor RAW
        #    quel valore arriva come `str`. La cinghia di sicurezza e' il BB
        #    `jsonb_out`, non una scritta a mano.
        # ⛔ E non `coerce_jsonb_dict`: il suo ripiego a `{}` farebbe scattare il
        #    `if not config` del service, cioe' direbbe «lista non trovata» su
        #    una lista che c'e'. Qui un JSON illeggibile e' un bug del contratto
        #    e deve esplodere.
        # ⚠️ Il vecchio `dict(row[0])` faceva anche una COPIA: non serviva a
        #    nessuno — la riga nasce da questa query e non e' condivisa — ma il
        #    service scrive dentro il risultato (`richiede_scelta_emittente`),
        #    quindi valeva la pena verificarlo prima di toglierla.
        return jsonb_out(row[0])

    # Scopo: le misure «righe per pagina» ammesse e i due default, per TUTTI i
    #        paginatori dell'applicazione. Wrapper 1:1 di
    #        `ui.fn_get_misure_pagina()`: `{misure, default_compatta,
    #        default_pagina}`. Se un default manca a catalogo la fn solleva
    #        `E_UI_MISURA_PAGINA_DEFAULT_MANCANTE` (TECNICO): mai un NULL.
    def get_misure_pagina(self) -> dict[str, Any]:
        with connection.cursor() as cursor:
            cursor.execute("SELECT ui.fn_get_misure_pagina()")
            row = cursor.fetchone()
        # La fn e' un SELECT senza FROM: una riga c'e' sempre.
        assert row is not None
        return jsonb_out(row[0])

    # Scopo: la lista ha, per l'utente CORRENTE, almeno una colonna in cui la
    #        ricerca libera cerca? Legge la stessa sede del BB di ricerca
    #        (`colonne_ricerca_accese`, cioe' `ui.fn_lista_colonne_ricerca_full`,
    #        gia' filtrata dai permessi di colonna): la casella a video e la
    #        ricerca non possono dire cose diverse.
    def ha_ricerca_full(self, lista_codice: str) -> bool:
        return bool(colonne_ricerca_accese(lista_codice))

    # Scopo: l'utente del contesto di sessione (GUC `app.current_user_id`), cioe'
    #        quello per cui `ha_ricerca_full` e la ricerca vera rispondono. Lo
    #        legge la guardia di `UiService.get_lista_config_per_video`.
    def utente_di_sessione(self) -> int | None:
        return utente_di_sessione(
            codice_errore="E_UI_CHIAMATA_NON_VALIDA",
            function_name="ui_repository.utente_di_sessione",
        )

    # Scopo: la `lista_definizione.id` di una lista accesa, dal suo codice,
    #        letta dal BB del DB `ui.fn_lista_da_codice` (U39 di
    #        brief-db-revisione-ui, Q23): «lista accesa per codice» ha una sede
    #        sola. Lista assente o spenta: `E_UI_LISTA_NON_TROVATA` dal BB, che
    #        si propaga (404) — il service lo darebbe comunque, non c'e' un
    #        «niente» da intercettare.
    # ⚠️ `SELECT … FROM`: `SELECT ui.fn_lista_da_codice(…)` da' la riga intera
    #    come una tupla in un campo solo.
    def get_lista_id(self, lista_codice: str) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM ui.fn_lista_da_codice(%s)",
                [lista_codice],
            )
            return int(fetchone_scalar(cursor))

    # Scopo: Catalogo colonne per la modale di personalizzazione, lookup
    #        diretto per `lista_codice` (single round-trip via JOIN con
    #        lista_definizione). Restituisce lista vuota se la lista non
    #        esiste o non e' attiva: il chiamante che vuole il 404 sulla lista
    #        usa prima `get_lista_id`, che lo solleva dal DB.
    #        Filtra colonne `attivo=TRUE`. Non applica permessi: il
    #        service applica filtro BLOCCATO sulla base del profilo utente
    #        (delegato a fn_resolve_lista_config — qui restiamo grezzi).
    #        ⛔ Non e' la sede delle colonne di RICERCA: `ricercabile_full` letto
    #        da qui cercherebbe anche le colonne BLOCCATE. Quella lettura, gia'
    #        filtrata dai permessi, e' `ui.fn_lista_colonne_ricerca_full`, via il
    #        BB `add_ricerca_full_condition` (apps/core/db/_helpers.py).
    def list_colonne_by_codice(
        self, lista_codice: str,
    ) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT lc.id,
                       lc.codice,
                       lc.etichetta,
                       lc.etichetta_estesa,
                       -- ⚠️ Senza questa colonna il catalogo torna al frontend
                       -- con la sola etichetta ITALIANA del seed, e la modale
                       -- «personalizza colonne» resta in italiano in qualunque
                       -- lingua (difetto misurato il 2026-08-22: 506 colonne su
                       -- 47 liste, tutte con la chiave a catalogo e nessuna
                       -- tradotta). La chiave e' gia' nel seed: mancava solo
                       -- qui.
                       lc.etichetta_i18n_key,
                       lc.campo_sorgente,
                       lc.tipo_colonna::text     AS tipo_colonna,
                       lc.tipo_dato::text        AS tipo_dato,
                       lc.formato,
                       lc.larghezza_default,
                       lc.ordine_default,
                       lc.allineamento::text     AS allineamento,
                       lc.gruppo,
                       lc.gruppo_ordine,
                       lc.filtrabile,
                       lc.ordinabile,
                       lc.esportabile,
                       lc.ricercabile_full,
                       lc.sensibile,
                       lc.attivo
                  FROM ui.lista_colonna     lc
                  JOIN ui.lista_definizione ld ON ld.id = lc.lista_id
                 WHERE ld.codice = %s
                   AND ld.attivo = TRUE
                   AND lc.attivo = TRUE
                 ORDER BY COALESCE(lc.gruppo_ordine, 9999),
                          lc.gruppo NULLS FIRST,
                          lc.ordine_default
                """,
                [lista_codice],
            )
            rows = rows_to_list(cursor)
        return rows

    # Scopo: Preferenza utente per (auth_user, lista). None se non esiste.
    #        Inclusi metadati (`preset_base_id`, lo snapshot per chiave
    #        `preset_base_contenuto_aggiornato_il` come dict `{chiave: data}`
    #        o None, `data_update`).
    def get_preferenza(
        self, auth_user_id: int, lista_id: int
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
                  FROM ui.lista_preferenza_utente
                 WHERE auth_user_id = %s
                   AND lista_id     = %s
                """,
                [auth_user_id, lista_id],
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

    # Scopo: UPSERT preferenza utente. La UNIQUE (auth_user_id, lista_id)
    #        fa del conflict target un UPDATE coerente.
    # ⭐ Lo snapshot (`preset_base_contenuto_aggiornato_il`) non si scrive: lo
    #    scrive `ui.trgfn_preferenza_preset_base_snapshot` (BE6, giro 1a di
    #    brief-db-revisione-ui), `BEFORE INSERT OR UPDATE OF preset_base_id`.
    # ⛔ `preset_base_id` resta nel SET anche quando non cambia: e' la colonna
    #    nominata che fa scattare il trigger, cioe' il riallineamento.
    # ⛔ `data_update` non si scrive: lo scrive `ui.trgfn_preferenza_data_update`
    #    a ogni UPDATE, e un valore passato non conta (BE21, giro 5 di
    #    brief-db-revisione-ui, Q22).
    def upsert_preferenza(
        self,
        auth_user_id: int,
        lista_id: int,
        configurazione: dict[str, Any],
        preset_base_id: int | None,
    ) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO ui.lista_preferenza_utente (
                    auth_user_id,
                    lista_id,
                    preset_base_id,
                    configurazione,
                    data_insert
                )
                VALUES (%s, %s, %s, %s::jsonb, now())
                ON CONFLICT (auth_user_id, lista_id) DO UPDATE
                   SET configurazione           = EXCLUDED.configurazione,
                       preset_base_id           = EXCLUDED.preset_base_id
                RETURNING id
                """,
                [
                    auth_user_id,
                    lista_id,
                    preset_base_id,
                    json.dumps(configurazione),
                ],
            )
            row = cursor.fetchone()
        # RETURNING di INSERT/UPDATE garantisce sempre 1 riga.
        assert row is not None
        return int(row[0])

    # Scopo: «Ignora» del banner preset aggiornato (DEF-2): riallinea lo
    #        snapshot del preset di base al contenuto di oggi, riscrivendo
    #        `preset_base_id` col valore che ha gia'. Ritorna True se ha
    #        aggiornato una riga, False se la preferenza non esiste (il
    #        service lo traduce in E_UI_PREFERENZA_NON_TROVATA 404).
    # ⭐ Lo snapshot lo scrive `ui.trgfn_preferenza_preset_base_snapshot`
    #    (`BEFORE UPDATE OF preset_base_id`): e' nominare la colonna, non
    #    cambiarla, a farlo scattare. Dal giro 1b di brief-db-revisione-ui
    #    l'ignorato (`preset_aggiornato_ignored_at`) non c'e' piu'.
    # ⛔ La base resta quella salvata: con la base cambiata il banner e'
    #    «Riallinea», che salva la base di oggi (`upsert_preferenza`).
    def riallinea_snapshot_base(
        self, auth_user_id: int, lista_id: int
    ) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE ui.lista_preferenza_utente
                   SET preset_base_id = preset_base_id
                 WHERE auth_user_id = %s
                   AND lista_id     = %s
                """,
                [auth_user_id, lista_id],
            )
            return cursor.rowcount > 0

    # Scopo: Elimina preferenza utente per (user, lista). Idempotente:
    #        ritorna True se ha eliminato una riga, False se non esisteva.
    def delete_preferenza(self, auth_user_id: int, lista_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM ui.lista_preferenza_utente
                 WHERE auth_user_id = %s
                   AND lista_id     = %s
                """,
                [auth_user_id, lista_id],
            )
            return cursor.rowcount > 0
