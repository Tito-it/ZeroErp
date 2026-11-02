# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari UserLanguageMiddleware — parsing Accept-Language,
#        propagazione GUC myapp.user_language, reset simmetrico.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_resolve_language_empty_header_returns_default
2) test_resolve_language_missing_header_returns_default
3) test_resolve_language_unsupported_returns_default
4) test_resolve_language_simple_supported
5) test_resolve_language_with_region_normalized
6) test_resolve_language_picks_first_supported_from_list
7) test_resolve_language_ignores_q_values
8) test_process_request_skipped_on_non_api_path
9) test_process_request_sets_guc_on_api_path
10) test_process_request_db_error_does_not_raise
11) test_process_response_resets_guc_when_flag_set
12) test_process_response_no_flag_no_reset
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.db import DatabaseError

from apps.core.middleware.user_language_middleware import (
    DEFAULT_LANGUAGE,
    GUC_NAME,
    UserLanguageMiddleware,
)

_CONN = "apps.core.middleware.user_language_middleware.connection"


def _mock_request(
    path: str = "/api/v1/test/",
    accept_language: str | None = None,
) -> MagicMock:
    """Scopo: Mock request con path + META.HTTP_ACCEPT_LANGUAGE controllati."""
    request = MagicMock(spec=[])
    request.path = path
    meta: dict[str, str] = {}
    if accept_language is not None:
        meta["HTTP_ACCEPT_LANGUAGE"] = accept_language
    request.META = meta
    return request


class ResolveLanguageTests(TestCase):
    """Parsing Accept-Language senza dipendenza DB."""

    # Scopo: Header vuoto deve ritornare la lingua di default.
    def test_resolve_language_empty_header_returns_default(self):
        req = _mock_request(accept_language="")
        self.assertEqual(
            UserLanguageMiddleware._resolve_language(req), DEFAULT_LANGUAGE
        )

    # Scopo: Header assente deve ritornare la lingua di default.
    def test_resolve_language_missing_header_returns_default(self):
        req = _mock_request(accept_language=None)
        self.assertEqual(
            UserLanguageMiddleware._resolve_language(req), DEFAULT_LANGUAGE
        )

    # Scopo: Lingua non in whitelist deve cadere sul default.
    def test_resolve_language_unsupported_returns_default(self):
        req = _mock_request(accept_language="fr-FR,fr;q=0.9")
        self.assertEqual(
            UserLanguageMiddleware._resolve_language(req), DEFAULT_LANGUAGE
        )

    # Scopo: Codice ISO-2 diretto supportato viene restituito tale quale.
    def test_resolve_language_simple_supported(self):
        req = _mock_request(accept_language="en")
        self.assertEqual(
            UserLanguageMiddleware._resolve_language(req), "en"
        )

    # Scopo: "en-US" deve normalizzarsi a "en".
    def test_resolve_language_with_region_normalized(self):
        req = _mock_request(accept_language="en-US")
        self.assertEqual(
            UserLanguageMiddleware._resolve_language(req), "en"
        )

    # Scopo: In una lista, il primo codice base supportato vince.
    def test_resolve_language_picks_first_supported_from_list(self):
        req = _mock_request(accept_language="fr-FR,en-US;q=0.9,it;q=0.8")
        self.assertEqual(
            UserLanguageMiddleware._resolve_language(req), "en"
        )

    # Scopo: I q-values nel token non devono confondere il parsing.
    def test_resolve_language_ignores_q_values(self):
        req = _mock_request(accept_language="it-IT;q=1.0")
        self.assertEqual(
            UserLanguageMiddleware._resolve_language(req), "it"
        )


class ProcessRequestTests(TestCase):
    """Propagazione GUC lato process_request."""

    def setUp(self) -> None:
        self.middleware = UserLanguageMiddleware(get_response=MagicMock())

    # Scopo: Path non-API non deve toccare il DB.
    @patch(_CONN)
    def test_process_request_skipped_on_non_api_path(self, mock_conn):
        req = _mock_request(path="/admin/", accept_language="en")
        result = self.middleware.process_request(req)
        self.assertIsNone(result)
        mock_conn.cursor.assert_not_called()
        self.assertFalse(getattr(req, "_zeroerp_user_language_set", False))

    # Scopo: Path API deve chiamare set_config con lingua risolta e marcare il flag.
    @patch(_CONN)
    def test_process_request_sets_guc_on_api_path(self, mock_conn):
        cursor_ctx = mock_conn.cursor.return_value
        cursor = cursor_ctx.__enter__.return_value
        req = _mock_request(
            path="/api/v1/vendite/lotti/", accept_language="en-US"
        )
        self.middleware.process_request(req)
        cursor.execute.assert_called_once_with(
            "SELECT set_config(%s, %s, false)",
            [GUC_NAME, "en"],
        )
        self.assertTrue(req._zeroerp_user_language_set)

    # Scopo: DatabaseError durante set_config non deve propagarsi.
    @patch(_CONN)
    def test_process_request_db_error_does_not_raise(self, mock_conn):
        mock_conn.cursor.side_effect = DatabaseError("boom")
        req = _mock_request(path="/api/v1/x/", accept_language="en")
        # Non deve sollevare
        result = self.middleware.process_request(req)
        self.assertIsNone(result)
        # Il flag NON deve essere impostato (reset non serve, set fallito)
        self.assertFalse(getattr(req, "_zeroerp_user_language_set", False))


class ProcessResponseTests(TestCase):
    """Reset simmetrico lato process_response."""

    def setUp(self) -> None:
        self.middleware = UserLanguageMiddleware(get_response=MagicMock())

    # Scopo: Con flag attivo, deve chiamare set_config con stringa vuota.
    @patch(_CONN)
    def test_process_response_resets_guc_when_flag_set(self, mock_conn):
        cursor_ctx = mock_conn.cursor.return_value
        cursor = cursor_ctx.__enter__.return_value
        req = _mock_request(path="/api/v1/x/")
        req._zeroerp_user_language_set = True
        response = MagicMock()
        result = self.middleware.process_response(req, response)
        cursor.execute.assert_called_once_with(
            "SELECT set_config(%s, '', false)",
            [GUC_NAME],
        )
        self.assertIs(result, response)

    # Scopo: Senza flag, nessun touch al DB.
    @patch(_CONN)
    def test_process_response_no_flag_no_reset(self, mock_conn):
        req = _mock_request(path="/api/v1/x/")
        response = MagicMock()
        result = self.middleware.process_response(req, response)
        mock_conn.cursor.assert_not_called()
        self.assertIs(result, response)
