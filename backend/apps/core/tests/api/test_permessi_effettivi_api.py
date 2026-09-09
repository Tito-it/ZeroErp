# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari ApiPermessiEffettivi — endpoint permessi risolti con livello oggetto.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_aree_includono_modelli              — risposta contiene chiave `modelli` per ogni area
 2) test_modelli_con_livello_oggetto         — livello oggetto risolto per model registrati
 3) test_modelli_vuoti_se_nessun_override    — `modelli` lista vuota se area non ha model
 4) test_admin_puo_vedere_altro_utente       — ADMIN puo' interrogare altri user_id
 5) test_operativo_negato_altro_utente       — OPERATIVO non puo' vedere altri user_id
 6) test_utente_non_trovato                  — 404-equivalente se user_id inesistente
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch



def _mock_request(user_id: int = 1, is_superuser: bool = False) -> MagicMock:
    """Scopo: Crea un mock DRF request per i test permessi effettivi."""
    request = MagicMock()
    user = MagicMock()
    user.id = user_id
    user.is_superuser = is_superuser
    user.is_authenticated = True
    request.user = user
    return request


def _make_area(codice: str, schema_db: str, descrizione: str) -> MagicMock:
    """Scopo: Crea un mock AreaFunzionale con i campi minimi usati dalla view."""
    area = MagicMock()
    area.codice = codice
    area.schema_db = schema_db
    area.descrizione = descrizione
    return area


