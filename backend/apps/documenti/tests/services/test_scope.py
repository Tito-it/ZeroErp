# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit `apps.documenti.services._scope`. Helper centralizzato
#        condiviso da `template_admin_service`, `template_asset_admin_service`
#        e `document_generation_service` — la sua correttezza copre lo
#        scope/auth check di tutto il dominio documenti. Mock-only.
#
# Indice test (0..N):
#   0. guard_user_authenticated_user_none_raises
#   1. guard_user_authenticated_user_not_authenticated_raises
#   2. guard_user_authenticated_user_authenticated_no_raise
#   3. resolve_emittente_scope_delega_a_permission_resolver
#   4. guard_emittente_in_scope_admin_globale_no_raise
#   5. guard_emittente_in_scope_id_in_scope_no_raise
#   6. guard_emittente_in_scope_id_fuori_scope_raises
#   7. guard_emittente_in_scope_for_user_happy_path
#   8. guard_emittente_in_scope_for_user_anon_raises
#   9. guard_emittente_in_scope_for_user_fuori_scope_raises
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.documenti.services import _scope


def _user(*, authenticated: bool = True) -> Any:
    u = MagicMock()
    u.is_authenticated = authenticated
    return u


class GuardUserAuthenticatedTests(SimpleTestCase):
    # 0. user None -> ServiceError E_DOCUMENTI_VALIDATION.
    def test_guard_user_authenticated_user_none_raises(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            _scope.guard_user_authenticated(None)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")

    # 1. user non autenticato -> stesso errore.
    def test_guard_user_authenticated_user_not_authenticated_raises(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            _scope.guard_user_authenticated(_user(authenticated=False))
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")

    # 2. user autenticato -> nessuna eccezione.
    def test_guard_user_authenticated_user_authenticated_no_raise(self) -> None:
        # Non solleva.
        _scope.guard_user_authenticated(_user(authenticated=True))


class ResolveEmittenteScopeTests(SimpleTestCase):
    # 3. delega all'oggetto PermissionResolver.get_emittenti_pk_ids.
    @patch(
        "apps.documenti.services._scope.PermissionResolver.get_emittenti_pk_ids",
    )
    def test_resolve_emittente_scope_delega_a_permission_resolver(
        self, mock_resolver
    ) -> None:
        mock_resolver.return_value = [11, 22]
        u = _user()
        result = _scope.resolve_emittente_scope(u)
        self.assertEqual(result, [11, 22])
        mock_resolver.assert_called_once_with(u)


class GuardEmittenteInScopeTests(SimpleTestCase):
    # 4. scope=None (admin globale) -> qualunque id passa.
    def test_guard_emittente_in_scope_admin_globale_no_raise(self) -> None:
        _scope.guard_emittente_in_scope(None, 999)

    # 5. id presente nello scope -> nessuna eccezione.
    def test_guard_emittente_in_scope_id_in_scope_no_raise(self) -> None:
        _scope.guard_emittente_in_scope([11, 22], 11)

    # 6. id fuori scope -> E_DOCUMENTI_VALIDATION con messaggio parlante.
    def test_guard_emittente_in_scope_id_fuori_scope_raises(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            _scope.guard_emittente_in_scope([1, 2], 99)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        self.assertIn("99", str(ctx.exception.detail or ""))


class GuardEmittenteInScopeForUserTests(SimpleTestCase):
    # 7. happy path: user autenticato + id in scope.
    @patch(
        "apps.documenti.services._scope.PermissionResolver.get_emittenti_pk_ids",
        return_value=[11, 22],
    )
    def test_guard_emittente_in_scope_for_user_happy_path(
        self, _mock_resolver
    ) -> None:
        # Non solleva.
        _scope.guard_emittente_in_scope_for_user(_user(), 11)

    # 8. user anon -> raise pre-resolver (mai chiamato).
    @patch(
        "apps.documenti.services._scope.PermissionResolver.get_emittenti_pk_ids",
    )
    def test_guard_emittente_in_scope_for_user_anon_raises(
        self, mock_resolver
    ) -> None:
        with self.assertRaises(ServiceError) as ctx:
            _scope.guard_emittente_in_scope_for_user(None, 11)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        mock_resolver.assert_not_called()

    # 9. user autenticato ma id fuori scope -> raise.
    @patch(
        "apps.documenti.services._scope.PermissionResolver.get_emittenti_pk_ids",
        return_value=[1, 2],
    )
    def test_guard_emittente_in_scope_for_user_fuori_scope_raises(
        self, _mock_resolver
    ) -> None:
        with self.assertRaises(ServiceError) as ctx:
            _scope.guard_emittente_in_scope_for_user(_user(), 99)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
