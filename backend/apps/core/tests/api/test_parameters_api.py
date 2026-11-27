# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
 3b) ParameterDefaultsViewTests.test_get_defaults_superuser_resolves_identita
 4) ParameterSettingsViewTests.test_list_settings_success
 5) ParameterSettingsViewTests.test_list_settings_superuser_resolves_identita
 6) ParameterOverrideViewTests.test_upsert_override_success
 7) ParameterOverrideDeleteViewTests.test_delete_override_success
 8) ParameterOverrideDeleteViewTests.test_delete_override_not_found
 9) ParameterSettingsViewTests.test_list_settings_ba_non_risulta_404 — BA inesistente o fuori scope → E_BILLING_ACCOUNT_NOT_FOUND (F-6)
10) ParameterSettingsViewTests.test_list_settings_ba_zero_400 — billing_account_id <= 0 → ValueError (400 E_VALIDATION_INPUT)
11) ParameterOverrideEmittenteTests — override per emittente sull'emittente scelto; in «tutti» 400 E_EMITTENTE_NON_RISOLTO (POST e DELETE); defaults in «tutti» senza livello emittente (E1-1)
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.service_errors import ServiceError

SVC_PATH = "apps.core.api.views_parameters.ParameterService"


# Scopo: l'emittente di chi agisce, finto per tutti i test del file. Lo leggono
#        `get_user_context` (letture) e il BB `emittente_per_scrivere` (override
#        per emittente), entrambi da `PermissionResolver.get_emittente_for_user`
#        (dal 2026-11-25: prima `ParameterService.get_emittente_fiscale_id_for_user`,
#        che ripiegava sul gestore globale). Default None = «tutti gli emittenti».
class _ConEmittenteDiChiAgisce(TestCase):

    def setUp(self) -> None:
        patcher = patch(
            "apps.core.services.permissions_resolver.PermissionResolver.get_emittente_for_user",
            return_value=None,
        )
        self.emittente = patcher.start()
        self.addCleanup(patcher.stop)


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


class ParameterDefaultsViewTests(_ConEmittenteDiChiAgisce):

    # Scopo: Verifica che GET defaults restituisca i valori risolti.
    @patch(SVC_PATH)
    def test_get_defaults_success(self, mock_svc_cls):
        from apps.core.api.views_parameters import ParameterDefaultsView

        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.get_defaults.return_value = {"DEFAULT_IVA_ID": "22"}
        self.emittente.return_value = 3

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
        self.emittente.return_value = 5

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

    # Scopo: Verifica che anche il superuser riceva l'identita' reale per la
    #        risoluzione delle cascade override (regressione bug 2026-05-03:
    #        gli override personali del superuser non venivano applicati).
    @patch(SVC_PATH)
    def test_get_defaults_superuser_resolves_identita(self, mock_svc_cls):
        from apps.core.api.views_parameters import ParameterDefaultsView

        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.get_defaults.return_value = {"DEFAULT_UTILITY": "BASE"}
        self.emittente.return_value = 9

        view = ParameterDefaultsView()
        request = _make_request(
            user_id=1, is_superuser=True, query_params={"codes": "DEFAULT_UTILITY"},
        )
        response = view.get(request)

        self.assertEqual(response.status_code, 200)
        mock_svc.get_defaults.assert_called_once_with(
            ["DEFAULT_UTILITY"],
            django_user_id=1,
            group_ids=[10, 20],
            emittente_fiscale_id=9,
        )


