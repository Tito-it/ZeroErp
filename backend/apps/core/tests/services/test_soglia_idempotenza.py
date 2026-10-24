# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il presidio di avvio fra timeout di gunicorn e soglia di ripresa
#        delle Idempotency-Key (`soglia_idempotenza`, BE-5). La soglia si
#        finge: qui si prova la regola, non la lettura dal database.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) VerificaSogliaTests.test_timeout_sotto_soglia_col_margine_passa
2) VerificaSogliaTests.test_margine_mancante_rifiuta
3) VerificaSogliaTests.test_timeout_zero_rifiuta_senza_leggere_la_soglia
4) VerificaSogliaTests.test_worker_non_sync_rifiuta
5) DefaultIntPositivoTests.test_forme_rifiutate_come_la_funzione_db
"""
from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from gunicorn.workers.gthread import ThreadWorker
from gunicorn.workers.sync import SyncWorker

from apps.core.services.parameter_service import ParameterService
from apps.core.services.service_errors import ServiceError
from apps.core.services.soglia_idempotenza import (
    MARGINE_SECONDI,
    SogliaIdempotenzaNonSicura,
    verifica_soglia_contro_timeout,
)

_SOGLIA = "apps.core.services.soglia_idempotenza.ParameterService.get_default_int_positivo"


class VerificaSogliaTests(TestCase):
    def test_timeout_sotto_soglia_col_margine_passa(self) -> None:
        with patch(_SOGLIA, return_value=60 + MARGINE_SECONDI):
            verifica_soglia_contro_timeout(timeout_secondi=60, worker_class=SyncWorker)

    def test_margine_mancante_rifiuta(self) -> None:
        with patch(_SOGLIA, return_value=60 + MARGINE_SECONDI - 1):
            with self.assertRaises(SogliaIdempotenzaNonSicura):
                verifica_soglia_contro_timeout(timeout_secondi=60, worker_class=SyncWorker)

    # ⭐ 0 per gunicorn e' «nessun timeout»: nessun tetto da confrontare.
    def test_timeout_zero_rifiuta_senza_leggere_la_soglia(self) -> None:
        with patch(_SOGLIA) as soglia:
            with self.assertRaises(SogliaIdempotenzaNonSicura):
                verifica_soglia_contro_timeout(timeout_secondi=0, worker_class=SyncWorker)
        soglia.assert_not_called()

    def test_worker_non_sync_rifiuta(self) -> None:
        with patch(_SOGLIA, return_value=10_000):
            with self.assertRaises(SogliaIdempotenzaNonSicura):
                verifica_soglia_contro_timeout(timeout_secondi=60, worker_class=ThreadWorker)


class DefaultIntPositivoTests(TestCase):
    # ⚠️ Le forme che `dbops.fn_idempotency_prenota` rifiuta (`^[1-9][0-9]{0,5}$`)
    #    le rifiuta anche il backend: una soglia letta qui e rifiutata la' non
    #    sarebbe un presidio.
    def test_forme_rifiutate_come_la_funzione_db(self) -> None:
        servizio = ParameterService()
        for valore in (None, "", "  ", "0", "007", "-5", "1.5", "１２０", "1234567", " 120 "):
            with self.subTest(valore=valore):
                with patch.object(servizio._repo, "get_default_value", return_value=valore):
                    with self.assertRaises(ServiceError) as ctx:
                        servizio.get_default_int_positivo("X")
                    self.assertEqual(ctx.exception.code, "E_CONFIG_MANCANTE")
        with patch.object(servizio._repo, "get_default_value", return_value="120"):
            self.assertEqual(servizio.get_default_int_positivo("X"), 120)
