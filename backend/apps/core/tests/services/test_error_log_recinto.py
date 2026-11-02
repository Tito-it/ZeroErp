# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: IL RECINTO fra i test e il diario tecnico `dbops.error_log`. Presidia
#        che la suite non scriva nel diario, e che a spegnerlo sia il RUNNER —
#        non la buona volonta' di chi lancia i test.
#
#        PERCHE' ESISTE. I test girano contro il database configurato vero
#        (nessuno dichiara un database, quindi Django non ne crea uno
#        usa-e-getta). Un test che esercita un service con `log_to_db=True`
#        sostituisce il repository con un mock, ma NON il logger: la riga
#        finisce nel diario davvero, con `area='backend'`, indistinguibile da un
#        errore accaduto a un utente. Il 2026-08-19 il team DB ha letto 587
#        occorrenze di un codice che il database non puo' piu' sollevare e ne ha
#        dedotto un difetto del pricing: erano 587 esecuzioni di
#        `test_pricing_service.py`
#        (work-in-progress/brief-be-pricing-codice-errore-fantasma.md §10).
#
#        ⚠️ Nessun accesso DB: la connessione e' sostituita da un mock, cosi'
#        il test che sorveglia le scritture non ne fa una sua.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_il_runner_ha_spento_il_diario      — il recinto e' attivo ORA, in questa suite
 2) test_log_error_only_non_scrive          — flag spenta -> nessun cursore aperto
 3) test_log_error_only_scrive_se_acceso    — flag accesa -> SQL eseguito (produzione)
 4) test_raise_error_non_scrive             — la via vera dei service: log_to_db=True
 5) test_settings_dichiara_il_runner        — TEST_RUNNER punta a ZeroErpTestRunner
"""

from __future__ import annotations

from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from apps.core.services.error_manager import ErrorManager
from apps.core.services.service_errors import ServiceError

_CONNECTION = "apps.core.services.error_manager.connection"


class ErrorLogRecinto(SimpleTestCase):
    # Scopo: il cancello vero. Non verifica un ramo di codice: verifica lo STATO
    #        dell'ambiente in cui gira l'intera suite. Se qualcuno togliesse
    #        `TEST_RUNNER` dalle settings, i test 2-4 resterebbero verdi (la
    #        flag la impostano loro) e solo questo diventerebbe rosso.
    def test_il_runner_ha_spento_il_diario(self):
        self.assertFalse(
            settings.ERROR_LOG_DB_ENABLED,
            "il diario dbops.error_log e' ACCESO durante i test: le righe "
            "scritte da qui sono indistinguibili da errori veri di produzione "
            "(vedi brief-be-pricing-codice-errore-fantasma.md §10)",
        )

    def test_log_error_only_non_scrive(self):
        with patch(_CONNECTION) as mock_conn:
            ErrorManager.log_error_only(code="E_QUALUNQUE", context={"a": 1})
        mock_conn.cursor.assert_not_called()

    @override_settings(ERROR_LOG_DB_ENABLED=True)
    def test_log_error_only_scrive_se_acceso(self):
        # Il comportamento di produzione non cambia: quando la flag e' accesa
        # la scrittura avviene. Senza questo, il recinto potrebbe essere un
        # `return` incondizionato e nessuno se ne accorgerebbe.
        with patch(_CONNECTION) as mock_conn:
            ErrorManager.log_error_only(code="E_QUALUNQUE", context={"a": 1})
        cursor = mock_conn.cursor.return_value.__enter__.return_value
        cursor.execute.assert_called_once()
        self.assertIn("fn_log_error_only", cursor.execute.call_args.args[0])

    def test_raise_error_non_scrive(self):
        # La via che percorrono davvero i service: `log_to_db=True`. Il recinto
        # sta nel punto centrale, quindi vale anche di qui senza che il
        # chiamante sappia nulla.
        with patch(_CONNECTION) as mock_conn:
            with self.assertRaises(ServiceError):
                ErrorManager.raise_error(
                    code="E_QUALUNQUE",
                    message="messaggio",
                    log_to_db=True,
                )
        mock_conn.cursor.assert_not_called()

    def test_settings_dichiara_il_runner(self):
        self.assertEqual(
            settings.TEST_RUNNER,
            "zeroerp_backend.test_runner.ZeroErpTestRunner",
        )
