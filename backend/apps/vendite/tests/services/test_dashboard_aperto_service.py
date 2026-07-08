# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari service Situazione aperta (mock repository).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) DashApertoRiepilogoServiceTests.test_quattro_aree_sempre_presenti_ordine_funnel
2) DashApertoRiepilogoServiceTests.test_contratto_simmetrico_griglia_fasi
3) DashApertoRiepilogoServiceTests.test_pivot_totali_area_e_fasi
4) DashApertoRiepilogoServiceTests.test_area_conteggi_valori_none
5) DashApertoRiepilogoServiceTests.test_fase_sconosciuta_accodata_fail_visible
6) DashApertoRiepilogoServiceTests.test_area_sconosciuta_accodata_fail_visible
7) DashApertoRiepilogoServiceTests.test_area_extra_con_valori_non_li_perde
8) DashApertoDocumentiServiceTests.test_documenti_ok_envelope_paginato
9) DashApertoDocumentiServiceTests.test_documenti_fase_sconosciuta_passthrough
10) DashApertoDocumentiServiceTests.test_documenti_area_sconosciuta_passthrough
11) DashApertoDocumentiServiceTests.test_documenti_default_solo_aperti
12) DashApertoDocumentiServiceTests.test_documenti_page_invalida
13) DashApertoDocumentiServiceTests.test_documenti_pagina_stantia_clampata
"""

from unittest import TestCase
from unittest.mock import patch

from apps.core.services.service_errors import ServiceError
from apps.vendite.services import vendite_service
from apps.vendite.services.vendite_service import (
    fn_dash_aperto_documenti,
    fn_dash_aperto_riepilogo,
)

# Un'area euro con due fasi + un'area a conteggi: esercitano insieme i totali
# di area (somma Decimal sulle fasi) e la serializzazione per tipo misura.
_ROWS_RIEPILOGO = [
    {
        "area": "PREVENTIVI",
        "fase": "APERTO",
        "n_documenti": 3,
        "n_aperti": 3,
        "valore_totale": "1500.00",
        "valore_transitato": "0",
    },
    {
        "area": "PREVENTIVI",
        "fase": "IN_CORSO",
        "n_documenti": 2,
        "n_aperti": 1,
        "valore_totale": "500.50",
        "valore_transitato": "300.00",
    },
    {
        "area": "CONTRATTI",
        "fase": "IN_CORSO",
        "n_documenti": 4,
        "n_aperti": 4,
        "valore_totale": None,
        "valore_transitato": None,
    },
]

_ORDINE_FASI = ["APERTO", "IN_ATTESA", "IN_CORSO", "CHIUSO"]


class DashApertoRiepilogoServiceTests(TestCase):
    # Scopo: Le 4 aree documento sono sempre presenti nell'ordine del funnel
    #        anche a repo vuoto (NIENTE COMMESSE: coperte dalla Lente 1), e il
    #        vocabolario `fasi` top-level e' sempre esposto (alimenta i filtri
    #        FE senza dipendere dalla griglia di un'area).
    @patch.object(vendite_service.VenditeRepository, "list_dash_aperto_riepilogo", return_value=[])
    def test_quattro_aree_sempre_presenti_ordine_funnel(self, _mock_repo):
        data = fn_dash_aperto_riepilogo()
        ordine = [a["area"] for a in data["aree"]]
        self.assertEqual(ordine, ["PREVENTIVI", "ORDINI", "OFFERTE", "CONTRATTI"])
        self.assertEqual(data["fasi"], _ORDINE_FASI)

    # Scopo: Contratto simmetrico: ogni area espone SEMPRE la griglia delle 4
    #        fasi nell'ordine del ciclo di vita, con zeri espliciti (aree euro
    #        a "0", aree a conteggi a None) — DL-13: il FE decide cosa rendere.
    @patch.object(vendite_service.VenditeRepository, "list_dash_aperto_riepilogo", return_value=[])
    def test_contratto_simmetrico_griglia_fasi(self, _mock_repo):
        data = fn_dash_aperto_riepilogo()
        for area in data["aree"]:
            self.assertEqual([f["fase"] for f in area["fasi"]], _ORDINE_FASI)
            self.assertEqual(area["n_documenti"], 0)
            self.assertEqual(area["n_aperti"], 0)
        preventivi = data["aree"][0]
        self.assertEqual(preventivi["valore_totale"], "0")
        offerte = data["aree"][2]
        self.assertIsNone(offerte["valore_totale"])

    # Scopo: I totali di area sommano le fasi (Decimal, niente float) e le
    #        celle per fase restano consultabili singolarmente.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_aperto_riepilogo",
        return_value=_ROWS_RIEPILOGO,
    )
    def test_pivot_totali_area_e_fasi(self, _mock_repo):
        data = fn_dash_aperto_riepilogo()
        aree = {a["area"]: a for a in data["aree"]}
        prev = aree["PREVENTIVI"]
        self.assertEqual(prev["n_documenti"], 5)
        self.assertEqual(prev["n_aperti"], 4)
        self.assertEqual(prev["valore_totale"], "2000.50")
        self.assertEqual(prev["valore_transitato"], "300.00")
        fasi = {f["fase"]: f for f in prev["fasi"]}
        self.assertEqual(fasi["APERTO"]["n_documenti"], 3)
        self.assertEqual(fasi["IN_CORSO"]["valore_totale"], "500.50")
        self.assertEqual(fasi["IN_ATTESA"]["n_documenti"], 0)

    # Scopo: Le aree a conteggi (OFFERTE/CONTRATTI, DL-11) espongono
    #        valore_* None anche quando popolate.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_aperto_riepilogo",
        return_value=_ROWS_RIEPILOGO,
    )
    def test_area_conteggi_valori_none(self, _mock_repo):
        data = fn_dash_aperto_riepilogo()
        contratti = next(a for a in data["aree"] if a["area"] == "CONTRATTI")
        self.assertEqual(contratti["n_documenti"], 4)
        self.assertIsNone(contratti["valore_totale"])
        fase_in_corso = next(f for f in contratti["fasi"] if f["fase"] == "IN_CORSO")
        self.assertEqual(fase_in_corso["n_aperti"], 4)
        self.assertIsNone(fase_in_corso["valore_totale"])

    # Scopo: Una fase emessa dalla vista ma fuori whitelist NON viene persa:
    #        accodata dopo le 4 note su TUTTE le aree (griglia simmetrica).
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_aperto_riepilogo",
        return_value=[
            {
                "area": "ORDINI",
                "fase": "NUOVA_FASE",
                "n_documenti": 1,
                "n_aperti": 1,
                "valore_totale": "10.00",
                "valore_transitato": "0",
            }
        ],
    )
    def test_fase_sconosciuta_accodata_fail_visible(self, _mock_repo):
        data = fn_dash_aperto_riepilogo()
        self.assertEqual(data["fasi"], _ORDINE_FASI + ["NUOVA_FASE"])
        ordini = next(a for a in data["aree"] if a["area"] == "ORDINI")
        self.assertEqual(
            [f["fase"] for f in ordini["fasi"]], _ORDINE_FASI + ["NUOVA_FASE"]
        )
        self.assertEqual(ordini["fasi"][4]["n_documenti"], 1)
        preventivi = data["aree"][0]
        self.assertEqual(len(preventivi["fasi"]), 5)

    # Scopo: Un'area emessa dalla vista ma fuori whitelist NON viene persa:
    #        accodata dopo le 4 note (fail-visible).
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_aperto_riepilogo",
        return_value=[
            {
                "area": "NUOVA_AREA",
                "fase": "APERTO",
                "n_documenti": 2,
                "n_aperti": 2,
                "valore_totale": None,
                "valore_transitato": None,
            }
        ],
    )
    def test_area_sconosciuta_accodata_fail_visible(self, _mock_repo):
        data = fn_dash_aperto_riepilogo()
        ordine = [a["area"] for a in data["aree"]]
        self.assertEqual(
            ordine, ["PREVENTIVI", "ORDINI", "OFFERTE", "CONTRATTI", "NUOVA_AREA"]
        )
        self.assertEqual(data["aree"][4]["n_documenti"], 2)

    # Scopo: Un'area extra che porta VALORI li espone (decisione data-driven,
    #        non la whitelist euro statica): niente euro persi in silenzio.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_aperto_riepilogo",
        return_value=[
            {
                "area": "DDT",
                "fase": "APERTO",
                "n_documenti": 2,
                "n_aperti": 2,
                "valore_totale": "750.00",
                "valore_transitato": "250.00",
            }
        ],
    )
    def test_area_extra_con_valori_non_li_perde(self, _mock_repo):
        data = fn_dash_aperto_riepilogo()
        ddt = next(a for a in data["aree"] if a["area"] == "DDT")
        self.assertEqual(ddt["valore_totale"], "750.00")
        self.assertEqual(ddt["valore_transitato"], "250.00")
        fase_aperto = next(f for f in ddt["fasi"] if f["fase"] == "APERTO")
        self.assertEqual(fase_aperto["valore_totale"], "750.00")


class DashApertoDocumentiServiceTests(TestCase):
    # Scopo: Envelope paginato standard con i risultati del repository.
    #        Nessun auth_user_id: lo scope e' interamente DB-side.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_aperto_documenti",
        return_value=([{"documento_id": 1}], 1),
    )
    def test_documenti_ok_envelope_paginato(self, mock_repo):
        data = fn_dash_aperto_documenti(area="PREVENTIVI", fase="APERTO")
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["total_pages"], 1)
        self.assertEqual(data["results"], [{"documento_id": 1}])
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual(kwargs["area"], "PREVENTIVI")
        self.assertEqual(kwargs["fase"], "APERTO")
        self.assertNotIn("auth_user_id", kwargs)

    # Scopo: Il filtro fase NON e' whitellistato (coerenza fail-visible col
    #        riepilogo): una fase sconosciuta passa al repository e produce
    #        lista vuota, mai 400 — le fasi future restano drillabili.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_aperto_documenti",
        return_value=([], 0),
    )
    def test_documenti_fase_sconosciuta_passthrough(self, mock_repo):
        data = fn_dash_aperto_documenti(fase="NUOVA_FASE")
        self.assertEqual(data["count"], 0)
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual(kwargs["fase"], "NUOVA_FASE")

    # Scopo: Anche il filtro area NON e' whitellistato (coerenza fail-visible
    #        col riepilogo, che accoda le aree extra E le rende card
    #        cliccabili): un'area sconosciuta — o COMMESSE, esclusa dal WHERE
    #        della vista — passa al repository e produce lista vuota, mai 400.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_aperto_documenti",
        return_value=([], 0),
    )
    def test_documenti_area_sconosciuta_passthrough(self, mock_repo):
        data = fn_dash_aperto_documenti(area="COMMESSE")
        self.assertEqual(data["count"], 0)
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual(kwargs["area"], "COMMESSE")

    # Scopo: Default solo_aperti: la pagina e' la "Situazione aperta" — il
    #        service normalizza None (parametro omesso) a True in un punto
    #        SOLO (la view passa il raw); senza filtri area/fase il
    #        repository riceve None.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_aperto_documenti",
        return_value=([], 0),
    )
    def test_documenti_default_solo_aperti(self, mock_repo):
        fn_dash_aperto_documenti(solo_aperti=None)
        kwargs = mock_repo.call_args.kwargs
        self.assertIsNone(kwargs["area"])
        self.assertIsNone(kwargs["fase"])
        self.assertTrue(kwargs["solo_aperti"])

    # Scopo: Paginazione invalida -> E_VENDITE_VALIDATION (validate_pagination).
    def test_documenti_page_invalida(self):
        with self.assertRaises(ServiceError) as ctx:
            fn_dash_aperto_documenti(page=0)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: Rientro da pagina stantia: il repository clampa l'offset in SQL
    #        (una sola valutazione della union) e il service dichiara
    #        nell'envelope la pagina EFFETTIVA servita, che il FE adotta.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_aperto_documenti",
        return_value=([{"documento_id": 1}], 10),
    )
    def test_documenti_pagina_stantia_clampata(self, _mock_repo):
        data = fn_dash_aperto_documenti(page=99, page_size=50)
        self.assertEqual(data["count"], 10)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["total_pages"], 1)
