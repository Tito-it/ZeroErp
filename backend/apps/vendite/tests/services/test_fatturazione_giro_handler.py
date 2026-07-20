# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit dell'handler del job FATTURAZIONE_GIRO (C-3). Mock del core
#        `esegui_giro_fatturazione`: verifica corsia (differita), normalizzazione
#        competenza, fino_a_stato opzionale, compattazione del result (no lista
#        per-terna), guard payload con codice registrato, e registrazione.
#
# Indice test:
#   0. happy_path_differita_competenza_normalizzata_result_compatto
#   1. fino_a_stato_opzionale_propagato
#   2. competenza_mancante_raises_payload
#   3. competenza_invalida_raises_payload
#   4. handler_registrato_dopo_boot
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.fatturazione_giro_handler import (
    HANDLER_CODE,
    fatturazione_giro_handler,
)

_GIRO = "apps.vendite.services.fatturazione_driver_service.esegui_giro_fatturazione"


class FatturazioneGiroHandlerTests(SimpleTestCase):

    # 0. Corsia differita, competenza normalizzata al 1°, result senza `esiti`.
    @patch(_GIRO)
    def test_happy_path_differita_competenza_normalizzata_result_compatto(
        self, mock_giro,
    ) -> None:
        mock_giro.return_value = {
            "lane": 3, "per_motivo": {"COMPLETATO": 3}, "falliti": 0,
            "esiti": [{"x": 1}],  # lista per-terna: va compattata via
        }

        result = fatturazione_giro_handler(
            {"competenza_mese": "2026-06-15"},
            scope={"auth_user_id": 9, "emittente_ids": [3]},
        )

        kwargs = mock_giro.call_args.kwargs
        self.assertEqual(kwargs["modalita"], "differita")
        self.assertEqual(kwargs["competenza"], date(2026, 6, 1))  # 1° del mese
        self.assertNotIn("fino_a_stato", kwargs)  # non passato → default corsia
        self.assertNotIn("esiti", result)  # compattato
        self.assertEqual(result["lane"], 3)

    # 1. fino_a_stato opzionale propagato al core quando presente.
    @patch(_GIRO)
    def test_fino_a_stato_opzionale_propagato(self, mock_giro) -> None:
        mock_giro.return_value = {"lane": 0}
        fatturazione_giro_handler(
            {"competenza_mese": "2026-06-01", "fino_a_stato": "DEFINITIVA"},
            scope=None,
        )
        self.assertEqual(mock_giro.call_args.kwargs["fino_a_stato"], "DEFINITIVA")

    # 2. competenza mancante → codice registrato (non eccezione generica).
    @patch(_GIRO)
    def test_competenza_mancante_raises_payload(self, mock_giro) -> None:
        with self.assertRaises(ServiceError) as ctx:
            fatturazione_giro_handler({}, scope=None)
        self.assertEqual(ctx.exception.code, "E_FATTURAZIONE_GIRO_PAYLOAD")
        mock_giro.assert_not_called()

    # 3. competenza malformata → stesso codice registrato.
    @patch(_GIRO)
    def test_competenza_invalida_raises_payload(self, mock_giro) -> None:
        with self.assertRaises(ServiceError) as ctx:
            fatturazione_giro_handler({"competenza_mese": "non-una-data"}, scope=None)
        self.assertEqual(ctx.exception.code, "E_FATTURAZIONE_GIRO_PAYLOAD")
        mock_giro.assert_not_called()

    # 4. L'handler è registrato nel registry dopo il boot (VenditeConfig.ready()).
    def test_handler_registrato_dopo_boot(self) -> None:
        from apps.core.services.coda_lavori.handler_registry import (
            get_handler,
            registered_handlers,
        )
        self.assertIn(HANDLER_CODE, registered_handlers())
        self.assertIs(get_handler(HANDLER_CODE), fatturazione_giro_handler)