class ParameterSettingsViewTests(_ConEmittenteDiChiAgisce):

    # Scopo: Verifica che GET settings restituisca la lista parametri con livelli.
    @patch(SVC_PATH)
    def test_list_settings_success(self, mock_svc_cls):
        from apps.core.api.views_parameters import ParameterSettingsView

        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        self.emittente.return_value = 3
        mock_svc.list_parameters_for_user.return_value = ([
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
        ], 1)

        view = ParameterSettingsView()
        request = _make_request(user_id=1)
        response = view.get(request)

        self.assertEqual(response.status_code, 200)
        import json
        body = json.loads(response.content)
        # La pagina della lista `config.parametri_impostazioni` (dal 2026-10-31).
        self.assertEqual(body["data"]["count"], 1)
        self.assertEqual(body["data"]["results"][0]["code"], "DEFAULT_IVA_ID")
        self.assertEqual(body["data"]["results"][0]["resolved_value"], "5")
        mock_svc.list_parameters_for_user.assert_called_once_with(
            django_user_id=1,
            group_ids=[10, 20],
            emittente_fiscale_id=3,
            categoria_cliente_id=None,
            search=None, order_by="code", order_dir=None, limit=25, offset=0,
        )

    # Scopo: Verifica che un superuser riceva l'identita' reale (user_id,
    #        groups, emittente) nella lista settings. Post-fix 2026-05-03:
    #        get_user_context non bypassa piu' il superuser — la cascade
    #        override (user → group → emittente → default) e' identity-based,
    #        non un filtro di scope. Anche il superuser deve poter avere
    #        override personali risolti correttamente.
    @patch(SVC_PATH)
    def test_list_settings_superuser_resolves_identita(self, mock_svc_cls):
        from apps.core.api.views_parameters import ParameterSettingsView

        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        self.emittente.return_value = 7
        mock_svc.list_parameters_for_user.return_value = ([], 0)

        view = ParameterSettingsView()
        request = _make_request(user_id=1, is_superuser=True)
        response = view.get(request)

        self.assertEqual(response.status_code, 200)
        mock_svc.list_parameters_for_user.assert_called_once_with(
            django_user_id=1,
            group_ids=[10, 20],
            emittente_fiscale_id=7,
            categoria_cliente_id=None,
            search=None, order_by="code", order_dir=None, limit=25, offset=0,
        )

    # Scopo: Verifica che il query param `categoria_cliente_id` venga propagato
    #        al service. Post brief DB 2026-05-19, migration 20260519-01.
    @patch(SVC_PATH)
    def test_list_settings_propaga_categoria_cliente_id_esplicito(self, mock_svc_cls):
        from apps.core.api.views_parameters import ParameterSettingsView

        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        self.emittente.return_value = 3
        mock_svc.list_parameters_for_user.return_value = ([], 0)

        view = ParameterSettingsView()
        request = _make_request(user_id=1, query_params={"categoria_cliente_id": "12"})
        response = view.get(request)

        self.assertEqual(response.status_code, 200)
        mock_svc.list_parameters_for_user.assert_called_once_with(
            django_user_id=1,
            group_ids=[10, 20],
            emittente_fiscale_id=3,
            categoria_cliente_id=12,
            search=None, order_by="code", order_dir=None, limit=25, offset=0,
        )

    # Scopo: Verifica derivazione automatica `categoria_cliente_id` da BA via
    #        BillingAccountRepository.get_categoria_cliente_id quando il query
    #        param esplicito non e' valorizzato.
    @patch("apps.anagrafiche.services.billing_account_service.BillingAccountRepository", autospec=True)
    @patch(SVC_PATH)
    def test_list_settings_deriva_categoria_da_ba(self, mock_svc_cls, mock_ba_repo_cls):
        from apps.core.api.views_parameters import ParameterSettingsView

        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        self.emittente.return_value = 3
        mock_svc.list_parameters_for_user.return_value = ([], 0)
        mock_ba_repo = MagicMock()
        mock_ba_repo_cls.return_value = mock_ba_repo
        mock_ba_repo.get_categoria_cliente_id.return_value = 42

        view = ParameterSettingsView()
        request = _make_request(user_id=1, query_params={"billing_account_id": "777"})
        response = view.get(request)

        self.assertEqual(response.status_code, 200)
        mock_ba_repo.get_categoria_cliente_id.assert_called_once_with(777)
        mock_svc.list_parameters_for_user.assert_called_once_with(
            django_user_id=1,
            group_ids=[10, 20],
            emittente_fiscale_id=3,
            categoria_cliente_id=42,
            search=None, order_by="code", order_dir=None, limit=25, offset=0,
        )

    # Scopo: F-6 — BA che non risulta (inesistente, o fuori scope: la RLS di
    #        anagrafiche.billing_account non lo restituisce) → 404
    #        E_BILLING_ACCOUNT_NOT_FOUND. Prima la categoria restava NULL in silenzio.
    @patch("apps.anagrafiche.services.billing_account_service.BillingAccountRepository", autospec=True)
    @patch(SVC_PATH)
    def test_list_settings_ba_non_risulta_404(self, mock_svc_cls, mock_ba_repo_cls):
        from apps.core.api.views_parameters import ParameterSettingsView

        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        self.emittente.return_value = 3
        mock_ba_repo_cls.return_value.get_categoria_cliente_id.return_value = None

        view = ParameterSettingsView()
        request = _make_request(user_id=1, query_params={"billing_account_id": "777"})
        with self.assertRaises(ServiceError) as ctx:
            view.get(request)
        self.assertEqual(ctx.exception.code, "E_BILLING_ACCOUNT_NOT_FOUND")
        mock_svc.list_parameters_for_user.assert_not_called()

    # Scopo: billing_account_id <= 0 → ValueError (400 E_VALIDATION_INPUT),
    #        senza interrogare il BA.
    @patch("apps.anagrafiche.services.billing_account_service.BillingAccountRepository", autospec=True)
    @patch(SVC_PATH)
    def test_list_settings_ba_zero_400(self, mock_svc_cls, mock_ba_repo_cls):
        from apps.core.api.views_parameters import ParameterSettingsView

        self.emittente.return_value = 3

        view = ParameterSettingsView()
        request = _make_request(user_id=1, query_params={"billing_account_id": "0"})
        with self.assertRaises(ValueError):
            view.get(request)
        mock_ba_repo_cls.return_value.get_categoria_cliente_id.assert_not_called()

    # Scopo: Fail-fast su categoria_cliente_id non numerico o <= 0. Evita di
    #        passare valori non-positivi silenziosamente al DB (LEFT JOIN
    #        no-match, UX rumorosa). ValueError → 400 E_VALIDATION_INPUT, lo
    #        stesso codice di `billing_account_id` (query string = dato di input).
    @patch(SVC_PATH)
    def test_list_settings_categoria_zero_solleva_validation(self, mock_svc_cls):
        from apps.core.api.views_parameters import ParameterSettingsView

        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        self.emittente.return_value = 3

        view = ParameterSettingsView()
        for raw in ("0", "-2", "abc"):
            with self.subTest(raw=raw):
                request = _make_request(user_id=1, query_params={"categoria_cliente_id": raw})
                with self.assertRaises(ValueError):
                    view.get(request)
        mock_svc.list_parameters_for_user.assert_not_called()

    # Scopo: Priorita' esplicito > derivato quando entrambi presenti.
    @patch("apps.anagrafiche.services.billing_account_service.BillingAccountRepository", autospec=True)
    @patch(SVC_PATH)
    def test_list_settings_categoria_esplicito_batte_ba(
        self, mock_svc_cls, mock_ba_repo_cls,
    ):
        from apps.core.api.views_parameters import ParameterSettingsView

        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        self.emittente.return_value = 3
        mock_svc.list_parameters_for_user.return_value = ([], 0)
        mock_ba_repo = MagicMock()
        mock_ba_repo_cls.return_value = mock_ba_repo

        view = ParameterSettingsView()
        request = _make_request(user_id=1, query_params={
            "categoria_cliente_id": "12",
            "billing_account_id": "777",
        })
        view.get(request)

        # BA NON viene interrogato perche' categoria esplicita ha priorita'.
        mock_ba_repo.get_categoria_cliente_id.assert_not_called()
        mock_svc.list_parameters_for_user.assert_called_once_with(
            django_user_id=1,
            group_ids=[10, 20],
            emittente_fiscale_id=3,
            categoria_cliente_id=12,
            search=None, order_by="code", order_dir=None, limit=25, offset=0,
        )


