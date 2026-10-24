# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `ErrorManager.raise_error` solleva SEMPRE ed e' dichiarato `NoReturn`
#        (dal 2026-09-28): e' la premessa per cui dopo una chiamata non si
#        scrive piu' una riga `raise AssertionError("unreachable")`.
# Note: se un giorno `raise_error` potesse tornare, il codice che lo chiama
#       proseguirebbe in silenzio oltre un errore: qui ogni ramo si prova.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) RaiseErrorTests.test_solleva_service_error_col_codice
2) RaiseErrorTests.test_con_cause_la_concatena
3) RaiseErrorTests.test_con_log_to_db_solleva_dopo_aver_scritto
4) RaiseErrorTests.test_dichiarato_noreturn
5) RaiseErrorTests.test_i_traduttori_che_lo_usano_per_ultimi_sono_noreturn
6) DiarioDopoLaTransazioneTests.test_le_righe_si_scrivono_all_uscita
7) DiarioDopoLaTransazioneTests.test_annidato_consegna_le_righe_all_esterno
"""

import typing
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.core.services.error_manager import ErrorManager
from apps.core.services.service_errors import ServiceError


class RaiseErrorTests(SimpleTestCase):

    def test_solleva_service_error_col_codice(self):
        with self.assertRaises(ServiceError) as ctx:
            ErrorManager.raise_error(code="E_PROVA", message="m")
        self.assertEqual(ctx.exception.code, "E_PROVA")

    def test_con_cause_la_concatena(self):
        causa = ValueError("origine")
        with self.assertRaises(ServiceError) as ctx:
            ErrorManager.raise_error(code="E_PROVA", message="m", cause=causa)
        self.assertIs(ctx.exception.__cause__, causa)

    # Il ramo che scrive sul diario tecnico solleva anche lui, dopo la scrittura.
    @patch.object(ErrorManager, "log_error_only")
    def test_con_log_to_db_solleva_dopo_aver_scritto(self, mock_log):
        with self.assertRaises(ServiceError):
            ErrorManager.raise_error(code="E_PROVA", message="m", log_to_db=True)
        mock_log.assert_called_once()

    def test_dichiarato_noreturn(self):
        self.assertIs(typing.get_type_hints(ErrorManager.raise_error)["return"], typing.NoReturn)

    # Chi chiude con `raise_error`/`map_integrity_error` e non ha altro dopo
    # dichiara lo stesso contratto: i chiamanti non scrivono l'«irraggiungibile».
    def test_i_traduttori_che_lo_usano_per_ultimi_sono_noreturn(self):
        from apps.catalogo.services.catalogo_service import _translate_nota_integrity_error
        from apps.core.services.payload_helpers import map_integrity_error
        from apps.pratiche.services.pratiche_service import _raise_known_db_error
        from apps.vendite.services.famiglie_service import FamiglieDocumentoService
        from apps.vendite.services.listini_service import _translate_integrity_error
        from apps.vendite.services.registri_service import RegistriService

        # I traduttori locali (dal 2026-09-28): `_raise_known_db_error` chiude
        # con `raise exc` quando non riconosce l'errore, gli altri con
        # `raise_error`/`map_integrity_error` su ogni ramo.
        for funzione in (
            map_integrity_error,
            _translate_integrity_error,
            _raise_known_db_error,
            _translate_nota_integrity_error,
            FamiglieDocumentoService._traduci,
            RegistriService._traduci,
        ):
            with self.subTest(funzione=funzione.__name__):
                self.assertIs(typing.get_type_hints(funzione)["return"], typing.NoReturn)


# ⭐ Il rinvio del diario a dopo la transazione (BE-2,
#    `diario_dopo_la_transazione`): qui la regola, senza database; il caso
#    vero della transazione abortita lo prova `tests/db/test_idempotency_prenota_db.py`.
@override_settings(ERROR_LOG_DB_ENABLED=True)
class DiarioDopoLaTransazioneTests(SimpleTestCase):

    def test_le_righe_si_scrivono_all_uscita(self):
        with patch.object(ErrorManager, "_scrivi_diario") as scrivi:
            with ErrorManager.diario_dopo_la_transazione():
                ErrorManager.log_error_only(code="E_PROVA", context={})
                scrivi.assert_not_called()
            self.assertEqual(scrivi.call_count, 1)
            self.assertEqual(scrivi.call_args.args[0][2], "E_PROVA")

    def test_annidato_consegna_le_righe_all_esterno(self):
        with patch.object(ErrorManager, "_scrivi_diario") as scrivi:
            with ErrorManager.diario_dopo_la_transazione():
                with ErrorManager.diario_dopo_la_transazione():
                    ErrorManager.log_error_only(code="E_PROVA", context={})
                scrivi.assert_not_called()
            self.assertEqual(scrivi.call_count, 1)
