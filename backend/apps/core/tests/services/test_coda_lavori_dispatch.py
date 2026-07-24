# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit del dispatch coda lavori (`drainer_service._dispatch_item`)
#        e del registry handler. Mock-only: verifica il routing per `run_as`
#        (SISTEMA → system_process_context; OPERATORE → operator_identity_context
#        + scope catturato), la risoluzione handler dal registry, e il guard
#        fail-loud su handler non registrato.
#
# Indice test:
#   1. dispatch_sistema_apre_canale_sistema_scope_none
#   2. dispatch_operatore_apre_contesto_operatore_con_scope
#   3. registry_register_e_get
#   4. registry_get_non_registrato_raises
#   5. context_operatore_setta_5_guc_e_resetta
#   6. context_operatore_scope_incompleto_raises
#   7. context_operatore_identita_inattiva_raises_e_resetta
# ------------------------------------------------------------

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.services.coda_lavori.backend import QueueItem
from apps.core.services.coda_lavori.drainer_service import _dispatch_item
from apps.core.services.coda_lavori.handler_registry import (
    get_handler,
    register_handler,
    registered_handlers,
)
from apps.core.services.service_errors import ServiceError

_MOD = "apps.core.services.coda_lavori.drainer_service"


def _item(run_as, scope) -> QueueItem:
    return QueueItem(
        id=7, job_type="J", payload={"a": 1}, run_as=run_as, scope=scope,
        tentativi=0, max_tentativi=5, raw={"handler_code": "h"},
    )


class DispatchTests(SimpleTestCase):

    # 1. SISTEMA → apre il canale di sistema (BYPASSRLS), handler con scope=None.
    @patch(f"{_MOD}.system_process_context")
    @patch(f"{_MOD}.get_handler")
    def test_dispatch_sistema_apre_canale_sistema_scope_none(
        self, get_handler_mock, sys_ctx,
    ) -> None:
        handler = MagicMock(return_value={"ok": 1})
        get_handler_mock.return_value = handler

        result = _dispatch_item(_item("SISTEMA", None))

        get_handler_mock.assert_called_once_with("h")
        sys_ctx.assert_called_once()  # canale di sistema aperto
        handler.assert_called_once_with({"a": 1}, scope=None)
        self.assertEqual(result, {"ok": 1})

    # 2. OPERATORE → apre il contesto operatore con l'identità COMPLETA
    #    (auth_user_id + username + identita_id) dallo scope catturato.
    @patch(f"{_MOD}.operator_identity_context")
    @patch(f"{_MOD}.get_handler")
    def test_dispatch_operatore_apre_contesto_operatore_con_scope(
        self, get_handler_mock, op_ctx,
    ) -> None:
        handler = MagicMock(return_value={"ok": 2})
        get_handler_mock.return_value = handler
        scope = {
            "auth_user_id": 9, "username": "op9", "identita_id": 5,
            "emittente_ids": [3, 4],
        }

        result = _dispatch_item(_item("OPERATORE", scope))

        op_ctx.assert_called_once_with(9, username="op9", identita_id=5)
        handler.assert_called_once_with({"a": 1}, scope=scope)
        self.assertEqual(result, {"ok": 2})


class RegistryTests(SimpleTestCase):

    # 3. register_handler + get_handler + registered_handlers.
    def test_registry_register_e_get(self) -> None:
        def _h(payload, *, scope):  # noqa: ARG001
            return {}
        register_handler("test_handler_xyz", _h)
        self.assertIn("test_handler_xyz", registered_handlers())
        self.assertIs(get_handler("test_handler_xyz"), _h)

    # 4. handler non registrato → fail-loud parlante (bug di cablaggio).
    def test_registry_get_non_registrato_raises(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            get_handler("handler_mai_registrato_qwerty")
        self.assertEqual(ctx.exception.code, "E_CODA_HANDLER_NON_REGISTRATO")


_CTX = "apps.core.services.coda_lavori.context"


class OperatorIdentityContextTests(SimpleTestCase):

    # 5. Identità completa → set_jwt_gucs (5 GUC come nel web) + reset canonico
    #    nel finally (JWT_GUC_RESET_SQL sulla connessione del worker).
    @patch(f"{_CTX}.connection")
    @patch(f"{_CTX}.set_jwt_gucs", return_value=True)
    def test_context_operatore_setta_5_guc_e_resetta(
        self, set_gucs, conn,
    ) -> None:
        from apps.core.api.jwt_audit_authentication import JWT_GUC_RESET_SQL
        from apps.core.services.coda_lavori.context import (
            operator_identity_context,
        )
        with operator_identity_context(9, username="op9", identita_id=5):
            set_gucs.assert_called_once_with(
                username="op9", user_id=9, identita_id=5,
            )
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.execute.assert_called_once_with(JWT_GUC_RESET_SQL)

    # 6. Scope incompleto (bug di accodamento) → fail-loud, nessun set GUC.
    @patch(f"{_CTX}.connection")
    @patch(f"{_CTX}.set_jwt_gucs")
    def test_context_operatore_scope_incompleto_raises(
        self, set_gucs, conn,
    ) -> None:
        from apps.core.services.coda_lavori.context import (
            operator_identity_context,
        )
        with self.assertRaises(ServiceError) as ctx:
            with operator_identity_context(9, username=None, identita_id=5):
                pass  # pragma: no cover
        self.assertEqual(ctx.exception.code, "E_CODA_SCOPE_OPERATORE_INVALIDO")
        set_gucs.assert_not_called()

    # 7. Identità revocata tra enqueue ed esecuzione → fail-loud (niente
    #    esecuzione con RLS a 0 righe) E reset dei GUC parziali nel finally.
    @patch(f"{_CTX}.connection")
    @patch(f"{_CTX}.set_jwt_gucs", return_value=False)
    def test_context_operatore_identita_inattiva_raises_e_resetta(
        self, _set_gucs, conn,
    ) -> None:
        from apps.core.services.coda_lavori.context import (
            operator_identity_context,
        )
        with self.assertRaises(ServiceError) as ctx:
            with operator_identity_context(9, username="op9", identita_id=5):
                pass  # pragma: no cover
        self.assertEqual(ctx.exception.code, "E_CODA_IDENTITA_NON_ATTIVA")
        # Il reset gira comunque (GUC parziali azzerate).
        cursor = conn.cursor.return_value.__enter__.return_value
        self.assertEqual(cursor.execute.call_count, 1)
