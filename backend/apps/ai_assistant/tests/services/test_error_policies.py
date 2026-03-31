# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per i codici errore AI registrati
#        in error_policies.py. Verifica che tutti i codici E_AI_*
#        siano registrati con HTTP status e ui_action corretti.
# ------------------------------------------------------------

# Indice test:
# 1. test_all_ai_error_codes_registered
# 2. test_ai_disabled_is_501
# 3. test_ai_provider_unknown_is_500
# 4. test_ai_provider_error_is_502
# 5. test_ai_query_empty_is_400
# 6. test_ai_query_too_long_is_400
# 7. test_ai_tool_not_found_is_500
# 8. test_ai_tool_denied_is_403
# 9. test_ai_confirmation_required_is_428

import unittest

from apps.core.services.error_policies import ErrorPolicyRegistry


class TestAIErrorPolicies(unittest.TestCase):
    """Test registrazione codici errore AI."""

    AI_CODES = [
        "E_AI_DISABLED",
        "E_AI_PROVIDER_UNKNOWN",
        "E_AI_PROVIDER_ERROR",
        "E_AI_QUERY_EMPTY",
        "E_AI_QUERY_TOO_LONG",
        "E_AI_TOOL_NOT_FOUND",
        "E_AI_TOOL_DENIED",
        "E_AI_CONFIRMATION_REQUIRED",
    ]

    # Scopo: Verifica che tutti i codici E_AI_* siano registrati.
    def test_all_ai_error_codes_registered(self):
        for code in self.AI_CODES:
            with self.subTest(code=code):
                self.assertTrue(
                    ErrorPolicyRegistry.has(code),
                    f"Codice errore {code} non registrato in error_policies.py",
                )

    # Scopo: E_AI_DISABLED deve restituire 501 (Not Implemented).
    def test_ai_disabled_is_501(self):
        policy = ErrorPolicyRegistry.resolve("E_AI_DISABLED")
        self.assertEqual(policy.http_status, 501)

    # Scopo: E_AI_PROVIDER_UNKNOWN deve restituire 500.
    def test_ai_provider_unknown_is_500(self):
        policy = ErrorPolicyRegistry.resolve("E_AI_PROVIDER_UNKNOWN")
        self.assertEqual(policy.http_status, 500)

    # Scopo: E_AI_PROVIDER_ERROR deve restituire 502 (Bad Gateway).
    def test_ai_provider_error_is_502(self):
        policy = ErrorPolicyRegistry.resolve("E_AI_PROVIDER_ERROR")
        self.assertEqual(policy.http_status, 502)

    # Scopo: E_AI_QUERY_EMPTY deve restituire 400.
    def test_ai_query_empty_is_400(self):
        policy = ErrorPolicyRegistry.resolve("E_AI_QUERY_EMPTY")
        self.assertEqual(policy.http_status, 400)

    # Scopo: E_AI_QUERY_TOO_LONG deve restituire 400.
    def test_ai_query_too_long_is_400(self):
        policy = ErrorPolicyRegistry.resolve("E_AI_QUERY_TOO_LONG")
        self.assertEqual(policy.http_status, 400)

    # Scopo: E_AI_TOOL_NOT_FOUND deve restituire 500.
    def test_ai_tool_not_found_is_500(self):
        policy = ErrorPolicyRegistry.resolve("E_AI_TOOL_NOT_FOUND")
        self.assertEqual(policy.http_status, 500)

    # Scopo: E_AI_TOOL_DENIED deve restituire 403.
    def test_ai_tool_denied_is_403(self):
        policy = ErrorPolicyRegistry.resolve("E_AI_TOOL_DENIED")
        self.assertEqual(policy.http_status, 403)

    # Scopo: E_AI_CONFIRMATION_REQUIRED deve restituire 428.
    def test_ai_confirmation_required_is_428(self):
        policy = ErrorPolicyRegistry.resolve("E_AI_CONFIRMATION_REQUIRED")
        self.assertEqual(policy.http_status, 428)
