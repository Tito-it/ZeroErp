# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB al modello del documento (guida
#        `modello-documento-di-vendita.md` §6): l'azione di processo che un
#        passaggio di stato chiede, lo stato di emissione, quello d'annullo,
#        di cessazione, di accettazione e quello iniziale,
#        letti dai lettori unici del DB
#        (`script.fn_doc_azione_passaggio`, `script.fn_doc_stato_id`,
#        `script.fn_stato_emissione_id`, `script.fn_stato_abortito_id`,
#        `script.fn_stato_cessazione_id`, `script.fn_stato_accettazione_id`,
#        `script.fn_doc_stato_iniziale_id`,
#        `script.fn_doc_stato_codice`), gli stessi che usano i verbi e le
#        capability. Generico per ogni testata della mappa
#        `script.fn_doc_stato_modello`: un documento portato al modello non
#        scrive niente qui.
# Note: ⭐ Nessun SQL composto sulla mappa (brief-modello-documento-vendita
#       §8.7 punto 3): fino al giro 6 il backend leggeva da se' testata,
#       colonna di stato e vocabolario, e traduceva il codice su
#       `codice_interno`. Ora lo fa il DB, in un posto solo.
#       ⛔ Una testata fuori mappa e' un errore di cablaggio, non di dati: il DB
#       risponde `E_SCRIPT_CHIAMATA_NON_VALIDA` (un 500), mai un None che
#       farebbe passare col solo livello.
# ------------------------------------------------------------

from __future__ import annotations

from typing import NamedTuple

from django.db import connection


# Uno stato del modello di una testata (l'emissione, l'annullo), con le sue due
# chiavi: l'id (lo scrive chi aggiorna la colonna di stato) e il
# `codice_interno` (lo prende un verbo).
class StatoDocumento(NamedTuple):
    id: int
    codice: str


# I lettori del DB degli stati che il modello dice, interpolati nella query:
# ⛔ solo queste costanti, mai un valore che arriva da fuori.
_LETTORE_EMISSIONE = "script.fn_stato_emissione_id"
_LETTORE_ANNULLO = "script.fn_stato_abortito_id"
# La cessazione (contratti) e l'accettazione (preventivi, offerte): due colonne
# del vocabolario, non una (brief-modello-documento-vendita §17.2): l'accettazione
# non chiude il documento, la cessazione si'.
_LETTORE_CESSAZIONE = "script.fn_stato_cessazione_id"
_LETTORE_ACCETTAZIONE = "script.fn_stato_accettazione_id"
# Lo stato in cui il documento nasce, letto dalla TESTATA (`20261027-29`,
# brief-modello-documento-vendita §15.13): mai `'DRAFT'` scritto qui.
_LETTORE_INIZIALE = "script.fn_doc_stato_iniziale_id"


