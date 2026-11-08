# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test di `PipelineStepExecutor` — dispatch task, tracing task_run,
#        esiti parziali (D-Q p.3) e vincoli d'ordine fra task dello step.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) PipelineStepExecutorUnitTests.test_execute_step_runs_generate_fatture_righe_task
2) PipelineStepExecutorUnitTests.test_execute_step_rejects_generate_fatture_righe_fn_override
3) PipelineStepExecutorUnitTests.test_execute_step_runs_genera_fondi_source_lotto_task
4) PipelineStepExecutorUnitTests.test_execute_step_runs_applica_fondi_lotto_task
5) PipelineStepExecutorUnitTests.test_execute_step_runs_ricalcola_iva_lotto_task
6) PipelineStepExecutorUnitTests.test_execute_step_runs_prepare_sdi_payload_lotto_task
7) PipelineStepExecutorUnitTests.test_execute_step_runs_numera_fatture_task
8) PipelineStepExecutorUnitTests.test_execute_step_runs_close_lotto_task
9) PipelineStepExecutorUnitTests.test_execute_step_runs_reset_lotto_draft_task
10) PipelineStepExecutorUnitTests.test_execute_step_numera_logs_fattura_error_on_single_failure
11) PipelineStepExecutorUnitTests.test_execute_step_logs_lotto_error_on_not_allowed_function
12) PipelineStepExecutorUnitTests.test_execute_step_logs_lotto_error_on_missing_handler
13) PipelineStepExecutorUnitTests.test_execute_step_skips_close_lotto_task_when_flag_is_false
14) PipelineStepExecutorUnitTests.test_execute_step_skips_task_when_execution_mode_is_skip
14a) PipelineStepExecutorUnitTests.test_rilancio_riesegue_i_task_a_valle_di_uno_rieseguito (catena, lotto 13338)
14b) PipelineStepExecutorUnitTests.test_skip_resta_valido_se_a_monte_niente_e_stato_eseguito (controprova del 14a)
15) PipelineStepExecutorUnitTests.test_execute_step_raises_when_execution_mode_is_reset_required
16) PipelineStepExecutorUnitTests.test_execute_step_traces_task_run_on_success
17) PipelineStepExecutorUnitTests.test_execute_step_traces_fail_on_handler_error
18) PipelineStepExecutorUnitTests.test_execute_step_no_tracing_when_no_pipeline_id
19) PipelineStepExecutorUnitTests.test_execute_step_no_tracing_when_no_policy
20) PipelineStepExecutorUnitTests.test_execute_step_select_attivita_uses_emittente_from_context
21) PipelineStepExecutorUnitTests.test_execute_step_runs_pull_attivita_da_commessa_task
22) PipelineStepExecutorUnitTests.test_pull_attivita_da_commessa_dry_run_skips_emit
23) PipelineStepExecutorUnitTests.test_pull_attivita_da_commessa_empty_list_no_emit
23a) PipelineStepExecutorUnitTests.test_pull_attivita_da_commessa_parziale_chiude_task_run_errore (D-Q p.3)
23b) PipelineStepExecutorUnitTests.test_pull_attivita_da_commessa_tutte_ok_completa_task_run
23c) PipelineStepExecutorUnitTests.test_pull_attivita_da_commessa_tutte_fallite_solleva
23d) PipelineStepExecutorUnitTests.test_pull_attivita_da_commessa_dry_run_non_produce_parziale
23e) PipelineStepExecutorUnitTests.test_pull_consegna_al_db_l_identita_del_giro (D1: discovery E emit)
23f) PipelineStepExecutorUnitTests.test_pull_si_ferma_se_il_giro_non_ha_identita (il guard precede la discovery)
23g) PipelineStepExecutorUnitTests.test_pull_dry_run_senza_identita_si_ferma_lo_stesso
24) PipelineStepExecutorUnitTests.test_execute_step_runs_stampa_documenti_lotto_task (C-2c)
25) PipelineStepExecutorUnitTests.test_execute_step_stampa_documenti_lotto_dry_run_skips (C-2c)
26) PipelineStepExecutorUnitTests.test_execute_step_runs_snapshot_indirizzi_lotto_task (Fase 2 satelliti)
27) PipelineStepExecutorUnitTests.test_execute_step_snapshot_indirizzi_dry_run_skips
28) PipelineStepExecutorUnitTests.test_execute_step_snapshot_indirizzi_failed_rows_chiude_task_run_errore (D-Q p.3)
29) PipelineStepExecutorUnitTests.test_execute_step_snapshot_indirizzi_senza_falliti_completa_task_run
30) PipelineStepExecutorUnitTests.test_execute_step_runs_genera_scadenze_lotto_task (Fase 4 satelliti)
31) PipelineStepExecutorUnitTests.test_execute_step_genera_scadenze_dry_run_skips
32) PipelineStepExecutorUnitTests.test_execute_step_genera_scadenze_failed_rows_chiude_task_run_errore (D-Q p.3)
33) PipelineStepExecutorUnitTests.test_execute_step_genera_scadenze_senza_falliti_completa_task_run
34) PipelineStepExecutorUnitTests.test_execute_step_genera_scadenze_dopo_ricalcola_iva_ok (ordine)
35) PipelineStepExecutorUnitTests.test_execute_step_genera_scadenze_prima_di_ricalcola_iva_rifiutato (ordine)
36) PipelineStepExecutorUnitTests.test_execute_step_genera_scadenze_senza_ricalcola_iva_nello_step_ammesso (ordine)
37) PipelineStepExecutorUnitTests.test_execute_step_ordine_non_verificato_in_rollback (ordine)
38) PipelineStepExecutorUnitTests.test_execute_step_runs_popola_fatture_rettifiche_task (N10/BE-8)
39) PipelineStepExecutorUnitTests.test_popola_fatture_rettifiche_dry_run_skips
40) PipelineStepExecutorUnitTests.test_popola_fatture_rettifiche_fail_fast_su_singola_fattura
41) PipelineStepExecutorUnitTests.test_popola_fatture_rettifiche_dopo_numera_ok (ordine)
42) PipelineStepExecutorUnitTests.test_popola_fatture_rettifiche_prima_di_numera_rifiutato (ordine)
43) PipelineStepExecutorUnitTests.test_popola_fatture_rettifiche_agganciata_al_registry_reale
44) PipelineStepExecutorUnitTests.test_pull_una_segnalazione_per_documento (§6.1)
45) PipelineStepExecutorUnitTests.test_pull_senza_proprietario_scrive_una_riga_del_giro (§6.1)
46) PipelineStepExecutorUnitTests.test_pull_ogni_segnalazione_dichiara_la_commessa (V-7-bis)
"""

from contextlib import nullcontext
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.tests.db_error_fakes import make_db_error
from apps.core.services.service_errors import ServiceError
from apps.vendite.services.pipeline_step_executor import PipelineStepExecutor

# Identita' del giro di fatturazione usata dai test del pull: e' il valore che
# `fn_select_attivita_fatturabili` cerchera' poi come marchio sulle righe.
_LOCK_BATCH_GIRO = "01a06d0c-e9e1-72a1-a4d1-54020186de27"


class PipelineStepExecutorUnitTests(SimpleTestCase):
    # Scopo: ⚠️ `transaction.atomic` NEUTRALIZZATO per tutta la classe.
    #        `_run_per_fattura_task` apre un SAVEPOINT per fattura (vedi il suo
    #        commento: senza, l'errore della madre DB abortisce la transazione e
    #        distrugge il proprio messaggio). Qui il repository e' un mock e non
    #        c'e' database: un `SAVEPOINT` vero e' una query, e `SimpleTestCase`
    #        le vieta — vincolo CI, gli stessi test girano dove il DB non c'e'.
    #        Convenzione gia' in uso nel repo (`_atomic_noop` di
    #        `test_commesse_source_handlers`), qui alzata a livello di classe
    #        perche' il savepoint sta in un helper che quasi ogni test attraversa.
    #        ⭐ Che il savepoint ci SIA e' presidiato a parte, da
    #        `test_ogni_fattura_gira_nel_suo_savepoint`: neutralizzarlo ovunque
    #        senza un test che lo pretende sarebbe il modo di perderlo al primo
    #        refactor.
    def setUp(self):
        super().setUp()
        patcher = patch(
            "apps.vendite.services.pipeline_step_executor.transaction.atomic",
            new=lambda *a, **k: nullcontext(),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    # Scopo: Gestisce `_build_executor` nel flusso applicativo del modulo.
    def _build_executor(self, processi):
        repo = MagicMock()
        repo.get_lotto_context.return_value = MagicMock(
            competenza_mese="2026-01-01",
            utility_id=None,
            tipo_doc_fiscale_id=None,
            emittente_soggetto_ruolo_id=None,
        )
        repo.get_step_processes.return_value = processi
        repo.log_pipeline_fase.return_value = None
        repo.list_fatture_by_lotto.return_value = [101, 102]
        repo.get_task_handler_code.return_value = "generate_fatture_righe_default"
        repo.is_stato_doc_chiude_lotto.return_value = True
        repo.ALLOWED_TASK_FUNCTIONS = {
            "select_attivita": "vendite.fn_select_attivita_fatturabili",
            # Speculare alla mappa reale: None = task Python-only
            # (`FattureRigheService`), la fn SQL e' stata rimossa (20260728-21).
            "generate_fatture_righe": None,
            # R-3: i due giri passano dalle MADRI per lotto, non piu' dalle
            # funzioni per-scope (che restano, chiamate dalle madri).
            "genera_fondi_source_lotto": "vendite.fn_genera_fondi_fattura_lotto",
            "applica_fondi_lotto": "vendite.fn_applica_fondi_lotto",
            "ricalcola_iva_lotto": "vendite.fn_ricalcola_riepiloghi_iva_lotto",
            "prepare_sdi_payload_lotto": "vendite.fn_prepare_sdi_payload",
            "numera_fatture": "vendite.fn_numera_fattura_opz_emessa",
            "close_lotto": None,
            "reset_lotto_draft": "vendite.fn_annulla_lotto_da_draft",
            "snapshot_indirizzi_lotto": "vendite.fn_snapshot_fattura_lotto",
            "genera_scadenze_lotto": "vendite.fn_genera_scadenze_lotto",
            "popola_fatture_rettifiche": "vendite.fn_popola_fatture_rettifiche",
        }
        # Tracing: default nessuna policy → nessun tracing (test esistenti non cambiano).
        repo.get_pipeline_id_for_step.return_value = 100
        repo.task_policy_exists.return_value = False
        exec_mode_mock = MagicMock()
        exec_mode_mock.execution_mode = "RUN"
        exec_mode_mock.last_task_stato = None
        exec_mode_mock.last_tentativo = None
        repo.resolve_lotto_task_execution_mode.return_value = exec_mode_mock
        task_run_mock = MagicMock()
        task_run_mock.task_run_id = 999
        task_run_mock.tentativo = 1
        repo.start_lotto_task_run.return_value = task_run_mock
        repo.complete_lotto_task_run.return_value = None
        repo.fail_lotto_task_run.return_value = None
        fatture_righe_service = MagicMock()
        error_logger = MagicMock()
        executor = PipelineStepExecutor(
            repository=repo,
            fatture_righe_service=fatture_righe_service,
            error_logger=error_logger,
        )
        return executor, repo, fatture_righe_service, error_logger

    # Scopo: Verifica il caso `test_execute_step_runs_generate_fatture_righe_task`.
    def test_execute_step_runs_generate_fatture_righe_task(self):
        processi = [{"task": "generate_fatture_righe", "fase": "Genera righe", "params": {}}]
        executor, repo, fatture_righe_service, _ = self._build_executor(processi)
        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )
        repo.get_step_processes.assert_called_once_with(
            2,
            tipo_lotto="MASSIVO",
            utility_id=None,
            tipo_doc_fiscale_id=None,
            rollback=False,
        )
        repo.get_task_handler_code.assert_called_once_with(
            task_code="generate_fatture_righe",
            implementation_key=None,
        )
        fatture_righe_service.generate_fatture_righe.assert_called_once_with(1, dry_run=False)

    # Scopo: Verifica il caso `test_execute_step_runs_genera_fondi_source_lotto_task`.
    def test_execute_step_runs_genera_fondi_source_lotto_task(self):
        processi = [{"task": "genera_fondi_source_lotto", "fase": "Genera fondi", "params": {}}]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "genera_fondi_source_lotto_default"

        executor.execute_step(
            lotto_id=11,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.run_genera_fondi_source_lotto_task.assert_called_once_with(
            lotto_id=11,
            tipo_fondo_codice_interno="F_F_ADD_ACC",
        )

    # Scopo: Verifica il caso `test_execute_step_runs_applica_fondi_lotto_task`.
    def test_execute_step_runs_applica_fondi_lotto_task(self):
        processi = [{"task": "applica_fondi_lotto", "fase": "Applica fondi", "params": {}}]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "applica_fondi_lotto_default"

        executor.execute_step(
            lotto_id=11,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.run_applica_fondi_lotto_task.assert_called_once_with(
            lotto_id=11,
            tipo_fondo_codice_interno="F_F_ADD_ACC",
        )

    # Scopo: Verifica il caso `test_execute_step_runs_ricalcola_iva_lotto_task`.
    def test_execute_step_runs_ricalcola_iva_lotto_task(self):
        processi = [{"task": "ricalcola_iva_lotto", "fase": "Ricalcolo IVA", "params": {"batch_size": 500}}]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "ricalcola_iva_lotto_default"

        executor.execute_step(
            lotto_id=11,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.run_ricalcola_iva_lotto_task.assert_called_once_with(
            lotto_id=11,
            batch_size=500,
        )

    # Scopo: Verifica il caso `test_execute_step_runs_prepare_sdi_payload_lotto_task`.
    def test_execute_step_runs_prepare_sdi_payload_lotto_task(self):
        processi = [
            {
                "task": "prepare_sdi_payload_lotto",
                "fase": "Preparazione payload SDI",
                "params": {
                    "stato_sdi_codice_interno": "DA_INVIARE",
                    "force_new_tentativo": False,
                },
            }
        ]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "prepare_sdi_payload_lotto_default"

        executor.execute_step(
            lotto_id=11,
            stato_doc_fiscale_id=3,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.run_prepare_sdi_payload_lotto_task.assert_called_once_with(
            lotto_id=11,
            stato_sdi_codice_interno="DA_INVIARE",
            force_new_tentativo=False,
        )

    # Scopo: Verifica il caso `test_execute_step_rejects_generate_fatture_righe_fn_override`.
    def test_execute_step_rejects_generate_fatture_righe_fn_override(self):
        processi = [
            {
                "task": "generate_fatture_righe",
                "fase": "Genera righe",
                "params": {"fn": "vendite.fn_non_permessa"},
            }
        ]
        executor, repo, fatture_righe_service, error_logger = self._build_executor(processi)
        with self.assertRaises(ServiceError) as exc:
            executor.execute_step(
                lotto_id=1,
                stato_doc_fiscale_id=2,
                tipo_lotto="MASSIVO",
                rollback=False,
                dry_run=False,
            )
        self.assertEqual(exc.exception.code, "E_TASK_NOT_ALLOWED")
        self.assertEqual(repo.get_task_handler_code.call_count, 1)
        fatture_righe_service.generate_fatture_righe.assert_not_called()
        error_logger.log_error.assert_called_once()
        kwargs = error_logger.log_error.call_args.kwargs
        self.assertEqual(kwargs["scope"], "LOTTO")
        self.assertEqual(kwargs["lotto_id"], 1)

    # Scopo: Verifica il caso `test_execute_step_runs_numera_fatture_task`.
    def test_execute_step_runs_numera_fatture_task(self):
        processi = [{"task": "numera_fatture", "fase": "Numerazione", "params": {}}]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "numera_fatture_default"

        executor.execute_step(
            lotto_id=9,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.list_fatture_by_lotto.assert_called_once_with(9)
        repo.numera_fattura_opz_emessa.assert_any_call(101)
        repo.numera_fattura_opz_emessa.assert_any_call(102)
        # Il task numera NON sincronizza piu' lo stato documentale: l'allineamento allo
        # stato dello step (→ DEFINITIVA/8) e' centralizzato nel runner (_execute_pipeline_step).
        repo.sync_lotto_fatture_stato.assert_not_called()

    # Scopo: ⭐ L'ORDINE DI NUMERAZIONE, che dal 2026-08-21 e' un requisito e non
    #        una comodita' (brief note credito §44.2). La madre DB rifiuta di
    #        numerare una nota di credito la cui fattura rettificata non ha
    #        ancora un numero, e il giro e' FAIL-FAST: una nota incontrata prima
    #        della sua fattura fermerebbe l'intero step.
    #
    #        ⚠️ Il repository e' un MagicMock e restituisce quello che gli si
    #        dice: qui restituisce gli id MESCOLATI apposta, cosi' il test
    #        misura il riordino del PASSO e non l'`ORDER BY` della query — che
    #        e' esattamente la ragione per cui il `sorted` sta li' invece di
    #        appoggiarsi al repository.
    def test_numera_fatture_numera_in_ordine_di_id_anche_se_il_repo_non_ordina(self):
        processi = [{"task": "numera_fatture", "fase": "Numerazione", "params": {}}]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "numera_fatture_default"
        # 903 = la nota di credito, 811 = la fattura che rettifica.
        repo.list_fatture_by_lotto.return_value = [903, 811, 850]

        executor.execute_step(
            lotto_id=9,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        ordine = [c.args[0] for c in repo.numera_fattura_opz_emessa.call_args_list]
        self.assertEqual(ordine, [811, 850, 903])

    # Scopo: C-2c (outbox stampa) — il task stampa_documenti_lotto ACCODA via
    #        fn_accoda_stampe_lotto e non tocca altro (nessun render qui).
    def test_execute_step_runs_stampa_documenti_lotto_task(self):
        processi = [{"task": "stampa_documenti_lotto", "fase": "Stampa documenti lotto", "params": {"implementation_key": "default"}}]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "stampa_documenti_lotto_default"
        repo.accoda_stampe_lotto.return_value = 3

        executor.execute_step(
            lotto_id=9,
            stato_doc_fiscale_id=8,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.accoda_stampe_lotto.assert_called_once_with(9)
        # Adattatore stupido: niente render, niente numerazione qui.
        repo.numera_fattura_opz_emessa.assert_not_called()

    # Scopo: C-2c — in dry-run l'accodamento NON viene eseguito.
    def test_execute_step_stampa_documenti_lotto_dry_run_skips(self):
        processi = [{"task": "stampa_documenti_lotto", "fase": "Stampa documenti lotto", "params": {}}]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "stampa_documenti_lotto_default"

        executor.execute_step(
            lotto_id=9,
            stato_doc_fiscale_id=8,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=True,
        )

        repo.accoda_stampe_lotto.assert_not_called()

    # Scopo: Verifica il caso `test_execute_step_runs_close_lotto_task`.
    def test_execute_step_runs_close_lotto_task(self):
        processi = [{"task": "close_lotto", "fase": "Chiusura lotto", "params": {}}]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "close_lotto_default"

        executor.execute_step(
            lotto_id=5,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.close_lotto_operativo.assert_called_once_with(5)

    # Scopo: Verifica il caso `test_execute_step_skips_close_lotto_task_when_flag_is_false`.
    def test_execute_step_skips_close_lotto_task_when_flag_is_false(self):
        processi = [{"task": "close_lotto", "fase": "Chiusura lotto", "params": {}}]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "close_lotto_default"
        repo.is_stato_doc_chiude_lotto.return_value = False

        executor.execute_step(
            lotto_id=5,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.close_lotto_operativo.assert_not_called()

    # Scopo: Verifica il caso `test_execute_step_runs_reset_lotto_draft_task`.
    def test_execute_step_runs_reset_lotto_draft_task(self):
        processi = [{"task": "reset_lotto_draft", "fase": "Reset lotto", "params": {}}]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "reset_lotto_draft_default"

        executor.execute_step(
            lotto_id=12,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=True,
            dry_run=False,
        )

        repo.annulla_lotto_da_draft.assert_called_once_with(12)

    # Scopo: Verifica il caso `test_execute_step_numera_logs_fattura_error_on_single_failure`.
    def test_execute_step_numera_logs_fattura_error_on_single_failure(self):
        processi = [{"task": "numera_fatture", "fase": "Numerazione", "params": {}}]
        executor, repo, _, error_logger = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "numera_fatture_default"
        repo.list_fatture_by_lotto.return_value = [101, 102]
        repo.numera_fattura_opz_emessa.side_effect = [None, RuntimeError("boom-numera")]

        with self.assertRaises(ServiceError) as exc:
            executor.execute_step(
                lotto_id=9,
                stato_doc_fiscale_id=2,
                tipo_lotto="MASSIVO",
                rollback=False,
                dry_run=False,
            )

        self.assertEqual(exc.exception.code, "E_TASK_FATTURA")
        error_logger.log_error.assert_called_once()
        kwargs = error_logger.log_error.call_args.kwargs
        self.assertEqual(kwargs["scope"], "FATTURA")
        self.assertEqual(kwargs["fattura_id"], 102)
        self.assertEqual(kwargs["lotto_id"], 9)

    # Scopo: 🔴 OGNI FATTURA GIRA NEL SUO SAVEPOINT — il presidio del difetto
    #        misurato in-app il 2026-08-21 (collaudo nota di credito).
    #
    #        Quando una madre DB solleva, la transazione PostgreSQL entra in
    #        stato ABORTITO e ogni istruzione successiva risponde «la
    #        transazione corrente e' interrotta». Le due scritture del percorso
    #        d'errore — il log di scope FATTURA e il diario — sono istruzioni
    #        SQL: fallivano, e il loro fallimento SOSTITUIVA l'errore di
    #        dominio. All'operatore arrivava `E_PIPELINE`, «Errore nella
    #        pipeline di fatturazione», mentre il DB aveva scritto «numera prima
    #        la fattura 835».
    #
    #        ⚠️ Il test guarda la FORMA (un `atomic()` per fattura) e non
    #        l'effetto, perche' l'effetto e' un comportamento di PostgreSQL che
    #        senza database non si puo' riprodurre. E' il motivo per cui il
    #        `setUp` di questa classe neutralizza `atomic`: qui invece si
    #        conta, ed e' l'unico posto dove il savepoint esiste per i test.
    def test_ogni_fattura_gira_nel_suo_savepoint(self):
        processi = [{"task": "numera_fatture", "fase": "Numerazione", "params": {}}]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "numera_fatture_default"
        repo.list_fatture_by_lotto.return_value = [101, 102, 103]

        aperti = []
        repo.numera_fattura_opz_emessa.side_effect = lambda fid: aperti.append(("numera", fid))

        def _atomic_contato(*_a, **_k):
            aperti.append(("savepoint", None))
            return nullcontext()

        with patch(
            "apps.vendite.services.pipeline_step_executor.transaction.atomic",
            new=_atomic_contato,
        ):
            executor.execute_step(
                lotto_id=9,
                stato_doc_fiscale_id=2,
                tipo_lotto="MASSIVO",
                rollback=False,
                dry_run=False,
            )

        # Un savepoint PRIMA di ogni numerazione, non uno solo per tutto il giro:
        # con un savepoint unico la prima fattura caduta porterebbe con se' la
        # leggibilita' di tutte le altre.
        self.assertEqual(
            aperti,
            [
                ("savepoint", None), ("numera", 101),
                ("savepoint", None), ("numera", 102),
                ("savepoint", None), ("numera", 103),
            ],
        )

    # Scopo: 🔴 IL CODICE DEL DATABASE ARRIVA INTATTO ALL'OPERATORE. Il giro
    #        per-fattura appiattiva ogni `DatabaseError` su `E_TASK_FATTURA`
    #        («Errore su singola fattura durante task pipeline»), cioe' buttava
    #        via proprio la frase che dice cosa fare. Misurato il 2026-08-21
    #        sulla guardia nuova della numerazione delle note di credito.
    #
    #        ⚠️ Il finto ha la forma VERA (`db_error_fakes`): campo strutturato
    #        `CONSTRAINT` su SQLSTATE P0001. Un `DatabaseError` nudo passerebbe
    #        dal ripiego testuale ed esercirebbe un percorso diverso da quello
    #        del sistema.
    def test_task_per_fattura_conserva_il_codice_di_dominio_del_database(self):
        processi = [{"task": "numera_fatture", "fase": "Numerazione", "params": {}}]
        executor, repo, _, error_logger = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "numera_fatture_default"
        repo.list_fatture_by_lotto.return_value = [101]
        repo.numera_fattura_opz_emessa.side_effect = make_db_error(
            "Non si puo' numerare il documento: rettifica righe di altri "
            "documenti che non risultano ancora numerati. Documenti da "
            "numerare prima: 1.",
            codice="E_FATTURA_RETTIFICATA_SENZA_NUMERO",
        )

        with self.assertRaises(ServiceError) as exc:
            executor.execute_step(
                lotto_id=9,
                stato_doc_fiscale_id=2,
                tipo_lotto="MASSIVO",
                rollback=False,
                dry_run=False,
            )

        self.assertEqual(exc.exception.code, "E_FATTURA_RETTIFICATA_SENZA_NUMERO")
        # Il messaggio e' quello del RAISE, non il generico del giro per-fattura.
        # ⚠️ Dal `T-3b` (2026-08-24) quella frase NON porta piu' nessun id: porta
        #    il conteggio dei bloccanti, e QUALE documento aprire lo dice il
        #    bersaglio (`test_bersaglio_pipeline`). Qui si prova che la frase del
        #    database arriva intatta, che e' la cosa che il giro appiattiva.
        self.assertIn("Documenti da numerare prima", exc.exception.message)
        # E lo stesso codice nel log di scope FATTURA, non il generico.
        self.assertEqual(
            error_logger.log_error.call_args.kwargs["code"],
            "E_FATTURA_RETTIFICATA_SENZA_NUMERO",
        )

    # Scopo: Verifica il caso `test_execute_step_logs_lotto_error_on_not_allowed_function`.
    def test_execute_step_logs_lotto_error_on_not_allowed_function(self):
        processi = [
            {
                "task": "select_attivita",
                "fase": "Caricamento",
                "params": {"fn": "vendite.fn_non_permessa"},
            }
        ]
        executor, _, _, error_logger = self._build_executor(processi)
        with self.assertRaises(ServiceError) as exc:
            executor.execute_step(
                lotto_id=21,
                stato_doc_fiscale_id=1,
                tipo_lotto="MASSIVO",
                rollback=False,
                dry_run=False,
            )
        self.assertEqual(exc.exception.code, "E_TASK_NOT_ALLOWED")
        error_logger.log_error.assert_called_once()
        kwargs = error_logger.log_error.call_args.kwargs
        self.assertEqual(kwargs["scope"], "LOTTO")
        self.assertEqual(kwargs["lotto_id"], 21)

    # Scopo: Verifica il caso `test_execute_step_logs_lotto_error_on_missing_handler`.
    def test_execute_step_logs_lotto_error_on_missing_handler(self):
        processi = [{"task": "generate_fatture_righe", "fase": "Genera righe", "params": {}}]
        executor, repo, _, error_logger = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "handler_non_esistente"

        with self.assertRaises(ServiceError) as exc:
            executor.execute_step(
                lotto_id=22,
                stato_doc_fiscale_id=2,
                tipo_lotto="MASSIVO",
                rollback=False,
                dry_run=False,
            )

        self.assertEqual(exc.exception.code, "E_TASK_IMPLEMENTATION_NOT_FOUND")
        error_logger.log_error.assert_called_once()
        kwargs = error_logger.log_error.call_args.kwargs
        self.assertEqual(kwargs["scope"], "LOTTO")
        self.assertEqual(kwargs["lotto_id"], 22)

    # Scopo: Verifica che il task venga saltato quando la modalità di esecuzione è SKIP.
    def test_execute_step_skips_task_when_execution_mode_is_skip(self):
        processi = [{"task": "generate_fatture_righe", "fase": "Genera righe", "params": {}}]
        executor, repo, fatture_righe_service, _ = self._build_executor(processi)
        repo.task_policy_exists.return_value = True
        skip_mode = MagicMock()
        skip_mode.execution_mode = "SKIP"
        repo.resolve_lotto_task_execution_mode.return_value = skip_mode

        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.start_lotto_task_run.assert_not_called()
        fatture_righe_service.generate_fatture_righe.assert_not_called()

    # Scopo: 🔴 I TASK DI UNO STEP SONO UNA CATENA (2026-09-12, LTF-0010973): il
    #        resolver dice SKIP a un task perche' la sua ultima corsa e'
    #        COMPLETATO, ma se un task A MONTE e' stato rieseguito in QUESTO
    #        giro quel COMPLETATO e' stantio — era girato a vuoto su un input
    #        che ora e' cambiato. Nel caso vero il pull ha ripreso due commesse
    #        e `select_attivita`/`generate_fatture_righe`/`snapshot` sono stati
    #        saltati: le attivita' emesse non sono diventate fatture e il lotto
    #        e' uscito COMPLETATO con zero documenti.
    # ⭐ Si asserisce che il task a valle sia ESEGUITO (handler chiamato) e che
    #        abbia un task_run suo (nuovo tentativo), non che il resolver sia
    #        stato ignorato: la regola vive nell'orchestratore, il resolver
    #        continua a rispondere per task.
    @patch("apps.core.services.fan_out.transaction")
    def test_rilancio_riesegue_i_task_a_valle_di_uno_rieseguito(self, _mock_txn):
        processi = [
            {"task": "pull_attivita_da_commessa", "fase": "Pull commesse", "params": {}},
            {"task": "select_attivita", "fase": "Seleziona attivita", "params": {}},
        ]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.side_effect = lambda task_code, implementation_key: f"{task_code}_default"
        repo.ALLOWED_TASK_FUNCTIONS["pull_attivita_da_commessa"] = (
            "vendite.fn_emit_attivita_fatturabili_da_commessa"
        )
        repo.task_policy_exists.return_value = True
        repo.get_lotto_context.return_value.lock_batch_id = _LOCK_BATCH_GIRO
        repo.gruppi_di_commessa_nel_lotto.side_effect = (
            lambda lotto_id, commessa_id: [f"COMMESSA:{commessa_id}"]
        )
        commesse_repo = MagicMock()
        commesse_repo.list_commesse_emittibili.return_value = [10]
        executor.commesse_repository = commesse_repo
        task_run = MagicMock()
        task_run.task_run_id = 900
        repo.start_lotto_task_run.return_value = task_run

        # Il resolver: il pull RIPARTE (ultima corsa in ERRORE), il select
        # sarebbe da SALTARE (ultima corsa COMPLETATO — a vuoto).
        def _modo(lotto_id, pipeline_id, stato_doc_fiscale_id, task_code):
            m = MagicMock()
            m.execution_mode = "RESUME" if task_code == "pull_attivita_da_commessa" else "SKIP"
            return m
        repo.resolve_lotto_task_execution_mode.side_effect = _modo

        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        commesse_repo.emit_attivita_fatturabili.assert_called_once()
        # ⭐ Il task a valle e' stato eseguito nonostante lo SKIP del resolver...
        repo.run_select_attivita_task.assert_called_once()
        # ...con un task_run suo: DUE aperture, una per task.
        self.assertEqual(repo.start_lotto_task_run.call_count, 2)
        task_codes = [c.kwargs["task_code"] for c in repo.start_lotto_task_run.call_args_list]
        self.assertEqual(task_codes, ["pull_attivita_da_commessa", "select_attivita"])

    # Scopo: la controprova — se a monte NIENTE e' stato eseguito, lo SKIP del
    #        resolver resta valido: nessun task_run, nessun handler. Senza
    #        questo test la regola potrebbe degenerare in «non saltare mai».
    def test_skip_resta_valido_se_a_monte_niente_e_stato_eseguito(self):
        processi = [
            {"task": "pull_attivita_da_commessa", "fase": "Pull commesse", "params": {}},
            {"task": "select_attivita", "fase": "Seleziona attivita", "params": {}},
        ]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.side_effect = lambda task_code, implementation_key: f"{task_code}_default"
        repo.task_policy_exists.return_value = True
        commesse_repo = MagicMock()
        executor.commesse_repository = commesse_repo
        skip_mode = MagicMock()
        skip_mode.execution_mode = "SKIP"
        repo.resolve_lotto_task_execution_mode.return_value = skip_mode

        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.start_lotto_task_run.assert_not_called()
        commesse_repo.list_commesse_emittibili.assert_not_called()
        repo.run_select_attivita_task.assert_not_called()

    # Scopo: Verifica che venga sollevato ServiceError quando la modalità è RESET_REQUIRED.
    def test_execute_step_raises_when_execution_mode_is_reset_required(self):
        processi = [{"task": "generate_fatture_righe", "fase": "Genera righe", "params": {}}]
        executor, repo, fatture_righe_service, error_logger = self._build_executor(processi)
        repo.task_policy_exists.return_value = True
        reset_mode = MagicMock()
        reset_mode.execution_mode = "RESET_REQUIRED"
        reset_mode.last_task_stato = "IN_ESECUZIONE"
        reset_mode.last_tentativo = 1
        repo.resolve_lotto_task_execution_mode.return_value = reset_mode

        with self.assertRaises(ServiceError) as exc:
            executor.execute_step(
                lotto_id=1,
                stato_doc_fiscale_id=2,
                tipo_lotto="MASSIVO",
                rollback=False,
                dry_run=False,
            )

        self.assertEqual(exc.exception.code, "E_TASK_RESET_REQUIRED")
        repo.start_lotto_task_run.assert_not_called()
        fatture_righe_service.generate_fatture_righe.assert_not_called()
        error_logger.log_error.assert_called_once()
        kwargs = error_logger.log_error.call_args.kwargs
        self.assertEqual(kwargs["scope"], "LOTTO")
        self.assertEqual(kwargs["lotto_id"], 1)

    # Scopo: Verifica che start e complete task run vengano chiamati su esecuzione riuscita.
    def test_execute_step_traces_task_run_on_success(self):
        processi = [{"task": "generate_fatture_righe", "fase": "Genera righe", "params": {}}]
        executor, repo, _, _ = self._build_executor(processi)
        repo.task_policy_exists.return_value = True
        run_mode = MagicMock()
        run_mode.execution_mode = "RUN"
        repo.resolve_lotto_task_execution_mode.return_value = run_mode
        task_run = MagicMock()
        task_run.task_run_id = 888
        repo.start_lotto_task_run.return_value = task_run

        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.start_lotto_task_run.assert_called_once()
        call_kwargs = repo.start_lotto_task_run.call_args.kwargs
        self.assertEqual(call_kwargs["lotto_id"], 1)
        self.assertEqual(call_kwargs["pipeline_id"], 100)
        self.assertEqual(call_kwargs["task_code"], "generate_fatture_righe")
        repo.complete_lotto_task_run.assert_called_once_with(888)
        repo.fail_lotto_task_run.assert_not_called()

    # Scopo: Verifica che fail task run venga chiamato e l'eccezione propagata quando l'handler fallisce.
    def test_execute_step_traces_fail_on_handler_error(self):
        processi = [{"task": "generate_fatture_righe", "fase": "Genera righe", "params": {}}]
        executor, repo, fatture_righe_service, _ = self._build_executor(processi)
        repo.task_policy_exists.return_value = True
        run_mode = MagicMock()
        run_mode.execution_mode = "RUN"
        repo.resolve_lotto_task_execution_mode.return_value = run_mode
        task_run = MagicMock()
        task_run.task_run_id = 777
        repo.start_lotto_task_run.return_value = task_run
        fatture_righe_service.generate_fatture_righe.side_effect = RuntimeError("boom-task")

        with self.assertRaises(RuntimeError):
            executor.execute_step(
                lotto_id=1,
                stato_doc_fiscale_id=2,
                tipo_lotto="MASSIVO",
                rollback=False,
                dry_run=False,
            )

        repo.start_lotto_task_run.assert_called_once()
        repo.fail_lotto_task_run.assert_called_once()
        fail_args = repo.fail_lotto_task_run.call_args.args
        self.assertEqual(fail_args[0], 777)
        repo.complete_lotto_task_run.assert_not_called()

    # Scopo: Verifica che il tracing venga saltato quando pipeline_id è None.
    def test_execute_step_no_tracing_when_no_pipeline_id(self):
        processi = [{"task": "generate_fatture_righe", "fase": "Genera righe", "params": {}}]
        executor, repo, fatture_righe_service, _ = self._build_executor(processi)
        repo.get_pipeline_id_for_step.return_value = None

        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.task_policy_exists.assert_not_called()
        repo.start_lotto_task_run.assert_not_called()
        repo.complete_lotto_task_run.assert_not_called()
        fatture_righe_service.generate_fatture_righe.assert_called_once()

    # Scopo: Verifica che il tracing venga saltato quando non esiste policy per il task.
    def test_execute_step_no_tracing_when_no_policy(self):
        processi = [{"task": "generate_fatture_righe", "fase": "Genera righe", "params": {}}]
        executor, repo, fatture_righe_service, _ = self._build_executor(processi)
        repo.task_policy_exists.return_value = False

        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.task_policy_exists.assert_called_once_with(100, "generate_fatture_righe")
        repo.start_lotto_task_run.assert_not_called()
        repo.complete_lotto_task_run.assert_not_called()
        fatture_righe_service.generate_fatture_righe.assert_called_once()

    # Scopo: Verifica che select_attivita usi emittente_soggetto_ruolo_id dal context (lotto), non dai params.
    def test_execute_step_select_attivita_uses_emittente_from_context(self):
        processi = [
            {
                "task": "select_attivita",
                "fase": "Selezione attivita",
                "params": {"emittente_soggetto_ruolo_id": 99},
            }
        ]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "select_attivita_default"
        repo.get_lotto_context.return_value = MagicMock(
            competenza_mese="2026-01-01",
            utility_id=None,
            tipo_doc_fiscale_id=None,
            emittente_soggetto_ruolo_id=42,
        )

        executor.execute_step(
            lotto_id=7,
            stato_doc_fiscale_id=1,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.run_select_attivita_task.assert_called_once()
        call_kwargs = repo.run_select_attivita_task.call_args.kwargs
        self.assertEqual(call_kwargs["context"].emittente_soggetto_ruolo_id, 42)

    # --- Pull attivita da commessa (step 0) ---

    # Scopo: Verifica il caso `test_execute_step_runs_pull_attivita_da_commessa_task`.
    @patch("apps.core.services.fan_out.transaction")
    def test_execute_step_runs_pull_attivita_da_commessa_task(self, _mock_txn):
        processi = [{"task": "pull_attivita_da_commessa", "fase": "Pull commesse", "params": {}}]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "pull_attivita_da_commessa_default"
        repo.ALLOWED_TASK_FUNCTIONS["pull_attivita_da_commessa"] = (
            "vendite.fn_emit_attivita_fatturabili_da_commessa"
        )
        commesse_repo = MagicMock()
        commesse_repo.list_commesse_emittibili.return_value = [10, 20]
        executor.commesse_repository = commesse_repo

        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        commesse_repo.list_commesse_emittibili.assert_called_once()
        self.assertEqual(commesse_repo.emit_attivita_fatturabili.call_count, 2)
        call_args_list = commesse_repo.emit_attivita_fatturabili.call_args_list
        self.assertEqual(call_args_list[0][0][0], 10)
        self.assertEqual(call_args_list[1][0][0], 20)

    # ══════════════════════════════════════════════════════════════════
    #  L'ESITO APPESO AI DOCUMENTI DEL LOTTO (brief-db-esito-gruppo-lotto §8)
    # ══════════════════════════════════════════════════════════════════
    #
    # ⛔ IL DIFETTO CHE PRESIDIANO. Un lotto prende in carico tre documenti e ne
    #    fattura due: il terzo falliva e SPARIVA dal racconto — non nel lotto
    #    (non e' mai diventato fattura) e nella competenza ancora fra quelli da
    #    emettere, senza un segno. Sembrava fatturabile.
    # ⚠️ Le uscite dell'handler sono TRE, e la marcatura serve in tutte: il ramo
    #    che SOLLEVA (tutte fallite) e' il caso peggiore ed e' il candidato
    #    naturale a essere dimenticato.

    # Scopo: fa fallire l'emit sulle commesse indicate, lasciando passare le altre.
    @staticmethod
    def _emit_che_fallisce_su(*commesse_ko):
        def _emit(commessa_id, **_kw):
            if commessa_id in commesse_ko:
                raise RuntimeError(f"ROOT source mancante per commessa {commessa_id}")
            return {"righe": 1}
        return _emit

    # Scopo: monta l'handler con un roster di commesse e un emit pilotabile.
    def _executor_pull(self, commesse, *, ko=()):
        processi = [{"task": "pull_attivita_da_commessa", "fase": "Pull commesse", "params": {}}]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "pull_attivita_da_commessa_default"
        repo.ALLOWED_TASK_FUNCTIONS["pull_attivita_da_commessa"] = (
            "vendite.fn_emit_attivita_fatturabili_da_commessa"
        )
        commesse_repo = MagicMock()
        commesse_repo.list_commesse_emittibili.return_value = list(commesse)
        commesse_repo.emit_attivita_fatturabili.side_effect = self._emit_che_fallisce_su(*ko)
        executor.commesse_repository = commesse_repo
        # ⚠️ Il marcatore torna TRE conteggi dal changeSet `20260909-20`,
        #    non piu' uno scalare: un `1` qui direbbe che il chiamante
        #    legge un intero, e il chiamante non lo legge piu'.
        repo.segna_esito_gruppo_lotto.return_value = {
            "marcati": 1, "usciti": 0, "fuori_perimetro": 0,
        }
        return executor, repo

    # Scopo: `{commessa_id: (stato, codice)}` da come il repository e' stato chiamato.
    @staticmethod
    def _esiti_marcati(repo):
        return {
            c.kwargs["commessa_id"]: (c.args[1], c.kwargs.get("errore_codice"))
            for c in repo.segna_esito_gruppo_lotto.call_args_list
        }

    # 1. Una fallita su tre: una `ERRORE` col codice, due `COMPLETED`.
    @patch("apps.core.services.fan_out.transaction")
    def test_pull_marca_errore_sulla_fallita_e_completed_sulle_altre(self, _mock_txn):
        executor, repo = self._executor_pull([10, 20, 30], ko=(20,))

        executor.execute_step(
            lotto_id=1, stato_doc_fiscale_id=2, tipo_lotto="MASSIVO",
            rollback=False, dry_run=False,
        )

        esiti = self._esiti_marcati(repo)
        self.assertEqual(esiti[20][0], "ERRORE")
        self.assertEqual(esiti[20][1], "E_PULL_COMMESSA")
        # ⭐ Anche le riuscite: senza, un gruppo andato bene resta a NULL e non
        #    si distingue da uno mai lavorato.
        self.assertEqual(esiti[10][0], "COMPLETED")
        self.assertEqual(esiti[30][0], "COMPLETED")
        self.assertIsNone(esiti[10][1])

    # 2. ⭐ TUTTE fallite: si marca e NON si solleva piu' (P-5, decisione di Tid
    #    2026-09-06 — «trattiamoli tutti come quando ne capita 2 su 3»).
    # 🔴 Fino al 2026-09-07 questo ramo sollevava `E_PULL_COMMESSA_ALL_FAILED`,
    #    e il rollback dello step si portava via i segni appena scritti: il caso
    #    PEGGIORE era l'unico che non lasciava traccia.
    # ⛔ E la catena si ferma lo stesso, ma per un'altra via: le segnalazioni
    #    critiche scritte per ogni commessa caduta fanno rifiutare l'avanzamento
    #    al giro successivo. Fermarsi e strappare gli appunti erano due cose che
    #    faceva lo stesso gesto.
    @patch("apps.core.services.fan_out.transaction")
    def test_pull_tutte_fallite_marca_e_non_solleva(self, _mock_txn):
        executor, repo = self._executor_pull([10, 20], ko=(10, 20))

        # ⛔ Nessun `assertRaises`: l'assenza dell'eccezione E' il contratto.
        executor.execute_step(
            lotto_id=1, stato_doc_fiscale_id=2, tipo_lotto="MASSIVO",
            rollback=False, dry_run=False,
        )

        esiti = self._esiti_marcati(repo)
        self.assertEqual({c: s for c, (s, _) in esiti.items()},
                         {10: "ERRORE", 20: "ERRORE"})

    # 2-bis. ⛔ IL CODICE DEL FALLIMENTO TOTALE NON LO SOLLEVA PIU' NESSUNO, ed
    #    e' la precondizione di P-6 (la deprecazione a catalogo, che tocca al
    #    DB): finche' una riga di Python lo emette, `obsoleto_dal` sarebbe una
    #    bugia.
    # ⚠️ Si guarda il SORGENTE e non un comportamento, ed e' l'unico modo: il
    #    ramo che lo sollevava non esiste piu', quindi non c'e' nessuna corsa
    #    che possa produrlo — un test sul comportamento sarebbe verde per
    #    sottrazione, cioe' verde anche se qualcuno lo rimettesse altrove.
    # ⛔ Si cerca la forma `code="..."`, non la stringa: il nome compare ancora
    #    nei commenti che raccontano perche' e' sparito, e devono poterci stare.
    def test_il_codice_del_fallimento_totale_non_si_solleva_piu(self):
        from pathlib import Path

        from apps.vendite.services import pipeline_step_executor as modulo

        sorgente = Path(modulo.__file__).read_text(encoding="utf-8")
        self.assertNotIn('code="E_PULL_COMMESSA_ALL_FAILED"', sorgente)

    # 3. Tutto riuscito: nessun campo d'errore valorizzato.
    @patch("apps.core.services.fan_out.transaction")
    def test_pull_marca_completed_quando_va_tutto_bene(self, _mock_txn):
        executor, repo = self._executor_pull([10, 20])

        executor.execute_step(
            lotto_id=1, stato_doc_fiscale_id=2, tipo_lotto="MASSIVO",
            rollback=False, dry_run=False,
        )

        for chiamata in repo.segna_esito_gruppo_lotto.call_args_list:
            self.assertEqual(chiamata.args[1], "COMPLETED")
            self.assertIsNone(chiamata.kwargs.get("errore_codice"))
            self.assertIsNone(chiamata.kwargs.get("errore_messaggio"))

    # 4. ⚠️ La funzione non solleva mai, quindi il suo consuntivo E' l'unico
    #    segnale: va almeno scritto nel log, o il lotto racconta un errore su un
    #    documento che non mostra.
    @patch("apps.core.services.fan_out.transaction")
    def test_pull_avvisa_quando_l_esito_non_viene_appeso(self, _mock_txn):
        executor, repo = self._executor_pull([10], ko=(10,))
        repo.segna_esito_gruppo_lotto.return_value = {
            "marcati": 0, "usciti": 0, "fuori_perimetro": 0,
        }

        with self.assertLogs(
            "apps.vendite.services.pipeline_step_executor", level="WARNING",
        ) as log:
            executor.execute_step(
                lotto_id=1, stato_doc_fiscale_id=2, tipo_lotto="MASSIVO",
                rollback=False, dry_run=False,
            )
        self.assertTrue(
            any("esito_non_appeso" in r for r in log.output),
            "nessun avviso: un esito non appeso resterebbe invisibile",
        )

    # 4-bis. ⭐ ZERO MARCATI PERCHE' SONO USCITI DAL GIRO — e qui l'avviso NON
    #    deve suonare. E' il caso NORMALE del verbo «togli dal giro»: il
    #    documento e' stato tolto apposta, e il marcatore lo salta apposta
    #    (changeSet `20260909-18`).
    # 🔴 Senza questa distinzione l'avviso diventava rumore su un caso
    #    legittimo, a ogni rilancio — e un avviso che suona quando va tutto bene
    #    e' un avviso che si smette di leggere, cioe' peggio di nessun avviso.
    @patch("apps.core.services.fan_out.transaction")
    def test_pull_non_avvisa_se_i_documenti_sono_usciti_dal_giro(self, _mock_txn):
        executor, repo = self._executor_pull([10], ko=(10,))
        repo.segna_esito_gruppo_lotto.return_value = {
            "marcati": 0, "usciti": 2, "fuori_perimetro": 0,
        }

        with self.assertNoLogs(
            "apps.vendite.services.pipeline_step_executor", level="WARNING",
        ):
            executor.execute_step(
                lotto_id=1, stato_doc_fiscale_id=2, tipo_lotto="MASSIVO",
                rollback=False, dry_run=False,
            )

    # 4-ter. ⚠️ E il terzo zero resta SOSPETTO: documenti che esistono ma non
    #    sono di questo lotto. Non nasce dal cantiere dell'uscita — c'era gia',
    #    nascosto nello stesso zero — e adesso che si distingue va detto anche
    #    quando qualcosa e' stato marcato.
    @patch("apps.core.services.fan_out.transaction")
    def test_pull_avvisa_sui_documenti_fuori_perimetro(self, _mock_txn):
        executor, repo = self._executor_pull([10], ko=(10,))
        repo.segna_esito_gruppo_lotto.return_value = {
            "marcati": 1, "usciti": 0, "fuori_perimetro": 1,
        }

        with self.assertLogs(
            "apps.vendite.services.pipeline_step_executor", level="WARNING",
        ) as log:
            executor.execute_step(
                lotto_id=1, stato_doc_fiscale_id=2, tipo_lotto="MASSIVO",
                rollback=False, dry_run=False,
            )
        self.assertTrue(any("fuori_perimetro=1" in r for r in log.output))

    # Scopo: Verifica il caso `test_pull_attivita_da_commessa_dry_run_skips_emit`.
    def test_pull_attivita_da_commessa_dry_run_skips_emit(self):
        processi = [{"task": "pull_attivita_da_commessa", "fase": "Pull commesse", "params": {}}]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "pull_attivita_da_commessa_default"
        repo.ALLOWED_TASK_FUNCTIONS["pull_attivita_da_commessa"] = (
            "vendite.fn_emit_attivita_fatturabili_da_commessa"
        )
        commesse_repo = MagicMock()
        commesse_repo.list_commesse_emittibili.return_value = [10, 20]
        executor.commesse_repository = commesse_repo

        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=True,
        )

        commesse_repo.emit_attivita_fatturabili.assert_not_called()

    # Scopo: Verifica il caso `test_pull_attivita_da_commessa_empty_list_no_emit`.
    def test_pull_attivita_da_commessa_empty_list_no_emit(self):
        processi = [{"task": "pull_attivita_da_commessa", "fase": "Pull commesse", "params": {}}]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "pull_attivita_da_commessa_default"
        repo.ALLOWED_TASK_FUNCTIONS["pull_attivita_da_commessa"] = (
            "vendite.fn_emit_attivita_fatturabili_da_commessa"
        )
        commesse_repo = MagicMock()
        commesse_repo.list_commesse_emittibili.return_value = []
        executor.commesse_repository = commesse_repo

        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        commesse_repo.list_commesse_emittibili.assert_called_once()
        commesse_repo.emit_attivita_fatturabili.assert_not_called()

    # Scopo: Gestisce `_build_executor_pull` nel flusso applicativo del modulo —
    #        executor col task di pull, tracing ATTIVO (serve un task_run vero
    #        per poter osservare COMPLETATO vs ERRORE) e repo commesse mockato
    #        con la lista di commesse emittibili passata.
    def _build_executor_pull(self, commesse_ids, task_run_id=555):
        processi = [{"task": "pull_attivita_da_commessa", "fase": "Pull commesse", "params": {}}]
        executor, repo, _, error_logger = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "pull_attivita_da_commessa_default"
        repo.ALLOWED_TASK_FUNCTIONS["pull_attivita_da_commessa"] = (
            "vendite.fn_emit_attivita_fatturabili_da_commessa"
        )
        repo.task_policy_exists.return_value = True
        run_mode = MagicMock()
        run_mode.execution_mode = "RUN"
        repo.resolve_lotto_task_execution_mode.return_value = run_mode
        task_run = MagicMock()
        task_run.task_run_id = task_run_id
        repo.start_lotto_task_run.return_value = task_run
        # Il giro ha un'IDENTITA', ed e' quella che il pull deve consegnare
        # alle righe che accetta. Un MagicMock nudo passerebbe l'assert per
        # identita' d'oggetto senza dire niente sul valore trasportato.
        repo.get_lotto_context.return_value.lock_batch_id = _LOCK_BATCH_GIRO
        commesse_repo = MagicMock()
        commesse_repo.list_commesse_emittibili.return_value = list(commesse_ids)
        executor.commesse_repository = commesse_repo
        # ⭐ DI CHI E' IL FALLIMENTO: la conversione commessa → documenti, che il
        #    pull chiede al database per dichiarare il proprietario della
        #    segnalazione (§6.1 di brief-db-uscita-documento-dal-giro).
        # ⛔ VA MOCKATA ESPLICITAMENTE, e il perche' e' una trappola vera: un
        #    `MagicMock` nudo si ITERA VUOTO, quindi il ciclo «una riga per
        #    documento» non gira e non viene scritta NESSUNA segnalazione — senza
        #    errori, senza fallimenti, con i test che vanno in rosso su
        #    `call_args is None` invece che sul difetto. Un default esplicito
        #    dice qual e' il caso normale: un documento per commessa.
        repo.gruppi_di_commessa_nel_lotto.side_effect = (
            lambda lotto_id, commessa_id: [f"COMMESSA:{commessa_id}"]
        )
        return executor, repo, commesse_repo, error_logger

    # Scopo: ⚠️ IL TEST CHE CONTA sul pull (D-Q p.3) — con 1 commessa su 3 in
    #        errore il task_run chiude in ERRORE (`fail_lotto_task_run`) e NON in
    #        COMPLETATO, SENZA sollevare. Con COMPLETATO il resolver darebbe SKIP
    #        al rilancio e la commessa rimasta indietro non verrebbe mai
    #        ritentata — in silenzio, perche' l'errore vive solo sui log.
    @patch("apps.core.services.fan_out.transaction")
    def test_pull_attivita_da_commessa_parziale_chiude_task_run_errore(self, _mock_txn):
        executor, repo, commesse_repo, error_logger = self._build_executor_pull([10, 20, 30])
        commesse_repo.emit_attivita_fatturabili.side_effect = [
            None, RuntimeError("emit ko"), None,
        ]

        # Nessuna eccezione: le due commesse sane restano emesse e lo step prosegue.
        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        self.assertEqual(commesse_repo.emit_attivita_fatturabili.call_count, 3)
        repo.fail_lotto_task_run.assert_called_once()
        args, kwargs = repo.fail_lotto_task_run.call_args
        self.assertEqual(args[0], 555)
        # Codice riusato, non sintetico: e' lo stesso motivo per-commessa.
        self.assertEqual(args[1], "E_PULL_COMMESSA")
        self.assertEqual(kwargs["meta"]["totale"], 3)
        self.assertEqual(kwargs["meta"]["ok"], 2)
        self.assertEqual(kwargs["meta"]["falliti"], 1)
        self.assertEqual(kwargs["meta"]["commesse_fallite"], [20])
        repo.complete_lotto_task_run.assert_not_called()
        # Il motivo per-commessa resta anche sui log di lotto.
        error_logger.log_error.assert_called_once()

    # Scopo: simmetrico — nessuna commessa fallita chiude il task_run in
    #        COMPLETATO. Serve a provare che il parziale non e' diventato la
    #        regola: un giro pulito deve restare pulito.
    # ⭐ E il giro pulito DICHIARA i suoi contatori (2026-09-04): un COMPLETATO
    #        muto non distingue «due commesse passate» da «non ho provato», e
    #        col perimetro consegnato il secondo caso esiste davvero — marchio
    #        assente, zero righe, nessun errore.
    @patch("apps.core.services.fan_out.transaction")
    def test_pull_attivita_da_commessa_tutte_ok_completa_task_run(self, _mock_txn):
        executor, repo, commesse_repo, _ = self._build_executor_pull([10, 20], task_run_id=556)

        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.complete_lotto_task_run.assert_called_once_with(
            556,
            meta={
                "task": "pull_attivita_da_commessa",
                "totale": 2,
                "ok": 2,
                "falliti": 0,
            },
        )
        repo.fail_lotto_task_run.assert_not_called()

    # Scopo: 🔴 IL PERIMETRO SI CONSEGNA — il pull riceve l'identita' DEL GIRO
    #        (`context.lock_batch_id`) e la porta a TUTTI E DUE i cancelli: la
    #        discovery (quali commesse visitare) e l'emit (quali righe emettere).
    # ⛔ Questo test non presidia una comodita': senza quel valore il pull firma
    #        NULL, `fn_select_attivita_fatturabili` (changeSet 20260904-50)
    #        filtra sul marchio e non trova NIENTE, e il giro emette ZERO
    #        fatture SENZA sollevare. E' il difetto peggiore della famiglia:
    #        non un errore, ma un lotto vuoto che sembra un mese senza lavoro.
    #        Una regressione qui e' invisibile a ogni altro test del file, che
    #        guardano gli esiti e non gli argomenti.
    # ⭐ E dal 2026-09-12 la stessa identita' la vuole ANCHE LA DISCOVERY (D1,
    #        changeSet `20260912-15`): al rilancio di un pull fallito i propri
    #        documenti sono `TRATTENUTA` dal lotto che sta riprovando, e senza
    #        identita' la discovery scarta la commessa — il giro visita zero
    #        commesse e chiude COMPLETATO senza aver emesso niente
    #        (LTF-0010972). Fino a quel giorno l'eccezione dell'emit era
    #        corretta e IRRAGGIUNGIBILE: chi l'avrebbe chiamata non arrivava
    #        mai a farlo. Consegnare l'identita' al solo emit e' il difetto.
    @patch("apps.core.services.fan_out.transaction")
    def test_pull_consegna_al_db_l_identita_del_giro(self, _mock_txn):
        executor, _repo, commesse_repo, _ = self._build_executor_pull([10, 20])

        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        # Primo cancello: la discovery riceve l'identita'.
        commesse_repo.list_commesse_emittibili.assert_called_once()
        self.assertEqual(
            commesse_repo.list_commesse_emittibili.call_args.kwargs["emit_batch_id"],
            _LOCK_BATCH_GIRO,
        )
        # Secondo cancello: l'emit riceve LA STESSA identita', per ogni commessa.
        self.assertEqual(commesse_repo.emit_attivita_fatturabili.call_count, 2)
        for chiamata in commesse_repo.emit_attivita_fatturabili.call_args_list:
            self.assertEqual(chiamata.kwargs["emit_batch_id"], _LOCK_BATCH_GIRO)

    # Scopo: ⛔ un giro SENZA identita' non parte, invece di emettere zero
    #        fatture in silenzio. E' la scelta fra un errore che si vede e un
    #        lotto vuoto indistinguibile da un mese senza lavoro.
    @patch("apps.core.services.fan_out.transaction")
    def test_pull_si_ferma_se_il_giro_non_ha_identita(self, _mock_txn):
        executor, _repo, commesse_repo, _ = self._build_executor_pull([10, 20])
        _repo.get_lotto_context.return_value.lock_batch_id = None

        with self.assertRaises(ServiceError) as ctx:
            executor.execute_step(
                lotto_id=1,
                stato_doc_fiscale_id=2,
                tipo_lotto="MASSIVO",
                rollback=False,
                dry_run=False,
            )

        self.assertEqual(ctx.exception.code, "E_PIPELINE_SCOPE_INCOMPLETE")
        # ⭐ E soprattutto: NESSUNA commessa e' stata toccata. Un pull partito a
        #    meta' avrebbe firmato righe con marchio nullo, cioe' seminato il
        #    difetto invece di fermarlo.
        commesse_repo.emit_attivita_fatturabili.assert_not_called()
        # ⛔ E NEMMENO LA DISCOVERY E' PARTITA — e' l'asserzione che distingue
        #    l'ordine nuovo (guard PRIMA della discovery, 2026-09-12) da quello
        #    vecchio (guard dopo). Con la discovery che legge l'identita' un
        #    guard a valle non ferma niente: chiamata con NULL non fallisce,
        #    risponde a un'altra domanda e scarta i propri documenti in
        #    silenzio. Senza questa riga il test restava verde su entrambi gli
        #    ordini, cioe' non decideva.
        commesse_repo.list_commesse_emittibili.assert_not_called()

    # Scopo: ⛔ DENTRO L'HANDLER, il guard sull'identita' precede ANCHE il ramo
    #        dry-run. Prima del 2026-09-12 il `return None` del dry-run stava
    #        fra la discovery e il guard: un dry-run senza identita' avrebbe
    #        interrogato la discovery con NULL e contato MENO commesse del giro
    #        vero — un'anteprima che risponde a un'altra domanda.
    #        `lock_batch_id` e' NOT NULL a tabella: se manca, il contesto non e'
    #        stato caricato, e un'anteprima su un contesto rotto non e'
    #        un'anteprima.
    # ⚠️ Si chiama l'HANDLER DIRETTAMENTE, e non `execute_step`: da li' il
    #        dry-run esce in `_run_task` prima ancora di invocarlo (test 23d), e
    #        il ramo dentro l'handler e' la «seconda cintura» dichiarata in quel
    #        test — quella che resta corretta se un domani l'handler venisse
    #        invocato fuori da `_run_task`. E' quella cintura che qui si prova.
    def test_pull_dry_run_senza_identita_si_ferma_lo_stesso(self):
        executor, repo, commesse_repo, _ = self._build_executor_pull([10, 20])
        context = repo.get_lotto_context.return_value
        context.lock_batch_id = None

        with self.assertRaises(ServiceError) as ctx:
            executor._handle_pull_attivita_da_commessa_task(
                task="pull_attivita_da_commessa",
                fn_name="vendite.fn_emit_attivita_fatturabili_da_commessa",
                lotto_id=1,
                stato_doc_fiscale_id=2,
                context=context,
                params={},
                dry_run=True,
            )

        self.assertEqual(ctx.exception.code, "E_PIPELINE_SCOPE_INCOMPLETE")
        commesse_repo.list_commesse_emittibili.assert_not_called()
        commesse_repo.emit_attivita_fatturabili.assert_not_called()

    # Scopo: ⭐ IL MOTIVO DI DOMINIO, non il dump. `vw_dash_commesse_respinte`
    #        mostra a video `meta->>'detail'`: se li' dentro finisce l'impasto
    #        di eccezione Python + DETAIL + stack PL/pgSQL, la promessa «ognuna
    #        mostra il problema» e' vera sulla carta e falsa a video.
    # ⚠️ Il dump non si perde — resta nel `context` come `dettaglio_tecnico`:
    #        serve a chi diagnostica, non a chi lavora. Il test presidia
    #        entrambe le meta', perche' spostare il motivo buttando via il
    #        tecnico sarebbe uno scambio, non una correzione.
    @patch("apps.core.services.fan_out.transaction")
    def test_pull_scrive_il_motivo_di_dominio_e_conserva_il_dump(self, _mock_txn):
        executor, _repo, commesse_repo, error_logger = self._build_executor_pull([10])
        # ⛔ LA FORMA E' QUELLA VERA, misurata sul DB il 2026-09-04: il motivo
        #    di dominio sta nel MESSAGGIO (`message_primary`), mentre `DETAIL`
        #    porta il testo generico della policy — uguale per ogni
        #    `E_VALORE_MANCANTE` del sistema. Un finto che invertisse i due
        #    farebbe passare il test con l'ordine di lettura SBAGLIATO: e'
        #    successo, ed e' il motivo per cui questo commento esiste.
        commesse_repo.emit_attivita_fatturabili.side_effect = make_db_error(
            "Indicare un valore per ROOT source mancante per commessa 10. "
            "Dato obbligatorio.",
            codice="E_VALORE_MANCANTE",
            detail="Non e' stato assegnato un valore all'informazione richiesta.",
        )

        # ⚠️ Una commessa sola, e fallisce: e' il ramo «tutte fallite», che dal
        #    2026-09-07 NON solleva piu' (P-5). Al diario per-commessa non
        #    cambia niente — il run logger ha gia' scritto prima che l'esito
        #    venisse aggregato, ed e' quello che questo test guarda.
        executor.execute_step(
                lotto_id=1,
                stato_doc_fiscale_id=2,
                tipo_lotto="MASSIVO",
                rollback=False,
                dry_run=False,
            )

        error_logger.log_error.assert_called_once()
        kwargs = error_logger.log_error.call_args.kwargs
        self.assertIn("ROOT source mancante per commessa 10", kwargs["detail"])
        # ⛔ E NON il testo generico della policy: quella frase e' vera per ogni
        #    E_VALORE_MANCANTE del sistema e non dice su cosa agire.
        self.assertNotIn("informazione richiesta", kwargs["detail"])
        self.assertEqual(kwargs["context"]["commessa_id"], 10)
        self.assertIn("dettaglio_tecnico", kwargs["context"])
        self.assertIn("commessa_id=10", kwargs["context"]["dettaglio_tecnico"])

    # Scopo: il ripiego quando il database non ha detto niente di leggibile —
    #        un errore nato in Python non ha campi `diag`, e restare senza
    #        motivo sarebbe peggio di un motivo tecnico.
    @patch("apps.core.services.fan_out.transaction")
    def test_pull_senza_campi_diag_ripiega_sul_messaggio_normalizzato(self, _mock_txn):
        executor, _repo, commesse_repo, error_logger = self._build_executor_pull([10])
        commesse_repo.emit_attivita_fatturabili.side_effect = RuntimeError("emit ko")

        # ⚠️ Nessuna eccezione da attendere: dal 2026-09-07 il ramo «tutte
        #    fallite» torna un esito (P-5). Il diario per-commessa e' scritto
        #    prima dell'aggregazione, quindi il presidio non cambia.
        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        kwargs = error_logger.log_error.call_args.kwargs
        self.assertIn("emit ko", kwargs["detail"])

    # Scopo: ⭐ «TUTTE FALLITE» NON SOLLEVA PIU', e chiude il task_run in ERRORE
    #        come il parziale (P-5, decisione di Tid 2026-09-06).
    # 🔴 QUESTO TEST PRESIDIAVA IL CONTRARIO, e il contrario era il difetto:
    #        sollevare faceva rollback dello step e si portava via i segni
    #        appena scritti sui documenti caduti — il caso peggiore era l'unico
    #        che non lasciava traccia.
    # ⛔ Il timore che lo motivava («proseguire costruirebbe un lotto VUOTO») e'
    #        coperto altrove e meglio: il passo scrive una segnalazione CRITICA
    #        per ogni commessa caduta, quindi al giro dopo `blocks_next_step`
    #        rifiuta l'avanzamento. Si ferma TENENDO, invece di fermarsi
    #        strappando.
    # ⚠️ `complete_lotto_task_run` NON deve essere chiamato: il giro e' finito,
    #        ma male. Chiuderlo COMPLETATO farebbe dare SKIP al resolver al
    #        rilancio — le commesse rimaste indietro non verrebbero piu'
    #        ritentate, in silenzio. E' il difetto gia' corretto sul parziale il
    #        2026-08-09, e qui non deve rientrare dalla finestra.
    @patch("apps.core.services.fan_out.transaction")
    def test_pull_attivita_da_commessa_tutte_fallite_non_solleva(self, _mock_txn):
        executor, repo, commesse_repo, _ = self._build_executor_pull([10, 20], task_run_id=557)
        commesse_repo.emit_attivita_fatturabili.side_effect = RuntimeError("emit ko")

        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.complete_lotto_task_run.assert_not_called()
        repo.fail_lotto_task_run.assert_called_once()
        # Stesso codice del parziale: i due rami sono diventati lo stesso codice.
        self.assertEqual(repo.fail_lotto_task_run.call_args.args[1], "E_PULL_COMMESSA")

    # Scopo: dry-run — nessun esito parziale puo' comparire, perche' non e'
    #        stato tentato nulla.
    #        ⚠️ Il gate che conta sta PRIMA dell'handler: `_run_task` esce in
    #        dry-run subito dopo aver risolto l'handler_code, quindi non parte
    #        nemmeno il task_run. Il `if dry_run: return None` dentro l'handler
    #        e' una seconda cintura (l'handler resta corretto se un domani
    #        venisse invocato fuori da `_run_task`), non il presidio primario:
    #        questo test verifica il comportamento reale, non quel ramo.
    @patch("apps.core.services.fan_out.transaction")
    def test_pull_attivita_da_commessa_dry_run_non_produce_parziale(self, _mock_txn):
        executor, repo, commesse_repo, _ = self._build_executor_pull([10, 20], task_run_id=558)

        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=True,
        )

        commesse_repo.emit_attivita_fatturabili.assert_not_called()
        repo.start_lotto_task_run.assert_not_called()
        repo.fail_lotto_task_run.assert_not_called()
        repo.complete_lotto_task_run.assert_not_called()

    # Scopo: task `snapshot_indirizzi_lotto` (Fase 2 satelliti fattura) — il
    #        run felice esegue il wrapper repo col batch di default e, senza
    #        fatture fallite, il task_run chiude in COMPLETATO.
    def test_execute_step_runs_snapshot_indirizzi_lotto_task(self):
        processi = [{
            "task": "snapshot_indirizzi_lotto",
            "fase": "Snapshot indirizzi fattura",
            "params": {"implementation_key": "default"},
        }]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "snapshot_indirizzi_lotto_default"
        repo.run_snapshot_indirizzi_lotto_task.return_value = {
            "fatture_count": 3, "inserted_rows": 3, "updated_rows": 0,
            "intestazioni_scritte": 3, "skipped_rows": 0, "failed_rows": 0,
        }

        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=1,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.run_snapshot_indirizzi_lotto_task.assert_called_once_with(
            lotto_id=1, batch_size=1000,
        )

    # Scopo: dry-run — nessuna esecuzione del wrapper (gate in _run_validated_task).
    def test_execute_step_snapshot_indirizzi_dry_run_skips(self):
        processi = [{
            "task": "snapshot_indirizzi_lotto",
            "fase": "Snapshot indirizzi fattura",
            "params": {"implementation_key": "default"},
        }]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "snapshot_indirizzi_lotto_default"

        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=1,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=True,
        )

        repo.run_snapshot_indirizzi_lotto_task.assert_not_called()

    # Scopo: ⚠️ D-Q p.3, IL TEST CHE CONTA — `failed_rows > 0` chiude il
    #        task_run in ERRORE (fail_lotto_task_run) e NON in COMPLETATO,
    #        SENZA sollevare: al rilancio dello step il resolver dara' RESUME
    #        (policy RESUME_TASK) invece di SKIP e il task verra' ripetuto.
    #        Con COMPLETATO la correzione dell'anagrafica non verrebbe mai
    #        riletta; con un raise il rollback cancellerebbe anche il lavoro
    #        delle fatture sane e la marcatura di quelle rotte.
    def test_execute_step_snapshot_indirizzi_failed_rows_chiude_task_run_errore(self):
        processi = [{
            "task": "snapshot_indirizzi_lotto",
            "fase": "Snapshot indirizzi fattura",
            "params": {"implementation_key": "default"},
        }]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "snapshot_indirizzi_lotto_default"
        repo.task_policy_exists.return_value = True
        run_mode = MagicMock()
        run_mode.execution_mode = "RUN"
        repo.resolve_lotto_task_execution_mode.return_value = run_mode
        task_run = MagicMock()
        task_run.task_run_id = 777
        repo.start_lotto_task_run.return_value = task_run
        repo.run_snapshot_indirizzi_lotto_task.return_value = {
            "fatture_count": 3, "inserted_rows": 2, "updated_rows": 0,
            "intestazioni_scritte": 2, "skipped_rows": 0, "failed_rows": 1,
        }

        # Nessuna eccezione: lo step si completa (D-Q).
        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=1,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.fail_lotto_task_run.assert_called_once()
        args, kwargs = repo.fail_lotto_task_run.call_args
        self.assertEqual(args[0], 777)
        self.assertEqual(args[1], "E_INDIRIZZO_FATTURA_MANCANTE")
        self.assertEqual(kwargs["meta"]["failed_rows"], 1)
        repo.complete_lotto_task_run.assert_not_called()

    # Scopo: simmetrico — `failed_rows == 0` con tracing attivo chiude il
    #        task_run in COMPLETATO (nessun fail).
    def test_execute_step_snapshot_indirizzi_senza_falliti_completa_task_run(self):
        processi = [{
            "task": "snapshot_indirizzi_lotto",
            "fase": "Snapshot indirizzi fattura",
            "params": {"implementation_key": "default"},
        }]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "snapshot_indirizzi_lotto_default"
        repo.task_policy_exists.return_value = True
        run_mode = MagicMock()
        run_mode.execution_mode = "RUN"
        repo.resolve_lotto_task_execution_mode.return_value = run_mode
        task_run = MagicMock()
        task_run.task_run_id = 778
        repo.start_lotto_task_run.return_value = task_run
        repo.run_snapshot_indirizzi_lotto_task.return_value = {
            "fatture_count": 2, "inserted_rows": 2, "updated_rows": 0,
            "intestazioni_scritte": 2, "skipped_rows": 0, "failed_rows": 0,
        }

        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=1,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.complete_lotto_task_run.assert_called_once_with(778)
        repo.fail_lotto_task_run.assert_not_called()

    # Scopo: task `genera_scadenze_lotto` (Fase 4 satelliti fattura) — il run
    #        felice esegue il wrapper repo col batch di default e, senza fatture
    #        fallite, il task_run chiude in COMPLETATO.
    def test_execute_step_runs_genera_scadenze_lotto_task(self):
        processi = [{
            "task": "genera_scadenze_lotto",
            "fase": "Generazione scadenze",
            "params": {"implementation_key": "default"},
        }]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "genera_scadenze_lotto_default"
        repo.run_genera_scadenze_lotto_task.return_value = {
            "fatture_count": 3, "deleted_rows": 0, "inserted_rows": 6,
            "skipped_rows": 0, "skipped_errore_rows": 0, "failed_rows": 0,
        }

        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.run_genera_scadenze_lotto_task.assert_called_once_with(
            lotto_id=1, batch_size=1000,
        )

    # Scopo: dry-run — nessuna esecuzione del wrapper (gate in _run_validated_task).
    def test_execute_step_genera_scadenze_dry_run_skips(self):
        processi = [{
            "task": "genera_scadenze_lotto",
            "fase": "Generazione scadenze",
            "params": {"implementation_key": "default"},
        }]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "genera_scadenze_lotto_default"

        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=True,
        )

        repo.run_genera_scadenze_lotto_task.assert_not_called()

    # Scopo: ⚠️ D-Q p.3 sul gemello scadenze — `failed_rows > 0` chiude il
    #        task_run in ERRORE SENZA sollevare, cosi' il rilancio dello step
    #        (policy RESUME_TASK — `RESUME_STEP` e' ritirato dal CHECK col
    #        `20260912-32`) ripete davvero il task invece di saltarlo.
    #        Verifica anche che i due contatori di salto restino SEPARATI nel
    #        meta: «chiusa» e «rotta» non vanno sommate.
    def test_execute_step_genera_scadenze_failed_rows_chiude_task_run_errore(self):
        processi = [{
            "task": "genera_scadenze_lotto",
            "fase": "Generazione scadenze",
            "params": {"implementation_key": "default"},
        }]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "genera_scadenze_lotto_default"
        repo.task_policy_exists.return_value = True
        run_mode = MagicMock()
        run_mode.execution_mode = "RUN"
        repo.resolve_lotto_task_execution_mode.return_value = run_mode
        task_run = MagicMock()
        task_run.task_run_id = 881
        repo.start_lotto_task_run.return_value = task_run
        repo.run_genera_scadenze_lotto_task.return_value = {
            "fatture_count": 4, "deleted_rows": 2, "inserted_rows": 6,
            "skipped_rows": 2, "skipped_errore_rows": 1, "failed_rows": 1,
        }

        # Nessuna eccezione: lo step si completa (D-Q).
        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.fail_lotto_task_run.assert_called_once()
        args, kwargs = repo.fail_lotto_task_run.call_args
        self.assertEqual(args[0], 881)
        self.assertEqual(args[1], "E_SCADENZE_LOTTO_PARZIALE")
        self.assertEqual(kwargs["meta"]["failed_rows"], 1)
        self.assertEqual(kwargs["meta"]["skipped_rows"], 2)
        self.assertEqual(kwargs["meta"]["skipped_errore_rows"], 1)
        repo.complete_lotto_task_run.assert_not_called()

    # Scopo: simmetrico — `failed_rows == 0` con tracing attivo chiude il
    #        task_run in COMPLETATO, anche con fatture SALTATE: un lotto in cui
    #        tutte le fatture sono gia' definitive e' un giro riuscito, non un
    #        giro fallito.
    def test_execute_step_genera_scadenze_senza_falliti_completa_task_run(self):
        processi = [{
            "task": "genera_scadenze_lotto",
            "fase": "Generazione scadenze",
            "params": {"implementation_key": "default"},
        }]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "genera_scadenze_lotto_default"
        repo.task_policy_exists.return_value = True
        run_mode = MagicMock()
        run_mode.execution_mode = "RUN"
        repo.resolve_lotto_task_execution_mode.return_value = run_mode
        task_run = MagicMock()
        task_run.task_run_id = 882
        repo.start_lotto_task_run.return_value = task_run
        repo.run_genera_scadenze_lotto_task.return_value = {
            "fatture_count": 0, "deleted_rows": 0, "inserted_rows": 0,
            "skipped_rows": 3, "skipped_errore_rows": 0, "failed_rows": 0,
        }

        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.complete_lotto_task_run.assert_called_once_with(882)
        repo.fail_lotto_task_run.assert_not_called()

    # Scopo: ORDINE (piano DB satelliti Fase 4) — nello step EMESSA le scadenze
    #        girano DOPO il ricalcolo IVA, perche' la base di ripartizione e'
    #        `totale_a_pagare`. Con la sequenza corretta lo step passa e i due
    #        wrapper sono invocati in quell'ordine.
    def test_execute_step_genera_scadenze_dopo_ricalcola_iva_ok(self):
        processi = [
            {"task": "ricalcola_iva_lotto", "fase": "IVA", "params": {"implementation_key": "default"}},
            {"task": "genera_scadenze_lotto", "fase": "Generazione scadenze", "params": {"implementation_key": "default"}},
        ]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.side_effect = (
            lambda *, task_code, implementation_key: f"{task_code}_default"
        )
        repo.run_genera_scadenze_lotto_task.return_value = {
            "fatture_count": 1, "deleted_rows": 0, "inserted_rows": 1,
            "skipped_rows": 0, "skipped_errore_rows": 0, "failed_rows": 0,
        }

        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        chiamati = [c[0] for c in repo.method_calls]
        self.assertLess(
            chiamati.index("run_ricalcola_iva_lotto_task"),
            chiamati.index("run_genera_scadenze_lotto_task"),
        )

    # Scopo: ⚠️ IL TEST CHE CONTA sull'ordine — la sequenza invertita e'
    #        RIFIUTATA prima che un solo task scriva. Senza questo guard il
    #        generatore solleverebbe `E_SCADENZE_BASE_NON_PRONTA` su OGNI
    #        fattura, e un giro interamente rosso sembrerebbe un difetto dei
    #        dati invece di una riga di configurazione girata.
    def test_execute_step_genera_scadenze_prima_di_ricalcola_iva_rifiutato(self):
        processi = [
            {"task": "genera_scadenze_lotto", "fase": "Generazione scadenze", "params": {"implementation_key": "default"}},
            {"task": "ricalcola_iva_lotto", "fase": "IVA", "params": {"implementation_key": "default"}},
        ]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.side_effect = (
            lambda *, task_code, implementation_key: f"{task_code}_default"
        )

        with self.assertRaises(ServiceError) as ctx:
            executor.execute_step(
                lotto_id=1,
                stato_doc_fiscale_id=2,
                tipo_lotto="MASSIVO",
                rollback=False,
                dry_run=False,
            )

        self.assertEqual(ctx.exception.code, "E_PIPELINE_VALIDATION")
        self.assertIn("genera_scadenze_lotto", str(ctx.exception.detail))
        self.assertIn("ricalcola_iva_lotto", str(ctx.exception.detail))
        # Nessuna scrittura: il rifiuto precede il primo task.
        repo.run_genera_scadenze_lotto_task.assert_not_called()
        repo.run_ricalcola_iva_lotto_task.assert_not_called()

    # Scopo: il guard NON e' un obbligo di co-presenza — se il ricalcolo IVA
    #        vive in uno step precedente lo step delle scadenze e' valido.
    #        Fallire qui vieterebbe di spezzare la catena su piu' step.
    def test_execute_step_genera_scadenze_senza_ricalcola_iva_nello_step_ammesso(self):
        processi = [{
            "task": "genera_scadenze_lotto",
            "fase": "Generazione scadenze",
            "params": {"implementation_key": "default"},
        }]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "genera_scadenze_lotto_default"
        repo.run_genera_scadenze_lotto_task.return_value = {
            "fatture_count": 1, "deleted_rows": 0, "inserted_rows": 1,
            "skipped_rows": 0, "skipped_errore_rows": 0, "failed_rows": 0,
        }

        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.run_genera_scadenze_lotto_task.assert_called_once()

    # Scopo: in ROLLBACK l'ordine non si verifica — la catena di annullamento
    #        percorre i passi a ritroso, quindi la sequenza «invertita» e'
    #        esattamente quella attesa e bloccarla impedirebbe l'annullamento.
    def test_execute_step_ordine_non_verificato_in_rollback(self):
        processi = [
            {"task": "genera_scadenze_lotto", "fase": "Generazione scadenze", "params": {"implementation_key": "default"}},
            {"task": "ricalcola_iva_lotto", "fase": "IVA", "params": {"implementation_key": "default"}},
        ]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.side_effect = (
            lambda *, task_code, implementation_key: f"{task_code}_default"
        )
        repo.run_genera_scadenze_lotto_task.return_value = {
            "fatture_count": 1, "deleted_rows": 1, "inserted_rows": 0,
            "skipped_rows": 0, "skipped_errore_rows": 0, "failed_rows": 0,
        }

        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=2,
            tipo_lotto="MASSIVO",
            rollback=True,
            dry_run=False,
        )

        repo.run_genera_scadenze_lotto_task.assert_called_once()

    # ══════════════════════════════════════════════════════════
    #  popola_fatture_rettifiche — il legame documentale (N10 / BE-8)
    # ══════════════════════════════════════════════════════════

    # Scopo: il task proietta il legame per OGNI fattura del lotto. Una fattura
    #        senza righe di rettifica aggiunge zero coppie, e va chiamata lo
    #        stesso: filtrarle a monte in Python significherebbe riscrivere qui
    #        il predicato che la funzione DB ha gia'.
    def test_execute_step_runs_popola_fatture_rettifiche_task(self):
        processi = [{
            "task": "popola_fatture_rettifiche",
            "fase": "Legame documentale note di credito",
            "params": {"implementation_key": "default"},
        }]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "popola_fatture_rettifiche_default"
        repo.popola_fatture_rettifiche.side_effect = [1, 0]

        executor.execute_step(
            lotto_id=9,
            stato_doc_fiscale_id=8,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        repo.list_fatture_by_lotto.assert_called_once_with(9)
        repo.popola_fatture_rettifiche.assert_any_call(101)
        repo.popola_fatture_rettifiche.assert_any_call(102)

    def test_popola_fatture_rettifiche_dry_run_skips(self):
        processi = [{
            "task": "popola_fatture_rettifiche",
            "fase": "Legame documentale note di credito",
            "params": {"implementation_key": "default"},
        }]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "popola_fatture_rettifiche_default"

        executor.execute_step(
            lotto_id=9,
            stato_doc_fiscale_id=8,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=True,
        )

        repo.popola_fatture_rettifiche.assert_not_called()

    # Scopo: 🔴 la scelta OPPOSTA a quella di `genera_scadenze_lotto` e
    #        `snapshot_indirizzi_lotto`, ed e' il test che la fissa: qui una
    #        fattura in errore FERMA lo step invece di produrre un esito
    #        parziale. Il motivo e' a valle, non qui: `stampa_documenti_lotto`
    #        viene subito dopo e consuma questo legame, quindi proseguire
    #        stamperebbe un documento fiscale senza `DatiFattureCollegate`.
    #        La terza fattura NON viene tentata: il fail-fast e' fail-fast.
    def test_popola_fatture_rettifiche_fail_fast_su_singola_fattura(self):
        processi = [{
            "task": "popola_fatture_rettifiche",
            "fase": "Legame documentale note di credito",
            "params": {"implementation_key": "default"},
        }]
        executor, repo, _, error_logger = self._build_executor(processi)
        repo.get_task_handler_code.return_value = "popola_fatture_rettifiche_default"
        repo.list_fatture_by_lotto.return_value = [101, 102, 103]
        repo.popola_fatture_rettifiche.side_effect = [1, RuntimeError("boom-legame"), 1]

        with self.assertRaises(ServiceError) as exc:
            executor.execute_step(
                lotto_id=9,
                stato_doc_fiscale_id=8,
                tipo_lotto="MASSIVO",
                rollback=False,
                dry_run=False,
            )

        self.assertEqual(exc.exception.code, "E_TASK_FATTURA")
        self.assertEqual(repo.popola_fatture_rettifiche.call_count, 2)
        kwargs = error_logger.log_error.call_args.kwargs
        self.assertEqual(kwargs["scope"], "FATTURA")
        self.assertEqual(kwargs["fattura_id"], 102)

    def test_popola_fatture_rettifiche_dopo_numera_ok(self):
        processi = [
            {"task": "numera_fatture", "fase": "Numerazione", "params": {"implementation_key": "default"}},
            {"task": "popola_fatture_rettifiche", "fase": "Legame documentale note di credito", "params": {"implementation_key": "default"}},
        ]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.side_effect = (
            lambda *, task_code, implementation_key: f"{task_code}_default"
        )
        repo.popola_fatture_rettifiche.return_value = 0

        executor.execute_step(
            lotto_id=1,
            stato_doc_fiscale_id=8,
            tipo_lotto="MASSIVO",
            rollback=False,
            dry_run=False,
        )

        chiamati = [c[0] for c in repo.method_calls]
        self.assertLess(
            chiamati.index("numera_fattura_opz_emessa"),
            chiamati.index("popola_fatture_rettifiche"),
        )

    # Scopo: ⚠️ IL TEST CHE CONTA sull'ordine. Con la proiezione scritta PRIMA
    #        della numerazione, un reset di lotto — che a quel punto e' ancora
    #        ammesso — sbatterebbe su `fk_fatture_ret_fattura`, che non e'
    #        ON DELETE CASCADE, dentro `fn_cleanup_fatture_by_ids`: una
    #        violazione di chiave esterna grezza in una funzione che i suoi
    #        chiamanti danno per infallibile. Il rifiuto deve arrivare PRIMA che
    #        un solo task scriva, cioe' prima della numerazione, che e'
    #        irreversibile.
    def test_popola_fatture_rettifiche_prima_di_numera_rifiutato(self):
        processi = [
            {"task": "popola_fatture_rettifiche", "fase": "Legame documentale note di credito", "params": {"implementation_key": "default"}},
            {"task": "numera_fatture", "fase": "Numerazione", "params": {"implementation_key": "default"}},
        ]
        executor, repo, _, _ = self._build_executor(processi)
        repo.get_task_handler_code.side_effect = (
            lambda *, task_code, implementation_key: f"{task_code}_default"
        )

        with self.assertRaises(ServiceError) as ctx:
            executor.execute_step(
                lotto_id=1,
                stato_doc_fiscale_id=8,
                tipo_lotto="MASSIVO",
                rollback=False,
                dry_run=False,
            )

        self.assertEqual(ctx.exception.code, "E_PIPELINE_VALIDATION")
        self.assertIn("popola_fatture_rettifiche", str(ctx.exception.detail))
        self.assertIn("numera_fatture", str(ctx.exception.detail))
        repo.numera_fattura_opz_emessa.assert_not_called()
        repo.popola_fatture_rettifiche.assert_not_called()

    # Scopo: 🔴 il test che avrebbe intercettato il buco vero. Il seed DB mette
    #        il task nelle pipeline 4 e 6 e la sua `implementation_key` risolve
    #        `popola_fatture_rettifiche_default`: se quel nome non e' nel
    #        registry dell'esecutore, il giro DEFINITIVA numera — irreversibile
    #        — e poi muore con E_TASK_IMPLEMENTATION_NOT_FOUND.
    #        ⚠️ Si leggono gli oggetti REALI, non il mock: la mappa del fixture
    #        e' uno specchio, e uno specchio non prova che l'originale esista.
    def test_popola_fatture_rettifiche_agganciata_al_registry_reale(self):
        from apps.vendite.db.pipeline_repository import VenditePipelineRepository

        executor = PipelineStepExecutor(
            repository=MagicMock(),
            fatture_righe_service=MagicMock(),
            error_logger=MagicMock(),
        )
        self.assertIn("popola_fatture_rettifiche_default", executor.handler_registry)
        self.assertEqual(
            VenditePipelineRepository.ALLOWED_TASK_FUNCTIONS["popola_fatture_rettifiche"],
            "vendite.fn_popola_fatture_rettifiche",
        )
        self.assertEqual(
            PipelineStepExecutor._TASK_ORDER_DEPENDENCIES["popola_fatture_rettifiche"],
            ("numera_fatture",),
        )

    # 44) ⛔ UNA SEGNALAZIONE PER DOCUMENTO, non una sola con una chiave scelta
    #     fra le tante (§6.1 di brief-db-uscita-documento-dal-giro).
    #
    # 🔴 Perche' conta: la segnalazione e' cio' che BLOCCA il lotto, e il verbo
    #    «togli dal giro» la spegne togliendo il suo documento. Se una commessa
    #    ne alimenta due e se ne dichiarasse uno solo, l'altro resterebbe a
    #    bloccare il lotto **per sempre** — e non sarebbe togliibile, perche'
    #    niente lo nomina.
    #
    # ⚠️ Il caso 1:N e' raro e per questo pericoloso: con un documento per
    #    commessa — la norma — un difetto qui non si vedrebbe mai.
    @patch("apps.core.services.fan_out.transaction")
    def test_pull_una_segnalazione_per_documento(self, _mock_txn):
        executor, repo, commesse_repo, error_logger = self._build_executor_pull([10])
        commesse_repo.emit_attivita_fatturabili.side_effect = RuntimeError("emit ko")
        repo.gruppi_di_commessa_nel_lotto.side_effect = (
            lambda lotto_id, commessa_id: ["ORDINE_VENDITA:aaa", "ORDINE_VENDITA:bbb"]
        )

        executor.execute_step(
            lotto_id=1, stato_doc_fiscale_id=2, tipo_lotto="MASSIVO",
            rollback=False, dry_run=False,
        )

        chiavi = [c.kwargs["gruppo_key"] for c in error_logger.log_error.call_args_list]
        self.assertEqual(chiavi, ["ORDINE_VENDITA:aaa", "ORDINE_VENDITA:bbb"])

    # 45) ⚠️ `[]` E' UNA RISPOSTA, e va letta: «questo fallimento non ha un
    #     proprietario in questo lotto» ⇒ UNA riga senza `gruppo_key`, che torna
    #     a valere «e' del giro» e ferma il giro.
    # ⛔ Non zero righe: un fallimento che non blocca niente e' un fallimento
    #    perso — il lotto proseguirebbe come se non fosse successo nulla.
    # ⚠️ E' anche il presidio della trappola del mock: un `MagicMock` nudo si
    #    itera VUOTO, quindi il ciclo non girerebbe e questo test sarebbe l'unico
    #    a dirlo.
    @patch("apps.core.services.fan_out.transaction")
    def test_pull_senza_proprietario_scrive_una_riga_del_giro(self, _mock_txn):
        executor, repo, commesse_repo, error_logger = self._build_executor_pull([10])
        commesse_repo.emit_attivita_fatturabili.side_effect = RuntimeError("emit ko")
        repo.gruppi_di_commessa_nel_lotto.side_effect = (
            lambda lotto_id, commessa_id: []
        )

        executor.execute_step(
            lotto_id=1, stato_doc_fiscale_id=2, tipo_lotto="MASSIVO",
            rollback=False, dry_run=False,
        )

        self.assertEqual(error_logger.log_error.call_count, 1)
        self.assertIsNone(error_logger.log_error.call_args.kwargs["gruppo_key"])

    # 46) ⭐ OGNI SEGNALAZIONE DEL PULL DICHIARA LA COMMESSA (V-7-bis,
    #     brief-db-sorgente-documento-e-riga §8.23): e' la commessa da cui il
    #     pull ricava i documenti, l'unica sede che la sa nel momento del
    #     fallimento. ⚠️ Anche la riga «del giro» (nessun documento) la porta:
    #     la commessa resta vera anche quando il proprietario manca.
    @patch("apps.core.services.fan_out.transaction")
    def test_pull_ogni_segnalazione_dichiara_la_commessa(self, _mock_txn):
        for gruppi in (["ORDINE_VENDITA:aaa", "ORDINE_VENDITA:bbb"], []):
            with self.subTest(gruppi=gruppi):
                executor, repo, commesse_repo, error_logger = self._build_executor_pull([10])
                commesse_repo.emit_attivita_fatturabili.side_effect = RuntimeError("emit ko")
                repo.gruppi_di_commessa_nel_lotto.side_effect = (
                    lambda lotto_id, commessa_id, _g=gruppi: list(_g)
                )

                executor.execute_step(
                    lotto_id=1, stato_doc_fiscale_id=2, tipo_lotto="MASSIVO",
                    rollback=False, dry_run=False,
                )

                commesse = [c.kwargs["commessa_id"] for c in error_logger.log_error.call_args_list]
                self.assertEqual(commesse, [10] * max(len(gruppi), 1))
