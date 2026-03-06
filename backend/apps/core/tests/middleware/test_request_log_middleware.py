# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per RequestLogMiddleware — mock DB,
#        compatibile CI senza database reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) RequestLogMiddlewareTests.test_api_request_logged
2) RequestLogMiddlewareTests.test_non_api_request_not_logged
3) RequestLogMiddlewareTests.test_excluded_path_not_logged
4) RequestLogMiddlewareTests.test_disabled_via_setting
5) RequestLogMiddlewareTests.test_duration_calculated
6) RequestLogMiddlewareTests.test_anonymous_user_logged_with_null_user
7) RequestLogMiddlewareTests.test_error_code_extracted_from_response
8) RequestLogMiddlewareTests.test_db_error_silent
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.middleware.request_log_middleware import RequestLogMiddleware, _extract_error_code

_CONNECTION = "apps.core.middleware.request_log_middleware.connection"


def _mock_request(
    path: str = "/api/v1/test/",
    method: str = "GET",
    user_id: int | None = 1,
    authenticated: bool = True,
    ip: str = "192.168.1.1",
    user_agent: str = "TestBrowser/1.0",
    request_id: str | None = "req-abc-123",
) -> MagicMock:
    """Scopo: Crea un mock HttpRequest con attributi realistici."""
    request = MagicMock(spec=[])
    request.path = path
    request.method = method
    request.META = {
        "REMOTE_ADDR": ip,
        "HTTP_USER_AGENT": user_agent,
        "QUERY_STRING": "page=1",
    }
    request.request_id = request_id
    if authenticated and user_id is not None:
        user = MagicMock()
        user.id = user_id
        user.is_authenticated = True
        user.__str__ = MagicMock(return_value="testuser")
        request.user = user
    else:
        user = MagicMock()
        user.is_authenticated = False
        request.user = user
    return request


def _mock_response(status_code: int = 200, body: bytes = b"{}") -> MagicMock:
    """Scopo: Crea un mock HttpResponse."""
    response = MagicMock()
    response.status_code = status_code
    response.content = body
    return response


class RequestLogMiddlewareTests(TestCase):

    def setUp(self) -> None:
        self.middleware = RequestLogMiddleware(get_response=MagicMock())

    # Scopo: Verifica che una request API venga loggata con INSERT.
    @patch(_CONNECTION)
    def test_api_request_logged(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        request = _mock_request()
        response = _mock_response()

        self.middleware.process_request(request)
        self.assertTrue(hasattr(request, "_request_log_start"))

        self.middleware.process_response(request, response)
        mock_cursor.execute.assert_called_once()
        sql = mock_cursor.execute.call_args[0][0]
        self.assertIn("INSERT INTO dbops.request_log", sql)

    # Scopo: Verifica che request non-API non venga loggata.
    @patch(_CONNECTION)
    def test_non_api_request_not_logged(self, mock_conn):
        request = _mock_request(path="/admin/")
        response = _mock_response()

        self.middleware.process_request(request)
        self.assertFalse(hasattr(request, "_request_log_start"))

        result = self.middleware.process_response(request, response)
        mock_conn.cursor.assert_not_called()
        self.assertEqual(result, response)

    # Scopo: Verifica che path esclusi (es. /api/docs/) non vengano loggati.
    @patch(_CONNECTION)
    def test_excluded_path_not_logged(self, mock_conn):
        request = _mock_request(path="/api/docs/")
        response = _mock_response()

        self.middleware.process_request(request)
        self.assertFalse(hasattr(request, "_request_log_start"))

    # Scopo: Verifica che il middleware non loggi quando disabilitato via settings.
    @patch("apps.core.middleware.request_log_middleware.settings")
    @patch(_CONNECTION)
    def test_disabled_via_setting(self, mock_conn, mock_settings):
        mock_settings.REQUEST_LOG_ENABLED = False
        request = _mock_request()
        response = _mock_response()

        self.middleware.process_request(request)
        self.assertFalse(hasattr(request, "_request_log_start"))

    # Scopo: Verifica che la durata venga calcolata e passata come intero.
    @patch(_CONNECTION)
    def test_duration_calculated(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        request = _mock_request()
        response = _mock_response()

        self.middleware.process_request(request)
        self.middleware.process_response(request, response)

        params = mock_cursor.execute.call_args[0][1]
        # duration_ms e' il parametro all'indice 7
        duration_ms = params[7]
        self.assertIsInstance(duration_ms, int)
        self.assertGreaterEqual(duration_ms, 0)

    # Scopo: Verifica che utente anonimo venga loggato con auth_user_id NULL.
    @patch(_CONNECTION)
    def test_anonymous_user_logged_with_null_user(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        request = _mock_request(authenticated=False, user_id=None)
        response = _mock_response()

        self.middleware.process_request(request)
        self.middleware.process_response(request, response)

        params = mock_cursor.execute.call_args[0][1]
        # auth_user_id e' il primo parametro
        self.assertIsNone(params[0])
        # username e' il secondo parametro
        self.assertIsNone(params[1])

    # Scopo: Verifica estrazione error_code dalla response JSON.
    def test_error_code_extracted_from_response(self):
        import json
        response = _mock_response(
            status_code=400,
            body=json.dumps({"error": {"code": "E_INVALID_ID", "message": "test"}}).encode(),
        )
        code = _extract_error_code(response)
        self.assertEqual(code, "E_INVALID_ID")

    # Scopo: Verifica che errori DB vengano gestiti silenziosamente.
    @patch(_CONNECTION)
    def test_db_error_silent(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = RuntimeError("DB down")
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        request = _mock_request()
        response = _mock_response()

        self.middleware.process_request(request)
        # Non deve sollevare eccezioni
        result = self.middleware.process_response(request, response)
        self.assertEqual(result, response)