class DocumentoModelloRepository:
    """Letture del modello del documento per il backend."""

    # Scopo: L'azione di processo del passaggio dallo stato CORRENTE del
    #        documento allo stato chiesto (codice), o None: riga senza azione
    #        (basta il permesso sul documento), passaggio fuori matrice, stato
    #        chiesto inesistente o spento, documento che non c'e' o non si vede.
    #        In tutti i casi None il rifiuto, se c'e', lo da' chi viene dopo (il
    #        service o il verbo), col suo codice.
    # Parametri: testata — nome qualificato (`vendite.ddt`), costante del codice.
    def azione_del_passaggio(
        self, testata: str, documento_id: int, stato_a_codice: str,
    ) -> str | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT p.azione_processo_codename"
                "  FROM script.fn_doc_azione_passaggio(%s::regclass, %s, %s) p",
                [testata, int(documento_id), stato_a_codice],
            )
            row = cursor.fetchone()
        return str(row[0]) if row and row[0] is not None else None

    # ⛔ `stato_id(testata, codice)` (codice -> id dello stato attivo) e'
    #    ritirato il 2026-10-26 (ok Tid, brief-modello-documento-vendita §13.8):
    #    i suoi consumatori (`get_stato_id_by_codice` di ordini, DDT, contratti,
    #    offerte) sono spariti quando i verbi hanno preso il codice e controllano
    #    da se' che lo stato esista.

    # Scopo: Lo stato chiesto (codice) e' lo stato di emissione della testata?
    #        False anche per un documento che non si emette (vocabolario senza
    #        la colonna `emissione`) e per un codice che non e' uno stato attivo.
    def e_stato_di_emissione(self, testata: str, codice: str) -> bool:
        return self._e_stato_del_modello(_LETTORE_EMISSIONE, testata, codice)

    # Scopo: Lo stato chiesto (codice) e' lo stato d'annullo della testata
    #        (`is_abortito` del vocabolario, uno solo e attivo: Z-3)? False per
    #        un codice che non e' uno stato attivo. Gemello di
    #        `e_stato_di_emissione`.
    def e_stato_di_annullo(self, testata: str, codice: str) -> bool:
        return self._e_stato_del_modello(_LETTORE_ANNULLO, testata, codice)

    # Scopo: Lo stato chiesto (codice) e' lo stato di cessazione della testata
    #        (colonna `cessazione`, §17.2)? False per un documento che non si
    #        cessa e per un codice che non e' uno stato attivo.
    def e_stato_di_cessazione(self, testata: str, codice: str) -> bool:
        return self._e_stato_del_modello(_LETTORE_CESSAZIONE, testata, codice)

    # Scopo: Lo stato chiesto (codice) e' lo stato di accettazione della
    #        testata (colonna `accettazione`, §17.2)? False per un documento che
    #        non si accetta e per un codice che non e' uno stato attivo.
    def e_stato_di_accettazione(self, testata: str, codice: str) -> bool:
        return self._e_stato_del_modello(_LETTORE_ACCETTAZIONE, testata, codice)

    # Scopo: Lo stato di emissione della testata (id e codice), o None: il
    #        documento non si emette (vocabolario senza la colonna `emissione`).
    #        Una lettura, i due lettori composti (V-1, brief-modello-documento-
    #        vendita §8.11): `fn_stato_emissione_id` da' l'id,
    #        `fn_doc_stato_codice` lo traduce nel codice.
    # ⭐ Si chiede a ogni uso, mai a import: quale stato sia l'emissione lo dice
    #    il vocabolario (B-2), e un letterale nel codice e' una seconda sede.
    def stato_di_emissione(self, testata: str) -> StatoDocumento | None:
        return self._stato_del_modello(_LETTORE_EMISSIONE, testata)

    # Scopo: Lo stato d'annullo della testata (id e codice), o None (il
    #        vocabolario non ne dichiara uno). Gemello di `stato_di_emissione`,
    #        su `fn_stato_abortito_id`.
    def stato_di_annullo(self, testata: str) -> StatoDocumento | None:
        return self._stato_del_modello(_LETTORE_ANNULLO, testata)

    # Scopo: Lo stato di accettazione della testata (id e codice), o None (il
    #        documento non si accetta). Gemello di `stato_di_emissione`, su
    #        `fn_stato_accettazione_id`.
    def stato_di_accettazione(self, testata: str) -> StatoDocumento | None:
        return self._stato_del_modello(_LETTORE_ACCETTAZIONE, testata)

    # Scopo: Lo stato iniziale della testata (id e codice), o None (il
    #        vocabolario non ne dichiara uno). Gemello dei due sopra, su
    #        `fn_doc_stato_iniziale_id` (§15.13): l'arrivo di «riporta in
    #        bozza» del lotto.
    def stato_iniziale(self, testata: str) -> StatoDocumento | None:
        return self._stato_del_modello(_LETTORE_INIZIALE, testata)

    # Scopo: la lettura (id, codice) di uno stato del modello col suo lettore
    #        del DB. Una query sola per ogni stato del modello: cambia il lettore.
    def _stato_del_modello(self, lettore: str, testata: str) -> StatoDocumento | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT e.id, script.fn_doc_stato_codice(%s::regclass, e.id)"  # noqa: S608 — lettore dalle costanti _LETTORE_* del modulo, valori come parametri
                f"  FROM (SELECT {lettore}(%s::regclass) AS id) e",
                [testata, testata],
            )
            row = cursor.fetchone()
        if not row or row[0] is None:
            return None
        return StatoDocumento(id=int(row[0]), codice=str(row[1]))

    # Scopo: il codice chiesto e' lo stato del modello che il lettore dice?
    #        False per un codice che non e' uno stato attivo e per una testata
    #        che quello stato non lo dichiara.
    def _e_stato_del_modello(self, lettore: str, testata: str, codice: str) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COALESCE(script.fn_doc_stato_id(%s::regclass, %s)"
                f"                = {lettore}(%s::regclass), false)",
                [testata, codice, testata],
            )
            row = cursor.fetchone()
        return bool(row and row[0])
