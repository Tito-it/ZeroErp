# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari service serbatoio pre-commessa (Situazione aperta v2,
#        mock repository).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) DashApertoRiepilogoServiceTests.test_cinque_aree_sempre_presenti_ordine_funnel
2) DashApertoRiepilogoServiceTests.test_contratto_simmetrico_griglia_fasi
3) DashApertoRiepilogoServiceTests.test_pivot_totali_area_e_fasi
4) DashApertoRiepilogoServiceTests.test_area_conteggi_valori_none
5) DashApertoRiepilogoServiceTests.test_fase_sconosciuta_accodata_fail_visible
6) DashApertoRiepilogoServiceTests.test_area_sconosciuta_accodata_fail_visible
7) DashApertoRiepilogoServiceTests.test_area_extra_con_valori_non_li_perde
8) DashApertoDocumentiServiceTests.test_documenti_ok_envelope_paginato
9) DashApertoDocumentiServiceTests.test_documenti_fase_fuori_vocabolario_e_400
10) DashApertoDocumentiServiceTests.test_documenti_area_sul_vocabolario_delle_sorgenti
10b) DashApertoDocumentiServiceTests.test_documenti_area_inventata_e_400
11) DashApertoDocumentiServiceTests.test_documenti_ritardo_giorni_inoltrato
12) DashApertoDocumentiServiceTests.test_documenti_ritardo_giorni_default_none
13) DashApertoDocumentiServiceTests.test_documenti_ritardo_giorni_non_positivo
13b) DashApertoDocumentiServiceTests.test_documenti_ritardo_giorni_sul_pavimento_passa
13c) DashApertoDocumentiServiceTests.test_documenti_ritardo_giorni_oltre_pavimento
13d) DashApertoDocumentiServiceTests.test_documenti_ritardo_giorni_enorme_e_400
14) DashApertoDocumentiServiceTests.test_documenti_anzianita_giorni_passthrough
15) DashApertoDocumentiServiceTests.test_documenti_page_invalida
16) DashApertoDocumentiServiceTests.test_documenti_pagina_stantia_clampata
17) DashApertoDocumentiServiceTests.test_documenti_ordinamento_inoltrato
18) DashApertoDocumentiServiceTests.test_documenti_order_by_non_valido
19) DashApertoDocumentiServiceTests.test_documenti_order_dir_non_valido
"""

from datetime import date
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
# v2: perimetro aperti-non-chiusi lato vista -> niente n_aperti/valore_transitato.
_ROWS_RIEPILOGO = [
    {"area": "PREVENTIVO", "fase": "APERTO", "n_documenti": 3, "valore_totale": "1500.00"},
    {"area": "PREVENTIVO", "fase": "IN_CORSO", "n_documenti": 2, "valore_totale": "500.50"},
    {"area": "CONTRATTO", "fase": "IN_CORSO", "n_documenti": 4, "valore_totale": None},
]

# 3 fasi vive del serbatoio (via CHIUSO, DL-15/16).
_ORDINE_FASI = ["APERTO", "IN_ATTESA", "IN_CORSO"]


class DashApertoRiepilogoServiceTests(TestCase):
    # Scopo: Le 5 aree documento sono sempre presenti nell'ordine del funnel
    #        anche a repo vuoto (DDT dopo ORDINI, suo veicolo di fatturazione
    #        differita — DL-21; NIENTE COMMESSE: coperte dalla Lente 1; NIENTE
    #        RESI: REVERSE_FLOW, solo Backlog — DL-24), e il vocabolario `fasi`
    #        top-level (3 fasi vive) e' sempre esposto (alimenta i filtri FE
    #        senza dipendere dalla griglia di un'area).
    @patch.object(vendite_service.VenditeRepository, "list_dash_aperto_riepilogo", return_value=[])
    def test_cinque_aree_sempre_presenti_ordine_funnel(self, _mock_repo):
        data = fn_dash_aperto_riepilogo()
        ordine = [a["area"] for a in data["aree"]]
        self.assertEqual(
            ordine, ["PREVENTIVO", "ORDINE_VENDITA", "DDT_VENDITA", "OFFERTA_COMMERCIALE", "CONTRATTO"]
        )
        self.assertNotIn("RESO_VENDITA", ordine)
        self.assertEqual(data["fasi"], _ORDINE_FASI)

    # Scopo: Contratto simmetrico: ogni area espone SEMPRE la griglia delle 3
    #        fasi nell'ordine del ciclo di vita, con zeri espliciti (aree euro
    #        a "0", aree a conteggi a None) — DL-13: il FE decide cosa rendere.
    #        DDT e' area euro (DL-21: ha importi via COALESCE riga/ordine).
    @patch.object(vendite_service.VenditeRepository, "list_dash_aperto_riepilogo", return_value=[])
    def test_contratto_simmetrico_griglia_fasi(self, _mock_repo):
        data = fn_dash_aperto_riepilogo()
        for area in data["aree"]:
            self.assertEqual([f["fase"] for f in area["fasi"]], _ORDINE_FASI)
            self.assertEqual(area["n_documenti"], 0)
        preventivi = data["aree"][0]
        self.assertEqual(preventivi["valore_totale"], "0")
        ddt = data["aree"][2]
        self.assertEqual(ddt["valore_totale"], "0")
        offerte = data["aree"][3]
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
        prev = aree["PREVENTIVO"]
        self.assertEqual(prev["n_documenti"], 5)
        self.assertEqual(prev["valore_totale"], "2000.50")
        fasi = {f["fase"]: f for f in prev["fasi"]}
        self.assertEqual(fasi["APERTO"]["n_documenti"], 3)
        self.assertEqual(fasi["IN_CORSO"]["valore_totale"], "500.50")
        self.assertEqual(fasi["IN_ATTESA"]["n_documenti"], 0)

    # Scopo: Le aree a conteggi (OFFERTE/CONTRATTI, DL-11) espongono
    #        valore_totale None anche quando popolate.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_aperto_riepilogo",
        return_value=_ROWS_RIEPILOGO,
    )
    def test_area_conteggi_valori_none(self, _mock_repo):
        data = fn_dash_aperto_riepilogo()
        contratti = next(a for a in data["aree"] if a["area"] == "CONTRATTO")
        self.assertEqual(contratti["n_documenti"], 4)
        self.assertIsNone(contratti["valore_totale"])
        fase_in_corso = next(f for f in contratti["fasi"] if f["fase"] == "IN_CORSO")
        self.assertEqual(fase_in_corso["n_documenti"], 4)
        self.assertIsNone(fase_in_corso["valore_totale"])

    # Scopo: Una fase emessa dalla vista ma fuori whitelist NON viene persa:
    #        accodata dopo le 3 note su TUTTE le aree (griglia simmetrica).
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_aperto_riepilogo",
        return_value=[
            {"area": "ORDINE_VENDITA", "fase": "NUOVA_FASE", "n_documenti": 1, "valore_totale": "10.00"}
        ],
    )
    def test_fase_sconosciuta_accodata_fail_visible(self, _mock_repo):
        data = fn_dash_aperto_riepilogo()
        self.assertEqual(data["fasi"], _ORDINE_FASI + ["NUOVA_FASE"])
        ordini = next(a for a in data["aree"] if a["area"] == "ORDINE_VENDITA")
        self.assertEqual(
            [f["fase"] for f in ordini["fasi"]], _ORDINE_FASI + ["NUOVA_FASE"]
        )
        self.assertEqual(ordini["fasi"][3]["n_documenti"], 1)
        preventivi = data["aree"][0]
        self.assertEqual(len(preventivi["fasi"]), 4)

    # Scopo: Un'area emessa dalla vista ma fuori whitelist NON viene persa:
    #        accodata dopo le 4 note (fail-visible).
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_aperto_riepilogo",
        return_value=[
            {"area": "NUOVA_AREA", "fase": "APERTO", "n_documenti": 2, "valore_totale": None}
        ],
    )
    def test_area_sconosciuta_accodata_fail_visible(self, _mock_repo):
        data = fn_dash_aperto_riepilogo()
        ordine = [a["area"] for a in data["aree"]]
        self.assertEqual(
            ordine,
            ["PREVENTIVO", "ORDINE_VENDITA", "DDT_VENDITA", "OFFERTA_COMMERCIALE", "CONTRATTO", "NUOVA_AREA"],
        )
        self.assertEqual(data["aree"][5]["n_documenti"], 2)

    # Scopo: Un'area extra che porta VALORI li espone (decisione data-driven,
    #        non la whitelist euro statica): niente euro persi in silenzio.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_aperto_riepilogo",
        return_value=[
            {"area": "DDT_VENDITA", "fase": "APERTO", "n_documenti": 2, "valore_totale": "750.00"}
        ],
    )
    def test_area_extra_con_valori_non_li_perde(self, _mock_repo):
        data = fn_dash_aperto_riepilogo()
        ddt = next(a for a in data["aree"] if a["area"] == "DDT_VENDITA")
        self.assertEqual(ddt["valore_totale"], "750.00")
        fase_aperto = next(f for f in ddt["fasi"] if f["fase"] == "APERTO")
        self.assertEqual(fase_aperto["valore_totale"], "750.00")


class DashApertoDocumentiServiceTests(TestCase):
    # Il vocabolario di `area` e' una TABELLA (`config.sorgenti`): qui il BB e'
    # finto, per restare senza database. La giuntura col vocabolario vero la
    # prova `core/tests/db/test_vocabolari_dei_filtri_db`.
    def setUp(self) -> None:
        patcher = patch.object(vendite_service, "richiedi_codice_a_vocabolario")
        self.vocabolario = patcher.start()
        self.addCleanup(patcher.stop)

    # Scopo: Envelope paginato standard con i risultati del repository.
    #        Nessun auth_user_id: lo scope e' interamente DB-side.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_aperto_documenti",
        return_value=([{"documento_id": 1}], 1),
    )
    def test_documenti_ok_envelope_paginato(self, mock_repo):
        data = fn_dash_aperto_documenti(area="PREVENTIVO", fase="APERTO")
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["total_pages"], 1)
        self.assertEqual(data["results"], [{"documento_id": 1}])
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual(kwargs["area"], "PREVENTIVO")
        self.assertEqual(kwargs["fase"], "APERTO")
        self.assertNotIn("auth_user_id", kwargs)

    # Scopo: ⛔ una fase fuori vocabolario (`FASI_DOCUMENTO`, specchio del
    #        CHECK) e' un 400 sul campo, e il repository non si interroga:
    #        prima passava e rispondeva lista vuota (2026-10-20).
    @patch.object(vendite_service.VenditeRepository, "list_dash_aperto_documenti")
    def test_documenti_fase_fuori_vocabolario_e_400(self, mock_repo):
        with self.assertRaises(ServiceError) as ctx:
            fn_dash_aperto_documenti(fase="NUOVA_FASE")
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertEqual(ctx.exception.context.get("parametro"), "fase")
        self.assertNotIn("field", ctx.exception.context)
        mock_repo.assert_not_called()

    # Scopo: l'area si valida sul vocabolario del MODELLO (`config.sorgenti`),
    #        non sulla whitelist del pivot: una sorgente vera fuori dalle cinque
    #        (qui COMMESSA, esclusa dalla vista) passa al repository — e' la
    #        card «extra» del riepilogo, fail-visible.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_aperto_documenti",
        return_value=([], 0),
    )
    def test_documenti_area_sul_vocabolario_delle_sorgenti(self, mock_repo):
        data = fn_dash_aperto_documenti(area="COMMESSA")
        self.assertEqual(data["count"], 0)
        self.assertEqual(mock_repo.call_args.kwargs["area"], "COMMESSA")
        args, kwargs = self.vocabolario.call_args
        self.assertEqual(args, ("config.sorgenti", "codice_interno", "COMMESSA"))
        self.assertEqual(kwargs["parametro"], "area")
        self.assertEqual(kwargs["codice_errore"], "E_VENDITE_VALIDATION")

    # Scopo: ⛔ un'area che non e' una sorgente (il plurale ritirato `ORDINI`)
    #        e' il 400 del BB, prima del repository.
    @patch.object(vendite_service.VenditeRepository, "list_dash_aperto_documenti")
    def test_documenti_area_inventata_e_400(self, mock_repo):
        self.vocabolario.side_effect = ServiceError(code="E_VENDITE_VALIDATION", message="no")
        with self.assertRaises(ServiceError):
            fn_dash_aperto_documenti(area="ORDINI")
        mock_repo.assert_not_called()

    # Scopo: Il filtro ritardo_giorni ("aperti da oltre N giorni", DL-17) e'
    #        inoltrato al repository (soglia del SOLO drill-down).
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_aperto_documenti",
        return_value=([], 0),
    )
    @patch.object(
        vendite_service.ParameterService, "get_default_date",
        return_value=date(2020, 1, 1),
    )
    def test_documenti_ritardo_giorni_inoltrato(self, _mock_param, mock_repo):
        fn_dash_aperto_documenti(ritardo_giorni=60)
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual(kwargs["ritardo_giorni"], 60)

    # Scopo: ritardo_giorni omesso -> None al repository (nessuna soglia:
    #        drill-down completo, coerente con le card fotografia). Senza
    #        filtri area/fase il repository li riceve None.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_aperto_documenti",
        return_value=([], 0),
    )
    def test_documenti_ritardo_giorni_default_none(self, mock_repo):
        fn_dash_aperto_documenti()
        kwargs = mock_repo.call_args.kwargs
        self.assertIsNone(kwargs["area"])
        self.assertIsNone(kwargs["fase"])
        self.assertIsNone(kwargs["ritardo_giorni"])

    # Scopo: ritardo_giorni non-positivo -> E_VENDITE_VALIDATION (niente
    #        normalizzazione silenziosa di una soglia priva di senso).
    def test_documenti_ritardo_giorni_non_positivo(self):
        for valore in (0, -5):
            with self.assertRaises(ServiceError) as ctx:
                fn_dash_aperto_documenti(ritardo_giorni=valore)
            self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: Il pavimento VENDITE_DASHBOARD_RITARDO_DATA_MINIMA e' compreso:
    #        oggi 2020-01-31, data minima 2020-01-01 -> 30 giorni passano
    #        (oggi - 30 = la data minima). Si legge il DEFAULT del parametro.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_aperto_documenti",
        return_value=([], 0),
    )
    @patch.object(vendite_service, "oggi_aziendale", return_value=date(2020, 1, 31))
    @patch.object(
        vendite_service.ParameterService, "get_default_date",
        return_value=date(2020, 1, 1),
    )
    def test_documenti_ritardo_giorni_sul_pavimento_passa(
        self, mock_param, _mock_oggi, mock_repo,
    ):
        fn_dash_aperto_documenti(ritardo_giorni=30)
        mock_param.assert_called_once_with("VENDITE_DASHBOARD_RITARDO_DATA_MINIMA")
        self.assertEqual(mock_repo.call_args.kwargs["ritardo_giorni"], 30)

    # Scopo: Un giorno oltre il pavimento -> E_VENDITE_VALIDATION, col detail
    #        che nomina la data minima; il repository non viene chiamato.
    @patch.object(vendite_service.VenditeRepository, "list_dash_aperto_documenti")
    @patch.object(vendite_service, "oggi_aziendale", return_value=date(2020, 1, 31))
    @patch.object(
        vendite_service.ParameterService, "get_default_date",
        return_value=date(2020, 1, 1),
    )
    def test_documenti_ritardo_giorni_oltre_pavimento(
        self, _mock_param, _mock_oggi, mock_repo,
    ):
        with self.assertRaises(ServiceError) as ctx:
            fn_dash_aperto_documenti(ritardo_giorni=31)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertIn("2020-01-01", ctx.exception.detail)
        mock_repo.assert_not_called()

    # Scopo: Il caso che dava il 500 (DataError `timestamp too small` con
    #        N = 2000000): ora e' un 400, e senza OverflowError lato Python
    #        (il confronto e' fra interi di giorni).
    @patch.object(vendite_service.VenditeRepository, "list_dash_aperto_documenti")
    @patch.object(
        vendite_service.ParameterService, "get_default_date",
        return_value=date(2020, 1, 1),
    )
    def test_documenti_ritardo_giorni_enorme_e_400(self, _mock_param, mock_repo):
        with self.assertRaises(ServiceError) as ctx:
            fn_dash_aperto_documenti(ritardo_giorni=2_000_000)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        mock_repo.assert_not_called()

    # Scopo: anzianita_giorni (derivata dal repo in SELECT) transita
    #        nell'envelope senza rielaborazione lato service.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_aperto_documenti",
        return_value=([{"documento_id": 1, "anzianita_giorni": 42}], 1),
    )
    def test_documenti_anzianita_giorni_passthrough(self, _mock_repo):
        data = fn_dash_aperto_documenti(area="PREVENTIVO")
        self.assertEqual(data["results"][0]["anzianita_giorni"], 42)

    # Scopo: la finestra arriva al repository come `limit`/`offset` (dal
    #        2026-10-21 un dialetto solo: la valida `pagina_da_query`, nella view).
    @patch.object(vendite_service.VenditeRepository, "list_dash_aperto_documenti", return_value=([], 0))
    def test_documenti_page_invalida(self, mock_repo):
        fn_dash_aperto_documenti(limit=10, offset=30)
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual((kwargs["limit"], kwargs["offset"]), (10, 30))

    # Scopo: Rientro da pagina stantia: il repository clampa l'offset in SQL
    #        (una sola valutazione della union) e il service dichiara
    #        nell'envelope la pagina EFFETTIVA servita, che il FE adotta.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_aperto_documenti",
        return_value=([{"documento_id": 1}], 10),
    )
    def test_documenti_pagina_stantia_clampata(self, _mock_repo):
        data = fn_dash_aperto_documenti(limit=50, offset=4900)
        self.assertEqual(data["count"], 10)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["total_pages"], 1)

    # Scopo: order_by/order_dir (whitelist) inoltrati al repository per
    #        l'ordinamento server-side su tutte le pagine.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_aperto_documenti",
        return_value=([], 0),
    )
    def test_documenti_ordinamento_inoltrato(self, mock_repo):
        fn_dash_aperto_documenti(order_by="valore_totale", order_dir="asc")
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual(kwargs["order_by"], "valore_totale")
        self.assertEqual(kwargs["order_dir"], "asc")

    # Scopo: order_by fuori whitelist -> E_VENDITE_VALIDATION (fail-fast 400,
    #        nessun input grezzo nell'ORDER BY).
    def test_documenti_order_by_non_valido(self):
        with self.assertRaises(ServiceError) as ctx:
            fn_dash_aperto_documenti(order_by="stato_codice; DROP")
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: order_dir diverso da asc/desc -> E_VENDITE_VALIDATION.
    def test_documenti_order_dir_non_valido(self):
        with self.assertRaises(ServiceError) as ctx:
            fn_dash_aperto_documenti(order_by="codice", order_dir="sideways")
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
