# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per handler_registry (mapping handler_key → classe).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) HandlerRegistryTests.test_handler_vendite_registrato_al_boot
2) HandlerRegistryTests.test_get_handler_chiave_mancante
3) HandlerRegistryTests.test_get_handler_chiave_registrata
4) HandlerRegistryTests.test_register_handler
"""

from unittest.mock import patch

from django.test import SimpleTestCase

from apps.pratiche.services.handler_registry import (
    HANDLER_MAP,
    get_handler,
    register_handler,
)


class HandlerRegistryTests(SimpleTestCase):

    # Scopo: il primo handler reale (vendita.push_preventivo) e' registrato al
    # boot da apps/vendite/apps.py:ready() — non piu' registry vuoto.
    def test_handler_vendite_registrato_al_boot(self):
        self.assertIn("vendita.push_preventivo", HANDLER_MAP)

    # Scopo: Verifica che get_handler ritorni None per chiave non registrata.
    def test_get_handler_chiave_mancante(self):
        result = get_handler("HANDLER_INESISTENTE")
        self.assertIsNone(result)

    # Scopo: Verifica che get_handler ritorni la classe per chiave registrata.
    def test_get_handler_chiave_registrata(self):
        # Registra temporaneamente un handler fittizio.
        class _FakeHandler:
            def execute(self, flusso_id, pratica_id, meta, handler_params):
                return {}

        with patch.dict(HANDLER_MAP, {"FAKE_HANDLER": _FakeHandler}):
            result = get_handler("FAKE_HANDLER")
            self.assertIs(result, _FakeHandler)

    # Scopo: register_handler popola la mappa (usato da AppConfig.ready()).
    def test_register_handler(self):
        class _FakeHandler:
            def execute(self, flusso_id, pratica_id, meta, handler_params, user=None):
                return {}

        with patch.dict(HANDLER_MAP, {}, clear=False):
            register_handler("FAKE_REG", _FakeHandler)
            self.assertIs(get_handler("FAKE_REG"), _FakeHandler)
