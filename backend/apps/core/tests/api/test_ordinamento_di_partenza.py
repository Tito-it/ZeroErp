# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: il BB `apps.core.services.ordinamento_di_partenza` (BE25 (2) di
#        brief-db-revisione-ui): una GET di lista configurabile senza
#        `order_by` riceve l'ordinamento risolto dal DB come PROPOSTA; la
#        risposta lo dice in `meta.ordinamento` solo se il repository lo
#        APPLICA (`colonna_ordinamento` risolve la chiave nella whitelist).
#        Una chiave rifiutata fa rileggere la lista senza; ogni altra
#        richiesta resta com'e'.
# Note: ⭐ Senza DB: la lettura dei fatti (`ordinamento_risolto`) e' finta, il BB
#       gira davvero, su una richiesta DRF vera e su una view vera. La lettura
#       sul DB vero la prova `apps/ui/tests/db/test_ordinamento_lista_db.py`.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) OrdinamentoDiPartenzaTests.test_senza_order_by_si_propone_il_preset
2) OrdinamentoDiPartenzaTests.test_la_whitelist_che_accetta_lo_applica
3) OrdinamentoDiPartenzaTests.test_proposta_mai_risolta_non_va_nel_meta
4) OrdinamentoDiPartenzaTests.test_chiave_proposta_fuori_whitelist_e_un_rifiuto_suo
5) OrdinamentoDiPartenzaTests.test_order_by_della_richiesta_vince
6) OrdinamentoDiPartenzaTests.test_le_scritture_non_si_ordinano
7) OrdinamentoDiPartenzaTests.test_senza_ordinamento_a_preset_resta_il_default
8) OrdinamentoDiPartenzaTests.test_voce_senza_campo_sorgente_saltata
9) OrdinamentoDiPartenzaTests.test_il_meta_si_azzera_alla_richiesta_dopo
10) OrdinamentoDiPartenzaTests.test_il_ritiro_rimette_la_query_di_prima
11) OrdinamentoDiPartenzaViewVeraTests.test_lista_senza_order_by_riceve_il_preset
12) OrdinamentoDiPartenzaViewVeraTests.test_lista_con_order_by_resta_sua
13) OrdinamentoDiPartenzaViewVeraTests.test_export_senza_order_by_riceve_il_preset
14) OrdinamentoDiPartenzaViewVeraTests.test_lista_che_non_ordina_non_dice_un_ordinamento
15) OrdinamentoDiPartenzaViewVeraTests.test_chiave_rifiutata_si_rilegge_senza
16) OrdinamentoDiPartenzaViewVeraTests.test_order_by_del_client_fuori_whitelist_resta_400
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock, patch

from django.test import RequestFactory, SimpleTestCase
from rest_framework.request import Request

from apps.core.api.success_responses import success_response
from apps.core.db._helpers import colonna_ordinamento
from apps.core.services.ordinamento_di_partenza import (
    applica_ordinamento_di_partenza,
    ritira_ordinamento_di_partenza,
)
from apps.core.services.request_context import (
    OrdinamentoPropostoRifiutato,
    get_ordinamento_applicato,
    set_ordinamento_applicato,
    set_request_context,
)
from apps.core.tests._helpers.jwt_mock import ClientApi, JwtMockedApiTest
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS

_LETTURA = "apps.core.services.ordinamento_di_partenza.ordinamento_risolto"
_PRESET = [
    {"col": "data", "dir": "desc", "campo_sorgente": "data_documento"},
    {"col": "numero", "dir": "asc", "campo_sorgente": "numero"},
]
_ATTESO = {"order_by": "data_documento", "order_dir": "desc", "col": "data"}


def _richiesta(metodo: str = "get", query: str = "") -> Request:
    grezza = getattr(RequestFactory(), metodo)(f"/api/v1/x/{query}")
    richiesta = Request(grezza)
    richiesta.user = SimpleNamespace(id=7, is_authenticated=True)
    return richiesta


