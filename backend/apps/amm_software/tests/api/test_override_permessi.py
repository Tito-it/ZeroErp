# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari API override permessi modulo Amm. Software.
# Tutti i test usano mock — nessuna dipendenza da DB reale (CI-compatible).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_get_override_aree — GET override aree ritorna lista
 2) test_put_override_aree — PUT override aree sostituisce e ritorna lista
 3) test_put_override_aree_invalidates_cache — PUT invalida cache utente
 4) test_get_override_azioni — GET override azioni ritorna lista
 5) test_put_override_azioni — PUT override azioni sostituisce e ritorna lista
 6) test_put_override_azioni_invalidates_cache — PUT invalida cache utente
 7) test_get_emittenti_scope — GET emittenti scope ritorna lista
 8) test_put_emittenti_scope — PUT emittenti scope sostituisce e ritorna lista
 9) test_put_emittenti_scope_invalidates_cache — PUT invalida cache utente
10) test_override_permission_denied — OPERATIVO non puo' accedere
"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.amm_software.api.views import (
    EmittentiScopeView,
    OverrideAreeView,
    OverrideAzioniView,
)


SAMPLE_OVERRIDE_AREA = {
    "id": 1, "area_id": 2, "area_codice": "vendite",
    "area_descrizione": "Vendite", "livello": "LETTURA",
    "motivo": None, "valido_dal": "2026-03-12", "valido_al": None,
}

SAMPLE_OVERRIDE_AZIONE = {
    "id": 1, "azione_id": 3, "permission_codename": "genera_fatture_lotti",
    "azione_descrizione": "Genera fatture lotti", "area_codice": "vendite",
    "abilitata": True, "motivo": None, "valido_dal": "2026-03-12", "valido_al": None,
}

SAMPLE_EMITTENTE = {
    "id": 1, "emittente_fiscale_id": 10,
    "emittente_denominazione": "Azienda Test", "emittente_piva": "12345678901",
}


def _make_request(method: str = "GET", data: dict | None = None) -> MagicMock:
    request = MagicMock()
    request.method = method
    request.user = MagicMock(is_authenticated=True, is_superuser=True, id=1)
    request.data = data or {}
    return request


class TestOverrideAreeView(TestCase):

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_get_override_aree(self, mock_repo_cls):
        """GET override aree ritorna lista."""
        mock_repo = MagicMock()
        mock_repo.get_override_aree.return_value = [SAMPLE_OVERRIDE_AREA]
        mock_repo_cls.return_value = mock_repo

        view = OverrideAreeView()
        response = view.get(_make_request(), auth_user_id=1)

        data = json.loads(response.content)
        self.assertEqual(len(data["data"]["results"]), 1)
        self.assertEqual(data["data"]["results"][0]["area_codice"], "vendite")

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    def test_put_override_aree(self, mock_invalidate, mock_repo_cls):
        """PUT override aree sostituisce e ritorna lista aggiornata."""
        mock_repo = MagicMock()
        mock_repo.get_override_aree.return_value = [SAMPLE_OVERRIDE_AREA]
        mock_repo_cls.return_value = mock_repo

        items = [{"area_id": 2, "livello": "LETTURA"}]
        request = _make_request("PUT", {"items": items})
        view = OverrideAreeView()
        response = view.put(request, auth_user_id=1)

        mock_repo.put_override_aree.assert_called_once_with(1, items)
        data = json.loads(response.content)
        self.assertEqual(len(data["data"]["results"]), 1)

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    def test_put_override_aree_invalidates_cache(self, mock_invalidate, mock_repo_cls):
        """PUT invalida cache utente dopo modifica."""
        mock_repo = MagicMock()
        mock_repo.get_override_aree.return_value = []
        mock_repo_cls.return_value = mock_repo

        view = OverrideAreeView()
        view.put(_make_request("PUT", {"items": []}), auth_user_id=42)

        mock_invalidate.assert_called_once_with(42)


