# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari funzioni commesse_service.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) CommesseServiceTests.test_pr_run_commesse_push_ok
2) CommesseServiceTests.test_pr_run_commesse_push_skipped
3) CommesseServiceTests.test_fn_get_commesse_push_log_ok
4) CommesseServiceTests.test_fn_get_commesse_push_log_not_found
5) CommesseServiceTests.test_fn_get_commessa_stato_ok
6) CommesseServiceTests.test_fn_get_commessa_stato_not_found
7) CommesseServiceTests.test_fn_list_commessa_attivita_ok
8) CommesseServiceTests.test_fn_list_commessa_attivita_invalid_limit
9) CommesseServiceTests.test_pr_run_commesse_push_invalid_source_types
10) CommesseServiceTests.test_build_handlers_only_active_sources
11) CommesseServiceTests.test_pr_run_commesse_push_one_ok_passa_sorgente_uid
12) CommesseServiceTests.test_pr_run_commesse_push_one_codice_sorgente_invalido
13) CommesseServiceTests.test_pr_run_commesse_push_one_sorgente_uid_invalido
13a) CommesseServiceTests.test_pr_run_commesse_push_one_parziale_solleva_all_or_nothing
13b) CommesseServiceTests.test_pr_run_commesse_push_one_errore_solleva_all_or_nothing
13c) CommesseServiceTests.test_pr_run_commesse_push_one_skipped_passa_dritto
13d) CommesseServiceTests.test_pr_run_commesse_push_one_dry_run_parziale_non_solleva
13e) CommesseServiceTests.test_pr_run_commesse_push_one_ponte_emittibilita
13f) CommesseServiceTests.test_pr_run_commesse_push_one_ponte_skip_se_gia_pronta
13g) CommesseServiceTests.test_pr_run_commesse_push_one_dry_run_non_attiva_ponte
13h) CommesseServiceTests.test_pr_run_commesse_push_batch_ponte_best_effort
14) CommesseServiceTests.test_variazione_eccezionale_ok
12) CommesseServiceTests.test_variazione_eccezionale_commessa_stato_bloccato
13) CommesseServiceTests.test_variazione_eccezionale_riga_fatturata_bloccata
14) CommesseServiceTests.test_variazione_eccezionale_senza_motivo
15) CommesseServiceTests.test_sblocca_prezzo_ok
16) CommesseServiceTests.test_sblocca_prezzo_non_bloccato
17) CommesseServiceTests.test_riallinea_prezzo_ok
18) CommesseServiceTests.test_riallinea_prezzo_bloccato
19) CommesseServiceTests.test_riallinea_prezzo_versione_cambiata_senza_conferma

Azioni di stato commessa (#7 — fn_available_actions_commessa + cambia stato):
20) CommesseServiceTests.test_fn_get_commessa_stato_include_capabilities
21) CommesseServiceTests.test_cambia_stato_commessa_ok
22) CommesseServiceTests.test_cambia_stato_commessa_azione_non_ammessa
23) CommesseServiceTests.test_cambia_stato_commessa_not_found
24) CommesseServiceTests.test_cambia_stato_commessa_validation

CommesseApprovazioneServiceTests (A-1/A-2 cockpit):
- test_approva_commessa_attivita_tutte / _selezione / _righe_ids_invalido
- test_approva_commessa_attivita_not_found / _id_invalido
- test_approva_attivita_competenza_ok / _vuota / _senza_mese
- test_approva_attivita_competenza_filtro_commesse / _all_or_nothing
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.commesse_push_orchestrator import PushReport
from apps.vendite.services.commesse_source_handlers import HandlerResult


