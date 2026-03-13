# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari API profili reparto modulo Amm. Software.
# Tutti i test usano mock — nessuna dipendenza da DB reale (CI-compatible).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_list_reparti — GET lista reparti con conteggi
 2) test_list_reparti_empty — GET lista reparti vuota
 3) test_get_profilo_reparto — GET profilo reparto (aree + azioni)
 4) test_get_profilo_reparto_empty — GET profilo vuoto
 5) test_put_profilo_reparto — PUT salva profilo e ritorna aggiornato
 6) test_put_profilo_invalidates_cache — PUT invalida cache reparto
 7) test_lookup_aree — GET lookup aree funzionali
 8) test_lookup_azioni — GET lookup azioni processo
 9) test_lookup_emittenti — GET lookup emittenti fiscali
10) test_profili_permission_denied — OPERATIVO non puo' accedere
"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.amm_software.api.views import (
    LookupAreeView,
    LookupAzioniView,
    LookupEmittentiView,
    RepartiListView,
    RepartoProfiloView,
)


SAMPLE_REPARTO = {
    "id": 1, "codice": "AMM", "nome": "Amministrazione", "attivo": True,
    "profilo_aree_count": 5, "profilo_azioni_count": 3, "operatori_count": 10,
}

SAMPLE_PROFILO = {
    "aree": [
        {"id": 1, "area_id": 2, "area_codice": "vendite",
         "area_descrizione": "Vendite", "livello": "TUTTO"},
    ],
    "azioni": [
        {"id": 1, "azione_id": 3, "permission_codename": "genera_fatture_lotti",
         "azione_descrizione": "Genera fatture lotti", "area_codice": "vendite",
         "abilitata": True},
    ],
}


def _make_request(method: str = "GET", data: dict | None = None) -> MagicMock:
    request = MagicMock()
    request.method = method
    request.user = MagicMock(is_authenticated=True, is_superuser=True, id=1)
    request.data = data or {}
    return request


class TestRepartiListView(TestCase):

    @patch("apps.amm_software.api.views.AmmSoftwareRepository")
    def test_list_reparti(self, mock_repo_cls):
        """GET lista reparti con conteggi profilo e operatori."""
        mock_repo = MagicMock()
        mock_repo.list_reparti.return_value = [SAMPLE_REPARTO]
        mock_repo_cls.return_value = mock_repo

        view = RepartiListView()
        response = view.get(_make_request())

        data = json.loads(response.content)
        self.assertEqual(len(data["data"]["results"]), 1)
        self.assertEqual(data["data"]["results"][0]["nome"], "Amministrazione")
        self.assertEqual(data["data"]["results"][0]["operatori_count"], 10)

    @patch("apps.amm_software.api.views.AmmSoftwareRepository")
    def test_list_reparti_empty(self, mock_repo_cls):
        """GET lista reparti vuota."""
        mock_repo = MagicMock()
        mock_repo.list_reparti.return_value = []
        mock_repo_cls.return_value = mock_repo

        view = RepartiListView()
        response = view.get(_make_request())

        data = json.loads(response.content)
        self.assertEqual(data["data"]["results"], [])


