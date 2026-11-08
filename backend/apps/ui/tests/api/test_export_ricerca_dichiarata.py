# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La ricerca libera nel metadato del file export la dichiara il BB
#        (`export_helpers.filtri_export_con_ricerca`), non la view.
#
# ⭐ Il difetto che pinna (rilievo in-app di Tid, 2026-09-29): l'export delle
#    righe di una distinta cercate per «rossi» consegnava le righe filtrate con
#    `# Filtri applicati: {}` — un sottoinsieme che si presenta come l'insieme,
#    senza nessun errore. La ricerca la dichiaravano le view, ciascuna a modo
#    suo (`"Ricerca"`, `"search"`), e chi se ne dimenticava sbagliava muto.
# ⚠️ La soglia e' del catalogo (DB): qui e' un contorno, finto dalla sede di
#    progetto (`catalogo_ricerca_finto`). Il BB sotto esame e' quello vero.
# ------------------------------------------------------------

"""Indice test eseguiti:
 1) test_termine_alla_soglia_si_dichiara — `Ricerca` accanto ai filtri del caller
 2) test_termine_sotto_soglia_non_si_dichiara — non ha filtrato, non si scrive
 3) test_la_soglia_e_quella_della_lista — letta per il `lista_codice` dell'export
 4) test_spazi_non_contano — `strip` prima della soglia, come la query
 5) test_termine_vuoto_non_legge_il_catalogo — niente ricerca, niente lettura
 6) test_chiavi_del_caller_non_raddoppiano — `search`/`Ricerca` del caller tolte
 7) test_nessun_filtro_resta_none — il file scrive «nessun filtro»
 8) test_build_export_response_passa_la_ricerca_al_renderer — la coda la usa
"""

from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.core.tests.ricerca_catalogo_fakes import catalogo_ricerca_finto
from apps.ui.api.export_helpers import build_export_response, filtri_export_con_ricerca


def _request(**qp):
    req = Mock()
    req.query_params = qp
    return req


class TestFiltriExportConRicerca(SimpleTestCase):

    @catalogo_ricerca_finto((), soglia=3)
    def test_termine_alla_soglia_si_dichiara(self) -> None:
        filtri = filtri_export_con_ricerca(
            _request(search="ros"), lista_codice="x.y", filtri_applicati={"scartate": True},
        )
        self.assertEqual(filtri, {"Ricerca": "ros", "scartate": True})

    @catalogo_ricerca_finto((), soglia=3)
    def test_termine_sotto_soglia_non_si_dichiara(self) -> None:
        filtri = filtri_export_con_ricerca(
            _request(search="ro"), lista_codice="x.y", filtri_applicati={"scartate": True},
        )
        self.assertEqual(filtri, {"scartate": True})

    def test_la_soglia_e_quella_della_lista(self) -> None:
        with catalogo_ricerca_finto((), soglia=1) as (_, lettura_soglia):
            filtri = filtri_export_con_ricerca(
                _request(search="K"), lista_codice="catalogo.unita_misura", filtri_applicati=None,
            )
        self.assertEqual(filtri, {"Ricerca": "K"})
        lettura_soglia.assert_called_once_with("catalogo.unita_misura")

    @catalogo_ricerca_finto((), soglia=3)
    def test_spazi_non_contano(self) -> None:
        self.assertIsNone(filtri_export_con_ricerca(
            _request(search="  ro  "), lista_codice="x.y", filtri_applicati=None,
        ))
        self.assertEqual(
            filtri_export_con_ricerca(_request(search=" rossi "), lista_codice="x.y", filtri_applicati=None),
            {"Ricerca": "rossi"},
        )

    def test_termine_vuoto_non_legge_il_catalogo(self) -> None:
        with catalogo_ricerca_finto(()) as (_, lettura_soglia):
            for qp in ({}, {"search": ""}, {"search": "   "}):
                self.assertIsNone(filtri_export_con_ricerca(
                    _request(**qp), lista_codice="x.y", filtri_applicati=None,
                ))
        lettura_soglia.assert_not_called()

    @catalogo_ricerca_finto((), soglia=3)
    def test_chiavi_del_caller_non_raddoppiano(self) -> None:
        # `search` resta nei dict dei filtri di magazzino e dei cruscotti (sono
        # gli argomenti della query); `Ricerca` la scrivevano i resolver.
        filtri = filtri_export_con_ricerca(
            _request(search="rossi"), lista_codice="x.y",
            filtri_applicati={"search": "rossi", "Ricerca": "rossi", "Stato": "Attivo"},
        )
        self.assertEqual(filtri, {"Ricerca": "rossi", "Stato": "Attivo"})

    @catalogo_ricerca_finto((), soglia=3)
    def test_nessun_filtro_resta_none(self) -> None:
        self.assertIsNone(filtri_export_con_ricerca(
            _request(), lista_codice="x.y", filtri_applicati={},
        ))

    @catalogo_ricerca_finto((), soglia=3)
    @patch("apps.ui.api.export_helpers.ListaExportService")
    @patch("apps.ui.api.export_helpers.UiRepository", autospec=True)
    @patch("apps.ui.api.export_helpers.UiService")
    def test_build_export_response_passa_la_ricerca_al_renderer(
        self, mock_ui_svc, _ui_repo, mock_render_cls,
    ) -> None:
        mock_ui_svc.return_value.get_lista_config.return_value = {"colonne": []}
        mock_render_cls.select_colonne_visibili_da_config.return_value = []
        mock_render_cls.return_value.render.return_value = (b"", "text/csv", "f.csv")

        build_export_response(
            _request(search="rossi"), lista_codice="pagamenti.distinta_righe",
            results=[], total=0, filtri_applicati=None, fmt="csv",
        )

        kw = mock_render_cls.return_value.render.call_args.kwargs
        self.assertEqual(kw["filtri_applicati"], {"Ricerca": "rossi"})
