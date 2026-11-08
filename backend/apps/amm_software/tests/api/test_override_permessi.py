# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
 7) test_get_emittenti_scope — GET emittenti scope ritorna shape Fase 2 (scope_mode + capability)
 8) test_put_emittenti_scope_global — PUT GLOBAL azzera lo scope
 9) test_put_emittenti_scope_single — PUT SINGLE imposta 1 emittente
 9a) test_put_emittenti_scope_rifiuta_multi — MULTI rifiutato con E_AMM_SCOPE_NON_AMMESSO
 9b) test_put_emittenti_scope_single_richiede_array_lunghezza_1 — SINGLE con array vuoto rifiutato
 9c) test_put_emittenti_scope_super_admin_guard_dbtrigger — race condition Fase 1 guard
9d) test_put_emittenti_scope_invalidates_cache — PUT invalida cache utente
10) test_override_permission_denied — OPERATIVO non puo' accedere
11) test_get_override_oggetti — GET override oggetti ritorna lista
12) test_put_override_oggetti — PUT override oggetti sostituisce e ritorna lista
13) test_put_override_oggetti_invalidates_cache — PUT invalida cache utente
14) test_put_override_oggetti_valida_catalogo — model non registrato -> E_AMM_VALIDAZIONE
15) test_put_override_oggetti_empty_skippa_validazione — lista vuota non chiama lookup
16) test_get_model_overrides_lookup — lookup catalogo model
17) test_override_su_credenziale_non_operatore_e_404 — macchina, ALTRO o id inesistente: 404 su GET e PUT dei tre override, niente scritto
18) test_voci_malformate_sono_400_non_500 — items non lista, voce non oggetto, campo mancante: 400 E_AMM_VALIDAZIONE, niente scritto
"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.db import DatabaseError

from apps.amm_software.api.views import (
    EmittentiScopeView,
    ModelOverridesLookupView,
    OverrideAreeView,
    OverrideAzioniView,
    OverrideOggettiView,
)
from apps.core.services.error_manager import ServiceError


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

# Fase 2: shape ritornato da `script.fn_get_user_emittenti_scope`.
# Singolo row con scope_mode + capability + reason.
SAMPLE_SCOPE_GLOBAL = {
    "auth_user_id": 1, "scope_mode": "GLOBAL",
    "emittente_id": None, "emittente_descrizione": None,
    "allowed_scope_modes": ["GLOBAL", "SINGLE"],
    "can_change_scope": True, "change_scope_reason": None,
}

SAMPLE_SCOPE_SINGLE = {
    "auth_user_id": 1, "scope_mode": "SINGLE",
    "emittente_id": 42, "emittente_descrizione": "Sede Roma",
    "allowed_scope_modes": ["GLOBAL", "SINGLE"],
    "can_change_scope": True, "change_scope_reason": None,
}

SAMPLE_OVERRIDE_OGGETTO = {
    "id": 1, "app_label": "anagrafiche", "model_name": "conto_bancario",
    "livello": "BLOCCATO", "motivo": "riservato",
    "valido_dal": "2026-04-10", "valido_al": None,
    "area_id": 1, "area_descrizione": "Anagrafiche",
}

SAMPLE_MODEL_OVERRIDE = {
    "id": 1, "app_label": "anagrafiche", "model_name": "conto_bancario",
    "area_schema": "anagrafiche", "area_descrizione": "Anagrafiche",
    # Fase 8: capability override-abilita'.
    "can_override": True, "reason": None,
}

SAMPLE_MODEL_OVERRIDE_RISERVATO = {
    # Riga `riservato = t` del catalogo (`area_model_overrides.csv`): identita_digitali
    # appartiene al kernel permessi e non puo' essere target di override
    # granulari (Fase 8 amm-software).
    "id": 99, "app_label": "anagrafiche", "model_name": "identita_digitali",
    "area_schema": "anagrafiche", "area_descrizione": "Anagrafiche",
    "can_override": False, "reason": "amm.model_override_reason_riservato",
}


def _make_request(method: str = "GET", data: dict | None = None) -> MagicMock:
    request = MagicMock()
    request.method = method
    request.user = MagicMock(is_authenticated=True, is_superuser=True, id=1)
    request.data = data or {}
    return request


