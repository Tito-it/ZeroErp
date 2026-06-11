# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per l'handler flusso `vendita.push_preventivo` —
#        orchestratore CONFERMA_VENDITA (modello split per natura).
#        DB mockato (SimpleTestCase + patch), CI-friendly. Verifica:
#        smistamento merce→ordine / servizi→commessa, gate EVASO (D6),
#        guard idempotenza natura-completo, validazione policy.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_mix_immediata_ok — merce+servizi, IMMEDIATA: ordine + commessa + EVASO
 2) test_differita_ok — servizi, DIFFERITA: policy false + mese da meta
 3) test_solo_servizi_ok — niente merce: nessun push ordine, commessa + EVASO
 3b) test_ponte_emittibilita_delegato_al_push — ponte approva+PRONTA delegato al push
 4) test_solo_merce_ok — niente servizi: push ordine, nessuna commessa, EVASO
 5) test_differita_senza_competenza — E_VENDITA_COMPETENZA_RICHIESTA (ramo commessa)
 6) test_solo_merce_differita_no_competenza — competenza NON richiesta se merce-only
 7) test_modalita_invalida — E_VENDITA_PARAM_MODALITA_FATTURAZIONE_INVALIDA
 8) test_preventivo_gia_smistato — artefatti pregressi → E_VENDITA_PREVENTIVO_GIA_PUSHATO
 9) test_preventivo_vuoto — nessuna riga smistabile → E_PREV_NESSUNA_RIGA
