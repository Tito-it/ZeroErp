# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari service dashboard fatturazione (mock repository).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) DashFatturazioneMensileServiceTests.test_matrice_12_mesi_5_aree_sempre_completa
2) DashFatturazioneMensileServiceTests.test_zeri_euro_vs_null_conteggi
3) DashFatturazioneMensileServiceTests.test_dati_repository_proiettati_nella_cella
4) DashFatturazioneMensileServiceTests.test_ordine_aree_funnel
5) DashFatturazioneMensileServiceTests.test_anno_fuori_range_min
6) DashFatturazioneMensileServiceTests.test_anno_fuori_range_max
7) DashFatturazioneFermiServiceTests.test_fermi_ok_envelope_paginato
8) DashFatturazioneFermiServiceTests.test_fermi_area_invalida
9) DashFatturazioneFermiServiceTests.test_fermi_competenza_normalizzata_al_primo
10) DashFatturazioneFermiServiceTests.test_fermi_page_invalida
"""

from datetime import date
from unittest import TestCase
from unittest.mock import patch

from apps.core.services.service_errors import ServiceError
from apps.vendite.services import vendite_service
from apps.vendite.services.vendite_service import (
    fn_dash_fatturazione_fermi,
    fn_dash_fatturazione_mensile,
)

_ROW_GENNAIO_PREVENTIVI = {
    "competenza_mese": "2026-01-01",
    "area": "PREVENTIVI",
    "valore_totale": "1500.00",
    "valore_transitato": "1200.00",
    "n_documenti": 4,
    "n_transitati": 3,
    "n_fermi": 1,
    "n_abortiti": 2,
}


class DashFatturazioneMensileServiceTests(TestCase):
    # Scopo: La matrice ha sempre 12 mesi x 5 aree anche a repository vuoto.
    @patch.object(vendite_service.VenditeRepository, "list_dash_fatturazione_mensile", return_value=[])
    def test_matrice_12_mesi_5_aree_sempre_completa(self, _mock_repo):
        data = fn_dash_fatturazione_mensile(anno=2026)
        self.assertEqual(data["anno"], 2026)
        self.assertEqual(len(data["mesi"]), 12)
        self.assertEqual(data["mesi"][0]["competenza_mese"], "2026-01-01")
        self.assertEqual(data["mesi"][11]["competenza_mese"], "2026-12-01")
        for mese in data["mesi"]:
            self.assertEqual(len(mese["aree"]), 5)

    # Scopo: Aree euro vuote -> valore "0"; aree a conteggi -> valore None.
    @patch.object(vendite_service.VenditeRepository, "list_dash_fatturazione_mensile", return_value=[])
    def test_zeri_euro_vs_null_conteggi(self, _mock_repo):
        data = fn_dash_fatturazione_mensile(anno=2026)
        aree = {a["area"]: a for a in data["mesi"][0]["aree"]}
        self.assertEqual(aree["PREVENTIVI"]["valore_totale"], "0")
        self.assertEqual(aree["ORDINI"]["valore_transitato"], "0")
        self.assertEqual(aree["COMMESSE"]["valore_totale"], "0")
        self.assertIsNone(aree["OFFERTE"]["valore_totale"])
        self.assertIsNone(aree["CONTRATTI"]["valore_totale"])
        self.assertEqual(aree["PREVENTIVI"]["n_documenti"], 0)
        self.assertEqual(aree["OFFERTE"]["n_fermi"], 0)

    # Scopo: Una riga repository finisce nella cella giusta della matrice.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_fatturazione_mensile",
        return_value=[_ROW_GENNAIO_PREVENTIVI],
    )
    def test_dati_repository_proiettati_nella_cella(self, _mock_repo):
        data = fn_dash_fatturazione_mensile(anno=2026)
        gennaio = {a["area"]: a for a in data["mesi"][0]["aree"]}
        self.assertEqual(gennaio["PREVENTIVI"]["valore_totale"], "1500.00")
        self.assertEqual(gennaio["PREVENTIVI"]["valore_transitato"], "1200.00")
        self.assertEqual(gennaio["PREVENTIVI"]["n_documenti"], 4)
        self.assertEqual(gennaio["PREVENTIVI"]["n_abortiti"], 2)
        # Le altre celle di gennaio restano a zero.
        self.assertEqual(gennaio["ORDINI"]["n_documenti"], 0)
        # Febbraio non eredita nulla.
        febbraio = {a["area"]: a for a in data["mesi"][1]["aree"]}
        self.assertEqual(febbraio["PREVENTIVI"]["n_documenti"], 0)

    # Scopo: L'ordine delle aree e' quello del funnel, non alfabetico.
    @patch.object(vendite_service.VenditeRepository, "list_dash_fatturazione_mensile", return_value=[])
    def test_ordine_aree_funnel(self, _mock_repo):
        data = fn_dash_fatturazione_mensile(anno=2026)
        ordine = [a["area"] for a in data["mesi"][0]["aree"]]
        self.assertEqual(
            ordine, ["PREVENTIVI", "ORDINI", "OFFERTE", "CONTRATTI", "COMMESSE"]
        )

    # Scopo: Anno sotto il minimo -> E_VENDITE_VALIDATION.
    def test_anno_fuori_range_min(self):
        with self.assertRaises(ServiceError) as ctx:
            fn_dash_fatturazione_mensile(anno=1999)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: Anno sopra il massimo -> E_VENDITE_VALIDATION.
    def test_anno_fuori_range_max(self):
        with self.assertRaises(ServiceError) as ctx:
            fn_dash_fatturazione_mensile(anno=2101)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")


class DashFatturazioneFermiServiceTests(TestCase):
    # Scopo: Envelope paginato standard con i risultati del repository.
    #        Nessun auth_user_id: lo scope e' interamente DB-side (RLS + GUC).
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_fatturazione_fermi",
        return_value=([{"documento_id": 1}], 1),
    )
    def test_fermi_ok_envelope_paginato(self, mock_repo):
        data = fn_dash_fatturazione_fermi(
            competenza_mese=date(2026, 5, 1), area="PREVENTIVI"
        )
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["total_pages"], 1)
        self.assertEqual(data["results"], [{"documento_id": 1}])
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual(kwargs["area"], "PREVENTIVI")
        # Il repository non riceve piu' auth_user_id (scope DB-side).
        self.assertNotIn("auth_user_id", kwargs)

    # Scopo: Area fuori whitelist -> E_VENDITE_VALIDATION.
    def test_fermi_area_invalida(self):
        with self.assertRaises(ServiceError) as ctx:
            fn_dash_fatturazione_fermi(
                competenza_mese=date(2026, 5, 1), area="FATTURE"
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: La competenza viene normalizzata al 1° del mese.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_fatturazione_fermi",
        return_value=([], 0),
    )
    def test_fermi_competenza_normalizzata_al_primo(self, mock_repo):
        fn_dash_fatturazione_fermi(
            competenza_mese=date(2026, 5, 17), area="ORDINI"
        )
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual(kwargs["competenza_mese"], date(2026, 5, 1))

    # Scopo: Paginazione invalida -> E_VENDITE_VALIDATION (validate_pagination).
    def test_fermi_page_invalida(self):
        with self.assertRaises(ServiceError) as ctx:
            fn_dash_fatturazione_fermi(
                competenza_mese=date(2026, 5, 1), area="ORDINI", page=0
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
