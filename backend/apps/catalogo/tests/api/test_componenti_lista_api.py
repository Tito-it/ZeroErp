# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke test HTTP della distinta base come lista configurabile
#        (`GET articoli/<id>/componenti/lista/` e `…/lista/export/`,
#        brief-db-liste-righe-documento, lotto C). Mock di service, cancello
#        e UI: nessun accesso DB (CI-compatible).
# ------------------------------------------------------------

"""⛔ PERCHE' QUESTO FILE ESISTE.

Le cose che una view sbagliata rende silenziose: l'articolo preso dal path,
il filtro «in vigore al» e i parametri della lista passati al service, il
tetto alzato solo dall'export, il cancello di perimetro chiamato con la lista
della distinta — e NON montato su `…/componenti/`, che serve anche la
creazione di un componente.

Indice test:

 1) test_lista_richiede_jwt
 2) test_lista_pagina_envelope_e_parametri
 3) test_data_malformata_e_un_400
 4) test_lista_ed_export_col_cancello_della_distinta
 5) test_export_csv_alza_il_tetto_e_porta_il_filtro
 6) test_componenti_completa_senza_cancello
 7) test_lista_ed_export_col_permesso_dell_articolo
"""

import datetime as dt
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import Client
from django.urls import resolve

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS
from apps.ui.tests._coda_export import coda_export_finta

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_GUARD = "apps.core.services.perimetro_emittente.guard_lista_per_codice"
_PAGINA = "apps.catalogo.api.views.fn_list_componenti_pagina"

_ARTICOLO = "11111111-1111-1111-1111-111111111111"
_BASE = f"/api/v1/catalogo/articoli/{_ARTICOLO}/componenti/"
_LISTA = "catalogo.articolo_componenti"


class TestComponentiListaApi(JwtMockedApiTest):

    def setUp(self) -> None:
        super().setUp()
        self.client = Client()
        # Le view sono `is_search_endpoint`: la cache del throttle e'
        # condivisa dalla suite (vedi `test_righe_lista_api`).
        cache.clear()

    def test_lista_richiede_jwt(self) -> None:
        self.assertEqual(self.client.get(f"{_BASE}lista/").status_code, 401)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PAGINA)
    def test_lista_pagina_envelope_e_parametri(self, pagina, _auth) -> None:
        pagina.return_value = ([{"id": "a"}, {"id": "b"}], 12)
        resp = self.client.get(
            f"{_BASE}lista/?valido_al=2026-09-28&search=vite&order_by=valido_al"
            "&order_dir=asc&limit=10&offset=10",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertEqual((data["count"], data["page"], len(data["results"])), (12, 2, 2))
        args, kwargs = pagina.call_args
        self.assertEqual(str(args[0]), _ARTICOLO)
        self.assertEqual(kwargs, {
            "valido_al": dt.date(2026, 9, 28), "search": "vite",
            "order_by": "valido_al", "order_dir": "asc", "limit": 10, "offset": 10,
        })

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PAGINA, return_value=([], 0))
    def test_data_malformata_e_un_400(self, pagina, _auth) -> None:
        resp = self.client.get(f"{_BASE}lista/?valido_al=28-09-2026")
        self.assertEqual(resp.status_code, 400)
        pagina.assert_not_called()

    # ⭐ Si guarda COSA riceve il cancello, non se rifiuta: la decisione ha i
    #    suoi test in core. La distinta non ha un emittente suo (D-8.2): il
    #    cancello non riceve un emittente esplicito dalla richiesta.
    @patch(_AUTH, return_value=(Mock(), None))
    def test_lista_ed_export_col_cancello_della_distinta(self, _auth) -> None:
        for suffisso in ("lista/", "lista/export/"):
            cache.clear()
            with self.subTest(suffisso=suffisso), patch(_GUARD) as guard, \
                    patch(_PAGINA, return_value=([], 0)), coda_export_finta():
                resp = self.client.get(f"{_BASE}{suffisso}")
                # Anche l'export deve rispondere: un cancello giusto davanti
                # a una view rotta non prova niente.
                self.assertEqual(resp.status_code, 200)
                guard.assert_called_once()
                self.assertEqual(guard.call_args.kwargs["lista_codice"], _LISTA)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PAGINA)
    def test_export_csv_alza_il_tetto_e_porta_il_filtro(self, pagina, _auth) -> None:
        pagina.return_value = ([{"componente_codice": "V1"}], 1)
        with coda_export_finta("bom.csv") as mock_render_cls:
            resp = self.client.get(f"{_BASE}lista/export/?formato=csv&valido_al=2026-09-28")
        self.assertEqual(resp.status_code, 200)
        kwargs = pagina.call_args.kwargs
        self.assertEqual(kwargs["valido_al"], dt.date(2026, 9, 28))
        self.assertEqual((kwargs["limit"], kwargs["max_limit"], kwargs["offset"]),
                         (EXPORT_MAX_ROWS + 1, EXPORT_MAX_ROWS + 1, 0))
        render_kw = mock_render_cls.return_value.render.call_args.kwargs
        self.assertEqual(render_kw["lista_codice"], _LISTA)
        self.assertEqual(render_kw["filtri_applicati"], {"valido_al": "2026-09-28"})

    # ⛔ `…/componenti/` serve anche il POST di creazione: il cancello di
    #    perimetro scatterebbe anche li'.
    def test_componenti_completa_senza_cancello(self) -> None:
        view = resolve(_BASE).func.view_class
        self.assertIsNone(getattr(view, "lista_codice", None))

    def test_lista_ed_export_col_permesso_dell_articolo(self) -> None:
        for suffisso in ("lista/", "lista/export/"):
            with self.subTest(suffisso=suffisso):
                view = resolve(f"{_BASE}{suffisso}").func.view_class
                self.assertEqual(view.model_permission, ("catalogo", "articolo"))
                self.assertEqual(view.lista_codice, _LISTA)
