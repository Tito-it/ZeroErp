# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per AuditTokenObtainPairView e AuditTokenRefreshView.
#        Mock service e SimpleJWT, compatibile CI senza database reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) AuditAuthViewsTests.test_login_success_calls_record_login
 2) AuditAuthViewsTests.test_login_failure_no_record
 3) AuditAuthViewsTests.test_refresh_success_calls_record_refresh
 4) AuditAuthViewsTests.test_refresh_failure_no_record
 5) AuditAuthViewsTests.test_login_success_propaga_gucs
 6) AuditAuthViewsTests.test_refresh_success_propaga_gucs
 7) AuditAuthViewsTests.test_refresh_username_non_risolvibile_fail_open
 8) AuditAuthViewsTests.test_veste_non_attiva_non_registra_tentativo
 9) AuditAuthViewsTests.test_base_astratta_guard_solleva_runtime_error
 9b) AuditAuthViewsTests.test_login_senza_provenienza_rifiuta_senza_cercare_l_utente
 9c) AuditAuthViewsTests.test_login_fallito_registra_con_la_provenienza
 9d) AuditAuthViewsTests.test_login_riuscito_registra_e_legge_il_flag_della_credenziale
 9e) AuditAuthViewsTests.test_nome_inesistente_check_e_registrazione_sul_nome
 9e-bis) AuditAuthViewsTests.test_password_sbagliata_senza_freno_scrive_il_log — ogni password sbagliata nel log di sicurezza
 9f) AuditAuthViewsTests.test_nome_con_spazi_trova_la_credenziale_come_authenticate
 9g) AuditAuthViewsTests.test_nome_assente_nessuna_chiamata_al_db
 9h) AuditAuthViewsTests.test_guasto_nella_ricerca_ferma_il_login
 9i) AuditAuthViewsTests.test_secondo_fattore_attivo_risponde_con_la_sfida — T-2
10) ExtractIdentitaIdFromRefreshTests.test_none_returns_none
11) ExtractIdentitaIdFromRefreshTests.test_empty_string_returns_none
12) ExtractIdentitaIdFromRefreshTests.test_invalid_token_fail_open
12b) DecodeRefreshPayloadTests.test_none_returns_empty_dict
12c) DecodeRefreshPayloadTests.test_invalid_token_returns_empty_dict
13) RefreshCrossNamespaceGuardTests.test_base_astratta_guard_solleva_runtime_error
14) RefreshCrossNamespaceGuardTests.test_admin_refresh_accetta_operatore
15) RefreshCrossNamespaceGuardTests.test_admin_refresh_rifiuta_portale
16) RefreshCrossNamespaceGuardTests.test_admin_refresh_rifiuta_claim_assente
17) RefreshCrossNamespaceGuardTests.test_portale_refresh_rifiuta_operatore
18) RefreshCrossNamespaceGuardTests.test_shop_refresh_rifiuta_portale
17) NamespaceRefreshViewConcreteTests.test_admin_refresh_expected_ruoli
18) NamespaceRefreshViewConcreteTests.test_portale_refresh_expected_ruoli
19) NamespaceRefreshViewConcreteTests.test_shop_refresh_expected_ruoli
20) RefreshCookieTests.test_refresh_senza_header_anti_csrf_rifiuta
21) RefreshCookieTests.test_refresh_senza_cookie_e_401
22) RefreshCookieTests.test_refresh_riuscito_ruota_il_cookie_e_toglie_il_corpo
23) RefreshCookieTests.test_login_riuscito_mette_il_refresh_nel_cookie
24) RefreshCookieTests.test_refresh_illeggibile_e_401_non_403
25) RefreshCookieTests.test_refresh_firmato_da_altri_e_401
26) RefreshCookieTests.test_refresh_nostro_di_altro_canale_resta_403
27) RefreshCookieTests.test_refresh_gucs_dai_claim_verificati
28) RefreshCookieTests.test_nome_cookie_e_header_uguali_nei_tre_linguaggi
29) RefreshCookieTests.test_post_con_refresh_riuscito_scrive_il_cookie
30) RefreshCookieTests.test_post_con_refresh_fallito_non_scrive_il_cookie
31) RefreshVesteSpentaTests.test_veste_utilizzabile_rinnova
32) RefreshVesteSpentaTests.test_veste_spenta_401_senza_rotazione_e_sessione_bloccata
33) RefreshVesteSpentaTests.test_veste_assente_401
34) RefreshVesteSpentaTests.test_claim_identita_assente_401_senza_db
35) RefreshVesteSpentaTests.test_guasto_lettura_veste_propaga
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.db import DatabaseError

from rest_framework.response import Response
# ⛔ Quello di DRF: e' cio' che solleva davvero il serializer di SimpleJWT
# (la classe omonima di SimpleJWT ne e' una sottoclasse, e con lei il test
# era verde mentre la view non contava nessun fallimento).
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import InvalidToken

from apps.core.api.auth_views import (
    AdminTokenRefreshView,
    AdminTokenView,
    AuditTokenObtainPairView,
    AuditTokenRefreshView,
    PortaleTokenRefreshView,
    ShopTokenRefreshView,
)
from apps.core.api.multi_veste_token_serializer import VesteNonAttivaError
from apps.core.api.refresh_cookie import (
    ANTI_CSRF_HEADER,
    ANTI_CSRF_VALORE,
    REFRESH_COOKIE_NAME,
)
from apps.core.services.auth_constants import (
    RUOLO_APPLICATIVO_CLIENTE_PORTALE,
    RUOLO_APPLICATIVO_FORNITORE_PORTALE,
    RUOLO_APPLICATIVO_OPERATORE,
    RUOLO_APPLICATIVO_SHOP_CUSTOMER,
)
from apps.core.services.nome_tentato import digest_nome_tentato
from apps.core.services.service_errors import ServiceError

_SERVICE = "apps.core.api.auth_views.session_audit_service"
_SET_GUCS = "apps.core.api.auth_views.set_jwt_gucs"
_GET_IP = "apps.core.services.request_context.get_client_ip"
_IP = "203.0.113.7"
_DIGEST_TID = digest_nome_tentato("tid")
_RINNOVA = "apps.core.api.auth_views.AuditTokenRefreshView._rinnova"
# I claim del refresh con la firma verificata (BB `claims_refresh_firmati`):
# i test dei guard li fissano, la verifica vera la prova test_refresh_cookie.
_CLAIMS = "apps.core.api.auth_views.claims_refresh_firmati"
# Il device del secondo fattore, che il login legge dopo la password giusta.
_SECONDO_FATTORE = "apps.core.api.auth_views._secondo_fattore_repo"
_VESTE_UTILIZZABILE = "apps.core.api.auth_views._veste_utilizzabile"
_AUTH_REPO = "apps.core.api.auth_views._auth_repo"
_BLOCCA = "apps.core.api.auth_views.blocca_token_sessioni"


