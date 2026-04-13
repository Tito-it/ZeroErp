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
11) CommesseServiceTests.test_variazione_eccezionale_ok
12) CommesseServiceTests.test_variazione_eccezionale_commessa_stato_bloccato
13) CommesseServiceTests.test_variazione_eccezionale_riga_fatturata_bloccata
14) CommesseServiceTests.test_variazione_eccezionale_senza_motivo
15) CommesseServiceTests.test_sblocca_prezzo_ok
16) CommesseServiceTests.test_sblocca_prezzo_non_bloccato
17) CommesseServiceTests.test_riallinea_prezzo_ok
18) CommesseServiceTests.test_riallinea_prezzo_bloccato
19) CommesseServiceTests.test_riallinea_prezzo_versione_cambiata_senza_conferma
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

    # --- N7: Variazione prezzo eccezionale ---

    _ATT_BASE = {
        "id": 501,
        "commessa_id": 10,
        "prezzo_snapshot": "45.0000000000",
        "prezzo_bloccato": False,
        "listino_versione_id": 101,
        "listino_riga_id": 301,
        "pricing_mode": "FIXED",
        "prezzo_da_riallineare": False,
        "articolo_id": "019bbee2-5f6a-704f-bbd0-34ed84db252d",
        "uom_id": 1,
        "data_attivita": "2026-04-01",
        "meta": None,
        "commessa_stato": "LIBERO",
        "af_id": 601,
        "af_prezzo_unitario": "45.0000000000",
        "af_prezzo_bloccato": False,
        "fattura_riga_id": None,
    }

    # Scopo: N7 - variazione eccezionale su commessa LIBERO OK.
    @patch("apps.vendite.services.commesse_service.transaction.atomic")
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_variazione_eccezionale_ok(self, mock_repo_cls, mock_atomic):
        from apps.vendite.services.commesse_service import fn_variazione_prezzo_eccezionale

        repo = mock_repo_cls.return_value
        repo.get_attivita_pricing.return_value = dict(self._ATT_BASE)

        result = fn_variazione_prezzo_eccezionale(10, 501, {"prezzo": "42.00", "motivo": "sconto annuale"})

        self.assertEqual(result["prezzo_nuovo"], "42.00")
        self.assertTrue(result["prezzo_bloccato"])
        repo.update_attivita_prezzo.assert_called_once()
        call_kwargs = repo.update_attivita_prezzo.call_args.kwargs
        self.assertTrue(call_kwargs["prezzo_bloccato"])

    # Scopo: N7 - commessa in stato non ammesso rifiutata.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_variazione_eccezionale_commessa_stato_bloccato(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import fn_variazione_prezzo_eccezionale

        repo = mock_repo_cls.return_value
        att = dict(self._ATT_BASE)
        att["commessa_stato"] = "CHIUSO"
        repo.get_attivita_pricing.return_value = att

        with self.assertRaises(ServiceError) as ctx:
            fn_variazione_prezzo_eccezionale(10, 501, {"prezzo": "42.00", "motivo": "test"})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VARIAZIONE_PREZZO_NON_AMMESSA")

    # Scopo: N7 - riga gia` fatturata bloccata.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_variazione_eccezionale_riga_fatturata_bloccata(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import fn_variazione_prezzo_eccezionale

        repo = mock_repo_cls.return_value
        att = dict(self._ATT_BASE)
        att["fattura_riga_id"] = 999
        repo.get_attivita_pricing.return_value = att

        with self.assertRaises(ServiceError) as ctx:
            fn_variazione_prezzo_eccezionale(10, 501, {"prezzo": "42.00", "motivo": "test"})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VARIAZIONE_PREZZO_NON_AMMESSA")

    # Scopo: N7 - senza motivo rifiutata.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_variazione_eccezionale_senza_motivo(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import fn_variazione_prezzo_eccezionale

        repo = mock_repo_cls.return_value
        repo.get_attivita_pricing.return_value = dict(self._ATT_BASE)

        with self.assertRaises(ServiceError) as ctx:
            fn_variazione_prezzo_eccezionale(10, 501, {"prezzo": "42.00", "motivo": ""})
        self.assertEqual(ctx.exception.code, "E_COMMESSA_VALIDATION")

    # --- N7 sblocco ---

    # Scopo: N7 sblocco - sblocco prezzo bloccato OK.
    @patch("apps.vendite.services.commesse_service.transaction.atomic")
    @patch("apps.vendite.services.commesse_service.ListiniRepository")
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_sblocca_prezzo_ok(self, mock_comm_repo, mock_list_repo, mock_atomic):
        from apps.vendite.services.commesse_service import fn_sblocca_prezzo

        repo = mock_comm_repo.return_value
        att = dict(self._ATT_BASE)
        att["prezzo_bloccato"] = True
        repo.get_attivita_pricing.return_value = att

        mock_list_repo.return_value.test_resolver.return_value = {
            "prezzo": "45.0000000000",
            "listino_versione_id": 101,
        }

        result = fn_sblocca_prezzo(10, 501, {"motivo": "errore variazione precedente"})

        self.assertFalse(result["prezzo_bloccato"])
        self.assertEqual(result["prezzo_ricalcolato"], "45.0000000000")

    # Scopo: N7 sblocco - prezzo non bloccato rifiutato.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_sblocca_prezzo_non_bloccato(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import fn_sblocca_prezzo

        repo = mock_repo_cls.return_value
        repo.get_attivita_pricing.return_value = dict(self._ATT_BASE)  # prezzo_bloccato=False

        with self.assertRaises(ServiceError) as ctx:
            fn_sblocca_prezzo(10, 501, {"motivo": "test"})
        self.assertEqual(ctx.exception.code, "E_VENDITE_SBLOCCO_PREZZO_NON_AMMESSO")

    # --- N5: Riallineamento prezzo ---

    # Scopo: N5 - riallineamento OK su prezzo non bloccato.
    @patch("apps.vendite.services.commesse_service.transaction.atomic")
    @patch("apps.vendite.services.commesse_service.ListiniRepository")
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_riallinea_prezzo_ok(self, mock_comm_repo, mock_list_repo, mock_atomic):
        from apps.vendite.services.commesse_service import fn_riallinea_prezzo

        repo = mock_comm_repo.return_value
        repo.get_attivita_pricing.return_value = dict(self._ATT_BASE)

        mock_list_repo.return_value.test_resolver.return_value = {
            "prezzo": "46.0000000000",
            "listino_versione_id": 101,
        }

        result = fn_riallinea_prezzo(10, 501, {})

        self.assertEqual(result["prezzo_nuovo"], "46.0000000000")
        self.assertFalse(result["versione_cambiata"])

    # Scopo: N5 - riallineamento su prezzo bloccato rifiutato.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_riallinea_prezzo_bloccato(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import fn_riallinea_prezzo

        repo = mock_repo_cls.return_value
        att = dict(self._ATT_BASE)
        att["prezzo_bloccato"] = True
        repo.get_attivita_pricing.return_value = att

        with self.assertRaises(ServiceError) as ctx:
            fn_riallinea_prezzo(10, 501, {})
        self.assertEqual(ctx.exception.code, "E_COMMESSA_VALIDATION")

    # Scopo: N5 - versione cambiata senza conferma restituisce warning.
    @patch("apps.vendite.services.commesse_service.ListiniRepository")
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_riallinea_prezzo_versione_cambiata_senza_conferma(self, mock_comm_repo, mock_list_repo):
        from apps.vendite.services.commesse_service import fn_riallinea_prezzo

        repo = mock_comm_repo.return_value
        repo.get_attivita_pricing.return_value = dict(self._ATT_BASE)  # listino_versione_id=101

        mock_list_repo.return_value.test_resolver.return_value = {
            "prezzo": "48.0000000000",
            "listino_versione_id": 202,  # diversa!
        }

        result = fn_riallinea_prezzo(10, 501, {})

        self.assertTrue(result["versione_cambiata"])
        self.assertTrue(result["richiede_conferma"])
        self.assertEqual(result["versione_originale_id"], 101)
        self.assertEqual(result["versione_attuale_id"], 202)
        repo.update_attivita_prezzo.assert_not_called()
