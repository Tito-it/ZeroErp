# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Un campo obbligatorio ASSENTE dal corpo di `collega-pratica` e di
#        `genera-pratica` e' un 400 `E_PREV_VALIDAZIONE` col campo. Fino al
#        2026-10-20 la view lo leggeva con `payload["x"]`: un KeyError, cioe' un
#        500. Service mockato, nessun accesso DB.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_campo_assente_e_400_col_campo — pratica_id, tipo_prestazione_id, priorita_id
"""

import json
from unittest.mock import Mock, patch

from django.test import Client

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest


_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_SVC = "apps.vendite.api.preventivi_views.preventivi_service"


class PreventiviCampiObbligatoriApiTests(JwtMockedApiTest):

    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    @patch(_AUTH, return_value=(Mock(), None))
    def test_campo_assente_e_400_col_campo(self, _auth) -> None:
        casi = (
            ("collega-pratica", {}, "collega_pratica", "pratica_id"),
            ("genera-pratica", {"priorita_id": 2}, "genera_pratica", "tipo_prestazione_id"),
            ("genera-pratica", {"tipo_prestazione_id": 5}, "genera_pratica", "priorita_id"),
        )
        for azione, corpo, servizio, campo in casi:
            with self.subTest(azione=azione, campo=campo), patch(f"{_SVC}.{servizio}") as svc:
                resp = self.client.post(
                    f"/api/v1/vendite/preventivi/7/{azione}/",
                    data=json.dumps(corpo), content_type="application/json",
                    HTTP_IDEMPOTENCY_KEY=f"k-{azione}-{campo}",
                )
                self.assertEqual(resp.status_code, 400, resp.content)
                errore = resp.json()["error"]
                self.assertEqual(errore["code"], "E_PREV_VALIDAZIONE")
                self.assertIn(campo, json.dumps(errore))
                svc.assert_not_called()
