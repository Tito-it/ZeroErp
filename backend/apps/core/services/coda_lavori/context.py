# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Contesto di esecuzione OPERATORE per i job della coda generica. A
#        Si resta sul ruolo applicativo NON-BYPASSRLS del worker e si
#        ripropone l'IDENTITÀ COMPLETA dell'operatore che ha
#        accodato il job — gli stessi 5 GUC del ciclo web (`set_jwt_gucs`:
#        `app.jwt_user` username, `app.current_user_id`, `app.current_identita_id`,
#        `app.ruolo_applicativo`, `app.soggetto_ruolo_id`). Effetto: le policy
#        RLS operatore (che richiedono `app.ruolo_applicativo='OPERATORE'` +
#        `app.current_user_id`) risolvono ESATTAMENTE come nel web, e l'audit
#        attribuisce le scritture all'operatore (username, come nel web).
#
#        ⚠️ Settare solo `app.jwt_user` NON basta: le policy RLS non
#        risolverebbero (GUC identità vuote ⇒ 0 righe fail-closed) e l'audit
#        registrerebbe un id al posto dello username.
#
#        La CTE di `set_jwt_gucs` valida che la coppia (auth_user, identità)
#        sia ANCORA attiva al momento dell'esecuzione: un'identità revocata
#        tra enqueue ed esecuzione → fail-loud (il job va in retry/ERRORE,
#        niente esecuzione con GUC vuote e RLS a 0 righe silenziosa). Coerente
#        col design §3a: la revoca vale per i job non ancora partiti, non
#        interrompe l'IN_CORSO.
#
#        NB: non ridirige credenziali né ruolo — imposta solo GUC di sessione.
#        ⭐ Dal 2026-09-05 è l'UNICO contesto di esecuzione dei job: il canale
#        `BYPASSRLS` che gli stava accanto è stato ritirato (R-2).
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from django.db import connection

# Import dal layer api: `set_jwt_gucs`/`JWT_GUC_RESET_SQL` sono la fonte
# canonica dei 5 GUC identità (stessa CTE del web — riuso, non copia).
# Precedente di direzione services→api: tracciamento_service.
from apps.core.api.jwt_audit_authentication import JWT_GUC_RESET_SQL, set_jwt_gucs
from apps.core.services.error_manager import ErrorManager

E_SCOPE_OPERATORE = "E_CODA_SCOPE_OPERATORE_INVALIDO"
E_IDENTITA_NON_ATTIVA = "E_CODA_IDENTITA_NON_ATTIVA"


# Scopo: Esegue il blocco con l'identità completa dell'operatore impostata
#        (5 GUC, RLS attiva che risolve all'operatore). Ripristina (azzera)
#        TUTTI i GUC all'uscita, sempre — anche su eccezione — per non lasciare
#        l'identità "appiccicata" alla connessione riusata dal worker per il
#        job successivo (stesso reset canonico del middleware web).
@contextmanager
def operator_identity_context(
    auth_user_id: int | None,
    *,
    username: str | None,
    identita_id: int | None,
    emittente_attivo_id: int | None = None,
) -> Iterator[None]:
    # Guard fail-loud: un job OPERATORE senza identità completa nello scope è
    # un bug di accodamento (il CHECK DB garantisce scope non-null, ma non il
    # contenuto — l'enqueue della view cattura sempre la terna completa).
    ErrorManager.require(
        auth_user_id is not None and bool(username) and identita_id is not None,
        code=E_SCOPE_OPERATORE,
        message="Job OPERATORE senza identità completa nello scope catturato.",
        detail=(
            f"auth_user_id={auth_user_id!r} username={username!r} "
            f"identita_id={identita_id!r}"
        ),
    )
    assert auth_user_id is not None and username and identita_id is not None
    # Stessa CTE del web: valida (auth_user, identità) attiva + setta i 5 GUC
    # in un round-trip. False = identità revocata/inattiva o errore DB.
    identita_attiva = set_jwt_gucs(
        username=username, user_id=auth_user_id, identita_id=identita_id,
        # Emittente CONGELATO all'enqueue: il job lavora dentro l'emittente in
        # cui si trovava chi l'ha chiesto, non dentro quello in cui l'utente si
        # trova adesso (potrebbe averlo cambiato, o essersi sconnesso). Senza,
        # il worker girerebbe in modalita' globale e un giro chiesto «dentro A»
        # toccherebbe anche B — silenziosamente, perche' nulla lo direbbe.
        # `None` = job accodato in modalita' globale, o prima del cantiere:
        # comportamento storico invariato.
        emittente_attivo_id=emittente_attivo_id,
    )
    try:
        # Fail-loud DENTRO il try: anche su identità non attiva i GUC parziali
        # (jwt_user/current_user_id) vengono azzerati dal finally.
        ErrorManager.require(
            identita_attiva,
            code=E_IDENTITA_NON_ATTIVA,
            message="Identità operatore non più attiva: job non eseguibile.",
            detail=f"auth_user_id={auth_user_id} identita_id={identita_id}",
        )
        yield
    finally:
        # Azzera TUTTI i GUC identità (session-scoped) — reset canonico
        # condiviso col middleware web (JWT_GUC_RESET_SQL).
        with connection.cursor() as cursor:
            cursor.execute(JWT_GUC_RESET_SQL)
