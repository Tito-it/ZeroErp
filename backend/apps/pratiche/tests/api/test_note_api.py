# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari API note pratiche (CRUD).
#        Mock services, compatibile CI senza database reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) NoteApiTests.test_get_note_ok
2) NoteApiTests.test_post_crea_nota_ok
3) NoteApiTests.test_post_crea_nota_senza_contenuto
4) NoteApiTests.test_patch_aggiorna_nota_ok
5) NoteApiTests.test_delete_nota_ok
6) NoteApiTests.test_note_richiede_jwt
"""

import json
from unittest.mock import Mock, patch


from apps.core.tests._helpers.jwt_mock import ClientApi
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_VIEWS = "apps.pratiche.api.views"


def _mock_nota() -> dict:
    return {
        "id": 1, "pratica_id": 10, "tipo_nota_id": 1,
        "tipo_nota_codice": "GENERALE", "tipo_nota_descrizione": "Generale",
        "contenuto": "Nota di test",
        "data_insert": "2026-03-29T10:00:00+00:00", "user_insert": "operatore1",
        "data_update": "2026-03-29T10:00:00+00:00", "user_update": "operatore1",
    }


class NoteApiTests(JwtMockedApiTest):

    def setUp(self) -> None:
        super().setUp()
        self.client = ClientApi()

    # Scopo: Verifica GET lista note pratica.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.get_note_pratica")
    def test_get_note_ok(self, mock_get, _auth):
        mock_get.return_value = [_mock_nota()]

        resp = self.client.get("/api/v1/pratiche/10/note/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body["data"]["results"]), 1)
        self.assertEqual(body["data"]["results"][0]["contenuto"], "Nota di test")

    # Scopo: Verifica POST creazione nota.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.crea_nota_pratica")
    def test_post_crea_nota_ok(self, mock_crea, _auth):
        mock_crea.return_value = 5

        resp = self.client.post(
            "/api/v1/pratiche/10/note/",
            data=json.dumps({"tipo_nota_codice": "GENERALE", "contenuto": "Nuova nota"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["nota_id"], 5)

    # Scopo: Verifica errore POST senza contenuto.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.crea_nota_pratica")
    def test_post_crea_nota_senza_contenuto(self, mock_crea, _auth):
        from apps.core.services.service_errors import ServiceError
        mock_crea.side_effect = ServiceError(code="E_PRATICA_VALIDATION", message="contenuto nota obbligatorio")

        resp = self.client.post(
            "/api/v1/pratiche/10/note/",
            data=json.dumps({"tipo_nota_codice": "GENERALE", "contenuto": ""}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    # Scopo: Verifica PATCH aggiornamento nota.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.aggiorna_nota_pratica")
    def test_patch_aggiorna_nota_ok(self, mock_aggiorna, _auth):
        resp = self.client.patch(
            "/api/v1/pratiche/10/note/1/",
            data=json.dumps({"contenuto": "Contenuto aggiornato"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["data"]["updated"])
        mock_aggiorna.assert_called_once_with(nota_id=1, pratica_id=10, contenuto="Contenuto aggiornato")

    # Scopo: Verifica DELETE nota.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.pratiche_service.elimina_nota_pratica")
    def test_delete_nota_ok(self, mock_elimina, _auth):
        resp = self.client.delete("/api/v1/pratiche/10/note/1/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["data"]["deleted"])
        mock_elimina.assert_called_once_with(nota_id=1, pratica_id=10)

    # Scopo: Verifica che endpoint note richieda JWT.
    def test_note_richiede_jwt(self):
        resp = self.client.get("/api/v1/pratiche/10/note/")
        self.assertEqual(resp.status_code, 401)
