# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari CommessaPushOrchestrator.
# ------------------------------------------------------------


"""
Indice test eseguiti:
1) CommessePushOrchestratorTests.test_run_completato_tutti_handler
2) CommessePushOrchestratorTests.test_run_parziale_un_handler_fallisce
3) CommessePushOrchestratorTests.test_run_errore_tutti_handler_falliscono
4) CommessePushOrchestratorTests.test_run_errore_nessun_handler
5) CommessePushOrchestratorTests.test_run_source_types_filtra_handler
6) CommessePushOrchestratorTests.test_run_dry_run_passa_flag_al_log
7) CommessePushOrchestratorTests.test_run_push_log_id_valorizzato
8) CommessePushOrchestratorTests.test_run_isolamento_handler_continua_dopo_eccezione
9) CommessePushOrchestratorTests.test_run_risultato_jsonb_include_tutti_handler
"""

from unittest import TestCase
from unittest.mock import MagicMock

from apps.vendite.db.commesse_repository import CommesseRepository
from apps.vendite.services.commesse_push_orchestrator import CommessaPushOrchestrator, PushReport
from apps.vendite.services.commesse_source_handlers import BaseSourceHandler, HandlerResult


def _mock_repo(push_log_id: int = 1) -> MagicMock:
    repo = MagicMock(spec=CommesseRepository)
    repo.log_push_run.return_value = push_log_id
    return repo


def _mock_handler(name: str, result: HandlerResult) -> MagicMock:
    h = MagicMock(spec=BaseSourceHandler)
    h.name = name
    h.run.return_value = result
    return h


def _ok_result(name: str, created: int = 1) -> HandlerResult:
    return HandlerResult(handler_name=name, created=created)


class CommessePushOrchestratorTests(TestCase):

    # Scopo: tutti gli handler riescono → stato COMPLETATO.
    def test_run_completato_tutti_handler(self):
        repo = _mock_repo()
        h1 = _mock_handler("HandlerA", _ok_result("HandlerA", created=2))
        h2 = _mock_handler("HandlerB", _ok_result("HandlerB", created=1))
        orch = CommessaPushOrchestrator(repo, [h1, h2])

        report = orch.run()

        self.assertEqual(report.stato, "COMPLETATO")
        self.assertEqual(len(report.handlers), 2)
        repo.log_push_run.assert_called_once()

    # Scopo: un handler lancia eccezione → stato PARZIALE, errore catturato nel risultato.
    def test_run_parziale_un_handler_fallisce(self):
        repo = _mock_repo()
        h_ok = _mock_handler("HandlerA", _ok_result("HandlerA"))
        h_fail = MagicMock(spec=BaseSourceHandler)
        h_fail.name = "HandlerB"
        h_fail.run.side_effect = RuntimeError("DB error")
        orch = CommessaPushOrchestrator(repo, [h_ok, h_fail])

        report = orch.run()

        self.assertEqual(report.stato, "PARZIALE")
        self.assertEqual(len(report.handlers), 2)
        b_result = next(r for r in report.handlers if r.handler_name == "HandlerB")
        self.assertEqual(len(b_result.errors), 1)
        self.assertIn("DB error", b_result.errors[0])

    # Scopo: tutti gli handler falliscono → stato ERRORE.
    def test_run_errore_tutti_handler_falliscono(self):
        repo = _mock_repo()
        h1 = MagicMock(spec=BaseSourceHandler)
        h1.name = "HandlerA"
        h1.run.side_effect = RuntimeError("fail A")
        h2 = MagicMock(spec=BaseSourceHandler)
        h2.name = "HandlerB"
        h2.run.side_effect = RuntimeError("fail B")
        orch = CommessaPushOrchestrator(repo, [h1, h2])

        report = orch.run()

        self.assertEqual(report.stato, "ERRORE")
        repo.log_push_run.assert_called_once()

    # Scopo: nessun handler registrato → stato ERRORE, log scritto.
    def test_run_errore_nessun_handler(self):
        repo = _mock_repo()
        orch = CommessaPushOrchestrator(repo, [])

        report = orch.run()

        self.assertEqual(report.stato, "ERRORE")
        self.assertEqual(report.handlers, [])
        repo.log_push_run.assert_called_once()

    # Scopo: source_types=[X] esegue solo l'handler X, gli altri non chiamati.
    def test_run_source_types_filtra_handler(self):
        repo = _mock_repo()
        h1 = _mock_handler("HandlerA", _ok_result("HandlerA"))
        h2 = _mock_handler("HandlerB", _ok_result("HandlerB"))
        orch = CommessaPushOrchestrator(repo, [h1, h2])

        report = orch.run(source_types=["HandlerA"])

        self.assertEqual(len(report.handlers), 1)
        self.assertEqual(report.handlers[0].handler_name, "HandlerA")
        h1.run.assert_called_once()
        h2.run.assert_not_called()

    # Scopo: dry_run=True → log scritto con dry_run=True, flag propagato all'handler.
    def test_run_dry_run_passa_flag_al_log(self):
        repo = _mock_repo()
        h = _mock_handler("HandlerA", _ok_result("HandlerA"))
        orch = CommessaPushOrchestrator(repo, [h])

        report = orch.run(dry_run=True)

        self.assertTrue(report.dry_run)
        repo.log_push_run.assert_called_once()
        call_kwargs = repo.log_push_run.call_args.kwargs
        self.assertTrue(call_kwargs["dry_run"])
        h.run.assert_called_once_with(dry_run=True)

    # Scopo: push_log_id nel report corrisponde al valore restituito da log_push_run.
    def test_run_push_log_id_valorizzato(self):
        repo = _mock_repo(push_log_id=42)
        h = _mock_handler("HandlerA", _ok_result("HandlerA"))
        orch = CommessaPushOrchestrator(repo, [h])

        report = orch.run()

        self.assertEqual(report.push_log_id, 42)

    # Scopo: eccezione in HandlerA non interrompe HandlerB — isolamento garantito.
    def test_run_isolamento_handler_continua_dopo_eccezione(self):
        repo = _mock_repo()
        h_fail = MagicMock(spec=BaseSourceHandler)
        h_fail.name = "HandlerA"
        h_fail.run.side_effect = RuntimeError("crash")
        h_ok = _mock_handler("HandlerB", _ok_result("HandlerB", created=3))
        orch = CommessaPushOrchestrator(repo, [h_fail, h_ok])

        report = orch.run()

        h_ok.run.assert_called_once()
        b_result = next(r for r in report.handlers if r.handler_name == "HandlerB")
        self.assertEqual(b_result.created, 3)
        self.assertEqual(b_result.errors, [])

    # Scopo: as_risultato include chiavi per tutti gli handler eseguiti.
    def test_run_risultato_jsonb_include_tutti_handler(self):
        repo = _mock_repo()
        h1 = _mock_handler("HandlerA", HandlerResult(handler_name="HandlerA", created=2, updated=1))
        h2 = _mock_handler("HandlerB", HandlerResult(handler_name="HandlerB", skipped=5))
        orch = CommessaPushOrchestrator(repo, [h1, h2])

        report = orch.run()

        risultato = report.as_risultato()
        self.assertIn("HandlerA", risultato)
        self.assertIn("HandlerB", risultato)
        self.assertEqual(risultato["HandlerA"]["created"], 2)
        self.assertEqual(risultato["HandlerB"]["skipped"], 5)
        call_kwargs = repo.log_push_run.call_args.kwargs
        self.assertIn("HandlerA", call_kwargs["risultato"])
