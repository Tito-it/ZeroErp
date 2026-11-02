# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: UN FALLIMENTO, UNA RIGA. Presidia la decisione DB+BE del 2026-08-19:
#        quando l'errore lo ha gia' scritto nel diario il DATABASE, il backend
#        non lo riscrive.
#
#        IL CONFINE, che e' la parte da non sbagliare. Il segnale non e' «viene
#        dal DB»: e' il CAMPO STRUTTURATO, valorizzato solo da
#        `script.fn_log_and_raise_error` — che prima di sollevare ha scritto la
#        sua riga (via dblink, quindi sopravvive al rollback del RAISE). Gli
#        altri errori del database — i ~135 `RAISE EXCEPTION` diretti, le
#        violazioni di vincolo, i timeout — nel diario NON ci sono, e quelli
#        continua a scriverli il backend: li' non c'e' nessun doppione da
#        evitare, c'e' una riga da non perdere.
#
#        Riferimento: work-in-progress/brief-be-pricing-codice-errore-fantasma.md
#        §13 (il difetto) e §14-ter (la decisione).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_errore_del_db_non_viene_riloggato   — campo strutturato -> il BE tace
 2) test_raise_diretto_viene_loggato         — campo assente -> il BE scrive
 3) test_violazione_vincolo_viene_loggata    — SQLSTATE 23505 -> il BE scrive
 4) test_la_risposta_non_cambia              — la scelta tocca il diario, non il codice
 5) test_col_campo_strutturato_la_frase_e_del_db — dal 2026-09-23 la frase e' del catalogo
"""

from __future__ import annotations

from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.services.error_manager import ErrorManager
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_error_fakes import make_db_error

_LOG = "apps.core.services.error_manager.ErrorManager.log_error_only"
_MARKERS = (("E_ESEMPIO", ("marcatore riconoscibile",)),)


def _traduci(exc):
    return ErrorManager.raise_from_database_error(
        exc,
        known_markers=_MARKERS,
        fallback_code="E_FALLBACK",
        message="messaggio utente",
        context={"chiave": "valore"},
        function_name="test.service",
    )


class ErrorLogNoDuplicazione(SimpleTestCase):
    def test_errore_del_db_non_viene_riloggato(self):
        # `codice` valorizzato = l'errore e' passato da fn_log_and_raise_error,
        # che ha gia' scritto la riga.
        exc = make_db_error("marcatore riconoscibile", codice="E_ESEMPIO")
        with patch(_LOG) as mock_log:
            with self.assertRaises(ServiceError):
                _traduci(exc)
        mock_log.assert_not_called()

    def test_raise_diretto_viene_loggato(self):
        # `codice=None` = RAISE EXCEPTION diretto: il DB non ha scritto niente.
        exc = make_db_error("marcatore riconoscibile", codice=None)
        with patch(_LOG) as mock_log:
            with self.assertRaises(ServiceError):
                _traduci(exc)
        mock_log.assert_called_once()

    def test_violazione_vincolo_viene_loggata(self):
        # Errore PG vero: nessun diario lato DB, la riga la scrive il backend.
        exc = make_db_error(
            "duplicate key value violates unique constraint",
            codice="uq_qualcosa",
            sqlstate="23505",
        )
        with patch(_LOG) as mock_log:
            with self.assertRaises(ServiceError):
                _traduci(exc)
        mock_log.assert_called_once()

    def test_la_risposta_non_cambia(self):
        # Il codice consegnato al chiamante e' lo stesso nei due casi: la
        # scelta di chi scrive nel diario non tocca l'esito.
        with patch(_LOG):
            with self.assertRaises(ServiceError) as senza:
                _traduci(make_db_error("marcatore riconoscibile", codice=None))
            with self.assertRaises(ServiceError) as con:
                _traduci(make_db_error("marcatore riconoscibile", codice="E_ESEMPIO"))
        self.assertEqual(senza.exception.code, con.exception.code)

    def test_col_campo_strutturato_la_frase_e_del_db(self):
        # ⭐ La frase invece si': col campo strutturato e' quella del catalogo
        # (Tid, 2026-09-23 — brief-db-guard-date-validita §13); sul ripiego a
        # marker resta quella del chiamante, perche' un RAISE diretto non ha
        # una frase di catalogo da dare.
        with patch(_LOG):
            with self.assertRaises(ServiceError) as senza:
                _traduci(make_db_error("marcatore riconoscibile", codice=None))
            with self.assertRaises(ServiceError) as con:
                _traduci(make_db_error("marcatore riconoscibile", codice="E_ESEMPIO"))
        self.assertEqual(senza.exception.message, "messaggio utente")
        self.assertEqual(con.exception.message, "marcatore riconoscibile")
