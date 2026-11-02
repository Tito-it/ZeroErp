# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
 4) test_envelope_porta_la_ui_action — i due percorsi dell'envelope portano gli stessi campi
 5) test_sottoclasse_prende_il_codice_della_madre — InvalidToken (token scaduto) nell'envelope (E-3)
 6) test_codice_dell_istanza_vince — `code` della permission (detail.code E_*) nell'envelope, col suo messaggio (E-5)
 7) test_codice_istanza_non_e_vale_la_classe — detail.code non E_* (quello di DRF) → mappa per classe
 8) test_permission_reparto_senza_profilo_porta_il_codice — ZeroERPPermission → code della permission (E-5)
"""

from unittest import TestCase
from unittest.mock import patch

from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.core.api.error_responses import drf_exception_handler
from apps.core.api.multi_veste_token_serializer import VesteNonAttivaError
from apps.core.services.error_policies import ErrorPolicyRegistry


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
        mappa classe -> code. PermissionDenied -> E_PERMISSION_DENIED."""
        mock_default.return_value = Response(
            {"detail": "permission"}, status=403
        )
        exc = PermissionDenied()

        response = drf_exception_handler(exc, context={})

        self.assertEqual(response.data["error"]["code"], "E_PERMISSION_DENIED")

    @patch("apps.core.api.error_responses.drf_default_handler")
    def test_envelope_porta_la_ui_action(self, mock_default):
        """⚠️ Fino al 2026-08-07 questo percorso la calcolava e la buttava via,
        mentre `exception_to_error_response` la spediva: lo stesso codice usciva
        con due forme diverse a seconda di CHI l'aveva sollevato.

        Il test esiste perche' il campo oggi **non lo legge nessuno** — il
        frontend non lo consuma ancora — e un contratto che nessuno consuma e'
        precisamente quello che si sfila senza che un rosso lo dica. Il giorno in
        cui il frontend lo leggera', «a volte funziona» sarebbe il modo peggiore
        in cui potrebbe presentarsi."""
        mock_default.return_value = Response({"detail": "permission"}, status=403)

        response = drf_exception_handler(PermissionDenied(), context={})

        errore = response.data["error"]
        self.assertIn("ui_action", errore)
        # Deriva dalla classe di E_PERMISSION_DENIED, non e' scritta qui.
        self.assertEqual(
            errore["ui_action"],
            ErrorPolicyRegistry.resolve("E_PERMISSION_DENIED").ui_action,
        )

    # Scopo: E-3 — `InvalidToken` di SimpleJWT (token scaduto o illeggibile)
    # e' una sottoclasse di `AuthenticationFailed`: col confronto per nome
    # usciva nel formato grezzo di DRF (`{"detail", "code": "token_not_valid"}`).
    @patch("apps.core.api.error_responses.drf_default_handler")
    def test_sottoclasse_prende_il_codice_della_madre(self, mock_default):
        from rest_framework_simplejwt.exceptions import InvalidToken

        mock_default.return_value = Response(
            {"detail": "Token is invalid", "code": "token_not_valid"}, status=401
        )

        response = drf_exception_handler(InvalidToken(), context={})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["error"]["code"], "E_AUTHENTICATION_FAILED")
        self.assertNotIn("detail", response.data)

    # Scopo: E-5 — DRF trasporta il `code` di una permission in
    # `detail.code`: e' il codice dell'istanza, e vince sulla mappa per
    # classe. Messaggio e status vengono dalla SUA policy.
    @patch("apps.core.api.error_responses.drf_default_handler")
    def test_codice_dell_istanza_vince(self, mock_default):
        mock_default.return_value = Response({"detail": "..."}, status=403)
        exc = PermissionDenied(detail="testo runtime", code="E_REPARTO_SENZA_PROFILO")

        response = drf_exception_handler(exc, context={})

        self.assertEqual(response.data["error"]["code"], "E_REPARTO_SENZA_PROFILO")
        self.assertEqual(
            response.data["error"]["message"],
            ErrorPolicyRegistry.resolve("E_REPARTO_SENZA_PROFILO").user_message,
        )

    # Scopo: un `code` che non e' nostro (quello di default di DRF) non
    # sostituisce niente: resta la mappa per classe.
    @patch("apps.core.api.error_responses.drf_default_handler")
    def test_codice_istanza_non_e_vale_la_classe(self, mock_default):
        mock_default.return_value = Response({"detail": "..."}, status=403)
        exc = PermissionDenied(detail="x", code="permission_denied")

        response = drf_exception_handler(exc, context={})

        self.assertEqual(response.data["error"]["code"], "E_PERMISSION_DENIED")

    # Scopo: E-5, il percorso intero dal lato della permission: operatore
    # senza profilo applicabile all'area → la permission porta il codice
    # `E_REPARTO_SENZA_PROFILO`; un diniego qualsiasi lo azzera.
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_permission_reparto_senza_profilo_porta_il_codice(self, mock_resolver):
        from apps.core.api.permissions import ZeroERPPermission
        from apps.core.services.auth_constants import RUOLO_APPLICATIVO_OPERATORE

        perm = ZeroERPPermission()
        mock_resolver.has_profilo_applicabile_per_area.return_value = False
        perm._set_deny_message(object(), RUOLO_APPLICATIVO_OPERATORE, "vendite", {})
        self.assertEqual(perm.code, "E_REPARTO_SENZA_PROFILO")

        mock_resolver.has_profilo_applicabile_per_area.return_value = True
        perm._set_deny_message(object(), RUOLO_APPLICATIVO_OPERATORE, "vendite", {})
        self.assertIsNone(perm.code)
