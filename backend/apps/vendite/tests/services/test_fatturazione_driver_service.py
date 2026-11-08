# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit del core driver `fatturazione_driver_service` (C-1).
# Indice test:
#   1) differita → fermata di corsia EMESSA (fino_a_stato='EMESSA' alla pipeline)
#   2) immediata → nessuna fermata (fino_a_stato=None: numera da sola, D-1)
#   3) override esplicito fino_a_stato prevale sul default di corsia
#   4) dry-run → solo discovery, esiti con total_candidate, nessun run pipeline
#   5) best-effort → terna in errore contata nei falliti, le altre proseguono
#   6) terne senza emittente → saltate e contate in senza_emittente
#   7) modalita sconosciuta → ValueError
#   8) callback on_lane_esito invocata per successo ed errore
#   9) callback on_discovery invocata con la testata PRIMA delle esecuzioni
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from unittest import TestCase
from unittest.mock import patch

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.fatturazione_driver_service import (
    STATO_FERMATA_EMESSA,
    esegui_giro_fatturazione,
    modalita_disponibili,
)
# Fixture lane condiviso (regola del 2): una sede sola per la forma di
# list_emittibili_lane.
from apps.vendite.tests._helpers.lane_fixture import lane as _lane

_SVC = "apps.vendite.services.fatturazione_driver_service"



_ESITO_OK = {"lotto_id": 100, "motivo_stop": "FERMATO_A_STATO", "step_eseguiti": 2}


