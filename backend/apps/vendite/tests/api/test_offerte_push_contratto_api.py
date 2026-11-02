# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test HTTP del flag `chiudi_esistente` di
#        `POST /api/v1/vendite/offerte/<id>/push-contratto/`. La successione
#        CHIUDE il contratto esistente: il flag si legge dal BB
#        `optional_bool`, mai con `bool(...)` (`bool("false")` e' True). Il BB
#        accetta solo un booleano JSON: una stringa, anche "false", e' un 400.
#        Service mockato, nessun accesso DB (CI-compatible).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_chiudi_esistente_non_booleano_rifiutato — "false" e "abc": 400, il service non e' chiamato
 2) test_chiudi_esistente_arriva_al_service_come_bool — true/false/assente arrivano come bool
"""

import json
from unittest.mock import Mock, patch


from apps.core.tests._helpers.jwt_mock import ClientApi

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest


_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_SVC = "apps.vendite.api.views_offerte.OfferteService"
_URL = "/api/v1/vendite/offerte/7/push-contratto/"


class TestOffertaPushContrattoChiudiEsistente(JwtMockedApiTest):

    def setUp(self) -> None:
        super().setUp()
        self.client = ClientApi()

    def _post(self, body: dict):
        return self.client.post(_URL, data=json.dumps(body), content_type="application/json")

    # Scopo: ⛔ con `bool(...)` la stringa "false" valeva True e la successione
    #        chiudeva il contratto esistente. Ora un valore che non e' un
    #        booleano JSON e' un 400 col campo, e il push non parte.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_chiudi_esistente_non_booleano_rifiutato(self, svc_cls, _auth) -> None:
        for grezzo in ("false", "abc"):
            with self.subTest(grezzo=grezzo):
                resp = self._post({"chiudi_esistente": grezzo})
                self.assertEqual(resp.status_code, 400)
                self.assertEqual(resp.json()["error"]["code"], "E_VALIDATION_INPUT")
        svc_cls.return_value.push_a_contratto.assert_not_called()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC)
    def test_chiudi_esistente_arriva_al_service_come_bool(self, svc_cls, _auth) -> None:
        svc_cls.return_value.push_a_contratto.return_value = {"contratto_id": 1}
        for body, atteso in (
            ({"chiudi_esistente": True}, True),
            ({"chiudi_esistente": False}, False),
            ({}, False),
        ):
            with self.subTest(body=body):
                resp = self._post(body)
                self.assertEqual(resp.status_code, 200)
                self.assertIs(
                    svc_cls.return_value.push_a_contratto.call_args.kwargs["chiudi_esistente"],
                    atteso,
                )