class ParameterOverrideViewTests(_ConEmittenteDiChiAgisce):

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

    # Scopo: ⛔ Un override senza `value` (assente o null) e' un 400 sul campo,
    #        non un override vuoto scritto con un 200 (2026-10-21, §B6 del
    #        brief-be-verifica-documentazione-api). `""` esplicito resta un valore.
    @patch(SVC_PATH)
    def test_override_senza_value_400(self, mock_svc_cls):
        import json

        from apps.core.api.views_parameters import ParameterOverrideView

        for corpo in (
            {"parameter_code": "DEFAULT_IVA_ID"},
            {"parameter_code": "DEFAULT_IVA_ID", "value": None},
            # Il valore e' testo: un booleano o un oggetto JSON non si «stringano».
            {"parameter_code": "DEFAULT_IVA_ID", "value": True},
            {"parameter_code": "DEFAULT_IVA_ID", "value": {"a": 1}},
            # Un codice non stringa era un 500 (`.strip()` nel service).
            {"parameter_code": 5, "value": "10"},
        ):
            with self.subTest(corpo=corpo):
                response = ParameterOverrideView().post(_make_request(user_id=5, data=corpo))
                self.assertEqual(response.status_code, 400)
                body = json.loads(response.content)
                self.assertEqual(body["error"]["code"], "E_PARAMETER_VALIDATION")
        mock_svc_cls.return_value.upsert_user_override.assert_not_called()
        ParameterOverrideView().post(
            _make_request(user_id=5, data={"parameter_code": "DEFAULT_IVA_ID", "value": ""}),
        )
        mock_svc_cls.return_value.upsert_user_override.assert_called_once()


