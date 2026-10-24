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
39) test_giornale_rotto_non_ferma_la_pipeline (BE-7 / D-15)
40) test_il_filo_del_giro_e_nuovo_a_ogni_corsa (BE-2 / D-7)
41) test_il_filo_del_giro_arriva_allo_step_executor (BE-2 / D-7)
42) test_giornale_rotto_non_annulla_la_marcatura_di_errore (BE-7, il verso mancante)
43) test_marcatura_rifiutata_non_impedisce_il_diario (lotto 6260, giro vero 2026-08-23)
44) test_resolver_fuori_catena_non_ricade_sul_primo_step (LTF-0009971, 2026-09-08)
45) test_resolver_lotto_nuovo_fuori_catena_parte_dal_primo_step (controprova del 44)
46) test_runner_rifiuta_il_giro_su_lotto_fuori_catena
47) test_giro_senza_step_non_cancella_lo_stato_errore
48) test_giro_senza_step_spegne_l_errore_se_le_segnalazioni_sono_rientrate (controprova del 47)
49) test_runner_blocks_when_documenti_hanno_esito_errore_senza_critiche (D2, 2026-09-12)

Nota Fase 6 (2026-08-03): i test 33-37 presidiano il ritorno del lotto a
DRAFT. Il 33 e il 34 vanno letti in COPPIA: da soli non distinguono un ramo
che discrimina da uno che risponde sempre allo stesso modo.

Nota D-Q (2026-07-31): i test 13-14 ora esercitano il blocco sull'AVANZAMENTO
(lotto esistente → step successivo); il rilancio dello STESSO step con
criticita' attive e' ammesso per disegno (test 28).

