# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari service Lente 2 Backlog (mock repository).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) DashBacklogRiepilogoServiceTests.test_tre_classi_sempre_presenti_ordine_ui
2) DashBacklogRiepilogoServiceTests.test_contratto_simmetrico_classi_vuote
3) DashBacklogRiepilogoServiceTests.test_pivot_classe_somma_aree
4) DashBacklogRiepilogoServiceTests.test_classe_sconosciuta_accodata_fail_visible
5) DashBacklogDocumentiServiceTests.test_documenti_ok_envelope_paginato
6) DashBacklogDocumentiServiceTests.test_documenti_classe_sconosciuta_passthrough
7) DashBacklogDocumentiServiceTests.test_documenti_area_invalida
8) DashBacklogDocumentiServiceTests.test_documenti_aree_ddt_resi_valide
9) DashBacklogDocumentiServiceTests.test_documenti_filtri_none_passthrough
10) DashBacklogDocumentiServiceTests.test_documenti_page_invalida
11) DashBacklogDocumentiServiceTests.test_documenti_ordinamento_inoltrato
12) DashBacklogDocumentiServiceTests.test_documenti_order_by_non_valido
13) DashBacklogDocumentiServiceTests.test_documenti_order_dir_non_valido
14) DashBacklogDocumentiServiceTests.test_documenti_ritardo_giorni_inoltrato
15) DashBacklogDocumentiServiceTests.test_documenti_ritardo_giorni_non_positivo
16) DashBacklogDocumentiServiceTests.test_documenti_ritardo_giorni_sul_pavimento_passa
17) DashBacklogDocumentiServiceTests.test_documenti_ritardo_giorni_oltre_pavimento
"""

from datetime import date
from unittest import TestCase
from unittest.mock import patch

from apps.core.services.service_errors import ServiceError
from apps.vendite.services import vendite_service
from apps.vendite.services.vendite_service import (
    fn_dash_backlog_documenti,
    fn_dash_backlog_riepilogo,
)

# Due aree della stessa classe + una classe a conteggi: esercitano insieme la
# somma per classe (valore/unita'/anzianita' max) e il dettaglio aree.
_ROWS_RIEPILOGO = [
    {
        "classe": "RECUPERABILE",
        "area": "PREVENTIVO",
        "n_documenti": 3,
        "valore_fermo_tot": "1500.00",
        "unita_ferme_tot": 5,
        "anzianita_max_giorni": 40,
    },
    {
        "classe": "RECUPERABILE",
        "area": "ORDINE_VENDITA",
        "n_documenti": 2,
        "valore_fermo_tot": "500.50",
        "unita_ferme_tot": 2,
        "anzianita_max_giorni": 90,
    },
    {
        "classe": "ANOMALIA",
        "area": "OFFERTA_COMMERCIALE",
        "n_documenti": 1,
        "valore_fermo_tot": None,
        "unita_ferme_tot": 1,
        "anzianita_max_giorni": 12,
    },
]


class DashBacklogRiepilogoServiceTests(TestCase):
    # Scopo: Le 3 classi sono sempre presenti nell'ordine UI del design
    #        (recuperabile, sollecito cliente, anomalia) anche a repo vuoto.
    @patch.object(vendite_service.VenditeRepository, "list_dash_backlog_riepilogo", return_value=[])
    def test_tre_classi_sempre_presenti_ordine_ui(self, _mock_repo):
        data = fn_dash_backlog_riepilogo()
        ordine = [c["classe"] for c in data["classi"]]
        self.assertEqual(ordine, ["RECUPERABILE", "SOLLECITO_CLIENTE", "ANOMALIA"])

    # Scopo: Contratto simmetrico: classe vuota con zeri espliciti, aree [] e
    #        anzianita' None (eta' sconosciuta != 0 giorni).
    @patch.object(vendite_service.VenditeRepository, "list_dash_backlog_riepilogo", return_value=[])
    def test_contratto_simmetrico_classi_vuote(self, _mock_repo):
        data = fn_dash_backlog_riepilogo()
        for classe in data["classi"]:
            self.assertEqual(classe["n_documenti"], 0)
            self.assertEqual(classe["valore_fermo_tot"], "0")
            self.assertEqual(classe["unita_ferme_tot"], 0)
            self.assertIsNone(classe["anzianita_max_giorni"])
            self.assertEqual(classe["aree"], [])

    # Scopo: Le righe area della stessa classe si sommano (valore Decimal,
    #        unita', max anzianita') e restano nel dettaglio aree.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_backlog_riepilogo",
        return_value=_ROWS_RIEPILOGO,
    )
    def test_pivot_classe_somma_aree(self, _mock_repo):
        data = fn_dash_backlog_riepilogo()
        classi = {c["classe"]: c for c in data["classi"]}
        rec = classi["RECUPERABILE"]
        self.assertEqual(rec["n_documenti"], 5)
        self.assertEqual(rec["valore_fermo_tot"], "2000.50")
        self.assertEqual(rec["unita_ferme_tot"], 7)
        self.assertEqual(rec["anzianita_max_giorni"], 90)
        self.assertEqual(len(rec["aree"]), 2)
        self.assertEqual(rec["aree"][0]["area"], "PREVENTIVO")
        # Classe con valore NULL (aree a conteggi): il totale resta "0".
        anomalia = classi["ANOMALIA"]
        self.assertEqual(anomalia["n_documenti"], 1)
        self.assertEqual(anomalia["valore_fermo_tot"], "0")
        # Classe senza righe resta a zero.
        self.assertEqual(classi["SOLLECITO_CLIENTE"]["n_documenti"], 0)

    # Scopo: Una classe emessa dalla vista ma fuori whitelist NON viene persa:
    #        accodata dopo le 3 note (fail-visible).
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_backlog_riepilogo",
        return_value=[
            {
                "classe": "NUOVA_CLASSE",
                "area": "ORDINE_VENDITA",
                "n_documenti": 1,
                "valore_fermo_tot": "10.00",
                "unita_ferme_tot": 1,
                "anzianita_max_giorni": 3,
            }
        ],
    )
    def test_classe_sconosciuta_accodata_fail_visible(self, _mock_repo):
        data = fn_dash_backlog_riepilogo()
        ordine = [c["classe"] for c in data["classi"]]
        self.assertEqual(
            ordine,
            ["RECUPERABILE", "SOLLECITO_CLIENTE", "ANOMALIA", "NUOVA_CLASSE"],
        )
        self.assertEqual(data["classi"][3]["n_documenti"], 1)


class DashBacklogDocumentiServiceTests(TestCase):
    # Scopo: Envelope paginato standard con i risultati del repository.
    #        Nessun auth_user_id: lo scope e' interamente DB-side.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_backlog_documenti",
        return_value=([{"documento_id": 1}], 1),
    )
    def test_documenti_ok_envelope_paginato(self, mock_repo):
        data = fn_dash_backlog_documenti(classe="RECUPERABILE", area="PREVENTIVO")
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["total_pages"], 1)
        self.assertEqual(data["results"], [{"documento_id": 1}])
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual(kwargs["classe"], "RECUPERABILE")
        self.assertEqual(kwargs["area"], "PREVENTIVO")
        self.assertNotIn("auth_user_id", kwargs)

    # Scopo: Il filtro classe NON e' whitellistato (coerenza fail-visible col
    #        riepilogo): una classe sconosciuta passa al repository e produce
    #        lista vuota, mai 400 — cosi' le classi future restano drillabili.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_backlog_documenti",
        return_value=([], 0),
    )
    def test_documenti_classe_sconosciuta_passthrough(self, mock_repo):
        data = fn_dash_backlog_documenti(classe="NUOVA_CLASSE")
        self.assertEqual(data["count"], 0)
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual(kwargs["classe"], "NUOVA_CLASSE")

    # Scopo: Area fuori whitelist -> E_VENDITE_VALIDATION.
    def test_documenti_area_invalida(self):
        with self.assertRaises(ServiceError) as ctx:
            fn_dash_backlog_documenti(area="FATTURE")
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: DDT e RESI sono aree valide del backlog (sesta area della union +
    #        ramo resi, DL-21/24): il drill-down NON deve dare 400 — era la
    #        regressione "card che non si aprono" (brief BE/FE §2 BE-1).
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_backlog_documenti",
        return_value=([], 0),
    )
    def test_documenti_aree_ddt_resi_valide(self, mock_repo):
        for area in ("DDT_VENDITA", "RESO_VENDITA"):
            with self.subTest(area=area):
                fn_dash_backlog_documenti(area=area)
                self.assertEqual(mock_repo.call_args.kwargs["area"], area)

    # Scopo: Senza filtri il repository riceve None (tutte le classi/aree).
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_backlog_documenti",
        return_value=([], 0),
    )
    def test_documenti_filtri_none_passthrough(self, mock_repo):
        fn_dash_backlog_documenti()
        kwargs = mock_repo.call_args.kwargs
        self.assertIsNone(kwargs["classe"])
        self.assertIsNone(kwargs["area"])
        self.assertIsNone(kwargs["ritardo_giorni"])

    # Scopo: il filtro "fermo da oltre N giorni" e' inoltrato al repository
    #        (stessa semantica del ritardo della Situazione aperta).
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_backlog_documenti",
        return_value=([], 0),
    )
    @patch.object(
        vendite_service.ParameterService, "get_default_date",
        return_value=date(2020, 1, 1),
    )
    def test_documenti_ritardo_giorni_inoltrato(self, _mock_param, mock_repo):
        fn_dash_backlog_documenti(ritardo_giorni=60)
        self.assertEqual(mock_repo.call_args.kwargs["ritardo_giorni"], 60)

    # Scopo: ritardo_giorni non-positivo -> E_VENDITE_VALIDATION (nessuna
    #        normalizzazione silenziosa: una soglia <= 0 non ha senso).
    def test_documenti_ritardo_giorni_non_positivo(self):
        for valore in (0, -5):
            with self.assertRaises(ServiceError) as ctx:
                fn_dash_backlog_documenti(ritardo_giorni=valore)
            self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: Il pavimento VENDITE_DASHBOARD_RITARDO_DATA_MINIMA vale anche qui
    #        (stesso helper della Situazione aperta): sul pavimento passa.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_backlog_documenti",
        return_value=([], 0),
    )
    @patch.object(vendite_service, "oggi_aziendale", return_value=date(2020, 1, 31))
    @patch.object(
        vendite_service.ParameterService, "get_default_date",
        return_value=date(2020, 1, 1),
    )
    def test_documenti_ritardo_giorni_sul_pavimento_passa(
        self, _mock_param, _mock_oggi, mock_repo,
    ):
        fn_dash_backlog_documenti(ritardo_giorni=30)
        self.assertEqual(mock_repo.call_args.kwargs["ritardo_giorni"], 30)

    # Scopo: Un giorno oltre il pavimento -> E_VENDITE_VALIDATION.
    @patch.object(vendite_service.VenditeRepository, "list_dash_backlog_documenti")
    @patch.object(vendite_service, "oggi_aziendale", return_value=date(2020, 1, 31))
    @patch.object(
        vendite_service.ParameterService, "get_default_date",
        return_value=date(2020, 1, 1),
    )
    def test_documenti_ritardo_giorni_oltre_pavimento(
        self, _mock_param, _mock_oggi, mock_repo,
    ):
        with self.assertRaises(ServiceError) as ctx:
            fn_dash_backlog_documenti(ritardo_giorni=31)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        mock_repo.assert_not_called()

    # Scopo: la finestra arriva al repository come `limit`/`offset` (dal
    #        2026-10-21 un dialetto solo: la valida `pagina_da_query`, nella view).
    @patch.object(vendite_service.VenditeRepository, "list_dash_backlog_documenti", return_value=([], 0))
    def test_documenti_page_invalida(self, mock_repo):
        fn_dash_backlog_documenti(limit=10, offset=30)
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual((kwargs["limit"], kwargs["offset"]), (10, 30))

    # Scopo: order_by/order_dir (whitelist) inoltrati al repository per
    #        l'ordinamento server-side su tutte le pagine.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_backlog_documenti",
        return_value=([], 0),
    )
    def test_documenti_ordinamento_inoltrato(self, mock_repo):
        fn_dash_backlog_documenti(order_by="stato_codice", order_dir="asc")
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual(kwargs["order_by"], "stato_codice")
        self.assertEqual(kwargs["order_dir"], "asc")

    # Scopo: order_by fuori whitelist -> E_VENDITE_VALIDATION (fail-fast 400).
    def test_documenti_order_by_non_valido(self):
        with self.assertRaises(ServiceError) as ctx:
            fn_dash_backlog_documenti(order_by="motivo_fermo; DROP")
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: order_dir diverso da asc/desc -> E_VENDITE_VALIDATION.
    def test_documenti_order_dir_non_valido(self):
        with self.assertRaises(ServiceError) as ctx:
            fn_dash_backlog_documenti(order_by="codice", order_dir="random")
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