def _proponi(query: str = "", voci: list[dict[str, Any]] | None = None) -> Request:
    richiesta = _richiesta(query=query)
    with patch(_LETTURA, return_value=_PRESET if voci is None else voci):
        applica_ordinamento_di_partenza(richiesta, lista_codice="vendite.x")
    return richiesta


def _meta() -> dict[str, Any]:
    return json.loads(success_response({"results": []}).content).get("meta", {})


class OrdinamentoDiPartenzaTests(SimpleTestCase):
    def setUp(self) -> None:
        set_request_context(request_id=None, idempotency_key=None)
        self.addCleanup(set_request_context, request_id=None, idempotency_key=None)

    def test_senza_order_by_si_propone_il_preset(self) -> None:
        richiesta = _proponi(query="?search=ros")
        # Lo vedono tutti e due i modi di leggere la query, e il resto resta.
        self.assertEqual(richiesta.query_params["order_by"], "data_documento")
        self.assertEqual(richiesta._request.GET["order_dir"], "desc")
        self.assertEqual(richiesta.query_params["search"], "ros")
        # ⭐ Proposto, non ancora applicato: nessuno ha risolto la chiave.
        self.assertIsNone(get_ordinamento_applicato())

    # La PRIMA voce (deciso da Tid il 2026-11-22), confermata dalla sede unica
    # della risoluzione delle chiavi: da qui la risposta la dice.
    def test_la_whitelist_che_accetta_lo_applica(self) -> None:
        _proponi()
        self.assertEqual(colonna_ordinamento("data_documento", {"data_documento": "v.data"}), "v.data")
        self.assertEqual(get_ordinamento_applicato(), _ATTESO)
        self.assertEqual(_meta()["ordinamento"], _ATTESO)

    # ⛔ Una lista che ordina nel browser non risolve nessuna chiave: la
    #    risposta non dice un ordinamento che i dati non hanno.
    def test_proposta_mai_risolta_non_va_nel_meta(self) -> None:
        _proponi()
        self.assertNotIn("ordinamento", _meta())

    def test_chiave_proposta_fuori_whitelist_e_un_rifiuto_suo(self) -> None:
        _proponi()
        with self.assertRaises(OrdinamentoPropostoRifiutato) as ctx:
            colonna_ordinamento("data_documento", {"numero": "v.numero"})
        # Resta un `order_by_invalid`: fuori da una DomainAPIView e' il 400 di sempre.
        self.assertIsInstance(ctx.exception, ValueError)
        self.assertEqual(str(ctx.exception), "order_by_invalid")
        # Una chiave che non e' la proposta e' il rifiuto comune.
        with self.assertRaises(ValueError) as altro:
            colonna_ordinamento("altro", {"numero": "v.numero"})
        self.assertNotIsInstance(altro.exception, OrdinamentoPropostoRifiutato)

    def test_order_by_della_richiesta_vince(self) -> None:
        richiesta = _richiesta(query="?order_by=numero&order_dir=asc")
        with patch(_LETTURA, return_value=_PRESET) as lettura:
            applica_ordinamento_di_partenza(richiesta, lista_codice="vendite.x")
        lettura.assert_not_called()
        self.assertEqual(richiesta.query_params["order_by"], "numero")
        colonna_ordinamento("numero", {"numero": "v.numero"})
        self.assertIsNone(get_ordinamento_applicato())
        self.assertNotIn("ordinamento", _meta())

    def test_le_scritture_non_si_ordinano(self) -> None:
        richiesta = _richiesta(metodo="post")
        with patch(_LETTURA, return_value=_PRESET) as lettura:
            applica_ordinamento_di_partenza(richiesta, lista_codice="vendite.x")
        lettura.assert_not_called()
        self.assertIsNone(get_ordinamento_applicato())

    def test_senza_ordinamento_a_preset_resta_il_default(self) -> None:
        richiesta = _proponi(voci=[])
        self.assertNotIn("order_by", richiesta.query_params)
        self.assertIsNone(get_ordinamento_applicato())

    def test_voce_senza_campo_sorgente_saltata(self) -> None:
        voci = [{"col": "azioni", "dir": "asc", "campo_sorgente": None}, *_PRESET[1:]]
        richiesta = _proponi(voci=voci)
        self.assertEqual(richiesta.query_params["order_by"], "numero")

    # ⚠️ Un worker riusa il thread: l'ordinamento di una richiesta non deve
    #    finire nel `meta` della successiva, ne' come proposta ne' come applicato.
    def test_il_meta_si_azzera_alla_richiesta_dopo(self) -> None:
        _proponi()
        colonna_ordinamento("data_documento", {"data_documento": "v.data"})
        set_request_context(request_id="r2", idempotency_key=None)
        self.assertIsNone(get_ordinamento_applicato())
        colonna_ordinamento("data_documento", {"data_documento": "v.data"})
        self.assertIsNone(get_ordinamento_applicato())

    def test_il_ritiro_rimette_la_query_di_prima(self) -> None:
        richiesta = _proponi(query="?search=ros")
        ritira_ordinamento_di_partenza(richiesta, lista_codice="vendite.x")
        self.assertNotIn("order_by", richiesta.query_params)
        self.assertNotIn("order_dir", richiesta.query_params)
        self.assertEqual(richiesta.query_params["search"], "ros")
        # Ritirata la proposta, la chiave non si conferma piu'.
        colonna_ordinamento("data_documento", {"data_documento": "v.data"})
        self.assertIsNone(get_ordinamento_applicato())
        set_ordinamento_applicato(None)


