# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari CommessaPushOrchestrator.
# ------------------------------------------------------------


"""
Indice test eseguiti:
1) CommessePushOrchestratorTests.test_run_completato_tutti_handler
2) CommessePushOrchestratorTests.test_run_parziale_un_handler_fallisce
3) CommessePushOrchestratorTests.test_run_errore_tutti_handler_falliscono
4) CommessePushOrchestratorTests.test_run_errore_nessun_handler
5) CommessePushOrchestratorTests.test_run_source_types_filtra_handler
6) CommessePushOrchestratorTests.test_run_dry_run_passa_flag_al_log
7) CommessePushOrchestratorTests.test_run_push_log_id_valorizzato
8) CommessePushOrchestratorTests.test_run_isolamento_handler_continua_dopo_eccezione
9) CommessePushOrchestratorTests.test_run_risultato_jsonb_include_tutti_handler
10) CommessePushOrchestratorTests.test_run_skipped_quando_lock_non_acquisito
11) CommessePushOrchestratorTests.test_run_rilascia_lock_dopo_esecuzione
12) CommessePushOrchestratorTests.test_run_non_scrive_su_event_log
13) CommessePushOrchestratorTests.test_run_with_sorgente_uid_propagated_to_handlers_and_perimetro
14) CommessePushOrchestratorTests.test_run_without_sorgente_uid_passes_none_to_handlers
15) CommessePushOrchestratorTests.test_run_with_righe_ids_propagated_to_handlers_and_perimetro
16) CommessePushOrchestratorTests.test_run_apre_il_giro_prima_di_eseguire_gli_handler
17) CommessePushOrchestratorTests.test_run_chiude_il_giro_che_ha_aperto
18) CommessePushOrchestratorTests.test_giro_interrotto_resta_aperto
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.vendite.db.commesse_repository import CommesseRepository
from apps.vendite.services.commesse_push_orchestrator import CommessaPushOrchestrator
from apps.vendite.services.commesse_source_handlers import BaseSourceHandler, HandlerResult


def _mock_repo(push_log_id: int = 1) -> MagicMock:
    repo = MagicMock(spec=CommesseRepository)
    # ⭐ Il giro si APRE e si CHIUDE (BE-3b): `log_push_run` non esiste piu',
    #    e nemmeno a DB — `fn_log_commessa_push_run` e' stata DROPpata dal
    #    changeSet 69. E' l'apertura a restituire il `push_log_id`.
    repo.start_push_run.return_value = push_log_id
    repo.log_event.return_value = 1
    return repo


def _mock_handler(name: str, result: HandlerResult, sorgente_codice: str = "") -> MagicMock:
    h = MagicMock(spec=BaseSourceHandler)
    h.name = name
    h.sorgente_codice = sorgente_codice or name
    h.run.return_value = result
    return h


def _ok_result(name: str, created: int = 1, sorgente_codice: str = "") -> HandlerResult:
    return HandlerResult(handler_name=name, sorgente_codice=sorgente_codice or name, created=created)


class CommessePushOrchestratorTests(TestCase):

    def setUp(self):
        # Scopo: mock advisory lock per evitare connessioni DB reali nei test unitari.
        patcher_acquire = patch.object(
            CommessaPushOrchestrator, "_try_acquire_lock", return_value=True,
        )
        patcher_release = patch.object(
            CommessaPushOrchestrator, "_release_lock",
        )
        self._mock_acquire = patcher_acquire.start()
        self._mock_release = patcher_release.start()
        self.addCleanup(patcher_acquire.stop)
        self.addCleanup(patcher_release.stop)

    # Scopo: tutti gli handler riescono → stato COMPLETATO.
    def test_run_completato_tutti_handler(self):
        repo = _mock_repo()
        h1 = _mock_handler("HandlerA", _ok_result("HandlerA", created=2))
        h2 = _mock_handler("HandlerB", _ok_result("HandlerB", created=1))
        orch = CommessaPushOrchestrator(repo, [h1, h2])

        report = orch.run()

        self.assertEqual(report.stato, "COMPLETATO")
        self.assertEqual(len(report.handlers), 2)
        repo.close_push_run.assert_called_once()

    # Scopo: un handler lancia eccezione → stato PARZIALE, errore catturato nel risultato.
    def test_run_parziale_un_handler_fallisce(self):
        repo = _mock_repo()
        h_ok = _mock_handler("HandlerA", _ok_result("HandlerA"))
        h_fail = MagicMock(spec=BaseSourceHandler)
        h_fail.name = "HandlerB"
        h_fail.sorgente_codice = "SRC_B"
        h_fail.run.side_effect = RuntimeError("DB error")
        orch = CommessaPushOrchestrator(repo, [h_ok, h_fail])

        report = orch.run()

        self.assertEqual(report.stato, "PARZIALE")
        self.assertEqual(len(report.handlers), 2)
        b_result = next(r for r in report.handlers if r.handler_name == "HandlerB")
        self.assertEqual(len(b_result.errors), 1)
        self.assertIn("DB error", b_result.errors[0])

    # Scopo: tutti gli handler falliscono → stato ERRORE.
    def test_run_errore_tutti_handler_falliscono(self):
        repo = _mock_repo()
        h1 = MagicMock(spec=BaseSourceHandler)
        h1.name = "HandlerA"
        h1.sorgente_codice = "SRC_A"
        h1.run.side_effect = RuntimeError("fail A")
        h2 = MagicMock(spec=BaseSourceHandler)
        h2.name = "HandlerB"
        h2.sorgente_codice = "SRC_B"
        h2.run.side_effect = RuntimeError("fail B")
        orch = CommessaPushOrchestrator(repo, [h1, h2])

        report = orch.run()

        self.assertEqual(report.stato, "ERRORE")
        repo.close_push_run.assert_called_once()

    # Scopo: nessun handler registrato → stato ERRORE, log scritto.
    def test_run_errore_nessun_handler(self):
        repo = _mock_repo()
        orch = CommessaPushOrchestrator(repo, [])

        report = orch.run()

        self.assertEqual(report.stato, "ERRORE")
        self.assertEqual(report.handlers, [])
        repo.close_push_run.assert_called_once()

    # Scopo: source_types=[codice_sorgente] esegue solo l'handler corrispondente.
    def test_run_source_types_filtra_handler(self):
        repo = _mock_repo()
        h1 = _mock_handler("HandlerA", _ok_result("HandlerA", sorgente_codice="SRC_A"), sorgente_codice="SRC_A")
        h2 = _mock_handler("HandlerB", _ok_result("HandlerB", sorgente_codice="SRC_B"), sorgente_codice="SRC_B")
        orch = CommessaPushOrchestrator(repo, [h1, h2])

        report = orch.run(source_types=["SRC_A"])

        self.assertEqual(len(report.handlers), 1)
        self.assertEqual(report.handlers[0].handler_name, "HandlerA")
        self.assertEqual(report.handlers[0].sorgente_codice, "SRC_A")
        h1.run.assert_called_once()
        h2.run.assert_not_called()

    # Scopo: dry_run=True → log scritto con dry_run=True, flag propagato all'handler.
    def test_run_dry_run_passa_flag_al_log(self):
        repo = _mock_repo()
        h = _mock_handler("HandlerA", _ok_result("HandlerA"))
        orch = CommessaPushOrchestrator(repo, [h])

        report = orch.run(dry_run=True)

        self.assertTrue(report.dry_run)
        # ⚠️ `dry_run` si dichiara all'APERTURA: e' una proprieta' del giro, nota
        #    prima che il giro produca qualcosa. La chiusura porta solo l'esito.
        repo.start_push_run.assert_called_once()
        self.assertTrue(repo.start_push_run.call_args.kwargs["dry_run"])
        repo.close_push_run.assert_called_once()
        # `sorgente_uid=None` aggiunto alla signature handler.run dopo
        # introduzione del push singolo (PR1 sviluppo-push-singolo-preventivo);
        # `righe_ids=None` dopo lo smistamento selettivo (Pannello Smistamento).
        h.run.assert_called_once_with(dry_run=True, sorgente_uid=None, righe_ids=None)

    # Scopo: push_log_id nel report corrisponde all'id restituito dall'APERTURA
    # del giro — che ora esiste fin dal primo istante, non a fine corsa.
    def test_run_push_log_id_valorizzato(self):
        repo = _mock_repo(push_log_id=42)
        h = _mock_handler("HandlerA", _ok_result("HandlerA"))
        orch = CommessaPushOrchestrator(repo, [h])

        report = orch.run()

        self.assertEqual(report.push_log_id, 42)

    # Scopo: eccezione in HandlerA non interrompe HandlerB — isolamento garantito.
    def test_run_isolamento_handler_continua_dopo_eccezione(self):
        repo = _mock_repo()
        h_fail = MagicMock(spec=BaseSourceHandler)
        h_fail.name = "HandlerA"
        h_fail.sorgente_codice = "SRC_A"
        h_fail.run.side_effect = RuntimeError("crash")
        h_ok = _mock_handler("HandlerB", _ok_result("HandlerB", created=3))
        orch = CommessaPushOrchestrator(repo, [h_fail, h_ok])

        report = orch.run()

        h_ok.run.assert_called_once()
        b_result = next(r for r in report.handlers if r.handler_name == "HandlerB")
        self.assertEqual(b_result.created, 3)
        self.assertEqual(b_result.errors, [])

    # Scopo: as_risultato include chiavi per tutti gli handler eseguiti.
    def test_run_risultato_jsonb_include_tutti_handler(self):
        repo = _mock_repo()
        h1 = _mock_handler("HandlerA", HandlerResult(handler_name="HandlerA", sorgente_codice="SRC_A", created=2, updated=1))
        h2 = _mock_handler("HandlerB", HandlerResult(handler_name="HandlerB", sorgente_codice="SRC_B", skipped=5))
        orch = CommessaPushOrchestrator(repo, [h1, h2])

        report = orch.run()

        risultato = report.as_risultato()
        self.assertIn("HandlerA", risultato)
        self.assertIn("HandlerB", risultato)
        self.assertEqual(risultato["HandlerA"]["created"], 2)
        self.assertEqual(risultato["HandlerB"]["skipped"], 5)
        call_kwargs = repo.close_push_run.call_args.kwargs
        # ⭐ Il `risultato` scritto e' annidato: `handlers` + `perimetro`
        #    (BE-3a). `as_risultato()` resta la sola mappa degli handler.
        self.assertIn("HandlerA", call_kwargs["risultato"]["handlers"])

    # Scopo: lock non acquisito → PushReport SKIPPED, nessun handler eseguito, nessun log.
    def test_run_skipped_quando_lock_non_acquisito(self):
        self._mock_acquire.return_value = False
        repo = _mock_repo()
        h = _mock_handler("HandlerA", _ok_result("HandlerA"))
        orch = CommessaPushOrchestrator(repo, [h])

        report = orch.run()

        self.assertEqual(report.stato, "SKIPPED")
        self.assertEqual(report.durata_ms, 0)
        self.assertEqual(report.handlers, [])
        self.assertIsNone(report.push_log_id)
        h.run.assert_not_called()
        # ⭐ Un giro saltato per lock occupato non lascia NESSUNA riga: non si
        #    apre e non si chiude. Diversamente da un giro interrotto, che la
        #    riga IN_ESECUZIONE la lascia — ed e' la distinzione che il registro
        #    deve saper fare.
        repo.start_push_run.assert_not_called()
        repo.close_push_run.assert_not_called()

    # Scopo: lock rilasciato dopo run (anche se handler fallisce).
    def test_run_rilascia_lock_dopo_esecuzione(self):
        repo = _mock_repo()
        h = MagicMock(spec=BaseSourceHandler)
        h.name = "HandlerA"
        h.sorgente_codice = "SRC_A"
        h.run.side_effect = RuntimeError("crash")
        orch = CommessaPushOrchestrator(repo, [h])

        report = orch.run()

        self.assertEqual(report.stato, "ERRORE")
        self._mock_release.assert_called()

    # Scopo: ⭐ IL GIRO SI APRE PRIMA DI PRODURRE QUALCOSA (BE-3b, D-3).
    #
    #        E' l'ordine il punto, non la scrittura: fino al 2026-08-22 la riga
    #        nasceva a FINE corsa, ed e' la ragione per cui l'evento d'avvio
    #        citava `entity_id = 0` — non un segnaposto, un id che non esisteva
    #        ancora. Un test che si limitasse a «la riga viene scritta»
    #        passerebbe anche con la sequenza vecchia.
    def test_run_apre_il_giro_prima_di_eseguire_gli_handler(self):
        ordine: list[str] = []
        repo = _mock_repo(push_log_id=7)
        repo.start_push_run.side_effect = lambda **kw: (ordine.append("apre"), 7)[1]
        h = _mock_handler("HandlerA", _ok_result("HandlerA"))
        h.run.side_effect = lambda **kw: (
            ordine.append("handler"), _ok_result("HandlerA")
        )[1]
        orch = CommessaPushOrchestrator(repo, [h])

        orch.run()

        self.assertEqual(ordine, ["apre", "handler"])

    # Scopo: si chiude ESATTAMENTE il giro che si e' aperto, con un esito finale.
    #
    # ⚠️ L'`id` non e' un dettaglio: `fn_close_commessa_push_run` chiude solo
    #    una riga IN_ESECUZIONE, e su un id sbagliato solleva
    #    `E_COMMESSA_PUSH_RUN_NON_APERTO`. Passare l'id giusto e' la meta' del
    #    contratto della coppia.
    def test_run_chiude_il_giro_che_ha_aperto(self):
        repo = _mock_repo(push_log_id=99)
        h = _mock_handler("HandlerA", _ok_result("HandlerA"))
        orch = CommessaPushOrchestrator(repo, [h])

        report = orch.run()

        kw = repo.close_push_run.call_args.kwargs
        self.assertEqual(kw["push_log_id"], 99)
        self.assertEqual(kw["push_log_id"], report.push_log_id)
        # ⛔ Mai IN_ESECUZIONE in chiusura: la funzione DB lo rifiuta con
        #    E_COMMESSA_PUSH_RUN_STATO_NON_FINALE.
        # ⚠️ Non si ri-elenca qui il vocabolario dei tre esiti: sarebbe la
        #    quarta copia di un elenco che vive gia' nel CHECK di tabella, nel
        #    guard della funzione e in `_compute_stato`. Si asserisce invece che
        #    lo stato scritto sia ESATTAMENTE quello calcolato — che e' la cosa
        #    che questo test deve sapere.
        self.assertNotEqual(kw["stato"], "IN_ESECUZIONE")
        self.assertEqual(kw["stato"], report.stato)

    # Scopo: ⭐ UN GIRO INTERROTTO RESTA APERTO, e non sparisce.
    #
    #        E' il guadagno che la riga-in-testa porta con se': prima, un push
    #        che moriva a meta' non scriveva niente — nessuno sapeva che fosse
    #        stato tentato. Ora la riga IN_ESECUZIONE rimasta li' e' l'unica
    #        prova che qualcosa e' partito e non e' tornato.
    #
    # ⚠️ Il verso e' che la chiusura NON avviene: se un domani qualcuno
    #    avvolgesse il ciclo in un `try/finally` che chiude comunque, il giro
    #    interrotto tornerebbe a somigliare a uno concluso — e questo test
    #    diventerebbe rosso, che e' esattamente il suo mestiere.
    def test_giro_interrotto_resta_aperto(self):
        repo = _mock_repo(push_log_id=13)
        h = _mock_handler("HandlerA", _ok_result("HandlerA"))
        # Non un errore di handler (quello e' isolato e diventa PARZIALE): un
        # guasto del giro stesso, come un processo che muore.
        h.run.side_effect = KeyboardInterrupt("il processo muore")
        orch = CommessaPushOrchestrator(repo, [h])

        with self.assertRaises(KeyboardInterrupt):
            orch.run()

        repo.start_push_run.assert_called_once()
        repo.close_push_run.assert_not_called()

    # Scopo: ⛔ IL GIRO DI PUSH NON SCRIVE SUL GIORNALE (BE-3a, D-3).
    #
    #        Il verso e' l'ASSENZA, e va presidiato proprio perche' l'assenza
    #        non si nota: `PUSH_STARTED`/`PUSH_COMPLETED` scrivevano
    #        `entity_type='TASK_RUN'`, che dal 2026-08-22 e' a catalogo con
    #        `modo_risoluzione_emittente = NULL` — il giornale lo rifiuta, e
    #        con `entity_id = 0` lo rifiuterebbe comunque. Rimetterle qui «per
    #        avere piu' tracciabilita'» farebbe fallire il push all'AVVIO,
    #        cioe' esattamente il difetto da cui si viene.
    #
    #        Che l'esito del giro resti registrato lo dicono il test 7
    #        (`push_log_id` valorizzato) e il 9 (il risultato per handler).
    def test_run_non_scrive_su_event_log(self):
        repo = _mock_repo(push_log_id=42)
        h = _mock_handler("HandlerA", _ok_result("HandlerA"))
        orch = CommessaPushOrchestrator(repo, [h])

        report = orch.run()

        repo.log_event.assert_not_called()
        # Il giro resta registrato dove ha un senso: nel suo log di run.
        repo.close_push_run.assert_called_once()
        self.assertEqual(report.push_log_id, 42)
        self.assertEqual(report.stato, "COMPLETATO")

    # Scopo: sorgente_uid valorizzato → propagato agli handler.run e nel
    # `risultato.perimetro` di commesse_push_log, per tracciabilita' del push
    # singolo. ⭐ Prima viveva nel payload di `PUSH_STARTED`: uscito l'evento
    # dal giornale (BE-3a), «su quale documento era stato chiesto il push»
    # sarebbe sparito senza questa sede.
    def test_run_with_sorgente_uid_propagated_to_handlers_and_perimetro(self):
        repo = _mock_repo(push_log_id=99)
        h = _mock_handler("HandlerPreventivi", _ok_result("HandlerPreventivi", sorgente_codice="PREVENTIVO"), sorgente_codice="PREVENTIVO")
        orch = CommessaPushOrchestrator(repo, [h])

        orch.run(source_types=["PREVENTIVO"], sorgente_uid=42)

        # Handler.run riceve dry_run=False + sorgente_uid=42 (+righe_ids=None:
        # nessun filtro sottoinsieme righe in questo run).
        h.run.assert_called_once_with(dry_run=False, sorgente_uid=42, righe_ids=None)

        # Il perimetro del giro finisce in commesse_push_log.risultato.
        perimetro = repo.close_push_run.call_args.kwargs["risultato"]["perimetro"]
        self.assertEqual(perimetro["sorgente_uid"], 42)
        self.assertEqual(perimetro["source_types"], ["PREVENTIVO"])

    # Scopo: sorgente_uid omesso → handler.run riceve sorgente_uid=None
    # (regressione: comportamento batch invariato).
    def test_run_without_sorgente_uid_passes_none_to_handlers(self):
        repo = _mock_repo()
        h = _mock_handler("HandlerA", _ok_result("HandlerA"))
        orch = CommessaPushOrchestrator(repo, [h])

        orch.run()

        h.run.assert_called_once_with(dry_run=False, sorgente_uid=None, righe_ids=None)

    # Scopo: righe_ids valorizzato (smistamento selettivo) → propagato a
    # handler.run e nel `risultato.perimetro` di commesse_push_log.
    def test_run_with_righe_ids_propagated_to_handlers_and_perimetro(self):
        repo = _mock_repo()
        h = _mock_handler("HandlerPreventivi", _ok_result("HandlerPreventivi", sorgente_codice="PREVENTIVO"), sorgente_codice="PREVENTIVO")
        orch = CommessaPushOrchestrator(repo, [h])

        orch.run(source_types=["PREVENTIVO"], sorgente_uid=42, righe_ids=[7, 9])

        h.run.assert_called_once_with(dry_run=False, sorgente_uid=42, righe_ids=[7, 9])
        perimetro = repo.close_push_run.call_args.kwargs["risultato"]["perimetro"]
        self.assertEqual(perimetro["righe_ids"], [7, 9])
