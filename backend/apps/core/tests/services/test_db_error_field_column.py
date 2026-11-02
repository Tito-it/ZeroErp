# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La lettura del CAMPO da correggere dal campo strutturato `COLUMN`
#        dell'eccezione DB — passo 4 del §12 del `piano-be-classe-codici-errore`,
#        **lato che riceve**.
#
#        PERCHE' ESISTE PRIMA CHE SERVA. Oggi quasi nessuna funzione PL/pgSQL
#        valorizza `COLUMN`: il campo resta `None` e non cambia niente. Ma il
#        giorno in cui il team DB comincera' a mandarlo, il backend non deve
#        avere lavoro da fare — e soprattutto non deve *scoprire* allora se il
#        percorso regge. Questi test provano il lato che riceve su un'eccezione
#        costruita a mano, senza database.
#
#        ⚠️ E LO PROVANO ANCHE SUL CASO CHE NON DIPENDE DAL DB: su una
#        violazione NOT NULL (SQLSTATE 23502) `column_name` lo valorizza
#        PostgreSQL da solo, ed e' gia' il campo giusto. Quella meta' e' viva
#        adesso.
#
#        Gira SENZA database.
# ------------------------------------------------------------

"""Indice test previsti.

 1) test_campo_da_using_column
 2) test_campo_da_violazione_not_null            <- vivo senza fare niente
 3) test_stringa_vuota_trattata_come_assente     <- la trappola gia' pagata sul codice
 4) test_nome_implausibile_scartato
 5) test_senza_diag_nessun_campo
 6) test_il_campo_arriva_nellenvelope            <- il percorso intero
"""

from __future__ import annotations

import json
from unittest import TestCase

from django.db import DatabaseError

from apps.core.api.error_responses import exception_to_error_response
from apps.core.services.db_error_fields import structured_db_error_field


class _Diag:
    def __init__(self, **kw):
        self.column_name = kw.get("column_name")
        self.constraint_name = kw.get("constraint_name")
        self.message_primary = kw.get("message_primary")
        self.message_detail = None
        self.message_hint = None


class _Causa(Exception):
    def __init__(self, sqlstate, **diag):
        super().__init__("errore db")
        self.sqlstate = sqlstate
        self.diag = _Diag(**diag)


def _errore(sqlstate="P0001", **diag) -> DatabaseError:
    exc = DatabaseError("errore db")
    exc.__cause__ = _Causa(sqlstate, **diag)
    return exc


class DbErrorFieldColumnTest(TestCase):
    # Scopo: la strada deliberata — `RAISE ... USING COLUMN = 'partita_iva'`.
    def test_campo_da_using_column(self):
        exc = _errore("P0001", column_name="partita_iva", constraint_name="E_ANAG_PIVA")
        self.assertEqual(structured_db_error_field(exc), "partita_iva")

    # Scopo: ⭐ La strada che NON aspetta nessuno. Su una violazione NOT NULL
    #        `column_name` lo mette PostgreSQL, ed e' gia' la colonna mancante.
    #        ⚠️ Qui non c'e' il guard sullo SQLSTATE che il CODICE ha su
    #        `constraint_name`, e l'asimmetria e' voluta: `constraint_name` su un
    #        23xxx e' il nome del vincolo (che scambiato per un codice darebbe un
    #        500), mentre `column_name` e' sempre e solo una colonna.
    def test_campo_da_violazione_not_null(self):
        exc = _errore("23502", column_name="descrizione")
        self.assertEqual(structured_db_error_field(exc), "descrizione")

    # Scopo: la trappola gia' pagata sul codice errore: un campo che nasce da
    #        un'espressione NULL arriva come STRINGA VUOTA, non come None.
    def test_stringa_vuota_trattata_come_assente(self):
        self.assertIsNone(structured_db_error_field(_errore(column_name="")))

    # Scopo: un valore che non e' un nome di colonna non rimbalza al client.
    def test_nome_implausibile_scartato(self):
        for nome in ("campo con spazi", "<script>", "1_cifra", "x" * 100):
            with self.subTest(nome=nome):
                self.assertIsNone(structured_db_error_field(_errore(column_name=nome)))

    # Scopo: un'eccezione che non viene dal DB non ha niente da dire.
    def test_senza_diag_nessun_campo(self):
        self.assertIsNone(structured_db_error_field(ValueError("niente")))

    # Scopo: il percorso intero, fino all'envelope che vede il client — cioe'
    #        quello che il frontend legge in `campiErrati`.
    def test_il_campo_arriva_nellenvelope(self):
        exc = _errore("23502", column_name="descrizione", message_primary="valore nullo")
        corpo = json.loads(exception_to_error_response(exc).content)
        self.assertEqual(corpo["error"]["fields"], ["descrizione"])
