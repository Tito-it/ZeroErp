# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per handler_registry (mapping handler_key → classe).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) HandlerRegistryTests.test_handler_map_vuota_per_default
2) HandlerRegistryTests.test_get_handler_chiave_mancante
3) HandlerRegistryTests.test_get_handler_chiave_registrata
"""

from unittest.mock import patch

from django.test import SimpleTestCase

from apps.pratiche.services.handler_registry import HANDLER_MAP, get_handler


class HandlerRegistryTests(SimpleTestCase):

    # Scopo: Verifica che HANDLER_MAP sia vuoto di default (nessun handler registrato).
    def test_handler_map_vuota_per_default(self):
        self.assertEqual(len(HANDLER_MAP), 0)

    # Scopo: Verifica che get_handler ritorni None per chiave non registrata.
    def test_get_handler_chiave_mancante(self):
        result = get_handler("HANDLER_INESISTENTE")
        self.assertIsNone(result)

    # Scopo: Verifica che get_handler ritorni la classe per chiave registrata.
    def test_get_handler_chiave_registrata(self):
        # Registra temporaneamente un handler fittizio.
        class _FakeHandler:
            def execute(self, flusso_id, pratica_id, meta):
                return {}

        with patch.dict(HANDLER_MAP, {"FAKE_HANDLER": _FakeHandler}):
            result = get_handler("FAKE_HANDLER")
            self.assertIs(result, _FakeHandler)
