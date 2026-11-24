# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: la misura di partenza del BB `apps.core.services.ordinamento_di_partenza`
#        (BE10 di brief-db-revisione-ui, 2026-11-22): una GET di lista
#        configurabile senza `limit` pagina con le righe per pagina della
#        configurazione della lista (`misura_risolta`, su `ui.fn_misura_lista`),
#        non con `DEFAULT_LIMIT`. La misura oltre il tetto della view si riporta
#        al tetto con un warning; un `limit` del client resta suo, e oltre il
#        tetto resta un 400.
# Note: ⭐ Senza DB: la lettura (`misura_risolta`) e' finta, il BB e
#       `pagina_da_query` girano davvero, su una richiesta DRF vera e su una
#       view vera. La lettura sul DB vero la prova
#       `apps/ui/tests/db/test_misura_lista_db.py`.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) MisuraDiPartenzaTests.test_senza_limit_vale_la_misura
2) MisuraDiPartenzaTests.test_la_misura_vince_sul_default_della_view
3) MisuraDiPartenzaTests.test_limit_della_richiesta_vince_e_non_legge
4) MisuraDiPartenzaTests.test_le_scritture_non_leggono_la_misura
5) MisuraDiPartenzaTests.test_letta_solo_se_si_pagina_e_una_volta
6) MisuraDiPartenzaTests.test_oltre_il_tetto_si_pagina_col_tetto_e_si_avvisa
7) MisuraDiPartenzaTests.test_limit_del_client_oltre_il_tetto_resta_400
8) MisuraDiPartenzaTests.test_fuori_da_una_lista_vale_il_default
9) MisuraDiPartenzaTests.test_la_misura_si_azzera_alla_richiesta_dopo
10) MisuraDiPartenzaViewVeraTests.test_lista_senza_limit_riceve_la_misura
11) MisuraDiPartenzaViewVeraTests.test_lista_con_limit_resta_sua
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import RequestFactory, SimpleTestCase
from rest_framework.request import Request

from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.api.payload_validators import pagina_da_query
from apps.core.services.ordinamento_di_partenza import applica_misura_di_partenza
from apps.core.services.request_context import set_request_context
from apps.core.tests._helpers.jwt_mock import ClientApi, JwtMockedApiTest

_LETTURA = "apps.core.services.ordinamento_di_partenza.misura_risolta"


def _richiesta(metodo: str = "get", query: str = "") -> Request:
    grezza = getattr(RequestFactory(), metodo)(f"/api/v1/x/{query}")
    richiesta = Request(grezza)
    richiesta.user = SimpleNamespace(id=7, is_authenticated=True)
    return richiesta