class ParameterOverrideDeleteViewTests(_ConEmittenteDiChiAgisce):

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


class ParameterOverrideCategoriaClienteTests(_ConEmittenteDiChiAgisce):
    """Phase B 2026-05-19: CRUD override scope categoria_cliente (admin-only)."""

    # Scopo: POST override scope=categoria_cliente crea override per la categoria.
    @patch("apps.core.api.views_parameters._is_admin", return_value=True)
    @patch(SVC_PATH)
    def test_upsert_categoria_cliente_admin_ok(self, mock_svc_cls, _is_admin):
        from apps.core.api.views_parameters import ParameterOverrideView

        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.upsert_categoria_cliente_override.return_value = 314

        view = ParameterOverrideView()
        request = _make_request(
            user_id=5,
            data={
                "parameter_code": "VENDITE_MAX_SCONTO_PCT",
                "value": "5",
                "scope": "categoria_cliente",
                "categoria_cliente_id": 12,
            },
        )
        response = view.post(request)
        self.assertEqual(response.status_code, 200)
        import json
        body = json.loads(response.content)
        self.assertEqual(body["data"]["override_id"], 314)
        self.assertEqual(body["data"]["scope"], "categoria_cliente")
        mock_svc.upsert_categoria_cliente_override.assert_called_once_with(
            parameter_code="VENDITE_MAX_SCONTO_PCT",
            categoria_cliente_id=12,
            value="5",
        )

    # Scopo: POST scope=categoria_cliente da non-admin → 403.
    #        Nota: i POST passano da handle_post_json che cattura ServiceError
    #        e le converte in JsonResponse error envelope; quindi qui si
    #        assercia sul body, non con assertRaises.
    @patch("apps.core.api.views_parameters._is_admin", return_value=False)
    @patch(SVC_PATH)
    def test_upsert_categoria_cliente_non_admin_denied(
        self, mock_svc_cls, _is_admin,
    ):
        from apps.core.api.views_parameters import ParameterOverrideView

        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc

        view = ParameterOverrideView()
        request = _make_request(
            user_id=5,
            data={
                "parameter_code": "X", "value": "y",
                "scope": "categoria_cliente", "categoria_cliente_id": 12,
            },
        )
        response = view.post(request)
        import json
        body = json.loads(response.content)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(body["error"]["code"], "E_PERMISSION_DENIED")
        mock_svc.upsert_categoria_cliente_override.assert_not_called()

    # Scopo: POST scope=categoria_cliente senza id → 400 parlante (no silent).
    @patch("apps.core.api.views_parameters._is_admin", return_value=True)
    @patch(SVC_PATH)
    def test_upsert_categoria_cliente_id_mancante(self, mock_svc_cls, _is_admin):
        from apps.core.api.views_parameters import ParameterOverrideView

        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc

        view = ParameterOverrideView()
        request = _make_request(
            user_id=5,
            data={"parameter_code": "X", "value": "y", "scope": "categoria_cliente"},
        )
        response = view.post(request)
        import json
        body = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(body["error"]["code"], "E_PARAMETER_VALIDATION")
        mock_svc.upsert_categoria_cliente_override.assert_not_called()

    # Scopo: DELETE scope=categoria_cliente con id query param OK.
    @patch("apps.core.api.views_parameters._is_admin", return_value=True)
    @patch(SVC_PATH)
    def test_delete_categoria_cliente_admin_ok(self, mock_svc_cls, _is_admin):
        from apps.core.api.views_parameters import ParameterOverrideDeleteView

        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc
        mock_svc.delete_categoria_cliente_override.return_value = True

        view = ParameterOverrideDeleteView()
        request = _make_request(
            user_id=5,
            query_params={"scope": "categoria_cliente", "categoria_cliente_id": "12"},
        )
        response = view.delete(request, override_id=314)
        self.assertEqual(response.status_code, 200)
        mock_svc.delete_categoria_cliente_override.assert_called_once_with(
            override_id=314,
            categoria_cliente_id=12,
        )

    # Scopo: DELETE scope=categoria_cliente senza id → 400 parlante.
    @patch("apps.core.api.views_parameters._is_admin", return_value=True)
    @patch(SVC_PATH)
    def test_delete_categoria_cliente_id_mancante(
        self, mock_svc_cls, _is_admin,
    ):
        from apps.core.api.views_parameters import ParameterOverrideDeleteView

        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc

        view = ParameterOverrideDeleteView()
        request = _make_request(
            user_id=5,
            query_params={"scope": "categoria_cliente"},
        )
        with self.assertRaises(ServiceError) as ctx:
            view.delete(request, override_id=314)
        self.assertEqual(ctx.exception.code, "E_PARAMETER_VALIDATION")

    # Scopo: DELETE scope=categoria_cliente con id malformato ('--5') → 400.
    #        Regression test post-fix regex stretto (no ValueError → 500).
    @patch("apps.core.api.views_parameters._is_admin", return_value=True)
    @patch(SVC_PATH)
    def test_delete_categoria_cliente_id_malformato(
        self, mock_svc_cls, _is_admin,
    ):
        from apps.core.api.views_parameters import ParameterOverrideDeleteView

        mock_svc = MagicMock()
        mock_svc_cls.return_value = mock_svc

        view = ParameterOverrideDeleteView()
        request = _make_request(
            user_id=5,
            query_params={"scope": "categoria_cliente", "categoria_cliente_id": "--5"},
        )
        with self.assertRaises(ServiceError) as ctx:
            view.delete(request, override_id=314)
        self.assertEqual(ctx.exception.code, "E_PARAMETER_VALIDATION")


