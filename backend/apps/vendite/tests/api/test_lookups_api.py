# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke test endpoint lookup statici vendite (Fase 2 refactor frontend).
#        Mock JWT, niente DB. Verifica solo envelope + chiavi base; le
#        invarianti enum sono coperte da test_vendite_lookups_service.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_tipi_variazione_contratto_ok — 200 con codice PERCENTUALE (post 2026-05-18 §3-bis-E: VALORE_FISSO rimosso dalla testata)
 2) test_tipi_variazione_promo_ok     — 200, include PREZZO_FISSO
 3) test_ambiti_contratto_ok          — 200 con codici COMMODITY/COMMERCIO
 4) test_modalita_pricing_contratto_ok — 200 con codici A/B/C
 5) test_lookup_richiede_jwt           — 401 senza autenticazione
"""

from unittest.mock import Mock, patch

from django.test import Client

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest


_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_PERM = "apps.core.api.permissions.PermissionResolver"


class TestVenditeLookupsApi(JwtMockedApiTest):

    def setUp(self) -> None:
        super().setUp()
        self.client = Client()
        # Permesso area vendite LETTURA: i lookup statici non richiedono di
        # piu'. PermissionResolver.get_livello_area mockato a TUTTO.
        self._perm_patcher = patch(_PERM)
        mock_resolver = self._perm_patcher.start()
        mock_resolver.return_value.get_livello_area.return_value = "TUTTO"
        mock_resolver.return_value.is_super_admin.return_value = False
        mock_resolver.return_value.get_ruolo_applicativo.return_value = "OPERATORE"
        self.addCleanup(self._perm_patcher.stop)

    def _codes(self, response):
        return [row["codice"] for row in response.json()["data"]]

    @patch(_AUTH, return_value=(Mock(), None))
    def test_tipi_variazione_contratto_ok(self, _auth):
        resp = self.client.get(
            "/api/v1/vendite/lookup/tipi-variazione-contratto/",
            HTTP_AUTHORIZATION="Bearer x",
        )
        self.assertEqual(resp.status_code, 200)
        codes = self._codes(resp)
        # Refactor 2026-05-18 §3-bis-E: solo PERCENTUALE come variazione
        # globale sulla testata. VALORE_FISSO resta ammesso unicamente per
        # OVERRIDE su singola riga (semantica "prezzo fisso sostitutivo").
        self.assertIn("PERCENTUALE", codes)
        self.assertNotIn("VALORE_FISSO", codes)
        self.assertNotIn("PREZZO_FISSO", codes)

    @patch(_AUTH, return_value=(Mock(), None))
    def test_tipi_variazione_promo_ok(self, _auth):
        resp = self.client.get(
            "/api/v1/vendite/lookup/tipi-variazione-promo/",
            HTTP_AUTHORIZATION="Bearer x",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("PREZZO_FISSO", self._codes(resp))

    @patch(_AUTH, return_value=(Mock(), None))
    def test_ambiti_contratto_ok(self, _auth):
        resp = self.client.get(
            "/api/v1/vendite/lookup/ambiti-contratto/",
            HTTP_AUTHORIZATION="Bearer x",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(set(self._codes(resp)), {"COMMODITY", "COMMERCIO"})

    @patch(_AUTH, return_value=(Mock(), None))
    def test_modalita_pricing_contratto_removed(self, _auth):
        # Refactor modalita 2026-05-15: l'endpoint modalita-pricing-contratto
        # e' stato rimosso (la modalita non e' piu' una scelta utente).
        resp = self.client.get(
            "/api/v1/vendite/lookup/modalita-pricing-contratto/",
            HTTP_AUTHORIZATION="Bearer x",
        )
        self.assertEqual(resp.status_code, 404)

    def test_lookup_richiede_jwt(self):
        # Senza Authorization header -> 401 (DomainAPIView richiede JWT).
        resp = self.client.get("/api/v1/vendite/lookup/ambiti-contratto/")
        self.assertEqual(resp.status_code, 401)
