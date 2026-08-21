"""
Indice test eseguiti:
1) LottoPipelineRunnerUnitTests.test_runner_calls_step_executor
2) LottoPipelineRunnerUnitTests.test_runner_wraps_unexpected_error_with_service_error
3) LottoPipelineRunnerUnitTests.test_runner_preserves_service_error_code
4) LottoPipelineRunnerUnitTests.test_runner_does_not_mask_error_when_mark_fails
5) LottoPipelineRunnerUnitTests.test_runner_completed_lotto_reexecutes_pipeline_steps
6) LottoPipelineRunnerUnitTests.test_runner_massivo_error_rerun_resumes_from_current_step
7) LottoPipelineRunnerUnitTests.test_runner_massivo_error_rerun_executes_step_rollback_when_enabled
8) LottoPipelineRunnerUnitTests.test_runner_massivo_error_rerun_skips_destructive_reset_lotto_rollback
9) LottoPipelineRunnerUnitTests.test_runner_blocks_when_lotto_in_esecuzione
10) LottoPipelineRunnerUnitTests.test_runner_closes_lotto_when_stato_has_chiude_lotto_flag
11) LottoPipelineRunnerUnitTests.test_runner_does_not_close_lotto_when_stato_has_no_chiude_lotto_flag
12) LottoPipelineRunnerUnitTests.test_runner_does_not_block_new_lotto_when_initial_state_is_in_esecuzione
13) LottoPipelineRunnerUnitTests.test_runner_blocks_when_lotto_has_critical_signals
14) LottoPipelineRunnerUnitTests.test_runner_blocks_when_fatture_hanno_stato_esecuzione_errore
15) LottoPipelineRunnerUnitTests.test_runner_non_blocca_se_solo_warning_senza_critical_e_senza_stato_errore
16) LottoPipelineRunnerUnitTests.test_runner_emits_pipeline_started_event
17) LottoPipelineRunnerUnitTests.test_runner_emits_pipeline_completed_event
18) LottoPipelineRunnerUnitTests.test_runner_emits_step_completed_event
19) LottoPipelineRunnerUnitTests.test_runner_emits_pipeline_error_event
20) LottoPipelineRunnerUnitTests.test_runner_syncs_fatture_to_step_stato_on_forward
21) LottoPipelineRunnerUnitTests.test_runner_does_not_sync_fatture_in_dry_run
22) test_runner_emits_pipeline_started_event (famiglia eventi, vedi classi sotto)
23) test_until_done_advances_and_stops_at_chiude_lotto (driver F2)
24) test_until_done_ferma_a_stato_richiesto (C-1, FERMATO_A_STATO)
25) test_until_done_stops_on_no_progress_without_chiude_flag
26) test_until_done_existing_lotto_already_at_last_step_no_phantom_step
27) test_until_done_blocked_by_critical_returns_outcome
28) test_runner_rilancio_stesso_step_ammesso_con_criticita (D-Q p.1)
29) test_runner_step_con_fatture_in_errore_marca_lotto_errore (D-Q)
30) test_runner_non_ritira_segnalazioni_senza_step_da_eseguire (D-Q p.2)
31) test_until_done_si_ferma_su_step_con_fatture_in_errore (D-Q, driver)
32) test_until_done_prosegue_dopo_rilancio_riuscito (D-Q, driver)
33) test_lotto_riaperto_rifa_step_corrente (Fase 6)
34) test_lotto_non_riaperto_avanza_allo_step_successivo (Fase 6, controprova)
35) test_lotto_riaperto_azzera_il_segnale_dopo_lo_step (Fase 6)
36) test_lotto_riaperto_non_azzera_se_nessuno_step_eseguito (Fase 6)
37) test_lotto_riaperto_non_innesca_rollback_automatico (Fase 6)
38) test_lotto_riaperto_non_azzera_se_il_giro_non_ha_prodotto_fatture (Fase 6)

Nota Fase 6 (2026-08-03): i test 33-37 presidiano il ritorno del lotto a
DRAFT. Il 33 e il 34 vanno letti in COPPIA: da soli non distinguono un ramo
che discrimina da uno che risponde sempre allo stesso modo.

Nota D-Q (2026-07-31): i test 13-14 ora esercitano il blocco sull'AVANZAMENTO
(lotto esistente → step successivo); il rilancio dello STESSO step con
criticita' attive e' ammesso per disegno (test 28).
"""

from contextlib import contextmanager, nullcontext
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.lotto_segnalazioni_service import LottoSignalStatus
from apps.vendite.services.pipeline_runner import LottoPipelineParams, LottoPipelineRunner


# Scopo: neutralizza la facade transazionale nei unit test (SimpleTestCase, zero
#        DB). Patcha `atomic` E `set_rollback` INSIEME: stubare solo `atomic`
#        lascerebbe `set_rollback` a colpire una connessione senza blocco
#        atomico → TransactionManagementError (regressione 2026-07-22, quando il
#        runner ha iniziato a marcare il rollback del dry-run).
#        Restituisce la lista dei valori passati a `set_rollback`, così i test
#        possono asserire l'invariante «il dry-run non persiste».
@contextmanager
def _fake_tx():
    rollback_calls: list[bool] = []
    with (
        patch(
            "apps.vendite.services.pipeline_runner.transaction.atomic",
            return_value=nullcontext(),
        ),
        patch(
            "apps.vendite.services.pipeline_runner.transaction.set_rollback",
            side_effect=rollback_calls.append,
        ),
    ):
        yield rollback_calls


