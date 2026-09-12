# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per accesso DB funzioni schema anagrafiche.
# Note: Segue pattern DB-first — delega logica a funzioni PostgreSQL.
# ------------------------------------------------------------

from __future__ import annotations

from django.db import connection, transaction

from apps.core.db._helpers import fetchone_scalar


class AnagraficheRepository:
    """Accesso DB per lo schema anagrafiche."""

    # Scopo: Esegue `anagrafiche.fn_sync_auth_user_expired()` — la disattivazione
    #        batch degli utenti con finestra temporale scaduta — e dice CHI ha
    #        toccato. Ritorna `(n_disattivati, auth_user_id modificati)`.
    #
    # ⭐ GLI ID SI RICAVANO DALL'EFFETTO, NON DA UNA COPIA DELLA REGOLA: si
    #    fotografano gli `auth_user` attivi prima e dopo la funzione, dentro la
    #    STESSA transazione, e la differenza e' chi ha cambiato stato. La regola
    #    «chi e' scaduto» vive in una sede sola, la funzione DB.
    # ⛔ Fino al 2026-09-12 qui c'era `list_expired_auth_user_ids`: la stessa
    #    `WHERE` della funzione ricopiata in Python — e ricopiata a META', perche'
    #    conosceva solo il ramo legacy (`risorse_umane` via la vista
    #    `risorse_umane_auth_user`) e ignorava `identita_digitali`: la cache dei
    #    permessi non veniva invalidata per le identita' portale/shop che la
    #    funzione invece disattivava. E leggeva la vista col nome vecchio, che
    #    il DB ritira (analisi-software-per-dati-morti §2.1, passo 1).
    # ⚠️ E gli id sono quelli DAVVERO modificati, non i candidati: la funzione
    #    puo' lasciare un candidato com'e' (`fn_sync_auth_user_is_active`
    #    decide), e prima la cache veniva invalidata su un elenco piu' largo
    #    del conteggio che si stampava accanto.
    # ⚠️ La differenza e' SIMMETRICA: la funzione oggi spegne soltanto, ma se
    #    un giorno riaccendesse, anche quell'utente ha una cache da buttare.
    # `dry_run`: la stessa corsa, dentro una transazione ritirata — l'elenco
    #    e' quello vero perche' lo produce la funzione vera, e non resta niente.
    # ⚠️ Il `set_rollback` e' l'ULTIMA istruzione del blocco: dentro un atomic
    #    marcato per rollback Django vieta altre query.
    def sync_auth_user_expired(self, *, dry_run: bool = False) -> tuple[int, list[int]]:
        with transaction.atomic():
            with connection.cursor() as cursor:
                prima = self._auth_user_attivi(cursor)
                cursor.execute("SELECT anagrafiche.fn_sync_auth_user_expired()")
                disattivati = int(fetchone_scalar(cursor))
                dopo = self._auth_user_attivi(cursor)
            if dry_run:
                transaction.set_rollback(True)
        return disattivati, sorted(prima ^ dopo)

    # Scopo: gli `auth_user` attivi in questo istante — un'osservazione, non
    #        una regola: nessun `WHERE` di dominio.
    @staticmethod
    def _auth_user_attivi(cursor) -> set[int]:
        cursor.execute("SELECT id FROM django.auth_user WHERE is_active = true")
        return {int(row[0]) for row in cursor.fetchall()}