class CommesseServiceTests(TestCase):

    # --- pr_run_commesse_push ---

    # Scopo: push ok → stato COMPLETATO con handler nel risultato.
    @patch("apps.vendite.services.commesse_service.CommessaPushOrchestrator")
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    @patch("apps.vendite.services.commesse_service._build_handlers")
    def test_pr_run_commesse_push_ok(self, mock_build, mock_repo_cls, mock_orch_cls):
        from apps.vendite.services.commesse_service import pr_run_commesse_push

        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_build.return_value = []

        report = PushReport(
            dry_run=False,
            stato="COMPLETATO",
            handlers=[HandlerResult(handler_name="HandlerA", created=3)],
            push_log_id=10,
            durata_ms=120,
        )
        mock_orch_cls.return_value.run.return_value = report

        result = pr_run_commesse_push(dry_run=False)

        self.assertEqual(result["stato"], "COMPLETATO")
        self.assertEqual(result["push_log_id"], 10)
        self.assertEqual(len(result["handlers"]), 1)
        self.assertEqual(result["handlers"][0]["handler_name"], "HandlerA")
        self.assertEqual(result["handlers"][0]["created"], 3)

    # Scopo: lock non acquisito → stato SKIPPED, nessun handler.
    @patch("apps.vendite.services.commesse_service.CommessaPushOrchestrator")
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    @patch("apps.vendite.services.commesse_service._build_handlers")
    def test_pr_run_commesse_push_skipped(self, mock_build, mock_repo_cls, mock_orch_cls):
        from apps.vendite.services.commesse_service import pr_run_commesse_push

        mock_repo_cls.return_value = MagicMock()
        mock_build.return_value = []

        report = PushReport(dry_run=False, stato="SKIPPED", durata_ms=0)
        mock_orch_cls.return_value.run.return_value = report

        result = pr_run_commesse_push()

        self.assertEqual(result["stato"], "SKIPPED")
        self.assertIsNone(result["push_log_id"])
        self.assertEqual(result["handlers"], [])

    # Scopo: source_types con codice non riconosciuto → ServiceError validazione.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_pr_run_commesse_push_invalid_source_types(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import pr_run_commesse_push

        mock_repo_cls.return_value.list_active_push_sources.return_value = ["PREVENTIVO"]

        with self.assertRaises(ServiceError) as ctx:
            pr_run_commesse_push(source_types=["SORGENTE_INESISTENTE"])
        self.assertEqual(ctx.exception.code, "E_COMMESSA_VALIDATION")
        self.assertIn("SORGENTE_INESISTENTE", ctx.exception.detail)
        self.assertIn("PREVENTIVO", ctx.exception.detail)

    # Scopo: _build_handlers costruisce solo handler per sorgenti attive in DB.
    def test_build_handlers_only_active_sources(self):
        from apps.vendite.services.commesse_service import _build_handlers

        mock_repo = MagicMock()
        mock_repo.list_active_push_sources.return_value = ["PREVENTIVO", "CONTRATTO"]

        handlers = _build_handlers(mock_repo)

        self.assertEqual(len(handlers), 2)
        codici = [h.sorgente_codice for h in handlers]
        self.assertEqual(codici, ["PREVENTIVO", "CONTRATTO"])

    # --- pr_run_commesse_push_one ---

    # Scopo: push singolo ok → orchestrator chiamato con source_types=[codice]
    # e sorgente_uid valorizzato. Payload ritorno equivalente al batch.
    @patch("apps.vendite.services.commesse_service.CommessaPushOrchestrator")
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    @patch("apps.vendite.services.commesse_service._build_handlers")
    def test_pr_run_commesse_push_one_ok_passa_sorgente_uid(self, mock_build, mock_repo_cls, mock_orch_cls):
        from apps.vendite.services.commesse_service import pr_run_commesse_push_one

        mock_repo_cls.return_value = MagicMock()
        # Handler "PREVENTIVO" attivo nel registry simulato.
        handler_mock = MagicMock()
        handler_mock.sorgente_codice = "PREVENTIVO"
        mock_build.return_value = [handler_mock]

        report = PushReport(
            dry_run=False,
            stato="COMPLETATO",
            handlers=[HandlerResult(handler_name="HandlerPreventivi", created=2)],
            push_log_id=11,
            durata_ms=80,
        )
        mock_orch_cls.return_value.run.return_value = report

        result = pr_run_commesse_push_one(sorgente_codice="PREVENTIVO", sorgente_uid=42)

        # Orchestrator chiamato con i parametri attesi (righe_ids=None:
        # push completo, nessun sottoinsieme selettivo).
        mock_orch_cls.return_value.run.assert_called_once_with(
            source_types=["PREVENTIVO"],
            dry_run=False,
            sorgente_uid=42,
            righe_ids=None,
        )
        # Payload coerente con pr_run_commesse_push (forma identica).
        self.assertEqual(result["stato"], "COMPLETATO")
        self.assertEqual(result["push_log_id"], 11)
        self.assertEqual(result["durata_ms"], 80)
        self.assertEqual(result["handlers"][0]["handler_name"], "HandlerPreventivi")

    # --- Ponte emittibilita' post-push (V9 generalizzato) ---

    def _push_one_con_commesse(self, mock_build, mock_orch_cls, *, commesse_ids,
                               dry_run=False, stato="COMPLETATO"):
        """Setup comune: handler PREVENTIVO attivo + report con commesse toccate."""
        handler_mock = MagicMock()
        handler_mock.sorgente_codice = "PREVENTIVO"
        mock_build.return_value = [handler_mock]
        report = PushReport(
            dry_run=dry_run,
            stato=stato,
            handlers=[HandlerResult(
                handler_name="HandlerPreventivi", created=2,
                commesse_ids=set(commesse_ids),
            )],
            push_log_id=11,
            durata_ms=80,
        )
        mock_orch_cls.return_value.run.return_value = report

    # Scopo: push singolo COMPLETATO → ogni commessa toccata viene resa
    # emittibile (righe APPROVATA + testata PRONTA_FATTURAZIONE) nella stessa
    # transazione, e le commesse sono esposte nel payload di ritorno.
    @patch("apps.vendite.services.commesse_service.CommessaPushOrchestrator")
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    @patch("apps.vendite.services.commesse_service._build_handlers")
    def test_pr_run_commesse_push_one_ponte_emittibilita(self, mock_build, mock_repo_cls, mock_orch_cls):
        from apps.vendite.services.commesse_service import pr_run_commesse_push_one

        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_repo.get_commessa_stato_codice.return_value = "BOZZA"
        self._push_one_con_commesse(mock_build, mock_orch_cls, commesse_ids={7701})

        result = pr_run_commesse_push_one(
            sorgente_codice="PREVENTIVO", sorgente_uid=42, user="alice",
        )

        mock_repo.approva_commessa_attivita.assert_called_once_with(
            commessa_id=7701, user="alice",
        )
        mock_repo.cambia_stato_commessa.assert_called_once_with(
            commessa_id=7701, nuovo_stato="PRONTA_FATTURAZIONE", user="alice",
        )
        self.assertEqual(result["commesse_ids"], [7701])

    # Scopo: commessa multi-sorgente GIA' PRONTA → approva comunque le nuove
    # righe ma NON ri-transita PRONTA→PRONTA (fn_cambia_stato non ammette da=a).
    @patch("apps.vendite.services.commesse_service.CommessaPushOrchestrator")
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    @patch("apps.vendite.services.commesse_service._build_handlers")
    def test_pr_run_commesse_push_one_ponte_skip_se_gia_pronta(self, mock_build, mock_repo_cls, mock_orch_cls):
        from apps.vendite.services.commesse_service import pr_run_commesse_push_one

        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_repo.get_commessa_stato_codice.return_value = "PRONTA_FATTURAZIONE"
        self._push_one_con_commesse(mock_build, mock_orch_cls, commesse_ids={7701})

        pr_run_commesse_push_one(sorgente_codice="PREVENTIVO", sorgente_uid=42)

        mock_repo.approva_commessa_attivita.assert_called_once()
        mock_repo.cambia_stato_commessa.assert_not_called()

    # Scopo: dry-run non scrive → ponte NON attivato (nessuna approvazione,
    # nessuna transizione), ma le commesse simulate restano nel report.
    @patch("apps.vendite.services.commesse_service.CommessaPushOrchestrator")
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    @patch("apps.vendite.services.commesse_service._build_handlers")
    def test_pr_run_commesse_push_one_dry_run_non_attiva_ponte(self, mock_build, mock_repo_cls, mock_orch_cls):
        from apps.vendite.services.commesse_service import pr_run_commesse_push_one

        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        self._push_one_con_commesse(
            mock_build, mock_orch_cls, commesse_ids={7701}, dry_run=True,
        )

        result = pr_run_commesse_push_one(
            sorgente_codice="PREVENTIVO", sorgente_uid=42, dry_run=True,
        )

        mock_repo.approva_commessa_attivita.assert_not_called()
        mock_repo.cambia_stato_commessa.assert_not_called()
        self.assertEqual(result["commesse_ids"], [7701])

    # Scopo: batch best-effort — una commessa che fallisce il ponte finisce in
    # emittibilita_errors senza bloccare le altre ne' far fallire il run.
    @patch("apps.vendite.services.commesse_service.CommessaPushOrchestrator")
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    @patch("apps.vendite.services.commesse_service._build_handlers")
    def test_pr_run_commesse_push_batch_ponte_best_effort(self, mock_build, mock_repo_cls, mock_orch_cls):
        from apps.vendite.services.commesse_service import pr_run_commesse_push

        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_repo.get_commessa_stato_codice.return_value = "BOZZA"
        # La commessa 1 fallisce l'approvazione, la 2 passa.
        mock_repo.approva_commessa_attivita.side_effect = [
            RuntimeError("guard DB"), 1,
        ]
        mock_build.return_value = []
        report = PushReport(
            dry_run=False,
            stato="COMPLETATO",
            handlers=[HandlerResult(handler_name="HandlerA", commesse_ids={1, 2})],
            push_log_id=10,
            durata_ms=120,
        )
        mock_orch_cls.return_value.run.return_value = report

        result = pr_run_commesse_push(dry_run=False)

        self.assertEqual(result["commesse_ids"], [1, 2])
        self.assertEqual(len(result["emittibilita_errors"]), 1)
        self.assertIn("commessa_id=1", result["emittibilita_errors"][0])
        # La commessa 2 e' stata comunque portata a PRONTA.
        mock_repo.cambia_stato_commessa.assert_called_once_with(
            commessa_id=2, nuovo_stato="PRONTA_FATTURAZIONE", user=None,
        )

    # Scopo (osservabilita' guard tipo_doc): un fallimento del ponte col codice
    # E_COMMESSA_ATTIVITA_TIPO_DOC_OBBLIGATORIO e' classificato a parte
    # (emittibilita_tipo_doc_mancante) e tracciato in event_log (EMITTIBILITA_FALLITA).
    @patch("apps.vendite.services.commesse_service.CommessaPushOrchestrator")
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    @patch("apps.vendite.services.commesse_service._build_handlers")
    def test_pr_run_commesse_push_emittibilita_tipo_doc_mancante_osservabile(
        self, mock_build, mock_repo_cls, mock_orch_cls,
    ):
        from apps.vendite.services.commesse_service import pr_run_commesse_push

        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_repo.get_commessa_stato_codice.return_value = "BOZZA"
        # Commessa 1: guard tipo_doc (codice nel messaggio, come da fn_log_and_raise_error).
        # Commessa 2: errore generico. Commessa 3: ok.
        mock_repo.approva_commessa_attivita.side_effect = [
            RuntimeError("E_COMMESSA_ATTIVITA_TIPO_DOC_OBBLIGATORIO: Tipo documento fiscale obbligatorio..."),
            RuntimeError("guard DB generico"),
            1,
        ]
        mock_build.return_value = []
        report = PushReport(
            dry_run=False,
            stato="COMPLETATO",
            handlers=[HandlerResult(handler_name="HandlerA", commesse_ids={1, 2, 3})],
            push_log_id=10,
            durata_ms=120,
        )
        mock_orch_cls.return_value.run.return_value = report

        result = pr_run_commesse_push(dry_run=False)

        # Classificazione: solo la commessa 1 nel gruppo tipo_doc mancante.
        self.assertEqual(result["emittibilita_tipo_doc_mancante"], [1])
        self.assertEqual(len(result["emittibilita_errors"]), 2)
        # Evento durevole emesso con il riepilogo (incluso il tipo_doc mancante).
        mock_repo.log_event.assert_called_once()
        kw = mock_repo.log_event.call_args.kwargs
        self.assertEqual(kw["event_code"], "EMITTIBILITA_FALLITA")
        self.assertEqual(kw["severity"], "WARNING")
        self.assertEqual(kw["payload"]["tipo_doc_mancante_commesse"], [1])
        self.assertEqual(kw["payload"]["totale_falliti"], 2)

    # Scopo: codice sorgente non riconosciuto → ServiceError validazione.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    @patch("apps.vendite.services.commesse_service._build_handlers")
    def test_pr_run_commesse_push_one_codice_sorgente_invalido(self, mock_build, mock_repo_cls):
        from apps.vendite.services.commesse_service import pr_run_commesse_push_one

        mock_repo_cls.return_value = MagicMock()
        handler_mock = MagicMock()
        handler_mock.sorgente_codice = "PREVENTIVO"
        mock_build.return_value = [handler_mock]

        with self.assertRaises(ServiceError) as ctx:
            pr_run_commesse_push_one(sorgente_codice="SORGENTE_INESISTENTE", sorgente_uid=1)
        self.assertEqual(ctx.exception.code, "E_COMMESSA_VALIDATION")
        self.assertIn("SORGENTE_INESISTENTE", ctx.exception.detail)

    # Scopo: sorgente_uid non valido (None/0/negativo) → ServiceError validazione.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    @patch("apps.vendite.services.commesse_service._build_handlers")
    def test_pr_run_commesse_push_one_sorgente_uid_invalido(self, mock_build, mock_repo_cls):
        from apps.vendite.services.commesse_service import pr_run_commesse_push_one

        mock_repo_cls.return_value = MagicMock()
        handler_mock = MagicMock()
        handler_mock.sorgente_codice = "PREVENTIVO"
        mock_build.return_value = [handler_mock]

        for invalid_uid in (0, -1):
            with self.assertRaises(ServiceError) as ctx:
                pr_run_commesse_push_one(sorgente_codice="PREVENTIVO", sorgente_uid=invalid_uid)
            self.assertEqual(ctx.exception.code, "E_COMMESSA_VALIDATION")

    # Scopo: all-or-nothing su PARZIALE — l'orchestrator ritorna PARZIALE
    # (qualche riga fallita), pr_run_commesse_push_one solleva
    # E_COMMESSA_PUSH_PARZIALE_VIETATO con detail = primo errore handler.
    # L'atomic esterna rolla ogni scrittura: niente attivita orfane in commessa.
    @patch("apps.vendite.services.commesse_service.CommessaPushOrchestrator")
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    @patch("apps.vendite.services.commesse_service._build_handlers")
    def test_pr_run_commesse_push_one_parziale_solleva_all_or_nothing(
        self, mock_build, mock_repo_cls, mock_orch_cls,
    ):
        from apps.vendite.services.commesse_service import pr_run_commesse_push_one

        mock_repo_cls.return_value = MagicMock()
        handler_mock = MagicMock()
        handler_mock.sorgente_codice = "PREVENTIVO"
        mock_build.return_value = [handler_mock]

        report = PushReport(
            dry_run=False,
            stato="PARZIALE",
            handlers=[HandlerResult(
                handler_name="HandlerPreventivi",
                created=3,
                errors=["Errore riga segment_key=PREV:abc:R:4: ServiceError: ..."],
            )],
            push_log_id=99,
            durata_ms=42,
        )
        mock_orch_cls.return_value.run.return_value = report

        with self.assertRaises(ServiceError) as ctx:
            pr_run_commesse_push_one(sorgente_codice="PREVENTIVO", sorgente_uid=7)
        self.assertEqual(ctx.exception.code, "E_COMMESSA_PUSH_PARZIALE_VIETATO")
        self.assertIn("segment_key=PREV:abc:R:4", ctx.exception.detail)

    # Scopo: all-or-nothing su ERRORE — stesso pattern del PARZIALE
    # (ogni handler con errors → rollback totale + raise).
    @patch("apps.vendite.services.commesse_service.CommessaPushOrchestrator")
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    @patch("apps.vendite.services.commesse_service._build_handlers")
    def test_pr_run_commesse_push_one_errore_solleva_all_or_nothing(
        self, mock_build, mock_repo_cls, mock_orch_cls,
    ):
        from apps.vendite.services.commesse_service import pr_run_commesse_push_one

        mock_repo_cls.return_value = MagicMock()
        handler_mock = MagicMock()
        handler_mock.sorgente_codice = "PREVENTIVO"
        mock_build.return_value = [handler_mock]

        report = PushReport(
            dry_run=False,
            stato="ERRORE",
            handlers=[HandlerResult(
                handler_name="HandlerPreventivi",
                errors=["Exception: connessione DB persa"],
            )],
            push_log_id=100,
            durata_ms=15,
        )
        mock_orch_cls.return_value.run.return_value = report

        with self.assertRaises(ServiceError) as ctx:
            pr_run_commesse_push_one(sorgente_codice="PREVENTIVO", sorgente_uid=8)
        self.assertEqual(ctx.exception.code, "E_COMMESSA_PUSH_PARZIALE_VIETATO")

    # Scopo: dry_run con esito PARZIALE NON solleva — la simulazione e'
    # esente dall'all-or-nothing perche' non scrive nulla in DB (niente da
    # proteggere). L'utente vuole vedere la diagnostica delle righe che
    # fallirebbero, non un errore generico.
    @patch("apps.vendite.services.commesse_service.CommessaPushOrchestrator")
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    @patch("apps.vendite.services.commesse_service._build_handlers")
    def test_pr_run_commesse_push_one_dry_run_parziale_non_solleva(
        self, mock_build, mock_repo_cls, mock_orch_cls,
    ):
        from apps.vendite.services.commesse_service import pr_run_commesse_push_one

        mock_repo_cls.return_value = MagicMock()
        handler_mock = MagicMock()
        handler_mock.sorgente_codice = "PREVENTIVO"
        mock_build.return_value = [handler_mock]

        report = PushReport(
            dry_run=True,
            stato="PARZIALE",
            handlers=[HandlerResult(
                handler_name="HandlerPreventivi",
                created=3,
                errors=["Errore riga simulato"],
            )],
            push_log_id=101,
            durata_ms=5,
        )
        mock_orch_cls.return_value.run.return_value = report

        result = pr_run_commesse_push_one(
            sorgente_codice="PREVENTIVO", sorgente_uid=10, dry_run=True,
        )
        # Diagnostica esposta normalmente: caller decide cosa farne.
        self.assertEqual(result["stato"], "PARZIALE")
        self.assertTrue(result["dry_run"])

    # Scopo: SKIPPED (lock gia' acquisito da altro run) NON e' un errore di
    # dominio: nessun rollback, nessuna raise — l'utente vede il toast warn
    # "push gia' in corso" tramite la response JSON normale.
    @patch("apps.vendite.services.commesse_service.CommessaPushOrchestrator")
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    @patch("apps.vendite.services.commesse_service._build_handlers")
    def test_pr_run_commesse_push_one_skipped_passa_dritto(
        self, mock_build, mock_repo_cls, mock_orch_cls,
    ):
        from apps.vendite.services.commesse_service import pr_run_commesse_push_one

        mock_repo_cls.return_value = MagicMock()
        handler_mock = MagicMock()
        handler_mock.sorgente_codice = "PREVENTIVO"
        mock_build.return_value = [handler_mock]

        report = PushReport(dry_run=False, stato="SKIPPED", durata_ms=0)
        mock_orch_cls.return_value.run.return_value = report

        result = pr_run_commesse_push_one(sorgente_codice="PREVENTIVO", sorgente_uid=9)
        self.assertEqual(result["stato"], "SKIPPED")

    # --- fn_get_commesse_push_log ---

    # Scopo: push log trovato → restituisce dict con i dati.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_fn_get_commesse_push_log_ok(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import fn_get_commesse_push_log

        mock_repo_cls.return_value.get_push_log.return_value = {
            "id": 5,
            "run_at": "2026-02-26T10:00:00",
            "dry_run": False,
            "source_types": ["SRC_A"],
            "risultato": {"HandlerA": {"created": 1}},
            "stato": "COMPLETATO",
            "durata_ms": 100,
        }

        result = fn_get_commesse_push_log(push_log_id=5)

        self.assertEqual(result["id"], 5)
        self.assertEqual(result["stato"], "COMPLETATO")

    # Scopo: push log non trovato → ServiceError.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_fn_get_commesse_push_log_not_found(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import fn_get_commesse_push_log

        mock_repo_cls.return_value.get_push_log.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            fn_get_commesse_push_log(push_log_id=999)
        self.assertEqual(ctx.exception.code, "E_COMMESSA_PUSH_LOG_NOT_FOUND")

    # --- fn_get_commessa_stato ---

    # Scopo: commessa trovata → restituisce commessa_id + stato_codice_interno +
    #        flag governance e contatori propagati dal repo (ApiCommessaStato).
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_fn_get_commessa_stato_ok(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import fn_get_commessa_stato

        repo = mock_repo_cls.return_value
        # stato_codice_interno deriva dal blob capability (stato_codice), non più
        # da un round-trip dedicato get_commessa_stato_codice.
        repo.get_capabilities.return_value = {
            "available_actions": [], "can_change_state": False,
            "can_edit_righe": True, "is_emittibile": True,
            "stato_codice": "PRONTA_FATTURAZIONE",
        }
        repo.get_commessa_stato.return_value = {
            "stato_commessa_id": 4,
            "stato_commessa": "PRONTA_FATTURAZIONE",
            "chiude_commessa": False,
            "emittibile": True,
            "modificabile": True,
            "total_attivita": 10,
            "total_approvate": 8,
            "total_non_approvate": 2,
            "total_emesse": 5,
            "total_non_emesse": 5,
            "total_prezzo_da_riallineare": 0,
            "last_update": "2026-06-15T10:00:00",
        }

        result = fn_get_commessa_stato(commessa_id=1)

        self.assertEqual(result["commessa_id"], 1)
        self.assertEqual(result["stato_codice_interno"], "PRONTA_FATTURAZIONE")
        # de-dup: nessun round-trip dedicato a get_commessa_stato_codice
        repo.get_commessa_stato_codice.assert_not_called()
        self.assertTrue(result["emittibile"])
        self.assertEqual(result["total_attivita"], 10)
        self.assertEqual(result["total_non_emesse"], 5)

    # Scopo: commessa non trovata → ServiceError.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_fn_get_commessa_stato_not_found(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import fn_get_commessa_stato

        mock_repo_cls.return_value.get_commessa_stato.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            fn_get_commessa_stato(commessa_id=999)
        self.assertEqual(ctx.exception.code, "E_COMMESSA_NOT_FOUND")

    # --- azioni di stato commessa (#7) ---

    # Scopo: fn_get_commessa_stato propaga il blob capabilities dal repo.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_fn_get_commessa_stato_include_capabilities(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import fn_get_commessa_stato

        repo = mock_repo_cls.return_value
        repo.get_commessa_stato_codice.return_value = "PRONTA_FATTURAZIONE"
        repo.get_commessa_stato.return_value = {
            "stato_commessa_id": 4, "stato_commessa": "PRONTA_FATTURAZIONE",
            "chiude_commessa": False, "emittibile": True, "modificabile": True,
            "total_attivita": 1, "total_approvate": 1, "total_non_approvate": 0,
            "total_emesse": 0, "total_non_emesse": 1, "total_prezzo_da_riallineare": 0,
            "last_update": None,
        }
        caps = {
            "available_actions": [
                {"key": "chiudi", "target_state": "CHIUSA"},
                {"key": "annulla", "target_state": "ANNULLATA"},
            ],
            "can_change_state": True, "can_edit_righe": True,
            "is_emittibile": True, "stato_codice": "PRONTA_FATTURAZIONE",
        }
        repo.get_capabilities.return_value = caps

        result = fn_get_commessa_stato(commessa_id=1)

        self.assertEqual(result["capabilities"], caps)
        repo.get_capabilities.assert_called_once_with(1)

    # Scopo: transizione utente ammessa → delega a repo.cambia_stato_commessa.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_cambia_stato_commessa_ok(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import cambia_stato_commessa

        repo = mock_repo_cls.return_value
        repo.get_capabilities.return_value = {
            "available_actions": [{"key": "chiudi", "target_state": "CHIUSA"}],
            "stato_codice": "PRONTA_FATTURAZIONE",
        }
        repo.cambia_stato_commessa.return_value = {
            "commessa_id": 1, "stato_da": "PRONTA_FATTURAZIONE", "stato_a": "CHIUSA",
        }

        result = cambia_stato_commessa(commessa_id=1, nuovo_stato="CHIUSA", user="op1")

        self.assertEqual(result["stato_a"], "CHIUSA")
        repo.cambia_stato_commessa.assert_called_once_with(
            commessa_id=1, nuovo_stato="CHIUSA", user="op1",
        )

    # Scopo: difesa applicativa — stato non tra le azioni utente → errore, no UPDATE.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_cambia_stato_commessa_azione_non_ammessa(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import cambia_stato_commessa

        repo = mock_repo_cls.return_value
        # solo 'chiudi' ammessa: forzare →PRONTA (automatica) deve essere respinto
        repo.get_capabilities.return_value = {
            "available_actions": [{"key": "chiudi", "target_state": "CHIUSA"}],
            "stato_codice": "PRONTA_FATTURAZIONE",
        }

        with self.assertRaises(ServiceError) as ctx:
            cambia_stato_commessa(commessa_id=1, nuovo_stato="PRONTA_FATTURAZIONE")
        self.assertEqual(ctx.exception.code, "E_COMMESSA_AZIONE_NON_AMMESSA")
        repo.cambia_stato_commessa.assert_not_called()

    # Scopo: capabilities vuoto (fn NULL) → commessa non trovata.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_cambia_stato_commessa_not_found(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import cambia_stato_commessa

        repo = mock_repo_cls.return_value
        repo.get_capabilities.return_value = {}

        with self.assertRaises(ServiceError) as ctx:
            cambia_stato_commessa(commessa_id=999, nuovo_stato="CHIUSA")
        self.assertEqual(ctx.exception.code, "E_COMMESSA_NOT_FOUND")
        repo.cambia_stato_commessa.assert_not_called()

    # Scopo: input non valido (nuovo_stato vuoto) → validazione, nessun lookup.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_cambia_stato_commessa_validation(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import cambia_stato_commessa

        with self.assertRaises(ServiceError) as ctx:
            cambia_stato_commessa(commessa_id=1, nuovo_stato="  ")
        self.assertEqual(ctx.exception.code, "E_COMMESSA_VALIDATION")
        mock_repo_cls.return_value.cambia_stato_commessa.assert_not_called()

    # --- fn_list_commessa_attivita ---

    # Scopo: lista attivita → restituisce dict con commessa_id e dati paginati.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_fn_list_commessa_attivita_ok(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import fn_list_commessa_attivita

        mock_repo_cls.return_value.list_commessa_attivita.return_value = {
            "count": 0,
            "rows": [],
        }

        result = fn_list_commessa_attivita(commessa_id=1, limit=50, offset=0)

        self.assertEqual(result["commessa_id"], 1)
        self.assertEqual(result["count"], 0)

    # Scopo: limit fuori range → ServiceError validazione.
    def test_fn_list_commessa_attivita_invalid_limit(self):
        from apps.vendite.services.commesse_service import fn_list_commessa_attivita

        with self.assertRaises(ServiceError) as ctx:
            fn_list_commessa_attivita(commessa_id=1, limit=500, offset=0)
        self.assertEqual(ctx.exception.code, "E_COMMESSA_VALIDATION")

    # --- N7: Variazione prezzo eccezionale ---

    _ATT_BASE = {
        "id": 501,
        "commessa_id": 10,
        "prezzo_snapshot": "45.0000000000",
        "prezzo_bloccato": False,
        "listino_versione_id": 101,
        "listino_riga_id": 301,
        "pricing_mode": "FIXED",
        "prezzo_da_riallineare": False,
        "articolo_id": "019bbee2-5f6a-704f-bbd0-34ed84db252d",
        "uom_id": 1,
        "data_attivita": "2026-04-01",
        "meta": None,
        "commessa_stato": "BOZZA",
        "commessa_modificabile": True,
        "af_id": 601,
        "af_prezzo_unitario": "45.0000000000",
        "af_prezzo_bloccato": False,
        "fattura_riga_id": None,
    }

    # Scopo: N7 - variazione eccezionale su commessa modificabile OK.
    @patch("apps.vendite.services.commesse_service.transaction.atomic")
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_variazione_eccezionale_ok(self, mock_repo_cls, mock_atomic):
        from apps.vendite.services.commesse_service import fn_variazione_prezzo_eccezionale

        repo = mock_repo_cls.return_value
        repo.get_attivita_pricing.return_value = dict(self._ATT_BASE)

        result = fn_variazione_prezzo_eccezionale(10, 501, {"prezzo": "42.00", "motivo": "sconto annuale"})

        self.assertEqual(result["prezzo_nuovo"], "42.00")
        self.assertTrue(result["prezzo_bloccato"])
        repo.update_attivita_prezzo.assert_called_once()
        call_kwargs = repo.update_attivita_prezzo.call_args.kwargs
        self.assertTrue(call_kwargs["prezzo_bloccato"])

    # Scopo: N7 - commessa in stato non modificabile rifiutata (flag data-driven
    #        stati_commessa.modificabile=false, es. CHIUSA/ANNULLATA).
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_variazione_eccezionale_commessa_stato_bloccato(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import fn_variazione_prezzo_eccezionale

        repo = mock_repo_cls.return_value
        att = dict(self._ATT_BASE)
        att["commessa_stato"] = "CHIUSA"
        att["commessa_modificabile"] = False
        repo.get_attivita_pricing.return_value = att

        with self.assertRaises(ServiceError) as ctx:
            fn_variazione_prezzo_eccezionale(10, 501, {"prezzo": "42.00", "motivo": "test"})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VARIAZIONE_PREZZO_NON_AMMESSA")

    # Scopo: N7 - riga gia` fatturata bloccata.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_variazione_eccezionale_riga_fatturata_bloccata(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import fn_variazione_prezzo_eccezionale

        repo = mock_repo_cls.return_value
        att = dict(self._ATT_BASE)
        att["fattura_riga_id"] = 999
        repo.get_attivita_pricing.return_value = att

        with self.assertRaises(ServiceError) as ctx:
            fn_variazione_prezzo_eccezionale(10, 501, {"prezzo": "42.00", "motivo": "test"})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VARIAZIONE_PREZZO_NON_AMMESSA")

    # Scopo: N7 - senza motivo rifiutata.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_variazione_eccezionale_senza_motivo(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import fn_variazione_prezzo_eccezionale

        repo = mock_repo_cls.return_value
        repo.get_attivita_pricing.return_value = dict(self._ATT_BASE)

        with self.assertRaises(ServiceError) as ctx:
            fn_variazione_prezzo_eccezionale(10, 501, {"prezzo": "42.00", "motivo": ""})
        self.assertEqual(ctx.exception.code, "E_COMMESSA_VALIDATION")

    # Scopo: X1 regressione - meta JSON malformato sulla riga -> 400
    #        E_VENDITE_VALIDATION, non un 500. Prima del fix il
    #        _parse_meta_json locale faceva json.loads bubble-ando il ValueError.
    @patch("apps.vendite.services.commesse_service.transaction.atomic")
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_variazione_eccezionale_meta_malformato_rifiutata(self, mock_repo_cls, mock_atomic):
        from apps.vendite.services.commesse_service import fn_variazione_prezzo_eccezionale

        repo = mock_repo_cls.return_value
        att = dict(self._ATT_BASE)
        att["meta"] = "{non-json"
        repo.get_attivita_pricing.return_value = att

        with self.assertRaises(ServiceError) as ctx:
            fn_variazione_prezzo_eccezionale(10, 501, {"prezzo": "42.00", "motivo": "sconto"})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # --- N7 sblocco ---

    # Scopo: N7 sblocco - sblocco prezzo bloccato OK.
    @patch("apps.vendite.services.commesse_service.transaction.atomic")
    @patch("apps.vendite.services.commesse_service.ListiniRepository")
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_sblocca_prezzo_ok(self, mock_comm_repo, mock_list_repo, mock_atomic):
        from apps.vendite.services.commesse_service import fn_sblocca_prezzo

        repo = mock_comm_repo.return_value
        att = dict(self._ATT_BASE)
        att["prezzo_bloccato"] = True
        repo.get_attivita_pricing.return_value = att

        mock_list_repo.return_value.test_resolver.return_value = {
            "prezzo": "45.0000000000",
            "listino_versione_id": 101,
        }

        result = fn_sblocca_prezzo(10, 501, {"motivo": "errore variazione precedente"})

        self.assertFalse(result["prezzo_bloccato"])
        self.assertEqual(result["prezzo_ricalcolato"], "45.0000000000")

    # Scopo: N7 sblocco - prezzo non bloccato rifiutato.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_sblocca_prezzo_non_bloccato(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import fn_sblocca_prezzo

        repo = mock_repo_cls.return_value
        repo.get_attivita_pricing.return_value = dict(self._ATT_BASE)  # prezzo_bloccato=False

        with self.assertRaises(ServiceError) as ctx:
            fn_sblocca_prezzo(10, 501, {"motivo": "test"})
        self.assertEqual(ctx.exception.code, "E_VENDITE_SBLOCCO_PREZZO_NON_AMMESSO")

    # --- N5: Riallineamento prezzo ---

    # Scopo: N5 - riallineamento OK su prezzo non bloccato.
    @patch("apps.vendite.services.commesse_service.transaction.atomic")
    @patch("apps.vendite.services.commesse_service.ListiniRepository")
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_riallinea_prezzo_ok(self, mock_comm_repo, mock_list_repo, mock_atomic):
        from apps.vendite.services.commesse_service import fn_riallinea_prezzo

        repo = mock_comm_repo.return_value
        repo.get_attivita_pricing.return_value = dict(self._ATT_BASE)

        mock_list_repo.return_value.test_resolver.return_value = {
            "prezzo": "46.0000000000",
            "listino_versione_id": 101,
        }

        result = fn_riallinea_prezzo(10, 501, {})

        self.assertEqual(result["prezzo_nuovo"], "46.0000000000")
        self.assertFalse(result["versione_cambiata"])

    # Scopo: N5 - riallineamento su prezzo bloccato rifiutato.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_riallinea_prezzo_bloccato(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import fn_riallinea_prezzo

        repo = mock_repo_cls.return_value
        att = dict(self._ATT_BASE)
        att["prezzo_bloccato"] = True
        repo.get_attivita_pricing.return_value = att

        with self.assertRaises(ServiceError) as ctx:
            fn_riallinea_prezzo(10, 501, {})
        self.assertEqual(ctx.exception.code, "E_COMMESSA_VALIDATION")

    # Scopo: N5 - versione cambiata senza conferma restituisce warning.
    @patch("apps.vendite.services.commesse_service.ListiniRepository")
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_riallinea_prezzo_versione_cambiata_senza_conferma(self, mock_comm_repo, mock_list_repo):
        from apps.vendite.services.commesse_service import fn_riallinea_prezzo

        repo = mock_comm_repo.return_value
        repo.get_attivita_pricing.return_value = dict(self._ATT_BASE)  # listino_versione_id=101

        mock_list_repo.return_value.test_resolver.return_value = {
            "prezzo": "48.0000000000",
            "listino_versione_id": 202,  # diversa!
        }

        result = fn_riallinea_prezzo(10, 501, {})

        self.assertTrue(result["versione_cambiata"])
        self.assertTrue(result["richiede_conferma"])
        self.assertEqual(result["versione_originale_id"], 101)
        self.assertEqual(result["versione_attuale_id"], 202)
        repo.update_attivita_prezzo.assert_not_called()


class CommesseApprovazioneServiceTests(TestCase):
    """Test A-1/A-2 cockpit: approva_commessa_attivita + approva_attivita_competenza."""

    # Scopo: approvazione di tutte le righe (righe_ids omesso) → repo con None.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_approva_commessa_attivita_tutte(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import approva_commessa_attivita

        repo = mock_repo_cls.return_value
        repo.get_commessa_stato_codice.return_value = "APERTA"
        repo.approva_commessa_attivita.return_value = 5

        result = approva_commessa_attivita(commessa_id=42, user="op1")

        self.assertEqual(result, {"commessa_id": 42, "approvate": 5})
        repo.approva_commessa_attivita.assert_called_once_with(
            commessa_id=42, righe_ids=None, user="op1",
        )

    # Scopo: selezione righe → passthrough della lista al repo.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_approva_commessa_attivita_selezione(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import approva_commessa_attivita

        repo = mock_repo_cls.return_value
        repo.get_commessa_stato_codice.return_value = "APERTA"
        repo.approva_commessa_attivita.return_value = 2

        result = approva_commessa_attivita(commessa_id=42, righe_ids=[10, 11])

        self.assertEqual(result["approvate"], 2)
        repo.approva_commessa_attivita.assert_called_once_with(
            commessa_id=42, righe_ids=[10, 11], user=None,
        )

    # Scopo: righe_ids invalido (lista vuota / tipi errati) → 400 E_COMMESSA_VALIDATION.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_approva_commessa_attivita_righe_ids_invalido(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import approva_commessa_attivita

        for bad in ([], [0], [-1], ["x"], [True], "10", 10):
            with self.subTest(righe_ids=bad):
                with self.assertRaises(ServiceError) as ctx:
                    approva_commessa_attivita(commessa_id=42, righe_ids=bad)
                self.assertEqual(ctx.exception.code, "E_COMMESSA_VALIDATION")
        mock_repo_cls.return_value.approva_commessa_attivita.assert_not_called()

    # Scopo: commessa inesistente → 404 E_COMMESSA_NOT_FOUND, nessuna scrittura.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_approva_commessa_attivita_not_found(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import approva_commessa_attivita

        repo = mock_repo_cls.return_value
        repo.get_commessa_stato_codice.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            approva_commessa_attivita(commessa_id=999)
        self.assertEqual(ctx.exception.code, "E_COMMESSA_NOT_FOUND")
        repo.approva_commessa_attivita.assert_not_called()

    # Scopo: commessa_id invalido → 400 senza toccare il repo.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_approva_commessa_attivita_id_invalido(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import approva_commessa_attivita

        with self.assertRaises(ServiceError) as ctx:
            approva_commessa_attivita(commessa_id=0)
        self.assertEqual(ctx.exception.code, "E_COMMESSA_VALIDATION")
        mock_repo_cls.return_value.approva_commessa_attivita.assert_not_called()

    # Scopo: massiva ok — normalizza al 1° del mese, un giro per commessa, somma esiti.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_approva_attivita_competenza_ok(self, mock_repo_cls):
        from datetime import date as _date

        from apps.vendite.services.commesse_service import approva_attivita_competenza

        repo = mock_repo_cls.return_value
        repo.list_da_approvare_per_competenza.return_value = [(1, [10, 11]), (2, [20])]
        repo.approva_commessa_attivita.side_effect = [2, 1]

        result = approva_attivita_competenza(
            competenza_mese=_date(2026, 7, 15), user="op1",
        )

        self.assertEqual(result, {
            "competenza_mese": "2026-07-01", "commesse": 2, "approvate": 3,
        })
        repo.list_da_approvare_per_competenza.assert_called_once_with(
            competenza_mese=_date(2026, 7, 1), commessa_ids=None,
        )
        self.assertEqual(repo.approva_commessa_attivita.call_count, 2)
        repo.approva_commessa_attivita.assert_any_call(
            commessa_id=1, righe_ids=[10, 11], user="op1",
        )
        repo.approva_commessa_attivita.assert_any_call(
            commessa_id=2, righe_ids=[20], user="op1",
        )

    # Scopo: perimetro vuoto → esito a zero senza scritture (non è un errore).
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_approva_attivita_competenza_vuota(self, mock_repo_cls):
        from datetime import date as _date

        from apps.vendite.services.commesse_service import approva_attivita_competenza

        repo = mock_repo_cls.return_value
        repo.list_da_approvare_per_competenza.return_value = []

        result = approva_attivita_competenza(competenza_mese=_date(2026, 7, 1))

        self.assertEqual(result, {
            "competenza_mese": "2026-07-01", "commesse": 0, "approvate": 0,
        })
        repo.approva_commessa_attivita.assert_not_called()

    # Scopo: competenza_mese mancante → 400 E_COMMESSA_VALIDATION.
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_approva_attivita_competenza_senza_mese(self, mock_repo_cls):
        from apps.vendite.services.commesse_service import approva_attivita_competenza

        with self.assertRaises(ServiceError) as ctx:
            approva_attivita_competenza(competenza_mese=None)  # type: ignore[arg-type]
        self.assertEqual(ctx.exception.code, "E_COMMESSA_VALIDATION")
        mock_repo_cls.return_value.list_da_approvare_per_competenza.assert_not_called()

    # Scopo: filtro commessa_ids → passthrough al repo (subset del mese).
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_approva_attivita_competenza_filtro_commesse(self, mock_repo_cls):
        from datetime import date as _date

        from apps.vendite.services.commesse_service import approva_attivita_competenza

        repo = mock_repo_cls.return_value
        repo.list_da_approvare_per_competenza.return_value = [(7, [70])]
        repo.approva_commessa_attivita.return_value = 1

        result = approva_attivita_competenza(
            competenza_mese=_date(2026, 7, 1), commessa_ids=[7],
        )

        self.assertEqual(result["commesse"], 1)
        repo.list_da_approvare_per_competenza.assert_called_once_with(
            competenza_mese=_date(2026, 7, 1), commessa_ids=[7],
        )

    # Scopo: errore su una commessa → all-or-nothing, l'eccezione propaga
    #        (la transazione avvolge il loop: niente esiti parziali).
    @patch("apps.vendite.services.commesse_service.CommesseRepository")
    def test_approva_attivita_competenza_all_or_nothing(self, mock_repo_cls):
        from datetime import date as _date

        from apps.vendite.services.commesse_service import approva_attivita_competenza

        repo = mock_repo_cls.return_value
        repo.list_da_approvare_per_competenza.return_value = [(1, [10]), (2, [20])]
        repo.approva_commessa_attivita.side_effect = [1, RuntimeError("guard DB")]

        with self.assertRaises(RuntimeError):
            approva_attivita_competenza(competenza_mese=_date(2026, 7, 1))
