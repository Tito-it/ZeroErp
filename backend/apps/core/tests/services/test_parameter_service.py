# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per ParameterService — risoluzione parametri
#        con override, conversione a intero, lista per utente,
#        CRUD override personale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) ParameterServiceTests.test_get_parameter_returns_value
 2) ParameterServiceTests.test_get_parameter_not_found_raises
 3) ParameterServiceTests.test_get_parameter_int_returns_int
 4) ParameterServiceTests.test_get_parameter_int_invalid_raises
 4b) ParameterServiceTests.test_get_parameter_decimal_returns_decimal
 4c) ParameterServiceTests.test_get_parameter_decimal_invalid_raises
 5) ParameterServiceTests.test_get_defaults_returns_dict
 6) ParameterServiceTests.test_get_defaults_empty_codes
 7) ParameterServiceTests.test_get_parameter_passes_user_context
 8) ParameterServiceTests.test_get_parameter_passes_emittente_fiscale
 9) ParameterServiceTests.test_list_parameters_for_user
10) ParameterServiceTests.test_upsert_user_override
11) ParameterServiceTests.test_upsert_user_override_empty_code_raises
12) ParameterServiceTests.test_delete_user_override
13) ParameterServiceTests.test_delete_user_override_not_found_raises
14) ParameterServiceTests.test_get_emittente_fiscale_id_for_user
15) ParameterServiceTests.test_upsert_parametro_inesistente_e_404_a_ogni_livello (E-9)
16) ParameterServiceTests.test_get_default_date_legge_il_default
17) ParameterServiceTests.test_get_default_date_assente_o_vuoto
18) ParameterServiceTests.test_get_default_date_non_iso
"""

from datetime import date
from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch, MagicMock

from apps.core.services.parameter_service import ParameterService
from apps.core.services.service_errors import ServiceError

REPO_PATH = "apps.core.services.parameter_service.ParameterRepository"


class ParameterServiceTests(TestCase):

    def setUp(self):
        self._patcher = patch(REPO_PATH)
        self._mock_repo_cls = self._patcher.start()
        self._mock_repo = MagicMock()
        self._mock_repo_cls.return_value = self._mock_repo
        self.svc = ParameterService()

    def tearDown(self):
        self._patcher.stop()

    # Scopo: Verifica che get_parameter restituisca il valore dal repository.
    def test_get_parameter_returns_value(self):
        self._mock_repo.get_parameter.return_value = "16"
        result = self.svc.get_parameter("PARAM_TEST")
        self.assertEqual(result, "16")
        self._mock_repo.get_parameter.assert_called_once_with(
            "PARAM_TEST", None, None, None,
            categoria_cliente_id=None,
        )

    # Scopo: Verifica che get_parameter lanci ServiceError se il parametro non esiste.
    def test_get_parameter_not_found_raises(self):
        self._mock_repo.get_parameter.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            self.svc.get_parameter("INESISTENTE")
        self.assertEqual(ctx.exception.code, "E_PARAMETER_NOT_FOUND")

    # Scopo: Verifica che get_parameter_int converta correttamente a intero.
    def test_get_parameter_int_returns_int(self):
        self._mock_repo.get_parameter.return_value = "42"
        result = self.svc.get_parameter_int("PARAM_TEST")
        self.assertEqual(result, 42)
        self.assertIsInstance(result, int)

    # Scopo: Verifica che get_parameter_int lanci errore per valore non numerico.
    def test_get_parameter_int_invalid_raises(self):
        self._mock_repo.get_parameter.return_value = "non_un_numero"
        with self.assertRaises(ServiceError) as ctx:
            self.svc.get_parameter_int("BAD_PARAM")
        self.assertEqual(ctx.exception.code, "E_PARAMETER_VALIDATION")

    # Scopo: Verifica che get_parameter_decimal converta correttamente (L2 Sprint D).
    def test_get_parameter_decimal_returns_decimal(self):
        self._mock_repo.get_parameter.return_value = "15.5"
        result = self.svc.get_parameter_decimal("VENDITE_MAX_SCONTO_PCT")
        self.assertEqual(result, Decimal("15.5"))
        self.assertIsInstance(result, Decimal)

    # Scopo: Verifica che get_parameter_decimal lanci errore per valore malformato.
    def test_get_parameter_decimal_invalid_raises(self):
        self._mock_repo.get_parameter.return_value = "quindici"
        with self.assertRaises(ServiceError) as ctx:
            self.svc.get_parameter_decimal("BAD_DECIMAL")
        self.assertEqual(ctx.exception.code, "E_PARAMETER_VALIDATION")

    # Scopo: Verifica che get_defaults restituisca un dizionario di parametri.
    def test_get_defaults_returns_dict(self):
        self._mock_repo.get_parameters.return_value = {
            "PARAM_TEST": "16",
            "DEFAULT_CURRENCY": "EUR",
        }
        result = self.svc.get_defaults(["PARAM_TEST", "DEFAULT_CURRENCY"])
        self.assertEqual(len(result), 2)
        self.assertEqual(result["PARAM_TEST"], "16")
        self.assertEqual(result["DEFAULT_CURRENCY"], "EUR")

    # Scopo: Verifica che get_defaults con lista vuota restituisca dizionario vuoto.
    def test_get_defaults_empty_codes(self):
        self._mock_repo.get_parameters.return_value = {}
        result = self.svc.get_defaults([])
        self.assertEqual(result, {})

    # Scopo: Verifica che il contesto utente venga passato al repository.
    def test_get_parameter_passes_user_context(self):
        self._mock_repo.get_parameter.return_value = "99"
        self.svc.get_parameter("TEST_PARAM", django_user_id=5, group_ids=[1, 2])
        self._mock_repo.get_parameter.assert_called_once_with(
            "TEST_PARAM", 5, [1, 2], None,
            categoria_cliente_id=None,
        )

    # Scopo: Verifica che emittente_fiscale_id venga propagato al repository.
    def test_get_parameter_passes_emittente_fiscale(self):
        self._mock_repo.get_parameter.return_value = "10"
        self.svc.get_parameter(
            "PARAM_TEST",
            django_user_id=5,
            group_ids=[1],
            emittente_fiscale_id=3,
        )
        self._mock_repo.get_parameter.assert_called_once_with(
            "PARAM_TEST", 5, [1], 3,
            categoria_cliente_id=None,
        )

    # Scopo: Verifica che categoria_cliente_id venga propagato al repository
    # (cascata estesa 2026-05-15: user -> categoria_cliente -> group -> ...).
    def test_get_parameter_passes_categoria_cliente(self):
        self._mock_repo.get_parameter.return_value = "5.0"
        self.svc.get_parameter(
            "VENDITE_MAX_SCONTO_PCT",
            django_user_id=5,
            emittente_fiscale_id=3,
            categoria_cliente_id=12,
        )
        self._mock_repo.get_parameter.assert_called_once_with(
            "VENDITE_MAX_SCONTO_PCT", 5, None, 3,
            categoria_cliente_id=12,
        )

    # Scopo: Verifica che categoria_cliente_id venga propagato anche su batch
    # get_defaults (PricingLimitiUtenteView resuita 2 chiavi in un colpo).
    def test_get_defaults_passes_categoria_cliente(self):
        self._mock_repo.get_parameters.return_value = {
            "VENDITE_MAX_SCONTO_PCT": "5",
            "VENDITE_MAX_MAGGIORAZIONE_PCT": "20",
        }
        self.svc.get_defaults(
            ["VENDITE_MAX_SCONTO_PCT", "VENDITE_MAX_MAGGIORAZIONE_PCT"],
            django_user_id=5,
            emittente_fiscale_id=3,
            categoria_cliente_id=12,
        )
        self._mock_repo.get_parameters.assert_called_once_with(
            ["VENDITE_MAX_SCONTO_PCT", "VENDITE_MAX_MAGGIORAZIONE_PCT"],
            5, None, 3,
            categoria_cliente_id=12,
        )

    # Scopo: Verifica che list_parameters_for_user deleghi al repository.
    def test_list_parameters_for_user(self):
        mock_data = [
            {
                "code": "PARAM_TEST",
                "description": "IVA default",
                "default_value": "22",
                "emittente_value": "10",
                "group_value": None,
                "categoria_cliente_value": None,
                "categoria_cliente_override_id": None,
                "user_value": "5",
                "user_override_id": 42,
                "resolved_value": "5",
            },
        ]
        self._mock_repo.list_for_user.return_value = (mock_data, 1)
        result = self.svc.list_parameters_for_user(
            django_user_id=1, group_ids=[2], emittente_fiscale_id=3,
        )
        self.assertEqual(result, (mock_data, 1))
        self._mock_repo.list_for_user.assert_called_once_with(
            1, [2], 3, categoria_cliente_id=None,
            search=None, order_by=None, order_dir=None, limit=25, offset=0,
        )

    # Scopo: Verifica che list_parameters_for_user propaghi categoria_cliente_id
    #        al repository (post brief DB 2026-05-19, migration 20260519-01).
    def test_list_parameters_for_user_propaga_categoria(self):
        self._mock_repo.list_for_user.return_value = ([], 0)
        self.svc.list_parameters_for_user(
            django_user_id=1, group_ids=[2], emittente_fiscale_id=3,
            categoria_cliente_id=12,
        )
        self._mock_repo.list_for_user.assert_called_once_with(
            1, [2], 3, categoria_cliente_id=12,
            search=None, order_by=None, order_dir=None, limit=25, offset=0,
        )

    # Scopo: Verifica che upsert_user_override chiami il repository e restituisca l'ID.
    def test_upsert_user_override(self):
        self._mock_repo.upsert_user_override.return_value = 99
        result = self.svc.upsert_user_override("PARAM_TEST", 5, "10")
        self.assertEqual(result, 99)
        self._mock_repo.upsert_user_override.assert_called_once_with(
            "PARAM_TEST", 5, "10",
        )

    # Scopo: Verifica che upsert con codice vuoto lanci errore.
    def test_upsert_user_override_empty_code_raises(self):
        with self.assertRaises(ServiceError) as ctx:
            self.svc.upsert_user_override("", 5, "10")
        self.assertEqual(ctx.exception.code, "E_PARAMETER_VALIDATION")

    # Scopo: Verifica che delete_user_override chiami il repository.
    def test_delete_user_override(self):
        self._mock_repo.delete_user_override.return_value = True
        result = self.svc.delete_user_override(42, 5)
        self.assertTrue(result)
        self._mock_repo.delete_user_override.assert_called_once_with(42, 5)

    # Scopo: Verifica che delete_user_override lanci errore se non trovato.
    def test_delete_user_override_not_found_raises(self):
        self._mock_repo.delete_user_override.return_value = False
        with self.assertRaises(ServiceError) as ctx:
            self.svc.delete_user_override(42, 5)
        self.assertEqual(ctx.exception.code, "E_PARAMETER_NOT_FOUND")

    # Scopo: Verifica che get_emittente_fiscale_id_for_user deleghi al repository.
    def test_get_emittente_fiscale_id_for_user(self):
        self._mock_repo.get_emittente_fiscale_id_for_user.return_value = 7
        result = self.svc.get_emittente_fiscale_id_for_user(1)
        self.assertEqual(result, 7)
        self._mock_repo.get_emittente_fiscale_id_for_user.assert_called_once_with(1)

    # === Phase B 2026-05-19: CRUD scope categoria_cliente ===

    # Scopo: Verifica che upsert_categoria_cliente_override chiami il repository.
    def test_upsert_categoria_cliente_override(self):
        self._mock_repo.upsert_categoria_cliente_override.return_value = 314
        result = self.svc.upsert_categoria_cliente_override(
            "VENDITE_MAX_SCONTO_PCT", 12, "5",
        )
        self.assertEqual(result, 314)
        self._mock_repo.upsert_categoria_cliente_override.assert_called_once_with(
            "VENDITE_MAX_SCONTO_PCT", 12, "5",
        )

    # Scopo: Verifica validazione categoria_cliente_id <= 0.
    def test_upsert_categoria_cliente_override_id_invalido(self):
        with self.assertRaises(ServiceError) as ctx:
            self.svc.upsert_categoria_cliente_override("CODE", 0, "v")
        self.assertEqual(ctx.exception.code, "E_PARAMETER_VALIDATION")
        self._mock_repo.upsert_categoria_cliente_override.assert_not_called()

    # Scopo: Verifica validazione parameter_code vuoto.
    def test_upsert_categoria_cliente_override_code_vuoto(self):
        with self.assertRaises(ServiceError) as ctx:
            self.svc.upsert_categoria_cliente_override("", 12, "v")
        self.assertEqual(ctx.exception.code, "E_PARAMETER_VALIDATION")

    # Scopo: Verifica che delete_categoria_cliente_override chiami il repository.
    def test_delete_categoria_cliente_override(self):
        self._mock_repo.delete_categoria_cliente_override.return_value = True
        result = self.svc.delete_categoria_cliente_override(314, 12)
        self.assertTrue(result)
        self._mock_repo.delete_categoria_cliente_override.assert_called_once_with(
            314, 12,
        )

    # Scopo: Verifica che delete_categoria_cliente_override lanci 404.
    def test_delete_categoria_cliente_override_not_found_raises(self):
        self._mock_repo.delete_categoria_cliente_override.return_value = False
        with self.assertRaises(ServiceError) as ctx:
            self.svc.delete_categoria_cliente_override(314, 12)
        self.assertEqual(ctx.exception.code, "E_PARAMETER_NOT_FOUND")

    # Scopo: ⭐ E-9 — parametro inesistente nell'upsert di OGNI livello:
    # 404 `E_PARAMETER_NOT_FOUND`, non `E_DATABASE`. Il repository torna None
    # quando il codice non risolve (niente INSERT con `parameter_id` NULL).
    def test_upsert_parametro_inesistente_e_404_a_ogni_livello(self):
        casi = (
            ("upsert_user_override", 7),
            ("upsert_emittente_override", 3),
            ("upsert_categoria_cliente_override", 12),
        )
        for metodo, scope in casi:
            with self.subTest(metodo=metodo):
                getattr(self._mock_repo, metodo).return_value = None
                with self.assertRaises(ServiceError) as ctx:
                    getattr(self.svc, metodo)("NON_ESISTE", scope, "v")
                self.assertEqual(ctx.exception.code, "E_PARAMETER_NOT_FOUND")

    # Scopo: get_default_date legge il DEFAULT nudo (mai la cascata) e lo
    #        converte a date.
    def test_get_default_date_legge_il_default(self):
        self._mock_repo.get_default_value.return_value = " 2020-01-01 "
        self.assertEqual(self.svc.get_default_date("P_DATA"), date(2020, 1, 1))
        self._mock_repo.get_default_value.assert_called_once_with("P_DATA")
        self._mock_repo.get_parameter.assert_not_called()

    # Scopo: Parametro assente, default NULL o vuoto -> E_CONFIG_MANCANTE.
    def test_get_default_date_assente_o_vuoto(self):
        for valore in (None, "", "   "):
            self._mock_repo.get_default_value.return_value = valore
            with self.assertRaises(ServiceError) as ctx:
                self.svc.get_default_date("P_DATA")
            self.assertEqual(ctx.exception.code, "E_CONFIG_MANCANTE")

    # Scopo: Valore non ISO -> E_CONFIG_MANCANTE parlante, mai un 500.
    def test_get_default_date_non_iso(self):
        for valore in ("01/01/2020", "2020-02-30", "domani"):
            self._mock_repo.get_default_value.return_value = valore
            with self.assertRaises(ServiceError) as ctx:
                self.svc.get_default_date("P_DATA")
            self.assertEqual(ctx.exception.code, "E_CONFIG_MANCANTE")