Nota «lotto dentro la propria catena» (2026-09-08, segnalazione team DB sul
lotto LTF-0009971): i test 44-48 presidiano due meta' dello stesso difetto —
il resolver che rispondeva con la catena INTERA su uno stato che non e' un suo
step (44/45), e la conclusione che dichiarava «Pipeline completata» dopo un
giro senza step (47/48). Le due COPPIE vanno lette come tali: il ramo deve
discriminare, non rispondere sempre allo stesso modo.
"""

from contextlib import contextmanager, nullcontext
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.services.db_error_fields import Bersaglio
from apps.core.tests.db_error_fakes import make_db_error
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
                "esiti_stato_esecuzione_errore_count": 0,
                # ⭐ Il verdetto lo dice il DB (D-V1, 2026-09-19): il fake lo
                #    dichiara coerente con gli addendi, come fa la vista.
                "fermo": False,
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

    # Scopo: BE-2 (brief-modello-documento-vendita §4-octies) — un codice del
    #        catalogo sollevato dal DB dentro lo step resta QUEL codice, come se
    #        l'avesse sollevato il runner. Prima il ramo generico lo appiattiva
    #        in `E_PIPELINE`. Il caso: il guard del lotto (R-1) rifiuta l'UPDATE
    #        dello stato perche' il lotto e' fermo.
    def test_runner_preserva_il_codice_del_database(self):
        class _RepoGuardFermo(self._RepoMock):
            def update_lotto_stato_doc(self, lotto_id, stato_doc_fiscale_id):
                raise make_db_error(
                    "Lotto bloccato: segnalazioni critiche o documenti in errore.",
                    codice="E_PIPELINE_LOTTO_CRITICAL",
                )

        repo = _RepoGuardFermo()
        runner = LottoPipelineRunner(repository=repo, step_executor=self._StepExecutorMock())
        with _fake_tx():
            with self.assertRaises(ServiceError) as exc:
                runner.run_pipeline(LottoPipelineParams(dry_run=False))
        self.assertEqual(exc.exception.code, "E_PIPELINE_LOTTO_CRITICAL")
        self.assertEqual(repo.last_stato, "ERRORE")

    # Scopo: BE-2, il rovescio — un errore DB SENZA codice del catalogo resta
    #        un guasto tecnico (`E_PIPELINE`): un `E_...` nel solo testo non e'
    #        una prova di dominio.
    def test_runner_errore_db_senza_codice_resta_tecnico(self):
        class _RepoGuasto(self._RepoMock):
            def update_lotto_stato_doc(self, lotto_id, stato_doc_fiscale_id):
                raise make_db_error("E_PIPELINE_LOTTO_CRITICAL nel testo e basta")

        runner = LottoPipelineRunner(repository=_RepoGuasto(), step_executor=self._StepExecutorMock())
        with _fake_tx():
            with self.assertRaises(ServiceError) as exc:
                runner.run_pipeline(LottoPipelineParams(dry_run=False))
        self.assertEqual(exc.exception.code, "E_PIPELINE")

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
                    esiti_stato_esecuzione_errore_count=0,
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
                    "esiti_stato_esecuzione_errore_count": 0,
                    # ⭐ Il verdetto lo dice il DB (D-V1, 2026-09-19): il fake lo
                    #    dichiara coerente con gli addendi, come fa la vista.
                    "fermo": True,
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

    # Scopo: ⭐ D2 (2026-09-12) — il runner blocca l'AVANZAMENTO quando un
    #        documento preso in carico ha l'ultimo esito ERRORE, con ZERO
    #        critiche vive e zero fatture in errore: e' il terzo addendo del
    #        verdetto, e il caso che prima usciva COMPLETATO per sottrazione.
    # ⚠️ E il rifiuto NOMINA il motivo: `context` e `detail` portano
    #        `esiti_errore_count`. Un lotto bloccato con `critical_count=0` e
    #        `stato_esecuzione_errore_count=0` e basta sarebbe un rifiuto senza
    #        ragione — un bug, agli occhi di chi legge il log.
    def test_runner_blocks_when_documenti_hanno_esito_errore_senza_critiche(self):
        class _EsitiErroreRepo(self._RepoMock):
            # Scopo: riepilogo con il SOLO terzo addendo valorizzato.
            def get_lotto_segnalazioni_summary(self, lotto_id):
                return {
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
                    # ⭐ Il verdetto lo dice il DB (D-V1, 2026-09-19): il fake lo
                    #    dichiara coerente con gli addendi, come fa la vista.
                    "fermo": True,
                }

        # Lotto ESISTENTE che tenterebbe l'avanzamento allo step 2 (come i due
        # gemelli sopra): il gate deve scattare per il solo terzo addendo.
        repo = _EsitiErroreRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            with self.assertRaises(ServiceError) as exc:
                runner.run_pipeline(LottoPipelineParams(lotto_id=10, dry_run=False))
        self.assertEqual(exc.exception.code, "E_PIPELINE_LOTTO_CRITICAL")
        self.assertFalse(step_executor.called)
        self.assertEqual(exc.exception.context["esiti_errore_count"], 2)
        self.assertEqual(exc.exception.context["critical_count"], 0)
        self.assertIn("esiti_errore_count=2", exc.exception.detail or "")

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
                    "esiti_stato_esecuzione_errore_count": 0,
                    # ⭐ Il verdetto lo dice il DB (D-V1, 2026-09-19): il fake lo
                    #    dichiara coerente con gli addendi, come fa la vista.
                    "fermo": True,
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
                    "esiti_stato_esecuzione_errore_count": 0,
                    # ⭐ Il verdetto lo dice il DB (D-V1, 2026-09-19): il fake lo
                    #    dichiara coerente con gli addendi, come fa la vista.
                    "fermo": True,
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
                    "esiti_stato_esecuzione_errore_count": 0,
                    # ⭐ Il verdetto lo dice il DB (D-V1, 2026-09-19): il fake lo
                    #    dichiara coerente con gli addendi, come fa la vista.
                    "fermo": errore,
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
                    "esiti_stato_esecuzione_errore_count": 0,
                    # ⭐ Il verdetto lo dice il DB (D-V1, 2026-09-19): il fake lo
                    #    dichiara coerente con gli addendi, come fa la vista.
                    "fermo": False,
                }

        repo = _OnlyWarningsRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            result = runner.run_pipeline(LottoPipelineParams(dry_run=True))
        self.assertEqual(result, 10)
        self.assertTrue(step_executor.called)

    # Scopo: 🔴 UNA MARCATURA RIFIUTATA NON IMPEDISCE IL DIARIO.
    #
    #        Lo SPECCHIO del test qui sotto, e non è un caso di scuola: è
    #        successo su un giro vero il 2026-08-23, lotto 6260. La pipeline era
    #        fallita per un motivo di dominio legittimo (nota di credito non
    #        numerabile), poi:
    #
    #          set_lotto_job_stato(6260, 'ERRORE')
    #            -> «Transizione non ammessa: COMPLETATO -> ERRORE»
    #
    #        Il lotto era gia' COMPLETATO da una corsa precedente. L'eccezione
    #        usciva prima che il diario venisse tentato, e in `event_log`
    #        restavano ZERO righe: dell'unico giro andato storto non c'era
    #        traccia nel registro fatto apposta per raccontarlo.
    #
    # ⚠️ Il verso è che `log_event` venga chiamato COMUNQUE. Un test che si
    #    limitasse a «non solleva» passerebbe anche col difetto — non sollevava
    #    nemmeno prima, perché il telaio ingoiava.
    def test_marcatura_rifiutata_non_impedisce_il_diario(self):
        repo = MagicMock()
        # La transizione di stato è rifiutata dal guard di dominio, come sul 6260.
        repo.set_lotto_job_stato.side_effect = RuntimeError(
            "Transizione non ammessa: COMPLETATO -> ERRORE"
        )
        runner = LottoPipelineRunner(repository=repo, error_logger=MagicMock())

        with _fake_tx():
            runner._mark_lotto_error_safely(
                lotto_id=6260, code="E_PIPELINE", tipo_lotto="MASSIVO",
                detail="nota di credito non numerabile",
                correlation_id="7f3a1c22-0000-4000-8000-000000000003",
            )

        repo.log_event.assert_called_once()
        kw = repo.log_event.call_args.kwargs
        self.assertEqual(kw["event_code"], "PIPELINE_ERROR")
        self.assertEqual(kw["entity_id"], 6260)
        self.assertEqual(kw["severity"], "ERROR")
        # ⭐ E il filo del giro sopravvive: è il modo in cui questa riga si
        #    ricollega al resto della corsa che è andata storta.
        self.assertEqual(
            kw["correlation_id"], "7f3a1c22-0000-4000-8000-000000000003"
        )

    # Scopo: 🔴 UN GIORNALE ROTTO NON ANNULLA LA MARCATURA DI ERRORE.
    #
    #        Il verso che mancava, e il difetto era reale: `log_event` stava
    #        DENTRO l'`atomic` di `_mark_lotto_error`, insieme alle tre
    #        scritture che contano (segnalazione di lotto, stato ERRORE,
    #        fotografia esito fatture). Una riga di giornale rifiutata rollava
    #        indietro **anche quelle**, e il telaio best-effort del chiamante
    #        ingoiava — quindi il lotto restava senza stato ERRORE, in silenzio,
    #        proprio nel ramo in cui qualcosa era gia' andato storto.
    #
    # ⚠️ Il telaio NON bastava: avvolge `_mark_lotto_error` per intero, quindi
    #    vede il guasto solo dopo che la transazione ha gia' annullato tutto.
    #    Per questo il test guarda l'ORDINE — la marcatura deve avvenire prima
    #    che il diario ci provi — e non solo «non solleva».
    def test_giornale_rotto_non_annulla_la_marcatura_di_errore(self):
        # Traccia APERTURA e CHIUSURA di ogni blocco transazionale, cosi' si puo'
        # dire in quale blocco cade ciascuna scrittura. ⚠️ Un test che guardasse
        # solo l'ORDINE delle chiamate non distinguerebbe le due versioni: anche
        # col difetto il diario veniva dopo la marcatura — solo, nello STESSO
        # blocco. E' la profondita' che conta, non la sequenza.
        # Ogni blocco transazionale ha un ID PROPRIO (non la profondita': due
        # blocchi fratelli hanno la stessa profondita' e sarebbero
        # indistinguibili). Cosi' si puo' chiedere la cosa giusta: «il blocco in
        # cui e' avvenuta la marcatura era gia' chiuso quando il diario ci ha
        # provato?».
        eventi: list[str] = []
        aperti: list[int] = []
        prossimo = {"id": 0}

        class _AtomicSpia:
            def __enter__(self_inner):
                prossimo["id"] += 1
                aperti.append(prossimo["id"])
                eventi.append(f"apre#{prossimo['id']}")
                return self_inner

            def __exit__(self_inner, *a):
                eventi.append(f"chiude#{aperti.pop()}")
                return False

        repo = MagicMock()
        repo.set_lotto_job_stato.side_effect = lambda *a, **k: eventi.append(
            f"marca#{aperti[-1]}"
        )

        def _diario_rifiutato(**_kwargs):
            eventi.append(f"diario#{aperti[-1]}")
            raise RuntimeError("E_EVENT_LOG_SCOPE_NON_RISOLTO")

        repo.log_event.side_effect = _diario_rifiutato
        runner = LottoPipelineRunner(repository=repo, error_logger=MagicMock())

        with patch(
            "apps.vendite.services.pipeline_runner.transaction.atomic",
            side_effect=lambda *a, **k: _AtomicSpia(),
        ):
            # Non deve sollevare: e' best-effort per costruzione.
            runner._mark_lotto_error_safely(
                lotto_id=1, code="E_X", tipo_lotto="MASSIVO", detail="dettaglio",
            )

        blocco_marcatura = next(e for e in eventi if e.startswith("marca#")).split("#")[1]
        diario = next(e for e in eventi if e.startswith("diario#"))
        # ⭐ Il blocco in cui e' avvenuta la marcatura DEVE essere gia' chiuso
        #    quando il diario ci prova. Se lo condividessero, il rifiuto della
        #    riga di giornale rollerebbe indietro anche lo stato ERRORE — ed e'
        #    esattamente cio' che faceva.
        self.assertLess(
            eventi.index(f"chiude#{blocco_marcatura}"), eventi.index(diario),
            f"il diario scrive dentro la transazione della marcatura: {eventi}",
        )
        # E le tre scritture che contano sono state fatte tutte.
        repo.log_lotto_esito_fatture.assert_called_once()

    # Scopo: ⭐ IL FILO DEL GIRO E' NUOVO A OGNI CORSA (BE-2, D-7).
    #
    # 🔴 E' il difetto che questa consegna chiude, ed e' invisibile a un test
    #    che guardi una corsa sola: il `correlation_id` valeva
    #    `lotto_context.lock_batch_id`, che nasce col LOTTO e **non cambia
    #    mai**. Diceva «di che lotto», che `entity_id` diceva gia' — e due
    #    corse dello stesso lotto erano indistinguibili proprio sulla domanda
    #    per cui il campo esiste.
    #
    # ⚠️ Per questo il test fa DUE corse sullo stesso lotto e confronta: con
    #    l'implementazione vecchia i due valori erano uguali e il test sarebbe
    #    rosso. Una corsa sola non distinguerebbe le due implementazioni.
    def test_il_filo_del_giro_e_nuovo_a_ogni_corsa(self):
        fili: list[str | None] = []

        def _corri() -> None:
            repo = MagicMock(wraps=self._RepoMock())
            step_executor = self._StepExecutorMock()
            runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
            with _fake_tx():
                runner.run_pipeline(LottoPipelineParams(lotto_id=10, dry_run=True))
            fili.append(step_executor.last_kwargs.get("correlation_id"))

        _corri()
        _corri()

        self.assertEqual(len(fili), 2)
        self.assertTrue(all(fili), "il giro deve avere un filo")
        self.assertNotEqual(
            fili[0], fili[1],
            "due corse dello stesso lotto condividono il filo: e' il difetto "
            "di `lock_batch_id`, che nasce col lotto e non cambia mai",
        )

    # Scopo: lo STESSO filo scende sugli eventi e sullo step executor — che e'
    #        poi la via per cui arriva ai `task_runs`.
    #
    # ⚠️ Il verso «lo stesso» conta quanto «c'e'»: due fili diversi nella stessa
    #    corsa non cucirebbero niente, ed e' un difetto che si vede solo
    #    confrontandoli fra loro.
    def test_il_filo_del_giro_arriva_allo_step_executor(self):
        repo = MagicMock(wraps=self._RepoMock())
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)

        with _fake_tx():
            runner.run_pipeline(LottoPipelineParams(lotto_id=10, dry_run=True))

        filo_step = step_executor.last_kwargs.get("correlation_id")
        self.assertTrue(filo_step)
        fili_eventi = {
            c.kwargs.get("correlation_id") for c in repo.log_event.call_args_list
        }
        self.assertEqual(
            fili_eventi, {filo_step},
            "eventi e task_runs dello stesso giro devono portare lo stesso filo",
        )

    # Scopo: ⭐ UN DIFETTO DEL DIARIO NON FERMA IL LAVORO CHE DESCRIVE
    #        (consegna BE-7, decisione D-15 del brief
    #        `brief-db-event-log-scope-e-riga-parlante.md`).
    #
    #        E' il verso che nessuno verificava, ed e' quello che conta: dal
    #        2026-08-22 `fn_log_event` PUO' rifiutare una riga — il giornale
    #        non accetta eventi di cui non sappia dire di chi sono. Le tre
    #        scritture di `PIPELINE_STARTED` / `STEP_COMPLETED` /
    #        `PIPELINE_COMPLETED` stanno DENTRO l'`atomic` del giro: senza il
    #        telaio best-effort, un evento rifiutato portava giu' l'intera
    #        pipeline di fatturazione — cioe' il difetto BE-1 in grande.
    #
    # ⚠️ Non basta che non sollevi: la pipeline deve ARRIVARE IN FONDO. Un
    #    test che si fermasse a `assertNoRaises` passerebbe anche se il giro
    #    uscisse a meta' in silenzio, che e' il modo in cui questo difetto
    #    sarebbe tornato.
    def test_giornale_rotto_non_ferma_la_pipeline(self):
        repo = MagicMock(wraps=self._RepoMock())
        # Il giornale rifiuta OGNI riga, come farebbe il trigger di derivazione
        # su un'entita' che non sa collocare.
        repo.log_event.side_effect = RuntimeError(
            "E_EVENT_LOG_SCOPE_NON_RISOLTO: il giornale non registra righe senza perimetro"
        )
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)

        with _fake_tx():
            result = runner.run_pipeline(LottoPipelineParams(dry_run=True))

        # Il giro e' arrivato in fondo: lotto restituito e step eseguito.
        self.assertEqual(result, 10)
        self.assertTrue(step_executor.called)
        # E il diario ci ha PROVATO su tutti e tre i momenti: il telaio
        # assorbe, non salta le scritture successive.
        codici = {
            c.kwargs.get("event_code") for c in repo.log_event.call_args_list
        }
        self.assertEqual(
            codici, {"PIPELINE_STARTED", "STEP_COMPLETED", "PIPELINE_COMPLETED"}
        )

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
                    "esiti_stato_esecuzione_errore_count": 0,
                    # ⭐ Il verdetto lo dice il DB (D-V1, 2026-09-19): il fake lo
                    #    dichiara coerente con gli addendi, come fa la vista.
                    "fermo": True,
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

    # Scopo: BE-2 — il lotto diventa fermo FRA il controllo del runner e
    #        l'UPDATE: lo ferma il guard del DB, e il driver esce con
    #        BLOCCATO_CRITICITA come quando lo ferma il runner (prima: ERRORE).
    def test_until_done_bloccato_dal_guard_del_database(self):
        class _GuardRepo(self._StatefulRepo):
            def update_lotto_stato_doc(self, lotto_id, stato_doc_fiscale_id):
                raise make_db_error(
                    "Lotto bloccato: segnalazioni critiche o documenti in errore.",
                    codice="E_PIPELINE_LOTTO_CRITICAL",
                )

        runner = LottoPipelineRunner(repository=_GuardRepo(), step_executor=self._StepExecutorMock())
        with _fake_tx():
            esito = runner.run_lotto_until_done(LottoPipelineParams(lotto_id=10, dry_run=False))
        self.assertEqual(esito["motivo_stop"], "BLOCCATO_CRITICITA")

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
                    "esiti_stato_esecuzione_errore_count": 0,
                    # ⭐ Il verdetto lo dice il DB (D-V1, 2026-09-19): il fake lo
                    #    dichiara coerente con gli addendi, come fa la vista.
                    "fermo": errore,
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
                    "esiti_stato_esecuzione_errore_count": 0,
                    # ⭐ Il verdetto lo dice il DB (D-V1, 2026-09-19): il fake lo
                    #    dichiara coerente con gli addendi, come fa la vista.
                    "fermo": errore,
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
    # Il blob `errore` dentro il 200: stessi NOMI dell'envelope, e dal
    # 2026-09-09 anche le stesse REGOLE.
    # ------------------------------------------------------------------

    # Scopo: 🔴 LA REGOLA CHE MANCAVA. Questi endpoint rispondono **200 anche
    #        quando la catena si ferma**: il fallimento e' un campo del payload,
    #        quindi `useApiHandler` non vede nessun envelope e a video arriva
    #        SOLO cio' che sta in questo dizionario.
    #        ⛔ Fino al 2026-09-09 il blob leggeva `exc.hint` ed `exc.targets`
    #        DIRETTI, mentre l'envelope li fa passare da `_apply_policy` — che su
    #        un codice tecnico li toglie. Stesso nome, regola diversa: e due
    #        regole non si notano come si notano due nomi. Il difetto e' diventato
    #        visibile quando il frontend ha cominciato a RENDERE il suggerimento.
    #        ⚠️ `message` e `detail` restano invece quelli grezzi dell'eccezione,
    #        di proposito: qui alimentano il pannello di diagnostica di un lotto.
    def test_il_blob_di_errore_applica_le_politiche_dell_envelope(self):
        class _StepChe(self._StepExecutorMock):
            def __init__(self, exc):
                super().__init__()
                self._exc = exc

            def execute_step(self, **kwargs):
                raise self._exc

        casi = {
            # Tecnico: niente suggerimento (il canale HINT li' porta il testo di
            # PostgreSQL) e niente bersaglio (su un guasto non c'e' un gesto).
            "E_DATABASE": (None, None),
            # Rimediabile: escono entrambi, o il test sopra passerebbe anche se
            # non uscissero MAI.
            "E_FATTURA_RETTIFICATA_SENZA_NUMERO": (
                "Numerare prima i documenti che questo rettifica.",
                [{"type": "FATTURA", "id": "820"}],
            ),
        }
        for codice, (hint_atteso, targets_attesi) in casi.items():
            with self.subTest(codice=codice):
                exc = ServiceError(
                    code=codice,
                    message="non numerabile",
                    detail="dettaglio grezzo del database",
                    hint="Numerare prima i documenti che questo rettifica.",
                    targets=(Bersaglio(tipo="FATTURA", id="820"),),
                )
                repo = self._StatefulRepo(chiude_su=8)
                runner = LottoPipelineRunner(
                    repository=repo, step_executor=_StepChe(exc),
                )
                with _fake_tx():
                    esito = runner.run_lotto_until_done(
                        LottoPipelineParams(lotto_id=10, dry_run=False)
                    )
                self.assertEqual(esito["motivo_stop"], "ERRORE")
                self.assertEqual(esito["errore"]["hint"], hint_atteso)
                self.assertEqual(esito["errore"]["targets"], targets_attesi)
                # ⚠️ Il codice e il messaggio NON passano dalla policy: restano
                #    quelli dell'eccezione. E' la differenza voluta.
                self.assertEqual(esito["errore"]["code"], codice)
                self.assertEqual(esito["errore"]["message"], "non numerabile")
                self.assertEqual(
                    esito["errore"]["detail"], "dettaglio grezzo del database"
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

    # ------------------------------------------------------------------
    # Il lotto dentro la propria catena (difetto 2026-09-08, LTF-0009971)
    # ------------------------------------------------------------------

    # Scopo: 🔴 UN LOTTO FUORI DALLA PROPRIA CATENA NON RIPARTE DAL PRIMO STEP.
    #
    #        `_resolve_steps_for_run` rispondeva con la catena INTERA quando lo
    #        stato corrente non e' uno dei suoi step, e il chiamante prende
    #        `steps[:1]`: su un lotto ANNULLATA veniva scelto lo step DRAFT e il
    #        runner provava a riportarcelo. E' la TRANSIZIONE RETROATTIVA che
    #        questo resolver dichiara di esistere per impedire.
    #
    # ⚠️ Il test guarda il RESOLVER e non l'effetto a valle, perche' a valle il
    #    difetto non si vedeva: la matrice di `stati_doc_fiscale_transizioni`
    #    non ha righe in uscita da ANNULLATA, quindi il guard a DB rifiutava e
    #    tutto sembrava a posto. Fail-safe per accidente del seed, non per
    #    progetto — ed e' il seed a poter cambiare.
    def test_resolver_fuori_catena_non_ricade_sul_primo_step(self):
        steps = self._RepoMock().list_pipeline_steps("MASSIVO")
        risolti = LottoPipelineRunner._resolve_steps_for_run(
            steps=steps,
            is_existing_lotto_request=True,
            deve_rifare_step_corrente=False,
            # 7 = ANNULLATA: non e' uno step della catena.
            lotto_stato_doc_corrente=7,
        )
        self.assertEqual(risolti, [])

    # Scopo: controprova del test precedente — su un lotto APPENA CREATO lo
    #        stesso stato sconosciuto NON blocca: non c'e' nessuna posizione da
    #        rispettare, e la catena parte dal suo primo step. Le due vanno
    #        lette in coppia: da sole non distinguono un ramo che discrimina da
    #        uno che risponde sempre allo stesso modo.
    def test_resolver_lotto_nuovo_fuori_catena_parte_dal_primo_step(self):
        steps = self._RepoMock().list_pipeline_steps("MASSIVO")
        risolti = LottoPipelineRunner._resolve_steps_for_run(
            steps=steps,
            is_existing_lotto_request=False,
            deve_rifare_step_corrente=False,
            lotto_stato_doc_corrente=7,
        )
        self.assertEqual(risolti, steps)

    # Scopo: ⭐ E il giro si RIFIUTA, non si esegue a vuoto. La lista vuota piu'
    #        avanti significa gia' «catena esaurita» e porta a «Pipeline
    #        completata»: su un lotto ANNULLATA sarebbe un giro che non ha fatto
    #        niente e si annuncia riuscito.
    #
    # ⚠️ `E_PIPELINE_STATO_LOTTO` e' un riuso dichiarato: dice il vero
    #    all'operatore ed e' della classe giusta (CONFLITTO_STATO), ma i suoi
    #    altri punti di chiamata parlano dell'asse LAVORO. Il codice suo e'
    #    `E_LOTTO_NON_AVANZABILE`, chiesto al team DB — e quando arriva questo
    #    test cambia una stringa.
    def test_runner_rifiuta_il_giro_su_lotto_fuori_catena(self):
        class _FuoriCatenaRepo(self._RepoMock):
            def get_lotto_stato_doc_fiscale_id(self, lotto_id):
                return 7  # ANNULLATA, fuori dalla catena [1, 2, 8]

        repo = _FuoriCatenaRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        with _fake_tx():
            with self.assertRaises(ServiceError) as exc:
                runner.run_pipeline(LottoPipelineParams(lotto_id=10, dry_run=False))
        self.assertEqual(exc.exception.code, "E_PIPELINE_STATO_LOTTO")
        # ⚠️ Anche la FRASE, e non e' pignoleria: gli endpoint del runner
        #    rispondono 200 con l'esito nel payload, e il frontend rende
        #    `errore.message` — quindi questa e' la riga che l'operatore legge.
        #    Lo stesso codice e' sollevato da altri tre punti con messaggi loro:
        #    se questo tornasse alla frase generica del catalogo, nessun test se
        #    ne accorgerebbe.
        self.assertEqual(
            exc.exception.message,
            "Il lotto non e' in uno stato da cui la pipeline possa proseguire.",
        )
        # Nessuno step eseguito: il rifiuto arriva PRIMA del lavoro.
        self.assertEqual(len(step_executor.calls), 0)

    # Scopo: 🔴 UN GIRO SENZA STEP NON CANCELLA UN ERRORE.
    #
    #        La conclusione leggeva le segnalazioni solo `if steps`: con la
    #        catena vuota `step_con_errori` risultava falso SENZA aver contato
    #        niente, e il lotto usciva COMPLETATO da un giro che non aveva
    #        eseguito nulla. La matrice di `set_lotto_job_stato` non poteva
    #        fermarlo: vieta `ERRORE -> COMPLETATO`, ma l'avvio scrive
    #        `IN_ESECUZIONE`, che da ERRORE e' l'unica porta aperta.
    #
    # ⚠️ Il caso non e' solo quello dei lotti fuori catena (ora rifiutati): un
    #    GIORNALIERO in ERRORE fermo all'ultimo step della sua catena risolve a
    #    `steps[current+1:] == []` — `is_massivo_error_rerun` guarda solo i
    #    MASSIVO — e ci passava.
    def test_giro_senza_step_non_cancella_lo_stato_errore(self):
        class _UltimoStepInErroreRepo(self._RepoMock):
            def get_lotto_job_stato(self, lotto_id):
                return "ERRORE"

            def get_lotto_stato_doc_fiscale_id(self, lotto_id):
                return 8  # ultimo step: non resta niente da eseguire

            # ⚠️ GIORNALIERO di proposito: su MASSIVO `is_massivo_error_rerun`
            #    rifarebbe lo step corrente e la catena non sarebbe vuota.
            def get_lotto_tipo(self, lotto_id):
                return "GIORNALIERO"

        class _SegnalazioniAncoraRotte:
            def evaluate_lotto_status(self, lotto_id):
                return LottoSignalStatus(
                    critical_count=1, warning_count=0, attention_count=0,
                    fatture_stato_esecuzione_errore_count=1,
                    esiti_stato_esecuzione_errore_count=0,
                    is_error=True, blocks_next_step=False, summary={},
                )

        repo = _UltimoStepInErroreRepo()
        step_executor = self._StepExecutorMock()
        runner = LottoPipelineRunner(repository=repo, step_executor=step_executor)
        runner.lotto_segnalazioni_service = _SegnalazioniAncoraRotte()
        with _fake_tx():
            runner.run_pipeline(LottoPipelineParams(lotto_id=10, dry_run=False))
        self.assertEqual(len(step_executor.calls), 0)
        self.assertEqual(
            repo.last_stato, "ERRORE",
            "Un giro a vuoto non puo' concludere «Pipeline completata» su un "
            "lotto le cui fatture sono ancora rotte",
        )

    # Scopo: controprova — se le segnalazioni sono RIENTRATE, lo stesso giro a
    #        vuoto riporta il lotto a COMPLETATO. E' lo spegnimento automatico
    #        promesso da `set_lotto_job_stato` («a fine di ogni giro il runner
    #        ricalcola»): la correzione toglie la scorciatoia, non il
    #        meccanismo. Senza questa coppia, «resta ERRORE» sarebbe
    #        indistinguibile da «non scrive mai piu' niente».
    def test_giro_senza_step_spegne_l_errore_se_le_segnalazioni_sono_rientrate(self):
        class _UltimoStepRepo(self._RepoMock):
            def get_lotto_job_stato(self, lotto_id):
                return "ERRORE"

            def get_lotto_stato_doc_fiscale_id(self, lotto_id):
                return 8

            def get_lotto_tipo(self, lotto_id):
                return "GIORNALIERO"

        class _SegnalazioniRientrate:
            def evaluate_lotto_status(self, lotto_id):
                return LottoSignalStatus(
                    critical_count=0, warning_count=0, attention_count=0,
                    fatture_stato_esecuzione_errore_count=0,
                    esiti_stato_esecuzione_errore_count=0,
                    is_error=False, blocks_next_step=False, summary={},
                )

        repo = _UltimoStepRepo()
        runner = LottoPipelineRunner(
            repository=repo, step_executor=self._StepExecutorMock(),
        )
        runner.lotto_segnalazioni_service = _SegnalazioniRientrate()
        with _fake_tx():
            runner.run_pipeline(LottoPipelineParams(lotto_id=10, dry_run=False))
        self.assertEqual(repo.last_stato, "COMPLETATO")
