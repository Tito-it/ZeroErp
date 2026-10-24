# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il presidio di avvio fra timeout di gunicorn e soglia di ripresa
#        delle Idempotency-Key (`soglia_idempotenza`, BE-5). La soglia si
#        finge: qui si prova la regola, non la lettura dal database (la
#        chiamata vera a `dbops.fn_idempotency_soglia_secondi` la prova
#        `tests/db/test_idempotency_prenota_db.py`; le forme ammesse della
#        soglia il pgTAP `script/test-intero-positivo-da-testo-v1`).
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) VerificaSogliaTests.test_timeout_sotto_soglia_col_margine_passa
2) VerificaSogliaTests.test_margine_mancante_rifiuta
3) VerificaSogliaTests.test_timeout_zero_rifiuta_senza_leggere_la_soglia
4) VerificaSogliaTests.test_worker_non_sync_rifiuta
"""
from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from gunicorn.workers.gthread import ThreadWorker
from gunicorn.workers.sync import SyncWorker

from apps.core.services.soglia_idempotenza import (
    MARGINE_SECONDI,
    SogliaIdempotenzaNonSicura,
    verifica_soglia_contro_timeout,
)

_SOGLIA = "apps.core.services.soglia_idempotenza.IdempotencyStore.soglia_ripresa_secondi"


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

