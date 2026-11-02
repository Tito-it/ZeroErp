# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit TemplateService. Mocka DocumentiRepository (via
#        init param) e PermissionResolver.get_emittenti_pk_ids (via patch).
#        Verifica:
#        - scope emittente: admin globale -> None, operatore -> lista,
#          user None/non auth -> lista vuota (no leak);
#        - get_template solleva E_DOCUMENTI_NOT_FOUND su row None;
#        - list_versioni pre-verifica visibilita' template (404);
#        - stato versione invalido -> E_DOCUMENTI_VALIDATION;
#        - id non positivo -> E_DOCUMENTI_VALIDATION.
#
# Indice test (0..N):
#   0. list_templates_passes_emittenti_ids_for_operator
#   1. list_templates_admin_globale_passes_none
#   2. list_templates_anonymous_user_no_leak
#   3. get_template_not_found_raises
#   4. get_template_invalid_id_raises_validation
#   5. list_versioni_404_if_template_invisible
#   6. list_versioni_invalid_stato_raises
#   7. get_versione_404_if_versione_missing
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.documenti.services.template_service import TemplateService


def _make_user(*, is_authenticated: bool = True) -> Any:
    user = MagicMock()
    user.is_authenticated = is_authenticated
    return user


class TemplateServiceListTests(SimpleTestCase):
    # 0. operatore -> emittente_ids_scope = lista.
    @patch(
        "apps.documenti.services.template_service.PermissionResolver.get_emittenti_pk_ids",
        return_value=[11, 22],
    )
    def test_list_templates_passes_emittenti_ids_for_operator(self, _mock) -> None:
        repo = MagicMock()
        repo.list_templates.return_value = ([{"id": 1}], 1)
        service = TemplateService(repo=repo)

        out = service.list_templates(_make_user())

        repo.list_templates.assert_called_once()
        call_kwargs = repo.list_templates.call_args.kwargs
        self.assertEqual(call_kwargs["emittente_ids_scope"], [11, 22])
        self.assertEqual(out, {"results": [{"id": 1}], "total_count": 1})

    # 1. admin globale -> emittente_ids_scope = None (vede tutto).
    @patch(
        "apps.documenti.services.template_service.PermissionResolver.get_emittenti_pk_ids",
        return_value=None,
    )
    def test_list_templates_admin_globale_passes_none(self, _mock) -> None:
        repo = MagicMock()
        repo.list_templates.return_value = ([], 0)
        service = TemplateService(repo=repo)

        service.list_templates(_make_user())

        self.assertIsNone(repo.list_templates.call_args.kwargs["emittente_ids_scope"])

    # 2. user non autenticato -> emittente_ids_scope = [] (no leak).
    def test_list_templates_anonymous_user_no_leak(self) -> None:
        repo = MagicMock()
        repo.list_templates.return_value = ([], 0)
        service = TemplateService(repo=repo)

        service.list_templates(_make_user(is_authenticated=False))

        self.assertEqual(repo.list_templates.call_args.kwargs["emittente_ids_scope"], [])

        # Anche None -> [].
        repo.reset_mock()
        repo.list_templates.return_value = ([], 0)
        service.list_templates(None)
        self.assertEqual(repo.list_templates.call_args.kwargs["emittente_ids_scope"], [])


class TemplateServiceGetTemplateTests(SimpleTestCase):
    # 3. row None -> E_DOCUMENTI_NOT_FOUND.
    @patch(
        "apps.documenti.services.template_service.PermissionResolver.get_emittenti_pk_ids",
        return_value=[11],
    )
    def test_get_template_not_found_raises(self, _mock) -> None:
        repo = MagicMock()
        repo.get_template.return_value = None
        service = TemplateService(repo=repo)

        with self.assertRaises(ServiceError) as ctx:
            service.get_template(_make_user(), 42)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_NOT_FOUND")

    # 4. id non positivo -> E_DOCUMENTI_VALIDATION (no DB call).
    def test_get_template_invalid_id_raises_validation(self) -> None:
        repo = MagicMock()
        service = TemplateService(repo=repo)

        with self.assertRaises(ServiceError) as ctx:
            service.get_template(_make_user(), 0)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.get_template.assert_not_called()


class TemplateServiceVersioniTests(SimpleTestCase):
    # 5. list_versioni: template fuori scope (get_template -> None) -> 404.
    @patch(
        "apps.documenti.services.template_service.PermissionResolver.get_emittenti_pk_ids",
        return_value=[11],
    )
    def test_list_versioni_404_if_template_invisible(self, _mock) -> None:
        repo = MagicMock()
        repo.get_template.return_value = None
        service = TemplateService(repo=repo)

        with self.assertRaises(ServiceError) as ctx:
            service.list_versioni(_make_user(), 42)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_NOT_FOUND")
        repo.list_versioni.assert_not_called()

    # 6. stato versione fuori whitelist -> E_DOCUMENTI_VALIDATION.
    @patch(
        "apps.documenti.services.template_service.PermissionResolver.get_emittenti_pk_ids",
        return_value=None,
    )
    def test_list_versioni_invalid_stato_raises(self, _mock) -> None:
        repo = MagicMock()
        repo.get_template.return_value = {"id": 42}
        service = TemplateService(repo=repo)

        with self.assertRaises(ServiceError) as ctx:
            service.list_versioni(_make_user(), 42, stato="INESISTENTE")
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")

    # 7. get_versione: template visibile + versione None -> 404 sulla versione.
    @patch(
        "apps.documenti.services.template_service.PermissionResolver.get_emittenti_pk_ids",
        return_value=None,
    )
    def test_get_versione_404_if_versione_missing(self, _mock) -> None:
        repo = MagicMock()
        repo.get_template.return_value = {"id": 42}
        repo.get_versione.return_value = None
        service = TemplateService(repo=repo)

        with self.assertRaises(ServiceError) as ctx:
            service.get_versione(_make_user(), 42, 99)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_NOT_FOUND")
        repo.get_versione.assert_called_once_with(42, 99)
