# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per endpoint parametri di sistema.
#        GET /api/v1/core/parameters/defaults/
#        GET /api/v1/core/parameters/settings/
#        POST /api/v1/core/parameters/settings/override/
#        DELETE /api/v1/core/parameters/settings/override/<id>/
#        Mock service, compatibile CI senza database reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) ParameterDefaultsViewTests.test_get_defaults_success
 2) ParameterDefaultsViewTests.test_get_defaults_empty_codes
 3) ParameterDefaultsViewTests.test_get_defaults_passes_emittente_context
 4) ParameterSettingsViewTests.test_list_settings_success
 5) ParameterSettingsViewTests.test_list_settings_superuser_resolves_emittente
 6) ParameterOverrideViewTests.test_upsert_override_success
 7) ParameterOverrideDeleteViewTests.test_delete_override_success
 8) ParameterOverrideDeleteViewTests.test_delete_override_not_found
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.service_errors import ServiceError

SVC_PATH = "apps.core.api.views_parameters.ParameterService"


def _make_request(user_id=1, is_superuser=False, query_params=None, data=None):
    """Crea un mock Request con utente autenticato."""
    request = MagicMock()
    request.user.id = user_id
    request.user.is_superuser = is_superuser
    request.user.is_authenticated = True
    request.user.groups.values_list.return_value = [10, 20]
    request.query_params = query_params or {}
    request.META = {"CONTENT_TYPE": "application/json"}
    if data is not None:
        request.body = __import__("json").dumps(data).encode()
        request.content_type = "application/json"
    return request


class ParameterDefaultsViewTests(TestCase):

    # Scopo: Verifica che GET defaults restituisca i valori risolti.
    @patch(SVC_PATH)
    def test_get_defaults_success(self, mock_svc_cls):
        from apps.core.api.views_parameters import ParameterDefaultsView

        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.get_defaults.return_value = {"DEFAULT_IVA_ID": "22"}
        mock_svc.get_emittente_fiscale_id_for_user.return_value = 3

        view = ParameterDefaultsView()
        request = _make_request(query_params={"codes": "DEFAULT_IVA_ID"})
        response = view.get(request)

        self.assertEqual(response.status_code, 200)
        import json
        body = json.loads(response.content)
        self.assertEqual(body["data"]["DEFAULT_IVA_ID"], "22")

    # Scopo: Verifica che GET defaults senza codici restituisca dict vuoto.
    @patch(SVC_PATH)
    def test_get_defaults_empty_codes(self, mock_svc_cls):
        from apps.core.api.views_parameters import ParameterDefaultsView

        view = ParameterDefaultsView()
        request = _make_request(query_params={"codes": ""})
        response = view.get(request)

        self.assertEqual(response.status_code, 200)
        import json
        body = json.loads(response.content)
        self.assertEqual(body["data"], {})

    # Scopo: Verifica che il contesto emittente fiscale venga passato al service.
    @patch(SVC_PATH)
    def test_get_defaults_passes_emittente_context(self, mock_svc_cls):
        from apps.core.api.views_parameters import ParameterDefaultsView

        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.get_defaults.return_value = {"P1": "v1"}
        mock_svc.get_emittente_fiscale_id_for_user.return_value = 5

        view = ParameterDefaultsView()
        request = _make_request(user_id=7, query_params={"codes": "P1"})
        response = view.get(request)

        self.assertEqual(response.status_code, 200)
        mock_svc.get_defaults.assert_called_once_with(
            ["P1"],
            django_user_id=7,
            group_ids=[10, 20],
            emittente_fiscale_id=5,
        )


