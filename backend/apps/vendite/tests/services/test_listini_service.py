# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari funzioni listini_service.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) ListiniServiceTests.test_list_listini_invalid_order_by
2) ListiniServiceTests.test_get_listino_dettaglio_nests_children
3) ListiniServiceTests.test_create_listino_duplicate_code
4) ListiniServiceTests.test_get_versione_not_found
5) ListiniServiceTests.test_change_versione_state_invalid_transition
6) ListiniServiceTests.test_change_versione_state_requires_rows
7) ListiniServiceTests.test_create_riga_invalid_articolo_uom
8) ListiniServiceTests.test_test_resolver_requires_uom
"""

from unittest import TestCase
from unittest.mock import patch

from django.db import IntegrityError

from apps.core.services.service_errors import ServiceError


class ListiniServiceTests(TestCase):
    # Scopo: Verifica validazione sort_by non ammesso.
    def test_list_listini_invalid_order_by(self):
        from apps.vendite.services.listini_service import fn_list_listini

        with self.assertRaises(ServiceError) as ctx:
            fn_list_listini(order_by="invalid")
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: Verifica che il dettaglio listino includa versioni e associazioni.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_get_listino_dettaglio_nests_children(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_get_listino_dettaglio

        repo = mock_repo_cls.return_value
        repo.get_listino.return_value = {"id": 10, "codice": "LIST-UTILITY"}
        repo.list_versioni.return_value = [{"id": 101}]
        repo.list_associazioni.return_value = [{"id": 301}]

        result = fn_get_listino_dettaglio(10)

        self.assertEqual(result["versioni"], [{"id": 101}])
        self.assertEqual(result["associazioni"], [{"id": 301}])

    # Scopo: Verifica traduzione duplicate code su create listino.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_create_listino_duplicate_code(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_create_listino

        mock_repo_cls.return_value.create_listino.side_effect = IntegrityError("uq_listini_codice")

        with self.assertRaises(ServiceError) as ctx:
            fn_create_listino(
                {"codice": "LIST-UTILITY", "descrizione": "Listino Utility Base", "dominio": "UTILITY"}
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: Verifica not found su dettaglio versione.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_get_versione_not_found(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_get_versione

        mock_repo_cls.return_value.get_versione.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            fn_get_versione(10, 101)
        self.assertEqual(ctx.exception.code, "E_VENDITE_LISTINO_VERSIONE_NOT_FOUND")

    # Scopo: Verifica transizione stato non ammessa.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_change_versione_state_invalid_transition(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_change_versione_state

        mock_repo_cls.return_value.get_versione.return_value = {
            "id": 101,
            "listino_id": 10,
            "stato": "BOZZA",
            "attivo": True,
        }

        with self.assertRaises(ServiceError) as ctx:
            fn_change_versione_state(10, 101, {"stato": "CHIUSA"})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: Verifica che ATTIVA richieda almeno una riga.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_change_versione_state_requires_rows(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_change_versione_state

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {
            "id": 101,
            "listino_id": 10,
            "stato": "BOZZA",
            "attivo": True,
        }
        repo.count_active_righe_versione.return_value = 0

        with self.assertRaises(ServiceError) as ctx:
            fn_change_versione_state(10, 101, {"stato": "ATTIVA"})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: Verifica blocco riga con articolo/UoM non coerenti.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_create_riga_invalid_articolo_uom(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_create_riga

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {"id": 101, "listino_id": 10}
        repo.get_articolo_uom_validation.return_value = {
            "articolo_attivo": True,
            "uom_attiva": True,
            "uom_compatibile": False,
        }

        with self.assertRaises(ServiceError) as ctx:
            fn_create_riga(
                10,
                101,
                {
                    "articolo_id": "019bbee2-5f6a-704f-bbd0-34ed84db252d",
                    "uom_id": 1,
                    "prezzo": "12.50",
                },
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: Verifica obbligatorieta` uom nel test resolver.
    def test_test_resolver_requires_uom(self):
        from apps.vendite.services.listini_service import fn_test_resolver_prezzo

        with self.assertRaises(ServiceError) as ctx:
            fn_test_resolver_prezzo(
                {
                    "articolo_id": "019bbee2-5f6a-704f-bbd0-34ed84db252d",
                    "data_riferimento": "2026-04-02",
                }
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