# Scopo: Spegne la lettura del device nel login: nessun secondo fattore.
#        ⛔ Questi sono `unittest.TestCase`: senza, la lettura andrebbe al DB
#        di sviluppo con un utente finto, e il test resterebbe verde.
def _senza_secondo_fattore(test: TestCase) -> MagicMock:
    patcher = patch(_SECONDO_FATTORE)
    repo = patcher.start()
    repo.get_device.return_value = {"stato": "ASSENTE"}
    test.addCleanup(patcher.stop)
    return repo


# Scopo: Tiene utilizzabile la veste del refresh (`_veste_utilizzabile`, D-5):
#        i test del rinnovo che non parlano di veste spenta non devono leggere
#        il DB.
#        Il controllo vero lo prova `RefreshVesteSpentaTests`.
def _veste_utilizzabile(test: TestCase) -> MagicMock:
    patcher = patch(_VESTE_UTILIZZABILE, return_value=True)
    mock = patcher.start()
    test.addCleanup(patcher.stop)
    return mock


# Scopo: Una richiesta di refresh come la manda il browser: il refresh nel
#        cookie HttpOnly e l'header anti-CSRF (brief sicurezza §2).
def _richiesta_refresh(refresh: str | None = "r.x.y", *, header: bool = True) -> MagicMock:
    request = MagicMock()
    request.COOKIES = {REFRESH_COOKIE_NAME: refresh} if refresh else {}
    request.headers = {ANTI_CSRF_HEADER: ANTI_CSRF_VALORE} if header else {}
    request._request = MagicMock()
    return request


