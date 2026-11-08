# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per TipiRuoloTipiIndirizzoService — Fase 4
#        (fallback_options + non_editable_fields). Mock repo, no DB.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_get_non_editable_fields_include_dimensions — gap dominio espone le 2 FK
 2) test_compute_fallback_options_ok — opzioni filtrate (no self) con catena lineare
 3) test_compute_fallback_options_excludes_self_reference — il record stesso e' escluso
 4) test_compute_fallback_options_excludes_cycle_direct — A->B + B->A: B escluso
 5) test_compute_fallback_options_excludes_cycle_indirect — A->B->C, C->A: C escluso (A vuole nuovo fb)
 6) test_compute_fallback_options_handles_self_loop — riga con fallback=self (corruzione DB) non blocca
 7) test_get_matrice_arricchito — get_matrice include non_editable_fields + fallback_options
"""

from unittest import TestCase
from unittest.mock import patch


SVC_MOD = "apps.config.services.tipi_ruolo_tipi_indirizzo_service"
REPO_PATH = f"{SVC_MOD}.TipiRuoloTipiIndirizzoRepository"


class TestNonEditableFields(TestCase):
    """non_editable_fields gap dominio (Fase 4 — A9)."""

    @patch("apps.core.services.non_editable_fields_helper.LockColumnsRepository.list_non_editable", autospec=True)
    def test_get_non_editable_fields_include_dimensions(self, mock_list):
        from apps.config.services.tipi_ruolo_tipi_indirizzo_service import (
            TipiRuoloTipiIndirizzoService,
        )

        mock_list.return_value = ()

        result = TipiRuoloTipiIndirizzoService().get_non_editable_fields()

        self.assertEqual(set(result), {"tipo_ruolo_id", "tipo_indirizzo_id"})


class TestComputeFallbackOptions(TestCase):
    """`_compute_fallback_options` — DFS no self-ref + no cicli (Fase 4 — A10)."""

    @patch(REPO_PATH, autospec=True)
    def test_compute_fallback_options_ok(self, mock_repo_cls):
        # Sotto-matrice ruolo: 3 tipi (A, B, C) con catena C->A->NULL, B->NULL.
        # Per A: candidati = {B, C}. C ha fallback A, ciclo -> escluso. B OK.
        from apps.config.services.tipi_ruolo_tipi_indirizzo_service import (
            TipiRuoloTipiIndirizzoService,
        )
        mock_repo_cls.return_value.list_fallback_chain_for_ruolo.return_value = [
            {"tipo_indirizzo_id": 1, "codice": "A", "descrizione": "Tipo A", "fallback_tipo_indirizzo_id": None},
            {"tipo_indirizzo_id": 2, "codice": "B", "descrizione": "Tipo B", "fallback_tipo_indirizzo_id": None},
            {"tipo_indirizzo_id": 3, "codice": "C", "descrizione": "Tipo C", "fallback_tipo_indirizzo_id": 1},
        ]

        svc = TipiRuoloTipiIndirizzoService()
        opts = svc._compute_fallback_options(tipo_ruolo_id=10, tipo_indirizzo_id=1)

        ids = sorted(o["tipo_indirizzo_id"] for o in opts)
        self.assertEqual(ids, [2])  # solo B (C escluso per ciclo)

    @patch(REPO_PATH, autospec=True)
    def test_compute_fallback_options_excludes_self_reference(self, mock_repo_cls):
        # Per A: A non puo' essere fallback di se stesso.
        from apps.config.services.tipi_ruolo_tipi_indirizzo_service import (
            TipiRuoloTipiIndirizzoService,
        )
        mock_repo_cls.return_value.list_fallback_chain_for_ruolo.return_value = [
            {"tipo_indirizzo_id": 1, "codice": "A", "descrizione": "Tipo A", "fallback_tipo_indirizzo_id": None},
            {"tipo_indirizzo_id": 2, "codice": "B", "descrizione": "Tipo B", "fallback_tipo_indirizzo_id": None},
        ]

        svc = TipiRuoloTipiIndirizzoService()
        opts = svc._compute_fallback_options(tipo_ruolo_id=10, tipo_indirizzo_id=1)

        ids = [o["tipo_indirizzo_id"] for o in opts]
        self.assertNotIn(1, ids)
        self.assertEqual(ids, [2])

    @patch(REPO_PATH, autospec=True)
    def test_compute_fallback_options_excludes_cycle_direct(self, mock_repo_cls):
        # A->B + B->A: per A i candidati sono {B}. B ha fb=A, scegliere B
        # creerebbe il loop A->B->A. Escluso.
        from apps.config.services.tipi_ruolo_tipi_indirizzo_service import (
            TipiRuoloTipiIndirizzoService,
        )
        mock_repo_cls.return_value.list_fallback_chain_for_ruolo.return_value = [
            {"tipo_indirizzo_id": 1, "codice": "A", "descrizione": "Tipo A", "fallback_tipo_indirizzo_id": 2},
            {"tipo_indirizzo_id": 2, "codice": "B", "descrizione": "Tipo B", "fallback_tipo_indirizzo_id": 1},
        ]

        svc = TipiRuoloTipiIndirizzoService()
        opts = svc._compute_fallback_options(tipo_ruolo_id=10, tipo_indirizzo_id=1)

        self.assertEqual(opts, [])  # nessun candidato valido

    @patch(REPO_PATH, autospec=True)
    def test_compute_fallback_options_excludes_cycle_indirect(self, mock_repo_cls):
        # A->B->C->A (catena 3 livelli, ciclo). Per A che vuole nuovo fallback:
        # C creerebbe loop, escluso. B ha fb=C->A, escluso. Nessun candidato.
        from apps.config.services.tipi_ruolo_tipi_indirizzo_service import (
            TipiRuoloTipiIndirizzoService,
        )
        mock_repo_cls.return_value.list_fallback_chain_for_ruolo.return_value = [
            {"tipo_indirizzo_id": 1, "codice": "A", "descrizione": "Tipo A", "fallback_tipo_indirizzo_id": 2},
            {"tipo_indirizzo_id": 2, "codice": "B", "descrizione": "Tipo B", "fallback_tipo_indirizzo_id": 3},
            {"tipo_indirizzo_id": 3, "codice": "C", "descrizione": "Tipo C", "fallback_tipo_indirizzo_id": 1},
        ]

        svc = TipiRuoloTipiIndirizzoService()
        opts = svc._compute_fallback_options(tipo_ruolo_id=10, tipo_indirizzo_id=1)

        self.assertEqual(opts, [])

    @patch(REPO_PATH, autospec=True)
    def test_compute_fallback_options_handles_self_loop(self, mock_repo_cls):
        # Edge case: una riga ha fb=se stesso (corruzione DB pre-esistente).
        # Il DFS con `visited` set deve fermarsi senza loop infinito.
        from apps.config.services.tipi_ruolo_tipi_indirizzo_service import (
            TipiRuoloTipiIndirizzoService,
        )
        mock_repo_cls.return_value.list_fallback_chain_for_ruolo.return_value = [
            {"tipo_indirizzo_id": 1, "codice": "A", "descrizione": "Tipo A", "fallback_tipo_indirizzo_id": None},
            {"tipo_indirizzo_id": 2, "codice": "B", "descrizione": "Tipo B", "fallback_tipo_indirizzo_id": 2},  # self-loop
        ]

        svc = TipiRuoloTipiIndirizzoService()
        # Per A: B ha fb=B (loop). DFS: cur=2, visited={2}, fb=2 in visited -> stop.
        # Non porta a 1, quindi B e' valido come fallback per A.
        opts = svc._compute_fallback_options(tipo_ruolo_id=10, tipo_indirizzo_id=1)

        ids = [o["tipo_indirizzo_id"] for o in opts]
        self.assertEqual(ids, [2])


class TestGetMatriceArricchito(TestCase):
    """get_matrice include non_editable_fields + fallback_options (Fase 4)."""

    @patch(REPO_PATH, autospec=True)
    @patch("apps.core.services.non_editable_fields_helper.LockColumnsRepository.list_non_editable", autospec=True)
    def test_get_matrice_arricchito(self, mock_list_locks, mock_repo_cls):
        from apps.config.services.tipi_ruolo_tipi_indirizzo_service import (
            TipiRuoloTipiIndirizzoService,
        )

        mock_list_locks.return_value = ()
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_matrice.return_value = {
            "id": 5, "tipo_ruolo_id": 10, "tipo_indirizzo_id": 1,
            "fallback_tipo_indirizzo_id": None,
        }
        mock_repo.list_fallback_chain_for_ruolo.return_value = [
            {"tipo_indirizzo_id": 1, "codice": "A", "descrizione": "A", "fallback_tipo_indirizzo_id": None},
            {"tipo_indirizzo_id": 2, "codice": "B", "descrizione": "B", "fallback_tipo_indirizzo_id": None},
        ]

        result = TipiRuoloTipiIndirizzoService().get_matrice(5)

        self.assertEqual(result["id"], 5)
        self.assertIn("non_editable_fields", result)
        self.assertEqual(set(result["non_editable_fields"]), {"tipo_ruolo_id", "tipo_indirizzo_id"})
        self.assertIn("fallback_options", result)
        ids = [o["tipo_indirizzo_id"] for o in result["fallback_options"]]
        self.assertEqual(ids, [2])
