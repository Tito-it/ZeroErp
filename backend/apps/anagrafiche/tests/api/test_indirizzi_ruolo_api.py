# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test API endpoints indirizzi a livello ruolo.
#        Mock del repository e JWT auth, nessun accesso DB (compatibilita CI).
#        I test GET con cascata 3 livelli sono coperti a livello service
#        (test_conti_bancari_service.TestContiBancariRuoloCascataIstanza).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_create_indirizzo_ruolo_ok — POST crea indirizzo normalizzato
 2) test_create_indirizzo_ruolo_with_istanza — POST crea con istanza_utility_id
 3) test_create_indirizzo_ruolo_libero — POST crea indirizzo libero
 3b) test_create_indirizzo_ruolo_senza_tipo_400 — tipo mancante → 400 senza toccare il DB
 4) test_update_indirizzo_ruolo_ok — PATCH aggiorna
 5) test_update_indirizzo_ruolo_not_found — PATCH indirizzo inesistente
 5b) test_update_indirizzo_ruolo_chiave_ignota_400 — chiave fuori contratto → 400
 6) test_delete_indirizzo_ruolo_ok — DELETE elimina
 7) test_delete_indirizzo_ruolo_not_found — DELETE indirizzo inesistente
"""

import json
from unittest.mock import Mock, patch


from apps.core.tests._helpers.jwt_mock import ClientApi
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_REPO = "apps.anagrafiche.api.views_indirizzi_ruolo._repo"
# La PATCH passa dal service dal 2026-09-26 (validazione delle chiavi): il
# repository da mockare e' quello che il service istanzia.
_SVC_REPO = "apps.anagrafiche.services.soggetti_service.SoggettiRepository"


class TestIndirizziRuoloCrudApi(JwtMockedApiTest):
    """Test endpoint CRUD indirizzi ruolo (POST, PATCH, DELETE)."""

    def setUp(self) -> None:
        super().setUp()
        self.client = ClientApi()

    # Il POST passa dal service dal 2026-10-19 (R-DB-16b): l'indirizzo arriva
    # alla madre del DB `fn_crea_indirizzo_ruolo` come un oggetto, codice del
    # tipo compreso (lo risolve la madre).
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC_REPO)
    def test_create_indirizzo_ruolo_ok(self, mock_repo_cls, _auth):
        """POST /anagrafiche/ruoli/{id}/indirizzi/ — crea normalizzato."""
        mock_repo = mock_repo_cls.return_value
        mock_repo.crea_indirizzo_ruolo.return_value = {
            "id": 50, "soggetto_ruolo_id": 10, "tipo_indirizzo_id": 1,
            "istanza_utility_id": None, "indirizzo_dettaglio_id": 100,
        }
        resp = self.client.post(
            "/api/v1/anagrafiche/ruoli/10/indirizzi/",
            data=json.dumps({
                "tipo_indirizzo_codice": "RES",
                "indirizzo_dettaglio_id": 100,
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["id"], 50)
        mock_repo.crea_indirizzo_ruolo.assert_called_once_with(
            10, {"tipo_indirizzo_codice": "RES", "indirizzo_dettaglio_id": 100},
        )

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC_REPO)
    def test_create_indirizzo_ruolo_with_istanza(self, mock_repo_cls, _auth):
        """POST con istanza_utility_id — crea indirizzo specifico istanza."""
        mock_repo = mock_repo_cls.return_value
        mock_repo.crea_indirizzo_ruolo.return_value = {
            "id": 51, "soggetto_ruolo_id": 10, "tipo_indirizzo_id": 1,
            "istanza_utility_id": 5, "indirizzo_dettaglio_id": 100,
        }
        resp = self.client.post(
            "/api/v1/anagrafiche/ruoli/10/indirizzi/",
            data=json.dumps({
                "tipo_indirizzo_codice": "RES",
                "indirizzo_dettaglio_id": 100,
                "istanza_utility_id": 5,
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["istanza_utility_id"], 5)
        self.assertEqual(mock_repo.crea_indirizzo_ruolo.call_args.args[1]["istanza_utility_id"], 5)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC_REPO)
    def test_create_indirizzo_ruolo_libero(self, mock_repo_cls, _auth):
        """POST con indirizzo_libero — crea indirizzo in modalita' libera."""
        mock_repo = mock_repo_cls.return_value
        mock_repo.crea_indirizzo_ruolo.return_value = {
            "id": 52, "soggetto_ruolo_id": 10, "tipo_indirizzo_id": 3,
            "istanza_utility_id": None, "indirizzo_libero": "123 Main St, London",
            "stato_id": 2,
        }
        resp = self.client.post(
            "/api/v1/anagrafiche/ruoli/10/indirizzi/",
            data=json.dumps({
                "tipo_indirizzo_codice": "EST",
                "indirizzo_libero": "123 Main St, London",
                "stato_id": 2,
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["indirizzo_libero"], "123 Main St, London")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC_REPO)
    def test_create_indirizzo_ruolo_senza_tipo_400(self, mock_repo_cls, _auth):
        """POST senza tipo → 400, la madre non si chiama."""
        resp = self.client.post(
            "/api/v1/anagrafiche/ruoli/10/indirizzi/",
            data=json.dumps({"indirizzo_dettaglio_id": 100}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        mock_repo_cls.return_value.crea_indirizzo_ruolo.assert_not_called()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC_REPO)
    def test_update_indirizzo_ruolo_ok(self, mock_repo_cls, _auth):
        """PATCH /anagrafiche/ruoli/{id}/indirizzi/{indirizzo_id}/ — aggiorna."""
        mock_repo = mock_repo_cls.return_value
        mock_repo.update_indirizzo_ruolo.return_value = True
        resp = self.client.patch(
            "/api/v1/anagrafiche/ruoli/10/indirizzi/50/",
            data=json.dumps({"tipo_indirizzo_id": 2}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["data"]["updated"])

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC_REPO)
    def test_update_indirizzo_ruolo_not_found(self, mock_repo_cls, _auth):
        """PATCH indirizzo inesistente → errore."""
        mock_repo = mock_repo_cls.return_value
        mock_repo.update_indirizzo_ruolo.return_value = False
        resp = self.client.patch(
            "/api/v1/anagrafiche/ruoli/10/indirizzi/999/",
            data=json.dumps({"tipo_indirizzo_id": 2}),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, (400, 404, 422))

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC_REPO)
    def test_update_indirizzo_ruolo_chiave_ignota_400(self, mock_repo_cls, _auth):
        """PATCH con una chiave fuori contratto → 400 che la nomina.

        ⛔ Fino al 2026-09-26 il repository la scartava in silenzio (200 senza
        aver scritto il campo); col BB a whitelist rigida sarebbe un 500. Il
        service la ferma prima.
        """
        resp = self.client.patch(
            "/api/v1/anagrafiche/ruoli/10/indirizzi/50/",
            data=json.dumps({"tipo_indirizzo_id": 2, "fonte": "ruolo"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("fonte", json.dumps(resp.json()))
        mock_repo_cls.return_value.update_indirizzo_ruolo.assert_not_called()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_REPO)
    def test_delete_indirizzo_ruolo_ok(self, mock_repo, _auth):
        """DELETE /anagrafiche/ruoli/{id}/indirizzi/{indirizzo_id}/ — elimina."""
        mock_repo.delete_indirizzo_ruolo.return_value = True
        resp = self.client.delete("/api/v1/anagrafiche/ruoli/10/indirizzi/50/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["data"]["deleted"])

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_REPO)
    def test_delete_indirizzo_ruolo_not_found(self, mock_repo, _auth):
        """DELETE indirizzo inesistente → errore."""
        mock_repo.delete_indirizzo_ruolo.return_value = False
        resp = self.client.delete("/api/v1/anagrafiche/ruoli/10/indirizzi/999/")
        self.assertIn(resp.status_code, (400, 404, 422))