class TestOverrideAzioniView(TestCase):

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_get_override_azioni(self, mock_repo_cls):
        """GET override azioni ritorna lista."""
        mock_repo = MagicMock()
        mock_repo.get_override_azioni.return_value = [SAMPLE_OVERRIDE_AZIONE]
        mock_repo_cls.return_value = mock_repo

        view = OverrideAzioniView()
        response = view.get(_make_request(), auth_user_id=1)

        data = json.loads(response.content)
        self.assertEqual(len(data["data"]["results"]), 1)

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    def test_put_override_azioni(self, mock_invalidate, mock_repo_cls):
        """PUT override azioni sostituisce e ritorna lista aggiornata."""
        mock_repo = MagicMock()
        mock_repo.get_override_azioni.return_value = [SAMPLE_OVERRIDE_AZIONE]
        mock_repo_cls.return_value = mock_repo

        items = [{"azione_id": 3, "abilitata": True}]
        request = _make_request("PUT", {"items": items})
        view = OverrideAzioniView()
        response = view.put(request, auth_user_id=1)

        mock_repo.put_override_azioni.assert_called_once_with(1, items)
        data = json.loads(response.content)
        self.assertEqual(len(data["data"]["results"]), 1)

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    def test_put_override_azioni_invalidates_cache(self, mock_invalidate, mock_repo_cls):
        """PUT invalida cache utente dopo modifica."""
        mock_repo = MagicMock()
        mock_repo.get_override_azioni.return_value = []
        mock_repo_cls.return_value = mock_repo

        view = OverrideAzioniView()
        view.put(_make_request("PUT", {"items": []}), auth_user_id=7)

        mock_invalidate.assert_called_once_with(7)


class TestEmittentiScopeView(TestCase):

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_get_emittenti_scope(self, mock_repo_cls):
        """GET emittenti scope ritorna lista."""
        mock_repo = MagicMock()
        mock_repo.get_emittenti_scope.return_value = [SAMPLE_EMITTENTE]
        mock_repo_cls.return_value = mock_repo

        view = EmittentiScopeView()
        response = view.get(_make_request(), auth_user_id=1)

        data = json.loads(response.content)
        self.assertEqual(len(data["data"]["results"]), 1)
        self.assertEqual(data["data"]["results"][0]["emittente_denominazione"], "Azienda Test")

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    def test_put_emittenti_scope(self, mock_invalidate, mock_repo_cls):
        """PUT emittenti scope sostituisce e ritorna lista aggiornata."""
        mock_repo = MagicMock()
        mock_repo.get_emittenti_scope.return_value = [SAMPLE_EMITTENTE]
        mock_repo_cls.return_value = mock_repo

        request = _make_request("PUT", {"emittente_ids": [10]})
        view = EmittentiScopeView()
        response = view.put(request, auth_user_id=1)

        mock_repo.put_emittenti_scope.assert_called_once_with(1, [10])

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    def test_put_emittenti_scope_invalidates_cache(self, mock_invalidate, mock_repo_cls):
        """PUT invalida cache utente dopo modifica."""
        mock_repo = MagicMock()
        mock_repo.get_emittenti_scope.return_value = []
        mock_repo_cls.return_value = mock_repo

        view = EmittentiScopeView()
        view.put(_make_request("PUT", {"emittente_ids": []}), auth_user_id=5)

        mock_invalidate.assert_called_once_with(5)


class TestOverridePermissionDenied(TestCase):

    @patch("apps.core.api.permissions.PermissionResolver")
    @patch("apps.core.api.permissions.ZeroERPPermission._get_cache", return_value={})
    @patch("apps.core.api.permissions.ZeroERPPermission._save_cache_to_redis")
    def test_override_permission_denied(self, mock_save, mock_cache, mock_resolver):
        """OPERATIVO non puo' accedere a override aree."""
        mock_resolver.get_ruolo_sistema.return_value = "OPERATIVO"

        from apps.core.api.permissions import IsAdminZeroERP
        request = _make_request()
        request.user = MagicMock(is_authenticated=True, is_superuser=False, id=2)
        request.path = "/api/v1/amm-software/utenti/1/override-aree/"

        perm = IsAdminZeroERP()
        self.assertFalse(perm.has_permission(request, OverrideAreeView()))
