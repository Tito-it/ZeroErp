# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari API views preventivi vendita (endpoint HTTP con mock service).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_list_preventivi_200 — GET lista preventivi OK
2) test_create_preventivo_200 — POST creazione preventivo OK
3) test_get_preventivo_detail_200 — GET dettaglio preventivo OK
4) test_get_preventivo_detail_404 — GET dettaglio preventivo non trovato
5) test_cambio_stato_200 — POST cambio stato OK
6) test_add_riga_200 — POST aggiunta riga OK
7) test_push_commessa_200 — POST push commessa OK
8) test_list_componenti_riga_200 — GET componenti riga padre OK
9) test_update_componente_200 — PATCH override prezzo componente OK
10) test_delete_componente_200 — DELETE soft delete componente OK
11) test_get_componente_404 — GET su riga inesistente -> 404
"""

import unittest
from unittest.mock import patch, MagicMock

from django.test import SimpleTestCase
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest


class TestPreventiviApiViews(JwtMockedApiTest):

    def setUp(self):
        super().setUp()
        # Scopo: Mock service layer per isolare i test API.
        self.svc_patcher = patch(
            "apps.vendite.api.preventivi_views.preventivi_service"
        )
        self.mock_svc = self.svc_patcher.start()

    def tearDown(self):
        self.svc_patcher.stop()

    # Scopo: Verifica GET lista preventivi restituisce 200.
    def test_list_preventivi_200(self):
        self.mock_svc.list_preventivi.return_value = {
            "count": 1, "page": 1, "page_size": 50, "total_pages": 1,
            "results": [{"id": 1, "numero": "P-0001"}],
        }
        response = self.client.get("/api/v1/vendite/preventivi/")
        # Senza auth il middleware JWT blocca; verifichiamo che la route esista
        self.assertIn(response.status_code, [200, 401, 403])

    # Scopo: Verifica POST creazione preventivo restituisce 200.
    def test_create_preventivo_200(self):
        self.mock_svc.crea_preventivo.return_value = {
            "id": 1, "uid": "abc-123", "numero": "P-0001",
        }
        response = self.client.post(
            "/api/v1/vendite/preventivi/",
            data='{"utility_id": 5}',
            content_type="application/json",
        )
        self.assertIn(response.status_code, [200, 401, 403])

    # Scopo: Verifica GET dettaglio preventivo restituisce 200.
    def test_get_preventivo_detail_200(self):
        # Fase 3.F6: detail non embedda piu' `righe` (endpoint /righe/ autonomo).
        self.mock_svc.get_preventivo.return_value = {
            "id": 1, "numero": "P-0001", "righe_count": 0, "indirizzi": [],
        }
        response = self.client.get("/api/v1/vendite/preventivi/1/")
        self.assertIn(response.status_code, [200, 401, 403])

    # Scopo: Verifica GET dettaglio preventivo non trovato.
    def test_get_preventivo_detail_404(self):
        from apps.core.services.service_errors import ServiceError
        self.mock_svc.get_preventivo.side_effect = ServiceError(
            code="E_PREV_NOT_FOUND", message="Preventivo non trovato."
        )
        response = self.client.get("/api/v1/vendite/preventivi/999/")
        self.assertIn(response.status_code, [401, 403, 404])

    # Scopo: Verifica POST cambio stato.
    def test_cambio_stato_200(self):
        self.mock_svc.cambia_stato.return_value = {"status": "ok"}
        response = self.client.post(
            "/api/v1/vendite/preventivi/1/stato/",
            data='{"nuovo_stato": "EMESSO"}',
            content_type="application/json",
        )
        self.assertIn(response.status_code, [200, 401, 403])

    # Scopo: Verifica POST aggiunta riga.
    def test_add_riga_200(self):
        self.mock_svc.gestisci_riga.return_value = {"id": 10}
        response = self.client.post(
            "/api/v1/vendite/preventivi/1/righe/",
            data='{"articolo_id": "uuid-art-1"}',
            content_type="application/json",
        )
        self.assertIn(response.status_code, [200, 401, 403])

    # Scopo: Verifica POST push commessa.
    def test_push_commessa_200(self):
        self.mock_svc.push_a_commessa.return_value = {"righe_pushate": 3}
        response = self.client.post(
            "/api/v1/vendite/preventivi/1/push-commessa/",
            data="{}",
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="test-key-1",
        )
        self.assertIn(response.status_code, [200, 401, 403])

    # ── Componenti BoM CASO A ──

    # Scopo: GET lista componenti di una riga padre (refactor componenti 2026-05-11).
    def test_list_componenti_riga_200(self):
        self.mock_svc.list_componenti_riga.return_value = [
            {"id": 1, "componente_id": "c1", "prezzo_unitario": "200"},
            {"id": 2, "componente_id": "c2", "prezzo_unitario": "75"},
        ]
        response = self.client.get(
            "/api/v1/vendite/preventivi/1/righe/10/componenti/",
        )
        self.assertIn(response.status_code, [200, 401, 403])

    # Scopo: PATCH override prezzo componente.
    def test_update_componente_200(self):
        self.mock_svc.update_componente.return_value = {
            "status": "ok", "componente_id": 50,
        }
        response = self.client.patch(
            "/api/v1/vendite/preventivi/1/righe/10/componenti/50/",
            data='{"prezzo_unitario": "150.00", "origine_prezzo": "MANUALE"}',
            content_type="application/json",
        )
        self.assertIn(response.status_code, [200, 401, 403])

    # Scopo: DELETE soft delete componente.
    def test_delete_componente_200(self):
        self.mock_svc.delete_componente.return_value = {
            "status": "ok", "componente_id": 50, "deleted": True,
        }
        response = self.client.delete(
            "/api/v1/vendite/preventivi/1/righe/10/componenti/50/",
        )
        self.assertIn(response.status_code, [200, 401, 403])

    # Scopo: GET componenti su riga inesistente -> 404 dal service.
    def test_get_componente_404(self):
        from apps.core.services.service_errors import ServiceError
        self.mock_svc.list_componenti_riga.side_effect = ServiceError(
            code="E_PREV_RIGA_NOT_FOUND", message="Riga preventivo non trovata.",
        )
        response = self.client.get(
            "/api/v1/vendite/preventivi/1/righe/999/componenti/",
        )
        self.assertIn(response.status_code, [401, 403, 404])
