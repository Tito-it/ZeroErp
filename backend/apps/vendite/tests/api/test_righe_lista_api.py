# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke test HTTP delle view della LISTA delle righe dei quattro
#        documenti di vendita (`GET …/righe/lista/` e `…/righe/lista/export/`),
#        nate dalla factory `build_lista_figlia_views` (apps/ui/api)
#        (brief-db-liste-righe-documento, lotto A). Mock di service, cancello
#        e UI: nessun accesso DB (CI-compatible).
# ------------------------------------------------------------

"""⛔ PERCHE' QUESTO FILE ESISTE.

Il BB SQL ha i suoi test (`tests/db/test_righe_documento_lista.py`); le otto
view che lo espongono no. E le cose che una view sbagliata rende silenziose
sono tutte qui: l'id del documento preso dal kwarg giusto, la pagina e i
parametri della lista passati al service, il tetto alzato solo dall'export,
il cancello di perimetro chiamato con la lista del documento e con
l'emittente letto da `emittente_fiscale_id` — e NON montato su `…/righe/`,
che serve anche la creazione di una riga (decisione di Tid, 2026-09-28).

Indice test (x4 documenti: preventivo, ordine, DDT, reso):

 1) test_lista_richiede_jwt
 2) test_lista_pagina_envelope_e_parametri
 3) test_lista_cancello_con_lista_ed_emittente_del_documento
 4) test_export_csv_alza_il_tetto
 5) test_righe_completa_senza_cancello
 6) test_lista_ed_export_col_permesso_del_documento
"""

from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import Client
from django.urls import resolve

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS
from apps.ui.tests._coda_export import coda_export_finta
from apps.core.tests.ricerca_catalogo_fakes import catalogo_ricerca_finto

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_GUARD = "apps.core.services.perimetro_emittente.guard_lista_per_codice"
_UI_SVC = "apps.ui.api.export_helpers.UiService"
_UI_REPO = "apps.ui.api.export_helpers.UiRepository"
_RENDER = "apps.ui.api.export_helpers.ListaExportService"

# (base URL, modulo service, lista a catalogo)
_DOCUMENTI = (
    ("/api/v1/vendite/preventivi/", "apps.vendite.services.preventivi_service",
     "vendite.preventivo_righe"),
    ("/api/v1/vendite/ordini/", "apps.vendite.services.ordini_service",
     "vendite.ordine_righe"),
    ("/api/v1/vendite/ddt/", "apps.vendite.services.ddt_service",
     "vendite.ddt_righe"),
    ("/api/v1/vendite/resi/", "apps.vendite.services.resi_service",
     "vendite.reso_righe"),
)

# L'oggetto dei permessi di ciascun documento: le righe ne chiedono il livello.
_PERMESSO = {
    "/api/v1/vendite/preventivi/": ("vendite", "preventivo"),
    "/api/v1/vendite/ordini/": ("vendite", "ordine"),
    "/api/v1/vendite/ddt/": ("vendite", "ddt"),
    "/api/v1/vendite/resi/": ("vendite", "reso"),
}


