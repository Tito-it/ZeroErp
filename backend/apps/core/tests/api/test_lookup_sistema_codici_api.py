# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: GET /core/lookup/sistema-codici/ — `schema` e `tabella` sono
#        obbligatori. Fino al 2026-10-14 un parametro assente valeva "" e la
#        risposta era «non configurato» (auto=false): il form avrebbe chiesto
#        il codice a mano per una tabella mai nominata (§6 di
#        analisi-be-difetti-emersi-verifica-doc-api-core).
#
# Indice test:
#   1. senza `schema` -> 400 E_VALIDATION_INPUT, il repository non e' chiamato
#   2. `tabella` vuota (solo spazi) -> 400, il messaggio nomina il parametro
#   3. tutti e due presenti, riga configurata -> 200 con auto e prefisso;
#      `colonna` assente vale `codice`
#   4. riga non configurata -> 200 auto=false
# ------------------------------------------------------------
from unittest.mock import Mock, patch

from django.test import Client

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_REPO = "apps.core.api.views_lookup.LookupRepository"
_URL = "/api/v1/core/lookup/sistema-codici/"
_SUPERUSER = (Mock(id=42, is_superuser=True, is_authenticated=True), None)


@patch(_AUTH, return_value=_SUPERUSER)
@patch(_REPO, autospec=True)
class LookupSistemaCodiciApiTests(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    # 1. Senza `schema`: 400, e nessuna lettura.
    def test_senza_schema_e_400(self, repo_cls, _auth) -> None:
        resp = self.client.get(_URL, {"tabella": "fornitori"})
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["error"]["code"], "E_VALIDATION_INPUT")
        repo_cls.return_value.get_sistema_codici.assert_not_called()

    # 2. `tabella` di soli spazi vale assente.
    def test_tabella_vuota_e_400(self, repo_cls, _auth) -> None:
        resp = self.client.get(_URL, {"schema": "anagrafiche", "tabella": "  "})
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("tabella", resp.json()["error"]["message"])
        repo_cls.return_value.get_sistema_codici.assert_not_called()

    # 3. Configurata: la forma, e `colonna` di default.
    def test_configurata(self, repo_cls, _auth) -> None:
        repo_cls.return_value.get_sistema_codici.return_value = {
            "usa_sequenza": True, "prefisso": "FRN", "separatore": "-", "lunghezza_numero": 6,
        }
        resp = self.client.get(_URL, {"schema": "anagrafiche", "tabella": "fornitori"})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(
            resp.json()["data"],
            {"auto": True, "prefisso": "FRN", "separatore": "-", "lunghezza_numero": 6},
        )
        repo_cls.return_value.get_sistema_codici.assert_called_once_with(
            "anagrafiche", "fornitori", "codice",
        )

    # 4. Non configurata: auto=false.
    def test_non_configurata(self, repo_cls, _auth) -> None:
        repo_cls.return_value.get_sistema_codici.return_value = None
        resp = self.client.get(_URL, {"schema": "anagrafiche", "tabella": "fornitori"})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["data"], {"auto": False})