class ParameterOverrideEmittenteTests(_ConEmittenteDiChiAgisce):
    """E1-1 di brief-be-fe-BB-audit (2026-11-25): l'override per emittente si
    scrive sull'emittente SCELTO, e in «tutti gli emittenti» si rifiuta. Fino a
    quel giorno finiva sempre sul gestore globale."""

    _CORPO = {"parameter_code": "VENDITE_MAX_SCONTO_PCT", "value": "20", "scope": "emittente"}

    # Scopo: con l'emittente 32 scelto, l'override si scrive su 32.
    @patch("apps.core.api.views_parameters._is_admin", return_value=True)
    @patch(SVC_PATH)
    def test_upsert_sull_emittente_scelto(self, mock_svc_cls, _is_admin):
        from apps.core.api.views_parameters import ParameterOverrideView

        self.emittente.return_value = 32
        mock_svc_cls.return_value.upsert_emittente_override.return_value = 7
        response = ParameterOverrideView().post(_make_request(user_id=1, data=self._CORPO))
        self.assertEqual(response.status_code, 200)
        mock_svc_cls.return_value.upsert_emittente_override.assert_called_once_with(
            parameter_code="VENDITE_MAX_SCONTO_PCT", emittente_fiscale_id=32, value="20",
        )

    # Scopo: in «tutti gli emittenti» 400 E_EMITTENTE_NON_RISOLTO, niente scritto.
    @patch("apps.core.api.views_parameters._is_admin", return_value=True)
    @patch(SVC_PATH)
    def test_upsert_in_tutti_gli_emittenti_rifiutato(self, mock_svc_cls, _is_admin):
        import json

        from apps.core.api.views_parameters import ParameterOverrideView

        response = ParameterOverrideView().post(_make_request(user_id=1, data=self._CORPO))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content)["error"]["code"], "E_EMITTENTE_NON_RISOLTO")
        mock_svc_cls.return_value.upsert_emittente_override.assert_not_called()

    # Scopo: la cancellazione segue la stessa regola: sull'emittente scelto...
    @patch("apps.core.api.views_parameters._is_admin", return_value=True)
    @patch(SVC_PATH)
    def test_delete_sull_emittente_scelto(self, mock_svc_cls, _is_admin):
        from apps.core.api.views_parameters import ParameterOverrideDeleteView

        self.emittente.return_value = 32
        response = ParameterOverrideDeleteView().delete(
            _make_request(user_id=1, query_params={"scope": "emittente"}), override_id=9,
        )
        self.assertEqual(response.status_code, 200)
        mock_svc_cls.return_value.delete_emittente_override.assert_called_once_with(
            override_id=9, emittente_fiscale_id=32,
        )

    # Scopo: ...e in «tutti gli emittenti» si rifiuta.
    @patch("apps.core.api.views_parameters._is_admin", return_value=True)
    @patch(SVC_PATH)
    def test_delete_in_tutti_gli_emittenti_rifiutato(self, mock_svc_cls, _is_admin):
        from apps.core.api.views_parameters import ParameterOverrideDeleteView

        with self.assertRaises(ServiceError) as ctx:
            ParameterOverrideDeleteView().delete(
                _make_request(user_id=1, query_params={"scope": "emittente"}), override_id=9,
            )
        self.assertEqual(ctx.exception.code, "E_EMITTENTE_NON_RISOLTO")
        mock_svc_cls.return_value.delete_emittente_override.assert_not_called()

    # Scopo: in lettura «tutti gli emittenti» salta il livello emittente (None),
    #        come la cascata dentro il DB — non il gestore globale.
    @patch(SVC_PATH)
    def test_defaults_in_tutti_gli_emittenti_senza_livello_emittente(self, mock_svc_cls):
        from apps.core.api.views_parameters import ParameterDefaultsView

        mock_svc_cls.return_value.get_defaults.return_value = {}
        ParameterDefaultsView().get(_make_request(user_id=1, query_params={"codes": "P1"}))
        self.assertIsNone(
            mock_svc_cls.return_value.get_defaults.call_args.kwargs["emittente_fiscale_id"],
        )
