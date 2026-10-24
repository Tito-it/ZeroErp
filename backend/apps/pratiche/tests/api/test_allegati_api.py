# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari API allegati pratiche (CRUD senza upload).
#        Mock services, compatibile CI senza database reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) AllegatiApiTests.test_get_allegati_ok
2) AllegatiApiTests.test_post_crea_allegato_ok
3) AllegatiApiTests.test_delete_allegato_ok
4) AllegatiApiTests.test_allegati_richiede_jwt
"""

import json
from unittest.mock import Mock, patch


from apps.core.tests._helpers.jwt_mock import ClientApi
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_VIEWS = "apps.pratiche.api.views"


class AllegatiApiTests(JwtMockedApiTest):

    def setUp(self) -> None:
        super().setUp()
        self.client = ClientApi()

    # Scopo: Verifica GET lista allegati pratica.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.get_allegati_pratica")
    def test_get_allegati_ok(self, mock_get, _auth):
        mock_get.return_value = [{
            "id": 1, "pratica_id": 10, "tipo_allegato_id": 1,
            "tipo_allegato_codice": "DOCUMENTO", "tipo_allegato_descrizione": "Documento",
            "nome_file": "contratto.pdf", "percorso": None, "mime_type": "application/pdf",
            "dimensione": 12345, "allegato_padre_id": None,
            "data_insert": "2026-03-29T10:00:00+00:00", "user_insert": "operatore1",
        }]

        resp = self.client.get("/api/v1/pratiche/10/allegati/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body["data"]["results"]), 1)
        self.assertEqual(body["data"]["results"][0]["nome_file"], "contratto.pdf")

    # Scopo: Verifica POST creazione record allegato.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.crea_allegato_pratica")
    def test_post_crea_allegato_ok(self, mock_crea, _auth):
        mock_crea.return_value = 5

        resp = self.client.post(
            "/api/v1/pratiche/10/allegati/",
            data=json.dumps({
                "tipo_allegato_codice": "DOCUMENTO",
                "nome_file": "contratto.pdf",
                "mime_type": "application/pdf",
                "dimensione": 12345,
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["allegato_id"], 5)

    # Scopo: Verifica DELETE allegato.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.elimina_allegato_pratica")
    def test_delete_allegato_ok(self, mock_elimina, _auth):
        resp = self.client.delete("/api/v1/pratiche/10/allegati/1/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["data"]["deleted"])
        mock_elimina.assert_called_once_with(allegato_id=1, pratica_id=10)

    # Scopo: Verifica che endpoint allegati richieda JWT.
    def test_allegati_richiede_jwt(self):
        resp = self.client.get("/api/v1/pratiche/10/allegati/")
        self.assertEqual(resp.status_code, 401)