class ParameterSettingsViewTests(TestCase):

    # Scopo: Verifica che GET settings restituisca la lista parametri con livelli.
    @patch(SVC_PATH)
    def test_list_settings_success(self, mock_svc_cls):
        from apps.core.api.views_parameters import ParameterSettingsView

        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.get_emittente_fiscale_id_for_user.return_value = 3
        mock_svc.list_parameters_for_user.return_value = [
            {
                "code": "DEFAULT_IVA_ID",
                "description": "IVA default",
                "default_value": "22",
                "emittente_value": "10",
                "group_value": None,
                "user_value": "5",
                "user_override_id": 42,
                "resolved_value": "5",
            },
        ]

        view = ParameterSettingsView()
        request = _make_request(user_id=1)
        response = view.get(request)

        self.assertEqual(response.status_code, 200)
        import json
        body = json.loads(response.content)
        self.assertIsInstance(body["data"], list)
        self.assertEqual(len(body["data"]), 1)
        self.assertEqual(body["data"][0]["code"], "DEFAULT_IVA_ID")
        self.assertEqual(body["data"][0]["resolved_value"], "5")
        mock_svc.list_parameters_for_user.assert_called_once_with(
            django_user_id=1,
            group_ids=[10, 20],
            emittente_fiscale_id=3,
        )

    # Scopo: Verifica che un superuser riceva comunque l'emittente_fiscale_id
    #        reale nella lista settings (fallback da get_emittente_fiscale_id_for_user),
    #        altrimenti il LEFT JOIN su emittente_fiscale_id = NULL non matcha
    #        mai e gli override emittente non vengono mostrati.
    @patch(SVC_PATH)
    def test_list_settings_superuser_resolves_emittente(self, mock_svc_cls):
        from apps.core.api.views_parameters import ParameterSettingsView

        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.get_emittente_fiscale_id_for_user.return_value = 7
        mock_svc.list_parameters_for_user.return_value = []

        view = ParameterSettingsView()
        request = _make_request(user_id=1, is_superuser=True)
        response = view.get(request)

        self.assertEqual(response.status_code, 200)
        # Superuser: _get_user_context restituisce emittente_fiscale_id=None,
        # ma il fallback in ParameterSettingsView deve risolvere il valore reale.
        mock_svc.list_parameters_for_user.assert_called_once_with(
            django_user_id=1,
            group_ids=None,
            emittente_fiscale_id=7,
        )


class ParameterOverrideViewTests(TestCase):

    # Scopo: Verifica che POST override crei/aggiorni l'override personale.
    @patch(SVC_PATH)
    def test_upsert_override_success(self, mock_svc_cls):
        from apps.core.api.views_parameters import ParameterOverrideView

        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.upsert_user_override.return_value = 99

        view = ParameterOverrideView()
        request = _make_request(
            user_id=5,
            data={"parameter_code": "DEFAULT_IVA_ID", "value": "10"},
        )
        response = view.post(request)

        self.assertEqual(response.status_code, 200)
        import json
        body = json.loads(response.content)
        self.assertEqual(body["data"]["override_id"], 99)
        mock_svc.upsert_user_override.assert_called_once_with(
            parameter_code="DEFAULT_IVA_ID",
            django_user_id=5,
            value="10",
        )


class ParameterOverrideDeleteViewTests(TestCase):

    # Scopo: Verifica che DELETE override rimuova l'override.
    @patch(SVC_PATH)
    def test_delete_override_success(self, mock_svc_cls):
        from apps.core.api.views_parameters import ParameterOverrideDeleteView

        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.delete_user_override.return_value = True

        view = ParameterOverrideDeleteView()
        request = _make_request(user_id=5)
        response = view.delete(request, override_id=42)

        self.assertEqual(response.status_code, 200)
        mock_svc.delete_user_override.assert_called_once_with(
            override_id=42,
            django_user_id=5,
        )

    # Scopo: Verifica che DELETE override non trovato lanci errore.
    @patch(SVC_PATH)
    def test_delete_override_not_found(self, mock_svc_cls):
        from apps.core.api.views_parameters import ParameterOverrideDeleteView

        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.delete_user_override.side_effect = ServiceError(
            code="E_PARAMETER_NOT_FOUND",
            message="Override non trovato.",
        )

        view = ParameterOverrideDeleteView()
        request = _make_request(user_id=5)
        with self.assertRaises(ServiceError) as ctx:
            view.delete(request, override_id=999)
        self.assertEqual(ctx.exception.code, "E_PARAMETER_NOT_FOUND")
