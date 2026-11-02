# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit `QueueDrainEngine` — il loop di drenaggio generico. Backend
#        mockato (QueueBackend): verifica claim vuota, happy-path (mark_done),
#        ERRORE terminale vs retry con backoff (soglia tentativi), reaper,
#        resilienza per-riga, formula di backoff.
#
# Indice test (0..N):
#   0. claim_vuota_nessun_lavoro
#   1. happy_path_mark_done_con_result
#   2. errore_terminale_soglia_raggiunta
#   3. retry_con_backoff_sotto_soglia
#   4. resilienza_per_riga
#   5. reaper_chiamato_e_disabilitato
#   6. backoff_esponenziale_cappato
#   7. terminale_dichiarato_non_consuma_tentativi
#   8. eccezione_non_prevista_resta_riprovabile
# ------------------------------------------------------------

from __future__ import annotations

from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.core.services.coda_lavori.backend import QueueItem
from apps.core.services.coda_lavori.drain_engine import (
    QueueDrainEngine,
    backoff_secondi_default,
    contesto_terminale,
)
from apps.core.services.service_errors import ServiceError


def _item(item_id: int, *, tentativi=0, max_tentativi=5) -> QueueItem:
    return QueueItem(
        id=item_id, job_type="TEST_JOB", payload={"k": "v"},
        run_as="SISTEMA", scope=None,
        tentativi=tentativi, max_tentativi=max_tentativi,
        raw={"handler_code": "test_default"},
    )


