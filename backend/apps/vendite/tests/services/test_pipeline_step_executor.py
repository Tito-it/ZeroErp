# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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
"""

from contextlib import nullcontext
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.tests.db_error_fakes import make_db_error
from apps.core.services.service_errors import ServiceError
from apps.vendite.services.pipeline_step_executor import PipelineStepExecutor


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
        commesse_repo = MagicMock()
        commesse_repo.list_commesse_emittibili.return_value = list(commesse_ids)
        executor.commesse_repository = commesse_repo
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

        repo.complete_lotto_task_run.assert_called_once_with(556)
        repo.fail_lotto_task_run.assert_not_called()

    # Scopo: il caso «tutte fallite» resta un RAISE e non un parziale — con zero
    #        commesse emesse proseguire costruirebbe un lotto VUOTO. E' la sola
    #        differenza di policy rispetto ai gemelli snapshot/scadenze, dove il
    #        caso non esiste perche' D-Q lo applica il DB.
    @patch("apps.core.services.fan_out.transaction")
    def test_pull_attivita_da_commessa_tutte_fallite_solleva(self, _mock_txn):
        executor, repo, commesse_repo, _ = self._build_executor_pull([10, 20], task_run_id=557)
        commesse_repo.emit_attivita_fatturabili.side_effect = RuntimeError("emit ko")

        with self.assertRaises(ServiceError) as ctx:
            executor.execute_step(
                lotto_id=1,
                stato_doc_fiscale_id=2,
                tipo_lotto="MASSIVO",
                rollback=False,
                dry_run=False,
            )

        self.assertEqual(ctx.exception.code, "E_PULL_COMMESSA_ALL_FAILED")
        repo.complete_lotto_task_run.assert_not_called()

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
    #        (policy RESUME_STEP) ripete davvero il task invece di saltarlo.
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