# Le voci come il service le passa al repository: i campi comuni a ogni
# override (`motivo`, `valido_dal`, `valido_al`) sempre presenti, validati.
def _normalizzate(items):
    return [{"motivo": None, "valido_dal": None, "valido_al": None, **it} for it in items]


class TestOverrideAreeView(TestCase):

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    def test_get_override_aree(self, mock_repo_cls):
        """GET override aree ritorna lista."""
        mock_repo = MagicMock()
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        mock_repo.get_override_aree.return_value = [SAMPLE_OVERRIDE_AREA]
        mock_repo_cls.return_value = mock_repo

        view = OverrideAreeView()
        response = view.get(_make_request(), auth_user_id=1)

        data = json.loads(response.content)
        self.assertEqual(len(data["data"]["results"]), 1)
        self.assertEqual(data["data"]["results"][0]["area_codice"], "vendite")

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    def test_put_override_aree(self, mock_invalidate, mock_repo_cls):
        """PUT override aree sostituisce e ritorna lista aggiornata."""
        mock_repo = MagicMock()
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        mock_repo.get_override_aree.return_value = [SAMPLE_OVERRIDE_AREA]
        mock_repo_cls.return_value = mock_repo

        items = [{"area_id": 2, "livello": "LETTURA"}]
        request = _make_request("PUT", {"items": items})
        view = OverrideAreeView()
        response = view.put(request, auth_user_id=1)

        mock_repo.put_override_aree.assert_called_once_with(1, _normalizzate(items))
        data = json.loads(response.content)
        self.assertEqual(len(data["data"]["results"]), 1)

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    def test_put_override_aree_invalidates_cache(self, mock_invalidate, mock_repo_cls):
        """PUT invalida cache utente dopo modifica."""
        mock_repo = MagicMock()
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        mock_repo.get_override_aree.return_value = []
        mock_repo_cls.return_value = mock_repo

        view = OverrideAreeView()
        view.put(_make_request("PUT", {"items": []}), auth_user_id=42)

        mock_invalidate.assert_called_once_with(42)


class TestOverrideAzioniView(TestCase):

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    def test_get_override_azioni(self, mock_repo_cls):
        """GET override azioni ritorna lista."""
        mock_repo = MagicMock()
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        mock_repo.get_override_azioni.return_value = [SAMPLE_OVERRIDE_AZIONE]
        mock_repo_cls.return_value = mock_repo

        view = OverrideAzioniView()
        response = view.get(_make_request(), auth_user_id=1)

        data = json.loads(response.content)
        self.assertEqual(len(data["data"]["results"]), 1)

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    def test_put_override_azioni(self, mock_invalidate, mock_repo_cls):
        """PUT override azioni sostituisce e ritorna lista aggiornata."""
        mock_repo = MagicMock()
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        mock_repo.get_override_azioni.return_value = [SAMPLE_OVERRIDE_AZIONE]
        mock_repo_cls.return_value = mock_repo

        items = [{"azione_id": 3, "abilitata": True}]
        request = _make_request("PUT", {"items": items})
        view = OverrideAzioniView()
        response = view.put(request, auth_user_id=1)

        mock_repo.put_override_azioni.assert_called_once_with(1, _normalizzate(items))
        data = json.loads(response.content)
        self.assertEqual(len(data["data"]["results"]), 1)

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    def test_put_override_azioni_invalidates_cache(self, mock_invalidate, mock_repo_cls):
        """PUT invalida cache utente dopo modifica."""
        mock_repo = MagicMock()
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        mock_repo.get_override_azioni.return_value = []
        mock_repo_cls.return_value = mock_repo

        view = OverrideAzioniView()
        view.put(_make_request("PUT", {"items": []}), auth_user_id=7)

        mock_invalidate.assert_called_once_with(7)


