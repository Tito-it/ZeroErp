# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB al modello del documento (guida
#        `modello-documento-di-vendita.md` §6): l'azione di processo che un
#        passaggio di stato chiede, letta dalla riga della matrice con
#        `script.fn_doc_passaggio`, il lettore unico che usano anche il verbo e
#        le capability. Generico per ogni testata della mappa
#        `script.fn_doc_stato_modello`: un documento portato al modello non
#        scrive niente qui.
# ------------------------------------------------------------

from __future__ import annotations

from django.db import connection


class DocumentoModelloRepository:
    """Letture del modello del documento per il backend."""

    # Scopo: L'azione di processo del passaggio dallo stato CORRENTE del
    #        documento allo stato chiesto (codice), o None: riga senza azione
    #        (basta il permesso sul documento), passaggio fuori matrice, stato
    #        chiesto inesistente, documento che non c'e' o non si vede. In tutti
    #        i casi None il rifiuto, se c'e', lo da' chi viene dopo (il service o
    #        il verbo), col suo codice.
    # ⚠️ Lo stato chiesto arriva come CODICE e si traduce in id su
    #    `codice_interno` del vocabolario: la colonna c'e', UNIQUE, in tutti i
    #    vocabolari della mappa, ma la mappa non la dichiara. E' la sola cosa che
    #    il backend sa del vocabolario; la funzione DB che la toglie di qui e'
    #    chiesta in brief-modello-documento-vendita §7.9.
    # ⛔ Una testata fuori mappa e' un errore di cablaggio della view, non di
    #    dati: RuntimeError (500), non un None che farebbe passare col solo
    #    livello.
    # Parametri: testata — nome qualificato (`vendite.ddt`), costante del codice.
    def azione_del_passaggio(
        self, testata: str, documento_id: int, stato_a_codice: str,
    ) -> str | None:
        with connection.cursor() as cursor:
            # Gli identificatori dal catalogo, quotati dal DB: il testo di un
            # regclass dipende dal search_path, i nomi qualificati no.
            cursor.execute(
                """
                SELECT quote_ident(tn.nspname) || '.' || quote_ident(tc.relname),
                       quote_ident(m.colonna_stato),
                       quote_ident(vn.nspname) || '.' || quote_ident(vc.relname)
                  FROM script.fn_doc_stato_modello(%s::regclass) m
                  JOIN pg_catalog.pg_class tc     ON tc.oid = %s::regclass
                  JOIN pg_catalog.pg_namespace tn ON tn.oid = tc.relnamespace
                  JOIN pg_catalog.pg_class vc     ON vc.oid = m.vocabolario
                  JOIN pg_catalog.pg_namespace vn ON vn.oid = vc.relnamespace
                """,
                [testata, testata],
            )
            mappa = cursor.fetchone()
            if mappa is None:
                raise RuntimeError(
                    f"DocumentoModelloRepository: {testata} non e' nella mappa "
                    "script.fn_doc_stato_modello"
                )
            tabella, colonna, vocabolario = mappa
            cursor.execute(
                f"""
                SELECT p.azione_processo_codename
                  FROM {tabella} t
                 CROSS JOIN LATERAL script.fn_doc_passaggio(
                       %s::regclass, t.{colonna},
                       (SELECT v.id FROM {vocabolario} v WHERE v.codice_interno = %s)) p
                 WHERE t.id = %s
                """,  # noqa: S608 — identificatori dal catalogo, quotati dal DB; valori come parametri
                [testata, stato_a_codice, int(documento_id)],
            )
            row = cursor.fetchone()
        return str(row[0]) if row and row[0] is not None else None
