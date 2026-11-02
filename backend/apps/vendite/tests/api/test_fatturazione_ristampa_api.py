# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke test HTTP dell'endpoint di ristampa massiva lotto (C-8):
#        POST /vendite/fatturazione/lotti/<id>/ristampa/. Mock del service
#        (nessun DB): verifica auth, idempotency-key obbligatoria, delega al
#        service con lotto_id + auth_user_id dello scope operatore.
#
# Indice test:
#   1) ristampa_richiede_jwt — 401
#   2) ristampa_richiede_idempotency_key — 400
#   3) ristampa_ok_delega_al_service — 200 + kwargs service
# ------------------------------------------------------------

import json
from unittest.mock import Mock, patch

from django.test import Client

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_RISTAMPA = "apps.vendite.api.views.ristampa_lotto"
_SCOPE_UID = "apps.vendite.api.views.get_scope_user_id"

_URL = "/api/v1/vendite/fatturazione/lotti/5/ristampa/"


class FatturazioneRistampaApiTests(JwtMockedApiTest):

    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    # 1. Senza JWT → 401.
    def test_ristampa_richiede_jwt(self) -> None:
        resp = self.client.post(
            _URL, content_type="application/json",
            headers={"Idempotency-Key": "r1"},
        )
        self.assertEqual(resp.status_code, 401)

    # 2. Senza Idempotency-Key → 400.
    @patch(_AUTH, return_value=(Mock(), None))
    def test_ristampa_richiede_idempotency_key(self, _auth) -> None:
        resp = self.client.post(_URL, content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    # 3. Delega al service con lotto_id (dal path) + auth_user_id (scope operatore).
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SCOPE_UID, return_value=9)
    @patch(_RISTAMPA, return_value={"lotto_id": 5, "accodate": 4})
    def test_ristampa_ok_delega_al_service(
        self, mock_svc, _scope, _auth,
    ) -> None:
        resp = self.client.post(
            _URL, data=json.dumps({}), content_type="application/json",
            headers={"Idempotency-Key": "r-ok"},
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"], {"lotto_id": 5, "accodate": 4})
        mock_svc.assert_called_once_with(lotto_id=5, auth_user_id=9)