class TestEmittentiScopeView(TestCase):
    """Test Fase 2 multi-face: scope dichiarativo via fn DB."""

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    def test_get_emittenti_scope(self, mock_repo_cls):
        """GET ritorna shape Fase 2 (scope_mode + emittenti_ids + capability)."""
        mock_repo = MagicMock()
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        mock_repo.get_user_emittenti_scope.return_value = SAMPLE_SCOPE_SINGLE
        mock_repo_cls.return_value = mock_repo

        view = EmittentiScopeView()
        response = view.get(_make_request(), auth_user_id=1)

        data = json.loads(response.content)["data"]
        self.assertEqual(data["scope_mode"], "SINGLE")
        self.assertEqual(data["emittenti_ids"], [42])
        self.assertEqual(data["emittente_descrizione"], "Sede Roma")
        self.assertEqual(data["allowed_scope_modes"], ["GLOBAL", "SINGLE"])
        self.assertTrue(data["can_change_scope"])
        self.assertIsNone(data["change_scope_reason"])

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    def test_put_emittenti_scope_global(self, mock_invalidate, mock_repo_cls):
        """PUT GLOBAL azzera lo scope (chiama fn change con array vuoto)."""
        mock_repo = MagicMock()
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        mock_repo.get_user_emittenti_scope.return_value = SAMPLE_SCOPE_GLOBAL
        mock_repo_cls.return_value = mock_repo

        view = EmittentiScopeView()
        view.put(_make_request("PUT", {"scope_mode": "GLOBAL"}), auth_user_id=1)

        mock_repo.change_user_emittenti_scope.assert_called_once_with(1, [])

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    def test_put_emittenti_scope_single(self, mock_invalidate, mock_repo_cls):
        """PUT SINGLE imposta esattamente 1 emittente."""
        mock_repo = MagicMock()
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        mock_repo.get_user_emittenti_scope.return_value = SAMPLE_SCOPE_SINGLE
        mock_repo_cls.return_value = mock_repo

        view = EmittentiScopeView()
        view.put(
            _make_request("PUT", {"scope_mode": "SINGLE", "emittenti_ids": [42]}),
            auth_user_id=1,
        )

        mock_repo.change_user_emittenti_scope.assert_called_once_with(1, [42])

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    def test_put_emittenti_scope_rifiuta_multi(self, mock_repo_cls):
        """MULTI rifiutato con E_AMM_SCOPE_NON_AMMESSO (Q2 chiuso applicativamente)."""
        mock_repo = MagicMock()
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        mock_repo_cls.return_value = mock_repo

        view = EmittentiScopeView()
        with self.assertRaises(ServiceError) as ctx:
            view.put(
                _make_request("PUT", {"scope_mode": "MULTI", "emittenti_ids": [1, 2]}),
                auth_user_id=1,
            )
        self.assertEqual(ctx.exception.code, "E_AMM_SCOPE_NON_AMMESSO")
        mock_repo.change_user_emittenti_scope.assert_not_called()

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    def test_put_emittenti_scope_single_richiede_array_lunghezza_1(self, mock_repo_cls):
        """SINGLE con array vuoto/multi rifiutato."""
        mock_repo = MagicMock()
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        mock_repo_cls.return_value = mock_repo

        view = EmittentiScopeView()
        # Array vuoto
        with self.assertRaises(ServiceError) as ctx:
            view.put(
                _make_request("PUT", {"scope_mode": "SINGLE", "emittenti_ids": []}),
                auth_user_id=1,
            )
        self.assertEqual(ctx.exception.code, "E_AMM_SCOPE_NON_AMMESSO")
        # Array con 2 elementi
        with self.assertRaises(ServiceError):
            view.put(
                _make_request("PUT", {"scope_mode": "SINGLE", "emittenti_ids": [1, 2]}),
                auth_user_id=1,
            )

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    def test_put_emittenti_scope_super_admin_guard_dbtrigger(
        self, _mock_invalidate, mock_repo_cls
    ):
        """Race condition Fase 1: trigger DB rifiuta -> E_PROFILO_ULTIMO_SUPER_ADMIN."""
        mock_repo = MagicMock()
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        mock_repo.change_user_emittenti_scope.side_effect = DatabaseError(
            "ERROR: E_PROFILO_ULTIMO_SUPER_ADMIN: ultimo super admin attivo"
        )
        mock_repo_cls.return_value = mock_repo

        view = EmittentiScopeView()
        with self.assertRaises(ServiceError) as ctx:
            view.put(
                _make_request("PUT", {"scope_mode": "SINGLE", "emittenti_ids": [42]}),
                auth_user_id=1,
            )
        self.assertEqual(ctx.exception.code, "E_PROFILO_ULTIMO_SUPER_ADMIN")

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    def test_put_emittenti_scope_invalidates_cache(self, mock_invalidate, mock_repo_cls):
        """PUT invalida cache utente dopo modifica."""
        mock_repo = MagicMock()
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 5}
        mock_repo.get_user_emittenti_scope.return_value = SAMPLE_SCOPE_GLOBAL
        mock_repo_cls.return_value = mock_repo

        view = EmittentiScopeView()
        view.put(_make_request("PUT", {"scope_mode": "GLOBAL"}), auth_user_id=5)

        mock_invalidate.assert_called_once_with(5)


