# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per il bridge M2 (brief BE §8.3):
#        completa_approvazione_da_flusso — il completamento del flusso
#        APPROVAZIONE_CLIENTE guida l'accettazione del preventivo.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_positivo_accetta_preventivo — completa flusso + ACCETTATO (policy neutra)
 2) test_negativo_solo_flusso — completa flusso, nessuna accettazione
"""

from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.vendite.services import preventivi_service

_SVC = "apps.vendite.services.preventivi_service"
_ATOMIC = "django.db.transaction.Atomic"
_COMPLETA = "apps.pratiche.services.pratiche_service.completa_flusso"


class CompletaApprovazioneDaFlussoTests(SimpleTestCase):
    def setUp(self) -> None:
        for p in (
            patch(f"{_ATOMIC}.__enter__", return_value=None),
            patch(f"{_ATOMIC}.__exit__", return_value=False),
        ):
            p.start()
            self.addCleanup(p.stop)

    @patch(f"{_SVC}.cambia_stato")
    @patch(f"{_SVC}.PreventiviRepository")
    @patch(_COMPLETA)
    def test_positivo_accetta_preventivo(self, mock_completa, MockPrevRepo, mock_cambia):
        MockPrevRepo.return_value.get_preventivo_id_by_pratica_root.return_value = 4711
        mock_cambia.return_value = {"stato": "ACCETTATO"}

        res = preventivi_service.completa_approvazione_da_flusso(
            2, flusso_id=9, esito="POSITIVO", note_esito="ok", user="alice",
        )

        mock_completa.assert_called_once_with(9, esito="POSITIVO", note_esito="ok")
        # Preventivo risolto dal ROOT della pratica; accettazione con policy
        # NEUTRA (sovrascritta a CONFERMA dall'handler).
        MockPrevRepo.return_value.get_preventivo_id_by_pratica_root.assert_called_once_with(2)
        mock_cambia.assert_called_once_with(
            4711, "ACCETTATO",
            fatturazione_immediata=False,
            competenza_mese=date.today().replace(day=1),
            user="alice",
        )
        self.assertEqual(res["flusso_esito"], "POSITIVO")

    @patch(f"{_SVC}.cambia_stato")
    @patch(f"{_SVC}.PreventiviRepository")
    @patch(_COMPLETA)
    def test_negativo_solo_flusso(self, mock_completa, MockPrevRepo, mock_cambia):
        res = preventivi_service.completa_approvazione_da_flusso(
            2, flusso_id=9, esito="NEGATIVO", user="alice",
        )

        mock_completa.assert_called_once_with(9, esito="NEGATIVO", note_esito=None)
        mock_cambia.assert_not_called()
        self.assertIsNone(res["preventivo"])
