# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari EmittenteFiscaleScopeMixin — filtro queryset per scope emittente.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_superuser_nessun_filtro
 2) test_emittente_field_none_nessun_filtro
 3) test_admin_nessun_filtro
 4) test_operativo_senza_righe_nessun_filtro
 5) test_operativo_con_righe_filtra_queryset
 6) test_filtro_usa_campo_personalizzato
 7) test_cache_request_riutilizzata
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.mixins import EmittenteFiscaleScopeMixin


_RESOLVER = "apps.core.mixins.PermissionResolver"


def _mock_request(
    user_id: int = 1,
    is_superuser: bool = False,
    cache: dict | None = None,
) -> MagicMock:
    """Scopo: Crea un mock HttpRequest con user configurato."""
    request = MagicMock()
    request.user.id = user_id
    request.user.is_superuser = is_superuser
    if cache is not None:
        request._zeroerp_perms_cache = cache
    else:
        # Simula assenza attributo cache
        del request._zeroerp_perms_cache
    return request


class _FakeParentView:
    """Scopo: Simula la classe base con get_queryset e request."""

    def __init__(self, qs: MagicMock, request: MagicMock) -> None:
        self._qs = qs
        self.request = request

    def get_queryset(self) -> MagicMock:
        return self._qs


class _ViewWithMixin(EmittenteFiscaleScopeMixin, _FakeParentView):
    """Scopo: View concreta che combina mixin + parent per i test."""

    pass


class EmittenteFiscaleScopeMixinTests(TestCase):
    """Test per EmittenteFiscaleScopeMixin."""

    # Scopo: Superuser non viene mai filtrato.
    def test_superuser_nessun_filtro(self):
        qs = MagicMock()
        request = _mock_request(is_superuser=True)
        view = _ViewWithMixin(qs, request)
        view.emittente_field = "emittente_fiscale_id"

        result = view.get_queryset()

        self.assertIs(result, qs)
        qs.filter.assert_not_called()

    # Scopo: Se emittente_field è None, nessun filtro applicato.
    def test_emittente_field_none_nessun_filtro(self):
        qs = MagicMock()
        request = _mock_request()
        view = _ViewWithMixin(qs, request)
        view.emittente_field = None

        result = view.get_queryset()

        self.assertIs(result, qs)
        qs.filter.assert_not_called()

    # Scopo: Utente SUPER_ADMIN non viene filtrato.
    @patch(_RESOLVER)
    def test_admin_nessun_filtro(self, mock_resolver):
        mock_resolver.is_super_admin.return_value = True

        qs = MagicMock()
        request = _mock_request()
        view = _ViewWithMixin(qs, request)
        view.emittente_field = "emittente_fiscale_id"

        result = view.get_queryset()

        self.assertIs(result, qs)
        qs.filter.assert_not_called()

    # Scopo: OPERATORE senza righe emittenti vede tutto (None = nessuna restrizione).
    @patch(_RESOLVER)
    def test_operativo_senza_righe_nessun_filtro(self, mock_resolver):
        mock_resolver.is_super_admin.return_value = False
        mock_resolver.get_emittenti_ids.return_value = None

        qs = MagicMock()
        request = _mock_request()
        view = _ViewWithMixin(qs, request)
        view.emittente_field = "emittente_fiscale_id"

        result = view.get_queryset()

        self.assertIs(result, qs)
        qs.filter.assert_not_called()

    # Scopo: OPERATORE con righe emittenti filtra il queryset.
    @patch(_RESOLVER)
    def test_operativo_con_righe_filtra_queryset(self, mock_resolver):
        mock_resolver.is_super_admin.return_value = False
        mock_resolver.get_emittenti_ids.return_value = [1, 3, 5]

        qs = MagicMock()
        filtered_qs = MagicMock()
        qs.filter.return_value = filtered_qs

        request = _mock_request()
        view = _ViewWithMixin(qs, request)
        view.emittente_field = "emittente_fiscale_id"

        result = view.get_queryset()

        self.assertIs(result, filtered_qs)
        qs.filter.assert_called_once_with(emittente_fiscale_id__in=[1, 3, 5])

    # Scopo: Il filtro usa il campo personalizzato (path con lookup).
    @patch(_RESOLVER)
    def test_filtro_usa_campo_personalizzato(self, mock_resolver):
        mock_resolver.is_super_admin.return_value = False
        mock_resolver.get_emittenti_ids.return_value = [2, 4]

        qs = MagicMock()
        filtered_qs = MagicMock()
        qs.filter.return_value = filtered_qs

        request = _mock_request()
        view = _ViewWithMixin(qs, request)
        view.emittente_field = "billing_account__emittente_fiscale_id"

        view.get_queryset()

        qs.filter.assert_called_once_with(
            billing_account__emittente_fiscale_id__in=[2, 4]
        )

    # Scopo: La cache su request viene riutilizzata se presente.
    @patch(_RESOLVER)
    def test_cache_request_riutilizzata(self, mock_resolver):
        mock_resolver.is_super_admin.return_value = False
        mock_resolver.get_emittenti_ids.return_value = [10]

        qs = MagicMock()
        qs.filter.return_value = MagicMock()

        cache = {"is_super_admin": False}
        request = _mock_request(cache=cache)
        view = _ViewWithMixin(qs, request)
        view.emittente_field = "emittente_fiscale_id"

        view.get_queryset()

        # Verifica che il resolver riceva il dict cache dalla request
        mock_resolver.is_super_admin.assert_called_once()
        call_kwargs = mock_resolver.is_super_admin.call_args
        self.assertIs(call_kwargs[1]["cache"], cache)
