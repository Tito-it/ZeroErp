# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test per drf_exception_handler, focalizzati sul supporto
#        default_code custom delle subclass (es. VesteNonAttivaError)
#        e sull'uso del user_message dalla policy registrata.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_default_code_custom_preserva_code_envelope — subclass con default_code E_* produce envelope con quel code
 2) test_user_message_from_policy_registry — message deriva da ErrorPolicyRegistry
 3) test_fallback_to_map_per_exception_standard — eccezione DRF standard usa _DRF_ERROR_CODE_MAP
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.response import Response

from apps.core.api.error_responses import drf_exception_handler
from apps.core.api.multi_veste_token_serializer import VesteNonAttivaError


class DrfExceptionHandlerTests(TestCase):

    @patch("apps.core.api.error_responses.drf_default_handler")
    def test_default_code_custom_preserva_code_envelope(self, mock_default):
        """VesteNonAttivaError.default_code=E_VESTE_NON_ATTIVA: l'envelope
        ha `code=E_VESTE_NON_ATTIVA`, non `E_AUTHENTICATION_FAILED` (che
        sarebbe il match naive su type(exc).__name__ subclass di
        AuthenticationFailed)."""
        mock_default.return_value = Response(
            {"detail": "..."}, status=status.HTTP_403_FORBIDDEN
        )
        exc = VesteNonAttivaError()

        response = drf_exception_handler(exc, context={})

        self.assertIsNotNone(response)
        self.assertIn("error", response.data)
        self.assertEqual(response.data["error"]["code"], "E_VESTE_NON_ATTIVA")

    @patch("apps.core.api.error_responses.drf_default_handler")
    def test_user_message_from_policy_registry(self, mock_default):
        """Il message nell'envelope deriva dalla policy registrata, non
        dal detail dell'eccezione. Garantisce consistenza del messaggio
        lato client indipendentemente dal testo runtime."""
        mock_default.return_value = Response(
            {"detail": "runtime detail ignorato"}, status=403
        )
        exc = VesteNonAttivaError()

        response = drf_exception_handler(exc, context={})

        message = response.data["error"]["message"]
        # Messaggio policy (vedi error_policies E_VESTE_NON_ATTIVA).
        self.assertIn("canale", message.lower())

    @patch("apps.core.api.error_responses.drf_default_handler")
    def test_fallback_to_map_per_exception_standard(self, mock_default):
        """Le eccezioni DRF standard (senza default_code E_*) usano la
        mappa type-name -> code. PermissionDenied -> E_PERMISSION_DENIED."""
        mock_default.return_value = Response(
            {"detail": "permission"}, status=403
        )
        exc = PermissionDenied()

        response = drf_exception_handler(exc, context={})

        self.assertEqual(response.data["error"]["code"], "E_PERMISSION_DENIED")
