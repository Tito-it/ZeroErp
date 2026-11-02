# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La sola domanda rimasta sul bypass della RLS: «questa connessione lo
#        ha?». Serve al middleware web come cancello fail-closed
#        (`E_DB_ROLE_UNSAFE`): una richiesta HTTP non deve MAI girare su un ruolo
#        che scavalca le policy.
# Note: ⛔ IL GATEWAY `system_process_context` NON ESISTE PIU' (2026-09-05, R-2).
#        Apriva una connessione sul ruolo `zeroerp_batch_fatturazione`
#        (`BYPASSRLS`) perche' i processi notturni non avevano un'identita'
#        propria e dovevano vedere tutte le aziende. Adesso ce l'hanno: un utente
#        tecnico per (processo x azienda), e ogni lavoro gira dentro il proprio
#        perimetro. Un canale che scavalca i muri non ha piu' nessun uso
#        legittimo — e finche' esisteva, bastava importarlo per riaprirlo.
#        ⭐ La funzione qui sotto resta, e ha il verso OPPOSTO: non concede il
#        bypass, verifica che non ci sia.
# ------------------------------------------------------------

from __future__ import annotations

from django.db import DEFAULT_DB_ALIAS, connections

# Scopo: legge il valore corrente di `rolbypassrls` per il ruolo della connessione
#        passata (default: connessione `default`). Una sola query leggera.
#        ⭐ Consumatore unico dal 2026-09-05: il middleware web, come cancello
#        fail-closed sul percorso richiesta. Il secondo consumatore era il
#        gateway del canale batch, che non esiste piu'.
def connection_role_bypasses_rls(alias: str = DEFAULT_DB_ALIAS) -> bool:
    with connections[alias].cursor() as cursor:
        cursor.execute(
            "SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user"
        )
        row = cursor.fetchone()
    return bool(row and row[0])
