# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Canale di SISTEMA per i processi HEADLESS sotto RLS (cron/management
#        command), modello Path A "per-job" del brief
#        work-in-progress/brief-db-contesto-sistema-batch-fatturazione-rls.md.
#        Espone il gateway `system_process_context(alias, actor)` e l'helper di
#        guardia `connection_role_bypasses_rls` usato dal middleware web (fail-open
#        defense). NIENTE GUC d'identità qui: la RLS è bypassata dal RUOLO DB del
#        canale, non da un sentinel applicativo (Opzione B ritirata).
# ------------------------------------------------------------

from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator

from django.db import DEFAULT_DB_ALIAS, connections

# Scopo: legge il valore corrente di `rolbypassrls` per il ruolo della connessione
#        passata (default: connessione `default`). Una sola query leggera; usata sia
#        dal gateway (sanity fail-loud sul canale batch) sia dal middleware web
#        (sanity fail-closed sul percorso richiesta). Ritorna bool.
def connection_role_bypasses_rls(alias: str = DEFAULT_DB_ALIAS) -> bool:
    with connections[alias].cursor() as cursor:
        cursor.execute(
            "SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user"
        )
        row = cursor.fetchone()
    return bool(row and row[0])


# Scopo: Gateway unico per i processi di sistema headless. Instrada l'INTERA catena
#        DB del processo sul ruolo del canale `alias` con la strategia Path A
#        "redirect del default": il processo (cron, single-thread, separato dal web)
#        ripunta la connessione `default` alle credenziali dell'alias di sistema per
#        la durata del blocco, così tutti i repository/service esistenti — che usano
#        `django.db.connection` e `transaction.atomic()` impliciti — girano come ruolo
#        di sistema SENZA modifiche. A fine blocco ripristina le credenziali web e
#        chiude la connessione (la GUC d'audit, session-scoped, muore con essa).
#
#        Difesa fail-loud: verifica che il ruolo del canale abbia davvero BYPASSRLS;
#        se non ce l'ha (alias mal configurato), SOLLEVA invece di far girare il batch
#        in default-deny silenzioso (il fallimento muto è esattamente ciò che il
#        canale di sistema esiste per evitare).
#
#        Audit: setta `app.jwt_user=actor` così le righe scritte dal processo restano
#        riconoscibili nel giornale (es. 'BATCH_FATTURAZIONE'). NON setta
#        `app.ruolo_applicativo` né altre GUC d'identità: nessuna policy le legge sul
#        canale di sistema.
#
#        ⚠️ USO ESCLUSIVO ai management command / percorsi headless: mai dentro un
#        ciclo di richiesta web (renderebbe la connessione web BYPASSRLS). Difese:
#        check statico di whitelist (test) + guard runtime nel middleware web.
@contextmanager
def system_process_context(*, alias: str, actor: str) -> Iterator[None]:
    sys_settings = connections[alias].settings_dict
    default = connections[DEFAULT_DB_ALIAS]

    # Chiude l'eventuale connessione aperta come ruolo web: la prossima query
    # riaprirà con le credenziali del canale di sistema.
    default.close()
    saved_user = default.settings_dict["USER"]
    saved_password = default.settings_dict["PASSWORD"]
    default.settings_dict["USER"] = sys_settings["USER"]
    default.settings_dict["PASSWORD"] = sys_settings["PASSWORD"]
    try:
        # Sanity fail-loud + marca attore d'audit sulla nuova connessione.
        if not connection_role_bypasses_rls(DEFAULT_DB_ALIAS):
            raise RuntimeError(
                f"system_process_context: il ruolo del canale '{alias}' "
                f"({sys_settings['USER']}) non ha BYPASSRLS — il batch headless "
                "girerebbe in default-deny silenzioso. Verificare il provisioning "
                "del ruolo di sistema."
            )
        # Marca l'attore d'audit sulla connessione di sistema. `app.jwt_user` è la
        # GUC d'audit canonica (stessa di JWT_IDENTITY_GUCS[0] in
        # jwt_audit_authentication): qui è l'UNICA GUC settata — niente identità/scope,
        # la RLS è bypassata dal ruolo, non da un sentinel applicativo.
        with default.cursor() as cursor:
            cursor.execute("SELECT set_config('app.jwt_user', %s, false)", [actor])
        yield
    finally:
        # Ripristino igienico: chiude la connessione di sistema (e la sua GUC) e
        # riallinea le credenziali del default al ruolo web.
        default.close()
        default.settings_dict["USER"] = saved_user
        default.settings_dict["PASSWORD"] = saved_password
