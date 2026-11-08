# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari logger errori pipeline vendite.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) PipelineErrorLoggerUnitTests.test_log_error_lotto_writes_pipeline_log_and_technical_log
2) PipelineErrorLoggerUnitTests.test_log_error_fattura_writes_fattura_log_and_technical_log
3) PipelineErrorLoggerUnitTests.test_log_error_lotto_without_lotto_id_keeps_only_technical_log
4) PipelineErrorLoggerUnitTests.test_log_error_lotto_passa_la_commessa_al_log_del_lotto
"""

from unittest.mock import MagicMock
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.vendite.services.pipeline_error_logger import PipelineErrorLogger


class PipelineErrorLoggerUnitTests(SimpleTestCase):
    # Scopo: Verifica il caso `test_log_error_lotto_writes_pipeline_log_and_technical_log`.
    @patch("apps.vendite.services.pipeline_error_logger.ErrorManager.log_error_only")
    def test_log_error_lotto_writes_pipeline_log_and_technical_log(self, mocked_log_error_only):
        repo = MagicMock()
        logger = PipelineErrorLogger(repository=repo)

        logger.log_error(
            scope="LOTTO",
            severity="C",
            code="E_PIPELINE",
            message="Errore pipeline",
            detail="boom",
            lotto_id=10,
            stato_doc_fiscale_id=2,
            context={"task": "select_attivita"},
        )

        mocked_log_error_only.assert_called_once()
        repo.log_pipeline_fase.assert_called_once()
        repo.log_fattura.assert_not_called()

    # Scopo: Verifica il caso `test_log_error_fattura_writes_fattura_log_and_technical_log`.
    @patch("apps.vendite.services.pipeline_error_logger.ErrorManager.log_error_only")
    def test_log_error_fattura_writes_fattura_log_and_technical_log(self, mocked_log_error_only):
        repo = MagicMock()
        logger = PipelineErrorLogger(repository=repo)

        logger.log_error(
            scope="FATTURA",
            severity="W",
            code="W_FATTURA_TEST",
            message="Warning fattura",
            detail=None,
            lotto_id=10,
            fattura_id=1001,
            context={"task": "numera_fatture"},
        )

        mocked_log_error_only.assert_called_once()
        repo.log_fattura.assert_called_once()
        repo.log_pipeline_fase.assert_not_called()

    # Scopo: Verifica il caso `test_log_error_lotto_without_lotto_id_keeps_only_technical_log`.
    @patch("apps.vendite.services.pipeline_error_logger.ErrorManager.log_error_only")
    def test_log_error_lotto_without_lotto_id_keeps_only_technical_log(self, mocked_log_error_only):
        repo = MagicMock()
        logger = PipelineErrorLogger(repository=repo)

        logger.log_error(
            scope="LOTTO",
            severity="C",
            code="E_PIPELINE",
            message="Errore senza lotto",
            detail=None,
            lotto_id=None,
            context={},
        )

        mocked_log_error_only.assert_called_once()
        repo.log_pipeline_fase.assert_not_called()
        repo.log_fattura.assert_not_called()

    # Scopo: V-7-bis (brief-db-sorgente-documento-e-riga §8.23) — la commessa
    #        dichiarata da chi solleva arriva alla colonna, accanto alla
    #        `gruppo_key`, e non solo nel `context` (JSON senza contratto).
    @patch("apps.vendite.services.pipeline_error_logger.ErrorManager.log_error_only")
    def test_log_error_lotto_passa_la_commessa_al_log_del_lotto(self, _mocked_log_error_only):
        repo = MagicMock()
        logger = PipelineErrorLogger(repository=repo)

        logger.log_error(
            scope="LOTTO",
            severity="C",
            code="E_PULL_COMMESSA",
            message="Errore emissione commessa 77",
            lotto_id=10,
            context={"commessa_id": 77},
            gruppo_key="ORDINE_VENDITA:aaa",
            commessa_id=77,
        )

        kwargs = repo.log_pipeline_fase.call_args.kwargs
        self.assertEqual(kwargs["commessa_id"], 77)
        self.assertEqual(kwargs["gruppo_key"], "ORDINE_VENDITA:aaa")

        # Chi non la dichiara non parla di una commessa: `None`, non un'inferenza.
        logger.log_error(
            scope="LOTTO", severity="C", code="E_PIPELINE", message="ko", lotto_id=10,
        )
        self.assertIsNone(repo.log_pipeline_fase.call_args.kwargs["commessa_id"])