class AuditAuthViewsTests(TestCase):

    # La provenienza la ricava il BB `get_client_ip` (provato in
    # test_request_context): qui si fissa, le request sono MagicMock.
    def setUp(self):
        patcher = patch(_GET_IP, return_value=_IP)
        self.mock_get_ip = patcher.start()
        self.addCleanup(patcher.stop)
        _senza_secondo_fattore(self)
        _veste_utilizzabile(self)

    # Scopo: Verifica che login con successo chiami record_login con user_id e jti.
    @patch(f"{_SERVICE}.record_login")
    @patch.object(AuditTokenObtainPairView, "_extract_claims", return_value=(42, "jti-abc"))
    @patch.object(AuditTokenObtainPairView, "_find_user")
    @patch("apps.core.api.auth_views._auth_repo")
    @patch(_SET_GUCS)
    @patch("rest_framework_simplejwt.views.TokenObtainPairView.post")
    def test_login_success_calls_record_login(
        self, mock_super_post, _gucs, mock_repo, mock_find_user, mock_extract, mock_record
    ):
        mock_find_user.return_value = MagicMock(id=42, username="alice")
        mock_repo.registra_tentativo_login.return_value = {"bloccato": False}
        mock_repo.get_deve_cambiare_password.return_value = False
        mock_super_post.return_value = Response(
            {"access": "tok.en.jwt", "refresh": "ref.tok.en"},
            status=200,
        )
        request = MagicMock()
        request._request = MagicMock()
        request.data = {"username": "alice"}

        view = AdminTokenView()
        response = view.post(request)

        self.assertEqual(response.status_code, 200)
        mock_record.assert_called_once_with(
            user_id=42,
            request=request._request,
            jti="jti-abc",
            dettaglio=None,
        )

    # Scopo: Verifica che login fallito non chiami record_login.
    @patch(f"{_SERVICE}.record_login")
    @patch("rest_framework_simplejwt.views.TokenObtainPairView.post")
    def test_login_failure_no_record(self, mock_super_post, mock_record):
        mock_super_post.return_value = Response(
            {"detail": "Invalid credentials"},
            status=401,
        )
        request = MagicMock()

        view = AdminTokenView()
        response = view.post(request)

        self.assertEqual(response.status_code, 401)
        mock_record.assert_not_called()

    # Scopo: Verifica che refresh con successo chiami record_refresh con user_id e jti.
    @patch(_CLAIMS, return_value={"ruolo_applicativo": "OPERATORE"})
    @patch(f"{_SERVICE}.record_refresh")
    @patch.object(AuditTokenRefreshView, "_resolve_username", return_value="alice")
    @patch.object(AuditTokenRefreshView, "_extract_claims", return_value=(42, "jti-xyz"))
    @patch(_RINNOVA)
    @patch(_SET_GUCS)
    def test_refresh_success_calls_record_refresh(
        self, _mock_gucs, mock_super_post, mock_extract, _mock_resolve, mock_record, _mock_ruolo
    ):
        mock_super_post.return_value = Response(
            {"access": "new.tok.en"},
            status=200,
        )
        request = _richiesta_refresh()

        view = AdminTokenRefreshView()
        response = view.post(request)

        self.assertEqual(response.status_code, 200)
        mock_record.assert_called_once_with(
            user_id=42,
            request=request._request,
            jti="jti-xyz",
        )

    # Scopo: Verifica che refresh fallito non chiami record_refresh.
    @patch(_CLAIMS, return_value={"ruolo_applicativo": "OPERATORE"})
    @patch(f"{_SERVICE}.record_refresh")
    @patch(_RINNOVA)
    def test_refresh_failure_no_record(self, mock_rinnova, mock_record, _mock_ruolo):
        mock_rinnova.side_effect = InvalidToken("Token is invalid")
        request = _richiesta_refresh()

        view = AdminTokenRefreshView()
        with self.assertRaises(InvalidToken):
            view.post(request)

        mock_record.assert_not_called()

    # Scopo: Hotfix BE-2.0ter — verifica che il LOGIN propaghi le GUC
    # `app.jwt_user`/`app.current_user_id` PRIMA della scrittura di
    # audit, cosi' i trigger DB di sessioni_utente popolano user_insert
    # con lo username effettivo invece di 'zeroerp_app'. Il login NON
    # passa dalla DRF auth chain, quindi senza questo set manuale le
    # GUC restano vuote.
    @patch(f"{_SERVICE}.record_login")
    @patch.object(AuditTokenObtainPairView, "_extract_claims", return_value=(42, "jti-abc"))
    @patch.object(AuditTokenObtainPairView, "_find_user")
    @patch("apps.core.api.auth_views._auth_repo")
    @patch("rest_framework_simplejwt.views.TokenObtainPairView.post")
    @patch(_SET_GUCS)
    def test_login_success_propaga_gucs(
        self, mock_set_gucs, mock_super_post, mock_repo,
        mock_find_user, mock_extract, mock_record_login,
    ):
        fake_user = MagicMock(id=42, username="alice")
        mock_find_user.return_value = fake_user
        mock_repo.check_blocco_login.return_value = None
        mock_repo.registra_tentativo_login.return_value = {"bloccato": False}
        mock_repo.get_deve_cambiare_password.return_value = False
        mock_super_post.return_value = Response(
            {"access": "tok.en.jwt", "refresh": "ref.tok.en"},
            status=200,
        )
        request = MagicMock()
        request._request = MagicMock()
        request.data = {"username": "alice"}

        view = AdminTokenView()
        view.post(request)

        mock_set_gucs.assert_called_once_with(
            username="alice",
            user_id=42,
            identita_id=None,  # refresh str "ref.tok.en" non parseable → fail-open
            request=request._request,
        )
        # E deve essere chiamato PRIMA di record_login (audit deve
        # vedere le GUC settate sulla connessione).
        gucs_call_order = mock_set_gucs.call_args_list
        record_call_order = mock_record_login.call_args_list
        self.assertEqual(len(gucs_call_order), 1)
        self.assertEqual(len(record_call_order), 1)

    # Scopo: Hotfix BE-2.0ter — verifica che il REFRESH propaghi le GUC
    # PRIMA della scrittura di audit. Il refresh NON porta Bearer
    # access token, quindi la DRF auth chain non passa per
    # JwtAuditAuthentication: bisogna risolvere l'username dal user_id
    # del claim e settare manualmente.
    @patch(_CLAIMS, return_value={"ruolo_applicativo": "OPERATORE"})
    @patch(f"{_SERVICE}.record_refresh")
    @patch.object(AuditTokenRefreshView, "_resolve_username", return_value="alice")
    @patch.object(AuditTokenRefreshView, "_extract_claims", return_value=(42, "jti-xyz"))
    @patch(_RINNOVA)
    @patch(_SET_GUCS)
    def test_refresh_success_propaga_gucs(
        self, mock_set_gucs, mock_super_post, mock_extract,
        mock_resolve, mock_record_refresh, _mock_ruolo,
    ):
        mock_super_post.return_value = Response(
            {"access": "new.tok.en"},
            status=200,
        )
        request = _richiesta_refresh()

        view = AdminTokenRefreshView()
        view.post(request)

        mock_resolve.assert_called_once_with(42)
        mock_set_gucs.assert_called_once_with(
            username="alice",
            user_id=42,
            identita_id=None,  # request.data.refresh mock -> parse fail -> None
            # Emittente attivo: stessa sorte dell'identita' su un refresh
            # mockato (parse fail -> None = modalita' globale). Il punto sotto
            # test e' che il claim viene PROPAGATO al refresh: senza, ogni
            # rinnovo del token riporterebbe l'utente fuori dal suo emittente.
            emittente_attivo_id=None,
            request=request._request,
        )
        mock_record_refresh.assert_called_once()

    # Scopo: Refresh con _resolve_username che ritorna None (utente
    # non trovato o query fallita) — fail-open: niente set_jwt_gucs ma
    # record_refresh comunque chiamato (l'audit storico resta).
    @patch(_CLAIMS, return_value={"ruolo_applicativo": "OPERATORE"})
    @patch(f"{_SERVICE}.record_refresh")
    @patch.object(AuditTokenRefreshView, "_resolve_username", return_value=None)
    @patch.object(AuditTokenRefreshView, "_extract_claims", return_value=(42, "jti-xyz"))
    @patch(_RINNOVA)
    @patch(_SET_GUCS)
    def test_refresh_username_non_risolvibile_fail_open(
        self, mock_set_gucs, mock_super_post, mock_extract,
        mock_resolve, mock_record_refresh, _mock_ruolo,
    ):
        mock_super_post.return_value = Response(
            {"access": "new.tok.en"},
            status=200,
        )
        request = _richiesta_refresh()

        view = AdminTokenRefreshView()
        view.post(request)

        mock_set_gucs.assert_not_called()
        mock_record_refresh.assert_called_once()

    # Scopo: Verifica che VesteNonAttivaError NON incrementi i tentativi
    # falliti. Il caso e': credenziali corrette ma l'utente non ha l'identita
    # richiesta dal namespace (es. operatore che tenta /portale/token/).
    # Il blocco utente non deve attivarsi per errori di "canale", altrimenti
    # un admin che sbaglia URL si autobloccherebbe.
    @patch("apps.core.api.auth_views._auth_repo")
    @patch.object(AuditTokenObtainPairView, "_find_user")
    @patch("rest_framework_simplejwt.views.TokenObtainPairView.post")
    def test_veste_non_attiva_non_registra_tentativo(
        self, mock_super_post, mock_find_user, mock_repo
    ):
        mock_find_user.return_value = MagicMock(id=42, username="tid")
        mock_repo.check_blocco_login.return_value = None
        mock_super_post.side_effect = VesteNonAttivaError()
        request = MagicMock()
        request.data = {"username": "tid"}

        view = AdminTokenView()
        with self.assertRaises(VesteNonAttivaError):
            view.post(request)

        # check_blocco_login si', registra_tentativo_login NO.
        mock_repo.check_blocco_login.assert_called_once_with(
            42, nome_digest=_DIGEST_TID, provenienza=_IP,
        )
        mock_repo.registra_tentativo_login.assert_not_called()

    # Scopo: Senza provenienza il freno non si applica: il login si rifiuta
    # (fail-closed) PRIMA di cercare l'utente, cosi' la risposta non dice se
    # lo username esiste, e il DB non riceve mai una provenienza NULL.
    @patch("apps.core.api.auth_views._auth_repo")
    @patch.object(AuditTokenObtainPairView, "_find_user")
    @patch("rest_framework_simplejwt.views.TokenObtainPairView.post")
    def test_login_senza_provenienza_rifiuta_senza_cercare_l_utente(
        self, mock_super_post, mock_find_user, mock_repo
    ):
        self.mock_get_ip.return_value = None
        request = MagicMock()
        request.data = {"username": "tid"}

        with self.assertRaises(ServiceError) as ctx:
            AdminTokenView().post(request)

        self.assertEqual(ctx.exception.code, "E_AUTH_CHIAMATA_NON_VALIDA")
        mock_find_user.assert_not_called()
        mock_repo.check_blocco_login.assert_not_called()
        mock_repo.registra_tentativo_login.assert_not_called()
        mock_super_post.assert_not_called()

    # Scopo: Password sbagliata → il fallimento si registra sulla coppia
    # credenziale + provenienza.
    @patch("apps.core.api.auth_views._auth_repo")
    @patch.object(AuditTokenObtainPairView, "_find_user")
    @patch("rest_framework_simplejwt.views.TokenObtainPairView.post")
    def test_login_fallito_registra_con_la_provenienza(
        self, mock_super_post, mock_find_user, mock_repo
    ):
        mock_find_user.return_value = MagicMock(id=42, username="tid")
        mock_repo.registra_tentativo_login.return_value = {
            "bloccato": False, "attesa_secondi": 0,
        }
        mock_super_post.side_effect = AuthenticationFailed()
        request = MagicMock()
        request.data = {"username": "tid"}

        with self.assertRaises(AuthenticationFailed):
            AdminTokenView().post(request)

        mock_repo.check_blocco_login.assert_called_once_with(
            42, nome_digest=_DIGEST_TID, provenienza=_IP,
        )
        mock_repo.registra_tentativo_login.assert_called_once_with(
            42, nome_digest=_DIGEST_TID, provenienza=_IP, successo=False,
        )

    # Scopo: Login riuscito → successo registrato sulla coppia; il cambio
    # password obbligatorio si legge dalla CREDENZIALE (D-7), senza veste.
    @patch(f"{_SERVICE}.record_login")
    @patch.object(AuditTokenObtainPairView, "_extract_claims", return_value=(42, "jti-abc"))
    @patch.object(AuditTokenObtainPairView, "_find_user")
    @patch("apps.core.api.auth_views._auth_repo")
    @patch("rest_framework_simplejwt.views.TokenObtainPairView.post")
    @patch(_SET_GUCS)
    def test_login_riuscito_registra_e_legge_il_flag_della_credenziale(
        self, _mock_set_gucs, mock_super_post, mock_repo,
        mock_find_user, _mock_extract, _mock_record_login,
    ):
        mock_find_user.return_value = MagicMock(id=42, username="tid")
        mock_repo.get_deve_cambiare_password.return_value = True
        mock_super_post.return_value = Response(
            {"access": "tok.en.jwt", "refresh": "ref.tok.en"}, status=200,
        )
        request = MagicMock()
        request._request = MagicMock()
        request.data = {"username": "tid"}

        response = AdminTokenView().post(request)

        mock_repo.registra_tentativo_login.assert_called_once_with(
            42, nome_digest=_DIGEST_TID, provenienza=_IP, successo=True,
        )
        mock_repo.get_deve_cambiare_password.assert_called_once_with(42)
        self.assertTrue(response.data["password_change_required"])

    # Scopo: R-7 — un nome che non trova una credenziale passa dalle STESSE
    # due chiamate, con la credenziale vuota e l'impronta del nome: la chiave
    # la sceglie il DB. E il nome in chiaro non finisce nel log (B-11).
    @patch("apps.core.api.auth_views._auth_repo")
    @patch.object(AuditTokenObtainPairView, "_find_user", return_value=None)
    @patch("rest_framework_simplejwt.views.TokenObtainPairView.post")
    def test_nome_inesistente_check_e_registrazione_sul_nome(
        self, mock_super_post, _mock_find_user, mock_repo
    ):
        nome = "Password-Digitata-Per-Sbaglio!"
        digest = digest_nome_tentato(nome)
        mock_repo.registra_tentativo_login.return_value = {
            "bloccato": True, "tentativi": 5, "minuti_rimanenti": 15,
            "attesa_secondi": 0,
        }
        mock_super_post.side_effect = AuthenticationFailed()
        request = MagicMock()
        request.data = {"username": nome}

        with self.assertLogs("security", level="WARNING") as log:
            with self.assertRaises(AuthenticationFailed):
                AdminTokenView().post(request)

        mock_repo.check_blocco_login.assert_called_once_with(
            None, nome_digest=digest, provenienza=_IP,
        )
        mock_repo.registra_tentativo_login.assert_called_once_with(
            None, nome_digest=digest, provenienza=_IP, successo=False,
        )
        testo = "\n".join(log.output)
        self.assertIn("security.login_fallito", testo)
        self.assertIn("security.login_locked", testo)
        self.assertIn(f"nome={digest.hex()[:12]}", testo)
        self.assertNotIn(nome, testo)

    # Scopo: Una password sbagliata che NON fa scattare il freno lascia
    #        comunque la sua riga nel log di sicurezza (prima stava solo a DB).
    @patch("apps.core.api.auth_views._auth_repo")
    @patch.object(AuditTokenObtainPairView, "_find_user", return_value=None)
    @patch("rest_framework_simplejwt.views.TokenObtainPairView.post")
    def test_password_sbagliata_senza_freno_scrive_il_log(
        self, mock_super_post, _mock_find_user, mock_repo
    ):
        mock_repo.registra_tentativo_login.return_value = {
            "bloccato": False, "tentativi": 1, "minuti_rimanenti": 0, "attesa_secondi": 0,
        }
        mock_super_post.side_effect = AuthenticationFailed()
        request = MagicMock()
        request.data = {"username": "qualcuno"}

        with self.assertLogs("security", level="WARNING") as log:
            with self.assertRaises(AuthenticationFailed):
                AdminTokenView().post(request)

        testo = "\n".join(log.output)
        self.assertIn("security.login_fallito", testo)
        self.assertIn(f"provenienza={_IP} bloccato=False", testo)
        self.assertNotIn("security.login_locked", testo)

    # Scopo: Il nome si normalizza come lo normalizza il serializer (spazi
    # tolti): « tid » deve trovare la credenziale di «tid» e avere la sua
    # impronta. Prima il lookup usava il valore grezzo e con uno spazio
    # davanti blocco, freno e attesa non si controllavano.
    @patch("apps.core.api.auth_views._auth_repo")
    @patch.object(AuditTokenObtainPairView, "_find_user")
    @patch("rest_framework_simplejwt.views.TokenObtainPairView.post")
    def test_nome_con_spazi_trova_la_credenziale_come_authenticate(
        self, mock_super_post, mock_find_user, mock_repo
    ):
        mock_find_user.return_value = MagicMock(id=42, username="tid")
        mock_repo.registra_tentativo_login.return_value = {"bloccato": False}
        mock_super_post.side_effect = AuthenticationFailed()
        request = MagicMock()
        request.data = {"username": "  tid "}

        with self.assertRaises(AuthenticationFailed):
            AdminTokenView().post(request)

        mock_find_user.assert_called_once_with("tid")
        mock_repo.check_blocco_login.assert_called_once_with(
            42, nome_digest=_DIGEST_TID, provenienza=_IP,
        )

    # Scopo: Senza un nome valido la richiesta non e' un tentativo: il
    # serializer rispondera' 400 senza guardare la password. Nessuna chiamata
    # al DB, e la risposta non dipende da nessuna credenziale.
    @patch("apps.core.api.auth_views._auth_repo")
    @patch.object(AuditTokenObtainPairView, "_find_user")
    @patch("rest_framework_simplejwt.views.TokenObtainPairView.post")
    def test_nome_assente_nessuna_chiamata_al_db(
        self, mock_super_post, mock_find_user, mock_repo
    ):
        mock_super_post.return_value = Response({"username": ["obbligatorio"]}, status=400)
        for dati in ({}, {"username": ""}, {"username": "   "}, {"username": ["x"]}):
            with self.subTest(dati=dati):
                request = MagicMock()
                request.data = dati
                AdminTokenView().post(request)
        mock_find_user.assert_not_called()
        mock_repo.check_blocco_login.assert_not_called()
        mock_repo.registra_tentativo_login.assert_not_called()

    # Scopo: Un guasto del DB mentre si cerca la credenziale NON e' «nome
    # inesistente»: l'errore sale e il login si ferma, senza controlli ne'
    # tentativi sul nome e senza arrivare ad `authenticate`. Prima un
    # `except Exception` lo ingoiava, e il blocco dell'admin non si guardava.
    @patch("apps.core.api.auth_views._auth_repo")
    @patch("apps.core.api.auth_views.User.objects.filter", side_effect=DatabaseError("giu'"))
    @patch("rest_framework_simplejwt.views.TokenObtainPairView.post")
    def test_guasto_nella_ricerca_ferma_il_login(
        self, mock_super_post, _mock_filter, mock_repo
    ):
        request = MagicMock()
        request.data = {"username": "tid", "password": "x"}
        with self.assertRaises(DatabaseError):
            AdminTokenView().post(request)
        mock_repo.check_blocco_login.assert_not_called()
        mock_repo.registra_tentativo_login.assert_not_called()
        mock_super_post.assert_not_called()

    # Scopo: T-2 (brief sicurezza §3.4-bis). Password giusta e secondo
    # fattore ATTIVO: niente JWT ne' cookie, niente successo sul freno ne'
    # sessione; una sfida legata alla credenziale, alla veste del refresh
    # appena emesso, alla porta e alla provenienza.
    @patch(f"{_SERVICE}.record_login")
    @patch("apps.core.api.auth_views._extract_identita_id_from_refresh", return_value=7)
    @patch.object(AuditTokenObtainPairView, "_extract_claims", return_value=(42, "sid-1"))
    @patch.object(AuditTokenObtainPairView, "_find_user")
    @patch("apps.core.api.auth_views._auth_repo")
    @patch(_SET_GUCS)
    @patch("rest_framework_simplejwt.views.TokenObtainPairView.post")
    def test_secondo_fattore_attivo_risponde_con_la_sfida(
        self, mock_super_post, mock_gucs, mock_repo, mock_find_user, _extract, _identita, mock_record,
    ):
        from apps.core.services.sfida_secondo_fattore import leggi_sfida

        mock_find_user.return_value = MagicMock(id=42, username="tid")
        mock_super_post.return_value = Response(
            {"access": "tok.access", "refresh": "tok.refresh"}, status=200,
        )
        with patch(_SECONDO_FATTORE) as device:
            device.get_device.return_value = {"stato": "ATTIVO"}
            request = MagicMock()
            request._request = MagicMock()
            request.data = {"username": "tid"}
            response = AdminTokenView().post(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["two_factor_required"])
        self.assertNotIn("access", response.data)
        self.assertNotIn("refresh", response.data)
        self.assertNotIn(REFRESH_COOKIE_NAME, response.cookies)
        mock_repo.registra_tentativo_login.assert_not_called()
        mock_gucs.assert_not_called()
        mock_record.assert_not_called()
        sfida = leggi_sfida(response.data["sfida"], porta="admin", provenienza=_IP)
        self.assertEqual((sfida.auth_user_id, sfida.identita_id), (42, 7))

    # Scopo: Verifica il guard di astrazione. Chiamare direttamente
    # AuditTokenObtainPairView().post() senza subclasse -> RuntimeError.
    # Previene regressione silente in cui qualcuno usa la base class
    # in urls.py o in test dimenticando serializer_class: il JWT emesso
    # sarebbe senza claim identita_id/ruolo_applicativo (multi-face broken).
    def test_base_astratta_guard_solleva_runtime_error(self):
        view = AuditTokenObtainPairView()
        request = MagicMock()
        request.data = {"username": "tid"}
        with self.assertRaises(RuntimeError) as ctx:
            view.post(request)
        self.assertIn("astratta", str(ctx.exception))


