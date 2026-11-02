# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test API della lista contatti a livello ruolo (GET), sul solo parametro
#        `istanza_utility_id`: si legge prima di qualunque accesso al database,
#        quindi nessun mock del DB serve (compatibilita CI).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_istanza_non_intera_400 — `istanza_utility_id=abc` e' un 400, non un 500
"""

from unittest.mock import Mock, patch

from django.test import Client

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"


class TestContattiRuoloApi(JwtMockedApiTest):
    """GET /anagrafiche/ruoli/{id}/contatti/: il parametro dell'istanza."""

    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    # 1. Fino al 2026-10-09 il valore passava per un `int()` grezzo: un
    #    `ValueError` non tradotto, cioe' un 500 (trovato da mypy). Ora e' il
    #    BB `qp_int_optional`, e il rifiuto e' un 400 che nomina il campo.
    @patch(_AUTH, return_value=(Mock(), None))
    def test_istanza_non_intera_400(self, _auth):
        resp = self.client.get("/api/v1/anagrafiche/ruoli/10/contatti/?istanza_utility_id=abc")
        self.assertEqual(resp.status_code, 400)