class TestRigheListaApi(JwtMockedApiTest):
    """Le view della lista righe, uguali per costruzione sui quattro documenti."""

    def setUp(self) -> None:
        super().setUp()
        self.client = Client()
        self._throttle_azzerato()

    # ⚠️ Le view sono `is_search_endpoint` (throttle di ricerca) e la cache del
    #    throttle e' CONDIVISA dalla suite, e sulla macchina di sviluppo
    #    sopravvive anche fra un'esecuzione e l'altra: qui ogni test fa da 4 a 8
    #    richieste, e senza azzerarla le ultime rispondono 429. Si azzera a ogni
    #    documento, non solo nel `setUp`, perche' il budget e' per utente e non
    #    per endpoint.
    @staticmethod
    def _throttle_azzerato() -> None:
        cache.clear()

    def test_lista_richiede_jwt(self) -> None:
        for base, _svc, _lista in _DOCUMENTI:
            with self.subTest(base=base):
                resp = self.client.get(f"{base}7/righe/lista/")
                self.assertEqual(resp.status_code, 401)

    @patch(_AUTH, return_value=(Mock(), None))
    def test_lista_pagina_envelope_e_parametri(self, _auth) -> None:
        for base, svc, _lista in _DOCUMENTI:
            self._throttle_azzerato()
            with self.subTest(base=base), patch(f"{svc}.list_righe_pagina") as pagina:
                pagina.return_value = ([{"id": 1}, {"id": 2}], 12)
                resp = self.client.get(
                    f"{base}7/righe/lista/?search=vite&order_by=descrizione"
                    "&order_dir=desc&limit=10&offset=10",
                )
                self.assertEqual(resp.status_code, 200)
                data = resp.json()["data"]
                self.assertEqual(data["count"], 12)
                self.assertEqual(data["page"], 2)
                self.assertEqual(len(data["results"]), 2)
                pagina.assert_called_once_with(
                    7, search="vite", order_by="descrizione", order_dir="desc",
                    limit=10, offset=10,
                )

    # ⭐ Si guarda COSA riceve il cancello, non se rifiuta: la decisione ha i
    #    suoi test in core. Qui conta che la view gli passi la lista del
    #    documento e l'emittente dal parametro dichiarato — un nome sbagliato
    #    lo lascerebbe a `None` e chi vede piu' emittenti avrebbe un 422 a
    #    drawer aperto.
    @patch(_AUTH, return_value=(Mock(), None))
    def test_lista_cancello_con_lista_ed_emittente_del_documento(self, _auth) -> None:
        for base, svc, lista in _DOCUMENTI:
            for suffisso in ("", "export/"):
                self._throttle_azzerato()
                with self.subTest(base=base, export=bool(suffisso)), \
                        patch(_GUARD) as guard, \
                        patch(f"{svc}.list_righe_pagina", return_value=([], 0)), \
                        coda_export_finta():
                    resp = self.client.get(
                        f"{base}7/righe/lista/{suffisso}?emittente_fiscale_id=3",
                    )
                    # Pagina ed export devono anche rispondere: un cancello
                    # giusto davanti a una view rotta non prova niente.
                    self.assertEqual(resp.status_code, 200)
                    guard.assert_called_once()
                    kwargs = guard.call_args.kwargs
                    self.assertEqual(kwargs["lista_codice"], lista)
                    self.assertEqual(kwargs["emittente_esplicito"], 3)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_RENDER)
    @patch(_UI_REPO, autospec=True)
    @patch(_UI_SVC)
    # La soglia della ricerca e' del catalogo (DB): qui e' un contorno finto.
    @catalogo_ricerca_finto(())
    def test_export_csv_alza_il_tetto(
        self, mock_ui_svc, mock_ui_repo, mock_render_cls, _auth,
    ) -> None:
        mock_ui_svc.return_value.get_lista_config.return_value = {
            "colonne": [{"codice": "descrizione", "ordine": 1, "visibile": True}],
            "pagina_dimensione": 25,
        }
        mock_ui_repo.return_value.list_colonne_by_codice.return_value = [
            {"codice": "descrizione", "etichetta": "Descrizione",
             "campo_sorgente": "descrizione", "tipo_colonna": "testo",
             "tipo_dato": "string", "esportabile": True, "ordine_default": 10},
        ]
        mock_render_cls.return_value.render.return_value = (
            b"descrizione\nVite\n", "text/csv; charset=utf-8", "righe.csv",
        )
        mock_render_cls.select_colonne_visibili_da_config.return_value = []
        for base, svc, _lista in _DOCUMENTI:
            self._throttle_azzerato()
            with self.subTest(base=base), patch(f"{svc}.list_righe_pagina") as pagina:
                pagina.return_value = ([{"descrizione": "Vite"}], 1)
                resp = self.client.get(
                    f"{base}7/righe/lista/export/?formato=csv&search=vite",
                )
                self.assertEqual(resp.status_code, 200)
                self.assertIn("text/csv", resp["Content-Type"])
                args, kwargs = pagina.call_args
                self.assertEqual(args, (7,))
                self.assertEqual(kwargs["search"], "vite")
                self.assertEqual(kwargs["offset"], 0)
                # EXPORT_MAX_ROWS + 1: la riga in piu' dice che il file e' troncato.
                self.assertEqual(kwargs["limit"], EXPORT_MAX_ROWS + 1)
                self.assertEqual(kwargs["max_limit"], EXPORT_MAX_ROWS + 1)

    # ⛔ `…/righe/` serve anche il POST di creazione riga: il cancello di
    #    perimetro scatta su ogni metodo della view che lo dichiara, e li'
    #    rifiuterebbe la creazione a chi vede piu' emittenti.
    def test_righe_completa_senza_cancello(self) -> None:
        for base, _svc, _lista in _DOCUMENTI:
            with self.subTest(base=base):
                view = resolve(f"{base}7/righe/").func.view_class
                self.assertIsNone(getattr(view, "lista_codice", None))

    # ⭐ Il permesso e' mockato negli altri test: un copia-incolla dell'oggetto
    #    di un altro documento passerebbe verde. Lo si legge dalla classe.
    def test_lista_ed_export_col_permesso_del_documento(self) -> None:
        for base, _svc, _lista in _DOCUMENTI:
            for suffisso in ("", "export/"):
                with self.subTest(base=base, export=bool(suffisso)):
                    view = resolve(f"{base}7/righe/lista/{suffisso}").func.view_class
                    self.assertEqual(view.model_permission, _PERMESSO[base])