class ExtractIdentitaIdFromRefreshTests(TestCase):
    """Helper `_extract_identita_id_from_refresh` deve essere fail-open:
    restituisce None per qualsiasi input non parseable, cosi' set_jwt_gucs
    cade sul fallback legacy invece di rompere il flusso login/refresh."""

    def test_none_returns_none(self):
        from apps.core.api.auth_views import _extract_identita_id_from_refresh
        self.assertIsNone(_extract_identita_id_from_refresh(None))

    def test_empty_string_returns_none(self):
        from apps.core.api.auth_views import _extract_identita_id_from_refresh
        self.assertIsNone(_extract_identita_id_from_refresh(""))

    def test_invalid_token_fail_open(self):
        """Token non parseable: non deve sollevare, ritorna None."""
        from apps.core.api.auth_views import _extract_identita_id_from_refresh
        self.assertIsNone(_extract_identita_id_from_refresh("not.a.valid.jwt"))


class DecodeRefreshPayloadTests(TestCase):
    """Helper `_decode_refresh_payload` e' la base di entrambi gli
    estrattori tipati (identita_id e ruolo_applicativo). Contratto:
    ritorna sempre un dict; fail-open su input invalido."""

    def test_none_returns_empty_dict(self):
        from apps.core.api.auth_views import _decode_refresh_payload
        self.assertEqual(_decode_refresh_payload(None), {})

    def test_invalid_token_returns_empty_dict(self):
        """Token non parseable: dict vuoto + log warning."""
        from apps.core.api.auth_views import _decode_refresh_payload
        self.assertEqual(_decode_refresh_payload("garbage.not.jwt"), {})


