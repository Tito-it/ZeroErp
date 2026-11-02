# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La GIUNTURA del BB `richiedi_codice_a_vocabolario` coi vocabolari veri:
#        per ogni (tabella, colonna) che un filtro di lista nomina, un codice
#        che la tabella contiene passa e uno inventato e' il 400. Un nome di
#        tabella o di colonna sbagliato nel codice farebbe di OGNI filtro un
#        500 (o un 400 su ogni valore): i test unitari, col cursore mockato,
#        non lo vedono.
# ⚠️ Ogni consumatore nuovo del BB si iscrive qui (2026-10-20).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_ogni_vocabolario_esiste_e_rifiuta_l_inventato
"""

from __future__ import annotations

from unittest import TestCase

from django.db import connection

from apps.core.db._helpers import richiedi_codice_a_vocabolario
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto


# (tabella, colonna, consumatore) — i vocabolari a TABELLA dei filtri di lista.
_VOCABOLARI: tuple[tuple[str, str, str], ...] = (
    ("config.stati_doc_ddt", "codice_interno", "ddt_service.list_ddt_rows"),
    ("config.stati_doc_reso", "codice_interno", "resi_service.list_resi_rows"),
    ("config.stati_doc_preventivi", "codice_interno", "preventivi_service.list_preventivi_rows"),
    ("config.stati_doc_ordini", "codice_interno", "ordini_service.list_ordini_rows"),
    ("config.stati_doc_offerte", "codice_interno", "OfferteService.list_offerte"),
    ("config.stati_doc_fiscale", "codice_interno", "vendite_service.list_fatture_rows"),
    ("config.nature_doc_fiscale", "codice_interno", "vendite_service.list_fatture_rows"),
    ("config.tipi_entita", "codice", "vendite_service.get_giornale_trasversale"),
    ("pagamenti.vendite_contabili_stati", "codice_interno", "pagamenti_service.list_distinte"),
    ("config.sorgenti", "codice_interno", "vendite_service.fn_dash_aperto_documenti"),
)


class VocabolariDeiFiltriDbTests(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)

    def test_ogni_vocabolario_esiste_e_rifiuta_l_inventato(self) -> None:
        for tabella, colonna, consumatore in _VOCABOLARI:
            with self.subTest(consumatore=consumatore, tabella=tabella):
                with connection.cursor() as cur:
                    cur.execute(f"SELECT {colonna} FROM {tabella} LIMIT 1")
                    riga = cur.fetchone()
                self.assertIsNotNone(riga, f"{tabella} e' vuota: il vocabolario non c'e'")
                assert riga is not None
                self.assertEqual(richiedi_codice_a_vocabolario(
                    tabella, colonna, riga[0], codice_errore="E_VENDITE_VALIDATION", parametro="x",
                ), riga[0])
                with self.assertRaises(ServiceError):
                    richiedi_codice_a_vocabolario(
                        tabella, colonna, "__NON_ESISTE__", codice_errore="E_VENDITE_VALIDATION", parametro="x",
                    )