class TestRepartoProfiloView(TestCase):

    @patch("apps.amm_software.api.views.AmmSoftwareRepository")
    def test_get_profilo_reparto(self, mock_repo_cls):
        """GET profilo reparto ritorna aree e azioni."""
        mock_repo = MagicMock()
        mock_repo.get_profilo_reparto.return_value = SAMPLE_PROFILO
        mock_repo_cls.return_value = mock_repo

        view = RepartoProfiloView()
        response = view.get(_make_request(), uo_id=1)

        data = json.loads(response.content)
        self.assertEqual(len(data["data"]["aree"]), 1)
        self.assertEqual(len(data["data"]["azioni"]), 1)
        self.assertEqual(data["data"]["aree"][0]["livello"], "TUTTO")

    @patch("apps.amm_software.api.views.AmmSoftwareRepository")
    def test_get_profilo_reparto_empty(self, mock_repo_cls):
        """GET profilo vuoto per reparto senza configurazione."""
        mock_repo = MagicMock()
        mock_repo.get_profilo_reparto.return_value = {"aree": [], "azioni": []}
        mock_repo_cls.return_value = mock_repo

        view = RepartoProfiloView()
        response = view.get(_make_request(), uo_id=99)

        data = json.loads(response.content)
        self.assertEqual(data["data"]["aree"], [])
        self.assertEqual(data["data"]["azioni"], [])

    @patch("apps.amm_software.api.views.AmmSoftwareRepository")
    @patch("apps.amm_software.api.views.invalidate_department")
    def test_put_profilo_reparto(self, mock_invalidate, mock_repo_cls):
        """PUT salva profilo e ritorna aggiornato."""
        mock_repo = MagicMock()
        mock_repo.get_profilo_reparto.return_value = SAMPLE_PROFILO
        mock_repo_cls.return_value = mock_repo

        aree = [{"area_id": 2, "livello": "TUTTO"}]
        azioni = [{"azione_id": 3, "abilitata": True}]
        request = _make_request("PUT", {"aree": aree, "azioni": azioni})

        view = RepartoProfiloView()
        response = view.put(request, uo_id=1)

        mock_repo.put_profilo_reparto.assert_called_once_with(1, aree, azioni)
        data = json.loads(response.content)
        self.assertIn("aree", data["data"])

    @patch("apps.amm_software.api.views.AmmSoftwareRepository")
    @patch("apps.amm_software.api.views.invalidate_department")
    def test_put_profilo_invalidates_cache(self, mock_invalidate, mock_repo_cls):
        """PUT invalida cache reparto dopo modifica."""
        mock_repo = MagicMock()
        mock_repo.get_profilo_reparto.return_value = {"aree": [], "azioni": []}
        mock_repo_cls.return_value = mock_repo

        view = RepartoProfiloView()
        view.put(_make_request("PUT", {"aree": [], "azioni": []}), uo_id=5)

        mock_invalidate.assert_called_once_with(5)


class TestLookupViews(TestCase):

    @patch("apps.amm_software.api.views.AmmSoftwareRepository")
    def test_lookup_aree(self, mock_repo_cls):
        """GET lookup aree funzionali."""
        mock_repo = MagicMock()
        mock_repo.list_aree_funzionali.return_value = [
            {"id": 1, "codice": "vendite", "descrizione": "Vendite", "ordinamento": 1},
        ]
        mock_repo_cls.return_value = mock_repo

        view = LookupAreeView()
        response = view.get(_make_request())

        data = json.loads(response.content)
        self.assertEqual(len(data["data"]["results"]), 1)

    @patch("apps.amm_software.api.views.AmmSoftwareRepository")
    def test_lookup_azioni(self, mock_repo_cls):
        """GET lookup azioni processo."""
        mock_repo = MagicMock()
        mock_repo.list_azioni_processo.return_value = [
            {"id": 1, "permission_codename": "genera_fatture_lotti",
             "descrizione": "Genera fatture", "pericolosa": False,
             "area_id": 2, "area_codice": "vendite"},
        ]
        mock_repo_cls.return_value = mock_repo

        view = LookupAzioniView()
        response = view.get(_make_request())

        data = json.loads(response.content)
        self.assertEqual(len(data["data"]["results"]), 1)

    @patch("apps.amm_software.api.views.AmmSoftwareRepository")
    def test_lookup_emittenti(self, mock_repo_cls):
        """GET lookup emittenti fiscali."""
        mock_repo = MagicMock()
        mock_repo.list_emittenti_fiscali.return_value = [
            {"id": 1, "denominazione": "Azienda Test", "partita_iva": "12345678901"},
        ]
        mock_repo_cls.return_value = mock_repo

        view = LookupEmittentiView()
        response = view.get(_make_request())

        data = json.loads(response.content)
        self.assertEqual(len(data["data"]["results"]), 1)


class TestProfiliPermissionDenied(TestCase):

    @patch("apps.core.api.permissions.PermissionResolver")
    @patch("apps.core.api.permissions.ZeroERPPermission._get_cache", return_value={})
    @patch("apps.core.api.permissions.ZeroERPPermission._save_cache_to_redis")
    def test_profili_permission_denied(self, mock_save, mock_cache, mock_resolver):
        """OPERATIVO non puo' accedere ai profili reparto."""
        mock_resolver.get_ruolo_sistema.return_value = "OPERATIVO"

        from apps.core.api.permissions import IsAdminZeroERP
        request = _make_request()
        request.user = MagicMock(is_authenticated=True, is_superuser=False, id=2)
        request.path = "/api/v1/amm-software/reparti/"

        perm = IsAdminZeroERP()
        self.assertFalse(perm.has_permission(request, RepartiListView()))