10) test_preventivo_non_accettato — E_VENDITA_PREVENTIVO_NON_ACCETTATO
11) test_preventivo_non_collegato — E_VENDITA_PREVENTIVO_NON_COLLEGATO
"""

from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.handlers.push_preventivo_handler import PushPreventivoHandler

_MOD = "apps.vendite.handlers.push_preventivo_handler"
_ATOMIC = "django.db.transaction.Atomic"
_PRAT_REPO = "apps.pratiche.db.pratiche_repository.PraticheRepository"
_PUSH = "apps.vendite.services.commesse_service.pr_run_commesse_push_one"


def _prev(stato: str = "ACCETTATO", uid: str = "P-UID-1") -> dict:
    return {"id": 4711, "uid": uid, "stato_codice_interno": stato}


@patch(_PUSH)
@patch(_PRAT_REPO)
@patch(f"{_MOD}.CommesseRepository")
@patch(f"{_MOD}.PreventiviRepository")
class PushPreventivoHandlerTests(SimpleTestCase):
    def setUp(self) -> None:
        # `with transaction.atomic()` → no-op (nessun DB reale).
        for p in (
            patch(f"{_ATOMIC}.__enter__", return_value=None),
            patch(f"{_ATOMIC}.__exit__", return_value=False),
        ):
            p.start()
            self.addCleanup(p.stop)

    def _run(
        self, MockPrev, MockComm, *, meta, handler_params, prev=None,
        preventivo_root=4711,
        residuo=(True, False),   # (discovery, gate EVASO)
        righe_commessa=2,
        ordine_id=5501,
        commessa_id=7701,
        ordine_pregresso=False,
        commessa_stato="BOZZA",
    ):
        prev_repo = MockPrev.return_value
        prev_repo.get_preventivo_id_by_pratica_root.return_value = preventivo_root
        prev_repo.get_preventivo.return_value = prev or _prev()
        prev_repo.preventivo_ha_residuo_ordine.side_effect = list(residuo)
        prev_repo.count_righe_pushable.return_value = righe_commessa
        prev_repo.push_a_ordine.return_value = ordine_id
        prev_repo.exists_ordine_da_preventivo.return_value = ordine_pregresso
        # get_commessa_id_by_sorgente: nel ramo commessa ritorna la commessa
        # creata; nel guard (righe_commessa==0) ritorna l'eventuale pregresso.
        MockComm.return_value.get_commessa_id_by_sorgente.return_value = commessa_id
        # Stato commessa per lo skip idempotente della transizione a PRONTA.
        MockComm.return_value.get_commessa_stato_codice.return_value = commessa_stato
        return PushPreventivoHandler().execute(
            flusso_id=1, pratica_id=2, meta=meta, handler_params=handler_params,
            user="alice",
        )

    # 1) MIX: merce + servizi, IMMEDIATA → ordine + commessa + EVASO.
    def test_mix_immediata_ok(self, MockPrev, MockComm, MockPrat, mock_push):
        res = self._run(
            MockPrev, MockComm,
            meta={}, handler_params={"modalita_fatturazione": "IMMEDIATA"},
            residuo=(True, False), righe_commessa=2,
        )
        prev, comm, prat = MockPrev.return_value, MockComm.return_value, MockPrat.return_value

        # Ramo merce: push ordine con pratica per l'aggancio sorgenti DB.
        prev.push_a_ordine.assert_called_once_with(4711, pratica_id=2)
        # Ramo servizi: policy IMMEDIATA (true + mese corrente) + push commessa.
        _, kw = prev.update_preventivo.call_args
        self.assertTrue(kw["fatturazione_immediata"])
        self.assertEqual(kw["competenza_mese"], date.today().replace(day=1))
        mock_push.assert_called_once_with(
            sorgente_codice="PREVENTIVO", sorgente_uid=4711, user="alice",
        )
        # Il ponte di emittibilita' (approva righe + PRONTA_FATTURAZIONE) vive
        # dentro pr_run_commesse_push_one: il handler NON lo replica.
        comm.approva_commessa_attivita.assert_not_called()
        comm.cambia_stato_commessa.assert_not_called()
        # Sorgenti commessa (ROOT preventivo + COLLEGATO commessa); l'ordine lo
        # aggancia la fn DB.
        self.assertEqual(prat.upsert_pratica_sorgente.call_count, 2)
        # EVASO esplicito + 3 eventi di giornale (ordine + commessa + evaso).
        prev.cambia_stato.assert_called_once_with(4711, "EVASO", "alice")
        self.assertEqual(prat.log_evento_dominio.call_count, 3)
        self.assertEqual(res["ordine_id"], 5501)
        self.assertEqual(res["commessa_id"], 7701)
        self.assertTrue(res["evaso"])

    # 2) DIFFERITA (servizi): policy false + mese da meta.
    def test_differita_ok(self, MockPrev, MockComm, MockPrat, mock_push):
        self._run(
            MockPrev, MockComm,
            meta={"competenza_fatturazione": "2026-09"},
            handler_params={"modalita_fatturazione": "DIFFERITA"},
            residuo=(False, False), righe_commessa=1,
        )
        _, kw = MockPrev.return_value.update_preventivo.call_args
        self.assertFalse(kw["fatturazione_immediata"])
        self.assertEqual(kw["competenza_mese"], date(2026, 9, 1))

    # 3) Solo servizi: nessun push ordine, commessa + EVASO.
    def test_solo_servizi_ok(self, MockPrev, MockComm, MockPrat, mock_push):
        res = self._run(
            MockPrev, MockComm,
            meta={}, handler_params={"modalita_fatturazione": "IMMEDIATA"},
            residuo=(False, False), righe_commessa=3,
        )
        MockPrev.return_value.push_a_ordine.assert_not_called()
        mock_push.assert_called_once()
        self.assertIsNone(res["ordine_id"])
        self.assertEqual(res["commessa_id"], 7701)
        self.assertTrue(res["evaso"])
        # Giornale: commessa + evaso (no ordine).
        self.assertEqual(MockPrat.return_value.log_evento_dominio.call_count, 2)

    # 3b) Il ponte emittibilita' (approva + PRONTA con skip idempotente
    #     multi-sorgente) e' DELEGATO a pr_run_commesse_push_one — il handler
    #     non tocca mai direttamente lo stato commessa. Lo skip PRONTA→PRONTA
    #     e' coperto in test_commesse_service (ponte centralizzato).
    def test_ponte_emittibilita_delegato_al_push(self, MockPrev, MockComm, MockPrat, mock_push):
        res = self._run(
            MockPrev, MockComm,
            meta={}, handler_params={"modalita_fatturazione": "IMMEDIATA"},
            residuo=(False, False), righe_commessa=2,
            commessa_stato="PRONTA_FATTURAZIONE",
        )
        comm = MockComm.return_value
        comm.approva_commessa_attivita.assert_not_called()
        comm.cambia_stato_commessa.assert_not_called()
        mock_push.assert_called_once_with(
            sorgente_codice="PREVENTIVO", sorgente_uid=4711, user="alice",
        )
        self.assertEqual(res["commessa_id"], 7701)
        self.assertTrue(res["evaso"])

    # 4) Solo merce: push ordine, nessuna commessa, EVASO.
    def test_solo_merce_ok(self, MockPrev, MockComm, MockPrat, mock_push):
        res = self._run(
            MockPrev, MockComm,
            meta={}, handler_params={"modalita_fatturazione": "IMMEDIATA"},
            residuo=(True, False), righe_commessa=0,
        )
        prev = MockPrev.return_value
        prev.push_a_ordine.assert_called_once_with(4711, pratica_id=2)
        # Ramo commessa saltato: niente policy, niente push commessa.
        prev.update_preventivo.assert_not_called()
        mock_push.assert_not_called()
        self.assertEqual(res["ordine_id"], 5501)
        self.assertIsNone(res["commessa_id"])
        self.assertTrue(res["evaso"])
        # Giornale: ordine + evaso (no commessa).
        self.assertEqual(MockPrat.return_value.log_evento_dominio.call_count, 2)

    # 5) DIFFERITA senza competenza (ramo commessa attivo) → errore parlante.
    def test_differita_senza_competenza(self, MockPrev, MockComm, MockPrat, mock_push):
        with self.assertRaises(ServiceError) as cm:
            self._run(
                MockPrev, MockComm,
                meta={}, handler_params={"modalita_fatturazione": "DIFFERITA"},
                residuo=(False,), righe_commessa=2,
            )
        self.assertEqual(cm.exception.code, "E_VENDITA_COMPETENZA_RICHIESTA")
        MockPrev.return_value.update_preventivo.assert_not_called()
        mock_push.assert_not_called()

    # 6) DIFFERITA su preventivo di SOLA MERCE: competenza NON richiesta (il
    #    ramo commessa non scatta). L'ordine si crea comunque.
    def test_solo_merce_differita_no_competenza(self, MockPrev, MockComm, MockPrat, mock_push):
        res = self._run(
            MockPrev, MockComm,
            meta={}, handler_params={"modalita_fatturazione": "DIFFERITA"},
            residuo=(True, False), righe_commessa=0,
        )
        self.assertEqual(res["ordine_id"], 5501)
        self.assertIsNone(res["commessa_id"])
        MockPrev.return_value.update_preventivo.assert_not_called()

    # 7) Modalita invalida → errore prima della discovery.
    def test_modalita_invalida(self, MockPrev, MockComm, MockPrat, mock_push):
        with self.assertRaises(ServiceError) as cm:
            self._run(
                MockPrev, MockComm,
                meta={}, handler_params={"modalita_fatturazione": "PIPPO"},
            )
        self.assertEqual(cm.exception.code, "E_VENDITA_PARAM_MODALITA_FATTURAZIONE_INVALIDA")
        mock_push.assert_not_called()
        MockPrev.return_value.push_a_ordine.assert_not_called()

    # 8) Nulla da smistare + artefatti pregressi → GIA_PUSHATO.
    def test_preventivo_gia_smistato(self, MockPrev, MockComm, MockPrat, mock_push):
        with self.assertRaises(ServiceError) as cm:
            self._run(
                MockPrev, MockComm,
                meta={}, handler_params={"modalita_fatturazione": "IMMEDIATA"},
                residuo=(False,), righe_commessa=0,
                ordine_pregresso=True,  # un ordine esiste gia'
            )
        self.assertEqual(cm.exception.code, "E_VENDITA_PREVENTIVO_GIA_PUSHATO")
        mock_push.assert_not_called()
        MockPrev.return_value.push_a_ordine.assert_not_called()

    # 9) Nulla da smistare e nessun artefatto → preventivo vuoto.
    def test_preventivo_vuoto(self, MockPrev, MockComm, MockPrat, mock_push):
        with self.assertRaises(ServiceError) as cm:
            self._run(
                MockPrev, MockComm,
                meta={}, handler_params={"modalita_fatturazione": "IMMEDIATA"},
                residuo=(False,), righe_commessa=0,
                commessa_id=None, ordine_pregresso=False,
            )
        self.assertEqual(cm.exception.code, "E_PREV_NESSUNA_RIGA")

    # 10) Preventivo non ACCETTATO (ancora di idempotenza: EVASO ricade qui).
    def test_preventivo_non_accettato(self, MockPrev, MockComm, MockPrat, mock_push):
        with self.assertRaises(ServiceError) as cm:
            self._run(
                MockPrev, MockComm,
                meta={}, handler_params={"modalita_fatturazione": "IMMEDIATA"},
                prev=_prev(stato="EVASO"),
            )
        self.assertEqual(cm.exception.code, "E_VENDITA_PREVENTIVO_NON_ACCETTATO")
        mock_push.assert_not_called()

    # 11) Nessun preventivo ROOT collegato alla pratica.
    def test_preventivo_non_collegato(self, MockPrev, MockComm, MockPrat, mock_push):
        with self.assertRaises(ServiceError) as cm:
            self._run(
                MockPrev, MockComm,
                meta={}, handler_params={"modalita_fatturazione": "IMMEDIATA"},
                preventivo_root=None,
            )
        self.assertEqual(cm.exception.code, "E_VENDITA_PREVENTIVO_NON_COLLEGATO")
        mock_push.assert_not_called()