class ApiPermessiEffettiviViewTests(TestCase):
    """Test per ApiPermessiEffettivi con verifica campo `modelli` (3.1 v2)."""

    def _base_resolver_mock(self, mock_resolver, is_super: bool = False) -> None:
        """Scopo: Configura i valori di default del resolver per i test base."""
        mock_resolver.is_super_admin.return_value = is_super
        mock_resolver.get_ruolo_applicativo.return_value = "OPERATORE"
        mock_resolver.get_unita_organizzativa_id.return_value = None
        mock_resolver.get_emittenti_ids.return_value = None
        mock_resolver.get_livello_area.return_value = "TUTTO"
        mock_resolver.has_profilo_applicabile_per_area.return_value = True
        mock_resolver.get_livello_oggetto.return_value = "TUTTO"
        mock_resolver.list_model_overrides_grouped.return_value = {}

    # Scopo: La risposta include chiave `modelli` per ogni area — anche vuota.
    @patch("apps.core.api.views.PermissionResolver")
    @patch("apps.core.api.views.get_user_model")
    @patch("apps.config.models.AreaFunzionale")
    def test_aree_includono_modelli(self, mock_area_cls, mock_get_user, mock_resolver):
        from apps.core.api.views import ApiPermessiEffettivi

        self._base_resolver_mock(mock_resolver)
        area = _make_area("ANA", "anagrafiche", "Anagrafiche")
        mock_area_cls.objects.filter.return_value = [area]

        target = MagicMock()
        target.id = 5
        target.get_username.return_value = "mario"
        mock_get_user.return_value.objects.get.return_value = target

        request = _mock_request(user_id=5)
        view = ApiPermessiEffettivi()
        response = view.get(request, user_id=5)

        self.assertEqual(response.status_code, 200)
        import json
        body = json.loads(response.content)
        aree = body["data"]["aree"]
        self.assertEqual(len(aree), 1)
        self.assertIn("modelli", aree[0])
        self.assertEqual(aree[0]["modelli"], [])

    # Scopo: I model registrati nell'area appaiono in `modelli` con il livello risolto.
    @patch("apps.core.api.views.PermissionResolver")
    @patch("apps.core.api.views.get_user_model")
    @patch("apps.config.models.AreaFunzionale")
    def test_modelli_con_livello_oggetto(self, mock_area_cls, mock_get_user, mock_resolver):
        from apps.core.api.views import ApiPermessiEffettivi

        self._base_resolver_mock(mock_resolver)
        mock_resolver.list_model_overrides_grouped.return_value = {
            "anagrafiche": [
                {"app_label": "anagrafiche", "model_name": "conto_bancario"},
                {"app_label": "anagrafiche", "model_name": "soggetto"},
            ]
        }
        mock_resolver.get_livello_oggetto.side_effect = lambda u, app, model, area, cache=None: (
            "BLOCCATO" if model == "conto_bancario" else "TUTTO"
        )

        area = _make_area("ANA", "anagrafiche", "Anagrafiche")
        mock_area_cls.objects.filter.return_value = [area]

        target = MagicMock()
        target.id = 5
        target.get_username.return_value = "mario"
        mock_get_user.return_value.objects.get.return_value = target

        request = _mock_request(user_id=5)
        view = ApiPermessiEffettivi()
        response = view.get(request, user_id=5)

        import json
        body = json.loads(response.content)
        modelli = body["data"]["aree"][0]["modelli"]
        self.assertEqual(len(modelli), 2)
        cb = next(m for m in modelli if m["model_name"] == "conto_bancario")
        sg = next(m for m in modelli if m["model_name"] == "soggetto")
        self.assertEqual(cb["livello"], "BLOCCATO")
        self.assertEqual(sg["livello"], "TUTTO")

    # Scopo: Area senza model registrati → `modelli` lista vuota.
    @patch("apps.core.api.views.PermissionResolver")
    @patch("apps.core.api.views.get_user_model")
    @patch("apps.config.models.AreaFunzionale")
    def test_modelli_vuoti_se_nessun_override(self, mock_area_cls, mock_get_user, mock_resolver):
        from apps.core.api.views import ApiPermessiEffettivi

        self._base_resolver_mock(mock_resolver)
        # Nessun model per "vendite"
        mock_resolver.list_model_overrides_grouped.return_value = {}

        area = _make_area("VEN", "vendite", "Vendite")
        mock_area_cls.objects.filter.return_value = [area]

        target = MagicMock()
        target.id = 5
        target.get_username.return_value = "luigi"
        mock_get_user.return_value.objects.get.return_value = target

        request = _mock_request(user_id=5)
        view = ApiPermessiEffettivi()
        response = view.get(request, user_id=5)

        import json
        body = json.loads(response.content)
        self.assertEqual(body["data"]["aree"][0]["modelli"], [])

    # Scopo: ADMIN puo' interrogare permessi di un altro utente.
    @patch("apps.core.api.views.PermissionResolver")
    @patch("apps.core.api.views.get_user_model")
    @patch("apps.config.models.AreaFunzionale")
    def test_admin_puo_vedere_altro_utente(self, mock_area_cls, mock_get_user, mock_resolver):
        from apps.core.api.views import ApiPermessiEffettivi

        self._base_resolver_mock(mock_resolver, is_super=True)
        mock_area_cls.objects.filter.return_value = []

        target = MagicMock()
        target.id = 99
        target.get_username.return_value = "altro"
        mock_get_user.return_value.objects.get.return_value = target

        request = _mock_request(user_id=1)
        view = ApiPermessiEffettivi()
        response = view.get(request, user_id=99)

        self.assertEqual(response.status_code, 200)

    # Scopo: OPERATIVO non puo' vedere i permessi di altri utenti.
    @patch("apps.core.api.views.PermissionResolver")
    def test_operativo_negato_altro_utente(self, mock_resolver):
        from apps.core.api.views import ApiPermessiEffettivi
        from apps.core.services.service_errors import ServiceError

        mock_resolver.is_super_admin.return_value = False

        request = _mock_request(user_id=5)
        view = ApiPermessiEffettivi()

        with self.assertRaises(ServiceError) as ctx:
            view.get(request, user_id=99)

        self.assertEqual(ctx.exception.code, "E_PERMESSO_NEGATO")

    # Scopo: user_id inesistente solleva ServiceError.
    @patch("apps.core.api.views.PermissionResolver")
    @patch("apps.core.api.views.get_user_model")
    def test_utente_non_trovato(self, mock_get_user, mock_resolver):
        from apps.core.api.views import ApiPermessiEffettivi
        from apps.core.services.service_errors import ServiceError

        mock_resolver.is_super_admin.return_value = True
        # Serve una vera classe Exception affinche' `except User.DoesNotExist` funzioni.
        DoesNotExist = type("DoesNotExist", (Exception,), {})
        User = MagicMock()
        User.DoesNotExist = DoesNotExist
        User.objects.get.side_effect = DoesNotExist
        mock_get_user.return_value = User

        request = _mock_request(user_id=1)
        view = ApiPermessiEffettivi()

        with self.assertRaises(ServiceError) as ctx:
            view.get(request, user_id=9999)

        self.assertEqual(ctx.exception.code, "E_CORE_VALIDATION")
