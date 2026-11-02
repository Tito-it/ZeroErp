# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test dell'endpoint di anteprima IVA
#        (POST /api/v1/vendite/iva/resolve/). Service e JWT mockati,
#        nessun DB.
#
# Indice test eseguiti:
#  1) test_anteprima_ok_deriva_emittente_dall_operatore
#  2) test_senza_emittente_non_ripiega_ma_si_ferma        ⛔ il caso che conta
#  3) test_il_payload_non_espone_quota
#  4) test_articolo_obbligatorio
#  5) test_richiede_jwt
#  6) test_usa_l_anteprima_e_non_la_ripartizione          ⛔ P1 nel contratto
#  7) test_il_contesto_viene_dal_documento_non_dal_client ⛔ opzione «c»
# ------------------------------------------------------------

import json
from decimal import Decimal
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import Client

from apps.core.services.service_errors import ServiceError
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

from datetime import date

_DATA = date(2026, 8, 31)

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_SVC = "apps.vendite.api.views_iva.IvaResolverService"
_CARICA = "apps.vendite.api.views_iva.carica_testata"
_CTX = "apps.vendite.api.views_iva.contesto_da_testata"
_BASE = "/api/v1/vendite/iva/resolve/"


class _BaseApiTest(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()

    def _payload(self, **overrides):
        # ⭐ Il client manda le COORDINATE del documento e nient'altro: il
        #    contesto lo deriva il backend dalla testata (opzione «c»).
        base = {
            "articolo_id": "11111111-2222-3333-4444-555555555555",
            "documento_tipo": "PREVENTIVO",
            "documento_id": 7,
        }
        base.update(overrides)
        return base

    def _parte(self):
        return {
            "quota": None,
            "iva_id": 3,
            "aliquota": Decimal("22.00"),
            "natura_codice": None,
            "is_reverse_charge": False,
            "esigibilita": "I",
            "split_payment": False,
            "riferimento_normativo": "Aliquota I.V.A. al 22%",
            "origine": "ARTICOLO",
            "titolo_iva_id": None,
        }


class TestIvaResolve(_BaseApiTest):
    # Scopo: il giro normale — l'emittente non lo passa il client, lo deriva
    #        il backend dall'operatore.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_CTX)
    @patch(_CARICA)
    @patch(_SVC)
    def test_anteprima_ok_deriva_emittente_dall_operatore(self, svc_cls, carica, ctx, _auth):
        ctx.return_value = {"emittente_fiscale_id": 44, "billing_account_id": 10,
                            "utility_id": 5, "data_riferimento": _DATA}
        svc_cls.return_value.risolvi_anteprima.return_value = self._parte()

        resp = self.client.post(
            _BASE, data=json.dumps(self._payload()), content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()["data"]
        self.assertEqual(body["iva_id"], 3)
        self.assertEqual(body["origine"], "ARTICOLO")
        # ⛔ La PK dell'emittente, non il soggetto_ruolo_id: con quello
        #    sbagliato il risolutore non trova i titoli e risponde con
        #    l'aliquota ordinaria, senza sollevare.
        kwargs = svc_cls.return_value.risolvi_anteprima.call_args.kwargs
        self.assertEqual(kwargs["emittente_fiscale_id"], 44)

    # Scopo: ⛔ IL CASO CHE CONTA (P3). Senza emittente il risolutore NON
    #        sbaglia: legge zero titoli sotto RLS e risponde con l'aliquota
    #        ordinaria. Il difetto non ha sintomi — una riga semplicemente
    #        sbagliata — quindi l'endpoint deve FERMARSI, non chiamare.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_CTX)
    @patch(_CARICA)
    @patch(_SVC)
    def test_senza_emittente_non_ripiega_ma_si_ferma(self, svc_cls, carica, ctx, _auth):
        ctx.side_effect = ServiceError(code="E_VENDITE_VALIDATION",
                                       message="emittente non risolvibile")

        resp = self.client.post(
            _BASE, data=json.dumps(self._payload()), content_type="application/json",
        )
        self.assertGreaterEqual(resp.status_code, 400)
        svc_cls.return_value.risolvi_anteprima.assert_not_called()

    # Scopo: ⚠️ `quota` in anteprima vale SEMPRE `NULL` — la spezzatura non e'
    #        calcolabile senza importo. Un campo sempre nullo nel payload e'
    #        una promessa che qualcuno prima o poi prova a leggere.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_CTX)
    @patch(_CARICA)
    @patch(_SVC)
    def test_il_payload_non_espone_quota(self, svc_cls, carica, ctx, _auth):
        ctx.return_value = {"emittente_fiscale_id": 44, "billing_account_id": 10,
                            "utility_id": 5, "data_riferimento": _DATA}
        svc_cls.return_value.risolvi_anteprima.return_value = self._parte()

        resp = self.client.post(
            _BASE, data=json.dumps(self._payload()), content_type="application/json",
        )
        self.assertNotIn("quota", resp.json()["data"])

    # Scopo: ⛔ P1 SCRITTO NEL CONTRATTO. Sui documenti la riga non si spezza,
    #        e il modo solido di tenerlo non e' ricordarselo: e' che il client
    #        non abbia il parametro con cui romperlo. Anche mandando un
    #        imponibile, l'endpoint chiama l'ANTEPRIMA — che quel parametro
    #        non ce l'ha.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_CTX)
    @patch(_CARICA)
    @patch(_SVC)
    def test_usa_l_anteprima_e_non_la_ripartizione(self, svc_cls, carica, ctx, _auth):
        ctx.return_value = {"emittente_fiscale_id": 44, "billing_account_id": 10,
                            "utility_id": 5, "data_riferimento": _DATA}
        svc_cls.return_value.risolvi_anteprima.return_value = self._parte()

        self.client.post(
            _BASE, data=json.dumps(self._payload(imponibile="1000.00")),
            content_type="application/json",
        )
        svc_cls.return_value.risolvi.assert_not_called()
        kwargs = svc_cls.return_value.risolvi_anteprima.call_args.kwargs
        self.assertNotIn("imponibile", kwargs)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_CTX)
    @patch(_CARICA)
    @patch(_SVC)
    def test_articolo_obbligatorio(self, svc_cls, carica, ctx, _auth):
        ctx.return_value = {"emittente_fiscale_id": 44, "billing_account_id": 10,
                            "utility_id": 5, "data_riferimento": _DATA}
        payload = self._payload()
        payload.pop("articolo_id")

        resp = self.client.post(
            _BASE, data=json.dumps(payload), content_type="application/json",
        )
        self.assertGreaterEqual(resp.status_code, 400)
        svc_cls.return_value.risolvi_anteprima.assert_not_called()

    def test_richiede_jwt(self):
        resp = self.client.post(
            _BASE, data=json.dumps(self._payload()), content_type="application/json",
        )
        self.assertIn(resp.status_code, (401, 403))

    # Scopo: ⭐ IL CONTESTO VIENE DAL DOCUMENTO (opzione «c», Tid 2026-08-31).
    #        Il client manda solo le coordinate; emittente, billing account,
    #        utility e data li deriva il backend dalla TESTATA — la stessa che
    #        leggera' al salvataggio.
    # ⛔ Il caso che questo previene non e' un errore: e' un DISACCORDO. Con il
    #    contesto preso dal client, l'anteprima poteva rispondere per un
    #    billing account o una data diversi da quelli del documento, e
    #    l'operatore avrebbe visto un numero ottenendone un altro.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_CARICA)
    @patch(_CTX)
    @patch(_SVC)
    def test_il_contesto_viene_dal_documento_non_dal_client(
        self, svc_cls, ctx, carica, _auth,
    ):
        ctx.return_value = {
            "emittente_fiscale_id": 44, "billing_account_id": 10,
            "utility_id": 5, "data_riferimento": _DATA,
        }
        svc_cls.return_value.risolvi_anteprima.return_value = self._parte()

        # Il client prova a dettare un contesto suo: deve essere IGNORATO.
        self.client.post(
            _BASE,
            data=json.dumps(self._payload(
                billing_account_id=999, data_riferimento="1999-01-01",
            )),
            content_type="application/json",
        )

        carica.assert_called_once()
        self.assertEqual(carica.call_args.kwargs["documento_tipo"], "PREVENTIVO")
        self.assertEqual(carica.call_args.kwargs["documento_id"], 7)
        kwargs = svc_cls.return_value.risolvi_anteprima.call_args.kwargs
        self.assertEqual(kwargs["billing_account_id"], 10)
        self.assertEqual(kwargs["data_riferimento"], _DATA)

