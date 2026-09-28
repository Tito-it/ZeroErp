# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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

_BB = "apps.core.api.multi_veste_token_serializer"
_VIEW = "apps.core.api.change_password_view"
_OPERATORE = {"id": 7, "ruolo_applicativo": "OPERATORE", "attivo": True}
_PORTALE = {"id": 8, "ruolo_applicativo": "CLIENTE_PORTALE", "attivo": True}


def _token_base(user) -> RefreshToken:
    """Scopo: Il token di `SidTokenObtainPairSerializer.get_token` senza il
    DB (l'OutstandingToken): user_id + sid nuovo."""
    token = RefreshToken()
    token["user_id"] = user.id
    token["sid"] = str(uuid.uuid4())
    return token


def _utente() -> MagicMock:
    user = MagicMock()
    user.id = 42
    user.is_authenticated = True
    user.is_superuser = False
    user.check_password.return_value = True
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
@patch("apps.core.api.permissions.ZeroERPPermission.has_permission", return_value=True)
class ChangePasswordTokenVesteTests(SimpleTestCase):
    def _chiama(self, *, identita_id=7):
        request = APIRequestFactory().post(
            "/api/v1/auth/change-password/",
            data=json.dumps({
                "old_password": "vecchia-Pw-1",
                "new_password": "nuova-Pw-22",
                "new_password_confirm": "nuova-Pw-22",
            }),
            content_type="application/json",
        )
        force_authenticate(request, user=_utente(), token={"identita_id": identita_id})
        return ChangePasswordView.as_view()(request)

    # Scopo: M-2 — il token restituito porta la veste della sessione.
    def test_cambio_password_emette_token_con_la_veste(
        self, _perm, repo, _audit, _apply, _val, svc, _get
    ):
        repo.get_identita_dettaglio.return_value = _OPERATORE
        svc.return_value.risolvi_per_login.return_value = None
        resp = self._chiama()
        self.assertEqual(resp.status_code, 200)
        # Il refresh nuovo sta nel cookie HttpOnly, il corpo porta il solo
        # access (brief sicurezza §2).
        self.assertNotIn("refresh", json.loads(resp.content)["data"])
        refresh = RefreshToken(resp.cookies[REFRESH_COOKIE_NAME].value, verify=False)
        self.assertEqual(refresh["identita_id"], 7)
        self.assertEqual(refresh["ruolo_applicativo"], "OPERATORE")
        repo.get_identita_dettaglio.assert_called_once_with(7, 42)

    # Scopo: l'audit LOGIN registra il sid della sessione nuova, non il jti.
    def test_cambio_password_audit_col_sid(
        self, _perm, repo, audit, _apply, _val, svc, _get
    ):
        repo.get_identita_dettaglio.return_value = _OPERATORE
        svc.return_value.risolvi_per_login.return_value = None
        resp = self._chiama()
        refresh = RefreshToken(resp.cookies[REFRESH_COOKIE_NAME].value, verify=False)
        self.assertEqual(audit.record_login.call_args.kwargs["jti"], refresh["sid"])

    # Scopo: veste revocata nel frattempo → 401 E_IDENTITA_NON_ATTIVA e la
    # password NON cambia.
    def test_veste_revocata_401_senza_toccare_la_password(
        self, _perm, repo, _audit, apply, _val, _svc, _get
    ):
        repo.get_identita_dettaglio.return_value = {**_OPERATORE, "attivo": False}
        resp = self._chiama()
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(json.loads(resp.content)["error"]["code"], "E_IDENTITA_NON_ATTIVA")
        apply.assert_not_called()