class FatturazioneDriverServiceTests(TestCase):
    # 1) differita → fermata di corsia EMESSA.
    def test_differita_ferma_a_emessa_default_corsia(self):
        with patch(f"{_SVC}.CommesseRepository", autospec=True) as RepoCls, \
             patch(f"{_SVC}.run_lotto_pipeline_until_done") as mock_run:
            RepoCls.return_value.list_emittibili_lane.return_value = [_lane(1)]
            mock_run.return_value = _ESITO_OK
            summary = esegui_giro_fatturazione(
                modalita="differita", competenza=date(2026, 6, 1),
            )
        self.assertEqual(
            mock_run.call_args.kwargs["fino_a_stato"], STATO_FERMATA_EMESSA,
        )
        self.assertEqual(mock_run.call_args.kwargs["tipo_lotto"], "MASSIVO")
        self.assertEqual(summary["fino_a_stato"], STATO_FERMATA_EMESSA)
        self.assertEqual(summary["per_motivo"], {"FERMATO_A_STATO": 1})
        self.assertEqual(summary["lane"], 1)
        self.assertEqual(summary["falliti"], 0)

    # 2) immediata → nessuna fermata (completa la catena, D-1).
    def test_immediata_nessuna_fermata(self):
        with patch(f"{_SVC}.CommesseRepository", autospec=True) as RepoCls, \
             patch(f"{_SVC}.run_lotto_pipeline_until_done") as mock_run:
            RepoCls.return_value.list_emittibili_lane.return_value = [_lane(1)]
            mock_run.return_value = {"lotto_id": 1, "motivo_stop": "COMPLETATO", "step_eseguiti": 4}
            summary = esegui_giro_fatturazione(
                modalita="immediata", competenza=date(2026, 6, 1),
            )
        self.assertIsNone(mock_run.call_args.kwargs["fino_a_stato"])
        self.assertEqual(mock_run.call_args.kwargs["tipo_lotto"], "GIORNALIERO")
        self.assertEqual(
            mock_run.call_args.kwargs["meta"], {"fatturazione_immediata": True},
        )
        self.assertIsNone(summary["fino_a_stato"])

    # 3) override esplicito prevale sul default di corsia.
    def test_override_fino_a_stato_esplicito(self):
        with patch(f"{_SVC}.CommesseRepository", autospec=True) as RepoCls, \
             patch(f"{_SVC}.run_lotto_pipeline_until_done") as mock_run:
            RepoCls.return_value.list_emittibili_lane.return_value = [_lane(1)]
            mock_run.return_value = {"lotto_id": 1, "motivo_stop": "COMPLETATO", "step_eseguiti": 4}
            summary = esegui_giro_fatturazione(
                modalita="differita", competenza=date(2026, 6, 1),
                fino_a_stato=None,
            )
        self.assertIsNone(mock_run.call_args.kwargs["fino_a_stato"])
        self.assertIsNone(summary["fino_a_stato"])

    # 4) dry-run: discovery e conteggio, nessuna pipeline.
    def test_dry_run_solo_discovery(self):
        with patch(f"{_SVC}.CommesseRepository", autospec=True) as RepoCls, \
             patch(f"{_SVC}.run_lotto_pipeline_until_done") as mock_run:
            RepoCls.return_value.list_emittibili_lane.return_value = [_lane(1, tot=5)]
            summary = esegui_giro_fatturazione(
                modalita="immediata", competenza=date(2026, 6, 1), dry_run=True,
            )
        mock_run.assert_not_called()
        self.assertTrue(summary["dry_run"])
        self.assertEqual(summary["esiti"][0]["total_candidate"], 5)
        self.assertEqual(summary["lane"], 1)

    # 5) best-effort: errore su una terna non blocca le altre.
    def test_best_effort_terna_in_errore(self):
        with patch(f"{_SVC}.CommesseRepository", autospec=True) as RepoCls, \
             patch(f"{_SVC}.run_lotto_pipeline_until_done") as mock_run:
            RepoCls.return_value.list_emittibili_lane.return_value = [_lane(1), _lane(2)]
            mock_run.side_effect = [
                ServiceError(code="E_PIPELINE", message="boom", detail="x"),
                _ESITO_OK,
            ]
            summary = esegui_giro_fatturazione(
                modalita="differita", competenza=date(2026, 6, 1),
            )
        self.assertEqual(mock_run.call_count, 2)
        self.assertEqual(summary["falliti"], 1)
        self.assertEqual(summary["per_motivo"], {"FERMATO_A_STATO": 1})
        self.assertFalse(summary["esiti"][0]["ok"])
        self.assertEqual(summary["esiti"][0]["errore_code"], "E_PIPELINE")
        self.assertTrue(summary["esiti"][1]["ok"])

    # 6) terne senza emittente: saltate e contate.
    def test_terne_senza_emittente_saltate(self):
        with patch(f"{_SVC}.CommesseRepository", autospec=True) as RepoCls, \
             patch(f"{_SVC}.run_lotto_pipeline_until_done") as mock_run:
            RepoCls.return_value.list_emittibili_lane.return_value = [
                _lane(None), _lane(2),
            ]
            mock_run.return_value = _ESITO_OK
            summary = esegui_giro_fatturazione(
                modalita="differita", competenza=date(2026, 6, 1),
            )
        self.assertEqual(mock_run.call_count, 1)
        self.assertEqual(summary["lane"], 1)
        self.assertEqual(summary["senza_emittente"], 1)

    # 7) modalita sconosciuta → ValueError (bug del chiamante, no ServiceError).
    def test_modalita_sconosciuta_value_error(self):
        with self.assertRaises(ValueError):
            esegui_giro_fatturazione(modalita="notturna", competenza=date(2026, 6, 1))
        self.assertEqual(modalita_disponibili(), ["differita", "immediata"])

    # 9) callback on_discovery: testata (lane/senza_emittente) PRIMA delle
    #    esecuzioni — a quel punto nessuna pipeline e' ancora partita.
    def test_callback_on_discovery_prima_delle_esecuzioni(self):
        stati = []
        with patch(f"{_SVC}.CommesseRepository", autospec=True) as RepoCls, \
             patch(f"{_SVC}.run_lotto_pipeline_until_done") as mock_run:
            RepoCls.return_value.list_emittibili_lane.return_value = [_lane(None), _lane(2)]
            mock_run.return_value = _ESITO_OK
            esegui_giro_fatturazione(
                modalita="differita", competenza=date(2026, 6, 1),
                on_discovery=lambda s: stati.append(
                    (s["lane"], s["senza_emittente"], mock_run.call_count),
                ),
            )
        # Invocata una volta, con i contatori giusti e 0 pipeline gia' partite.
        self.assertEqual(stati, [(1, 1, 0)])

    # 8) callback per-terna invocata con esito o errore.
    def test_callback_on_lane_esito(self):
        eventi = []
        with patch(f"{_SVC}.CommesseRepository", autospec=True) as RepoCls, \
             patch(f"{_SVC}.run_lotto_pipeline_until_done") as mock_run:
            RepoCls.return_value.list_emittibili_lane.return_value = [_lane(1), _lane(2)]
            mock_run.side_effect = [
                _ESITO_OK,
                ServiceError(code="E_PIPELINE", message="boom", detail="x"),
            ]
            esegui_giro_fatturazione(
                modalita="differita", competenza=date(2026, 6, 1),
                on_lane_esito=lambda lane, esito, errore: eventi.append(
                    (lane["emittente_soggetto_ruolo_id"], esito is not None, errore is not None),
                ),
            )
        self.assertEqual(eventi, [(1, True, False), (2, False, True)])
