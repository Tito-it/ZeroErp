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
9) RequestLogMiddlewareTests.test_emittente_attivo_id_letto_dalla_sessione (BE-8)
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.middleware.request_log_middleware import RequestLogMiddleware, _extract_error_code

_CONNECTION = "apps.core.middleware.request_log_middleware.connection"
_GET_REQ_ID = "apps.core.middleware.request_log_middleware.get_request_id"
_GET_IP = "apps.core.middleware.request_log_middleware.get_client_ip"
_GET_UA = "apps.core.middleware.request_log_middleware.get_user_agent"


def _mock_request(
    path: str = "/api/v1/test/",
    method: str = "GET",
    user_id: int | None = 1,
    authenticated: bool = True,
) -> MagicMock:
    """Scopo: Crea un mock HttpRequest con attributi realistici."""
    request = MagicMock(spec=[])
    request.path = path
    request.method = method
    request.META = {
        "REMOTE_ADDR": "192.168.1.1",
        "HTTP_USER_AGENT": "TestBrowser/1.0",
        "QUERY_STRING": "page=1",
    }
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
        # Forza abilitazione: il middleware deve essere attivo per i suoi test,
        # anche se CI usa DJANGO_REQUEST_LOG_ENABLED=0.
        patcher = patch(
            "apps.core.middleware.request_log_middleware.settings"
        )
        self._mock_settings = patcher.start()
        self._mock_settings.REQUEST_LOG_ENABLED = True
        self.addCleanup(patcher.stop)

    # Scopo: Verifica che una request API venga loggata con INSERT.
    @patch(_GET_UA, return_value="TestBrowser/1.0")
    @patch(_GET_IP, return_value="192.168.1.1")
    @patch(_GET_REQ_ID, return_value="req-abc-123")
    @patch(_CONNECTION)
    def test_api_request_logged(self, mock_conn, _rid, _ip, _ua):
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

    # Scopo: ⭐ `emittente_attivo_id` SI SCRIVE, e si legge dalla SESSIONE.
    #
    #        Era una delle due colonne morte di `dbops.request_log` — 0 righe
    #        valorizzate su 354.595 — ed e' la consegna BE-8. Il valore non
    #        passa dal Python: la `INSERT` lo prende dalla GUC
    #        `app.current_emittente_id`, la stessa che le policy RLS leggono
    #        per decidere cosa l'utente vede.
    #
    # ⚠️ Il test guarda l'SQL e non un parametro, ed e' il punto: se qualcuno
    #    "semplificasse" passando il valore come `%s` letto dal JWT, si
    #    perderebbe la verifica che l'autenticazione ha gia' fatto (che
    #    l'emittente esista e sia attivo) e il log potrebbe riportare un
    #    emittente diverso da quello che la richiesta ha davvero usato.
    # ⛔ E si presidia anche l'ASSENZA di `tx_id`: la colonna e' stata TOLTA a
    #    DB il 2026-08-24 (0 valorizzate su 355.702), perche' da qui non si
    #    poteva collegare — la riga si scrive quando la transazione di lavoro ha
    #    gia' chiuso. Nominarla adesso farebbe fallire l'INSERT: l'asserzione
    #    non e' piu' una preferenza di disegno, e' un presidio sullo schema.
    @patch(_GET_UA, return_value="TestBrowser/1.0")
    @patch(_GET_IP, return_value="192.168.1.1")
    @patch(_GET_REQ_ID, return_value="550e8400-e29b-41d4-a716-446655440000")
    @patch(_CONNECTION)
    def test_emittente_attivo_id_letto_dalla_sessione(self, mock_conn, _rid, _ip, _ua):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        request = _mock_request()
        self.middleware.process_request(request)
        self.middleware.process_response(request, _mock_response())

        sql, params = mock_cursor.execute.call_args[0]
        self.assertIn("emittente_attivo_id", sql)
        self.assertIn("current_setting('app.current_emittente_id', true)", sql)
        # La colonna non viaggia fra i parametri: il valore lo prende il DB.
        self.assertEqual(len(params), 12)
        self.assertNotIn("tx_id", sql)

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

        self.middleware.process_request(request)
        self.assertFalse(hasattr(request, "_request_log_start"))

    # Scopo: Verifica che il middleware non loggi quando disabilitato via settings.
    @patch(_CONNECTION)
    def test_disabled_via_setting(self, mock_conn):
        self._mock_settings.REQUEST_LOG_ENABLED = False
        request = _mock_request()

        self.middleware.process_request(request)
        self.assertFalse(hasattr(request, "_request_log_start"))

    # Scopo: Verifica che la durata venga calcolata e passata come intero.
    @patch(_GET_UA, return_value="TestBrowser/1.0")
    @patch(_GET_IP, return_value="192.168.1.1")
    @patch(_GET_REQ_ID, return_value="req-abc-123")
    @patch(_CONNECTION)
    def test_duration_calculated(self, mock_conn, _rid, _ip, _ua):
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
    @patch(_GET_UA, return_value=None)
    @patch(_GET_IP, return_value="192.168.1.1")
    @patch(_GET_REQ_ID, return_value=None)
    @patch(_CONNECTION)
    def test_anonymous_user_logged_with_null_user(self, mock_conn, _rid, _ip, _ua):
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
    @patch(_GET_UA, return_value="TestBrowser/1.0")
    @patch(_GET_IP, return_value="192.168.1.1")
    @patch(_GET_REQ_ID, return_value=None)
    @patch(_CONNECTION)
    def test_db_error_silent(self, mock_conn, _rid, _ip, _ua):
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
