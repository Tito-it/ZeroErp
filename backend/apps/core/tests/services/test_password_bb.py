# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del BB password: `password_digitata` (lettura dal corpo, senza
#        ripulire) e `valida_nuova_password` (regole della nuova password,
#        comuni a reset, attivazione e cambio password).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_password_digitata_tiene_gli_spazi
2) test_password_digitata_assente_e_vuota
3) test_password_digitata_non_testo_rifiutata
4) test_nuova_password_vuota_rifiutata
5) test_conferma_diversa_rifiutata
6) test_validatori_django_col_codice_del_flusso
7) test_nuova_password_valida_passa
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.core.exceptions import ValidationError as DjangoValidationError

from apps.core.api.payload_validators import password_digitata
from apps.core.services.auth_helpers import valida_nuova_password
from apps.core.services.service_errors import ServiceError

_VALIDATE = "apps.core.services.auth_helpers.validate_password"


class PasswordDigitataTests(TestCase):

    # Scopo: S-5 — la password si legge com'e' stata digitata.
    def test_password_digitata_tiene_gli_spazi(self):
        self.assertEqual(password_digitata({"pw": " segreta "}, "pw"), " segreta ")

    def test_password_digitata_assente_e_vuota(self):
        self.assertEqual(password_digitata({}, "pw"), "")
        self.assertEqual(password_digitata({"pw": None}, "pw"), "")

    # Scopo: Un numero o un oggetto non e' una password: 400, non un 500 dai
    # validatori di Django.
    def test_password_digitata_non_testo_rifiutata(self):
        for valore in (12345678, ["a"], {"a": 1}, True):
            with self.subTest(valore=valore), self.assertRaises(ValueError) as ctx:
                password_digitata({"pw": valore}, "pw")
            self.assertEqual(str(ctx.exception), "pw_invalid")


class ValidaNuovaPasswordTests(TestCase):

    @patch(_VALIDATE)
    def test_nuova_password_vuota_rifiutata(self, mock_validate):
        with self.assertRaises(ServiceError) as ctx:
            valida_nuova_password("", "", user=MagicMock(), code="E_X")
        self.assertEqual(ctx.exception.code, "E_X")
        self.assertIn("obbligatoria", ctx.exception.message)
        mock_validate.assert_not_called()

    @patch(_VALIDATE)
    def test_conferma_diversa_rifiutata(self, mock_validate):
        with self.assertRaises(ServiceError) as ctx:
            valida_nuova_password("Nuova-2026!x", "Nuova-2026!y", user=MagicMock(), code="E_X")
        self.assertIn("non coincidono", ctx.exception.message)
        mock_validate.assert_not_called()

    # Scopo: Il rifiuto dei validatori esce col codice del flusso chiamante.
    @patch(_VALIDATE, side_effect=DjangoValidationError(["Troppo corta.", "Troppo comune."]))
    def test_validatori_django_col_codice_del_flusso(self, _validate):
        with self.assertRaises(ServiceError) as ctx:
            valida_nuova_password("abc", "abc", user=MagicMock(), code="E_RESET_PASSWORD")
        self.assertEqual(ctx.exception.code, "E_RESET_PASSWORD")
        self.assertEqual(ctx.exception.message, "Troppo corta. Troppo comune.")

    @patch(_VALIDATE)
    def test_nuova_password_valida_passa(self, mock_validate):
        user = MagicMock()
        valida_nuova_password(" Nuova-2026!x ", " Nuova-2026!x ", user=user, code="E_X")
        mock_validate.assert_called_once_with(" Nuova-2026!x ", user=user)
