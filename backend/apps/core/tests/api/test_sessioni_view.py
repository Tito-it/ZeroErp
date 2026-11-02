# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per LogoutView, SessioniAttiveListView,
#        SessioneRevocaView e SessionAuditRepository.list_sessioni_attive.
#        Mock DB, compatibile CI senza database reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) LogoutViewTests.test_logout_success
2) LogoutViewTests.test_logout_no_token
3) LogoutViewTests.test_logout_chiude_sessione
4) LogoutViewTests.test_logout_token_invalido_idempotente
5) LogoutViewTests.test_logout_token_scaduto_registra_logout
5b) LogoutViewTests.test_logout_firma_estranea_non_revoca
5c) LogoutViewTests.test_logout_token_altrui_non_revoca
5d) LogoutViewTests.test_logout_access_token_non_revoca
5e) LogoutViewTests.test_logout_senza_sid_non_revoca
6) SessioniAttiveListViewTests.test_list_sessioni_success
7) SessioniAttiveListViewTests.test_list_sessioni_empty
7b) SessioniAttiveListViewTests.test_list_sessioni_con_ricerca_totale_attive
8) SessioneRevocaViewTests.test_revoca_success
9) SessioneRevocaViewTests.test_revoca_sessione_corrente
10) SessioneRevocaViewTests.test_revoca_sessione_not_found
10b) SessioneRevocaViewTests.test_revoca_gia_revocata_resta_idempotente
11) SessioniRevocaTutteViewTests.test_revoca_tutte_success
12) SessioniRevocaTutteViewTests.test_revoca_tutte_senza_remote
12b) SessioniRevocaTutteViewTests.test_revoca_tutte_sessione_senza_token
13) SessionAuditRepositoryTests.test_list_sessioni_attive
14) SessionAuditRepositoryTests.test_paginata_esclude_la_corrente_nella_sql
15) SessionAuditRepositoryTests.test_paginata_ordina_sulla_whitelist
16) SessionAuditRepositoryTests.test_paginata_ordine_fuori_whitelist_e_rifiutato
"""

import json
from datetime import UTC, datetime
from unittest import TestCase
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from apps.core.services.service_errors import ServiceError

# --------------- helpers ---------------

_LOGOUT_VIEW = "apps.core.api.logout_view"
_SESSIONI_VIEW = "apps.core.api.sessioni_view"
# Il giro sui token vive nel BB `revoca_token` (2026-09-26): i modelli e `jwt`
# si sostituiscono dove li usa lui, non nella view.
_REVOCA_TOKEN = "apps.core.services.revoca_token"
_REPO_PATH = "apps.core.db.session_audit_repository.connection"


def _mock_request(user_id: int = 1, auth: dict | None = None) -> MagicMock:
    """Crea un mock DRF Request con user e auth."""
    request = MagicMock()
    request.user = MagicMock()
    request.user.id = user_id
    request.user.is_authenticated = True
    request.auth = auth
    request.query_params = {}
    request._request = MagicMock()
    request._request.META = {
        "REMOTE_ADDR": "127.0.0.1",
        "HTTP_USER_AGENT": "TestBrowser/1.0",
    }
    return request


# --------------- LogoutView ---------------

# Scopo: un JWT VERO, firmato con la chiave del backend come quelli emessi al
#        login. ⭐ Nessun mock di `jwt`: la view ora verifica la firma, e un
#        decode sostituito da un MagicMock proverebbe il mock, non la verifica.
def _jwt(
    *, user_id: int = 1, sid: str | None = "sid-abc-123",
    tipo: str = "refresh", scaduto: bool = False,
) -> str:
    import time

    from rest_framework_simplejwt.settings import api_settings
    from rest_framework_simplejwt.state import token_backend

    adesso = int(time.time())
    payload = {
        api_settings.TOKEN_TYPE_CLAIM: tipo,
        api_settings.USER_ID_CLAIM: user_id,
        "jti": f"jti-{user_id}-{sid}",
        "iat": adesso - 7200,
        "exp": adesso - 3600 if scaduto else adesso + 3600,
    }
    if sid is not None:
        payload["sid"] = sid
    return token_backend.encode(payload)


class LogoutViewTests(TestCase):

    @staticmethod
    def _post(token: str | None, user_id: int = 1):
        from apps.core.api.logout_view import LogoutView

        from apps.core.api.refresh_cookie import REFRESH_COOKIE_NAME

        # Il refresh arriva nel cookie HttpOnly (brief sicurezza §2).
        request = _mock_request(user_id=user_id)
        request.COOKIES = {} if token is None else {REFRESH_COOKIE_NAME: token}
        return request, LogoutView().post(request)

    # Scopo: Il cookie del refresh esce CANCELLATO dalla risposta (stesso path
    #        con cui e' stato scritto, scadenza nel passato).
    def _assert_cookie_cancellato(self, response) -> None:
        from apps.core.api.refresh_cookie import REFRESH_COOKIE_NAME

        cookie = response.cookies[REFRESH_COOKIE_NAME]
        self.assertEqual(cookie.value, "")
        self.assertEqual(cookie["path"], "/api/v1/")
        self.assertEqual(int(cookie["max-age"]), 0)

    # Scopo: refresh valido → 204, revoca della SESSIONE (tutti i token col suo
    #        sid) ed evento LOGOUT con quel sid.
    @patch(f"{_LOGOUT_VIEW}.session_audit_service")
    @patch(f"{_LOGOUT_VIEW}.blocca_token_sessioni")
    def test_logout_success(self, mock_blocca, mock_audit):
        request, response = self._post(_jwt(sid="sid-abc-123"))

        self.assertEqual(response.status_code, 204)
        self._assert_cookie_cancellato(response)
        mock_blocca.assert_called_once()
        user_id, vale_sid = mock_blocca.call_args[0]
        self.assertEqual(user_id, 1)
        self.assertTrue(vale_sid("sid-abc-123"))
        self.assertFalse(vale_sid("sid-di-un-altra-sessione"))
        mock_audit.record_logout.assert_called_once_with(
            user_id=1, request=request._request, jti="sid-abc-123",
        )

    # Scopo: POST senza cookie di refresh → 400 E_LOGOUT_NO_TOKEN.
    def test_logout_no_token(self):
        with self.assertRaises(ServiceError) as ctx:
            self._post(None)
        self.assertEqual(ctx.exception.code, "E_LOGOUT_NO_TOKEN")

    # Scopo: la sessione chiusa e' quella del token, per l'utente autenticato.
    @patch(f"{_LOGOUT_VIEW}.session_audit_service")
    @patch(f"{_LOGOUT_VIEW}.blocca_token_sessioni")
    def test_logout_chiude_sessione(self, mock_blocca, mock_audit):
        self._post(_jwt(user_id=5, sid="sid-session-xyz"), user_id=5)

        self.assertEqual(mock_blocca.call_args[0][0], 5)
        call_kwargs = mock_audit.record_logout.call_args[1]
        self.assertEqual(call_kwargs["jti"], "sid-session-xyz")
        self.assertEqual(call_kwargs["user_id"], 5)

    # Scopo: stringa malformata → 204 idempotente, nessuna revoca, nessun evento.
    @patch(f"{_LOGOUT_VIEW}.session_audit_service")
    @patch(f"{_LOGOUT_VIEW}.blocca_token_sessioni")
    def test_logout_token_invalido_idempotente(self, mock_blocca, mock_audit):
        _request, response = self._post("invalid-token-string")

        self.assertEqual(response.status_code, 204)
        # Anche senza niente da revocare il browser smette di portarlo.
        self._assert_cookie_cancellato(response)
        mock_blocca.assert_not_called()
        mock_audit.record_logout.assert_not_called()

    # Scopo: refresh SCADUTO ma nostro → la sessione si chiude lo stesso: il
    #        successore emesso da una rotazione puo' essere ancora vivo.
    @patch(f"{_LOGOUT_VIEW}.session_audit_service")
    @patch(f"{_LOGOUT_VIEW}.blocca_token_sessioni")
    def test_logout_token_scaduto_registra_logout(self, mock_blocca, mock_audit):
        request, response = self._post(_jwt(sid="sid-expired-456", scaduto=True))

        self.assertEqual(response.status_code, 204)
        mock_blocca.assert_called_once()
        mock_audit.record_logout.assert_called_once_with(
            user_id=1, request=request._request, jti="sid-expired-456",
        )

    # Scopo: firma non nostra → nessuna revoca. Il sid deciderebbe QUALE
    #        sessione si chiude: da un token non verificato lo sceglierebbe
    #        chiunque.
    @patch(f"{_LOGOUT_VIEW}.session_audit_service")
    @patch(f"{_LOGOUT_VIEW}.blocca_token_sessioni")
    def test_logout_firma_estranea_non_revoca(self, mock_blocca, mock_audit):
        import jwt

        falso = jwt.encode(
            {"token_type": "refresh", "user_id": 1, "sid": "sid-abc-123"},
            "una-chiave-che-non-e-la-nostra-lunga-abbastanza-per-hs256", algorithm="HS256",
        )
        _request, response = self._post(falso)

        self.assertEqual(response.status_code, 204)
        mock_blocca.assert_not_called()
        mock_audit.record_logout.assert_not_called()

    # Scopo: il refresh di UN ALTRO utente → nessuna revoca (guardia anti-scambio).
    @patch(f"{_LOGOUT_VIEW}.session_audit_service")
    @patch(f"{_LOGOUT_VIEW}.blocca_token_sessioni")
    def test_logout_token_altrui_non_revoca(self, mock_blocca, mock_audit):
        _request, response = self._post(_jwt(user_id=99), user_id=1)

        self.assertEqual(response.status_code, 204)
        mock_blocca.assert_not_called()
        mock_audit.record_logout.assert_not_called()

    # Scopo: un ACCESS token al posto del refresh → nessuna revoca.
    @patch(f"{_LOGOUT_VIEW}.session_audit_service")
    @patch(f"{_LOGOUT_VIEW}.blocca_token_sessioni")
    def test_logout_access_token_non_revoca(self, mock_blocca, mock_audit):
        _request, response = self._post(_jwt(tipo="access"))

        self.assertEqual(response.status_code, 204)
        mock_blocca.assert_not_called()

    # Scopo: refresh nostro ma SENZA sid → nessuna revoca, nessun evento: non
    #        c'e' una sessione, e l'autenticazione rifiuta ogni access token
    #        senza sid (E_JWT_SENZA_SID).
    @patch(f"{_LOGOUT_VIEW}.session_audit_service")
    @patch(f"{_LOGOUT_VIEW}.blocca_token_sessioni")
    def test_logout_senza_sid_non_revoca(self, mock_blocca, mock_audit):
        _request, response = self._post(_jwt(sid=None))

        self.assertEqual(response.status_code, 204)
        mock_blocca.assert_not_called()
        mock_audit.record_logout.assert_not_called()


# --------------- SessioniAttiveListView ---------------

class SessioniAttiveListViewTests(TestCase):

    # Scopo: Verifica GET → 200 con envelope paginato; la sessione corrente la
    #        esclude la SQL (`escludi_jti`), non la view dopo la pagina.
    @patch(f"{_SESSIONI_VIEW}.SessionAuditRepository")
    @patch(f"{_SESSIONI_VIEW}.success_response")
    def test_list_sessioni_success(self, mock_resp, MockRepo):
        from apps.core.api.sessioni_view import SessioniAttiveListView

        mock_repo = MagicMock()
        mock_repo.list_sessioni_attive_paginata.return_value = ([
            {"jti": "other-sid", "ultimo_evento": "LOGIN", "ip_address": "10.0.0.2",
             "user_agent": "Chrome", "data_inizio": datetime(2026, 3, 9, 7, 0, tzinfo=UTC),
             "data_ultimo_evento": datetime(2026, 3, 9, 9, 0, tzinfo=UTC)},
        ], 1)
        MockRepo.return_value = mock_repo
        mock_resp.return_value = MagicMock(status_code=200)

        # Il sid e' nel claim "sid" dell'access token
        request = _mock_request(auth={"sid": "current-sid"})

        view = SessioniAttiveListView()
        response = view.get(request)

        self.assertEqual(response.status_code, 200)
        call_args = mock_resp.call_args[0][0]
        self.assertEqual(call_args["count"], 1)
        self.assertEqual(call_args["totale_attive"], 1)
        self.assertEqual(call_args["page"], 1)
        self.assertEqual(call_args["page_size"], 25)
        self.assertEqual(call_args["results"][0]["jti"], "other-sid")
        kwargs = mock_repo.list_sessioni_attive_paginata.call_args.kwargs
        self.assertEqual(kwargs["escludi_jti"], "current-sid")
        self.assertIsNone(kwargs["search"])
        self.assertEqual(kwargs["order_by"], "data_ultimo_evento")
        # ⚠️ Assente = None: il verso lo decide il repository (DESC sulle date).
        self.assertIsNone(kwargs["order_dir"])
        # Senza ricerca il totale delle attive E' il count: nessuna seconda lettura.
        mock_repo.conta_sessioni_attive.assert_not_called()

    # Scopo: Verifica GET con nessuna sessione → 200 con lista vuota.
    @patch(f"{_SESSIONI_VIEW}.SessionAuditRepository")
    @patch(f"{_SESSIONI_VIEW}.success_response")
    def test_list_sessioni_empty(self, mock_resp, MockRepo):
        from apps.core.api.sessioni_view import SessioniAttiveListView

        mock_repo = MagicMock()
        mock_repo.list_sessioni_attive_paginata.return_value = ([], 0)
        MockRepo.return_value = mock_repo
        mock_resp.return_value = MagicMock(status_code=200)

        request = _mock_request(auth={"sid": "current-sid"})

        view = SessioniAttiveListView()
        view.get(request)

        call_args = mock_resp.call_args[0][0]
        self.assertEqual(call_args["count"], 0)
        self.assertEqual(call_args["results"], [])
        self.assertEqual(call_args["totale_attive"], 0)

    # Scopo: ⭐ Con una ricerca `count` conta le TROVATE e `totale_attive` le
    #        sessioni che esistono: il badge e «revoca tutte» parlano del secondo.
    @patch(f"{_SESSIONI_VIEW}.SessionAuditRepository")
    @patch(f"{_SESSIONI_VIEW}.success_response")
    def test_list_sessioni_con_ricerca_totale_attive(self, mock_resp, MockRepo):
        from apps.core.api.sessioni_view import SessioniAttiveListView

        mock_repo = MagicMock()
        mock_repo.list_sessioni_attive_paginata.return_value = ([{"jti": "a"}], 1)
        mock_repo.conta_sessioni_attive.return_value = 3
        MockRepo.return_value = mock_repo
        mock_resp.return_value = MagicMock(status_code=200)

        request = _mock_request(auth={"sid": "current-sid"})
        request.query_params = {
            "search": "firefox", "order_by": "ip_address", "order_dir": "asc",
            "limit": "10", "offset": "10",
        }

        SessioniAttiveListView().get(request)

        call_args = mock_resp.call_args[0][0]
        self.assertEqual(call_args["count"], 1)
        self.assertEqual(call_args["totale_attive"], 3)
        self.assertEqual(call_args["page"], 2)
        kwargs = mock_repo.list_sessioni_attive_paginata.call_args.kwargs
        self.assertEqual(kwargs["search"], "firefox")
        self.assertEqual((kwargs["order_by"], kwargs["order_dir"]), ("ip_address", "asc"))
        self.assertEqual((kwargs["limit"], kwargs["offset"]), (10, 10))
        mock_repo.conta_sessioni_attive.assert_called_once_with(1, escludi_jti="current-sid")


# --------------- SessioneRevocaView ---------------

class SessioneRevocaViewTests(TestCase):

    # Scopo: Verifica POST con sid valido → 204 + blacklist token associati + evento REVOCA.
    @patch(f"{_SESSIONI_VIEW}.session_audit_service")
    @patch(f"{_REVOCA_TOKEN}.BlacklistedToken")
    @patch(f"{_REVOCA_TOKEN}.OutstandingToken")
    @patch(f"{_REVOCA_TOKEN}.jwt")
    def test_revoca_success(self, mock_jwt, MockOutstanding, MockBlacklisted, mock_audit):
        from apps.core.api.sessioni_view import SessioneRevocaView

        # Simula un OutstandingToken con sid corrispondente
        mock_ot = MagicMock()
        mock_ot.token = "encoded-jwt-token"
        MockOutstanding.objects.filter.return_value = [mock_ot]
        mock_jwt.decode.return_value = {"sid": "other-sid"}

        request = _mock_request(auth={"sid": "current-sid"})

        view = SessioneRevocaView()
        response = view.post(request, jti="other-sid")

        self.assertEqual(response.status_code, 204)
        MockOutstanding.objects.filter.assert_called_once_with(user_id=1)
        # ⚠️ `bulk_create` e non `get_or_create` per token: dal 2026-09-04 le
        #    due view di revoca condividono `blocca_token_sessioni`, che fa una
        #    query per i gia' bloccati e una scrittura sola. La copia precedente
        #    faceva una SELECT per token — ~1400 sul database di sviluppo — e
        #    avvolgeva la scrittura nel `try` della decodifica, trasformando un
        #    errore di scrittura in un «sessione non trovata».
        creati = MockBlacklisted.objects.bulk_create.call_args.args[0]
        self.assertEqual(len(creati), 1)
        mock_audit.record_revoca.assert_called_once_with(
            user_id=1,
            request=request._request,
            jti="other-sid",
        )

    # Scopo: ⛔ Revocare una sessione i cui token sono GIA' bloccati resta 204.
    #        E' l'idempotenza del verbo: un doppio click, o un secondo tentativo
    #        su una riga rimasta a video, non deve diventare «sessione non
    #        trovata». Presidia una regressione introdotta e corretta il
    #        2026-09-04 nell'estrazione di `blocca_token_sessioni`, che
    #        contava le SCRITTURE invece dei token corrispondenti.
    @patch(f"{_SESSIONI_VIEW}.session_audit_service")
    @patch(f"{_REVOCA_TOKEN}.BlacklistedToken")
    @patch(f"{_REVOCA_TOKEN}.OutstandingToken")
    @patch(f"{_REVOCA_TOKEN}.jwt")
    def test_revoca_gia_revocata_resta_idempotente(
        self, mock_jwt, MockOutstanding, MockBlacklisted, mock_audit
    ):
        from apps.core.api.sessioni_view import SessioneRevocaView

        mock_ot = MagicMock()
        mock_ot.id = 7
        mock_ot.token = "encoded-jwt-token"
        MockOutstanding.objects.filter.return_value = [mock_ot]
        mock_jwt.decode.return_value = {"sid": "other-sid"}
        # Il token di quella sessione risulta gia' bloccato.
        MockBlacklisted.objects.filter.return_value.values_list.return_value = [7]

        request = _mock_request(auth={"sid": "current-sid"})
        response = SessioneRevocaView().post(request, jti="other-sid")

        self.assertEqual(response.status_code, 204)
        # Niente da scrivere: era gia' bloccato.
        MockBlacklisted.objects.bulk_create.assert_not_called()
        # L'evento si registra comunque: e' la risposta a «revoca questa».
        mock_audit.record_revoca.assert_called_once()

    # Scopo: Verifica POST con sid corrente → 400 E_SESSIONE_REVOCA_CORRENTE.
    def test_revoca_sessione_corrente(self):
        from apps.core.api.sessioni_view import SessioneRevocaView

        request = _mock_request(auth={"sid": "current-sid"})

        view = SessioneRevocaView()
        with self.assertRaises(ServiceError) as ctx:
            view.post(request, jti="current-sid")

        self.assertEqual(ctx.exception.code, "E_SESSIONE_REVOCA_CORRENTE")

    # Scopo: Verifica POST con sid inesistente → 404 E_SESSIONE_NOT_FOUND.
    @patch(f"{_REVOCA_TOKEN}.OutstandingToken")
    @patch(f"{_REVOCA_TOKEN}.jwt")
    def test_revoca_sessione_not_found(self, mock_jwt, MockOutstanding):
        from apps.core.api.sessioni_view import SessioneRevocaView

        # Nessun token con sid corrispondente
        MockOutstanding.objects.filter.return_value = []

        request = _mock_request(auth={"sid": "current-sid"})

        view = SessioneRevocaView()
        with self.assertRaises(ServiceError) as ctx:
            view.post(request, jti="nonexistent-sid")

        self.assertEqual(ctx.exception.code, "E_SESSIONE_NOT_FOUND")


# --------------- SessioniRevocaTutteView ---------------

class SessioniRevocaTutteViewTests(TestCase):

    # Scopo: Verifica POST bulk → l'AUDIT copre le sole sessioni ATTIVE (quelle
    #        che il pannello mostra), la BLACKLIST tutti i token non correnti.
    #
    # ⭐ Il contratto e' cambiato il 2026-09-04, e questi due test dicevano il
    #    contrario: prima si scriveva una riga REVOCA per ogni sid trovato negli
    #    OutstandingToken, cioe' per ogni sessione MAI esistita. Misurato sul
    #    database di sviluppo: 1138 righe di diario e 2,2 secondi per un click
    #    con due sole sessioni a video, e `dbops.sessioni_utente` all'80% di
    #    REVOCA. Il perimetro dell'audit e' ora quello dell'elenco.
    # ⚠️ La blacklist resta LARGA di proposito: il diario racconta, la blacklist
    #    presidia, e i due perimetri non devono coincidere.
    @patch(f"{_SESSIONI_VIEW}.session_audit_service")
    @patch(f"{_SESSIONI_VIEW}.SessionAuditRepository")
    @patch(f"{_REVOCA_TOKEN}.BlacklistedToken")
    @patch(f"{_REVOCA_TOKEN}.OutstandingToken")
    @patch(f"{_REVOCA_TOKEN}.jwt")
    def test_revoca_tutte_success(
        self, mock_jwt, MockOutstanding, MockBlacklisted, MockRepo, mock_audit
    ):
        from apps.core.api.sessioni_view import SessioniRevocaTutteView

        current = MagicMock(token="jwt-current")
        other_1 = MagicMock(token="jwt-other-1")
        other_2 = MagicMock(token="jwt-other-2")
        other_2_refresh = MagicMock(token="jwt-other-2-refresh")
        MockOutstanding.objects.filter.return_value = [
            current, other_1, other_2, other_2_refresh,
        ]
        mock_jwt.decode.side_effect = [
            {"sid": "current-sid"},
            {"sid": "other-sid-1"},
            {"sid": "other-sid-2"},
            {"sid": "other-sid-2"},
        ]
        # L'elenco che il pannello mostra: due remote + la corrente.
        MockRepo.return_value.list_sessioni_attive.return_value = [
            {"jti": "current-sid"},
            {"jti": "other-sid-1"},
            {"jti": "other-sid-2"},
        ]

        request = _mock_request(auth={"sid": "current-sid"})

        view = SessioniRevocaTutteView()
        response = view.post(request)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        # Due SESSIONI revocate — non i sid storici.
        self.assertEqual(payload["data"]["revoked"], 2)
        MockOutstanding.objects.filter.assert_called_once_with(user_id=1)
        # I tre token non correnti bloccati in una scrittura sola.
        self.assertEqual(MockBlacklisted.objects.bulk_create.call_count, 1)
        creati = MockBlacklisted.objects.bulk_create.call_args.args[0]
        self.assertEqual(len(creati), 3)
        self.assertEqual(mock_audit.record_revoca.call_count, 2)
        revoked_sids = {
            call.kwargs["jti"]
            for call in mock_audit.record_revoca.call_args_list
        }
        self.assertEqual(revoked_sids, {"other-sid-1", "other-sid-2"})

    # Scopo: Verifica POST bulk senza sessioni remote → 200 con revoked=0 e
    #        nessuna riga di diario.
    @patch(f"{_SESSIONI_VIEW}.session_audit_service")
    @patch(f"{_SESSIONI_VIEW}.SessionAuditRepository")
    @patch(f"{_REVOCA_TOKEN}.BlacklistedToken")
    @patch(f"{_REVOCA_TOKEN}.OutstandingToken")
    @patch(f"{_REVOCA_TOKEN}.jwt")
    def test_revoca_tutte_senza_remote(
        self, mock_jwt, MockOutstanding, MockBlacklisted, MockRepo, mock_audit
    ):
        from apps.core.api.sessioni_view import SessioniRevocaTutteView

        current = MagicMock(token="jwt-current")
        MockOutstanding.objects.filter.return_value = [current]
        mock_jwt.decode.return_value = {"sid": "current-sid"}
        MockRepo.return_value.list_sessioni_attive.return_value = [{"jti": "current-sid"}]

        request = _mock_request(auth={"sid": "current-sid"})

        view = SessioniRevocaTutteView()
        response = view.post(request)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertEqual(payload["data"]["revoked"], 0)
        MockBlacklisted.objects.bulk_create.assert_not_called()
        mock_audit.record_revoca.assert_not_called()

    # Scopo: ⛔ Una sessione ATTIVA i cui token sono spariti (scaduti e ripuliti)
    #        va comunque tolta dall'elenco: e' proprio il caso in cui l'operatore
    #        preme «revoca tutte», niente si blocca, e la riga resterebbe li' a
    #        dire che la sessione e' viva.
    @patch(f"{_SESSIONI_VIEW}.session_audit_service")
    @patch(f"{_SESSIONI_VIEW}.SessionAuditRepository")
    @patch(f"{_REVOCA_TOKEN}.BlacklistedToken")
    @patch(f"{_REVOCA_TOKEN}.OutstandingToken")
    @patch(f"{_REVOCA_TOKEN}.jwt")
    def test_revoca_tutte_sessione_senza_token(
        self, mock_jwt, MockOutstanding, MockBlacklisted, MockRepo, mock_audit
    ):
        from apps.core.api.sessioni_view import SessioniRevocaTutteView

        MockOutstanding.objects.filter.return_value = []
        MockRepo.return_value.list_sessioni_attive.return_value = [
            {"jti": "current-sid"},
            {"jti": "orfana-sid"},
        ]

        request = _mock_request(auth={"sid": "current-sid"})
        response = SessioniRevocaTutteView().post(request)

        self.assertEqual(json.loads(response.content)["data"]["revoked"], 1)
        MockBlacklisted.objects.bulk_create.assert_not_called()
        self.assertEqual(mock_audit.record_revoca.call_count, 1)
        self.assertEqual(
            mock_audit.record_revoca.call_args.kwargs["jti"], "orfana-sid"
        )


# --------------- SessionAuditRepository ---------------

class SessionAuditRepositoryTests(TestCase):

    # Scopo: Verifica che list_sessioni_attive restituisce lista di dict dalla query CTE.
    @patch(_REPO_PATH)
    def test_list_sessioni_attive(self, mock_conn):
        from apps.core.db.session_audit_repository import SessionAuditRepository

        mock_cursor = MagicMock()
        # Colonne come quelle di psycopg (`.name`): le legge `row_to_dict`/`rows_to_list`.
        mock_cursor.description = [
            SimpleNamespace(name=c) for c in (
                "jti",
                "ultimo_evento",
                "ip_address",
                "user_agent",
                "data_inizio",
                "data_ultimo_evento",
            )
        ]
        mock_cursor.fetchall.return_value = [
            ("sid-1", "LOGIN", "10.0.0.1", "Firefox/100",
             datetime(2026, 3, 9, 8, 0, tzinfo=UTC), datetime(2026, 3, 9, 8, 0, tzinfo=UTC)),
            ("sid-2", "REFRESH", "10.0.0.2", "Chrome/120",
             datetime(2026, 3, 9, 7, 0, tzinfo=UTC), datetime(2026, 3, 9, 9, 0, tzinfo=UTC)),
        ]
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        repo = SessionAuditRepository()
        result = repo.list_sessioni_attive(auth_user_id=1)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["jti"], "sid-1")
        self.assertEqual(result[0]["ultimo_evento"], "LOGIN")
        self.assertEqual(result[0]["ip_address"], "10.0.0.1")
        self.assertEqual(result[1]["jti"], "sid-2")
        self.assertEqual(result[1]["ultimo_evento"], "REFRESH")
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        self.assertEqual(call_args[1], [1, 1])

    # Scopo: ⛔ La sessione corrente si toglie nella SQL (`IS DISTINCT FROM`),
    #        cosi' `COUNT(*) OVER ()` conta giusto; parametri nell'ordine della
    #        CTE (utente due volte), poi il sid, poi LIMIT/OFFSET.
    @patch("apps.core.db.session_audit_repository.fetch_paged_with_total")
    def test_paginata_esclude_la_corrente_nella_sql(self, mock_fetch):
        from apps.core.db.session_audit_repository import SessionAuditRepository

        mock_fetch.return_value = ([], 0)
        SessionAuditRepository().list_sessioni_attive_paginata(
            7, escludi_jti="sid-corrente", limit=25, offset=50,
        )

        sql, params = mock_fetch.call_args.args
        self.assertIn("r.jti IS DISTINCT FROM %s", sql)
        self.assertIn("COUNT(*) OVER () AS total_count", sql)
        self.assertEqual(params, [7, 7, "sid-corrente", 25, 50])
        # Il conteggio di ripiego ha lo stesso FROM/WHERE, senza pagina.
        kwargs = mock_fetch.call_args.kwargs
        self.assertIn("r.jti IS DISTINCT FROM %s", kwargs["fallback_count_sql"])
        self.assertEqual(kwargs["fallback_params"], [7, 7, "sid-corrente"])
        self.assertEqual(kwargs["offset"], 50)
        # Default: l'ultimo evento dal piu' recente, spareggio sul sid.
        self.assertIn("ORDER BY r.data_insert DESC NULLS LAST, r.jti DESC", sql)

    # Scopo: le chiavi della whitelist sono i `campo_sorgente`; una data senza
    #        verso ordina DESC (`colonne_desc`).
    @patch("apps.core.db.session_audit_repository.fetch_paged_with_total")
    def test_paginata_ordina_sulla_whitelist(self, mock_fetch):
        from apps.core.db.session_audit_repository import SessionAuditRepository

        mock_fetch.return_value = ([], 0)
        repo = SessionAuditRepository()
        repo.list_sessioni_attive_paginata(1, escludi_jti=None, order_by="ip_address", order_dir="asc")
        self.assertIn("ORDER BY r.ip_address ASC NULLS FIRST, r.jti ASC", mock_fetch.call_args.args[0])
        repo.list_sessioni_attive_paginata(1, escludi_jti=None, order_by="data_inizio")
        self.assertIn("ORDER BY pl.data_inizio DESC NULLS LAST, r.jti DESC", mock_fetch.call_args.args[0])

    # Scopo: un `order_by` fuori whitelist e' un 400 (`order_by_invalid`), mai
    #         SQL grezzo e mai il default in silenzio (dal 2026-10-20).
    @patch("apps.core.db.session_audit_repository.fetch_paged_with_total")
    def test_paginata_ordine_fuori_whitelist_e_rifiutato(self, mock_fetch):
        from apps.core.db.session_audit_repository import SessionAuditRepository

        mock_fetch.return_value = ([], 0)
        with self.assertRaisesRegex(ValueError, "order_by_invalid"):
            SessionAuditRepository().list_sessioni_attive_paginata(
                1, escludi_jti=None, order_by="user_agent; DROP TABLE x", order_dir="asc",
            )
        mock_fetch.assert_not_called()
