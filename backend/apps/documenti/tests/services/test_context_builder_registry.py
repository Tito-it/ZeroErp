# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit registry DocumentContextBuilder. Verifica
#        registrazione idempotente, dispatch su CODE, errore
#        whitelisted su codice non registrato, errore su builder
#        senza CODE. Niente DB (SimpleTestCase).
#
# Indice test (0..N):
#   0. register_then_get_returns_same_instance
#   1. register_idempotent_overwrite
#   2. get_unknown_code_raises_validation
#   3. register_builder_without_code_raises_validation
#   4. registered_codes_returns_sorted_list
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.documenti.services.context_builders import (
    DocumentContextBuilder,
    get_builder,
    register_builder,
    registered_codes,
)
from apps.documenti.services.context_builders import registry as registry_mod


class _FakeBuilder(DocumentContextBuilder):
    """Builder finto per test: ritorna il sorgente_id mappato a chiave 'id'."""

    def __init__(self, code: str) -> None:
        self.CODE = code

    def build_context(
        self,
        sorgente_id: int,
        *,
        auth_user_id: int | None = None,
        locale: str = "it-IT",
    ) -> dict[str, Any]:
        return {"id": sorgente_id, "locale": locale}


class _BuilderWithoutCode(DocumentContextBuilder):
    def build_context(
        self,
        sorgente_id: int,
        *,
        auth_user_id: int | None = None,
        locale: str = "it-IT",
    ) -> dict[str, Any]:
        return {}


class DocumentContextBuilderRegistryTests(SimpleTestCase):
    def setUp(self) -> None:
        # Scopo: snapshot/restore del dict modulo-level per non leakare tra test.
        self._snapshot = dict(registry_mod._REGISTRY)
        registry_mod._REGISTRY.clear()
        self.addCleanup(self._restore_registry)

    def _restore_registry(self) -> None:
        registry_mod._REGISTRY.clear()
        registry_mod._REGISTRY.update(self._snapshot)

    # 0. dispatch base.
    def test_register_then_get_returns_same_instance(self) -> None:
        b = _FakeBuilder("PREVENTIVO")
        register_builder(b)
        self.assertIs(get_builder("PREVENTIVO"), b)

    # 1. registrazione idempotente: secondo register sostituisce.
    def test_register_idempotent_overwrite(self) -> None:
        b1 = _FakeBuilder("PREVENTIVO")
        b2 = _FakeBuilder("PREVENTIVO")
        register_builder(b1)
        register_builder(b2)
        self.assertIs(get_builder("PREVENTIVO"), b2)

    # 2. codice non registrato → E_DOCUMENTI_VALIDATION.
    def test_get_unknown_code_raises_validation(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            get_builder("ORDINE_INESISTENTE")
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")

    # 3. builder senza CODE → E_DOCUMENTI_VALIDATION.
    def test_register_builder_without_code_raises_validation(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            register_builder(_BuilderWithoutCode())
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")

    # 4. registered_codes ritorna chiavi ordinate.
    def test_registered_codes_returns_sorted_list(self) -> None:
        register_builder(_FakeBuilder("PREVENTIVO"))
        register_builder(_FakeBuilder("CONTRATTO"))
        register_builder(_FakeBuilder("ORDINE"))
        self.assertEqual(registered_codes(), ["CONTRATTO", "ORDINE", "PREVENTIVO"])
