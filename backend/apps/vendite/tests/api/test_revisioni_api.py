# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: i due endpoint «Revisioni» (preventivo e offerta) col contratto di
#        lista (brief-db-liste-datatable-grezze §4 righe 7 e 8): envelope
#        paginato, parametri di lista al service, cancello di perimetro sciolto
#        dall'emittente del documento.
# Note: SimpleTestCase + mock del service; il cancello gira DAVVERO (si mocka la
#       risoluzione dello scope e il flag di catalogo, non il guard).
# ------------------------------------------------------------
"""
Indice test:

1) test_preventivo_envelope_e_parametri_di_lista
2) test_offerta_envelope_e_parametri_di_lista
3) test_le_view_dichiarano_lista_e_parametro_emittente
4) test_multi_emittente_senza_emittente_e_422
5) test_multi_emittente_con_emittente_del_documento_passa
"""

from unittest.mock import Mock, patch

from django.test import Client

from apps.core.db.lista_catalogo_repository import FlagPerimetroLista
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_PREV_SVC = "apps.vendite.api.preventivi_views.preventivi_service"
_OFF_SVC = "apps.vendite.api.views_offerte.OfferteService"
_SCOPE = "apps.core.services.perimetro_emittente.PermissionResolver.get_emittenti_pk_ids"
_FLAG = "apps.core.services.perimetro_emittente.fetch_flag_perimetro"


class RevisioniApiTests(JwtMockedApiTest):

    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    # Scopo: envelope paginato col totale del repository (non `len(results)`)
    #        e parametri di lista al service; ⚠️ `emittente_fiscale_id` NON
    #        arriva al service: lo legge solo il cancello.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PREV_SVC)
    def test_preventivo_envelope_e_parametri_di_lista(self, svc, _auth):
        svc.list_revisioni.return_value = ([{"id": 5, "rev": 0}], 12)
        response = self.client.get(
            "/api/v1/vendite/preventivi/5/revisioni/"
            "?limit=10&offset=10&order_by=data&order_dir=desc&emittente_fiscale_id=3",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["count"], 12)
        self.assertEqual(data["page"], 2)
        self.assertEqual(data["results"], [{"id": 5, "rev": 0}])
        svc.list_revisioni.assert_called_once_with(
            5, limit=10, offset=10, order_by="data", order_dir="desc",
        )

    # Scopo: stesso contratto sull'offerta, default `revisione_numero`.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_OFF_SVC)
    def test_offerta_envelope_e_parametri_di_lista(self, svc_cls, _auth):
        svc = svc_cls.return_value
        svc.list_revisioni.return_value = ([{"id": 9, "revisione_numero": 1}], 1)
        response = self.client.get("/api/v1/vendite/offerte/9/revisioni/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["count"], 1)
        svc.list_revisioni.assert_called_once_with(
            9, limit=25, offset=0, order_by="revisione_numero", order_dir=None,
        )

    # Scopo: le view dichiarano la lista a catalogo e il nome del parametro
    #        con cui il tab fissa l'emittente (la PK, come nella vista).
    def test_le_view_dichiarano_lista_e_parametro_emittente(self):
        from apps.vendite.api.preventivi_views import ApiPreventivoRevisioniList
        from apps.vendite.api.views_offerte import ApiOffertaRevisioni

        self.assertEqual(ApiPreventivoRevisioniList.lista_codice, "vendite.preventivo_revisioni")
        self.assertEqual(ApiOffertaRevisioni.lista_codice, "vendite.offerta_revisioni")
        self.assertEqual(ApiPreventivoRevisioniList.lista_emittente_param, "emittente_fiscale_id")
        self.assertEqual(ApiOffertaRevisioni.lista_emittente_param, "emittente_fiscale_id")

    # Scopo: chi vede piu' emittenti e NON manda l'emittente riceve il
    #        cancello (422): e' il caso che il tab deve evitare.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_FLAG, return_value=FlagPerimetroLista(multi_emittente=False, perimetro_emittente=True))
    @patch(_SCOPE, return_value=None)
    @patch(_PREV_SVC)
    def test_multi_emittente_senza_emittente_e_422(self, svc, _scope, _flag, _auth):
        response = self.client.get("/api/v1/vendite/preventivi/5/revisioni/")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["error"]["code"], "E_UI_LISTA_EMITTENTE_DA_SCEGLIERE",
        )
        svc.list_revisioni.assert_not_called()

    # Scopo: con l'emittente del documento il cancello si scioglie, sulle due
    #        liste.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_FLAG, return_value=FlagPerimetroLista(multi_emittente=False, perimetro_emittente=True))
    @patch(_SCOPE, return_value=None)
    @patch(_OFF_SVC)
    @patch(_PREV_SVC)
    def test_multi_emittente_con_emittente_del_documento_passa(
        self, prev_svc, off_svc_cls, _scope, _flag, _auth,
    ):
        prev_svc.list_revisioni.return_value = ([], 0)
        off_svc_cls.return_value.list_revisioni.return_value = ([], 0)
        for url in (
            "/api/v1/vendite/preventivi/5/revisioni/?emittente_fiscale_id=3",
            "/api/v1/vendite/offerte/9/revisioni/?emittente_fiscale_id=3",
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
