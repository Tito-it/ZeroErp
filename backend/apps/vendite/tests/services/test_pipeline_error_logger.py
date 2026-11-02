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
