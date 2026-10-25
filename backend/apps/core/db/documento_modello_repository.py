# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB al modello del documento (guida
#        `modello-documento-di-vendita.md` §6): l'azione di processo che un
#        passaggio di stato chiede, la traduzione codice -> id dello stato e lo
#        stato di emissione, letti dai lettori unici del DB
#        (`script.fn_doc_azione_passaggio`, `script.fn_doc_stato_id`,
#        `script.fn_stato_emissione_id`), gli stessi che usano i verbi e le
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

from django.db import connection


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

    # Scopo: L'id dello stato ATTIVO con quel codice nel vocabolario della
    #        testata, o None (nessuno stato attivo con quel codice: l'errore lo
    #        decide il chiamante). Uno stato spento non e' una destinazione (U-3).
    def stato_id(self, testata: str, codice: str) -> int | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT script.fn_doc_stato_id(%s::regclass, %s)",
                [testata, codice],
            )
            row = cursor.fetchone()
        return int(row[0]) if row and row[0] is not None else None

    # Scopo: Lo stato chiesto (codice) e' lo stato di emissione della testata?
    #        False anche per un documento che non si emette (vocabolario senza
    #        la colonna `emissione`) e per un codice che non e' uno stato attivo.
    def e_stato_di_emissione(self, testata: str, codice: str) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COALESCE(script.fn_doc_stato_id(%s::regclass, %s)"
                "                = script.fn_stato_emissione_id(%s::regclass), false)",
                [testata, codice, testata],
            )
            row = cursor.fetchone()
        return bool(row and row[0])
