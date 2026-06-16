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
1) test_accetta_ok — risolve preventivo ROOT e lo porta ad ACCETTATO (policy neutra)
2) test_preventivo_non_collegato — nessun ROOT → E_VENDITA_PREVENTIVO_NON_COLLEGATO
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