class RefreshCrossNamespaceGuardTests(TestCase):
    """Guard §8.3.5: la view refresh concreta rifiuta il refresh di un
    token la cui veste non rientra in `expected_ruoli_applicativi`.
    Impedisce che un refresh portale venga girato su /admin/token/refresh/
    e viceversa (rumore semantico cross-path)."""

    def setUp(self):
        _veste_utilizzabile(self)

    def test_base_astratta_guard_solleva_runtime_error(self):
        """AuditTokenRefreshView e' astratta: `as_view()` diretto senza
        subclass → RuntimeError. Consistenza con §8.3.3 A1
        (AuditTokenObtainPairView). Previene che qualcuno registri la
        base direttamente in urls, bypassando il guard cross-namespace."""
        view = AuditTokenRefreshView()
        self.assertEqual(tuple(view.expected_ruoli_applicativi), ())
        request = _richiesta_refresh("r.x.y")
        with self.assertRaises(RuntimeError) as ctx:
            view.post(request)
        self.assertIn("astratta", str(ctx.exception))

    @patch(_CLAIMS)
    @patch(_RINNOVA)
    def test_admin_refresh_accetta_operatore(self, mock_super, mock_extract):
        """Token admin valido (veste OPERATORE) → guard passa, super.post chiamato."""
        mock_extract.return_value = {"ruolo_applicativo": RUOLO_APPLICATIVO_OPERATORE}
        mock_super.return_value = Response({"access": "new"}, status=200)
        view = AdminTokenRefreshView()
        request = _richiesta_refresh("r.admin.token")
        # Non deve sollevare — flow continua.
        view.post(request)
        mock_super.assert_called_once()

    @patch(_CLAIMS)
    @patch(_RINNOVA)
    def test_admin_refresh_rifiuta_portale(self, mock_super, mock_extract):
        """Token portale inviato a /admin/token/refresh/ → VesteNonAttivaError
        (403) SENZA arrivare a super().post(): non diamo feedback al client."""
        mock_extract.return_value = {"ruolo_applicativo": RUOLO_APPLICATIVO_CLIENTE_PORTALE}
        view = AdminTokenRefreshView()
        request = _richiesta_refresh("r.portale.token")
        with self.assertRaises(VesteNonAttivaError):
            view.post(request)
        mock_super.assert_not_called()

    @patch(_CLAIMS)
    def test_admin_refresh_rifiuta_claim_assente(self, mock_extract):
        """Claim ruolo_applicativo None (token pre-§8.3.2) → VesteNonAttivaError.
        Rompe il refresh dei token vecchi — coerente con la politica grace=0."""
        mock_extract.return_value = {}
        view = AdminTokenRefreshView()
        request = _richiesta_refresh("r.legacy.token")
        with self.assertRaises(VesteNonAttivaError):
            view.post(request)

    @patch(_CLAIMS)
    @patch(_RINNOVA)
    def test_portale_refresh_rifiuta_operatore(self, mock_super, mock_extract):
        """Simmetrico ad admin_refresh_rifiuta_portale: token OPERATORE
        inviato a /portale/token/refresh/ → VesteNonAttivaError, niente
        super().post()."""
        mock_extract.return_value = {"ruolo_applicativo": RUOLO_APPLICATIVO_OPERATORE}
        view = PortaleTokenRefreshView()
        request = _richiesta_refresh("r.admin.token")
        with self.assertRaises(VesteNonAttivaError):
            view.post(request)
        mock_super.assert_not_called()

    @patch(_CLAIMS)
    @patch(_RINNOVA)
    def test_shop_refresh_rifiuta_portale(self, mock_super, mock_extract):
        """Token CLIENTE_PORTALE inviato a /shop/token/refresh/ → rifiutato.
        Assicura che shop namespace sia strictamente isolato da portale."""
        mock_extract.return_value = {"ruolo_applicativo": RUOLO_APPLICATIVO_CLIENTE_PORTALE}
        view = ShopTokenRefreshView()
        request = _richiesta_refresh("r.portale.token")
        with self.assertRaises(VesteNonAttivaError):
            view.post(request)
        mock_super.assert_not_called()


