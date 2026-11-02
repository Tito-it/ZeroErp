# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
 4) test_modalita_pricing_contratto_removed — 404 (endpoint rimosso post refactor 2026-05-15)
 5) test_listini_selezionabili_ok — 200, envelope {"results": [...]} con {id, codice, descrizione}, utility ed emittente passati al service
 5b) test_listini_selezionabili_senza_parametri — assenti: None al service (il DB risponde nessun listino)
 5c) test_listini_selezionabili_parametro_non_numerico_400 — 400 E_VALIDATION_INPUT (non un id a caso), il service non si chiama
 5d) test_listini_selezionabili_fuori_dal_tipo_400 — oltre integer (utility) o bigint (emittente): 400, non il 500 del DB
 6) test_lookup_richiede_jwt           — 401 senza autenticazione
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

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(
        "apps.vendite.api.views_lookups.fn_list_listini_selezionabili",
        return_value=[
            {"id": 7, "codice": "LST-A", "descrizione": "Listino A"},
            {"id": 9, "codice": "LST-B", "descrizione": "Listino B"},
        ],
    )
    def test_listini_selezionabili_ok(self, _service, _auth):
        # La view trasporta la lettura del DB per utility ed emittente del
        # form (F-2.3 di brief-db-offerta-emissione-ed-erogazione). Service
        # mockato: niente DB (CI).
        resp = self.client.get(
            "/api/v1/vendite/lookup/listini-selezionabili/"
            "?utility_id=3&emittente_fiscale_id=41",
            HTTP_AUTHORIZATION="Bearer x",
        )
        self.assertEqual(resp.status_code, 200)
        # ⛔ L'envelope dei lookup e' `{"results": [...]}`, non la lista nuda:
        # `useLookup`/`useGlobalLookup` leggono `data.results` di default.
        rows = resp.json()["data"]["results"]
        self.assertEqual(len(rows), 2)
        self.assertEqual(set(rows[0].keys()), {"id", "codice", "descrizione"})
        self.assertEqual([r["codice"] for r in rows], ["LST-A", "LST-B"])
        _service.assert_called_once_with(3, 41)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(
        "apps.vendite.api.views_lookups.fn_list_listini_selezionabili",
        return_value=[],
    )
    def test_listini_selezionabili_senza_parametri(self, _service, _auth):
        # Utility ed emittente assenti (form ancora vuoto): la view non
        # inventa un rifiuto, passa None e il DB risponde «nessun listino».
        resp = self.client.get(
            "/api/v1/vendite/lookup/listini-selezionabili/",
            HTTP_AUTHORIZATION="Bearer x",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["results"], [])
        _service.assert_called_once_with(None, None)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch("apps.vendite.api.views_lookups.fn_list_listini_selezionabili")
    def test_listini_selezionabili_parametro_non_numerico_400(
        self, _service, _auth,
    ):
        for nome, query in (
            ("utility_id", "utility_id=abc&emittente_fiscale_id=41"),
            ("emittente_fiscale_id", "utility_id=3&emittente_fiscale_id=x"),
        ):
            with self.subTest(campo=nome):
                resp = self.client.get(
                    f"/api/v1/vendite/lookup/listini-selezionabili/?{query}",
                    HTTP_AUTHORIZATION="Bearer x",
                )
                self.assertEqual(resp.status_code, 400)
                err = resp.json()["error"]
                self.assertEqual(err["code"], "E_VALIDATION_INPUT")
                # Niente `fields`: una query string non e' un input del form
                # (api.md §Envelope, `highlight_form_fields`).
        _service.assert_not_called()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch("apps.vendite.api.views_lookups.fn_list_listini_selezionabili")
    def test_listini_selezionabili_fuori_dal_tipo_400(self, _service, _auth):
        # `fn_listini_selezionabili(integer, bigint)`: un numero oltre il tipo
        # arriva a DB come bigint/numeric, la funzione non si risolve → 500.
        for nome, query in (
            ("utility_id", "utility_id=2147483648&emittente_fiscale_id=41"),
            ("emittente_fiscale_id", "utility_id=3&emittente_fiscale_id=9223372036854775808"),
        ):
            with self.subTest(campo=nome):
                resp = self.client.get(
                    f"/api/v1/vendite/lookup/listini-selezionabili/?{query}",
                    HTTP_AUTHORIZATION="Bearer x",
                )
                self.assertEqual(resp.status_code, 400)
                self.assertEqual(resp.json()["error"]["code"], "E_VALIDATION_INPUT")
        _service.assert_not_called()

    def test_lookup_richiede_jwt(self):
        # Senza Authorization header -> 401 (DomainAPIView richiede JWT).
        resp = self.client.get("/api/v1/vendite/lookup/ambiti-contratto/")
        self.assertEqual(resp.status_code, 401)