class MisuraDiPartenzaTests(SimpleTestCase):
    def setUp(self) -> None:
        set_request_context(request_id=None, idempotency_key=None)
        self.addCleanup(set_request_context, request_id=None, idempotency_key=None)

    def _applica(self, richiesta: Request, misura: int) -> Mock:
        patcher = patch(_LETTURA, return_value=misura)
        lettura = patcher.start()
        self.addCleanup(patcher.stop)
        applica_misura_di_partenza(richiesta, lista_codice="vendite.x")
        return lettura

    def test_senza_limit_vale_la_misura(self) -> None:
        richiesta = _richiesta(query="?offset=10")
        lettura = self._applica(richiesta, 50)
        self.assertEqual(pagina_da_query(richiesta.query_params), (50, 10))
        self.assertEqual(lettura.call_args.args, ("vendite.x",))
        self.assertEqual(lettura.call_args.kwargs["user"].id, 7)

    # ⭐ Tid, 2026-11-22: il `default_limit` di una view con `lista_codice` non
    #    vale piu' (i task run del lotto avevano 100).
    def test_la_misura_vince_sul_default_della_view(self) -> None:
        richiesta = _richiesta()
        self._applica(richiesta, 10)
        self.assertEqual(
            pagina_da_query(richiesta.query_params, default_limit=100, max_limit=500),
            (10, 0),
        )

    def test_limit_della_richiesta_vince_e_non_legge(self) -> None:
        richiesta = _richiesta(query="?limit=7")
        lettura = self._applica(richiesta, 50)
        self.assertEqual(pagina_da_query(richiesta.query_params), (7, 0))
        lettura.assert_not_called()

    def test_le_scritture_non_leggono_la_misura(self) -> None:
        richiesta = _richiesta(metodo="post")
        lettura = self._applica(richiesta, 50)
        self.assertEqual(pagina_da_query(richiesta.query_params), (DEFAULT_LIMIT, 0))
        lettura.assert_not_called()

    # La lettura costa una query: la paga solo chi pagina, e una volta sola.
    def test_letta_solo_se_si_pagina_e_una_volta(self) -> None:
        richiesta = _richiesta()
        lettura = self._applica(richiesta, 50)
        lettura.assert_not_called()
        pagina_da_query(richiesta.query_params)
        pagina_da_query(richiesta.query_params)
        lettura.assert_called_once()

    # Tid, 2026-11-22: un difetto del catalogo, non della richiesta.
    def test_oltre_il_tetto_si_pagina_col_tetto_e_si_avvisa(self) -> None:
        richiesta = _richiesta()
        self._applica(richiesta, 100)
        with self.assertLogs("apps.core.api.payload_validators", level="WARNING") as log:
            self.assertEqual(pagina_da_query(richiesta.query_params, max_limit=50), (50, 0))
        self.assertIn("misura_di_partenza.oltre_il_tetto", log.output[0])

    def test_limit_del_client_oltre_il_tetto_resta_400(self) -> None:
        richiesta = _richiesta(query="?limit=100")
        self._applica(richiesta, 10)
        with self.assertRaises(ValueError) as ctx:
            pagina_da_query(richiesta.query_params, max_limit=50)
        self.assertEqual(str(ctx.exception), "limit_fuori_limiti_1_50")

    def test_fuori_da_una_lista_vale_il_default(self) -> None:
        self.assertEqual(pagina_da_query(_richiesta().query_params), (DEFAULT_LIMIT, 0))

    # Un worker riusa il suo thread: la misura della richiesta prima non vale.
    def test_la_misura_si_azzera_alla_richiesta_dopo(self) -> None:
        self._applica(_richiesta(), 50)
        set_request_context(request_id=None, idempotency_key=None)
        self.assertEqual(pagina_da_query(_richiesta().query_params), (DEFAULT_LIMIT, 0))


_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_SVC_OFFERTE = "apps.vendite.api.views_offerte.OfferteService"


class MisuraDiPartenzaViewVeraTests(JwtMockedApiTest):
    come_super_admin = True
    def setUp(self) -> None:
        super().setUp()
        self.client = ClientApi()
        self.mock_misura_risolta.return_value = 50

    def _limit(self, svc_cls: Mock) -> int:
        return svc_cls.return_value.list_offerte.call_args.kwargs["limit"]

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC_OFFERTE)
    def test_lista_senza_limit_riceve_la_misura(self, svc_cls, _auth) -> None:
        svc_cls.return_value.list_offerte.return_value = ([], 0)
        resp = self.client.get("/api/v1/vendite/offerte/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.mock_misura_risolta.call_args.args[0], "vendite.offerte")
        self.assertEqual(self._limit(svc_cls), 50)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC_OFFERTE)
    def test_lista_con_limit_resta_sua(self, svc_cls, _auth) -> None:
        svc_cls.return_value.list_offerte.return_value = ([], 0)
        resp = self.client.get("/api/v1/vendite/offerte/?limit=10")
        self.assertEqual(resp.status_code, 200)
        self.mock_misura_risolta.assert_not_called()
        self.assertEqual(self._limit(svc_cls), 10)
