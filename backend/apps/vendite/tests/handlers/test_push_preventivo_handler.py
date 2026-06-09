# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per l'handler flusso `vendita.push_preventivo`.
#        DB mockato (SimpleTestCase + patch), CI-friendly. Verifica la logica
#        di orchestrazione: validazione politica, idempotenza, sequenza
#        push → approva → PRONTA_FATTURAZIONE → sorgenti → EVASO → giornale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_immediata_ok — IMMEDIATA: policy true + mese corrente, sequenza completa
 2) test_differita_ok — DIFFERITA: policy false + mese scelto da meta
 3) test_differita_senza_competenza — E_VENDITA_COMPETENZA_RICHIESTA
 4) test_modalita_invalida — E_VENDITA_PARAM_MODALITA_FATTURAZIONE_INVALIDA
 5) test_preventivo_gia_pushato — idempotenza → E_VENDITA_PREVENTIVO_GIA_PUSHATO
 6) test_preventivo_non_accettato — E_VENDITA_PREVENTIVO_NON_ACCETTATO
 7) test_preventivo_non_collegato — E_VENDITA_PREVENTIVO_NON_COLLEGATO
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

    def _run(self, MockPrev, MockComm, *, meta, handler_params, prev=None,
             existing_then_commessa=(None, 7701), preventivo_root=4711):
        MockPrev.return_value.get_preventivo_id_by_pratica_root.return_value = preventivo_root
        MockPrev.return_value.get_preventivo.return_value = prev or _prev()
        MockComm.return_value.get_commessa_id_by_sorgente.side_effect = list(
            existing_then_commessa
        )
        return PushPreventivoHandler().execute(
            flusso_id=1, pratica_id=2, meta=meta, handler_params=handler_params,
            user="alice",
        )

    def test_immediata_ok(self, MockPrev, MockComm, MockPrat, mock_push):
        res = self._run(
            MockPrev, MockComm,
            meta={"preventivo_id": 4711},
            handler_params={"modalita_fatturazione": "IMMEDIATA"},
        )
        prev, comm, prat = MockPrev.return_value, MockComm.return_value, MockPrat.return_value

        # Policy IMMEDIATA scritta sul preventivo (c7-2): true + mese corrente.
        _, kw = prev.update_preventivo.call_args
        self.assertTrue(kw["fatturazione_immediata"])
        self.assertEqual(kw["competenza_mese"], date.today().replace(day=1))
        # Push delegato all'orchestratore esistente.
        mock_push.assert_called_once_with(sorgente_codice="PREVENTIVO", sorgente_uid=4711)
        # Sequenza commessa: approva PRIMA, poi PRONTA_FATTURAZIONE.
        comm.approva_commessa_attivita.assert_called_once_with(commessa_id=7701, user="alice")
        comm.cambia_stato_commessa.assert_called_once_with(
            commessa_id=7701, nuovo_stato="PRONTA_FATTURAZIONE", user="alice",
        )
        # Aggancio: 2 sorgenti (ROOT preventivo + COLLEGATO commessa).
        self.assertEqual(prat.upsert_pratica_sorgente.call_count, 2)
        # Preventivo → EVASO (esplicito).
        prev.cambia_stato.assert_called_once_with(4711, "EVASO", "alice")
        # Giornale: DOMINIO_COMMESSA_CREATA + DOMINIO_PREVENTIVO_EVASO.
        self.assertEqual(prat.log_evento_dominio.call_count, 2)
        self.assertEqual(res["commessa_id"], 7701)
        self.assertEqual(res["modalita_fatturazione"], "IMMEDIATA")

    def test_differita_ok(self, MockPrev, MockComm, MockPrat, mock_push):
        self._run(
            MockPrev, MockComm,
            meta={"preventivo_id": 4711, "competenza_fatturazione": "2026-09"},
            handler_params={"modalita_fatturazione": "DIFFERITA"},
        )
        _, kw = MockPrev.return_value.update_preventivo.call_args
        self.assertFalse(kw["fatturazione_immediata"])
        self.assertEqual(kw["competenza_mese"], date(2026, 9, 1))

    def test_differita_senza_competenza(self, MockPrev, MockComm, MockPrat, mock_push):
        with self.assertRaises(ServiceError) as cm:
            self._run(
                MockPrev, MockComm,
                meta={"preventivo_id": 4711},
                handler_params={"modalita_fatturazione": "DIFFERITA"},
            )
        self.assertEqual(cm.exception.code, "E_VENDITA_COMPETENZA_RICHIESTA")
        MockPrev.return_value.update_preventivo.assert_not_called()
        mock_push.assert_not_called()

    def test_modalita_invalida(self, MockPrev, MockComm, MockPrat, mock_push):
        with self.assertRaises(ServiceError) as cm:
            self._run(
                MockPrev, MockComm,
                meta={"preventivo_id": 4711},
                handler_params={"modalita_fatturazione": "PIPPO"},
            )
        self.assertEqual(cm.exception.code, "E_VENDITA_PARAM_MODALITA_FATTURAZIONE_INVALIDA")
        mock_push.assert_not_called()

    def test_preventivo_gia_pushato(self, MockPrev, MockComm, MockPrat, mock_push):
        with self.assertRaises(ServiceError) as cm:
            self._run(
                MockPrev, MockComm,
                meta={"preventivo_id": 4711},
                handler_params={"modalita_fatturazione": "IMMEDIATA"},
                existing_then_commessa=(9999,),  # commessa gia' esistente
            )
        self.assertEqual(cm.exception.code, "E_VENDITA_PREVENTIVO_GIA_PUSHATO")
        mock_push.assert_not_called()

    def test_preventivo_non_accettato(self, MockPrev, MockComm, MockPrat, mock_push):
        with self.assertRaises(ServiceError) as cm:
            self._run(
                MockPrev, MockComm,
                meta={"preventivo_id": 4711},
                handler_params={"modalita_fatturazione": "IMMEDIATA"},
                prev=_prev(stato="EMESSO"),
            )
        self.assertEqual(cm.exception.code, "E_VENDITA_PREVENTIVO_NON_ACCETTATO")

    def test_preventivo_non_collegato(self, MockPrev, MockComm, MockPrat, mock_push):
        with self.assertRaises(ServiceError) as cm:
            self._run(
                MockPrev, MockComm,
                meta={},
                handler_params={"modalita_fatturazione": "IMMEDIATA"},
                preventivo_root=None,  # nessun preventivo ROOT sulla pratica
            )
        self.assertEqual(cm.exception.code, "E_VENDITA_PREVENTIVO_NON_COLLEGATO")
        mock_push.assert_not_called()