class TestOverrideOggettiView(TestCase):
    """Override oggetti v2: CRUD admin + validazione catalogo."""

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    def test_get_override_oggetti(self, mock_repo_cls):
        """GET override oggetti ritorna lista con info model+area."""
        mock_repo = MagicMock()
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        mock_repo.get_override_oggetti.return_value = [SAMPLE_OVERRIDE_OGGETTO]
        mock_repo_cls.return_value = mock_repo

        view = OverrideOggettiView()
        response = view.get(_make_request(), auth_user_id=1)

        data = json.loads(response.content)
        self.assertEqual(len(data["data"]["results"]), 1)
        self.assertEqual(data["data"]["results"][0]["app_label"], "anagrafiche")
        self.assertEqual(data["data"]["results"][0]["model_name"], "conto_bancario")
        self.assertEqual(data["data"]["results"][0]["livello"], "BLOCCATO")

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    def test_put_override_oggetti(self, mock_invalidate, mock_repo_cls):
        """PUT override oggetti sostituisce e ritorna lista aggiornata."""
        mock_repo = MagicMock()
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        mock_repo.list_model_overrides.return_value = [SAMPLE_MODEL_OVERRIDE]
        mock_repo.get_override_oggetti.return_value = [SAMPLE_OVERRIDE_OGGETTO]
        mock_repo_cls.return_value = mock_repo

        items = [{
            "app_label": "anagrafiche", "model_name": "conto_bancario",
            "livello": "BLOCCATO", "motivo": "test",
        }]
        request = _make_request("PUT", {"items": items})
        view = OverrideOggettiView()
        response = view.put(request, auth_user_id=1)

        mock_repo.put_override_oggetti.assert_called_once_with(1, _normalizzate(items))
        data = json.loads(response.content)
        self.assertEqual(len(data["data"]["results"]), 1)

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    def test_put_override_oggetti_invalidates_cache(self, mock_invalidate, mock_repo_cls):
        """PUT invalida cache utente dopo modifica."""
        mock_repo = MagicMock()
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        mock_repo.list_model_overrides.return_value = [SAMPLE_MODEL_OVERRIDE]
        mock_repo.get_override_oggetti.return_value = []
        mock_repo_cls.return_value = mock_repo

        view = OverrideOggettiView()
        view.put(_make_request("PUT", {"items": []}), auth_user_id=99)

        mock_invalidate.assert_called_once_with(99)

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    def test_put_override_oggetti_valida_catalogo(self, mock_invalidate, mock_repo_cls):
        """PUT con model non registrato -> E_AMM_VALIDAZIONE, nessuna scrittura."""
        mock_repo = MagicMock()
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        mock_repo.list_model_overrides.return_value = [SAMPLE_MODEL_OVERRIDE]
        mock_repo_cls.return_value = mock_repo

        items = [{
            "app_label": "fantasma", "model_name": "inesistente",
            "livello": "BLOCCATO",
        }]
        request = _make_request("PUT", {"items": items})
        view = OverrideOggettiView()

        with self.assertRaises(ServiceError) as ctx:
            view.put(request, auth_user_id=1)
        self.assertEqual(ctx.exception.code, "E_AMM_VALIDAZIONE")
        mock_repo.put_override_oggetti.assert_not_called()
        mock_invalidate.assert_not_called()

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    def test_put_override_oggetti_empty_skippa_validazione(self, mock_invalidate, mock_repo_cls):
        """PUT con lista vuota non interroga il catalogo (cancellazione pura)."""
        mock_repo = MagicMock()
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        mock_repo.get_override_oggetti.return_value = []
        mock_repo_cls.return_value = mock_repo

        view = OverrideOggettiView()
        view.put(_make_request("PUT", {"items": []}), auth_user_id=1)

        mock_repo.list_model_overrides.assert_not_called()
        mock_repo.put_override_oggetti.assert_called_once_with(1, [])


