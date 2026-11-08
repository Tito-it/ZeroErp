# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari funzioni pipeline_service (validazione lookup ID).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) PipelineServiceTests.test_run_invalid_tipo_doc_fiscale_id
2) PipelineServiceTests.test_run_invalid_utility_id
3) PipelineServiceTests.test_run_valid_ids_pass_through
4) PipelineServiceTests.test_run_none_ids_skip_validation
5) PipelineServiceTests.test_get_lotto_segnalazioni_summary_consegna_il_decimo_numero_nel_riepilogo (D2)
"""

from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError


class PipelineServiceTests(SimpleTestCase):

    # Scopo: tipo_doc_fiscale_id inesistente solleva E_PIPELINE_VALIDATION.
    @patch("apps.vendite.services.pipeline_service.DbopsRepository", autospec=True)
    def test_run_invalid_tipo_doc_fiscale_id(self, mock_dbops_cls):
        from apps.vendite.services.pipeline_service import run_lotto_pipeline

        mock_dbops_cls.return_value.check_lookup_id_exists.return_value = False

        with self.assertRaises(ServiceError) as ctx:
            run_lotto_pipeline(tipo_doc_fiscale_id=999)
        self.assertEqual(ctx.exception.code, "E_PIPELINE_VALIDATION")
        self.assertIn("tipo_doc_fiscale_id=999", ctx.exception.detail)

    # Scopo: utility_id inesistente solleva E_PIPELINE_VALIDATION.
    @patch("apps.vendite.services.pipeline_service.DbopsRepository", autospec=True)
    def test_run_invalid_utility_id(self, mock_dbops_cls):
        from apps.vendite.services.pipeline_service import run_lotto_pipeline

        mock_dbops_cls.return_value.check_lookup_id_exists.side_effect = (
            lambda *, rel, record_id: rel != "config.utilities"
        )

        with self.assertRaises(ServiceError) as ctx:
            run_lotto_pipeline(utility_id=888)
        self.assertEqual(ctx.exception.code, "E_PIPELINE_VALIDATION")
        self.assertIn("utility_id=888", ctx.exception.detail)

    # Scopo: ID validi non sollevano errore e il runner viene invocato.
    @patch("apps.vendite.services.pipeline_service.LottoPipelineRunner")
    @patch("apps.vendite.services.pipeline_service.DbopsRepository", autospec=True)
    def test_run_valid_ids_pass_through(self, mock_dbops_cls, mock_runner_cls):
        from apps.vendite.services.pipeline_service import run_lotto_pipeline

        mock_dbops_cls.return_value.check_lookup_id_exists.return_value = True
        mock_runner_cls.return_value.run_pipeline.return_value = 10

        result = run_lotto_pipeline(tipo_doc_fiscale_id=1, utility_id=2)

        self.assertEqual(result, 10)
        mock_runner_cls.return_value.run_pipeline.assert_called_once()

    # Scopo: ID None non attivano la validazione lookup e il runner viene invocato.
    @patch("apps.vendite.services.pipeline_service.LottoPipelineRunner")
    @patch("apps.vendite.services.pipeline_service.DbopsRepository", autospec=True)
    def test_run_none_ids_skip_validation(self, mock_dbops_cls, mock_runner_cls):
        from apps.vendite.services.pipeline_service import run_lotto_pipeline

        mock_runner_cls.return_value.run_pipeline.return_value = 20

        result = run_lotto_pipeline()

        self.assertEqual(result, 20)
        mock_dbops_cls.return_value.check_lookup_id_exists.assert_not_called()

    # Scopo: ⭐ B6 del piano D2 (2026-09-12) — l'envelope del riepilogo porta il
    #        decimo numero DENTRO `summary`, e il verdetto lo conta. La forma
    #        non cambia (nessuna chiave nuova al primo livello): il client legge
    #        `summary.*`, e questo test e' l'unico punto che DICHIARA che quel
    #        campo arriva — «un campo emesso e non dichiarato non si nota,
    #        perche' niente fallisce».
    # ⚠️ Si mocka il REPOSITORY e non il service: e' la catena vera
    #        repository → service → facade che va attraversata, o il test
    #        proverebbe il mock.
    def test_get_lotto_segnalazioni_summary_consegna_il_decimo_numero_nel_riepilogo(self):
        from apps.vendite.services.pipeline_service import fn_get_lotto_segnalazioni_summary

        riepilogo = {
            "fatture_critical_count": 0,
            "fatture_warning_count": 0,
            "lotto_critical_count": 0,
            "lotto_warning_count": 0,
            "lotto_info_count": 0,
            "fatture_stato_esecuzione_errore_count": 0,
            "documenti_bloccanti_count": 0,
            "documenti_presi_in_carico_count": 2,
            "critiche_giro_count": 0,
            "esiti_stato_esecuzione_errore_count": 2,
            "fermo": True,
        }
        with patch(
            "apps.vendite.services.lotto_segnalazioni_service.VenditePipelineRepository", autospec=True) as repo_cls:
            repo_cls.return_value.get_lotto_segnalazioni_summary.return_value = riepilogo
            with patch("apps.vendite.services.pipeline_service.lotto_visibile"):
                data = fn_get_lotto_segnalazioni_summary(lotto_id=80, auth_user_id=1)

        self.assertEqual(data["summary"]["esiti_stato_esecuzione_errore_count"], 2)
        # Il verdetto con ZERO critiche: e' il caso D2, e il client deve
        # leggerlo da qui e non ricalcolarlo da `critical_count`.
        self.assertEqual(data["critical_count"], 0)
        # ⭐ E dal 2026-09-19 il verdetto e' `summary["fermo"]` letto dal DB:
        #    `is_error`/`blocks_next_step` lo trasportano.
        self.assertTrue(data["is_error"])
        self.assertTrue(data["blocks_next_step"])
        self.assertIs(data["summary"]["fermo"], True)
        self.assertTrue(data["is_error"])
        self.assertTrue(data["blocks_next_step"])
