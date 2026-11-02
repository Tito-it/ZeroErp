# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del token emesso dal cambio password (M-2): la sessione si
#        riapre nella stessa veste con la catena del login,
#        `emetti_refresh_veste`.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_bb_operatore_porta_veste_sid_ed_emittente
2) test_bb_portale_senza_emittente
3) test_cambio_password_emette_token_con_la_veste
4) test_cambio_password_audit_col_sid
5) test_veste_revocata_401_senza_toccare_la_password
6) test_password_attuale_sbagliata_conta — D-T2, e la password non cambia
7) test_password_attuale_assente_non_conta
8) test_credenziale_frenata_ferma_prima_della_password
9) test_password_attuale_sbagliata_conta_anche_con_la_nuova_debole — l'ordine
10) test_il_tentativo_che_fa_scattare_il_freno_chiude_la_sessione — decisione A
11) test_freno_gia_scattato_chiude_la_sessione
12) test_l_attesa_non_chiude_la_sessione — E_LOGIN_ATTESA rallenta, non blocca
"""

import json
import uuid
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.api.change_password_view import ChangePasswordView
from apps.core.api.refresh_cookie import REFRESH_COOKIE_NAME
from apps.core.api.multi_veste_token_serializer import emetti_refresh_veste
from django.db import DatabaseError

from apps.core.services.service_errors import ServiceError
from apps.core.tests._helpers.operatore_di_prova import operatore_di_prova

_BB = "apps.core.api.multi_veste_token_serializer"
_VIEW = "apps.core.api.change_password_view"
_OPERATORE = {"id": 7, "ruolo_applicativo": "OPERATORE", "attivo": True}
_PORTALE = {"id": 8, "ruolo_applicativo": "CLIENTE_PORTALE", "attivo": True}
_VECCHIA = "vecchia-Pw-1"
_SID = "sid-della-sessione"
_FRENO = "apps.core.services.password_con_freno"


def _token_base(user) -> RefreshToken:
    """Scopo: Il token di `SidTokenObtainPairSerializer.get_token` senza il
    DB (l'OutstandingToken): user_id + sid nuovo."""
    token = RefreshToken()
    token["user_id"] = user.id
    token["sid"] = str(uuid.uuid4())
    return token


def _utente() -> MagicMock:
    user = operatore_di_prova(user_id=42)
    user.get_username.return_value = "alice"
    user.check_password.side_effect = lambda p: p == _VECCHIA
    return user


@patch(f"{_BB}.SidTokenObtainPairSerializer.get_token", side_effect=_token_base)
class EmettiRefreshVesteTests(SimpleTestCase):
    # Scopo: operatore → sid, identita_id, ruolo_applicativo ed emittente.
    @patch(f"{_BB}.EmittenteAttivoService")
    def test_bb_operatore_porta_veste_sid_ed_emittente(self, mock_svc, _get):
        mock_svc.return_value.risolvi_per_login.return_value = 3
        refresh = emetti_refresh_veste(_utente(), _OPERATORE)
        self.assertEqual(refresh["identita_id"], 7)
        self.assertEqual(refresh["ruolo_applicativo"], "OPERATORE")
        self.assertEqual(refresh["emittente_attivo_id"], 3)
        self.assertTrue(refresh["sid"])
        # I claim arrivano anche sull'access token.
        self.assertEqual(refresh.access_token["identita_id"], 7)

    # Scopo: portale → niente emittente, e il resolver non si interroga.
    @patch(f"{_BB}.EmittenteAttivoService")
    def test_bb_portale_senza_emittente(self, mock_svc, _get):
        refresh = emetti_refresh_veste(_utente(), _PORTALE)
        self.assertEqual(refresh["ruolo_applicativo"], "CLIENTE_PORTALE")
        self.assertNotIn("emittente_attivo_id", refresh.payload)
        mock_svc.return_value.risolvi_per_login.assert_not_called()


@patch(f"{_BB}.SidTokenObtainPairSerializer.get_token", side_effect=_token_base)
@patch(f"{_BB}.EmittenteAttivoService")
@patch("apps.core.services.auth_helpers.validate_password")
@patch(f"{_VIEW}.apply_new_password")
@patch(f"{_VIEW}.session_audit_service")
@patch(f"{_VIEW}._auth_repo")
@patch("apps.core.services.request_context.get_client_ip", return_value="203.0.113.7")
@patch("apps.core.api.permissions.ZeroERPPermission.has_permission", return_value=True)
class ChangePasswordTokenVesteTests(SimpleTestCase):
    # Il savepoint del freno vuole una connessione: il suo motivo lo prova il
    # DB vero (`test_la_password_sbagliata_conta_e_frena_la_configurazione`).
    def setUp(self) -> None:
        savepoint = patch(f"{_FRENO}.transaction")
        savepoint.start()
        self.addCleanup(savepoint.stop)
        # La richiesta non passa dal middleware che legge l'header: la key la
        # porta il contesto, come per ogni POST che scrive (§A5).
        chiave = patch("apps.core.api.base_views.get_idempotency_key", return_value="k")
        chiave.start()
        self.addCleanup(chiave.stop)

    def _chiama(self, *, identita_id=7, old_password=_VECCHIA, new_password="nuova-Pw-22"):
        corpo = {"new_password": new_password, "new_password_confirm": new_password}
        if old_password is not None:
            corpo["old_password"] = old_password
        request = APIRequestFactory().post(
            "/api/v1/auth/change-password/", data=json.dumps(corpo), content_type="application/json",
        )
        self.user = _utente()
        force_authenticate(request, user=self.user, token={"identita_id": identita_id, "sid": _SID})
        return ChangePasswordView.as_view()(request)

    def _codice(self, resp) -> str:
        return json.loads(resp.content)["error"]["code"]

    # Scopo: M-2 — il token restituito porta la veste della sessione.
    def test_cambio_password_emette_token_con_la_veste(
        self, _ip, _perm, repo, _audit, _apply, _val, svc, _get
    ):
        repo.get_veste_utilizzabile.return_value = _OPERATORE
        svc.return_value.risolvi_per_login.return_value = None
        resp = self._chiama()
        self.assertEqual(resp.status_code, 200)
        # Il refresh nuovo sta nel cookie HttpOnly, il corpo porta il solo
        # access (brief sicurezza §2).
        self.assertNotIn("refresh", json.loads(resp.content)["data"])
        refresh = RefreshToken(resp.cookies[REFRESH_COOKIE_NAME].value, verify=False)
        self.assertEqual(refresh["identita_id"], 7)
        self.assertEqual(refresh["ruolo_applicativo"], "OPERATORE")
        repo.get_veste_utilizzabile.assert_called_once_with(7, 42)

    # Scopo: l'audit LOGIN registra il sid della sessione nuova, non il jti.
    def test_cambio_password_audit_col_sid(
        self, _ip, _perm, repo, audit, _apply, _val, svc, _get
    ):
        repo.get_veste_utilizzabile.return_value = _OPERATORE
        svc.return_value.risolvi_per_login.return_value = None
        resp = self._chiama()
        refresh = RefreshToken(resp.cookies[REFRESH_COOKIE_NAME].value, verify=False)
        self.assertEqual(audit.record_login.call_args.kwargs["jti"], refresh["sid"])

    # Scopo: veste revocata nel frattempo → 401 E_IDENTITA_NON_ATTIVA e la
    # password NON cambia.
    def test_veste_revocata_401_senza_toccare_la_password(
        self, _ip, _perm, repo, _audit, apply, _val, _svc, _get
    ):
        repo.get_veste_utilizzabile.return_value = None
        resp = self._chiama()
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(json.loads(resp.content)["error"]["code"], "E_IDENTITA_NON_ATTIVA")
        apply.assert_not_called()

    # Scopo: Chi tiene una sessione rubata non prova password senza freno.
    def test_password_attuale_sbagliata_conta(self, _ip, _perm, repo, _audit, apply, _val, _svc, _get):
        repo.registra_tentativo_login.return_value = {"bloccato": False}
        resp = self._chiama(old_password="sbagliata-Pw-1")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(self._codice(resp), "E_CHANGE_PASSWORD")
        repo.check_blocco_login.assert_called_once()
        self.assertFalse(repo.registra_tentativo_login.call_args.kwargs["successo"])
        apply.assert_not_called()

    def test_password_attuale_assente_non_conta(self, _ip, _perm, repo, _audit, apply, _val, _svc, _get):
        resp = self._chiama(old_password=None)
        self.assertEqual(self._codice(resp), "E_CHANGE_PASSWORD")
        repo.registra_tentativo_login.assert_not_called()
        apply.assert_not_called()

    # Scopo: Il freno prima della password: frenata, la password non si guarda.
    def test_credenziale_frenata_ferma_prima_della_password(
        self, _ip, _perm, repo, _audit, apply, _val, _svc, _get
    ):
        repo.check_blocco_login.side_effect = ServiceError(code="E_UTENTE_BLOCCATO", message="bloccato")
        resp = self._chiama()
        self.assertEqual(self._codice(resp), "E_UTENTE_BLOCCATO")
        self.user.check_password.assert_not_called()
        apply.assert_not_called()

    # Scopo: L'ordine. Una nuova password rifiutata non deve arrivare prima
    #        della verifica dell'attuale: altrimenti l'attuale si prova senza
    #        che il tentativo conti.
    def test_password_attuale_sbagliata_conta_anche_con_la_nuova_debole(
        self, _ip, _perm, repo, _audit, apply, val, _svc, _get
    ):
        repo.registra_tentativo_login.return_value = {"bloccato": False}
        resp = self._chiama(old_password="sbagliata-Pw-1", new_password="x")
        self.assertEqual(self._codice(resp), "E_CHANGE_PASSWORD")
        repo.registra_tentativo_login.assert_called_once()
        val.assert_not_called()

    # Scopo: Il rifiuto del DB col codice dato, visto dal BB del freno.
    def _rifiuto(self, codice: str):
        p = patch(f"{_FRENO}.structured_db_error_code", return_value=codice)
        p.start()
        self.addCleanup(p.stop)
        return DatabaseError(codice)

    # Scopo: Le sessioni chiuse dal BB: i sid per cui il filtro passato a
    #        `blocca_token_sessioni` vale.
    @staticmethod
    def _sid_chiusi(blocca) -> list[str]:
        return [s for c in blocca.call_args_list for s in (_SID, "altra-sessione") if c.args[1](s)]

    @patch(f"{_FRENO}.session_audit_service")
    @patch(f"{_FRENO}.blocca_token_sessioni")
    def test_il_tentativo_che_fa_scattare_il_freno_chiude_la_sessione(
        self, blocca, audit, _ip, _perm, repo, _audit, apply, _val, _svc, _get
    ):
        repo.registra_tentativo_login.return_value = {"bloccato": True}
        repo.check_blocco_login.side_effect = [None, self._rifiuto("E_UTENTE_BLOCCATO")]
        self._chiama(old_password="sbagliata-Pw-1")
        # Solo QUELLA sessione, con la riga LOGOUT e il motivo.
        self.assertEqual(self._sid_chiusi(blocca), [_SID])
        self.assertEqual(audit.record_logout.call_args.kwargs["dettaglio"], {"motivo": "FRENO_PASSWORD"})
        apply.assert_not_called()

    @patch(f"{_FRENO}.session_audit_service")
    @patch(f"{_FRENO}.blocca_token_sessioni")
    def test_freno_gia_scattato_chiude_la_sessione(
        self, blocca, _audit_freno, _ip, _perm, repo, _audit, apply, _val, _svc, _get
    ):
        repo.check_blocco_login.side_effect = self._rifiuto("E_UTENTE_BLOCCATO")
        self._chiama()
        self.assertEqual(self._sid_chiusi(blocca), [_SID])
        self.user.check_password.assert_not_called()

    @patch(f"{_FRENO}.blocca_token_sessioni")
    def test_l_attesa_non_chiude_la_sessione(
        self, blocca, _ip, _perm, repo, _audit, apply, _val, _svc, _get
    ):
        repo.check_blocco_login.side_effect = self._rifiuto("E_LOGIN_ATTESA")
        self._chiama()
        blocca.assert_not_called()
