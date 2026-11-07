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
    #    ⭐ BE10 (2026-11-07): e gira SENZA identita' anche dentro il giro di
    #    un utente tecnico — col badge addosso lavorerebbe col perimetro di
    #    quell'azienda, che non e' il suo.
    @patch(f"{_MOD}.senza_identita_context")
    @patch(f"{_MOD}.get_handler")
    def test_dispatch_sistema_senza_canale_scope_none(
        self, get_handler_mock, senza_ctx,
    ) -> None:
        import apps.core.services.coda_lavori.drainer_service as modulo

        dentro: list[bool] = []
        handler = MagicMock(side_effect=lambda *_a, **_k: (
            dentro.append(senza_ctx.return_value.__enter__.called), {"ok": 1})[1])
        get_handler_mock.return_value = handler

        result = _dispatch_item(_item("SISTEMA", None))

        get_handler_mock.assert_called_once_with("h")
        handler.assert_called_once_with({"a": 1}, scope=None)
        self.assertEqual(dentro, [True])
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


# Scopo: una connessione finta che risponde alla lettura dei GUC identita'
#        con `precedente` (tutti '' = nessuna identita') e registra le query.
def _connessione_finta(conn, precedente=None):
    from apps.core.api.jwt_audit_authentication import JWT_IDENTITY_GUCS
    cursor = conn.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = tuple(precedente or ("",) * len(JWT_IDENTITY_GUCS))
    return cursor


class OperatorIdentityContextTests(SimpleTestCase):

    # 5. Identità completa → set_jwt_gucs (6 GUC come nel web); senza
    #    un'identità prima, all'uscita il reset canonico (JWT_GUC_RESET_SQL).
    @patch(f"{_CTX}.connection")
    @patch(f"{_CTX}.set_jwt_gucs", return_value=True)
    def test_context_operatore_setta_6_guc_e_resetta(
        self, set_gucs, conn,
    ) -> None:
        from apps.core.api.jwt_audit_authentication import JWT_GUC_RESET_SQL
        from apps.core.services.coda_lavori.context import (
            operator_identity_context,
        )
        cursor = _connessione_finta(conn)
        with operator_identity_context(
            9, username="op9", identita_id=5, emittente_attivo_id=3,
        ):
            set_gucs.assert_called_once_with(
                username="op9", user_id=9, identita_id=5,
                emittente_attivo_id=3,
            )
        self.assertEqual(cursor.execute.call_args.args, (JWT_GUC_RESET_SQL,))

    # 5-ter. ⛔ BE10: dentro l'identità di un badge, all'uscita torna QUELLA,
    #        non il vuoto. Azzerando, la `mark_done` del drenatore girava senza
    #        identità e sotto la RLS aggiornava zero righe senza dirlo.
    @patch(f"{_CTX}.connection")
    @patch(f"{_CTX}.set_jwt_gucs", return_value=True)
    def test_context_operatore_rimette_l_identita_esterna(
        self, _set_gucs, conn,
    ) -> None:
        from apps.core.api.jwt_audit_authentication import JWT_IDENTITY_GUCS
        from apps.core.services.coda_lavori.context import (
            _IDENTITA_RIPRISTINA_SQL,
            operator_identity_context,
        )
        badge = ("badge@ACME", "70", "700", "OPERATORE", "7000", "3")
        self.assertEqual(len(badge), len(JWT_IDENTITY_GUCS))
        cursor = _connessione_finta(conn, badge)
        with operator_identity_context(9, username="op9", identita_id=5):
            pass
        self.assertEqual(
            cursor.execute.call_args.args, (_IDENTITA_RIPRISTINA_SQL, list(badge)),
        )

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
        _connessione_finta(conn)
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
    #    esecuzione con RLS a 0 righe) E i GUC parziali via nel finally: torna
    #    l'identità di prima (qui nessuna, quindi il reset canonico).
    @patch(f"{_CTX}.connection")
    @patch(f"{_CTX}.set_jwt_gucs", return_value=False)
    def test_context_operatore_identita_inattiva_raises_e_resetta(
        self, _set_gucs, conn,
    ) -> None:
        from apps.core.api.jwt_audit_authentication import JWT_GUC_RESET_SQL
        from apps.core.services.coda_lavori.context import (
            operator_identity_context,
        )
        cursor = _connessione_finta(conn)
        with self.assertRaises(ServiceError) as ctx:
            with operator_identity_context(9, username="op9", identita_id=5):
                pass  # pragma: no cover
        self.assertEqual(ctx.exception.code, "E_CODA_IDENTITA_NON_ATTIVA")
        self.assertEqual(cursor.execute.call_args.args, (JWT_GUC_RESET_SQL,))


class SenzaIdentitaContextTests(SimpleTestCase):

    # 8. ⭐ BE10: senza identità dentro il blocco (reset canonico), e
    #    all'uscita torna quella del badge, anche su eccezione.
    @patch(f"{_CTX}.connection")
    def test_azzera_e_rimette_anche_su_eccezione(self, conn) -> None:
        from apps.core.api.jwt_audit_authentication import JWT_GUC_RESET_SQL
        from apps.core.services.coda_lavori.context import (
            _IDENTITA_RIPRISTINA_SQL,
            senza_identita_context,
        )
        badge = ("badge@ACME", "70", "700", "OPERATORE", "7000", "3")
        cursor = _connessione_finta(conn, badge)
        with self.assertRaises(RuntimeError):
            with senza_identita_context():
                self.assertEqual(cursor.execute.call_args.args, (JWT_GUC_RESET_SQL,))
                raise RuntimeError("lavoro fallito")
        self.assertEqual(
            cursor.execute.call_args.args, (_IDENTITA_RIPRISTINA_SQL, list(badge)),
        )
