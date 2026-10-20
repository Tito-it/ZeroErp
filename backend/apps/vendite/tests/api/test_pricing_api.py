# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test API endpoint diagnostico pricing v5
#        (POST /api/v1/vendite/pricing/resolve/).
#        Mock PricingService + JWT mockata. Nessun DB.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_resolve_ok_deriva_emittente_da_jwt
 2) test_resolve_ok_override_emittente
 3) test_resolve_requires_jwt
 4) test_resolve_payload_invalido_400
 5) test_resolve_senza_emittente_user_404
 6) test_resolve_propaga_service_error
 7) test_limiti_utente_ritorna_defaults — endpoint L2 con default parametri
 8) test_limiti_utente_con_override_user — endpoint L2 con override utente
 9) test_limiti_utente_ba_malformato_400 — billing_account_id non numerico → 400 (F-6)
10) test_limiti_utente_ba_non_risulta_404 — BA inesistente o fuori scope → 404 (F-6)
11) test_resolve_e_diagnose_id_obbligatori_assenti_400 — uom/ba/utility assenti: 400 sul campo, resolver non chiamato
"""

import json
from decimal import Decimal
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import Client

from apps.core.services.service_errors import ServiceError
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest


_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_SVC = "apps.vendite.api.views_pricing.PricingService"
_PERM = "apps.vendite.api.views_pricing.PermissionResolver"
_BASE = "/api/v1/vendite/pricing/resolve/"


class _BaseApiTest(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()

    def _payload(self, **overrides):
        base = {
            "articolo_id": "11111111-2222-3333-4444-555555555555",
            "uom_id": 1,
            "data_riferimento": "2026-04-15",
            "ba_id": 10,
            "utility_id": 3,
        }
        base.update(overrides)
        return base

    def _mock_resolve_result(self):
        # Valori rappresentativi coerenti con la firma del resolver v2.
        return {
            "prezzo_finale": Decimal("45.00"),
            "prezzo_base_snapshot": Decimal("50.00"),
            "tipo_variazione_applicata": "PERCENTUALE",
            "valore_variazione_applicata": Decimal("-10.00"),
            "origine": "CATEGORIA",
            "listino_id": 100,
            "listino_versione_id": 10,
            "listino_riga_id": 1000,
            "contratto_id": None,
            "promo_id": None,
            "categoria_cliente_listino_id": 5,
            "categoria_cliente_id_snapshot": 3,
            "classe_utenza_id_snapshot": None,
        }


class TestResolve(_BaseApiTest):
    # Scopo: risoluzione con emittente derivato dal JWT operatore.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM)
    @patch(_SVC)
    def test_resolve_ok_deriva_emittente_da_jwt(self, svc_cls, perm, _auth):
        perm.get_emittenti_sr_ids.return_value = [42]
        svc_cls.return_value.resolve_prezzo.return_value = self._mock_resolve_result()

        resp = self.client.post(
            _BASE,
            data=json.dumps(self._payload()),
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 200)
        body = resp.json()["data"]
        self.assertEqual(body["origine"], "CATEGORIA")
        # Il service deve essere stato chiamato con emittente derivato (42).
        kwargs = svc_cls.return_value.resolve_prezzo.call_args.kwargs
        self.assertEqual(kwargs["emittente_soggetto_ruolo_id"], 42)
        self.assertEqual(kwargs["ba_id"], 10)

    # Scopo: override esplicito ha priorita' sulla derivazione da JWT.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM)
    @patch(_SVC)
    def test_resolve_ok_override_emittente(self, svc_cls, perm, _auth):
        perm.get_emittenti_sr_ids.return_value = [42]  # ignorato
        svc_cls.return_value.resolve_prezzo.return_value = self._mock_resolve_result()

        resp = self.client.post(
            _BASE,
            data=json.dumps(self._payload(emittente_soggetto_ruolo_id=99)),
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 200)
        kwargs = svc_cls.return_value.resolve_prezzo.call_args.kwargs
        self.assertEqual(kwargs["emittente_soggetto_ruolo_id"], 99)

    # Scopo: senza JWT ritorna 401.
    def test_resolve_requires_jwt(self):
        resp = self.client.post(
            _BASE,
            data=json.dumps(self._payload()),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)

    # Scopo: payload malformato (articolo_id mancante) ritorna 400.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM)
    def test_resolve_payload_invalido_400(self, perm, _auth):
        perm.get_emittenti_sr_ids.return_value = [42]
        payload = self._payload()
        del payload["articolo_id"]

        resp = self.client.post(
            _BASE,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    # Scopo: ⛔ i tre id obbligatori assenti sono un 400 sul campo, prima del
    #        resolver. Fino al 2026-10-20 `int(x or 0)` li faceva diventare 0, e
    #        il DB rispondeva con un errore generico invece che sul campo.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM)
    @patch("apps.vendite.api.views_pricing.PricingDiagnoseService")
    @patch(_SVC)
    def test_resolve_e_diagnose_id_obbligatori_assenti_400(self, svc_cls, diag_cls, perm, _auth):
        perm.get_emittenti_sr_ids.return_value = [42]
        for url in (_BASE, "/api/v1/vendite/pricing/diagnose/"):
            for campo in ("uom_id", "ba_id", "utility_id"):
                payload = self._payload()
                del payload[campo]
                with self.subTest(url=url, campo=campo):
                    resp = self.client.post(
                        url, data=json.dumps(payload), content_type="application/json",
                    )
                    self.assertEqual(resp.status_code, 400)
                    errore = resp.json()["error"]
                    self.assertEqual(errore["code"], "E_VENDITE_VALIDATION")
                    self.assertIn(campo, json.dumps(errore))
        svc_cls.return_value.resolve_prezzo.assert_not_called()
        diag_cls.return_value.diagnose.assert_not_called()

    # Scopo: `data_riferimento` vuota e' come assente: 400 col campo, senza
    #        arrivare al resolver. Fino al 2026-10-09 il controllo era sul valore
    #        grezzo, e `""` passava (trovato da mypy).
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM)
    @patch("apps.vendite.api.views_pricing.PricingService")
    def test_resolve_data_riferimento_vuota_400(self, svc_cls, perm, _auth):
        perm.get_emittenti_sr_ids.return_value = [42]
        resp = self.client.post(
            _BASE,
            data=json.dumps(self._payload(data_riferimento="")),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("data_riferimento", resp.json()["error"].get("fields") or [])
        svc_cls.return_value.resolve_prezzo.assert_not_called()

    # Scopo: user senza emittenti autorizzati e senza override -> 400 parlante.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM)
    def test_resolve_senza_emittente_user_400(self, perm, _auth):
        perm.get_emittenti_sr_ids.return_value = []

        resp = self.client.post(
            _BASE,
            data=json.dumps(self._payload()),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertEqual(body["error"]["code"], "E_VENDITE_VALIDATION")

    # Scopo: ServiceError del service (es. E_CATEGORIA_LISTINO_NON_MAPPATA)
    #        propagato dal middleware come error envelope col codice originale.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM)
    @patch(_SVC)
    def test_resolve_propaga_service_error(self, svc_cls, perm, _auth):
        perm.get_emittenti_sr_ids.return_value = [42]
        svc_cls.return_value.resolve_prezzo.side_effect = ServiceError(
            code="E_CATEGORIA_LISTINO_NON_MAPPATA",
            message="Nessuna mappa categoria -> listino per utility",
        )

        resp = self.client.post(
            _BASE,
            data=json.dumps(self._payload()),
            content_type="application/json",
        )
        # Il mapping codice->status dipende da error_policies; qui ci basta
        # verificare che il codice dominio arrivi intatto al client.
        self.assertIn(resp.status_code, (400, 404, 409, 500))
        body = resp.json()
        self.assertEqual(body["error"]["code"], "E_CATEGORIA_LISTINO_NON_MAPPATA")


_LIMITI_BASE = "/api/v1/vendite/pricing/limiti-utente/"
_LIMITI_PS = "apps.vendite.api.views_pricing.ParameterService"


class TestLimitiUtente(_BaseApiTest):
    # Scopo: endpoint ritorna i default "0/0" quando nessun override.
    #        Post-ottimizzazione O1 usa get_defaults (single round-trip).
    @patch(_AUTH, return_value=(Mock(id=1), None))
    @patch(_LIMITI_PS)
    def test_limiti_utente_ritorna_defaults(self, ps_cls, _auth):
        ps_cls.return_value.get_defaults.return_value = {
            "VENDITE_MAX_SCONTO_PCT": "0",
            "VENDITE_MAX_MAGGIORAZIONE_PCT": "0",
        }

        resp = self.client.get(_LIMITI_BASE)

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["data"]["max_sconto_pct"], "0")
        self.assertEqual(body["data"]["max_maggiorazione_pct"], "0")
        ps_cls.return_value.get_defaults.assert_called_once()

    # Scopo: endpoint rispecchia gli override user risolti dal service.
    @patch(_AUTH, return_value=(Mock(id=42), None))
    @patch(_LIMITI_PS)
    def test_limiti_utente_con_override_user(self, ps_cls, _auth):
        ps_cls.return_value.get_defaults.return_value = {
            "VENDITE_MAX_SCONTO_PCT": "15",
            "VENDITE_MAX_MAGGIORAZIONE_PCT": "5",
        }

        resp = self.client.get(_LIMITI_BASE)

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["data"]["max_sconto_pct"], "15")
        self.assertEqual(body["data"]["max_maggiorazione_pct"], "5")

    # Scopo: senza billing_account_id il livello categoria_cliente della
    # cascata viene saltato (categoria_cliente_id=None).
    @patch(_AUTH, return_value=(Mock(id=1), None))
    @patch(_LIMITI_PS)
    def test_limiti_utente_senza_ba_categoria_none(self, ps_cls, _auth):
        ps_cls.return_value.get_defaults.return_value = {
            "VENDITE_MAX_SCONTO_PCT": "10",
            "VENDITE_MAX_MAGGIORAZIONE_PCT": "10",
        }

        resp = self.client.get(_LIMITI_BASE)

        self.assertEqual(resp.status_code, 200)
        _, kwargs = ps_cls.return_value.get_defaults.call_args
        self.assertIsNone(kwargs.get("categoria_cliente_id"))

    # Scopo: con billing_account_id la view recupera la categoria del BA
    # via BillingAccountRepository e la propaga a ParameterService.
    @patch("apps.anagrafiche.services.billing_account_service.BillingAccountRepository")
    @patch(_AUTH, return_value=(Mock(id=1), None))
    @patch(_LIMITI_PS)
    def test_limiti_utente_con_ba_propaga_categoria(self, ps_cls, _auth, ba_cls):
        ba_cls.return_value.get_categoria_cliente_id.return_value = 7
        ps_cls.return_value.get_defaults.return_value = {
            "VENDITE_MAX_SCONTO_PCT": "5",
            "VENDITE_MAX_MAGGIORAZIONE_PCT": "5",
        }

        resp = self.client.get(_LIMITI_BASE + "?billing_account_id=99")

        self.assertEqual(resp.status_code, 200)
        ba_cls.return_value.get_categoria_cliente_id.assert_called_once_with(99)
        _, kwargs = ps_cls.return_value.get_defaults.call_args
        self.assertEqual(kwargs.get("categoria_cliente_id"), 7)

    # Scopo: billing_account_id malformato (non numerico) → 400
    # E_VALIDATION_INPUT, niente lookup BA (F-6, 2026-10-08: prima veniva
    # ignorato in silenzio e il drawer mostrava la soglia generica).
    @patch("apps.anagrafiche.services.billing_account_service.BillingAccountRepository")
    @patch(_AUTH, return_value=(Mock(id=1), None))
    @patch(_LIMITI_PS)
    def test_limiti_utente_ba_malformato_400(self, ps_cls, _auth, ba_cls):
        resp = self.client.get(_LIMITI_BASE + "?billing_account_id=abc")

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"]["code"], "E_VALIDATION_INPUT")
        ba_cls.return_value.get_categoria_cliente_id.assert_not_called()
        ps_cls.return_value.get_defaults.assert_not_called()

    # Scopo: BA che non risulta (inesistente o fuori scope RLS) → 404
    # E_ANAG_NOT_FOUND, non la soglia senza livello categoria (F-6).
    @patch("apps.anagrafiche.services.billing_account_service.BillingAccountRepository")
    @patch(_AUTH, return_value=(Mock(id=1), None))
    @patch(_LIMITI_PS)
    def test_limiti_utente_ba_non_risulta_404(self, ps_cls, _auth, ba_cls):
        ba_cls.return_value.get_categoria_cliente_id.return_value = None

        resp = self.client.get(_LIMITI_BASE + "?billing_account_id=99")

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"]["code"], "E_ANAG_NOT_FOUND")
        ps_cls.return_value.get_defaults.assert_not_called()
