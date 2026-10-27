# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari repository pipeline vendite.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) VenditePipelineRepositoryUnitTests.test_get_step_processes_returns_list_from_jsonb_list
2) VenditePipelineRepositoryUnitTests.test_get_step_processes_decodes_jsonb_string_list
3) VenditePipelineRepositoryUnitTests.test_get_step_processes_returns_empty_on_invalid_json
4) VenditePipelineRepositoryUnitTests.test_run_prepare_sdi_payload_lotto_task_maps_rows
5) VenditePipelineRepositoryUnitTests.test_run_prepare_sdi_payload_lotto_task_returns_empty_list
6) VenditePipelineRepositoryUnitTests.test_log_fattura_inserts_with_explicit_critical
7) VenditePipelineRepositoryUnitTests.test_log_fatture_lotto_sets_critical_from_status
8) VenditePipelineRepositoryUnitTests.test_is_lotto_in_errore_returns_true_when_stato_is_errore
9) VenditePipelineRepositoryUnitTests.test_is_lotto_in_errore_returns_false_when_lotto_not_found
10) VenditePipelineRepositoryUnitTests.test_get_lotto_segnalazioni_summary_maps_counts
10-bis) VenditePipelineRepositoryUnitTests.test_get_lotto_segnalazioni_summary_ripiego_a_riga_assente
11) VenditePipelineRepositoryUnitTests.test_get_pipeline_id_for_step_returns_id_when_found
12) VenditePipelineRepositoryUnitTests.test_get_pipeline_id_for_step_returns_none_when_not_found
13) VenditePipelineRepositoryUnitTests.test_task_policy_exists_returns_true_when_policy_active
14) VenditePipelineRepositoryUnitTests.test_task_policy_exists_returns_false_when_no_policy
15) VenditePipelineRepositoryUnitTests.test_resolve_lotto_task_execution_mode_maps_row
16) VenditePipelineRepositoryUnitTests.test_resolve_lotto_task_execution_mode_decodes_meta_strings
17) VenditePipelineRepositoryUnitTests.test_start_lotto_task_run_returns_task_run_result
18) VenditePipelineRepositoryUnitTests.test_complete_lotto_task_run_calls_sql_function
19) VenditePipelineRepositoryUnitTests.test_fail_lotto_task_run_calls_sql_function_with_error_params
20) VenditePipelineRepositoryUnitTests.test_set_lotto_job_stato_updates_only_stato_lotto
21) VenditePipelineRepositoryUnitTests.test_set_lotto_job_stato_non_giudica_il_passaggio
22) VenditePipelineRepositoryUnitTests.test_update_lotto_stato_doc_passa_dal_verbo_di_processo
22b) VenditePipelineRepositoryUnitTests.test_set_lotto_job_stato_completato_puo_andare_in_errore
23) VenditePipelineRepositoryUnitTests.test_list_lotto_task_runs_maps_rows
24) VenditePipelineRepositoryUnitTests.test_popola_fatture_rettifiche_chiama_la_fn_e_ritorna_le_coppie
25) VenditePipelineRepositoryUnitTests.test_popola_fatture_rettifiche_casta_id_a_intero
26) VenditePipelineRepositoryUnitTests.test_gruppi_di_commessa_decodifica_il_jsonb_stringa
27) VenditePipelineRepositoryUnitTests.test_gruppi_di_commessa_forma_inattesa_ripiega_a_vuoto
28) VenditePipelineRepositoryUnitTests.test_log_pipeline_fase_passa_la_gruppo_key_per_nome
"""

from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch
from unittest import TestCase

from datetime import date
from decimal import Decimal

from apps.vendite.db.pipeline_repository import TaskExecutionMode, TaskRunResult, VenditePipelineRepository


class VenditePipelineRepositoryUnitTests(TestCase):
    # Scopo: Verifica il caso `test_get_step_processes_returns_list_from_jsonb_list`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_get_step_processes_returns_list_from_jsonb_list(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = ([{"task": "select_attivita"}],)
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        processi = repo.get_step_processes(
            1,
            tipo_lotto="MASSIVO",
            utility_id=None,
            tipo_doc_fiscale_id=None,
            rollback=False,
        )

        self.assertEqual(processi, [{"task": "select_attivita"}])

    # Scopo: Verifica il caso `test_get_step_processes_decodes_jsonb_string_list`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_get_step_processes_decodes_jsonb_string_list(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = ('[{"task":"generate_fatture_righe"}]',)
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        processi = repo.get_step_processes(
            1,
            tipo_lotto="MASSIVO",
            utility_id=None,
            tipo_doc_fiscale_id=None,
            rollback=False,
        )

        self.assertEqual(processi, [{"task": "generate_fatture_righe"}])

    # Scopo: Verifica il caso `test_get_step_processes_returns_empty_on_invalid_json`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_get_step_processes_returns_empty_on_invalid_json(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = ("not-a-json",)
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        processi = repo.get_step_processes(
            1,
            tipo_lotto="MASSIVO",
            utility_id=None,
            tipo_doc_fiscale_id=None,
            rollback=False,
        )

        self.assertEqual(processi, [])

    # Scopo: Verifica il caso `test_run_prepare_sdi_payload_lotto_task_maps_rows`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_run_prepare_sdi_payload_lotto_task_maps_rows(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchall.return_value = [
            (
                101, 2001, 1, 3, "2026/A/123", 123, date(2026, 2, 17),
                501, 601, 1, Decimal("99.50"),
            )
        ]
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        result = repo.run_prepare_sdi_payload_lotto_task(
            lotto_id=10,
            stato_sdi_codice_interno="DA_INVIARE",
            force_new_tentativo=False,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].fattura_sdi_id, 101)
        self.assertEqual(result[0].fattura_id, 2001)
        self.assertEqual(result[0].codice_documento, "2026/A/123")
        self.assertEqual(result[0].billing_account_id, 501)
        self.assertEqual(result[0].emittente_soggetto_ruolo_id, 601)

    # Scopo: Verifica il caso `test_run_prepare_sdi_payload_lotto_task_returns_empty_list`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_run_prepare_sdi_payload_lotto_task_returns_empty_list(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchall.return_value = []
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        result = repo.run_prepare_sdi_payload_lotto_task(
            lotto_id=10,
            stato_sdi_codice_interno="DA_INVIARE",
            force_new_tentativo=False,
        )

        self.assertEqual(result, [])

    # Scopo: Verifica il caso `test_log_fattura_inserts_with_explicit_critical`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_log_fattura_inserts_with_explicit_critical(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        repo.log_fattura(
            fattura_id=123,
            status="W",
            messaggio="warning test",
            critical=True,
            meta={"scope": "FATTURA"},
        )

        cursor.execute.assert_called_once()
        _, execute_params = cursor.execute.call_args.args
        self.assertEqual(execute_params[0], "warning test")
        self.assertEqual(execute_params[1], "W")
        self.assertEqual(execute_params[3], 123)

    # Scopo: Verifica il caso `test_log_fatture_lotto_sets_critical_from_status`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_log_fatture_lotto_sets_critical_from_status(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        repo.log_fatture_lotto(
            lotto_id=55,
            status="C",
            messaggio="critical lotto",
            meta={"scope": "LOTTO"},
        )

        cursor.execute.assert_called_once()
        _, execute_params = cursor.execute.call_args.args
        self.assertEqual(execute_params[0], "critical lotto")
        self.assertEqual(execute_params[1], "C")
        self.assertEqual(execute_params[3], 55)

    # Scopo: Verifica il caso `test_is_lotto_in_errore_returns_true_when_stato_is_errore`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_is_lotto_in_errore_returns_true_when_stato_is_errore(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = (True,)
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        result = repo.is_lotto_in_errore(10)

        self.assertTrue(result)

    # Scopo: Verifica il caso `test_is_lotto_in_errore_returns_false_when_lotto_not_found`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_is_lotto_in_errore_returns_false_when_lotto_not_found(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = None
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        result = repo.is_lotto_in_errore(999999)

        self.assertFalse(result)

    # Scopo: Verifica il caso `test_get_lotto_segnalazioni_summary_maps_counts`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_get_lotto_segnalazioni_summary_maps_counts(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        # ⭐ I NOMI vengono dal cursore (`row_to_dict`), e qui il cursore finto
        #    li dichiara nell'ORDINE della SELECT: e' il contratto che il test
        #    presidia. Una colonna aggiunta alla SELECT e non al `TypedDict` —
        #    o rinominata — fa divergere il dict atteso, invece di uscire a
        #    video con un numero plausibile sotto il nome sbagliato.
        cursor.description = [
            SimpleNamespace(name=nome) for nome in (
                "fatture_critical_count", "fatture_warning_count",
                "lotto_critical_count", "lotto_warning_count", "lotto_info_count",
                "fatture_stato_esecuzione_errore_count",
                "documenti_bloccanti_count", "documenti_presi_in_carico_count",
                "critiche_giro_count", "esiti_stato_esecuzione_errore_count",
                "fermo",
            )
        ]
        cursor.fetchone.return_value = (1, 2, 3, 4, 5, 7, 2, 4, 1, 3, True)
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        result = repo.get_lotto_segnalazioni_summary(10)

        self.assertEqual(
            result,
            {
                "fatture_critical_count": 1,
                "fatture_warning_count": 2,
                "lotto_critical_count": 3,
                "lotto_warning_count": 4,
                "lotto_info_count": 5,
                "fatture_stato_esecuzione_errore_count": 7,
                # ⭐ I GESTI, non gli allarmi: due documenti da togliere su
                #    quattro presi in carico, piu' una critica del GIRO che
                #    non si toglie in nessun modo.
                "documenti_bloccanti_count": 2,
                "documenti_presi_in_carico_count": 4,
                "critiche_giro_count": 1,
                # ⭐ Il DECIMO (D2, `20260912-16`): tre documenti presi in carico
                #    il cui ultimo esito e' ERRORE. Questo entra nel verdetto.
                "esiti_stato_esecuzione_errore_count": 3,
                # ⭐ L'UNDICESIMA (D-V1, `20260919-02`): il verdetto, letto e
                #    non ricalcolato. Resta un booleano: `int(True)` a video
                #    sarebbe un «1» sotto il nome sbagliato.
                "fermo": True,
            },
        )
        self.assertIs(result["fermo"], True)
        execute_sql, execute_params = cursor.execute.call_args.args
        self.assertIn("fn_get_lotto_segnalazioni_summary", execute_sql)
        # ⛔ La colonna si chiede PER NOME: un lettore posizionale sbagliato non
        #    protesta, mostra numeri plausibili e falsi.
        self.assertIn("esiti_stato_esecuzione_errore_count", execute_sql)
        self.assertIn("fermo", execute_sql)
        self.assertEqual(execute_params, [10])

    # Scopo: a riga assente (difensivo: la funzione risponde sempre una riga)
    #        il ripiego e' zero sui conteggi e `False` sul verdetto — non uno
    #        zero intero sotto la chiave booleana.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_get_lotto_segnalazioni_summary_ripiego_a_riga_assente(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.description = [
            SimpleNamespace(name=nome) for nome in (
                "fatture_critical_count", "esiti_stato_esecuzione_errore_count", "fermo",
            )
        ]
        cursor.fetchone.return_value = None
        mocked_cursor_factory.return_value = cursor

        result = VenditePipelineRepository().get_lotto_segnalazioni_summary(10)

        self.assertEqual(result["fatture_critical_count"], 0)
        self.assertEqual(result["esiti_stato_esecuzione_errore_count"], 0)
        self.assertIs(result["fermo"], False)

    # Scopo: Verifica il caso `test_get_pipeline_id_for_step_returns_id_when_found`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_get_pipeline_id_for_step_returns_id_when_found(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = (42,)
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        result = repo.get_pipeline_id_for_step("MASSIVO", 2, None, None)

        self.assertEqual(result, 42)
        execute_sql, execute_params = cursor.execute.call_args.args
        self.assertIn("fn_resolve_fatturazione_pipeline_step", execute_sql)
        self.assertEqual(execute_params, ["MASSIVO", 2, None, None])

    # Scopo: Verifica il caso `test_get_pipeline_id_for_step_returns_none_when_not_found`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_get_pipeline_id_for_step_returns_none_when_not_found(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = None
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        result = repo.get_pipeline_id_for_step("MASSIVO", 2, None, None)

        self.assertIsNone(result)

    # Scopo: Verifica il caso `test_task_policy_exists_returns_true_when_policy_active`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_task_policy_exists_returns_true_when_policy_active(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = (True,)
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        result = repo.task_policy_exists(100, "generate_fatture_righe")

        self.assertTrue(result)
        execute_sql, execute_params = cursor.execute.call_args.args
        self.assertIn("fatturazione_pipeline_task_policy", execute_sql)
        self.assertEqual(execute_params, [100, "generate_fatture_righe"])

    # Scopo: Verifica il caso `test_task_policy_exists_returns_false_when_no_policy`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_task_policy_exists_returns_false_when_no_policy(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = (False,)
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        result = repo.task_policy_exists(100, "task_senza_policy")

        self.assertFalse(result)

    # Scopo: Verifica il caso `test_resolve_lotto_task_execution_mode_maps_row`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_resolve_lotto_task_execution_mode_maps_row(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = (
            "RUN", True, "RESUME_TASK", None, None, {"max_tentativi": 3}, {},
        )
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        result = repo.resolve_lotto_task_execution_mode(1, 100, 2, "generate_fatture_righe")

        self.assertIsInstance(result, TaskExecutionMode)
        self.assertEqual(result.execution_mode, "RUN")
        self.assertTrue(result.annullabile)
        self.assertEqual(result.resume_mode, "RESUME_TASK")
        self.assertIsNone(result.last_task_stato)
        self.assertIsNone(result.last_tentativo)
        self.assertEqual(result.policy_meta, {"max_tentativi": 3})
        self.assertEqual(result.run_meta, {})
        execute_sql, execute_params = cursor.execute.call_args.args
        self.assertIn("fn_resolve_lotto_task_execution_mode", execute_sql)
        self.assertEqual(execute_params, [1, 100, 2, "generate_fatture_righe"])

    # Scopo: Verifica che policy_meta e run_meta vengano decodificati correttamente da stringa JSON.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_resolve_lotto_task_execution_mode_decodes_meta_strings(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = (
            "SKIP", False, "NO_RESUME", "COMPLETATO", 2,
            '{"key": "val"}', '{"run": true}',
        )
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        result = repo.resolve_lotto_task_execution_mode(5, 10, 3, "numera_fatture")

        self.assertEqual(result.execution_mode, "SKIP")
        self.assertEqual(result.last_task_stato, "COMPLETATO")
        self.assertEqual(result.last_tentativo, 2)
        self.assertEqual(result.policy_meta, {"key": "val"})
        self.assertEqual(result.run_meta, {"run": True})

    # Scopo: Verifica il caso `test_start_lotto_task_run_returns_task_run_result`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_start_lotto_task_run_returns_task_run_result(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = (999, 1)
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        result = repo.start_lotto_task_run(
            lotto_id=1,
            pipeline_id=100,
            stato_doc_fiscale_id=2,
            task_code="generate_fatture_righe",
            fase="Genera righe",
            meta={"rollback": False},
        )

        self.assertIsInstance(result, TaskRunResult)
        self.assertEqual(result.task_run_id, 999)
        self.assertEqual(result.tentativo, 1)
        execute_sql, execute_params = cursor.execute.call_args.args
        self.assertIn("fn_start_lotto_task_run", execute_sql)
        self.assertEqual(execute_params[0], 1)
        self.assertEqual(execute_params[1], 100)
        self.assertEqual(execute_params[3], "generate_fatture_righe")
        # ⚠️ ARGOMENTI NOMINATI, e il presidio non e' pedanteria: il changeSet
        #    67 ha aggiunto `p_correlation_id` e ha DROPpato la firma a sei,
        #    perche' `CREATE OR REPLACE` con un parametro in PIU' non sostituisce
        #    — affianca, e una chiamata a sei argomenti soddisfa entrambe le
        #    firme («la funzione non e' unica»). Coi nomi, una prossima
        #    revisione non puo' scivolare su un parametro adiacente.
        self.assertIn("p_correlation_id =>", execute_sql)
        # Il settimo posto e' il filo del giro, qui non passato.
        self.assertEqual(len(execute_params), 7)
        self.assertIsNone(execute_params[6])

    # Scopo: Verifica il caso `test_complete_lotto_task_run_calls_sql_function`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_complete_lotto_task_run_calls_sql_function(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        repo.complete_lotto_task_run(999)

        cursor.execute.assert_called_once()
        execute_sql, execute_params = cursor.execute.call_args.args
        self.assertIn("fn_complete_lotto_task_run", execute_sql)
        self.assertEqual(execute_params[0], 999)

    # Scopo: Verifica il caso `test_fail_lotto_task_run_calls_sql_function_with_error_params`.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_fail_lotto_task_run_calls_sql_function_with_error_params(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        repo.fail_lotto_task_run(999, "E_TASK", "Errore task boom")

        cursor.execute.assert_called_once()
        execute_sql, execute_params = cursor.execute.call_args.args
        self.assertIn("fn_fail_lotto_task_run", execute_sql)
        self.assertEqual(execute_params[0], 999)
        self.assertEqual(execute_params[1], "E_TASK")
        self.assertEqual(execute_params[2], "Errore task boom")

    # Scopo: Verifica che set_lotto_job_stato aggiorni solo stato_lotto e meta senza toccare stato_operativo.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_set_lotto_job_stato_updates_only_stato_lotto(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = ("IN_ESECUZIONE",)
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        repo.set_lotto_job_stato(10, "COMPLETATO", "Pipeline completata")

        self.assertEqual(cursor.execute.call_count, 2)
        first_sql, first_params = cursor.execute.call_args_list[0].args
        second_sql, second_params = cursor.execute.call_args_list[1].args
        self.assertIn("SELECT stato_lotto", first_sql)
        self.assertEqual(first_params, [10])
        self.assertIn("UPDATE vendite.fatturazione_lotti", second_sql)
        self.assertIn("SET stato_lotto = %s", second_sql)
        self.assertNotIn("stato_operativo", second_sql)
        self.assertEqual(second_params, ["COMPLETATO", "Pipeline completata", "Pipeline completata", 10])

    # Scopo: ⭐ LA REGOLA DEI PASSAGGI DEL JOB NON STA PIU' NEL BACKEND
    #        (brief-modello-documento-vendita §15.8 punto 2, F-4, 2026-10-27).
    #        Uno stato fuori vocabolario e un passaggio fuori matrice arrivano al
    #        DB senza essere giudicati qui: li rifiutano la FK sul codice e il
    #        guard `trgfn_fatturazione_lotti_guard_stato_job`
    #        (`E_LOTTO_PARAMETRO_NON_COERENTE`). La regola si presidia dove sta:
    #        `db/pgtap/vendite/test-fattura-lotto-al-modello-v1` (5 e 22,
    #        ERRORE -> COMPLETATO rifiutato compreso).
    # ⛔ Se tornasse un controllo qui, il caso sotto non arriverebbe all'UPDATE:
    #    sarebbe la seconda sede della regola, ritirata apposta.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_set_lotto_job_stato_non_giudica_il_passaggio(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = ("ERRORE",)
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        repo.set_lotto_job_stato(10, "COMPLETATO", "scorciatoia")

        self.assertEqual(cursor.execute.call_count, 2)
        update_sql, params = cursor.execute.call_args_list[1].args
        self.assertIn("UPDATE vendite.fatturazione_lotti", update_sql)
        self.assertEqual(params[0], "COMPLETATO")

    # Scopo: ⭐ LO STATO DELLO STEP PASSA DAL VERBO DI PROCESSO DEL DB
    #        (`vendite.fn_lotto_proietta_stato_step`, §15.8 punto 1), mai da un
    #        `UPDATE`: la porta `trgfn_doc_stato_solo_dal_verbo` lo rifiuterebbe,
    #        e il giro della pipeline si fermerebbe al primo step.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_update_lotto_stato_doc_passa_dal_verbo_di_processo(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        mocked_cursor_factory.return_value = cursor

        VenditePipelineRepository().update_lotto_stato_doc(10, 2)

        cursor.execute.assert_called_once()
        sql, params = cursor.execute.call_args.args
        self.assertIn("vendite.fn_lotto_proietta_stato_step(%s, %s)", sql)
        self.assertNotIn("UPDATE", sql)
        self.assertEqual(params, [10, 2])

    # Scopo: ⭐ UN LOTTO COMPLETATO PUO' ESSERE MARCATO IN ERRORE.
    #
    # 🔴 Fino al 2026-08-24 non poteva, e il difetto e' stato visto su un giro
    #    VERO (lotto 6260): rilanciato un lotto gia' COMPLETATO, la pipeline e'
    #    fallita su una nota di credito non numerabile, e la marcatura d'errore
    #    e' stata RIFIUTATA qui. Il lotto e' rimasto COMPLETATO pur avendo una
    #    fattura che non si era numerata — un errore reale che il registro non
    #    poteva dire.
    #
    # ⚠️ Il divieto colpiva SOLO quel caso: l'avvio del giro scrive
    #    `IN_ESECUZIONE` dentro la transazione del giro, quindi un fallimento la
    #    rolla indietro e il marcatore ritrova lo stato precedente. Il lotto era
    #    COMPLETATO non perche' fosse a posto, ma perche' il fallimento aveva
    #    cancellato la prova di essere partito.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_set_lotto_job_stato_completato_puo_andare_in_errore(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = ("COMPLETATO",)
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        repo.set_lotto_job_stato(6260, "ERRORE", "Errore pipeline")

        # Nessun rifiuto: due execute, la lettura e l'UPDATE (non il log errore).
        self.assertEqual(cursor.execute.call_count, 2)
        update_sql, params = cursor.execute.call_args_list[1].args
        self.assertIn("UPDATE vendite.fatturazione_lotti", update_sql)
        self.assertEqual(params[0], "ERRORE")
        self.assertEqual(params[-1], 6260)

    # Scopo: ⭐ IL BERSAGLIO sulla riga di segnalazione, e la mappatura POSIZIONALE
    #        che lo porta. Il repository non fa `SELECT *`: nomina le colonne e
    #        NON prende `id`, quindi la posizione di `target` nella tupla non
    #        coincide con la sua posizione nella funzione DB (li' e' la 16a).
    #        Un off-by-one qui metterebbe `fuori_job_count` dentro `target`: un
    #        numero al posto di un array, che a video diventa **nessun pulsante**
    #        — senza errori e senza avvisi. E' il difetto che questo test esiste
    #        per rendere impossibile.
    #
    # ⛔ E si presidia anche che `target` NON sia `fattura_id`: quello e' il
    #    documento che ha FALLITO, il bersaglio e' dove andare. Sul caso
    #    collaudato sono due fatture diverse (19563 contro 835).
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_list_lotto_segnalazioni_mappa_il_bersaglio(self, mocked_cursor_factory):
        class _DT:
            # Scopo: data/ora finta serializzabile, come negli altri test del file.
            def __init__(self, value: str):
                self._value = value

            def isoformat(self):
                return self._value

        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchall.return_value = [
            (
                "FATTURA:42",                       # 0  riga_key
                "FATTURA",                          # 1  origine
                _DT("2026-08-24T09:36:45+02:00"),   # 2  data_ora
                "C",                                # 3  livello
                "Non si puo' numerare il documento 19563.",  # 4  messaggio
                "E_FATTURA_RETTIFICATA_SENZA_NUMERO",        # 5  error_code
                None,                               # 6  fase
                19563,                              # 7  fattura_id — il FALLITO
                "NC 2/2026",                        # 8  documento_display
                "100.00",                           # 9  importo
                False,                              # 10 disabilitato
                True,                               # 11 job_corrente
                1,                                  # 12 total_count
                0,                                  # 13 fuori_job_count
                # ⚠️ 15a colonna della SELECT: il bersaglio. Come stringa,
                #    perche' da un cursore RAW psycopg NON decodifica i jsonb.
                '[{"id": "835", "type": "FATTURA"}]',        # 14 target
                # ⛔ Sul ramo FATTURA la `gruppo_key` e' NULL per costruzione:
                #    una bozza puo' coprire piu' documenti, quindi una
                #    segnalazione appesa alla fattura non ne nomina uno — e
                #    sceglierne uno sarebbe una scommessa.
                None,                               # 15 gruppo_key
                # ⚠️ Le due colonne del blocco restano NULL sulle righe senza
                #    documento: il `CASE` non chiama nemmeno la check.
                None,                               # 16 uscita_blocco_reason
                None,                               # 17 uscita_blocco_reason_key
                # ⚠️ Senza chiave non c'e' riferimento: e' lo STESSO NULL, non
                #    un'identita' che non si e' risolta.
                None,                               # 18 riferimento
            ),
        ]
        mocked_cursor_factory.return_value = cursor

        righe, total, fuori = VenditePipelineRepository().list_lotto_segnalazioni(
            lotto_id=6260,
        )

        self.assertEqual((total, fuori), (1, 0))
        riga = righe[0]
        self.assertEqual(riga["target"], [{"id": "835", "type": "FATTURA"}])
        # Le due entita' sono diverse, ed e' tutto il punto.
        self.assertEqual(riga["fattura_id"], 19563)
        self.assertNotEqual(str(riga["fattura_id"]), riga["target"][0]["id"])

    # Scopo: ⚠️ Nessun bersaglio = `None`, non `[]`. E' il caso NORMALE (oggi
    #        tutte le righe di origine `LOTTO`), e il degrado a video e'
    #        «nessun pulsante, messaggio invariato».
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_list_lotto_segnalazioni_senza_bersaglio(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchall.return_value = [
            # ⚠️ Riga del GIRO: nessun bersaglio, nessun documento e — di
            #    conseguenza — nessun motivo di blocco, perche' il `CASE` non
            #    chiama nemmeno la check, ne' riferimento leggibile, perche'
            #    senza chiave non c'e' niente da nominare. Le QUATTRO code sono
            #    `None` insieme, e non e' una coincidenza: senza documento il
            #    verbo non ha oggetto e l'etichetta non ha soggetto.
            ("LOTTO:7", "LOTTO", None, "C", "Errore pipeline", "E_PIPELINE",
             "Numerazione", None, None, None, False, True, 1, 0, None,
             None, None, None, None),
        ]
        mocked_cursor_factory.return_value = cursor

        righe, _, _ = VenditePipelineRepository().list_lotto_segnalazioni(lotto_id=6260)
        self.assertIsNone(righe[0]["target"])
        # ⭐ E la riga dichiara di essere del GIRO: `gruppo_key` a `None` NON e'
        #    un buco — e' la meta' sana del vocabolario, ed e' cio' che il
        #    frontend legge per spegnere «togli dal giro» col motivo giusto.
        self.assertIsNone(righe[0]["gruppo_key"])
        self.assertIsNone(righe[0]["uscita_blocco_reason"])
        self.assertIsNone(righe[0]["riferimento"])

    # Scopo: Verifica che list_lotto_task_runs mappi correttamente righe runtime task da DB.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_list_lotto_task_runs_maps_rows(self, mocked_cursor_factory):
        class _DT:
            # Scopo: Simula data/ora DB serializzabile in isoformat per i test repository.
            def __init__(self, value: str):
                self._value = value

            def isoformat(self):
                return self._value

        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchall.return_value = [
            (
                1001,
                80,
                4,
                8,
                "numera_fatture",
                "Numerazione fatture",
                1,
                "COMPLETATO",
                _DT("2026-02-19T10:00:00+01:00"),
                _DT("2026-02-19T10:00:02+01:00"),
                None,
                None,
                '{"rollback": false}',
                # ⚠️ 14a colonna: `giro_corrente`, per riga (`20260824-11`).
                True,
                # ⚠️ 15a colonna: `total_count`, che la funzione DB ripete su
                # OGNI riga. Il repository lo legge dalla prima — senza questa
                # colonna nel finto, il test misurerebbe una forma che la
                # funzione non ha (BE-2, 2026-08-22).
                37,
                # ⚠️ 16a: `esclusi_count`, ripetuto come il totale. Invariante
                # dichiarata dal DB: `total_count + esclusi_count` = le righe
                # che il lotto ha davvero (`20260824-11`).
                12,
            )
        ]
        mocked_cursor_factory.return_value = cursor

        repo = VenditePipelineRepository()
        result, total_count, esclusi_count = repo.list_lotto_task_runs(80, limit=50)

        self.assertEqual(total_count, 37)
        self.assertEqual(esclusi_count, 12)
        self.assertTrue(result[0]["giro_corrente"])
        self.assertEqual(len(result), 1)
        row = result[0]
        self.assertEqual(row["id"], 1001)
        self.assertEqual(row["lotto_id"], 80)
        self.assertEqual(row["pipeline_id"], 4)
        self.assertEqual(row["task_code"], "numera_fatture")
        self.assertEqual(row["task_stato"], "COMPLETATO")
        self.assertEqual(row["meta"], {"rollback": False})
        # ⭐ La SORGENTE e' la funzione DB, non piu' una SELECT nostra: e' il
        # punto di BE-2 (due verita' sullo stesso elenco, e quella a video non
        # era quella dichiarata). Il presidio sta sulla stringa perche' il
        # binding di una funzione i mock non lo vedono.
        execute_sql, execute_params = cursor.execute.call_args.args
        self.assertIn("vendite.fn_list_lotto_task_runs", execute_sql)
        self.assertNotIn("FROM vendite.fatturazione_lotti_task_runs", execute_sql)
        # ⭐ Gli ultimi due sono i filtri del `20260824-11`, e senza argomenti
        # arrivano SPENTI: nessun default nasconde righe.
        # ⚠️ La lista vuota degli stati diventa `None`, non `[]`: «nessuno
        # stato scelto» e «tutti gli stati» sono la stessa domanda, e un array
        # vuoto a DB non lo sarebbe.
        self.assertEqual(execute_params, [80, True, 50, 0, None, "desc", False, None])

    # Scopo: il legame documentale delle note di credito (N10/BE-8) passa da una
    #        sola `SELECT fn_()` per fattura e ritorna quante coppie ha aggiunto.
    #        L'handler di pipeline mocka il repository, quindi questa e' l'unica
    #        rete sulla stringa SQL: senza, il nome della funzione sarebbe
    #        verificato solo dalla whitelist, che e' una stringa a sua volta.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_popola_fatture_rettifiche_chiama_la_fn_e_ritorna_le_coppie(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = (2,)
        mocked_cursor_factory.return_value = cursor

        result = VenditePipelineRepository().popola_fatture_rettifiche(7701)

        self.assertEqual(result, 2)
        execute_sql, execute_params = cursor.execute.call_args.args
        self.assertIn("vendite.fn_popola_fatture_rettifiche", execute_sql)
        self.assertEqual(execute_params, [7701])

    # Scopo: il confine SQL casta l'id; il guard di merito (NULL / <= 0) sta
    #        nella funzione DB e non si ripete qui.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_popola_fatture_rettifiche_casta_id_a_intero(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = (0,)
        mocked_cursor_factory.return_value = cursor

        VenditePipelineRepository().popola_fatture_rettifiche("7701")

        self.assertEqual(cursor.execute.call_args.args[1], [7701])

    # 26) 🔴 IL `jsonb` ARRIVA COME STRINGA, e una stringa e' ITERABILE.
    #
    #     Il difetto, misurato con una chiamata vera il 2026-09-08: senza
    #     decodifica il chiamante riceve `'["ORDINE_VENDITA:01a0…"]'` e il ciclo
    #     «una riga per documento» gira una volta per CARATTERE — cinquantacinque
    #     segnalazioni critiche su un lotto, una per lettera, senza nessun errore.
    #
    # ⛔ E i mock non lo vedono: restituiscono liste. Questo test esiste per
    #    riprodurre la forma che il DRIVER consegna davvero, non quella comoda.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_gruppi_di_commessa_decodifica_il_jsonb_stringa(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = ('["ORDINE_VENDITA:aaa", "ORDINE_VENDITA:bbb"]',)
        mocked_cursor_factory.return_value = cursor

        gruppi = VenditePipelineRepository().gruppi_di_commessa_nel_lotto(1, 2)

        self.assertEqual(gruppi, ["ORDINE_VENDITA:aaa", "ORDINE_VENDITA:bbb"])

    # 27) ⛔ DECODIFICARE NON BASTA: un JSON scalare resta una stringa iterabile
    #     e rifarebbe lo stesso danno. Sulla forma inattesa si ripiega a `[]`, che
    #     il chiamante legge come «nessun proprietario» e traduce in UNA riga
    #     senza `gruppo_key` — cioe' una segnalazione che BLOCCA il giro.
    # ⚠️ E' il verso sicuro, ed e' una scelta: un contratto rotto deve fermare il
    #    lotto, non inventargli documenti.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_gruppi_di_commessa_forma_inattesa_ripiega_a_vuoto(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = ('"ORDINE_VENDITA:aaa"',)
        mocked_cursor_factory.return_value = cursor

        self.assertEqual(VenditePipelineRepository().gruppi_di_commessa_nel_lotto(1, 2), [])

    # 28) ⚠️ PARAMETRI PER NOME, e non e' estetica: `p_gruppo_key` e' l'OTTAVO e
    #     il settimo (`p_error_code`) qui non si passa — posizionalmente non si
    #     puo' saltare un buco. Per nome il default del settimo resta quello che
    #     era, e il comportamento storico non cambia.
    @patch("apps.vendite.db.pipeline_repository.connection.cursor")
    def test_log_pipeline_fase_passa_la_gruppo_key_per_nome(self, mocked_cursor_factory):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        mocked_cursor_factory.return_value = cursor

        VenditePipelineRepository().log_pipeline_fase(
            lotto_id=1, stato_doc_fiscale_id=2, fase="Errore pipeline",
            status="C", messaggio="ko", meta=None, gruppo_key="ORDINE_VENDITA:aaa",
        )

        sql, params = cursor.execute.call_args.args[0], cursor.execute.call_args.args[1]
        self.assertIn("p_gruppo_key           => %s", sql)
        # ⛔ `p_error_code` NON si passa: deve restare al suo default.
        self.assertNotIn("p_error_code", sql)
        self.assertEqual(params[-1], "ORDINE_VENDITA:aaa")