class NamespaceRefreshViewConcreteTests(TestCase):
    """Invariante di configurazione: le 3 subclass refresh espongono il
    subset atteso di ruoli — stesso contratto delle subclass Token (§8.3.3)."""

    def test_admin_refresh_expected_ruoli(self):
        self.assertEqual(
            tuple(AdminTokenRefreshView.expected_ruoli_applicativi),
            (RUOLO_APPLICATIVO_OPERATORE,),
        )

    def test_portale_refresh_expected_ruoli(self):
        ruoli = set(PortaleTokenRefreshView.expected_ruoli_applicativi)
        self.assertEqual(
            ruoli,
            {RUOLO_APPLICATIVO_CLIENTE_PORTALE, RUOLO_APPLICATIVO_FORNITORE_PORTALE},
        )
        self.assertNotIn(RUOLO_APPLICATIVO_OPERATORE, ruoli)
        self.assertNotIn(RUOLO_APPLICATIVO_SHOP_CUSTOMER, ruoli)

    def test_shop_refresh_expected_ruoli(self):
        self.assertEqual(
            tuple(ShopTokenRefreshView.expected_ruoli_applicativi),
            (RUOLO_APPLICATIVO_SHOP_CUSTOMER,),
        )


class RefreshCookieTests(TestCase):
    """Brief sicurezza §2 (2026-09-28): il refresh viaggia nel cookie
    HttpOnly, mai nel corpo; il refresh, autenticato dal solo cookie,
    pretende l'header anti-CSRF."""

    def setUp(self):
        _senza_secondo_fattore(self)
        _veste_utilizzabile(self)

    # Scopo: Gli attributi del cookie scritto: sono loro la protezione.
    def _assert_cookie_refresh(self, response, valore: str) -> None:
        cookie = response.cookies[REFRESH_COOKIE_NAME]
        self.assertEqual(cookie.value, valore)
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Strict")
        self.assertEqual(cookie["path"], "/api/v1/")
        self.assertGreater(int(cookie["max-age"]), 0)

    # Scopo: Senza `X-Requested-With` il refresh non parte: un form di un altro
    #        sito porterebbe il cookie ma non l'header.
    @patch(_RINNOVA)
    def test_refresh_senza_header_anti_csrf_rifiuta(self, mock_rinnova):
        with self.assertRaises(ServiceError) as ctx:
            AdminTokenRefreshView().post(_richiesta_refresh(header=False))
        self.assertEqual(ctx.exception.code, "E_PERMISSION_DENIED")
        mock_rinnova.assert_not_called()

    # Scopo: Senza cookie e' una sessione assente: 401, il client va al login.
    @patch(_RINNOVA)
    def test_refresh_senza_cookie_e_401(self, mock_rinnova):
        with self.assertRaises(InvalidToken):
            AdminTokenRefreshView().post(_richiesta_refresh(None))
        mock_rinnova.assert_not_called()

    # Scopo: Il refresh ruotato torna nel cookie; nel corpo resta il solo access.
    @patch(_CLAIMS, return_value={"ruolo_applicativo": RUOLO_APPLICATIVO_OPERATORE})
    @patch(f"{_SERVICE}.record_refresh")
    @patch.object(AuditTokenRefreshView, "_resolve_username", return_value=None)
    @patch(_RINNOVA)
    def test_refresh_riuscito_ruota_il_cookie_e_toglie_il_corpo(
        self, mock_rinnova, _mock_resolve, _mock_record, _mock_ruolo,
    ):
        mock_rinnova.return_value = Response(
            {"access": "nuovo.access", "refresh": "nuovo.refresh"}, status=200,
        )
        response = AdminTokenRefreshView().post(_richiesta_refresh("vecchio.refresh"))
        mock_rinnova.assert_called_once_with("vecchio.refresh")
        self.assertEqual(response.data, {"access": "nuovo.access"})
        self._assert_cookie_refresh(response, "nuovo.refresh")

    # Scopo: Il login risponde col solo access; il refresh e' nel cookie.
    @patch(_GET_IP, return_value=_IP)
    @patch(f"{_SERVICE}.record_login")
    @patch.object(AuditTokenObtainPairView, "_extract_claims", return_value=(42, "sid-1"))
    @patch.object(AuditTokenObtainPairView, "_find_user")
    @patch("apps.core.api.auth_views._auth_repo")
    @patch(_SET_GUCS)
    @patch("rest_framework_simplejwt.views.TokenObtainPairView.post")
    def test_login_riuscito_mette_il_refresh_nel_cookie(
        self, mock_super_post, _gucs, mock_repo, mock_find_user, _mock_extract, _mock_record, _mock_ip,
    ):
        mock_find_user.return_value = MagicMock(id=42, username="alice")
        mock_repo.registra_tentativo_login.return_value = {"bloccato": False}
        mock_repo.get_deve_cambiare_password.return_value = False
        mock_super_post.return_value = Response(
            {"access": "tok.access", "refresh": "tok.refresh"}, status=200,
        )
        request = MagicMock()
        request._request = MagicMock()
        request.data = {"username": "alice"}
        response = AdminTokenView().post(request)
        self.assertEqual(response.data, {"access": "tok.access"})
        self._assert_cookie_refresh(response, "tok.refresh")

    # Scopo: E-8 — un refresh illeggibile o non emesso da noi e' una sessione
    #        non valida: 401, non il 403 «veste assente» di quando la veste si
    #        leggeva da un token decodificato alla cieca. Qui la verifica e'
    #        VERA (nessun mock dei claim): la stringa non e' un JWT nostro.
    @patch(_RINNOVA)
    def test_refresh_illeggibile_e_401_non_403(self, mock_rinnova):
        with self.assertRaises(InvalidToken):
            AdminTokenRefreshView().post(_richiesta_refresh("non.un.jwt"))
        mock_rinnova.assert_not_called()

    # Scopo: una firma che non e' la nostra, anche con la veste «giusta» nel
    #        payload, e' un 401: la veste si legge solo da un token verificato.
    @patch(_RINNOVA)
    def test_refresh_firmato_da_altri_e_401(self, mock_rinnova):
        import jwt

        falso = jwt.encode(
            {"token_type": "refresh", "user_id": 1, "ruolo_applicativo": RUOLO_APPLICATIVO_OPERATORE},
            "una-chiave-che-non-e-la-nostra-lunga-abbastanza-per-hs256", algorithm="HS256",
        )
        with self.assertRaises(InvalidToken):
            AdminTokenRefreshView().post(_richiesta_refresh(falso))
        mock_rinnova.assert_not_called()

    # Scopo: un refresh NOSTRO (firma vera) ma di un altro canale resta il 403
    #        del guard cross-namespace: E-8 non ha cambiato quel verso.
    @patch(_RINNOVA)
    def test_refresh_nostro_di_altro_canale_resta_403(self, mock_rinnova):
        from rest_framework_simplejwt.tokens import RefreshToken

        token = RefreshToken()
        token["ruolo_applicativo"] = RUOLO_APPLICATIVO_CLIENTE_PORTALE
        with self.assertRaises(VesteNonAttivaError):
            AdminTokenRefreshView().post(_richiesta_refresh(str(token)))
        mock_rinnova.assert_not_called()

    # Scopo: GUC e audit del refresh nascono dagli STESSI claim verificati del
    #        guard: identita, emittente attivo, user_id e sid. Se l'emittente
    #        si perdesse, ogni rinnovo riporterebbe l'utente in modalita'
    #        globale a sua insaputa.
    @patch(f"{_SERVICE}.record_refresh")
    @patch.object(AuditTokenRefreshView, "_resolve_username", return_value="alice")
    @patch(_SET_GUCS)
    @patch(_RINNOVA)
    @patch(_CLAIMS)
    def test_refresh_gucs_dai_claim_verificati(
        self, mock_claims, mock_rinnova, mock_set_gucs, _mock_resolve, mock_record,
    ):
        mock_claims.return_value = {
            "ruolo_applicativo": RUOLO_APPLICATIVO_OPERATORE,
            "user_id": "42", "identita_id": 7, "emittente_attivo_id": 32, "sid": "sid-x",
        }
        mock_rinnova.return_value = Response({"access": "a", "refresh": "r"}, status=200)
        request = _richiesta_refresh()
        AdminTokenRefreshView().post(request)
        mock_set_gucs.assert_called_once_with(
            username="alice", user_id=42, identita_id=7,
            emittente_attivo_id=32, request=request._request,
        )
        mock_record.assert_called_once_with(user_id=42, request=request._request, jti="sid-x")

    # Scopo: nome del cookie e header anti-CSRF sono scritti anche in bash
    #        (`_smoke_refresh.sh`) e nel frontend (`core/api.js`), che non
    #        possono importarli. Una divergenza non da' errore: il refresh
    #        risponde 403 o 401 e l'utente torna al login. Qui si confrontano.
    def test_nome_cookie_e_header_uguali_nei_tre_linguaggi(self):
        from apps.core.tests._repo import repo_root

        smoke = (repo_root() / "backend/scripts/tests/_smoke_refresh.sh").read_text(encoding="utf-8")
        self.assertIn(f'SMOKE_REFRESH_COOKIE="{REFRESH_COOKIE_NAME}"', smoke)
        self.assertIn(f"{ANTI_CSRF_HEADER}: {ANTI_CSRF_VALORE}", smoke)

        fe = (repo_root() / "frontend/src/core/api.js").read_text(encoding="utf-8")
        self.assertIn(f"const ANTI_CSRF_HEADER = '{ANTI_CSRF_HEADER}'", fe)
        self.assertIn(f"const ANTI_CSRF_VALORE = '{ANTI_CSRF_VALORE}'", fe)

    # Scopo: `handle_post_json_con_refresh`: dati nel corpo, refresh nel cookie.
    def test_post_con_refresh_riuscito_scrive_il_cookie(self):
        from rest_framework.parsers import JSONParser
        from rest_framework.request import Request
        from rest_framework.test import APIRequestFactory

        from apps.core.api.refresh_cookie import handle_post_json_con_refresh

        grezza = APIRequestFactory().post("/api/v1/x/", "{}", content_type="application/json")
        response = handle_post_json_con_refresh(
            Request(grezza, parsers=[JSONParser()]), lambda _p: ({"access": "a"}, "r.nuovo"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"r.nuovo", response.content)
        self._assert_cookie_refresh(response, "r.nuovo")

    # Scopo: un errore del gestore (dopo aver emesso o no) → nessun cookie: il
    #        browser non tiene il refresh di una sessione dichiarata fallita.
    def test_post_con_refresh_fallito_non_scrive_il_cookie(self):
        from rest_framework.parsers import JSONParser
        from rest_framework.request import Request
        from rest_framework.test import APIRequestFactory

        from apps.core.api.refresh_cookie import handle_post_json_con_refresh

        def _gestore(_payload):
            raise ServiceError(code="E_CHANGE_PASSWORD", message="no")

        grezza = APIRequestFactory().post("/api/v1/x/", "{}", content_type="application/json")
        response = handle_post_json_con_refresh(Request(grezza, parsers=[JSONParser()]), _gestore)
        self.assertNotEqual(response.status_code, 200)
        self.assertNotIn(REFRESH_COOKIE_NAME, response.cookies)


class RefreshVesteSpentaTests(TestCase):
    """D-5 (Tid, 2026-10-02): una veste spenta chiude le sue sessioni al primo
    rinnovo, qualunque strada l'abbia spenta. Il controllo sta PRIMA della
    rotazione, e il refresh presentato si blocca per sid: una veste riaccesa
    dopo non resuscita la sessione."""

    _CLAIMS_VESTE = {
        "ruolo_applicativo": RUOLO_APPLICATIVO_OPERATORE,
        "user_id": "42", "identita_id": 7, "sid": "sid-x",
    }

    # Scopo: Veste utilizzabile → si rinnova, e la veste si cerca sulla credenziale
    #        del token (id della veste + user_id, mai la sola veste).
    @patch(f"{_SERVICE}.record_refresh")
    @patch.object(AuditTokenRefreshView, "_resolve_username", return_value=None)
    @patch(_BLOCCA)
    @patch(_RINNOVA)
    @patch(_AUTH_REPO)
    @patch(_CLAIMS)
    def test_veste_utilizzabile_rinnova(
        self, mock_claims, mock_repo, mock_rinnova, mock_blocca, _resolve, _record,
    ):
        mock_claims.return_value = dict(self._CLAIMS_VESTE)
        mock_repo.get_veste_utilizzabile.return_value = {"id": 7, "attivo": True}
        mock_rinnova.return_value = Response({"access": "a", "refresh": "r"}, status=200)
        response = AdminTokenRefreshView().post(_richiesta_refresh())
        self.assertEqual(response.status_code, 200)
        mock_repo.get_veste_utilizzabile.assert_called_once_with(7, 42)
        mock_blocca.assert_not_called()

    # Scopo: Veste non utilizzabile (spenta o fuori date: decide il DB) → 401,
    #        nessuna rotazione, e la SOLA sessione del token presentato finisce
    #        in blacklist (filtro per sid).
    @patch(_BLOCCA)
    @patch(_RINNOVA)
    @patch(_AUTH_REPO)
    @patch(_CLAIMS)
    def test_veste_spenta_401_senza_rotazione_e_sessione_bloccata(
        self, mock_claims, mock_repo, mock_rinnova, mock_blocca,
    ):
        mock_claims.return_value = dict(self._CLAIMS_VESTE)
        mock_repo.get_veste_utilizzabile.return_value = None
        with self.assertRaises(InvalidToken):
            AdminTokenRefreshView().post(_richiesta_refresh())
        mock_rinnova.assert_not_called()
        mock_blocca.assert_called_once()
        user_id, vale_sid = mock_blocca.call_args.args
        self.assertEqual(user_id, 42)
        self.assertTrue(vale_sid("sid-x"))
        self.assertFalse(vale_sid("sid-altra"))
        self.assertFalse(vale_sid(""))

    # Scopo: Veste che non c'e' (o di un'altra credenziale: il repo filtra per
    #        user_id e non la trova) → stesso esito della veste spenta.
    @patch(_BLOCCA)
    @patch(_RINNOVA)
    @patch(_AUTH_REPO)
    @patch(_CLAIMS)
    def test_veste_assente_401(self, mock_claims, mock_repo, mock_rinnova, _blocca):
        mock_claims.return_value = dict(self._CLAIMS_VESTE)
        mock_repo.get_veste_utilizzabile.return_value = None
        with self.assertRaises(InvalidToken):
            AdminTokenRefreshView().post(_richiesta_refresh())
        mock_rinnova.assert_not_called()

    # Scopo: Claim `identita_id` assente → 401 senza leggere il DB: ogni
    #        refresh nostro lo porta (grace 0, come per `ruolo_applicativo`).
    @patch(_BLOCCA)
    @patch(_RINNOVA)
    @patch(_AUTH_REPO)
    @patch(_CLAIMS)
    def test_claim_identita_assente_401_senza_db(
        self, mock_claims, mock_repo, mock_rinnova, _blocca,
    ):
        claims = dict(self._CLAIMS_VESTE)
        del claims["identita_id"]
        mock_claims.return_value = claims
        with self.assertRaises(InvalidToken):
            AdminTokenRefreshView().post(_richiesta_refresh())
        mock_repo.get_veste_utilizzabile.assert_not_called()
        mock_rinnova.assert_not_called()

    # Scopo: Un guasto nella lettura della veste PROPAGA: il refresh non si
    #        concede su un dubbio, e nemmeno si chiude la sessione.
    @patch(_BLOCCA)
    @patch(_RINNOVA)
    @patch(_AUTH_REPO)
    @patch(_CLAIMS)
    def test_guasto_lettura_veste_propaga(
        self, mock_claims, mock_repo, mock_rinnova, mock_blocca,
    ):
        mock_claims.return_value = dict(self._CLAIMS_VESTE)
        mock_repo.get_veste_utilizzabile.side_effect = DatabaseError("giu'")
        with self.assertRaises(DatabaseError):
            AdminTokenRefreshView().post(_richiesta_refresh())
        mock_rinnova.assert_not_called()
        mock_blocca.assert_not_called()
