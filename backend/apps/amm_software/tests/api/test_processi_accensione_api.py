# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: L'endpoint della scelta a mano sull'accensione di un processo
#        (`POST /api/v1/amm-software/processi/<codice>/accensione/`): la porta,
#        la rotta, l'idempotenza e il passaggio al service col nome di chi
#        preme. Le regole del gesto sono in `test_processi_accensione.py`, il
#        giro sul DB vero in `tests/db/test_processi_accensione_db.py`.
# ------------------------------------------------------------
"""Indice test.

1. test_richiede_jwt                 senza JWT -> 401
2. test_richiede_idempotency_key     verbo che scrive -> 400 senza chiave
3. test_porta_admin_e_rotta          `AdminAPIView`, e la rotta porta qui
4. test_ok_passa_corpo_e_attore      200 con l'accensione rinfrescata; il
                                     service riceve corpo e username
"""

import json
from unittest.mock import Mock, patch

from django.test import Client
from django.urls import resolve

from apps.amm_software.api.views import ProcessiAccensioneView
from apps.core.api.base_views import AdminAPIView
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_SERVICE = "apps.amm_software.api.views.ProcessiService"
_URL = "/api/v1/amm-software/processi/draina_coda_stampa/accensione/"


# Scopo: un superuser: `AdminAPIView` lo fa passare da `is_superuser`.
def _mock_user() -> Mock:
    user = Mock(id=9, username="op9", is_superuser=True, is_authenticated=True)
    user.get_username.return_value = "op9"
    return user


class ProcessiAccensioneApiTests(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    # Scopo: POST con il corpo dato e l'header, salvo `senza_chiave`.
    def _post(self, body: dict, *, senza_chiave: bool = False):
        headers = {} if senza_chiave else {"Idempotency-Key": "k-accensione-1"}
        return self.client.post(
            _URL, data=json.dumps(body), content_type="application/json", headers=headers,
        )

    # 1. Senza JWT -> 401.
    def test_richiede_jwt(self) -> None:
        self.assertEqual(self._post({"acceso": False, "motivo": "m"}).status_code, 401)

    # 2. Senza Idempotency-Key -> 400: e' un verbo che scrive.
    @patch(_AUTH, return_value=(_mock_user(), None))
    def test_richiede_idempotency_key(self, _auth) -> None:
        resp = self._post({"acceso": False, "motivo": "m"}, senza_chiave=True)
        self.assertEqual(resp.status_code, 400)

    # 3. La porta e' `AdminAPIView` (come «Esegui ora»), e la rotta porta qui.
    def test_porta_admin_e_rotta(self) -> None:
        self.assertTrue(issubclass(ProcessiAccensioneView, AdminAPIView))
        self.assertIs(resolve(_URL).func.view_class, ProcessiAccensioneView)
        self.assertFalse(hasattr(ProcessiAccensioneView, "post_permission"))

    # 4. Il caso buono: il corpo arriva al service com'e', con lo username di
    #    chi preme; la risposta e' cio' che il service restituisce.
    @patch(_AUTH, return_value=(_mock_user(), None))
    @patch(_SERVICE)
    def test_ok_passa_corpo_e_attore(self, svc_cls, _auth) -> None:
        svc_cls.return_value.imposta_accensione.return_value = {"acceso": False}
        resp = self._post({"acceso": False, "motivo": "manutenzione"})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["data"], {"acceso": False})
        args, kwargs = svc_cls.return_value.imposta_accensione.call_args
        self.assertEqual(args, ("draina_coda_stampa", {"acceso": False, "motivo": "manutenzione"}))
        self.assertEqual(kwargs, {"attore": "op9"})
