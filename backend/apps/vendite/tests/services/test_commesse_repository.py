# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari CommesseRepository.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) CommesseRepositoryUnitTests.test_get_or_create_commessa_returns_int
2) CommesseRepositoryUnitTests.test_link_sorgente_returns_int
3) CommesseRepositoryUnitTests.test_upsert_attivita_returns_int
4) CommesseRepositoryUnitTests.test_emit_attivita_fatturabili_maps_result
5) CommesseRepositoryUnitTests.test_emit_attivita_fatturabili_dry_run_zero_writes
6) CommesseRepositoryUnitTests.test_get_commessa_stato_maps_contatori
7) CommesseRepositoryUnitTests.test_get_commessa_stato_returns_none_when_not_found
8) CommesseRepositoryUnitTests.test_log_push_run_returns_int
9) CommesseRepositoryUnitTests.test_get_push_log_maps_row
10) CommesseRepositoryUnitTests.test_get_push_log_returns_none_when_not_found
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.vendite.db.commesse_repository import CommessaAttivitaInput, CommesseRepository


def _mock_cursor(fetchone=None, fetchall=None):
    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = fetchone
    cursor.fetchall.return_value = fetchall or []
    return cursor


class CommesseRepositoryUnitTests(TestCase):

    # Scopo: Verifica che get_or_create_commessa chiami la funzione DB e restituisca int.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_get_or_create_commessa_returns_int(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(42,))
        repo = CommesseRepository()
        result = repo.get_or_create_commessa(
            billing_account_id=1,
            utility_id=2,
            tipo_commessa="AUTO",
            policy_fatturazione="DA_DOCUMENTO",
            fatturazione_immediata=False,
            priorita_operativa="NORMALE",
            emittente_soggetto_ruolo_id=3,
            competenza_dal=date(2026, 6, 1),
            competenza_al=date(2026, 6, 30),
        )
        self.assertEqual(result, 42)
        sql = mock_cursor_factory.return_value.execute.call_args[0][0]
        self.assertIn("fn_get_or_create_commessa", sql)

    # Scopo: Verifica che link_sorgente chiami la funzione DB e restituisca int.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_link_sorgente_returns_int(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(99,))
        repo = CommesseRepository()
        result = repo.link_sorgente(
            commessa_id=10,
            sorgente_tipo_id=5,
            sorgente_uid="PREV-001",
        )
        self.assertEqual(result, 99)
        sql = mock_cursor_factory.return_value.execute.call_args[0][0]
        self.assertIn("fn_link_commessa_sorgente", sql)

    # Scopo: Verifica che upsert_attivita chiami la funzione DB e restituisca int.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_upsert_attivita_returns_int(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(77,))
        repo = CommesseRepository()
        inp = CommessaAttivitaInput(
            commessa_id=10,
            segment_key="10_2026-06_BASE",
            articolo_id=1,
            uom_id=1,
            quantita=Decimal("2.0"),
            competenza_mese=date(2026, 6, 1),
            prezzo_snapshot=Decimal("22.10"),
            tipo_doc_fiscale_id=1,
            valuta_id=1,
            prezzo_bloccato=True,
            pricing_mode="FIXED",
            prezzo_da_riallineare=False,
            stato_approvazione="APPROVATA",
            stato_emissione="NON_EMESSA",
            tipo_movimento="NORMALE",
            tipo_consumo="ACCONTO",
        )
        result = repo.upsert_attivita(inp)
        self.assertEqual(result, 77)
        sql = mock_cursor_factory.return_value.execute.call_args[0][0]
        self.assertIn("fn_upsert_commessa_attivita", sql)

    # Scopo: Verifica mapping CommessaEmitResult da fn_emit_attivita_fatturabili_da_commessa.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_emit_attivita_fatturabili_maps_result(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(5, 3, 2))
        repo = CommesseRepository()
        result = repo.emit_attivita_fatturabili(commessa_id=10)
        self.assertEqual(result["total_candidate"], 5)
        self.assertEqual(result["inserted_rows"], 3)
        self.assertEqual(result["updated_rows"], 2)
        sql = mock_cursor_factory.return_value.execute.call_args[0][0]
        self.assertIn("fn_emit_attivita_fatturabili_da_commessa", sql)

    # Scopo: Verifica che dry_run=True venga passato e non produca righe scritte.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_emit_attivita_fatturabili_dry_run_zero_writes(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(3, 3, 0))
        repo = CommesseRepository()
        result = repo.emit_attivita_fatturabili(commessa_id=10, dry_run=True)
        self.assertEqual(result["total_candidate"], 3)
        params = mock_cursor_factory.return_value.execute.call_args[0][1]
        # p_dry_run è il 4° parametro (indice 3)
        self.assertTrue(params[3])

    # Scopo: Verifica mapping CommessaStatoResult da fn_get_commessa_stato.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_get_commessa_stato_maps_contatori(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(10, 8, 6))
        repo = CommesseRepository()
        result = repo.get_commessa_stato(commessa_id=10)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["total_attivita"], 10)
        self.assertEqual(result["total_approvate"], 8)
        self.assertEqual(result["total_emesse"], 6)

    # Scopo: Verifica che get_commessa_stato restituisca None quando la commessa non esiste.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_get_commessa_stato_returns_none_when_not_found(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=None)
        repo = CommesseRepository()
        result = repo.get_commessa_stato(commessa_id=999)
        self.assertIsNone(result)

    # Scopo: Verifica che log_push_run chiami fn_log_commessa_push_run e restituisca int.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_log_push_run_returns_int(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(55,))
        repo = CommesseRepository()
        result = repo.log_push_run(
            stato="COMPLETATO",
            dry_run=False,
            source_types=["HandlerPreventivi"],
            risultato={"HandlerPreventivi": {"created": 3, "errors": []}},
            durata_ms=1200,
            user_run="scheduler",
        )
        self.assertEqual(result, 55)
        sql = mock_cursor_factory.return_value.execute.call_args[0][0]
        self.assertIn("fn_log_commessa_push_run", sql)

    # Scopo: Verifica mapping CommessaPushLogRow da SELECT commesse_push_log.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_get_push_log_maps_row(self, mock_cursor_factory):
        ts = datetime(2026, 2, 24, 10, 0, 0, tzinfo=timezone.utc)
        mock_cursor_factory.return_value = _mock_cursor(
            fetchone=(
                55,
                ts,
                False,
                ["HandlerPreventivi", "HandlerOrdini"],
                '{"HandlerPreventivi": {"created": 3}}',
                "COMPLETATO",
                1200,
                "scheduler",
            )
        )
        repo = CommesseRepository()
        result = repo.get_push_log(55)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["id"], 55)
        self.assertEqual(result["stato"], "COMPLETATO")
        self.assertEqual(result["durata_ms"], 1200)
        self.assertFalse(result["dry_run"])
        self.assertEqual(result["source_types"], ["HandlerPreventivi", "HandlerOrdini"])
        self.assertIn("HandlerPreventivi", result["risultato"] or {})

    # Scopo: Verifica che get_push_log restituisca None quando il log non esiste.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_get_push_log_returns_none_when_not_found(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=None)
        repo = CommesseRepository()
        result = repo.get_push_log(999)
        self.assertIsNone(result)
