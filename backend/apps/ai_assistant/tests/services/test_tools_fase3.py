# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per i tool Fase 3 (anagrafiche, pratiche
#        dettaglio/flussi, operatori). Verifica registrazione,
#        schema e struttura output con service mockati.
# ------------------------------------------------------------

# Indice test:
# 1. test_cerca_soggetti_registered
# 2. test_dettaglio_soggetto_registered
# 3. test_dettaglio_pratica_registered
# 4. test_cerca_flussi_pratica_registered
# 5. test_cerca_operatori_registered
# 6. test_total_tools_count
# 7. test_cerca_soggetti_schema_has_search
# 8. test_dettaglio_pratica_requires_pratica_id
# 9. test_cerca_operatori_gemello_e_l_endpoint_admin

import unittest

from apps.ai_assistant.services import tool_registry
from apps.amm_software.api.views import OperatoriListView
from apps.anagrafiche.api.views_soggetti import SoggettiDetailView, SoggettiView
from apps.core.api.permissions import IsAdminZeroERP
from apps.pratiche.api.views import ApiPraticaDetail, ApiPraticaFlussiList


class TestFase3ToolRegistration(unittest.TestCase):
    """Verifica che tutti i tool Fase 3 siano registrati correttamente."""

    def setUp(self):
        tool_registry.clear_registry()
        tool_registry.populate_registry()

    def tearDown(self):
        tool_registry.clear_registry()

    # Scopo: cerca_soggetti deve essere registrato.
    def test_cerca_soggetti_registered(self):
        tool = tool_registry.get_tool_by_name("cerca_soggetti")
        self.assertIsNotNone(tool)
        self.assertIs(tool.endpoint.view, SoggettiView)

    # Scopo: dettaglio_soggetto deve essere registrato.
    def test_dettaglio_soggetto_registered(self):
        tool = tool_registry.get_tool_by_name("dettaglio_soggetto")
        self.assertIsNotNone(tool)
        self.assertIs(tool.endpoint.view, SoggettiDetailView)

    # Scopo: dettaglio_pratica deve essere registrato.
    def test_dettaglio_pratica_registered(self):
        tool = tool_registry.get_tool_by_name("dettaglio_pratica")
        self.assertIsNotNone(tool)
        self.assertIs(tool.endpoint.view, ApiPraticaDetail)

    # Scopo: cerca_flussi_pratica deve essere registrato.
    def test_cerca_flussi_pratica_registered(self):
        tool = tool_registry.get_tool_by_name("cerca_flussi_pratica")
        self.assertIsNotNone(tool)
        self.assertIs(tool.endpoint.view, ApiPraticaFlussiList)

    # Scopo: cerca_operatori deve essere registrato.
    def test_cerca_operatori_registered(self):
        tool = tool_registry.get_tool_by_name("cerca_operatori")
        self.assertIsNotNone(tool)
        self.assertIs(tool.endpoint.view, OperatoriListView)

    # Scopo: Verifica il conteggio totale tool registrati.
    def test_total_tools_count(self):
        all_tools = tool_registry.get_all_tools()
        # Fase 1: cerca_pratiche (1)
        # Fase 3: dettaglio_pratica, cerca_flussi_pratica (2)
        #         cerca_soggetti, dettaglio_soggetto (2)
        #         cerca_operatori (1)
        # Fase 4: crea_pratica, cambia_stato_pratica, aggiungi_nota_pratica (3)
        # Fase 5: cerca_billing_account (1)
        # Fase 6: cerca_articoli (1)
        # Fase 7: cerca_contratti, dettaglio_contratto (2)
        # Fase 8 (vendite estesa): cerca_preventivi, dettaglio_preventivo,
        #         cerca_promo_articoli, cerca_listini (4)
        # Fase 8 (documenti): cerca_documenti_generati (1)
        self.assertEqual(len(all_tools), 18)

    # Scopo: cerca_soggetti deve avere search nello schema.
    def test_cerca_soggetti_schema_has_search(self):
        tool = tool_registry.get_tool_by_name("cerca_soggetti")
        self.assertIn("search", tool.input_schema["properties"])

    # Scopo: dettaglio_pratica deve richiedere pratica_id.
    def test_dettaglio_pratica_requires_pratica_id(self):
        tool = tool_registry.get_tool_by_name("dettaglio_pratica")
        self.assertIn("pratica_id", tool.input_schema["required"])

    # Scopo: cerca_operatori e' «solo SUPER_ADMIN» perche' lo e' il suo
    #        gemello (una `AdminAPIView`), non per un'area inesistente
    #        (`amm_software`, fuori catalogo fino al 2026-09-24).
    def test_cerca_operatori_gemello_e_l_endpoint_admin(self):
        tool = tool_registry.get_tool_by_name("cerca_operatori")
        self.assertIs(tool.endpoint.view, OperatoriListView)
        self.assertEqual(tool.endpoint.metodo, "GET")
        self.assertIn(IsAdminZeroERP, OperatoriListView.permission_classes)