# ------------------------------------------------------------
# ⭐ LA GIUNTURA CON UNA VIEW VERA (`/verifica` del 2026-11-22). I test sopra
#    provano il BB su una richiesta costruita a mano; `JwtMockedApiTest`
#    spegne la lettura (`[]`) in OGNI altro test API, quindi nessuno provava
#    che una view di lista, attraverso tutta la catena (middleware,
#    `DomainAPIView.initial()`, `parse_list_params`, `success_response`,
#    `handle_exception`), passi al service l'ordinamento del preset e lo dica
#    in `meta`. Si usa la lista offerte, che dichiara `lista_codice` sulla
#    lista E sull'export: il service e' finto, la view no. Il service finto
#    risolve la chiave con `colonna_ordinamento`, come fa ogni repository.
# ------------------------------------------------------------
_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_SVC_OFFERTE = "apps.vendite.api.views_offerte.OfferteService"
_VOCE = {"col": "data", "dir": "desc", "campo_sorgente": "data_insert"}
_WHITELIST = {"data_insert": "v.data_insert", "numero": "v.numero"}


# Scopo: un `list_offerte` finto che ordina come un repository: risolve la
#        chiave nella sua whitelist, e restituisce `risultato`.
def _service_che_ordina(whitelist: dict[str, str], risultato: Any):
    def list_offerte(**kwargs: Any) -> Any:
        colonna_ordinamento(kwargs["order_by"], whitelist)
        return risultato
    return list_offerte


