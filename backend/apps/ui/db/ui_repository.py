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
    jsonb_out,
    rows_to_list,
    utente_di_sessione,
)


# Espressione SQL pura per leggere la GUC `app.ruolo_applicativo` con
# fallback NULL. Stessa semantica della 2-arg di
# `script.fn_get_profili_accesso_applicabili` post DB-4: GUC vuota ->
# NULL -> "tutte le vesti" (comportamento legacy). Nessun valore utente
# concatenato qui: il letterale e' SQL-safe.
_GUC_VESTE_EXPR = (
    "NULLIF(current_setting('app.ruolo_applicativo', true), '')"
    "::config.ruolo_applicativo"
)

# Tabelle preset ammesse dal BB `fetch_preset_base_snapshot`
# (tabella -> colonna FK dell'entita' personalizzata). Whitelist chiusa:
# i nomi vengono interpolati nell'SQL, mai valori provenienti dall'esterno.
_PRESET_SNAPSHOT_TABLES: dict[str, str] = {
    "ui.lista_preset": "lista_id",
    "ui.dashboard_preset": "dashboard_id",
}


# Scopo: BB condiviso liste/dashboard — snapshot (id, snapshot_ts) del
#        preset di base risolto per l'utente, da memorizzare nella
#        preferenza al momento del salvataggio. Replica la cascata
#        Step 2b/c/d delle fn DB (`ui.fn_resolve_lista_config` /
#        `ui.fn_resolve_dashboard_config`): ruolo (priorita ASC) ->
#        emittente fiscale -> sistema. Ritorna `(None, None)` se nessun
#        preset applicabile (la preferenza partira' dal catalogo grezzo).
#
# `snapshot_ts = contenuto_aggiornato_il`: la data del CONTENUTO del preset,
# `NOT NULL`, scritta solo dai due trigger a mano del DB
# (`ui.trgfn_preset_contenuto_aggiornato` sulle colonne di contenuto,
# `ui.trgfn_preset_riga_tocca_preset` dalle righe figlie). ⛔ Non
# `data_update`: dal blocco 7-bis-c di brief-db-revisione-dbops (2026-11-08)
# e' l'audit, che il trigger generico sposta a OGNI UPDATE (anche il solo
# `attivo`, anche la riscrittura uguale di un seed) e accenderebbe il badge
# `preset_aggiornato` a tutti. Il ripiego su `data_insert` (DEF-2,
# 2026-05-11) non serve piu': la colonna nasce valorizzata.
#
# ATTENZIONE — drift risk: questa cascata duplica la logica DB. Se in
# futuro le fn di risoluzione cambiano (nuovo livello di preset,
# ordinamento, ecc.) va aggiornata anche questa funzione. Soluzione
# strutturale: brief team DB per esporre il preset di base nel JSONB
# delle fn (campo `preset_base`) — eliminerebbe la duplicazione.
def fetch_preset_base_snapshot(
    preset_table: str,
    *,
    entity_id: int,
    auth_user_id: int,
    emittente_fiscale_id: int | None,
) -> tuple[int | None, Any | None]:
    fk_column = _PRESET_SNAPSHOT_TABLES.get(preset_table)
    if fk_column is None:
        raise ValueError(f"tabella preset non in whitelist: {preset_table}")

    # 1. preset di ruolo (priorita ASC)
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT p.id, p.contenuto_aggiornato_il
              FROM {preset_table} p
              JOIN script.fn_get_profili_accesso_applicabili(
                     %s,
                     {_GUC_VESTE_EXPR}
                   ) pa
                ON pa.profilo_accesso_id = p.profilo_accesso_id
             WHERE p.{fk_column} = %s
               AND p.ambito      = 'ruolo'
               AND p.is_default  = TRUE
               AND p.attivo      = TRUE
             ORDER BY pa.priorita ASC
             LIMIT 1
            """,  # noqa: S608 — tabella/FK da whitelist _PRESET_SNAPSHOT_TABLES, GUC letterale, valori come parametri
            [auth_user_id, entity_id],
        )
        row = cursor.fetchone()
    if row:
        return int(row[0]), row[1]

    # 2. preset di emittente fiscale
    if emittente_fiscale_id is not None:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT id, contenuto_aggiornato_il
                  FROM {preset_table}
                 WHERE {fk_column}           = %s
                   AND ambito               = 'emittente_fiscale'
                   AND emittente_fiscale_id = %s
                   AND is_default           = TRUE
                   AND attivo               = TRUE
                 LIMIT 1
                """,  # noqa: S608 — tabella/FK da whitelist _PRESET_SNAPSHOT_TABLES, valori come parametri
                [entity_id, emittente_fiscale_id],
            )
            row = cursor.fetchone()
        if row:
            return int(row[0]), row[1]

    # 3. preset di sistema
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT id, contenuto_aggiornato_il
              FROM {preset_table}
             WHERE {fk_column} = %s
               AND ambito      = 'sistema'
               AND is_default  = TRUE
               AND attivo      = TRUE
             LIMIT 1
            """,  # noqa: S608 — tabella/FK da whitelist _PRESET_SNAPSHOT_TABLES, valori come parametri
            [entity_id],
        )
        row = cursor.fetchone()
    if row:
        return int(row[0]), row[1]

    return None, None


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
        return utente_di_sessione()

    # Scopo: Restituisce la `lista_definizione.id` data il codice. None se
    #        inesistente o non attivo. Usato dai service per distinguere
    #        404 (lista) da preferenze orfane prima di toccare la fn.
    def get_lista_id(self, lista_codice: str) -> int | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM ui.lista_definizione "
                "WHERE codice = %s AND attivo = TRUE",
                [lista_codice],
            )
            row = cursor.fetchone()
        return int(row[0]) if row else None

    # Scopo: Catalogo colonne per la modale di personalizzazione, lookup
    #        diretto per `lista_codice` (single round-trip via JOIN con
    #        lista_definizione). Restituisce lista vuota se la lista non
    #        esiste o non e' attiva: il chiamante che vuole distinguere
    #        404 vs lista vuota usa `get_lista_id` separatamente.
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
    #        Inclusi metadati (`preset_base_id`, `preset_base_contenuto_aggiornato_il`,
    #        `data_update`) per permettere al FE/service il check del
    #        badge "preset aggiornato" (DEF-2).
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
            "preset_base_contenuto_aggiornato_il": row[3],
            "data_insert": row[4],
            "data_update": row[5],
        }

    # Scopo: UPSERT preferenza utente. Snapshot di
    #        `lista_preset.contenuto_aggiornato_il` catturato dal service e passato qui come parametro
    #        `preset_base_contenuto_aggiornato_il`. La PK e' (auth_user_id, lista_id)
    #        (UNIQUE), quindi il conflict target esegue UPDATE coerente.
    def upsert_preferenza(
        self,
        auth_user_id: int,
        lista_id: int,
        configurazione: dict[str, Any],
        preset_base_id: int | None,
        preset_base_contenuto_aggiornato_il: Any | None,
    ) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO ui.lista_preferenza_utente (
                    auth_user_id,
                    lista_id,
                    preset_base_id,
                    preset_base_contenuto_aggiornato_il,
                    configurazione,
                    data_insert
                )
                VALUES (%s, %s, %s, %s, %s::jsonb, now())
                ON CONFLICT (auth_user_id, lista_id) DO UPDATE
                   SET configurazione           = EXCLUDED.configurazione,
                       preset_base_id           = EXCLUDED.preset_base_id,
                       preset_base_contenuto_aggiornato_il  = EXCLUDED.preset_base_contenuto_aggiornato_il,
                       data_update              = now()
                RETURNING id
                """,
                [
                    auth_user_id,
                    lista_id,
                    preset_base_id,
                    preset_base_contenuto_aggiornato_il,
                    json.dumps(configurazione),
                ],
            )
            row = cursor.fetchone()
        # RETURNING di INSERT/UPDATE garantisce sempre 1 riga.
        assert row is not None
        return int(row[0])

    # Scopo: Setta `preset_aggiornato_ignored_at = NOW()` sulla preferenza
    #        utente (DEF-2 "Ignora" banner preset aggiornato). Ritorna True
    #        se ha aggiornato una riga, False se la preferenza non esiste
    #        (il chiamante service trasforma False in
    #        E_UI_PREFERENZA_NON_TROVATA 404).
    def set_preset_aggiornato_ignored(
        self, auth_user_id: int, lista_id: int
    ) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE ui.lista_preferenza_utente
                   SET preset_aggiornato_ignored_at = now(),
                       data_update                  = now()
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

    # Scopo: Snapshot preset di base per la preferenza liste. Delega al BB
    #        condiviso `fetch_preset_base_snapshot` (cascata, COALESCE e
    #        drift risk documentati li').
    def get_preset_base_snapshot(
        self,
        lista_id: int,
        auth_user_id: int,
        emittente_fiscale_id: int | None,
    ) -> tuple[int | None, Any | None]:
        return fetch_preset_base_snapshot(
            "ui.lista_preset",
            entity_id=lista_id,
            auth_user_id=auth_user_id,
            emittente_fiscale_id=emittente_fiscale_id,
        )
