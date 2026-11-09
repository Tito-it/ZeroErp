# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke test HTTP di GET /amm-software/processi/vocabolari/ — le classi
#        e i canali con cui il pannello costruisce i filtri. Nessun database:
#        la risposta sono le costanti del service.
# Note: ⛔ Perche' esiste (2026-11-09). Il frontend teneva una copia a mano dei
#        canali, senza presidio, e le mancava `CODA_AUTOMATICA`. Ora le tendine
#        leggono da qui, e qui si pinna che si leggano le STESSE costanti con
#        cui la lista rifiuta un filtro (quelle che il guardrail
#        `test_coda_lavori_tipi_handler_guardrail` confronta coi CHECK).
#        ⚠️ La rotta sta sotto `processi/`, dove `<str:codice>/` prende tutto:
#        il test 2 pinna che `vocabolari/` arrivi a QUESTA view.
#
# Indice test:
#   1. senza JWT -> 401
#   2. la view e' una AdminAPIView, e la rotta porta a QUESTA view (non al
#      dettaglio processo)
#   3. ok -> 200 {classi, canali}, uguali alle costanti di validazione
# ------------------------------------------------------------
from unittest.mock import Mock, patch

from django.test import Client
from django.urls import resolve

from apps.amm_software.api.views import ProcessiDetailView, ProcessiVocabolariView
from apps.core.api.base_views import AdminAPIView
from apps.core.services import processi_service
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_URL = "/api/v1/amm-software/processi/vocabolari/"


# Scopo: un superuser: `AdminAPIView` lo fa passare da `is_superuser`.
def _mock_user() -> Mock:
    return Mock(id=9, username="op9", is_superuser=True, is_authenticated=True)


class ProcessiVocabolariApiTests(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    # 1. Senza JWT -> 401.
    def test_richiede_jwt(self) -> None:
        self.assertEqual(self.client.get(_URL).status_code, 401)

    # 2. La porta e' `AdminAPIView`, e la rotta porta a QUESTA view.
    def test_porta_admin_e_rotta(self) -> None:
        self.assertTrue(issubclass(ProcessiVocabolariView, AdminAPIView))
        match = resolve(_URL)
        self.assertIs(match.func.view_class, ProcessiVocabolariView)
        self.assertIsNot(match.func.view_class, ProcessiDetailView)

    # 3. Le costanti di validazione, non una copia.
    @patch(_AUTH, return_value=(_mock_user(), None))
    def test_ok_le_costanti_della_validazione(self, _auth) -> None:
        resp = self.client.get(_URL)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["data"], {
            "classi": list(processi_service._CLASSI),
            "canali": list(processi_service._CANALI),
        })
