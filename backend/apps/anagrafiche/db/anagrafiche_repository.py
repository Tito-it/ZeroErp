# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per accesso DB funzioni schema anagrafiche.
# Note: Segue pattern DB-first — delega logica a funzioni PostgreSQL.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import connection, transaction

from apps.core.db._helpers import fetchone_scalar, rows_to_list, pattern_contiene


class AnagraficheRepository:
    """Accesso DB per lo schema anagrafiche."""

    # Scopo: Esegue `anagrafiche.fn_sync_auth_user_expired()` — il
    #        riallineamento batch di `auth_user.is_active` a «esiste una veste
    #        utilizzabile oggi», nei due versi (spegne chi non ne ha piu' una,
    #        accende chi ne ha una diventata valida) — e dice CHI ha toccato.
    #        Ritorna `(n_riallineati, auth_user_id modificati)`. Il nome resta
    #        quello della funzione DB (brief-db-veste-utilizzabile §8.2).
    #
    # ⭐ GLI ID SI RICAVANO DALL'EFFETTO, NON DA UNA COPIA DELLA REGOLA: si
    #    fotografano gli `auth_user` attivi prima e dopo la funzione, dentro la
    #    STESSA transazione, e la differenza e' chi ha cambiato stato. La regola
    #    «chi vale oggi» vive in una sede sola, a DB
    #    (`script.fn_veste_utilizzabile`, letta dalla funzione).
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
    # ⚠️ La differenza e' SIMMETRICA: dal 2026-10-07 la funzione spegne E
    #    accende, e anche chi si accende ha una cache da buttare.
    # `dry_run`: la stessa corsa, dentro una transazione ritirata — l'elenco
    #    e' quello vero perche' lo produce la funzione vera, e non resta niente.
    # ⚠️ Il `set_rollback` e' l'ULTIMA istruzione del blocco: dentro un atomic
    #    marcato per rollback Django vieta altre query.
    def sync_auth_user_expired(self, *, dry_run: bool = False) -> tuple[int, list[int]]:
        with transaction.atomic():
            with connection.cursor() as cursor:
                prima = self._auth_user_attivi(cursor)
                cursor.execute("SELECT anagrafiche.fn_sync_auth_user_expired()")
                riallineati = int(fetchone_scalar(cursor))
                dopo = self._auth_user_attivi(cursor)
            if dry_run:
                transaction.set_rollback(True)
        return riallineati, sorted(prima ^ dopo)

    # Scopo: gli `auth_user` attivi in questo istante — un'osservazione, non
    #        una regola: nessun `WHERE` di dominio.
    @staticmethod
    def _auth_user_attivi(cursor) -> set[int]:
        cursor.execute("SELECT id FROM django.auth_user WHERE is_active = true")
        return {int(row[0]) for row in cursor.fetchall()}

    # Scopo: Le RISORSE UMANE per un lookup di selezione («chi governa questa
    #        cosa»): id + nome della persona, con qualifica e reparto per
    #        distinguere due omonimi. Non c'e' `codice`/`descrizione` sulla
    #        tabella, ed e' il motivo per cui il lookup generico non serve.
    # ⭐ Nasce per il responsabile della commessa (brief-db-modifiche-certe-
    #        ciclo-vendita-e-articolo, §5.5 voce 4, D-A): l'unico lookup in
    #        servizio era `/pratiche/operatori/`, che e' PER REPARTO. Qui si
    #        elencano tutte le attive, con ricerca libera opzionale.
    # ⚠️ `solo_attive=True` e' il default del picker: una persona disattivata
    #        non si assegna (il require sul figlio la rifiuterebbe a DB). Chi
    #        deve MOSTRARE un'assegnazione gia' fatta a una persona poi spenta
    #        legge il display dal proprio dettaglio, non da qui.
    def list_risorse_umane_lookup(
        self, *, search: str | None = None, solo_attive: bool = True,
    ) -> list[dict]:
        condizioni: list[str] = []
        params: list[Any] = []
        if solo_attive:
            condizioni.append("v.risorsa_umana_attivo = true")
        # La guardia legge il PATTERN, non il termine grezzo: «  » e' un
        # termine assente, e con `if search:` diventava `ILIKE NULL` (zero righe).
        pattern = pattern_contiene(search)
        if pattern is not None:
            condizioni.append("v.ragione_sociale_completa ILIKE %s")
            params.append(pattern)
        return self._risorse_umane_lookup(condizioni, params)

    # Scopo: LA query del lookup delle risorse umane.
    #        Legge la VISTA MODELLO `anagrafiche.vw_risorse_umane_dettaglio`
    #        (risorsa + soggetto + qualifica + unita' organizzativa): il nome
    #        della persona e' la `ragione_sociale_completa` del soggetto, e la
    #        catena che ce lo porta vive nella vista, non qui — riscriverla
    #        per join in ogni lettore e' il modo in cui due picker della
    #        stessa persona finiscono per chiamarla in due modi.
    # ⚠️ La vista legge il soggetto da `risorse_umane.soggetto_id`, che
    #        `trgfn_risorse_umane_guard_ruolo` tiene uguale a quello del
    #        `soggetto_ruolo`: e' la stessa persona per costruzione, senza
    #        passare da `soggetti_ruoli`.
    # ⚠️ `condizioni` sono letterali di questa classe, i VALORI viaggiano in
    #        `params`: la forma di `conta_con_perimetro`.
    def _risorse_umane_lookup(
        self, condizioni: list[str], params: list[Any],
    ) -> list[dict]:
        where = f"WHERE {' AND '.join(condizioni)}" if condizioni else ""
        sql = f"""
            SELECT v.risorsa_umana_id            AS id,
                   v.ragione_sociale_completa    AS display,
                   v.risorsa_umana_attivo        AS attivo,
                   v.qualifica_descrizione,
                   v.unita_organizzativa_descrizione
              FROM anagrafiche.vw_risorse_umane_dettaglio v
             {where}
             ORDER BY v.ragione_sociale_completa, v.risorsa_umana_id
        """  # noqa: S608 — condizioni da letterali della classe, valori in params
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return rows_to_list(cursor)
