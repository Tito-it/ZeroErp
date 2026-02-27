# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari funzioni pipeline_service (validazione lookup ID).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) PipelineServiceTests.test_pr_run_invalid_tipo_doc_fiscale_id
2) PipelineServiceTests.test_pr_run_invalid_utility_id
3) PipelineServiceTests.test_pr_run_valid_ids_pass_through
4) PipelineServiceTests.test_pr_run_none_ids_skip_validation
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.service_errors import ServiceError


class PipelineServiceTests(TestCase):

    # Scopo: tipo_doc_fiscale_id inesistente solleva E_PIPELINE_VALIDATION.
    @patch("apps.vendite.services.pipeline_service.DbopsRepository")
    def test_pr_run_invalid_tipo_doc_fiscale_id(self, mock_dbops_cls):
        from apps.vendite.services.pipeline_service import pr_run_lotto_pipeline

        mock_dbops_cls.return_value.check_lookup_id_exists.return_value = False

        with self.assertRaises(ServiceError) as ctx:
            pr_run_lotto_pipeline(tipo_doc_fiscale_id=999)
        self.assertEqual(ctx.exception.code, "E_PIPELINE_VALIDATION")
        self.assertIn("tipo_doc_fiscale_id=999", ctx.exception.detail)

    # Scopo: utility_id inesistente solleva E_PIPELINE_VALIDATION.
    @patch("apps.vendite.services.pipeline_service.DbopsRepository")
    def test_pr_run_invalid_utility_id(self, mock_dbops_cls):
        from apps.vendite.services.pipeline_service import pr_run_lotto_pipeline

        mock_dbops_cls.return_value.check_lookup_id_exists.side_effect = (
            lambda *, rel, record_id: rel != "config.utilities"
        )

        with self.assertRaises(ServiceError) as ctx:
            pr_run_lotto_pipeline(utility_id=888)
        self.assertEqual(ctx.exception.code, "E_PIPELINE_VALIDATION")
        self.assertIn("utility_id=888", ctx.exception.detail)

    # Scopo: ID validi non sollevano errore e il runner viene invocato.
    @patch("apps.vendite.services.pipeline_service.LottoPipelineRunner")
    @patch("apps.vendite.services.pipeline_service.DbopsRepository")
    def test_pr_run_valid_ids_pass_through(self, mock_dbops_cls, mock_runner_cls):
        from apps.vendite.services.pipeline_service import pr_run_lotto_pipeline

        mock_dbops_cls.return_value.check_lookup_id_exists.return_value = True
        mock_runner_cls.return_value.run_pipeline.return_value = 10

        result = pr_run_lotto_pipeline(tipo_doc_fiscale_id=1, utility_id=2)

        self.assertEqual(result, 10)
        mock_runner_cls.return_value.run_pipeline.assert_called_once()

    # Scopo: ID None non attivano la validazione lookup e il runner viene invocato.
    @patch("apps.vendite.services.pipeline_service.LottoPipelineRunner")
    @patch("apps.vendite.services.pipeline_service.DbopsRepository")
    def test_pr_run_none_ids_skip_validation(self, mock_dbops_cls, mock_runner_cls):
        from apps.vendite.services.pipeline_service import pr_run_lotto_pipeline

        mock_runner_cls.return_value.run_pipeline.return_value = 20

        result = pr_run_lotto_pipeline()

        self.assertEqual(result, 20)
        mock_dbops_cls.return_value.check_lookup_id_exists.assert_not_called()