class TestModelOverridesLookupView(TestCase):
    """Lookup catalogo model registrati (dropdown admin)."""

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    def test_get_model_overrides_lookup(self, mock_repo_cls):
        """GET lookup ritorna catalogo con schema area + capability."""
        mock_repo = MagicMock()
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        mock_repo.list_model_overrides.return_value = [SAMPLE_MODEL_OVERRIDE]
        mock_repo_cls.return_value = mock_repo

        view = ModelOverridesLookupView()
        response = view.get(_make_request())

        data = json.loads(response.content)
        self.assertEqual(len(data["data"]["results"]), 1)
        row = data["data"]["results"][0]
        self.assertEqual(row["app_label"], "anagrafiche")
        self.assertEqual(row["area_schema"], "anagrafiche")
        # Fase 8: capability esposta dal lookup.
        self.assertTrue(row["can_override"])
        self.assertIsNone(row["reason"])

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    def test_get_model_overrides_lookup_riservato(self, mock_repo_cls):
        """Fase 8: model riservati hanno can_override=False + reason i18n."""
        mock_repo = MagicMock()
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        mock_repo.list_model_overrides.return_value = [
            SAMPLE_MODEL_OVERRIDE,
            SAMPLE_MODEL_OVERRIDE_RISERVATO,
        ]
        mock_repo_cls.return_value = mock_repo

        view = ModelOverridesLookupView()
        response = view.get(_make_request())

        data = json.loads(response.content)
        results = {r["model_name"]: r for r in data["data"]["results"]}
        self.assertTrue(results["conto_bancario"]["can_override"])
        self.assertFalse(results["identita_digitali"]["can_override"])
        self.assertEqual(
            results["identita_digitali"]["reason"],
            "amm.model_override_reason_riservato",
        )

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    def test_put_override_oggetti_rifiuta_model_riservato(
        self, mock_invalidate, mock_repo_cls
    ):
        """Fase 8: scrittura su model riservato -> E_AMM_VALIDAZIONE.

        Defense-in-depth: il FE filtra gia' i riservati dal dropdown, ma
        una request crafted bypasserebbe il filtro lato client. Il service
        deve rifiutare.
        """
        mock_repo = MagicMock()
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        mock_repo.list_model_overrides.return_value = [
            SAMPLE_MODEL_OVERRIDE,
            SAMPLE_MODEL_OVERRIDE_RISERVATO,
        ]
        mock_repo_cls.return_value = mock_repo

        items = [{
            "app_label": "anagrafiche", "model_name": "identita_digitali",
            "livello": "BLOCCATO",
        }]
        view = OverrideOggettiView()
        with self.assertRaises(ServiceError) as ctx:
            view.put(_make_request("PUT", {"items": items}), auth_user_id=1)
        self.assertEqual(ctx.exception.code, "E_AMM_VALIDAZIONE")
        mock_repo.put_override_oggetti.assert_not_called()
        mock_invalidate.assert_not_called()


class TestOverridePermissionDenied(TestCase):

    @patch("apps.core.api.permissions.PermissionResolver")
    @patch("apps.core.api.permissions.ZeroERPPermission._get_cache", return_value={})
    @patch("apps.core.api.permissions.ZeroERPPermission._save_cache_to_redis")
    def test_override_permission_denied(self, mock_save, mock_cache, mock_resolver):
        """OPERATIVO non puo' accedere a override aree."""
        mock_resolver.is_super_admin.return_value = False

        from apps.core.api.permissions import IsAdminZeroERP
        request = _make_request()
        request.user = MagicMock(is_authenticated=True, is_superuser=False, id=2)
        request.path = "/api/v1/amm-software/operatori/1/override-aree/"

        perm = IsAdminZeroERP()
        self.assertFalse(perm.has_permission(request, OverrideAreeView()))


