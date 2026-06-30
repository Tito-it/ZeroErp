# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per l'handler flusso `vendita.accetta_preventivo` —
#        azione di completamento (APPROVAZIONE_CLIENTE COMPLETATO+POSITIVO).
#        DB mockato (SimpleTestCase + patch), CI-friendly.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_accetta_ok — meta vuoto → fallback neutro (immediata False, mese corrente)
2) test_preventivo_non_collegato — nessun ROOT → E_VENDITA_PREVENTIVO_NON_COLLEGATO
3) test_accetta_immediata — meta immediata=True → competenza forzata mese corrente
4) test_accetta_differita — meta immediata=False + competenza → persistita sul preventivo
5) test_accetta_differita_senza_competenza — immediata=False senza competenza → E_VENDITA_COMPETENZA_RICHIESTA
"""

from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.handlers.accetta_preventivo_handler import AccettaPreventivoHandler

_REPO = "apps.vendite.handlers.accetta_preventivo_handler.PreventiviRepository"
_SVC = "apps.vendite.services.preventivi_service.cambia_stato"


class AccettaPreventivoHandlerTests(SimpleTestCase):

    # Scopo: ROOT risolto → cambia_stato ACCETTATO con policy neutra (immediata
    # False, competenza mese corrente), user inoltrato.
    @patch(_SVC)
    @patch(_REPO)
    def test_accetta_ok(self, MockRepo, mock_cambia_stato):
        MockRepo.return_value.get_preventivo_id_by_pratica_root.return_value = 4711
        mock_cambia_stato.return_value = {"id": 4711, "stato_codice_interno": "ACCETTATO"}

        out = AccettaPreventivoHandler().execute(
            flusso_id=1, pratica_id=2, meta={}, handler_params={}, user="op1",
        )

        self.assertEqual(out["preventivo_id"], 4711)
        mock_cambia_stato.assert_called_once_with(
            4711, "ACCETTATO",
            fatturazione_immediata=False,
            competenza_mese=date.today().replace(day=1),
            user="op1",
        )

    # Scopo: nessun preventivo ROOT collegato → errore parlante, niente accept.
    @patch(_SVC)
    @patch(_REPO)
    def test_preventivo_non_collegato(self, MockRepo, mock_cambia_stato):
        MockRepo.return_value.get_preventivo_id_by_pratica_root.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            AccettaPreventivoHandler().execute(
                flusso_id=1, pratica_id=2, meta={}, handler_params={},
            )
        self.assertEqual(ctx.exception.code, "E_VENDITA_PREVENTIVO_NON_COLLEGATO")
        mock_cambia_stato.assert_not_called()

    # Scopo: meta immediata=True → competenza forzata al primo del mese corrente.
    @patch(_SVC)
    @patch(_REPO)
    def test_accetta_immediata(self, MockRepo, mock_cambia_stato):
        MockRepo.return_value.get_preventivo_id_by_pratica_root.return_value = 4711
        mock_cambia_stato.return_value = {"id": 4711}

        AccettaPreventivoHandler().execute(
            flusso_id=1, pratica_id=2,
            meta={"fatturazione_immediata": True, "competenza_mese": "2026-08"},
            handler_params={}, user="op1",
        )
        mock_cambia_stato.assert_called_once_with(
            4711, "ACCETTATO",
            fatturazione_immediata=True,
            competenza_mese=date.today().replace(day=1),
            user="op1",
        )

    # Scopo: meta differita + competenza → persistita (parsata YYYY-MM) sul preventivo.
    @patch(_SVC)
    @patch(_REPO)
    def test_accetta_differita(self, MockRepo, mock_cambia_stato):
        MockRepo.return_value.get_preventivo_id_by_pratica_root.return_value = 4711
        mock_cambia_stato.return_value = {"id": 4711}

        AccettaPreventivoHandler().execute(
            flusso_id=1, pratica_id=2,
            meta={"fatturazione_immediata": False, "competenza_mese": "2026-08"},
            handler_params={}, user="op1",
        )
        mock_cambia_stato.assert_called_once_with(
            4711, "ACCETTATO",
            fatturazione_immediata=False,
            competenza_mese=date(2026, 8, 1),
            user="op1",
        )

    # Scopo: differita senza competenza → errore parlante, niente accept.
    @patch(_SVC)
    @patch(_REPO)
    def test_accetta_differita_senza_competenza(self, MockRepo, mock_cambia_stato):
        MockRepo.return_value.get_preventivo_id_by_pratica_root.return_value = 4711

        with self.assertRaises(ServiceError) as ctx:
            AccettaPreventivoHandler().execute(
                flusso_id=1, pratica_id=2,
                meta={"fatturazione_immediata": False},
                handler_params={}, user="op1",
            )
        self.assertEqual(ctx.exception.code, "E_VENDITA_COMPETENZA_RICHIESTA")
        mock_cambia_stato.assert_not_called()
