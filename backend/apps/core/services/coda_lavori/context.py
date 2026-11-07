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
from apps.core.api.jwt_audit_authentication import (
    JWT_GUC_RESET_SQL,
    JWT_IDENTITY_GUCS,
    set_jwt_gucs,
)
from apps.core.services.error_manager import ErrorManager

E_SCOPE_OPERATORE = "E_CODA_SCOPE_OPERATORE_INVALIDO"
E_IDENTITA_NON_ATTIVA = "E_CODA_IDENTITA_NON_ATTIVA"

# Lettura e riscrittura dei GUC identita', derivate dalla tupla canonica come
# `JWT_GUC_RESET_SQL`: nessuna lista ricopiata. I nomi sono costanti fidate.
_IDENTITA_LEGGI_SQL: str = "SELECT " + ", ".join(
    f"current_setting('{_guc}', true)" for _guc in JWT_IDENTITY_GUCS
)
_IDENTITA_RIPRISTINA_SQL: str = "SELECT " + ", ".join(
    f"set_config('{_guc}', %s, false)" for _guc in JWT_IDENTITY_GUCS
)


# Scopo: L'identita' che la connessione porta ADESSO (i GUC canonici, '' se
#        assenti). Serve a chi apre un contesto dentro un altro: all'uscita deve
#        rimettere QUESTA, non azzerare.
def _identita_corrente() -> tuple[str, ...]:
    with connection.cursor() as cursor:
        cursor.execute(_IDENTITA_LEGGI_SQL)
        row = cursor.fetchone()
    return tuple(v or "" for v in (row or ("",) * len(JWT_IDENTITY_GUCS)))


# Scopo: Rimette l'identita' letta all'ingresso. Senza identita' prima, e' il
#        reset canonico del middleware (`JWT_GUC_RESET_SQL`).
# ⚠️ Non si rivalida: l'identita' esterna l'ha gia' validata chi l'ha aperta,
#    e il contesto interno ne e' solo una parentesi.
def _ripristina_identita(valori: tuple[str, ...]) -> None:
    with connection.cursor() as cursor:
        if any(valori):
            cursor.execute(_IDENTITA_RIPRISTINA_SQL, list(valori))
        else:
            cursor.execute(JWT_GUC_RESET_SQL)


# Scopo: Esegue il blocco con l'identità completa dell'operatore impostata
#        (5 GUC, RLS attiva che risolve all'operatore). All'uscita, sempre —
#        anche su eccezione — RIMETTE l'identità che c'era prima: nessuna (il
#        reset canonico del middleware) o quella del contesto esterno.
# ⛔ Rimettere, non azzerare (BE10, brief-db-revisione-dbops §5). Il drenatore
#    della coda lavori gira con l'utente tecnico dell'azienda e, dentro, esegue
#    ogni lavoro con l'identità di chi l'ha accodato. Azzerando, la `mark_done`
#    successiva girava senza identità: sotto la RLS aggiorna zero righe, senza
#    errore, e il lavoro resta IN_CORSO fino al reaper.
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
    precedente = _identita_corrente()
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
        # Anche su identità non attiva: i GUC parziali spariscono e torna
        # quella di prima.
        _ripristina_identita(precedente)


# Scopo: Esegue il blocco SENZA identità, e all'uscita rimette quella di prima.
#        È il contesto di un lavoro `SISTEMA` dentro il giro di un utente
#        tecnico: senza, il lavoro girerebbe col perimetro di quell'azienda,
#        che non è il suo.
@contextmanager
def senza_identita_context() -> Iterator[None]:
    precedente = _identita_corrente()
    with connection.cursor() as cursor:
        cursor.execute(JWT_GUC_RESET_SQL)
    try:
        yield
    finally:
        _ripristina_identita(precedente)