class TestOverrideSoloSuOperatori(TestCase):

    # Scopo: ⛔ le rotte `operatori/{id}/override-*` valgono solo per una
    #        credenziale di categoria OPERATORE, come tutte le `operatori/{id}/`.
    #        Prima un id di macchina (SISTEMA) o di cliente del portale (ALTRO)
    #        riceveva gli override col PUT, e il GET rispondeva una lista vuota.
    #        Ora e' il 404 di `get_operatore`, e il repository non scrive niente.
    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    def test_override_su_credenziale_non_operatore_e_404(self, mock_repo_cls, _invalidate):
        mock_repo = mock_repo_cls.return_value
        put = {"items": [{"area_id": 2, "livello": "LETTURA"}]}
        for categoria in ("SISTEMA", "ALTRO", None):
            mock_repo.get_categoria_accesso.return_value = categoria
            for view in (OverrideAreeView(), OverrideAzioniView(), OverrideOggettiView()):
                for metodo in ("get", "put"):
                    with self.subTest(categoria=categoria, view=type(view).__name__, metodo=metodo):
                        request = _make_request(metodo.upper(), put if metodo == "put" else None)
                        with self.assertRaises(ServiceError) as ctx:
                            getattr(view, metodo)(request, auth_user_id=7)
                        self.assertEqual(ctx.exception.code, "E_AMM_OPERATORE_NOT_FOUND")
        for nome in (
            "put_override_aree", "put_override_azioni", "put_override_oggetti",
            "get_override_aree", "get_override_azioni", "get_override_oggetti",
        ):
            getattr(mock_repo, nome).assert_not_called()


class TestVociOverrideValidate(TestCase):

    # Scopo: ⛔ le voci dei tre PUT si validano PRIMA del repository. Fino al
    #        2026-10-20 arrivavano crude: una chiave mancante era un KeyError, una
    #        voce non-oggetto un AttributeError — un 500 per un errore di chi chiama.
    @patch("apps.amm_software.services.amm_software_service.invalidate_user")
    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository", autospec=True)
    def test_voci_malformate_sono_400_non_500(self, mock_repo_cls, _invalidate):
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        mock_repo.list_model_overrides.return_value = [SAMPLE_MODEL_OVERRIDE]
        casi = (
            # `items` assente: il repository sostituisce in blocco, e un corpo
            # senza la chiave cancellava tutti gli override con un 200.
            (OverrideAreeView, {}),
            (OverrideAzioniView, {"item": [{"azione_id": 3, "abilitata": True}]}),
            (OverrideOggettiView, {}),
            # campi comuni: le date e il motivo, validati prima del DB
            (OverrideAreeView, {"items": [{"area_id": 2, "livello": "LETTURA", "valido_dal": "ieri"}]}),
            (OverrideAzioniView, {"items": [{"azione_id": 3, "abilitata": True, "motivo": {"x": 1}}]}),
            (OverrideAreeView, {"items": None}),
            (OverrideAreeView, {"items": ["non un oggetto"]}),
            (OverrideAreeView, {"items": [{"livello": "LETTURA"}]}),
            (OverrideAreeView, {"items": [{"area_id": 2}]}),
            (OverrideAzioniView, {"items": [{"azione_id": 3}]}),
            (OverrideAzioniView, {"items": [{"azione_id": 3, "abilitata": "true"}]}),
            (OverrideOggettiView, {"items": [{"app_label": "anagrafiche", "model_name": "conto_bancario"}]}),
        )
        for vista, corpo in casi:
            with self.subTest(vista=vista.__name__, corpo=corpo):
                with self.assertRaises(ServiceError) as ctx:
                    vista().put(_make_request("PUT", corpo), auth_user_id=1)
                self.assertEqual(ctx.exception.code, "E_AMM_VALIDAZIONE")
        mock_repo.put_override_aree.assert_not_called()
        mock_repo.put_override_azioni.assert_not_called()
        mock_repo.put_override_oggetti.assert_not_called()
