# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit UiService (lettura schema `ui`). Mock repository +
#        PermissionResolver. CI senza DB reale (SimpleTestCase).
#
# Indice test (0..N):
#   0. get_lista_config_happy_path
#   1. get_lista_config_admin_globale_passa_emittente_none
#   2. get_lista_config_lista_inesistente_raises
#   3. get_lista_config_database_error_marker_riconosciuto
#   4. get_lista_config_database_error_fallback_generic
#   5. get_catalogo_happy_path_filtra_bloccate
#   6. get_catalogo_lista_inesistente_raises
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from django.db import DatabaseError
from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.ui.services.ui_service import (
    E_UI_GENERIC_FAILED,
    E_UI_LISTA_NON_TROVATA,
    UiService,
)


# Scopo: Costruisce un MagicMock user con id stabile.
def _make_user(user_id: int = 42) -> Any:
    user = MagicMock()
    user.id = user_id
    user.is_authenticated = True
    return user


class UiServiceGetListaConfigTests(SimpleTestCase):
    @patch(
        "apps.ui.services.ui_service.PermissionResolver.get_emittente_for_user",
        return_value=11,
    )
    def test_get_lista_config_happy_path(self, _mock_em) -> None:
        repo = MagicMock()
        repo.resolve_lista_config.return_value = {
            "colonne": [
                {"codice": "ragione_sociale", "ordine": 1, "visibile": True},
            ],
            "ordinamento": [],
            "filtri": {},
            "pagina_dimensione": 25,
            "colonne_nuove": 0,
        }
        svc = UiService(repository=repo)

        config = svc.get_lista_config(_make_user(), "anagrafiche.clienti")

        self.assertEqual(config["pagina_dimensione"], 25)
        repo.resolve_lista_config.assert_called_once_with(
            lista_codice="anagrafiche.clienti",
            auth_user_id=42,
            emittente_fiscale_id=11,
        )

    @patch(
        "apps.ui.services.ui_service.PermissionResolver.get_emittente_for_user",
        return_value=None,
    )
    def test_get_lista_config_admin_globale_passa_emittente_none(
        self, _mock_em
    ) -> None:
        repo = MagicMock()
        repo.resolve_lista_config.return_value = {
            "colonne": [], "ordinamento": [], "filtri": {},
            "pagina_dimensione": 25, "colonne_nuove": 0,
        }
        svc = UiService(repository=repo)

        svc.get_lista_config(_make_user(), "anagrafiche.clienti")

        # Admin globale -> emittente_fiscale_id=None propagato alla fn DB.
        repo.resolve_lista_config.assert_called_once_with(
            lista_codice="anagrafiche.clienti",
            auth_user_id=42,
            emittente_fiscale_id=None,
        )

    @patch(
        "apps.ui.services.ui_service.PermissionResolver.get_emittente_for_user",
        return_value=11,
    )
    def test_get_lista_config_lista_inesistente_raises(self, _mock_em) -> None:
        # Caso difensivo: la fn ritorna dict vuoto invece di raise.
        repo = MagicMock()
        repo.resolve_lista_config.return_value = {}
        svc = UiService(repository=repo)

        with self.assertRaises(ServiceError) as ctx:
            svc.get_lista_config(_make_user(), "non.esiste")
        self.assertEqual(ctx.exception.code, E_UI_LISTA_NON_TROVATA)

    @patch(
        "apps.ui.services.ui_service.PermissionResolver.get_emittente_for_user",
        return_value=11,
    )
    def test_get_lista_config_db_error_marker_riconosciuto(
        self, _mock_em
    ) -> None:
        repo = MagicMock()
        # MESSAGE che contiene il marker E_UI_LISTA_NON_TROVATA.
        repo.resolve_lista_config.side_effect = DatabaseError(
            "ERROR: E_UI_LISTA_NON_TROVATA: codice lista 'foo'"
        )
        svc = UiService(repository=repo)

        with self.assertRaises(ServiceError) as ctx:
            svc.get_lista_config(_make_user(), "foo")
        self.assertEqual(ctx.exception.code, E_UI_LISTA_NON_TROVATA)

    @patch(
        "apps.ui.services.ui_service.PermissionResolver.get_emittente_for_user",
        return_value=11,
    )
    def test_get_lista_config_db_error_fallback_generic(self, _mock_em) -> None:
        repo = MagicMock()
        repo.resolve_lista_config.side_effect = DatabaseError(
            "ERROR: connection lost"
        )
        svc = UiService(repository=repo)

        with self.assertRaises(ServiceError) as ctx:
            svc.get_lista_config(_make_user(), "anagrafiche.clienti")
        self.assertEqual(ctx.exception.code, E_UI_GENERIC_FAILED)


class UiServiceGetCatalogoTests(SimpleTestCase):
    @patch(
        "apps.ui.services.ui_service.PermissionResolver.get_emittente_for_user",
        return_value=11,
    )
    def test_get_catalogo_happy_path_filtra_bloccate(self, _mock_em) -> None:
        repo = MagicMock()
        # 'iban' simulata BLOCCATA: presente nel catalogo grezzo ma assente
        # dal risultato di resolve_lista_config (la fn DB la rimuove).
        repo.list_colonne_by_codice.return_value = [
            {"codice": "ragione_sociale", "tipo_colonna": "identificatore"},
            {"codice": "partita_iva", "tipo_colonna": "informazione"},
            {"codice": "iban", "tipo_colonna": "informazione"},
        ]
        repo.resolve_lista_config.return_value = {
            "colonne": [
                {"codice": "ragione_sociale"},
                {"codice": "partita_iva"},
                # iban filtrata via permessi (non presente)
            ],
            "ordinamento": [], "filtri": {}, "pagina_dimensione": 25,
            "colonne_nuove": 0,
        }
        svc = UiService(repository=repo)

        result = svc.get_catalogo(_make_user(), "anagrafiche.clienti")

        codici = {c["codice"] for c in result["colonne"]}
        self.assertEqual(codici, {"ragione_sociale", "partita_iva"})
        self.assertNotIn("iban", codici)

    @patch(
        "apps.ui.services.ui_service.PermissionResolver.get_emittente_for_user",
        return_value=11,
    )
    def test_get_catalogo_lista_inesistente_raises(self, _mock_em) -> None:
        repo = MagicMock()
        # La fn DB ritorna dict vuoto per lista inesistente -> get_lista_config
        # solleva E_UI_LISTA_NON_TROVATA. Il catalogo non viene mai chiesto.
        repo.resolve_lista_config.return_value = {}
        svc = UiService(repository=repo)

        with self.assertRaises(ServiceError) as ctx:
            svc.get_catalogo(_make_user(), "non.esiste")
        self.assertEqual(ctx.exception.code, E_UI_LISTA_NON_TROVATA)
        repo.list_colonne_by_codice.assert_not_called()
