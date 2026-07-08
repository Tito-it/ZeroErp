# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari service Lente 1 Competenza (mock repository).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) DashCompetenzaMensileServiceTests.test_griglia_12_mesi_4_stadi_sempre_completa
2) DashCompetenzaMensileServiceTests.test_contratto_simmetrico_celle_vuote
3) DashCompetenzaMensileServiceTests.test_ordine_stadi_funnel
4) DashCompetenzaMensileServiceTests.test_pivot_fatturata_somma_e_breakdown
5) DashCompetenzaMensileServiceTests.test_stadio_non_fatturato_proiettato
6) DashCompetenzaMensileServiceTests.test_totali_mese_db6
7) DashCompetenzaMensileServiceTests.test_stadio_sconosciuto_accodato_fail_visible
8) DashCompetenzaMensileServiceTests.test_errori_per_mese
9) DashCompetenzaMensileServiceTests.test_anno_fuori_range_min
10) DashCompetenzaMensileServiceTests.test_anno_fuori_range_max
9) DashCompetenzaAttivitaServiceTests.test_attivita_ok_envelope_paginato
10) DashCompetenzaAttivitaServiceTests.test_attivita_stadio_invalido
11) DashCompetenzaAttivitaServiceTests.test_attivita_competenza_normalizzata_al_primo
12) DashCompetenzaAttivitaServiceTests.test_attivita_solo_ritardo_passthrough
13) DashCompetenzaAttivitaServiceTests.test_attivita_page_invalida
13a) DashCompetenzaAttivitaServiceTests.test_attivita_ordinamento_inoltrato
13b) DashCompetenzaAttivitaServiceTests.test_attivita_order_by_non_valido
13c) DashCompetenzaAttivitaServiceTests.test_attivita_order_dir_non_valido
14) DashCompetenzaErroriServiceTests.test_errori_ok_envelope_paginato
15) DashCompetenzaErroriServiceTests.test_errori_competenza_opzionale_none
16) DashCompetenzaErroriServiceTests.test_errori_competenza_normalizzata_al_primo
"""

from datetime import date
from unittest import TestCase
from unittest.mock import patch

from apps.core.services.service_errors import ServiceError
from apps.vendite.services import vendite_service
from apps.vendite.services.vendite_service import (
    fn_dash_competenza_attivita,
    fn_dash_competenza_errori,
    fn_dash_competenza_mensile,
)

# Due righe FATTURATA di gennaio (una per stato fattura) + una DA_EMETTERE:
# esercitano insieme la somma per stadio e il breakdown 3a.
_ROWS_GENNAIO = [
    {
        "competenza_mese": "2026-01-01",
        "stadio": "DA_EMETTERE",
        "stato_fattura_codice_interno": None,
        "stato_fattura_codice": None,
        "n_attivita": 2,
        "valore": "300.00",
        "valore_fatturato": "0",
        "n_in_ritardo": 0,
        "valore_in_ritardo": "0",
    },
    {
        "competenza_mese": "2026-01-01",
        "stadio": "FATTURATA",
        "stato_fattura_codice_interno": "DRAFT",
        "stato_fattura_codice": "DRAFT",
        "n_attivita": 3,
        "valore": "1000.00",
        "valore_fatturato": "990.00",
        "n_in_ritardo": 1,
        "valore_in_ritardo": "100.00",
    },
    {
        "competenza_mese": "2026-01-01",
        "stadio": "FATTURATA",
        "stato_fattura_codice_interno": "DEFINITIVA",
        "stato_fattura_codice": "DEFINITIVA",
        "n_attivita": 4,
        "valore": "2000.00",
        "valore_fatturato": "2010.50",
        "n_in_ritardo": 0,
        "valore_in_ritardo": "0",
    },
]


class DashCompetenzaMensileServiceTests(TestCase):
    # Scopo: La griglia ha sempre 12 mesi x 4 stadi anche a repository vuoto.
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_errori_mensile", return_value={})
    @patch.object(vendite_service.VenditeRepository, "list_dash_competenza_mensile", return_value=[])
    def test_griglia_12_mesi_4_stadi_sempre_completa(self, _mock_rows, _mock_err):
        data = fn_dash_competenza_mensile(anno=2026)
        self.assertEqual(data["anno"], 2026)
        self.assertEqual(len(data["mesi"]), 12)
        self.assertEqual(data["mesi"][0]["competenza_mese"], "2026-01-01")
        self.assertEqual(data["mesi"][11]["competenza_mese"], "2026-12-01")
        for mese in data["mesi"]:
            self.assertEqual(len(mese["stadi"]), 4)
            self.assertEqual(mese["n_errori"], 0)

    # Scopo: Contratto simmetrico: ogni cella vuota ha tutti i campi a zero
    #        (inclusa la misura display) e stati_fattura lista vuota; i totali
    #        del mese vuoto sono zeri espliciti (concentrico DL-8).
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_errori_mensile", return_value={})
    @patch.object(vendite_service.VenditeRepository, "list_dash_competenza_mensile", return_value=[])
    def test_contratto_simmetrico_celle_vuote(self, _mock_rows, _mock_err):
        data = fn_dash_competenza_mensile(anno=2026)
        for cella in data["mesi"][0]["stadi"]:
            self.assertEqual(cella["n_attivita"], 0)
            self.assertEqual(cella["valore"], "0")
            self.assertEqual(cella["valore_fatturato"], "0")
            self.assertEqual(cella["valore_display"], "0")
            self.assertEqual(cella["n_in_ritardo"], 0)
            self.assertEqual(cella["valore_in_ritardo"], "0")
            self.assertEqual(cella["stati_fattura"], [])
        totali = data["mesi"][0]["totali"]
        self.assertEqual(totali["valore_teorico"], "0")
        self.assertEqual(totali["valore_fatturato"], "0")
        self.assertEqual(totali["valore_da_fatturare"], "0")
        self.assertEqual(totali["n_in_ritardo"], 0)

    # Scopo: L'ordine degli stadi e' quello del funnel commessa → fattura.
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_errori_mensile", return_value={})
    @patch.object(vendite_service.VenditeRepository, "list_dash_competenza_mensile", return_value=[])
    def test_ordine_stadi_funnel(self, _mock_rows, _mock_err):
        data = fn_dash_competenza_mensile(anno=2026)
        ordine = [s["stadio"] for s in data["mesi"][0]["stadi"]]
        self.assertEqual(
            ordine,
            ["DA_APPROVARE", "DA_EMETTERE", "EMESSA_NON_FATTURATA", "FATTURATA"],
        )

    # Scopo: Le righe FATTURATA per stato si sommano nella cella stadio e
    #        alimentano il breakdown stati_fattura (blocco 3a, ordine repo).
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_errori_mensile", return_value={})
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_mensile",
        return_value=_ROWS_GENNAIO,
    )
    def test_pivot_fatturata_somma_e_breakdown(self, _mock_rows, _mock_err):
        data = fn_dash_competenza_mensile(anno=2026)
        gennaio = {s["stadio"]: s for s in data["mesi"][0]["stadi"]}
        fatturata = gennaio["FATTURATA"]
        self.assertEqual(fatturata["n_attivita"], 7)
        self.assertEqual(fatturata["valore"], "3000.00")
        self.assertEqual(fatturata["valore_fatturato"], "3000.50")
        # DB-6: la misura display del fatturato e' l'imponibile riga.
        self.assertEqual(fatturata["valore_display"], "3000.50")
        self.assertEqual(fatturata["n_in_ritardo"], 1)
        self.assertEqual(fatturata["valore_in_ritardo"], "100.00")
        self.assertEqual(len(fatturata["stati_fattura"]), 2)
        self.assertEqual(
            fatturata["stati_fattura"][0]["stato_fattura_codice_interno"], "DRAFT"
        )
        self.assertEqual(fatturata["stati_fattura"][0]["valore_fatturato"], "990.00")
        self.assertEqual(
            fatturata["stati_fattura"][1]["stato_fattura_codice_interno"], "DEFINITIVA"
        )
        # Febbraio non eredita nulla.
        febbraio = {s["stadio"]: s for s in data["mesi"][1]["stadi"]}
        self.assertEqual(febbraio["FATTURATA"]["n_attivita"], 0)

    # Scopo: Uno stadio non fatturato finisce nella cella giusta senza
    #        popolare il breakdown stati_fattura.
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_errori_mensile", return_value={})
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_mensile",
        return_value=_ROWS_GENNAIO,
    )
    def test_stadio_non_fatturato_proiettato(self, _mock_rows, _mock_err):
        data = fn_dash_competenza_mensile(anno=2026)
        gennaio = {s["stadio"]: s for s in data["mesi"][0]["stadi"]}
        da_emettere = gennaio["DA_EMETTERE"]
        self.assertEqual(da_emettere["n_attivita"], 2)
        self.assertEqual(da_emettere["valore"], "300.00")
        # DB-6: fuori dal fatturato la misura display resta il teorico.
        self.assertEqual(da_emettere["valore_display"], "300.00")
        self.assertEqual(da_emettere["stati_fattura"], [])

    # Scopo: I totali del mese seguono DB-6: fatturato = imponibile riga,
    #        da fatturare = teorico degli stadi non fatturati.
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_errori_mensile", return_value={})
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_mensile",
        return_value=_ROWS_GENNAIO,
    )
    def test_totali_mese_db6(self, _mock_rows, _mock_err):
        data = fn_dash_competenza_mensile(anno=2026)
        totali = data["mesi"][0]["totali"]
        self.assertEqual(totali["valore_teorico"], "3300.00")
        self.assertEqual(totali["valore_fatturato"], "3000.50")
        self.assertEqual(totali["valore_da_fatturare"], "300.00")
        self.assertEqual(totali["n_in_ritardo"], 1)

    # Scopo: Uno stadio emesso dalla vista ma fuori whitelist NON viene perso:
    #        accodato dopo i 4 noti (fail-visible) e conteggiato nei totali.
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_errori_mensile", return_value={})
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_mensile",
        return_value=[
            {
                "competenza_mese": "2026-01-01",
                "stadio": "STORNATA",
                "stato_fattura_codice_interno": None,
                "stato_fattura_codice": None,
                "n_attivita": 1,
                "valore": "50.00",
                "valore_fatturato": "0",
                "n_in_ritardo": 0,
                "valore_in_ritardo": "0",
            }
        ],
    )
    def test_stadio_sconosciuto_accodato_fail_visible(self, _mock_rows, _mock_err):
        data = fn_dash_competenza_mensile(anno=2026)
        gennaio = data["mesi"][0]
        stadi = [s["stadio"] for s in gennaio["stadi"]]
        self.assertEqual(
            stadi,
            ["DA_APPROVARE", "DA_EMETTERE", "EMESSA_NON_FATTURATA", "FATTURATA", "STORNATA"],
        )
        self.assertEqual(gennaio["stadi"][4]["n_attivita"], 1)
        self.assertEqual(gennaio["totali"]["valore_teorico"], "50.00")
        self.assertEqual(gennaio["totali"]["valore_da_fatturare"], "50.00")
        # Gli altri mesi restano a 4 stadi.
        self.assertEqual(len(data["mesi"][1]["stadi"]), 4)

    # Scopo: Il conteggio errori vivi arriva nel mese giusto (blocco 4).
    @patch.object(
        vendite_service.VenditeRepository,
        "count_dash_competenza_errori_mensile",
        return_value={"2026-03-01": 2},
    )
    @patch.object(vendite_service.VenditeRepository, "list_dash_competenza_mensile", return_value=[])
    def test_errori_per_mese(self, _mock_rows, _mock_err):
        data = fn_dash_competenza_mensile(anno=2026)
        self.assertEqual(data["mesi"][2]["n_errori"], 2)
        self.assertEqual(data["mesi"][0]["n_errori"], 0)

    # Scopo: Anno sotto il minimo -> E_VENDITE_VALIDATION.
    def test_anno_fuori_range_min(self):
        with self.assertRaises(ServiceError) as ctx:
            fn_dash_competenza_mensile(anno=1999)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: Anno sopra il massimo -> E_VENDITE_VALIDATION.
    def test_anno_fuori_range_max(self):
        with self.assertRaises(ServiceError) as ctx:
            fn_dash_competenza_mensile(anno=2101)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")


class DashCompetenzaAttivitaServiceTests(TestCase):
    # Scopo: Envelope paginato standard con i risultati del repository.
    #        Nessun auth_user_id: lo scope e' interamente DB-side (GUC vista).
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_attivita",
        return_value=([{"commessa_attivita_id": 1}], 1),
    )
    def test_attivita_ok_envelope_paginato(self, mock_repo):
        data = fn_dash_competenza_attivita(
            competenza_mese=date(2026, 5, 1), stadio="FATTURATA"
        )
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["total_pages"], 1)
        self.assertEqual(data["results"], [{"commessa_attivita_id": 1}])
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual(kwargs["stadio"], "FATTURATA")
        self.assertNotIn("auth_user_id", kwargs)

    # Scopo: Stadio fuori whitelist -> E_VENDITE_VALIDATION.
    def test_attivita_stadio_invalido(self):
        with self.assertRaises(ServiceError) as ctx:
            fn_dash_competenza_attivita(
                competenza_mese=date(2026, 5, 1), stadio="TRANSITATA"
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: La competenza viene normalizzata al 1° del mese.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_attivita",
        return_value=([], 0),
    )
    def test_attivita_competenza_normalizzata_al_primo(self, mock_repo):
        fn_dash_competenza_attivita(competenza_mese=date(2026, 5, 17))
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual(kwargs["competenza_mese"], date(2026, 5, 1))
        # Senza filtro stadio il repository riceve None (tutti gli stadi).
        self.assertIsNone(kwargs["stadio"])
        self.assertFalse(kwargs["solo_ritardo"])

    # Scopo: Il filtro recuperi tardivi viene inoltrato al repository.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_attivita",
        return_value=([], 0),
    )
    def test_attivita_solo_ritardo_passthrough(self, mock_repo):
        fn_dash_competenza_attivita(
            competenza_mese=date(2026, 5, 1), solo_ritardo=True
        )
        kwargs = mock_repo.call_args.kwargs
        self.assertTrue(kwargs["solo_ritardo"])

    # Scopo: Paginazione invalida -> E_VENDITE_VALIDATION (validate_pagination).
    def test_attivita_page_invalida(self):
        with self.assertRaises(ServiceError) as ctx:
            fn_dash_competenza_attivita(competenza_mese=date(2026, 5, 1), page=0)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: order_by/order_dir (whitelist) inoltrati al repository per
    #        l'ordinamento server-side su tutte le pagine.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_attivita",
        return_value=([], 0),
    )
    def test_attivita_ordinamento_inoltrato(self, mock_repo):
        fn_dash_competenza_attivita(
            competenza_mese=date(2026, 5, 1),
            order_by="data_attivita",
            order_dir="asc",
        )
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual(kwargs["order_by"], "data_attivita")
        self.assertEqual(kwargs["order_dir"], "asc")

    # Scopo: order_by fuori whitelist -> E_VENDITE_VALIDATION (fail-fast 400).
    def test_attivita_order_by_non_valido(self):
        with self.assertRaises(ServiceError) as ctx:
            fn_dash_competenza_attivita(
                competenza_mese=date(2026, 5, 1), order_by="quantita; DROP"
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: order_dir diverso da asc/desc -> E_VENDITE_VALIDATION.
    def test_attivita_order_dir_non_valido(self):
        with self.assertRaises(ServiceError) as ctx:
            fn_dash_competenza_attivita(
                competenza_mese=date(2026, 5, 1),
                order_by="valore",
                order_dir="up",
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")


class DashCompetenzaErroriServiceTests(TestCase):
    # Scopo: Envelope paginato standard con i risultati del repository.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_errori",
        return_value=([{"tipo_evento": "TASK_ERRORE"}], 1),
    )
    def test_errori_ok_envelope_paginato(self, mock_repo):
        data = fn_dash_competenza_errori(competenza_mese=date(2026, 5, 1))
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"], [{"tipo_evento": "TASK_ERRORE"}])
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual(kwargs["competenza_mese"], date(2026, 5, 1))

    # Scopo: Senza competenza il repository riceve None (tutti i mesi).
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_errori",
        return_value=([], 0),
    )
    def test_errori_competenza_opzionale_none(self, mock_repo):
        fn_dash_competenza_errori()
        kwargs = mock_repo.call_args.kwargs
        self.assertIsNone(kwargs["competenza_mese"])

    # Scopo: La competenza (se presente) viene normalizzata al 1° del mese.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_errori",
        return_value=([], 0),
    )
    def test_errori_competenza_normalizzata_al_primo(self, mock_repo):
        fn_dash_competenza_errori(competenza_mese=date(2026, 5, 17))
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual(kwargs["competenza_mese"], date(2026, 5, 1))