class QueueDrainEngineTests(SimpleTestCase):

    # 0. Claim vuota: nessun lavoro, per_item mai chiamato.
    def test_claim_vuota_nessun_lavoro(self) -> None:
        backend = MagicMock()
        backend.reap_stale.return_value = 0
        backend.claim.return_value = []
        per_item = MagicMock()
        engine = QueueDrainEngine(backend, per_item=per_item)

        summary = engine.drain(limit=10, stale_minuti=30)

        self.assertEqual(summary["claimate"], 0)
        per_item.assert_not_called()
        backend.mark_done.assert_not_called()

    # 1. Happy path: per_item ritorna result → mark_done col result.
    def test_happy_path_mark_done_con_result(self) -> None:
        backend = MagicMock()
        backend.reap_stale.return_value = 0
        backend.claim.return_value = [_item(1)]
        per_item = MagicMock(return_value={"lotto_id": 42})
        engine = QueueDrainEngine(backend, per_item=per_item)

        summary = engine.drain(limit=10, stale_minuti=0)

        self.assertEqual(summary["fatto"], 1)
        self.assertEqual(summary["errore"], 0)
        per_item.assert_called_once()
        backend.mark_done.assert_called_once_with(1, result={"lotto_id": 42})
        backend.mark_error.assert_not_called()

    # 2. Fallimento con tentativi+1 >= max → ERRORE terminale (retry_after=None).
    def test_errore_terminale_soglia_raggiunta(self) -> None:
        backend = MagicMock()
        backend.reap_stale.return_value = 0
        backend.claim.return_value = [_item(1, tentativi=4, max_tentativi=5)]
        per_item = MagicMock(side_effect=ServiceError(code="E_BOOM", message="boom"))
        engine = QueueDrainEngine(backend, per_item=per_item)

        summary = engine.drain(limit=10, stale_minuti=0)

        self.assertEqual(summary["errore"], 1)
        self.assertEqual(summary["riprovabili"], 0)
        kwargs = backend.mark_error.call_args.kwargs
        self.assertIsNone(kwargs["retry_after_secondi"])
        self.assertEqual(kwargs["errore"]["code"], "E_BOOM")

    # 3. Fallimento sotto soglia → PENDING con backoff (retry_after int).
    def test_retry_con_backoff_sotto_soglia(self) -> None:
        backend = MagicMock()
        backend.reap_stale.return_value = 0
        backend.claim.return_value = [_item(1, tentativi=1, max_tentativi=5)]
        per_item = MagicMock(side_effect=RuntimeError("transient"))
        engine = QueueDrainEngine(backend, per_item=per_item)

        summary = engine.drain(limit=10, stale_minuti=0)

        self.assertEqual(summary["riprovabili"], 1)
        self.assertEqual(summary["errore"], 0)
        kwargs = backend.mark_error.call_args.kwargs
        # prossimo tentativo = 2 → backoff = 60 * 2^1 = 120s
        self.assertEqual(kwargs["retry_after_secondi"], 120)
        self.assertEqual(kwargs["errore"]["code"], "RuntimeError")

    # 4. Resilienza per-riga: la prima fallisce, la seconda completa comunque.
    def test_resilienza_per_riga(self) -> None:
        backend = MagicMock()
        backend.reap_stale.return_value = 0
        backend.claim.return_value = [_item(1), _item(2)]
        per_item = MagicMock(side_effect=[
            ServiceError(code="E_BOOM", message="boom"),
            {"ok": True},
        ])
        engine = QueueDrainEngine(backend, per_item=per_item)

        summary = engine.drain(limit=10, stale_minuti=0)

        self.assertEqual(summary["claimate"], 2)
        self.assertEqual(summary["fatto"], 1)
        # tentativi=0, max=5 → 0+1 < 5 → riprovabile (non terminale)
        self.assertEqual(summary["riprovabili"], 1)
        backend.mark_done.assert_called_once_with(2, result={"ok": True})

    # 5. Reaper: invocato con la soglia; stale_minuti=0 lo disabilita.
    def test_reaper_chiamato_e_disabilitato(self) -> None:
        backend = MagicMock()
        backend.reap_stale.return_value = 3
        backend.claim.return_value = []
        engine = QueueDrainEngine(backend, per_item=MagicMock())

        s1 = engine.drain(limit=10, stale_minuti=15)
        backend.reap_stale.assert_called_once_with(stale_minuti=15)
        self.assertEqual(s1["recuperate"], 3)

        backend.reset_mock()
        backend.claim.return_value = []
        s2 = engine.drain(limit=10, stale_minuti=0)
        backend.reap_stale.assert_not_called()
        self.assertEqual(s2["recuperate"], 0)

    # 6. Backoff esponenziale cappato a 1h.
    def test_backoff_esponenziale_cappato(self) -> None:
        self.assertEqual(backoff_secondi_default(1), 60)
        self.assertEqual(backoff_secondi_default(2), 120)
        self.assertEqual(backoff_secondi_default(3), 240)
        self.assertEqual(backoff_secondi_default(99), 3600)  # cap

    # 7. Fallimento DICHIARATO deterministico dall'handler: ERRORE subito, anche
    #    se i tentativi non sono esauriti. Senza questo, un perimetro non
    #    fatturabile o un payload malformato verrebbero ripetuti max_tentativi
    #    volte con lo stesso esito, tenendo il job «in corso» a video.
    def test_terminale_dichiarato_non_consuma_tentativi(self) -> None:
        backend = MagicMock()
        backend.reap_stale.return_value = 0
        backend.claim.return_value = [_item(1, tentativi=0, max_tentativi=5)]
        per_item = MagicMock(side_effect=ServiceError(
            code="E_PERIMETRO", message="niente da fatturare",
            context=contesto_terminale(gruppi_non_serviti=[{"motivo": "X"}]),
        ))
        engine = QueueDrainEngine(backend, per_item=per_item)

        summary = engine.drain(limit=10, stale_minuti=0)

        self.assertEqual(summary["errore"], 1)
        self.assertEqual(summary["riprovabili"], 0)
        self.assertIsNone(backend.mark_error.call_args.kwargs["retry_after_secondi"])
        # Il context dell'handler DEVE arrivare in ultimo_errore: e' il
        # dettaglio strutturato (motivi per gruppo) — senza, resterebbe solo
        # il testo del messaggio da riparsare.
        errore = backend.mark_error.call_args.kwargs["errore"]
        self.assertEqual(
            errore["context"]["gruppi_non_serviti"], [{"motivo": "X"}],
        )

    # 8. Eccezione non prevista (non dichiarata): resta riprovabile, comportamento
    #    storico — solo l'handler sa se riprovare ha senso.
    def test_eccezione_non_prevista_resta_riprovabile(self) -> None:
        backend = MagicMock()
        backend.reap_stale.return_value = 0
        backend.claim.return_value = [_item(1, tentativi=0, max_tentativi=5)]
        per_item = MagicMock(side_effect=RuntimeError("connessione persa"))
        engine = QueueDrainEngine(backend, per_item=per_item)

        summary = engine.drain(limit=10, stale_minuti=0)

        self.assertEqual(summary["riprovabili"], 1)
        self.assertEqual(summary["errore"], 0)
        self.assertIsNotNone(backend.mark_error.call_args.kwargs["retry_after_secondi"])
