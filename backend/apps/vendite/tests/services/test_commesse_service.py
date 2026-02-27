# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari funzioni commesse_service.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) CommesseServiceTests.test_pr_run_commesse_push_ok
2) CommesseServiceTests.test_pr_run_commesse_push_skipped
3) CommesseServiceTests.test_fn_get_commesse_push_log_ok
4) CommesseServiceTests.test_fn_get_commesse_push_log_not_found
5) CommesseServiceTests.test_fn_get_commessa_stato_ok
6) CommesseServiceTests.test_fn_get_commessa_stato_not_found
7) CommesseServiceTests.test_fn_list_commessa_attivita_ok
8) CommesseServiceTests.test_fn_list_commessa_attivita_invalid_limit
9) CommesseServiceTests.test_pr_run_commesse_push_invalid_source_types
10) CommesseServiceTests.test_build_handlers_only_active_sources
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.commesse_push_orchestrator import PushReport
from apps.vendite.services.commesse_source_handlers import HandlerResult


class CommesseServiceTests(TestCase):

    # --- pr_run_commesse_push ---

    # Scopo: push ok → stato COMPLETATO con handler nel risultato.
    @patch("apps.vendite.services.commesse_service.CommessaPushOrchestrator")
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    @patch("apps.vendite.services.commesse_service._build_handlers")
    def test_pr_run_commesse_push_ok(self, mock_build, mock_repo_cls, mock_orch_cls):
        from apps.vendite.services.commesse_service import pr_run_commesse_push

        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_build.return_value = []

        report = PushReport(
            dry_run=False,
            stato="COMPLETATO",
            handlers=[HandlerResult(handler_name="HandlerA", created=3)],
            push_log_id=10,
            durata_ms=120,
        )
        mock_orch_cls.return_value.run.return_value = report

        result = pr_run_commesse_push(dry_run=False)

        self.assertEqual(result["stato"], "COMPLETATO")
        self.assertEqual(result["push_log_id"], 10)
        self.assertEqual(len(result["handlers"]), 1)
        self.assertEqual(result["handlers"][0]["handler_name"], "HandlerA")
        self.assertEqual(result["handlers"][0]["created"], 3)

    # Scopo: lock non acquisito → stato SKIPPED, nessun handler.
    @patch("apps.vendite.services.commesse_service.CommessaPushOrchestrator")
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    @patch("apps.vendite.services.commesse_service._build_handlers")
    def test_pr_run_commesse_push_skipped(self, mock_build, mock_repo_cls, mock_orch_cls):
        from apps.vendite.services.commesse_service import pr_run_commesse_push

        mock_repo_cls.return_value = MagicMock()
        mock_build.return_value = []

        report = PushReport(dry_run=False, stato="SKIPPED", durata_ms=0)
        mock_orch_cls.return_value.run.return_value = report

        result = pr_run_commesse_push()

        self.assertEqual(result["stato"], "SKIPPED")
        self.assertIsNone(result["push_log_id"])
        self.assertEqual(result["handlers"], [])

    # Scopo: source_types con codice non riconosciuto → ServiceError validazione.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_pr_run_commesse_push_invalid_source_types(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import pr_run_commesse_push

        mock_repo_cls.return_value.list_active_push_sources.return_value = ["PREVENTIVO"]

        with self.assertRaises(ServiceError) as ctx:
            pr_run_commesse_push(source_types=["SORGENTE_INESISTENTE"])
        self.assertEqual(ctx.exception.code, "E_COMMESSA_VALIDATION")
        self.assertIn("SORGENTE_INESISTENTE", ctx.exception.detail)
        self.assertIn("PREVENTIVO", ctx.exception.detail)

    # Scopo: _build_handlers costruisce solo handler per sorgenti attive in DB.
    def test_build_handlers_only_active_sources(self):
        from apps.vendite.services.commesse_service import _build_handlers

        mock_repo = MagicMock()
        mock_repo.list_active_push_sources.return_value = ["PREVENTIVO", "CONTRATTO"]

        handlers = _build_handlers(mock_repo)

        self.assertEqual(len(handlers), 2)
        codici = [h.sorgente_codice for h in handlers]
        self.assertEqual(codici, ["PREVENTIVO", "CONTRATTO"])

    # --- fn_get_commesse_push_log ---

    # Scopo: push log trovato → restituisce dict con i dati.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_fn_get_commesse_push_log_ok(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import fn_get_commesse_push_log

        mock_repo_cls.return_value.get_push_log.return_value = {
            "id": 5,
            "run_at": "2026-02-26T10:00:00",
            "dry_run": False,
            "source_types": ["SRC_A"],
            "risultato": {"HandlerA": {"created": 1}},
            "stato": "COMPLETATO",
            "durata_ms": 100,
        }

        result = fn_get_commesse_push_log(push_log_id=5)

        self.assertEqual(result["id"], 5)
        self.assertEqual(result["stato"], "COMPLETATO")

    # Scopo: push log non trovato → ServiceError.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_fn_get_commesse_push_log_not_found(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import fn_get_commesse_push_log

        mock_repo_cls.return_value.get_push_log.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            fn_get_commesse_push_log(push_log_id=999)
        self.assertEqual(ctx.exception.code, "E_COMMESSA_PUSH_LOG_NOT_FOUND")

    # --- fn_get_commessa_stato ---

    # Scopo: commessa trovata → restituisce commessa_id + contatori.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_fn_get_commessa_stato_ok(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import fn_get_commessa_stato

        mock_repo_cls.return_value.get_commessa_stato.return_value = {
            "total_attivita": 10,
            "total_approvate": 8,
            "total_emesse": 5,
        }

        result = fn_get_commessa_stato(commessa_id=1)

        self.assertEqual(result["commessa_id"], 1)
        self.assertEqual(result["total_attivita"], 10)

    # Scopo: commessa non trovata → ServiceError.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_fn_get_commessa_stato_not_found(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import fn_get_commessa_stato

        mock_repo_cls.return_value.get_commessa_stato.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            fn_get_commessa_stato(commessa_id=999)
        self.assertEqual(ctx.exception.code, "E_COMMESSA_NOT_FOUND")

    # --- fn_list_commessa_attivita ---

    # Scopo: lista attivita → restituisce dict con commessa_id e dati paginati.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_fn_list_commessa_attivita_ok(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import fn_list_commessa_attivita

        mock_repo_cls.return_value.list_commessa_attivita.return_value = {
            "count": 0,
            "rows": [],
        }

        result = fn_list_commessa_attivita(commessa_id=1, limit=50, offset=0)

        self.assertEqual(result["commessa_id"], 1)
        self.assertEqual(result["count"], 0)

    # Scopo: limit fuori range → ServiceError validazione.
    def test_fn_list_commessa_attivita_invalid_limit(self):
        from apps.vendite.services.commesse_service import fn_list_commessa_attivita

        with self.assertRaises(ServiceError) as ctx:
            fn_list_commessa_attivita(commessa_id=1, limit=500, offset=0)
        self.assertEqual(ctx.exception.code, "E_COMMESSA_VALIDATION")