class OrdinamentoDiPartenzaViewVeraTests(JwtMockedApiTest):
    come_super_admin = True
    def setUp(self) -> None:
        super().setUp()
        self.client = ClientApi()
        self.mock_ordinamento_risolto.return_value = [_VOCE]

    def _chiamate(self, svc_cls: Mock) -> list[dict]:
        return [c.kwargs for c in svc_cls.return_value.list_offerte.call_args_list]

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC_OFFERTE)
    def test_lista_senza_order_by_riceve_il_preset(self, svc_cls, _auth) -> None:
        svc_cls.return_value.list_offerte.side_effect = _service_che_ordina(_WHITELIST, ([], 0))
        resp = self.client.get("/api/v1/vendite/offerte/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.mock_ordinamento_risolto.call_args.args[0], "vendite.offerte")
        self.assertEqual(self._chiamate(svc_cls)[0]["order_by"], "data_insert")
        self.assertEqual(self._chiamate(svc_cls)[0]["order_dir"], "desc")
        self.assertEqual(
            resp.json()["meta"]["ordinamento"],
            {"order_by": "data_insert", "order_dir": "desc", "col": "data"},
        )

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC_OFFERTE)
    def test_lista_con_order_by_resta_sua(self, svc_cls, _auth) -> None:
        svc_cls.return_value.list_offerte.side_effect = _service_che_ordina(_WHITELIST, ([], 0))
        resp = self.client.get("/api/v1/vendite/offerte/?order_by=numero&order_dir=asc")
        self.assertEqual(resp.status_code, 200)
        self.mock_ordinamento_risolto.assert_not_called()
        self.assertEqual(self._chiamate(svc_cls)[0]["order_by"], "numero")
        self.assertNotIn("ordinamento", resp.json().get("meta", {}))

    # L'export e' l'altra porta della stessa lista: il file esce nell'ordine
    # che l'operatore vede. Il tetto di righe ferma la view DOPO la lettura.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC_OFFERTE)
    def test_export_senza_order_by_riceve_il_preset(self, svc_cls, _auth) -> None:
        svc_cls.return_value.list_offerte.side_effect = _service_che_ordina(
            _WHITELIST, ([], EXPORT_MAX_ROWS + 1),
        )
        svc_cls.return_value.resolve_filtri_export_label.return_value = {}
        resp = self.client.get("/api/v1/vendite/offerte/export/?formato=csv")
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(self._chiamate(svc_cls)[0]["order_by"], "data_insert")
        self.assertEqual(self._chiamate(svc_cls)[0]["order_dir"], "desc")

    # ⛔ Una lista che non risolve chiavi (ordina nel browser, come gli ambiti
    #    di un titolo IVA) riceve la proposta ma non la applica: la risposta
    #    non dice un ordinamento che i dati non hanno.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC_OFFERTE)
    def test_lista_che_non_ordina_non_dice_un_ordinamento(self, svc_cls, _auth) -> None:
        svc_cls.return_value.list_offerte.return_value = ([], 0)
        resp = self.client.get("/api/v1/vendite/offerte/")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("ordinamento", resp.json().get("meta", {}))

    # ⭐ Il preset nomina una colonna `ordinabile` a catalogo su un campo che
    #    il repository non sa ordinare: la lista si apre col suo default (una
    #    seconda lettura, senza `order_by` NE' `order_dir`), non con un 400 su
    #    una richiesta che non ordinava niente. Il difetto va nel log.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC_OFFERTE)
    def test_chiave_rifiutata_si_rilegge_senza(self, svc_cls, _auth) -> None:
        self.mock_ordinamento_risolto.return_value = [
            {"col": "fuori", "dir": "desc", "campo_sorgente": "campo_fuori"},
        ]
        svc_cls.return_value.list_offerte.side_effect = _service_che_ordina(_WHITELIST, ([], 0))
        with self.assertLogs("apps.core.services.ordinamento_di_partenza", "WARNING"):
            resp = self.client.get("/api/v1/vendite/offerte/")
        self.assertEqual(resp.status_code, 200)
        prima, seconda = self._chiamate(svc_cls)
        self.assertEqual(prima["order_by"], "campo_fuori")
        # La seconda lettura e' quella di una richiesta senza ordinamento: il
        # default della view, senza il verso del preset.
        self.assertEqual(seconda["order_by"], "data_insert")
        self.assertIsNone(seconda["order_dir"])
        self.assertNotIn("ordinamento", resp.json().get("meta", {}))

    # ⛔ La rilettura vale solo per la PROPOSTA: un `order_by` che il client
    #    chiede fuori whitelist resta il 400 di sempre (decisione Tid del
    #    2026-10-20, nessun ripiego silenzioso).
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SVC_OFFERTE)
    def test_order_by_del_client_fuori_whitelist_resta_400(self, svc_cls, _auth) -> None:
        svc_cls.return_value.list_offerte.side_effect = _service_che_ordina(
            {"numero": "v.numero"}, ([], 0),
        )
        resp = self.client.get("/api/v1/vendite/offerte/?order_by=pippo")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(len(self._chiamate(svc_cls)), 1)
