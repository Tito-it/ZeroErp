# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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

    # 1. ⛔ SISTEMA → NESSUN canale di sistema (R-2, 2026-09-05). Il test e'
    #    stato GIRATO, non tolto: prima verificava che il canale `BYPASSRLS`
    #    venisse aperto, adesso che non esista piu' nulla da aprire.
    #    ⭐ `SISTEMA` ha cambiato significato: voleva dire «col bypass», adesso
    #    vuole dire «senza emittente». L'handler gira sul ruolo applicativo
    #    normale con `scope=None`, quindi puo' toccare solo cio' che non ha un
    #    perimetro.
    @patch(f"{_MOD}.get_handler")
    def test_dispatch_sistema_senza_canale_scope_none(
        self, get_handler_mock,
    ) -> None:
        import apps.core.services.coda_lavori.drainer_service as modulo

        handler = MagicMock(return_value={"ok": 1})
        get_handler_mock.return_value = handler

        result = _dispatch_item(_item("SISTEMA", None))

        get_handler_mock.assert_called_once_with("h")
        handler.assert_called_once_with({"a": 1}, scope=None)
        self.assertEqual(result, {"ok": 1})
        # ⭐ Si guarda il MODULO, non una chiamata: un gateway importato e non
        #    ancora usato sarebbe il primo passo per rimetterlo.
        self.assertFalse(hasattr(modulo, "system_process_context"))

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
            # Emittente congelato all'enqueue: il worker deve rimetterlo,
            # altrimenti il job gira in modalità globale e tocca anche gli
            # emittenti che il richiedente non stava guardando.
            "emittente_attivo_id": 3,
        }

        result = _dispatch_item(_item("OPERATORE", scope))

        op_ctx.assert_called_once_with(
            9, username="op9", identita_id=5, emittente_attivo_id=3,
        )
        handler.assert_called_once_with({"a": 1}, scope=scope)
        self.assertEqual(result, {"ok": 2})


# Scopo: toglie un handler dal registry globale. ⚠️ Il registry non espone un
#        `unregister` — e non deve: in esercizio un handler non si ritira a
#        runtime. Qui si tocca il dizionario interno di proposito, ed e' l'unico
#        punto che lo fa.
def _dimentica_handler(codice: str) -> None:
    from apps.core.services.coda_lavori import handler_registry

    handler_registry._REGISTRY.pop(codice, None)


class RegistryTests(SimpleTestCase):

    # 3. register_handler + get_handler + registered_handlers.
    #
    # ⚠️ IL REGISTRY E' GLOBALE E VIVE OLTRE IL TEST, quindi si ripulisce. Non e'
    #    igiene formale: il finto `test_handler_xyz` restava registrato per tutta
    #    la corsa e faceva rosso il presidio degli handler orfani
    #    (`apps/core/tests/db/test_coda_lavori_tipi_handler_guardrail.py`), che
    #    cerca proprio gli handler che nessun tipo di coda nomina. Un test che
    #    sporca uno stato condiviso rompe un ALTRO test, e il rosso compare dove
    #    il difetto non e'.
    def test_registry_register_e_get(self) -> None:
        def _h(payload, *, scope):
            return {}
        register_handler("test_handler_xyz", _h)
        self.addCleanup(_dimentica_handler, "test_handler_xyz")
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
    def test_context_operatore_setta_6_guc_e_resetta(
        self, set_gucs, conn,
    ) -> None:
        from apps.core.api.jwt_audit_authentication import JWT_GUC_RESET_SQL
        from apps.core.services.coda_lavori.context import (
            operator_identity_context,
        )
        with operator_identity_context(
            9, username="op9", identita_id=5, emittente_attivo_id=3,
        ):
            set_gucs.assert_called_once_with(
                username="op9", user_id=9, identita_id=5,
                emittente_attivo_id=3,
            )
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.execute.assert_called_once_with(JWT_GUC_RESET_SQL)

    # 5-bis. Job accodato PRIMA del cantiere impersonazione: la chiave non
    #        esiste nello scope → None → modalità globale, comportamento
    #        storico. I job in coda al momento del rilascio non devono fallire.
    @patch(f"{_CTX}.connection")
    @patch(f"{_CTX}.set_jwt_gucs")
    def test_context_operatore_senza_emittente_congelato(
        self, set_gucs, conn,
    ) -> None:
        from apps.core.services.coda_lavori.context import (
            operator_identity_context,
        )
        with operator_identity_context(9, username="op9", identita_id=5):
            set_gucs.assert_called_once_with(
                username="op9", user_id=9, identita_id=5,
                emittente_attivo_id=None,
            )

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
