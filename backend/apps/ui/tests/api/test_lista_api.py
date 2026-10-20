# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke test API personalizzazioni liste — verifica routing,
#        delega ai service, envelope risposta. Service mockati per
#        evitare round-trip DB (CI senza DB reale).
#
# Indice test (0..N):
#   0. get_config_envelope_corretto
#   1. get_config_richiede_jwt
#   2. get_catalogo_envelope_corretto
#   3. put_preferenza_idempotency_key_obbligatoria
#   4. put_preferenza_happy_path_con_idempotency_key
#   5. delete_preferenza_envelope_corretto
#   6. post_ignore_preset_update_envelope_corretto (DEF-2)
#   7. post_ignore_preset_update_richiede_jwt (DEF-2)
#   8. post_ignore_preset_update_richiede_idempotency_key (DEF-2)
#   9. get_misure_pagina_envelope_corretto
#  10. get_misure_pagina_richiede_jwt
# ------------------------------------------------------------

from __future__ import annotations

import json
from unittest.mock import patch

from django.test import Client

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest


# Path mock di PermissionResolver lato view (skip_area_check abilitato ma
# DomainAPIView legge comunque `is_super_admin` per il bypass).
_PERM = "apps.core.api.permissions.PermissionResolver"


class _UserStub:
    """User stub con id stabile per i test API."""

    def __init__(self, user_id: int = 42) -> None:
        self.id = user_id
        self.is_authenticated = True
        self.is_superuser = False


class UiListaApiTests(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()
        # Mocka PermissionResolver per evitare query DB sotto SimpleTestCase.
        self._perm_patcher = patch(_PERM)
        mock_resolver = self._perm_patcher.start()
        # is_super_admin=False -> passa al check area, che skippiamo via
        # skip_area_check=True nelle 3 view.
        mock_resolver.return_value.get_ruolo_applicativo.return_value = "OPERATORE"
        mock_resolver.return_value.is_super_admin.return_value = False
        self.addCleanup(self._perm_patcher.stop)

    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(_UserStub(), None),
    )
    @patch(
        "apps.ui.api.views.UiService.get_lista_config_per_video",
        return_value={
            "colonne": [{"codice": "ragione_sociale", "ordine": 1}],
            "ordinamento": [],
            "filtri": {},
            "pagina_dimensione": 25,
            "colonne_nuove": 0,
        },
    )
    def test_get_config_envelope_corretto(self, mock_svc, _mock_auth) -> None:
        response = self.client.get("/api/v1/ui/liste/anagrafiche.clienti/config/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("data", body)
        self.assertEqual(body["data"]["pagina_dimensione"], 25)
        mock_svc.assert_called_once()

    def test_get_config_richiede_jwt(self) -> None:
        # Senza Authorization header: 401 (DRF default per SimpleJWT).
        response = self.client.get("/api/v1/ui/liste/anagrafiche.clienti/config/")
        self.assertEqual(response.status_code, 401)

    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(_UserStub(), None),
    )
    @patch(
        "apps.ui.api.views.UiService.get_misure_pagina",
        return_value={"misure": [10, 25, 50, 100], "default_compatta": 10, "default_pagina": 25},
    )
    def test_get_misure_pagina_envelope_corretto(self, mock_svc, _mock_auth) -> None:
        response = self.client.get("/api/v1/ui/misure-pagina/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["data"],
            {"misure": [10, 25, 50, 100], "default_compatta": 10, "default_pagina": 25},
        )
        mock_svc.assert_called_once()

    def test_get_misure_pagina_richiede_jwt(self) -> None:
        response = self.client.get("/api/v1/ui/misure-pagina/")
        self.assertEqual(response.status_code, 401)

    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(_UserStub(), None),
    )
    @patch(
        "apps.ui.api.views.UiService.get_catalogo",
        return_value={"colonne": [{"codice": "ragione_sociale"}]},
    )
    def test_get_catalogo_envelope_corretto(self, mock_svc, _mock_auth) -> None:
        response = self.client.get("/api/v1/ui/liste/anagrafiche.clienti/catalogo/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("data", response.json())
        mock_svc.assert_called_once()

    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(_UserStub(), None),
    )
    def test_put_preferenza_idempotency_key_obbligatoria(self, _mock_auth) -> None:
        # Senza Idempotency-Key: 400 con E_IDEMPOTENCY_KEY_MANCANTE
        # (gestito da handle_post_json con require_idempotency_key=True).
        response = self.client.put(
            "/api/v1/ui/liste/anagrafiche.clienti/preferenza/",
            data=json.dumps({"colonne": []}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(_UserStub(), None),
    )
    @patch(
        "apps.ui.api.views.ListaPreferenzaService.upsert",
        return_value={"id": 99, "preset_base_id": 5},
    )
    def test_put_preferenza_happy_path(self, mock_svc, _mock_auth) -> None:
        response = self.client.put(
            "/api/v1/ui/liste/anagrafiche.clienti/preferenza/",
            data=json.dumps(
                {
                    "colonne": [
                        {"codice": "ragione_sociale", "ordine": 1, "visibile": True},
                    ],
                }
            ),
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="11111111-2222-3333-4444-555555555555",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"]["id"], 99)
        mock_svc.assert_called_once()

    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(_UserStub(), None),
    )
    @patch(
        "apps.ui.api.views.ListaPreferenzaService.delete",
        return_value={"deleted": True},
    )
    def test_delete_preferenza_envelope_corretto(
        self, mock_svc, _mock_auth
    ) -> None:
        response = self.client.delete(
            "/api/v1/ui/liste/anagrafiche.clienti/preferenza/",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["data"]["deleted"])
        mock_svc.assert_called_once()

    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(_UserStub(), None),
    )
    @patch(
        "apps.ui.api.views.ListaPreferenzaService.ignore_preset_update",
        return_value={"ignored": True},
    )
    def test_post_ignore_preset_update_envelope_corretto(
        self, mock_svc, _mock_auth
    ) -> None:
        response = self.client.post(
            "/api/v1/ui/liste/anagrafiche.clienti/preferenza/ignore-preset-update/",
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["data"]["ignored"])
        mock_svc.assert_called_once()

    def test_post_ignore_preset_update_richiede_jwt(self) -> None:
        # Senza Authorization header: 401 (DRF default per SimpleJWT).
        response = self.client.post(
            "/api/v1/ui/liste/anagrafiche.clienti/preferenza/ignore-preset-update/",
        )
        self.assertEqual(response.status_code, 401)

    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(_UserStub(), None),
    )
    def test_post_ignore_preset_update_richiede_idempotency_key(
        self, _mock_auth,
    ) -> None:
        # Senza Idempotency-Key: 400 (handle_post_json con
        # require_idempotency_key=True).
        response = self.client.post(
            "/api/v1/ui/liste/anagrafiche.clienti/preferenza/ignore-preset-update/",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
