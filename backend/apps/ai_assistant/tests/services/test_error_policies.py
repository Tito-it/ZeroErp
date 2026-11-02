# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
# 9. test_conferma_non_e_un_errore_http
#
# ⚠️ Ritirato il 2026-08-06: `test_ai_confirmation_required_is_428`.
#    `E_AI_CONFIRMATION_REQUIRED` non lo solleva nessuno — il flusso di conferma
#    dei tool in scrittura restituisce **200 con `requires_confirmation` nel
#    payload** (`ai_assistant_service`), che e' la scelta giusta: una conferma
#    richiesta non e' un errore HTTP. E il 428 non c'entrava comunque (RFC 6585:
#    «la richiesta deve essere condizionale», `If-Match`, non «l'utente deve
#    confermare»). Codice e test ritirati insieme nell'audit di coerenza degli
#    status: vedi docs/it/dev/api.md §Tassonomia errori.
#    Se un giorno servira' un errore per questo caso, i presidi sui codici lo
#    pretenderanno dichiarato — si riparte da li', con lo status giusto.

import unittest

from apps.core.services.error_policies import ErrorPolicyRegistry
from apps.core.services.error_policies_generated import CODICI_RITIRATI


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

    # Scopo: `E_AI_CONFIRMATION_REQUIRED` non deve tornare. La conferma di un
    #        tool in scrittura si esprime con un 200 e `requires_confirmation`
    #        nel payload, non con un errore HTTP: se qualcuno lo rimettesse in
    #        circolo, questo test lo dice invece di lasciar tornare il 428.
    #
    #        ⚠️ LA DOMANDA E' CAMBIATA IL 2026-08-07, e il test lo aveva detto
    #        diventando rosso. Chiedeva `has(...) is False` — «non e' registrato»
    #        — e andava bene finche' il registro era scritto a mano: bastava non
    #        scriverci il codice. Ora il registro e' GENERATO dal catalogo, e il
    #        catalogo contiene TUTTI i codici, ritirati compresi (devono
    #        continuare a risolvere per il diario). Quindi `has()` oggi risponde
    #        «lo conosco», non «e' buono», ed e' vero anche per un codice morto.
    #
    #        La domanda giusta e' la stessa intenzione, detta piu' forte: **e'
    #        ritirato a catalogo?** Non «l'abbiamo dimenticato», ma «l'abbiamo
    #        deciso», e la decisione sta in un dato invece che in un'assenza.
    def test_conferma_non_e_un_errore_http(self):
        self.assertIn("E_AI_CONFIRMATION_REQUIRED", CODICI_RITIRATI)