class LottoPipelineRunnerUnitTests(SimpleTestCase):
    class _RepoMock:
        # Scopo: Recupera `or_create_lotto` dal contesto applicativo o dal database.
        def get_or_create_lotto(self, **kwargs):
            return 10

        # Scopo: Recupera `lotto_tipo` dal contesto applicativo o dal database.
        def get_lotto_tipo(self, lotto_id):
            return "MASSIVO"

        # Scopo: Recupera `stato_doc_fiscale_id` dal contesto applicativo o dal database.
        def get_stato_doc_fiscale_id(self, codice):
            mapping = {
                "DRAFT": 1,
                "EMESSA": 2,
                "INVIATA": 3,
            }
            return mapping.get(codice, 99)

        # Scopo: Recupera `lotto_job_stato` dal contesto applicativo o dal database.
        def get_lotto_job_stato(self, lotto_id):
            return "DRAFT"

        # Scopo: Determina se il lotto e` in errore usando lo stato job persistito.
        def is_lotto_in_errore(self, lotto_id):
            return self.get_lotto_job_stato(lotto_id) == "ERRORE"

        # Scopo: Fase 6 — il lotto e` stato riportato a bozza e non ha ancora
        #        rifatto il giro. Default False: i mock che esercitano la
        #        riapertura lo sovrascrivono.
        def is_lotto_riaperto(self, lotto_id):
            return False

        # Scopo: fatture del lotto. Il default NON e` vuoto perche` il caso
        #        normale e` «il lotto le ha»: e` l'assenza a essere l'eccezione
        #        (giro a vuoto), e la dichiarano i test che la esercitano.
        def list_fatture_by_lotto(self, lotto_id, *, limit=50000):
            return [1]

        # Scopo: Spegne il segnale di riapertura. Registra la chiamata invece di
        #        essere un no-op: «e` stato azzerato» e` proprio cio` che i test
        #        della Fase 6 devono poter asserire.
        # ⚠️ Lista creata pigramente e NON in `__init__`: meta` delle ~20
        #        sottoclassi di questo mock definisce il proprio `__init__`
        #        senza chiamare `super()` (es. `_StatefulRepo`). Un attributo
        #        inizializzato li` sparirebbe su quelle istanze, e il primo test
        #        della Fase 6 che le usasse fallirebbe con un AttributeError che
        #        non parla del difetto vero.
        def azzera_riaperto_il(self, lotto_id):
            if not hasattr(self, "riaperto_azzerato"):
                self.riaperto_azzerato: list[int] = []
            self.riaperto_azzerato.append(lotto_id)

        # Scopo: Recupera `lotto_stato_doc_fiscale_id` dal contesto applicativo o dal database.
        def get_lotto_stato_doc_fiscale_id(self, lotto_id):
            return 1

        # Scopo: Restituisce riepilogo segnalazioni lotto per severita`.
        def get_lotto_segnalazioni_summary(self, lotto_id):
            return {
                "fatture_critical_count": 0,
                "fatture_warning_count": 0,
                "lotto_critical_count": 0,
                "lotto_warning_count": 0,
                "lotto_info_count": 0,
                "fatture_stato_esecuzione_errore_count": 0,
            }

        # Scopo: Aggiorna `lotto_job_stato` con i valori richiesti dal flusso corrente.
        def set_lotto_job_stato(self, lotto_id, stato, messaggio):
            self.last_stato = stato

        # Scopo: Restituisce elenco `pipeline_steps` in base ai filtri disponibili.
        def list_pipeline_steps(self, tipo_lotto, utility_id=None, tipo_doc_fiscale_id=None):
            class _Step:
                # Scopo: Inizializza la istanza.
                def __init__(self, stato_doc_fiscale_id, descrizione, ordine):
                    self.stato_doc_fiscale_id = stato_doc_fiscale_id
                    self.descrizione = descrizione
                    self.ordine = ordine

            return [
                _Step(1, "Step DRAFT", 1),
                _Step(2, "Step EMESSA", 2),
                _Step(8, "Step DEFINITIVA", 3),
            ]

        # Scopo: Gestisce `update_lotto_stato_doc` nel flusso applicativo del modulo.
        def update_lotto_stato_doc(self, lotto_id, stato_doc_fiscale_id):
            return None

        # Scopo: Gestisce `close_giornaliero_lotto` nel flusso applicativo del modulo.
        def close_giornaliero_lotto(self, lotto_id, inviata_id):
            return None

        # Scopo: Recupera `stato_doc_chiude_lotto` dal contesto applicativo o dal database.
        def is_stato_doc_chiude_lotto(self, stato_doc_fiscale_id):
            return False

        # Scopo: Gestisce `close_lotto_operativo` nel flusso applicativo del modulo.
        def close_lotto_operativo(self, lotto_id):
            self.close_lotto_operativo_called = lotto_id
            return None

        # Scopo: Gestisce `log_pipeline_fase` nel flusso applicativo del modulo.
        def log_pipeline_fase(self, **kwargs):
            return None

        # Scopo: Gestisce `log_lotto_esito_fatture` nel flusso applicativo del modulo.
        def log_lotto_esito_fatture(self, lotto_id):
            return None

        # Scopo: Stub del ritiro bandiere BE (D-Q p.2) con tracking chiamate.
        def disattiva_segnalazioni_lotto_be(self, lotto_id):
            self.disattiva_calls = getattr(self, "disattiva_calls", 0) + 1
            return 0

        # Scopo: Stub del ritiro delle marcature per-fattura scritte dal BE.
        #        Registra l'ORDINE rispetto al verdetto: e' l'unica cosa che
        #        conta di questo metodo (vedi il test dedicato).
        def ritira_marcature_fatture_be(self, lotto_id):
            self.eventi = getattr(self, "eventi", [])
            self.eventi.append("ritira")
            return 0

        # Scopo: Stub `sync_lotto_fatture_stato` con tracking delle chiamate (lotto, stato).
        def sync_lotto_fatture_stato(self, *, lotto_id, stato_doc_fiscale_id=None):
            if not hasattr(self, "sync_calls"):
                self.sync_calls = []
            self.sync_calls.append((lotto_id, stato_doc_fiscale_id))
            return None

        # Scopo: Gestisce `log_fatture_lotto` nel flusso applicativo del modulo.
        def log_fatture_lotto(self, **kwargs):
            return None

        # Scopo: Recupera `step_processes` dal contesto applicativo o dal database.
        def get_step_processes(
            self,
            stato_doc_fiscale_id,
            *,
            tipo_lotto,
            utility_id,
            tipo_doc_fiscale_id,
            rollback,
        ):
            if rollback and stato_doc_fiscale_id == 2:
                return [{"task": "reset_lotto_draft", "params": {}}]
            return []

        # Scopo: Gestisce `has_step_processes` nel flusso applicativo del modulo.
        def has_step_processes(
            self,
            *,
            stato_doc_fiscale_id,
            tipo_lotto,
            utility_id,
            tipo_doc_fiscale_id,
            rollback,
        ):
            return rollback and stato_doc_fiscale_id == 2

        # Scopo: Recupera `lotto_context` dal contesto applicativo o dal database.
        def get_lotto_context(self, lotto_id):
            class _Ctx:
                competenza_mese = "2026-01-01"
                tipo_doc_fiscale_id = 1
                utility_id = 1
                billing_account_id = None
                lock_batch_id = None
                emittente_soggetto_ruolo_id = None

            return _Ctx()

        # Scopo: Stub per log_event su event_log.
        def log_event(self, **kwargs):
            return 1

    # Scopo: repo con UN SOLO step (EMESSA/2) da eseguire — usato dalla coppia di
    #        test sulla sync fatture (run vero vs dry-run), che devono differire
    #        SOLO per il flag `dry_run` per essere confrontabili.
    class _SingleEmessaStepRepo(_RepoMock):
        # Scopo: Forza il resolve a tenere lo step EMESSA come unico step da eseguire.
        def get_lotto_stato_doc_fiscale_id(self, lotto_id):
            return None

        # Scopo: Restituisce un solo step EMESSA(2).
        def list_pipeline_steps(self, tipo_lotto, utility_id=None, tipo_doc_fiscale_id=None):
            class _Step:
                # Scopo: Inizializza la istanza.
                def __init__(self, stato_doc_fiscale_id, descrizione, ordine):
                    self.stato_doc_fiscale_id = stato_doc_fiscale_id
                    self.descrizione = descrizione
                    self.ordine = ordine

            return [_Step(2, "Step EMESSA", 1)]

    class _StepExecutorMock:
        # Scopo: Inizializza la istanza.
        def __init__(self):
            self.called = False
            self.last_kwargs = {}
            self.calls = []

        # Scopo: Gestisce `execute_step` nel flusso applicativo del modulo.
        def execute_step(self, **kwargs):
            self.called = True
            self.last_kwargs = kwargs
            self.calls.append(kwargs)

    class _UnexpectedFailingStepExecutorMock:
        # Scopo: Gestisce `execute_step` nel flusso applicativo del modulo.
        def execute_step(self, **kwargs):
            raise RuntimeError("boom")

    class _ServiceFailingStepExecutorMock:
        # Scopo: Gestisce `execute_step` nel flusso applicativo del modulo.
        def execute_step(self, **kwargs):
            raise ServiceError(
                code="E_TASK_NOT_IMPLEMENTED",
                message="Task pipeline non implementato.",
                detail="Task pipeline non implementato: test",
            )

    # Scopo: Verifica il caso `test_runner_calls_step_executor`.
    def test_runner_calls_step_executor(self):
        repo = self._RepoMock()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            result = runner.run_pipeline(LottoPipelineParams(dry_run=True))
        self.assertEqual(result, 10)
        self.assertTrue(step_executor.called)
        self.assertEqual(step_executor.last_kwargs["tipo_lotto"], "MASSIVO")

    # Scopo: Verifica il caso `test_runner_wraps_unexpected_error_with_service_error`.
    def test_runner_wraps_unexpected_error_with_service_error(self):
        repo = self._RepoMock()
        step_executor = self._UnexpectedFailingStepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            with self.assertRaises(ServiceError) as exc:
                runner.run_pipeline(LottoPipelineParams(dry_run=False))
        self.assertEqual(exc.exception.code, "E_PIPELINE")
        self.assertIsInstance(exc.exception.__cause__, RuntimeError)
        self.assertEqual(repo.last_stato, "ERRORE")

    # Scopo: Verifica il caso `test_runner_preserves_service_error_code`.
    def test_runner_preserves_service_error_code(self):
        repo = self._RepoMock()
        step_executor = self._ServiceFailingStepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            with self.assertRaises(ServiceError) as exc:
                runner.run_pipeline(LottoPipelineParams(dry_run=False))
        self.assertEqual(exc.exception.code, "E_TASK_NOT_IMPLEMENTED")
        self.assertEqual(repo.last_stato, "ERRORE")

    # Scopo: 🔴 LA BANDIERA SI ABBASSA PRIMA DEL VERDETTO — il presidio della
    #        porta a senso unico.
    #
    #        Dal 2026-08-21 il BE marca le fatture fallite perché l'operatore
    #        legga il motivo sulla riga. Quelle marcature entrano nella guardia
    #        unificata PRE-1 (`blocks_next_step` conta critici **e** righe in
    #        ERRORE): se il verdetto le vedesse ancora alzate dal tentativo
    #        precedente, il primo fallimento chiuderebbe il lotto per sempre —
    #        l'operatore corregge la causa, ripreme «Rendi definitive» e trova
    #        «Lotto bloccato per segnalazioni critiche attive», un messaggio
    #        che parla d'altro.
    #
    #        ⚠️ Il test guarda l'ORDINE, non l'effetto: l'effetto è un conteggio
    #        del database. È l'ordine la cosa fragile — invertirlo non rompe
    #        niente di visibile e rimette in scena esattamente quel difetto.
    def test_ritira_le_proprie_marcature_prima_di_chiedere_il_verdetto(self):
        eventi = []

        class _RepoOrdine(self._RepoMock):
            def ritira_marcature_fatture_be(self, lotto_id):
                eventi.append("ritira")
                return 0

        class _ServizioSegnalazioni:
            def evaluate_lotto_status(self, lotto_id):
                eventi.append("verdetto")
                return LottoSignalStatus(
                    critical_count=0, warning_count=0, attention_count=0,
                    fatture_stato_esecuzione_errore_count=0,
                    is_error=False, blocks_next_step=False, summary={},
                )

        runner = LottoPipelineRunner(
            repository=_RepoOrdine(), step_executor=self._StepExecutorMock(),
        )
        runner.lotto_segnalazioni_service = _ServizioSegnalazioni()
        with _fake_tx():
            runner.run_pipeline(LottoPipelineParams(dry_run=False))

        self.assertEqual(eventi[:2], ["ritira", "verdetto"])

    # Scopo: ⭐ IL FALLIMENTO RESTA ATTACCATO ALLA RIGA — e la scrittura avviene
    #        FUORI dalla transazione dello step, che e' l'unica ragione per cui
    #        sopravvive.
    #
    #        Il giro per-fattura e' fail-fast: rilancia, e lo step viene
    #        annullato. Una riga di log scritta li' dentro spariva col rollback
    #        insieme all'errore che descriveva — misurato in-app il 2026-08-21:
    #        il toast diceva il motivo, e un minuto dopo il motivo non esisteva
    #        piu' da nessuna parte (`stato_esecuzione` restava 'COMPLETED',
    #        `fatture_log` vuoto). Il valore 'ERRORE' era nel CHECK della
    #        tabella dal primo giorno e non lo scriveva nessuno.
    #
    #        ⚠️ Il `fattura_id` arriva dal `context` del ServiceError: e' il
    #        canale che `_run_per_fattura_task` riempie gia' per il diario.
    def test_runner_attacca_l_errore_alla_fattura_che_lo_ha_causato(self):
        class _RepoConMarca(self._RepoMock):
            marcate = None

            def marca_fattura_in_errore(self, *, lotto_id, fattura_id, code, messaggio, meta=None):
                self.marcate = {
                    "lotto_id": lotto_id, "fattura_id": fattura_id,
                    "code": code, "messaggio": messaggio,
                }

        class _StepConErroreDiFattura:
            def execute_step(self, **kwargs):
                raise ServiceError(
                    code="E_FATTURA_RETTIFICATA_SENZA_NUMERO",
                    message="Non si puo' numerare il documento 15353: ...",
                    detail="Task numera_fatture fallito su fattura_id=15353",
                    context={"lotto_id": 6034, "fattura_id": 15353, "task": "numera_fatture"},
                )

        repo = _RepoConMarca()
        runner = LottoPipelineRunner(repository=repo, step_executor=_StepConErroreDiFattura())
        with _fake_tx():
            with self.assertRaises(ServiceError):
                runner.run_pipeline(LottoPipelineParams(dry_run=False))

        self.assertIsNotNone(repo.marcate, "il fallimento non e' stato attaccato alla riga")
        self.assertEqual(repo.marcate["fattura_id"], 15353)
        self.assertEqual(repo.marcate["code"], "E_FATTURA_RETTIFICATA_SENZA_NUMERO")
        self.assertIn("15353", repo.marcate["messaggio"])

    # Scopo: un errore di LOTTO non ha una riga a cui attaccarsi, e non deve
    #        inventarsene una. Senza questo ramo il `context` senza
    #        `fattura_id` finirebbe in una marcatura su `None`.
    def test_errore_senza_fattura_non_marca_nessuna_riga(self):
        class _RepoConMarca(self._RepoMock):
            chiamate = 0

            def marca_fattura_in_errore(self, **kwargs):
                self.chiamate += 1

        repo = _RepoConMarca()
        runner = LottoPipelineRunner(
            repository=repo, step_executor=self._ServiceFailingStepExecutorMock(),
        )
        with _fake_tx():
            with self.assertRaises(ServiceError):
                runner.run_pipeline(LottoPipelineParams(dry_run=False))
        self.assertEqual(repo.chiamate, 0)

    # Scopo: la marcatura e' best-effort come il gemello sul lotto: se fallisce
    #        NON deve mascherare l'eccezione vera, che e' l'unica cosa che
    #        l'operatore sta aspettando.
    def test_marcatura_fallita_non_maschera_l_errore_vero(self):
        class _RepoRotto(self._RepoMock):
            def marca_fattura_in_errore(self, **kwargs):
                raise RuntimeError("marca-fallita")

        class _StepConErroreDiFattura:
            def execute_step(self, **kwargs):
                raise ServiceError(
                    code="E_FATTURA_RETTIFICATA_SENZA_NUMERO",
                    message="msg",
                    detail="d",
                    context={"fattura_id": 15353},
                )

        runner = LottoPipelineRunner(
            repository=_RepoRotto(), step_executor=_StepConErroreDiFattura(),
        )
        with _fake_tx():
            with self.assertRaises(ServiceError) as exc:
                runner.run_pipeline(LottoPipelineParams(dry_run=False))
        self.assertEqual(exc.exception.code, "E_FATTURA_RETTIFICATA_SENZA_NUMERO")

    # Scopo: Verifica il caso `test_runner_does_not_mask_error_when_mark_fails`.
    def test_runner_does_not_mask_error_when_mark_fails(self):
        class _FailingMarkRepo(self._RepoMock):
            # Scopo: Aggiorna `lotto_job_stato` con i valori richiesti dal flusso corrente.
            def set_lotto_job_stato(self, lotto_id, stato, messaggio):
                if stato == "ERRORE":
                    raise RuntimeError("mark-failed")
                self.last_stato = stato

        repo = _FailingMarkRepo()
        step_executor = self._ServiceFailingStepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            with self.assertRaises(ServiceError) as exc:
                runner.run_pipeline(LottoPipelineParams(dry_run=False))
        self.assertEqual(exc.exception.code, "E_TASK_NOT_IMPLEMENTED")

    # Scopo: Verifica il caso `test_runner_completed_lotto_reexecutes_pipeline_steps`.
    def test_runner_completed_lotto_reexecutes_pipeline_steps(self):
        class _CompletedRepo(self._RepoMock):
            # Scopo: Recupera `lotto_job_stato` dal contesto applicativo o dal database.
            def get_lotto_job_stato(self, lotto_id):
                return "COMPLETATO"

        repo = _CompletedRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            result = runner.run_pipeline(LottoPipelineParams(lotto_id=0, dry_run=True))
        self.assertEqual(result, 10)
        self.assertEqual(len(step_executor.calls), 1)
        self.assertEqual(step_executor.calls[0]["stato_doc_fiscale_id"], 1)

    # Scopo: Verifica il caso `test_runner_massivo_error_rerun_resumes_from_current_step`.
    def test_runner_massivo_error_rerun_resumes_from_current_step(self):
        class _ErroredRepo(self._RepoMock):
            # Scopo: Recupera `lotto_job_stato` dal contesto applicativo o dal database.
            def get_lotto_job_stato(self, lotto_id):
                return "ERRORE"

            # Scopo: Recupera `lotto_stato_doc_fiscale_id` dal contesto applicativo o dal database.
            def get_lotto_stato_doc_fiscale_id(self, lotto_id):
                return 8

        repo = _ErroredRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            result = runner.run_pipeline(LottoPipelineParams(dry_run=True, tipo_lotto="MASSIVO"))
        self.assertEqual(result, 10)
        self.assertEqual(len(step_executor.calls), 1)
        self.assertEqual(step_executor.calls[0]["stato_doc_fiscale_id"], 8)
        self.assertFalse(step_executor.calls[0]["rollback"])

    # Scopo: Verifica il caso `test_runner_massivo_error_rerun_executes_step_rollback_when_enabled`.
    def test_runner_massivo_error_rerun_executes_step_rollback_when_enabled(self):
        class _ErroredRepo(self._RepoMock):
            # Scopo: Recupera `lotto_job_stato` dal contesto applicativo o dal database.
            def get_lotto_job_stato(self, lotto_id):
                return "ERRORE"

            # Scopo: Recupera `lotto_stato_doc_fiscale_id` dal contesto applicativo o dal database.
            def get_lotto_stato_doc_fiscale_id(self, lotto_id):
                return 2

            # Scopo: Recupera `step_processes` dal contesto applicativo o dal database.
            def get_step_processes(
                self,
                stato_doc_fiscale_id,
                *,
                tipo_lotto,
                utility_id,
                tipo_doc_fiscale_id,
                rollback,
            ):
                if rollback and stato_doc_fiscale_id == 2:
                    return [{"task": "noop", "params": {}}]
                return []

        repo = _ErroredRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            result = runner.run_pipeline(
                LottoPipelineParams(
                    dry_run=True,
                    tipo_lotto="MASSIVO",
                    meta={"auto_step_rollback": True},
                )
            )
        self.assertEqual(result, 10)
        self.assertEqual(len(step_executor.calls), 2)
        self.assertEqual(step_executor.calls[0]["stato_doc_fiscale_id"], 2)
        self.assertTrue(step_executor.calls[0]["rollback"])
        self.assertEqual(step_executor.calls[1]["stato_doc_fiscale_id"], 2)
        self.assertFalse(step_executor.calls[1]["rollback"])

    # Scopo: Verifica il caso `test_runner_massivo_error_rerun_skips_destructive_reset_lotto_rollback`.
    def test_runner_massivo_error_rerun_skips_destructive_reset_lotto_rollback(self):
        class _ErroredRepo(self._RepoMock):
            # Scopo: Recupera `lotto_job_stato` dal contesto applicativo o dal database.
            def get_lotto_job_stato(self, lotto_id):
                return "ERRORE"

            # Scopo: Recupera `lotto_stato_doc_fiscale_id` dal contesto applicativo o dal database.
            def get_lotto_stato_doc_fiscale_id(self, lotto_id):
                return 2

        repo = _ErroredRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            result = runner.run_pipeline(
                LottoPipelineParams(
                    dry_run=True,
                    tipo_lotto="MASSIVO",
                    meta={"auto_step_rollback": True},
                )
            )
        self.assertEqual(result, 10)
        self.assertEqual(len(step_executor.calls), 1)
        self.assertEqual(step_executor.calls[0]["stato_doc_fiscale_id"], 2)
        self.assertFalse(step_executor.calls[0]["rollback"])

    # Scopo: Verifica il caso `test_runner_blocks_when_lotto_in_esecuzione`.
    def test_runner_blocks_when_lotto_in_esecuzione(self):
        class _RunningRepo(self._RepoMock):
            # Scopo: Recupera `lotto_job_stato` dal contesto applicativo o dal database.
            def get_lotto_job_stato(self, lotto_id):
                return "IN_ESECUZIONE"

        repo = _RunningRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            with self.assertRaises(ServiceError) as exc:
                runner.run_pipeline(LottoPipelineParams(lotto_id=10, dry_run=True))
        self.assertEqual(exc.exception.code, "E_PIPELINE_LOTTO_IN_ESECUZIONE")
        self.assertFalse(step_executor.called)

    # Scopo: Verifica il caso `test_runner_closes_lotto_when_stato_has_chiude_lotto_flag`.
    def test_runner_closes_lotto_when_stato_has_chiude_lotto_flag(self):
        class _CloseByFlagRepo(self._RepoMock):
            # Scopo: Recupera `stato_doc_chiude_lotto` dal contesto applicativo o dal database.
            def is_stato_doc_chiude_lotto(self, stato_doc_fiscale_id):
                return stato_doc_fiscale_id == 8

            # Scopo: Restituisce elenco `pipeline_steps` in base ai filtri disponibili.
            def list_pipeline_steps(self, tipo_lotto, utility_id=None, tipo_doc_fiscale_id=None):
                class _Step:
                    # Scopo: Inizializza la istanza.
                    def __init__(self, stato_doc_fiscale_id, descrizione, ordine):
                        self.stato_doc_fiscale_id = stato_doc_fiscale_id
                        self.descrizione = descrizione
                        self.ordine = ordine

                return [_Step(8, "Step DEFINITIVA", 1)]

        repo = _CloseByFlagRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            result = runner.run_pipeline(LottoPipelineParams(dry_run=False))
        self.assertEqual(result, 10)
        self.assertEqual(getattr(repo, "close_lotto_operativo_called", None), 10)

    # Scopo: Verifica il caso `test_runner_does_not_close_lotto_when_stato_has_no_chiude_lotto_flag`.
    def test_runner_does_not_close_lotto_when_stato_has_no_chiude_lotto_flag(self):
        class _NoCloseByFlagRepo(self._RepoMock):
            # Scopo: Recupera `stato_doc_chiude_lotto` dal contesto applicativo o dal database.
            def is_stato_doc_chiude_lotto(self, stato_doc_fiscale_id):
                return False

            # Scopo: Restituisce elenco `pipeline_steps` in base ai filtri disponibili.
            def list_pipeline_steps(self, tipo_lotto, utility_id=None, tipo_doc_fiscale_id=None):
                class _Step:
                    # Scopo: Inizializza la istanza.
                    def __init__(self, stato_doc_fiscale_id, descrizione, ordine):
                        self.stato_doc_fiscale_id = stato_doc_fiscale_id
                        self.descrizione = descrizione
                        self.ordine = ordine

                return [_Step(1, "Step DRAFT", 1)]

        repo = _NoCloseByFlagRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            result = runner.run_pipeline(LottoPipelineParams(dry_run=False))
        self.assertEqual(result, 10)
        self.assertIsNone(getattr(repo, "close_lotto_operativo_called", None))

    # Scopo: Verifica che dopo lo step (forward, non dry-run) le fatture vengano
    # sincronizzate allo stato_doc_fiscale_id dello step (es. EMESSA/2), così la
    # fattura segue il lotto e non salta a DEFINITIVA/8 violando la matrice.
    def test_runner_syncs_fatture_to_step_stato_on_forward(self):
        repo = self._SingleEmessaStepRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx() as rollback_calls:
            result = runner.run_pipeline(LottoPipelineParams(dry_run=False))
        self.assertEqual(result, 10)
        # La fattura viene allineata allo stato dello step (lotto 10, stato 2).
        self.assertEqual(getattr(repo, "sync_calls", []), [(10, 2)])
        # Run vero: la fase NON va mai marcata per il rollback (deve committare).
        self.assertEqual(rollback_calls, [])

    # Scopo: DRY-RUN — la sync fatture viene eseguita COME nel run vero (la coppia
    #        stato-lotto + stato-fatture è indivisibile: separarle è ciò che ha
    #        prodotto i lotti 106/107, lotto EMESSA con fatture DRAFT), ma
    #        l'intera fase è marcata per il ROLLBACK, quindi non persiste nulla.
    #        Regressione storica: qui si asseriva `sync_calls == []`, cioè
    #        esattamente il comportamento che generava l'incoerenza.
    def test_runner_dry_run_sincronizza_ma_non_persiste(self):
        # Stesso repo del gemello `..._syncs_fatture_to_step_stato_on_forward`:
        # l'unica differenza fra i due test è `dry_run`.
        repo = self._SingleEmessaStepRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx() as rollback_calls:
            result = runner.run_pipeline(LottoPipelineParams(dry_run=True))
        self.assertEqual(result, 10)
        # Stato lotto e stato fatture avanzano INSIEME anche in dry-run —
        # identico al run vero (la coppia è indivisibile)...
        self.assertEqual(getattr(repo, "sync_calls", []), [(10, 2)])
        # ...ma la fase viene marcata per il rollback: nessuna scrittura persiste.
        self.assertEqual(rollback_calls, [True])

    # Scopo: Verifica il caso `test_runner_does_not_block_new_lotto_when_initial_state_is_in_esecuzione`.
    def test_runner_does_not_block_new_lotto_when_initial_state_is_in_esecuzione(self):
        class _NewLottoInEsecuzioneRepo(self._RepoMock):
            # Scopo: Recupera `lotto_job_stato` dal contesto applicativo o dal database.
            def get_lotto_job_stato(self, lotto_id):
                return "IN_ESECUZIONE"

        repo = _NewLottoInEsecuzioneRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            result = runner.run_pipeline(LottoPipelineParams(lotto_id=0, dry_run=True))
        self.assertEqual(result, 10)
        self.assertTrue(step_executor.called)

    # Scopo: Verifica il caso `test_runner_blocks_when_lotto_has_critical_signals`.
    def test_runner_blocks_when_lotto_has_critical_signals(self):
        class _CriticalSignalsRepo(self._RepoMock):
            # Scopo: Restituisce riepilogo segnalazioni lotto per severita`.
            def get_lotto_segnalazioni_summary(self, lotto_id):
                return {
                    "fatture_critical_count": 1,
                    "fatture_warning_count": 0,
                    "lotto_critical_count": 0,
                    "lotto_warning_count": 0,
                    "lotto_info_count": 0,
                    "fatture_stato_esecuzione_errore_count": 0,
                }

        # D-Q p.1: il blocco vale per l'AVANZAMENTO. Lotto ESISTENTE (non in
        # errore) su stato 1 → step selezionato = 2 (successivo) → bloccato.
        # Un run che ricadesse sullo stesso step sarebbe invece un rilancio,
        # ammesso (vedi test dedicato).
        repo = _CriticalSignalsRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            with self.assertRaises(ServiceError) as exc:
                runner.run_pipeline(LottoPipelineParams(lotto_id=10, dry_run=False))
        self.assertEqual(exc.exception.code, "E_PIPELINE_LOTTO_CRITICAL")
        self.assertFalse(step_executor.called)

    # Scopo: Verifica che il runner blocchi quando la tabella ponte ha fatture con stato_esecuzione=ERRORE,
    # anche in assenza di segnalazioni critical nei log (guard unificata PRE-1).
    def test_runner_blocks_when_fatture_hanno_stato_esecuzione_errore(self):
        class _StatoEsecuzioneErroreRepo(self._RepoMock):
            # Scopo: Restituisce riepilogo con fatture in stato errore per test blocco.
            def get_lotto_segnalazioni_summary(self, lotto_id):
                return {
                    "fatture_critical_count": 0,
                    "fatture_warning_count": 0,
                    "lotto_critical_count": 0,
                    "lotto_warning_count": 0,
                    "lotto_info_count": 0,
                    "fatture_stato_esecuzione_errore_count": 2,
                }

        # Come sopra: lotto ESISTENTE che tenterebbe l'avanzamento allo step 2.
        repo = _StatoEsecuzioneErroreRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            with self.assertRaises(ServiceError) as exc:
                runner.run_pipeline(LottoPipelineParams(lotto_id=10, dry_run=False))
        self.assertEqual(exc.exception.code, "E_PIPELINE_LOTTO_CRITICAL")
        self.assertFalse(step_executor.called)

    # Scopo: D-Q p.1 — il RILANCIO dello STESSO step e' ammesso anche con
    #        criticita' attive: e' la via d'uscita (correggi → rilancia lo
    #        step). Lotto MASSIVO in errore su stato 1 → step selezionato = 1
    #        (corrente) → il gate non scatta e lo step viene eseguito.
    #        A fine step le criticita' sono ancora attive → il lotto resta
    #        marcato ERRORE (non un falso COMPLETATO).
    def test_runner_rilancio_stesso_step_ammesso_con_criticita(self):
        class _ErroreRerunRepo(self._RepoMock):
            # Scopo: lotto in errore (abilita il resume sullo step corrente).
            def get_lotto_job_stato(self, lotto_id):
                return "ERRORE"

            # Scopo: criticita' attive prima E dopo lo step.
            def get_lotto_segnalazioni_summary(self, lotto_id):
                return {
                    "fatture_critical_count": 1,
                    "fatture_warning_count": 0,
                    "lotto_critical_count": 0,
                    "lotto_warning_count": 0,
                    "lotto_info_count": 0,
                    "fatture_stato_esecuzione_errore_count": 1,
                }

        repo = _ErroreRerunRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            result = runner.run_pipeline(LottoPipelineParams(lotto_id=10, dry_run=False))
        self.assertEqual(result, 10)
        self.assertTrue(step_executor.called)
        # Il ritiro bandiere BE e' avvenuto prima dello step (D-Q p.2).
        self.assertEqual(getattr(repo, "disattiva_calls", 0), 1)
        # Fatture ancora in errore a fine step → lotto marcato ERRORE.
        self.assertEqual(repo.last_stato, "ERRORE")

    # Scopo: D-Q — a fine step, se le fatture risultano in errore (il task le ha
    #        marcate senza fermare il giro), il lotto va in ERRORE e non in
    #        COMPLETATO: e' cio' che rende il run successivo un rilancio dello
    #        stesso step. Gate pulito all'avvio (nessuna criticita'), errore
    #        comparso DURANTE lo step: la summary e' stateful.
    def test_runner_step_con_fatture_in_errore_marca_lotto_errore(self):
        class _ErroreDuranteStepRepo(self._RepoMock):
            # Scopo: prima valutazione pulita (gate), seconda con errori (esito).
            def get_lotto_segnalazioni_summary(self, lotto_id):
                self.summary_calls = getattr(self, "summary_calls", 0) + 1
                errore = self.summary_calls > 1
                return {
                    "fatture_critical_count": 1 if errore else 0,
                    "fatture_warning_count": 0,
                    "lotto_critical_count": 0,
                    "lotto_warning_count": 0,
                    "lotto_info_count": 0,
                    "fatture_stato_esecuzione_errore_count": 1 if errore else 0,
                }

        repo = _ErroreDuranteStepRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            result = runner.run_pipeline(LottoPipelineParams(dry_run=False))
        self.assertEqual(result, 10)
        self.assertTrue(step_executor.called)
        self.assertEqual(repo.last_stato, "ERRORE")

    # Scopo: D-Q p.2 — nessun ritiro bandiere quando non c'e' NESSUNO step da
    #        eseguire (lotto gia' all'ultimo step): il run non deve toccare le
    #        segnalazioni di un lavoro che non sta facendo.
    def test_runner_non_ritira_segnalazioni_senza_step_da_eseguire(self):
        class _UltimoStepRepo(self._RepoMock):
            # Scopo: lotto gia' sull'ultimo step del catalogo (8).
            def get_lotto_stato_doc_fiscale_id(self, lotto_id):
                return 8

        repo = _UltimoStepRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            runner.run_pipeline(LottoPipelineParams(lotto_id=10, dry_run=False))
        self.assertEqual(getattr(repo, "disattiva_calls", 0), 0)
        self.assertFalse(step_executor.called)

    # Scopo: Verifica che la sola presenza di warning (senza critical e senza stato_esecuzione=ERRORE)
    # non blocchi il runner (partial failure non bloccante).
    def test_runner_non_blocca_se_solo_warning_senza_critical_e_senza_stato_errore(self):
        class _OnlyWarningsRepo(self._RepoMock):
            # Scopo: Restituisce riepilogo segnalazioni lotto per severita`.
            def get_lotto_segnalazioni_summary(self, lotto_id):
                return {
                    "fatture_critical_count": 0,
                    "fatture_warning_count": 3,
                    "lotto_critical_count": 0,
                    "lotto_warning_count": 1,
                    "lotto_info_count": 0,
                    "fatture_stato_esecuzione_errore_count": 0,
                }

        repo = _OnlyWarningsRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            result = runner.run_pipeline(LottoPipelineParams(dry_run=True))
        self.assertEqual(result, 10)
        self.assertTrue(step_executor.called)

    # Scopo: Verifica che run_pipeline emetta PIPELINE_STARTED su event_log.
    def test_runner_emits_pipeline_started_event(self):
        repo = MagicMock(wraps=self._RepoMock())
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            runner.run_pipeline(LottoPipelineParams(dry_run=True))
        started_calls = [
            c for c in repo.log_event.call_args_list
            if c.kwargs.get("event_code") == "PIPELINE_STARTED"
        ]
        self.assertEqual(len(started_calls), 1)
        self.assertEqual(started_calls[0].kwargs["domain"], "PIPELINE")
        self.assertEqual(started_calls[0].kwargs["entity_type"], "LOTTO")
        self.assertEqual(started_calls[0].kwargs["entity_id"], 10)

    # Scopo: Verifica che run_pipeline emetta PIPELINE_COMPLETED su event_log.
    def test_runner_emits_pipeline_completed_event(self):
        repo = MagicMock(wraps=self._RepoMock())
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            runner.run_pipeline(LottoPipelineParams(dry_run=True))
        completed_calls = [
            c for c in repo.log_event.call_args_list
            if c.kwargs.get("event_code") == "PIPELINE_COMPLETED"
        ]
        self.assertEqual(len(completed_calls), 1)
        self.assertEqual(completed_calls[0].kwargs["domain"], "PIPELINE")
        self.assertEqual(completed_calls[0].kwargs["payload"]["tipo_lotto"], "MASSIVO")

    # Scopo: Verifica che _execute_pipeline_step emetta STEP_COMPLETED su event_log.
    def test_runner_emits_step_completed_event(self):
        repo = MagicMock(wraps=self._RepoMock())
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            runner.run_pipeline(LottoPipelineParams(dry_run=True))
        step_calls = [
            c for c in repo.log_event.call_args_list
            if c.kwargs.get("event_code") == "STEP_COMPLETED"
        ]
        self.assertEqual(len(step_calls), 1)
        self.assertEqual(step_calls[0].kwargs["payload"]["stato_doc_fiscale_id"], 1)

    # Scopo: Verifica che un errore pipeline emetta PIPELINE_ERROR su event_log.
    def test_runner_emits_pipeline_error_event(self):
        repo = MagicMock(wraps=self._RepoMock())
        step_executor = self._UnexpectedFailingStepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            with self.assertRaises(ServiceError):
                runner.run_pipeline(LottoPipelineParams(dry_run=False))
        error_calls = [
            c for c in repo.log_event.call_args_list
            if c.kwargs.get("event_code") == "PIPELINE_ERROR"
        ]
        self.assertEqual(len(error_calls), 1)
        self.assertEqual(error_calls[0].kwargs["severity"], "ERROR")
        self.assertEqual(error_calls[0].kwargs["domain"], "PIPELINE")

    # Scopo: F1 — su lotto ESISTENTE in successo, il runner AVANZA allo step
    # successivo a quello corrente (non ri-esegue il primo). Catalogo [1,2,8],
    # stato corrente 1 → esegue lo step 2.
    def test_runner_existing_lotto_success_advances_to_next_step(self):
        repo = self._RepoMock()  # job_stato "DRAFT" (non ERRORE), stato_doc corrente 1
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            result = runner.run_pipeline(LottoPipelineParams(lotto_id=10, dry_run=True))
        self.assertEqual(result, 10)
        self.assertEqual(len(step_executor.calls), 1)
        # Avanzamento: NON il primo step (1) ma il successivo (2).
        self.assertEqual(step_executor.calls[0]["stato_doc_fiscale_id"], 2)

    # Scopo: F1 — su lotto ESISTENTE in successo gia` all'ultimo step del catalogo,
    # non resta nulla da eseguire: nessuno step e il lotto risulta COMPLETATO.
    def test_runner_existing_lotto_success_at_last_step_is_noop(self):
        class _AtLastStepRepo(self._RepoMock):
            # Scopo: stato corrente = ultimo step del catalogo (8).
            def get_lotto_stato_doc_fiscale_id(self, lotto_id):
                return 8

        repo = _AtLastStepRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            result = runner.run_pipeline(LottoPipelineParams(lotto_id=10, dry_run=True))
        self.assertEqual(result, 10)
        self.assertEqual(len(step_executor.calls), 0)
        self.assertEqual(repo.last_stato, "COMPLETATO")

    # --- F2: driver run_lotto_until_done ---

    # Repo stateful: lo stato_doc avanza man mano che update_lotto_stato_doc viene
    # chiamato, così il loop del driver progredisce realmente tra le iterazioni.
    class _StatefulRepo(_RepoMock):
        # Scopo: stato corrente del lotto, mutato dal runner ad ogni step.
        def __init__(self, chiude_su=8):
            self.current = None
            self.last_stato = None
            self._chiude_su = chiude_su

        def get_lotto_stato_doc_fiscale_id(self, lotto_id):
            return self.current

        def update_lotto_stato_doc(self, lotto_id, stato_doc_fiscale_id):
            self.current = stato_doc_fiscale_id

        def is_stato_doc_chiude_lotto(self, stato_doc_fiscale_id):
            return self._chiude_su is not None and stato_doc_fiscale_id == self._chiude_su

    # Scopo: F2 — il driver concatena gli step del catalogo [1,2,8] e si ferma allo
    # step di chiusura (chiude_lotto su 8): 3 step eseguiti, esito COMPLETATO.
    def test_until_done_advances_and_stops_at_chiude_lotto(self):
        repo = self._StatefulRepo(chiude_su=8)
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx() as rollback_calls:
            esito = runner.run_lotto_until_done(LottoPipelineParams(dry_run=True))
        self.assertEqual(esito["lotto_id"], 10)
        self.assertEqual(esito["step_eseguiti"], 3)
        self.assertEqual(esito["motivo_stop"], "COMPLETATO")
        self.assertEqual(esito["stato_doc_fiscale_id"], 8)
        self.assertEqual([c["stato_doc_fiscale_id"] for c in step_executor.calls], [1, 2, 8])
        # DRY-RUN a livello driver: la catena INTERA viene simulata dentro una
        # sola transazione marcata per rollback UNA volta a fine corsa. Un
        # rollback per-step ([True, True, True]) sarebbe la regressione che
        # impedisce alla catena di avanzare (uscita immediata «COMPLETATO»/0).
        self.assertEqual(rollback_calls, [True])

    # Scopo: C-1 (gate fiscale D-1) — con fino_a_stato_doc_fiscale_id=2 (EMESSA)
    # il driver si FERMA allo stato richiesto senza eseguire lo step DEFINITIVA:
    # 2 step eseguiti [1,2], motivo FERMATO_A_STATO.
    def test_until_done_ferma_a_stato_richiesto(self):
        repo = self._StatefulRepo(chiude_su=8)
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            esito = runner.run_lotto_until_done(
                LottoPipelineParams(dry_run=True, fino_a_stato_doc_fiscale_id=2)
            )
        self.assertEqual(esito["lotto_id"], 10)
        self.assertEqual(esito["step_eseguiti"], 2)
        self.assertEqual(esito["motivo_stop"], "FERMATO_A_STATO")
        self.assertEqual(esito["stato_doc_fiscale_id"], 2)
        self.assertEqual([c["stato_doc_fiscale_id"] for c in step_executor.calls], [1, 2])

    # Scopo: F2 — senza flag chiude_lotto, il driver si ferma per "nessun avanzamento"
    # una volta esaurito il catalogo (3 step eseguiti), esito COMPLETATO.
    def test_until_done_stops_on_no_progress_without_chiude_flag(self):
        repo = self._StatefulRepo(chiude_su=None)
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            esito = runner.run_lotto_until_done(LottoPipelineParams(dry_run=True))
        self.assertEqual(esito["step_eseguiti"], 3)
        self.assertEqual(esito["motivo_stop"], "COMPLETATO")
        self.assertEqual([c["stato_doc_fiscale_id"] for c in step_executor.calls], [1, 2, 8])

    # Scopo: F2 (regressione bug step fantasma) — su lotto ESISTENTE già all'ultimo
    # step, il driver NON conta step inesistenti: 0 step, esito COMPLETATO.
    def test_until_done_existing_lotto_already_at_last_step_no_phantom_step(self):
        repo = self._StatefulRepo(chiude_su=8)
        repo.current = 8  # già all'ultimo step del catalogo [1,2,8]
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            esito = runner.run_lotto_until_done(LottoPipelineParams(lotto_id=10, dry_run=True))
        self.assertEqual(esito["lotto_id"], 10)
        self.assertEqual(esito["step_eseguiti"], 0)
        self.assertEqual(esito["motivo_stop"], "COMPLETATO")
        self.assertEqual(len(step_executor.calls), 0)

    # Scopo: F2 — su lotto ESISTENTE con segnalazioni critical il driver non esegue
    # step e ritorna un esito BLOCCATO_CRITICITA (no eccezione propagata).
    def test_until_done_blocked_by_critical_returns_outcome(self):
        class _CriticalRepo(self._StatefulRepo):
            # Scopo: riepilogo con criticità attive → blocks_next_step.
            def get_lotto_segnalazioni_summary(self, lotto_id):
                return {
                    "fatture_critical_count": 1,
                    "fatture_warning_count": 0,
                    "lotto_critical_count": 0,
                    "lotto_warning_count": 0,
                    "lotto_info_count": 0,
                    "fatture_stato_esecuzione_errore_count": 0,
                }

        repo = _CriticalRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx() as rollback_calls:
            esito = runner.run_lotto_until_done(LottoPipelineParams(lotto_id=10, dry_run=False))
        self.assertEqual(esito["lotto_id"], 10)
        self.assertEqual(esito["step_eseguiti"], 0)
        self.assertEqual(esito["motivo_stop"], "BLOCCATO_CRITICITA")
        self.assertEqual(len(step_executor.calls), 0)
        # Run vero (dry_run=False): il driver non marca MAI il rollback.
        self.assertEqual(rollback_calls, [])

    # Scopo: D-Q — lo step si completa ma alcune fatture restano in errore
    #        (marcate dal task senza fermare il giro): il driver NON itera sullo
    #        stesso step con dati identici — si ferma con motivo parlante
    #        BLOCCATO_CRITICITA e l'errore strutturato, contando lo step
    #        eseguito. E' l'esito che il cockpit mostra all'operatore.
    def test_until_done_si_ferma_su_step_con_fatture_in_errore(self):
        class _ErroreDuranteStepStatefulRepo(self._StatefulRepo):
            # Scopo: job stato reale (il runner lo scrive, il driver lo rilegge).
            def __init__(self):
                super().__init__(chiude_su=8)
                self._job = "DRAFT"

            def get_lotto_job_stato(self, lotto_id):
                return self._job

            def set_lotto_job_stato(self, lotto_id, stato, messaggio):
                self._job = stato
                self.last_stato = stato

            # Scopo: gate pulito (1a valutazione), errori comparsi nello step.
            def get_lotto_segnalazioni_summary(self, lotto_id):
                self.summary_calls = getattr(self, "summary_calls", 0) + 1
                errore = self.summary_calls > 1
                return {
                    "fatture_critical_count": 1 if errore else 0,
                    "fatture_warning_count": 0,
                    "lotto_critical_count": 0,
                    "lotto_warning_count": 0,
                    "lotto_info_count": 0,
                    "fatture_stato_esecuzione_errore_count": 1 if errore else 0,
                }

        repo = _ErroreDuranteStepStatefulRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            esito = runner.run_lotto_until_done(LottoPipelineParams(dry_run=False))
        self.assertEqual(esito["motivo_stop"], "BLOCCATO_CRITICITA")
        self.assertEqual(esito["step_eseguiti"], 1)
        self.assertEqual(esito["errore"]["code"], "E_PIPELINE_LOTTO_CRITICAL")
        self.assertEqual(len(step_executor.calls), 1)

    # Scopo: D-Q — RILANCIO riuscito dello step in errore: il driver NON esce
    #        con un finto COMPLETATO a meta' strada, prosegue e porta la catena
    #        fino in fondo ([1 rilanciato, 2, 8]). E' il flusso operatore
    #        «correggo → premo una volta → finisce».
    def test_until_done_prosegue_dopo_rilancio_riuscito(self):
        class _RilancioRiuscitoRepo(self._StatefulRepo):
            # Scopo: lotto ESISTENTE in errore sullo step 1; le criticita'
            #        risultano attive solo alla prima valutazione (il rilancio
            #        le risolve: i task ritirano le proprie segnalazioni).
            def __init__(self):
                super().__init__(chiude_su=8)
                self.current = 1
                self._job = "ERRORE"

            def get_lotto_job_stato(self, lotto_id):
                return self._job

            def set_lotto_job_stato(self, lotto_id, stato, messaggio):
                self._job = stato
                self.last_stato = stato

            def get_lotto_segnalazioni_summary(self, lotto_id):
                self.summary_calls = getattr(self, "summary_calls", 0) + 1
                errore = self.summary_calls == 1
                return {
                    "fatture_critical_count": 1 if errore else 0,
                    "fatture_warning_count": 0,
                    "lotto_critical_count": 0,
                    "lotto_warning_count": 0,
                    "lotto_info_count": 0,
                    "fatture_stato_esecuzione_errore_count": 0,
                }

        repo = _RilancioRiuscitoRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            esito = runner.run_lotto_until_done(
                LottoPipelineParams(lotto_id=10, dry_run=False)
            )
        self.assertEqual(esito["motivo_stop"], "COMPLETATO")
        self.assertEqual(esito["step_eseguiti"], 3)
        self.assertIsNone(esito["errore"])
        self.assertEqual(
            [c["stato_doc_fiscale_id"] for c in step_executor.calls], [1, 2, 8],
        )

    # ------------------------------------------------------------------
    # Fase 6 — ritorno del lotto a DRAFT (brief DB→BE ritorno-lotto-a-draft)
    # ------------------------------------------------------------------

    # Scopo: 🔴 il cuore della Fase 6. Un lotto riportato a bozza NON e' in
    #        errore: senza la lettura di `riaperto_il` cadrebbe nel ramo «lotto
    #        esistente riuscito» e ripartirebbe dallo step SUCCESSIVO (EMESSA),
    #        saltando proprio la rigenerazione delle righe per cui era stato
    #        riaperto. Qui deve rifare lo step CORRENTE (DRAFT = 1).
    def test_lotto_riaperto_rifa_step_corrente(self):
        class _RiapertoRepo(self._RepoMock):
            # Scopo: lotto esistente, NON in errore, con il segnale di
            #        riapertura acceso e stato fiscale fermo a DRAFT.
            def get_lotto_job_stato(self, lotto_id):
                return "COMPLETATO"

            def is_lotto_riaperto(self, lotto_id):
                return True

        repo = _RiapertoRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            runner.run_pipeline(LottoPipelineParams(lotto_id=10, dry_run=False))
        # Step 1 = DRAFT, cioe' quello corrente: rifatto, non saltato.
        self.assertEqual(
            [c["stato_doc_fiscale_id"] for c in step_executor.calls], [1],
        )

    # Scopo: controprova del test precedente — senza il segnale, lo STESSO
    #        lotto avanza allo step successivo. Se questa fosse verde insieme a
    #        una versione rotta della precedente, vorrebbe dire che il ramo non
    #        discrimina: le due vanno lette in coppia.
    def test_lotto_non_riaperto_avanza_allo_step_successivo(self):
        class _NormaleRepo(self._RepoMock):
            def get_lotto_job_stato(self, lotto_id):
                return "COMPLETATO"

        repo = _NormaleRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            runner.run_pipeline(LottoPipelineParams(lotto_id=10, dry_run=False))
        self.assertEqual(
            [c["stato_doc_fiscale_id"] for c in step_executor.calls], [2],
        )

    # Scopo: «chi accende il segnale lo spegne». Dopo che il giro ha rifatto lo
    #        step, `riaperto_il` va azzerato: senza, il lotto rifarebbe lo
    #        stesso passo per sempre (brief §3 punto 2).
    def test_lotto_riaperto_azzera_il_segnale_dopo_lo_step(self):
        class _RiapertoRepo(self._RepoMock):
            def get_lotto_job_stato(self, lotto_id):
                return "COMPLETATO"

            def is_lotto_riaperto(self, lotto_id):
                return True

        repo = _RiapertoRepo()
        runner = LottoPipelineRunner(
            repository=repo, step_executor=self._StepExecutorMock(),
        )
        with _fake_tx():
            runner.run_pipeline(LottoPipelineParams(lotto_id=10, dry_run=False))
        self.assertEqual(getattr(repo, "riaperto_azzerato", []), [10])

    # Scopo: il segnale NON si spegne se non c'e' stato alcuno step da eseguire
    #        (catena gia' all'ultimo passo). Spegnerlo li' sarebbe una bugia:
    #        la riapertura non e' stata onorata da nessuno.
    def test_lotto_riaperto_non_azzera_se_nessuno_step_eseguito(self):
        class _RiapertoUltimoStepRepo(self._RepoMock):
            def get_lotto_job_stato(self, lotto_id):
                return "COMPLETATO"

            def is_lotto_riaperto(self, lotto_id):
                return True

            def get_lotto_stato_doc_fiscale_id(self, lotto_id):
                # Stato non presente nel catalogo step -> nessuno step risolto.
                return 12345

            def list_pipeline_steps(self, tipo_lotto, **kwargs):
                return []

        repo = _RiapertoUltimoStepRepo()
        runner = LottoPipelineRunner(
            repository=repo, step_executor=self._StepExecutorMock(),
        )
        with _fake_tx():
            runner.run_pipeline(LottoPipelineParams(lotto_id=10, dry_run=False))
        self.assertEqual(getattr(repo, "riaperto_azzerato", []), [])

    # Scopo: il lotto riaperto NON deve innescare il rollback automatico dello
    #        step. Le fatture le ha gia' cancellate la funzione DB: un rollback
    #        in piu' lavorerebbe sul vuoto. E' la ragione per cui il flag di
    #        riapertura resta DISTINTO da `is_massivo_error_rerun` invece di
    #        essere fuso con lui — se venissero fusi, questo test diventa rosso.
    def test_lotto_riaperto_non_innesca_rollback_automatico(self):
        class _RiapertoRepo(self._RepoMock):
            def get_lotto_job_stato(self, lotto_id):
                return "COMPLETATO"

            def is_lotto_riaperto(self, lotto_id):
                return True

            # ⚠️ Rollback NON distruttivo sullo step DRAFT: senza questo il
            #    test sarebbe VACUO. Il mock base espone un rollback solo sullo
            #    step 2 e per giunta `reset_lotto_draft`, che il guard scarta
            #    come distruttivo — quindi il rollback non partirebbe comunque,
            #    e il test resterebbe verde anche fondendo i due flag (provato:
            #    la prima stesura non moriva sotto mutazione).
            def get_step_processes(
                self,
                stato_doc_fiscale_id,
                *,
                tipo_lotto,
                utility_id,
                tipo_doc_fiscale_id,
                rollback,
            ):
                if rollback and stato_doc_fiscale_id == 1:
                    return [{"task": "ricalcola_iva_lotto", "params": {}}]
                return []

        repo = _RiapertoRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            runner.run_pipeline(
                LottoPipelineParams(
                    lotto_id=10, dry_run=False, meta={"auto_step_rollback": True},
                )
            )
        self.assertEqual(
            [c.get("rollback") for c in step_executor.calls], [False],
            "Il lotto riaperto non deve eseguire il rollback dello step: le "
            "fatture le ha gia' cancellate la funzione DB",
        )

    # 38) 🔴 Il caso scoperto sul campo (lotto 1279, 2026-08-03): il rifacimento
    #     attraversa lo step ma NON produce fatture — i task erano tutti in
    #     `SKIP` perche' i loro task_runs risultavano gia' COMPLETATO. Il
    #     segnale NON deve spegnersi: se si spegnesse, il lotto resterebbe
    #     vuoto E senza segnale, e il rilancio dopo passerebbe allo step
    #     successivo su un documento che non esiste. E' esattamente il «non fa
    #     nulla» che ha portato a scoprire il difetto.
    def test_lotto_riaperto_non_azzera_se_il_giro_non_ha_prodotto_fatture(self):
        class _RiapertoAVuotoRepo(self._RepoMock):
            def get_lotto_job_stato(self, lotto_id):
                return "COMPLETATO"

            def is_lotto_riaperto(self, lotto_id):
                return True

            # Lo step gira, ma il lotto resta senza fatture.
            def list_fatture_by_lotto(self, lotto_id, *, limit=50000):
                return []

        repo = _RiapertoAVuotoRepo()
        runner = LottoPipelineRunner(
            repository=repo, step_executor=self._StepExecutorMock(),
        )
        with _fake_tx():
            runner.run_pipeline(LottoPipelineParams(lotto_id=10, dry_run=False))
        self.assertEqual(
            getattr(repo, "riaperto_azzerato", []), [],
            "Un rifacimento a vuoto non deve spegnere il segnale di riapertura",
        )
