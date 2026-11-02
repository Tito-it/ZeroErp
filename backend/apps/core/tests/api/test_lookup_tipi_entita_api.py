# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: GET /core/lookup/tipi-entita/ — il vocabolario di `config.tipi_entita`
#        per i filtri che nominano «su quale cosa» (giornale trasversale).
#        Due meta': la PORTA e la FORMA con repository finto (senza DB), e una
#        lettura sul DB provvisto — il binding delle colonne per nome e che il
#        catalogo risponda i tipi vivi, il verso che i mock non vedono.
#
# Indice test:
#   1. senza JWT -> 401
#   2. envelope `{"data": {"results": [...]}}` — MAI la lista nuda
#      (api.md §L'ENVELOPE DI UN LOOKUP: `useGlobalLookup` legge
#      `r.data.data.results`, e su una lista nuda la pagina va bianca)
#   3. [DB vero] la lettura reale: le tre colonne per nome, `LOTTO` e `FATTURA`
#      presenti, l'`etichetta_key` nella radice `config.tipi_entita.`
# ------------------------------------------------------------
from unittest import TestCase
from unittest.mock import Mock, patch

from django.db import connection
from django.test import Client

from apps.core.db.lookup_repository import LookupRepository
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest
from apps.core.tests.db_e2e import richiedi_db_provvisto

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_REPO = "apps.core.api.views_lookup.LookupRepository"
_URL = "/api/v1/core/lookup/tipi-entita/"


class LookupTipiEntitaApiTests(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    # 1. Senza JWT -> 401.
    def test_richiede_jwt(self) -> None:
        self.assertEqual(self.client.get(_URL).status_code, 401)

    # 2. La forma: `{"results": [...]}`, non la lista nuda. (Superuser: il
    #    permesso salta la catena e non parla col DB — qui si prova la forma.)
    @patch(_AUTH, return_value=(Mock(id=42, is_superuser=True, is_authenticated=True), None))
    @patch(_REPO)
    def test_il_lookup_torna_l_envelope_results(self, repo_cls, _auth) -> None:
        repo_cls.return_value.list_tipi_entita.return_value = [
            {"codice": "LOTTO", "etichetta_key": "config.tipi_entita.lotto", "key_selector": "id"},
        ]
        resp = self.client.get(_URL)
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()["data"]
        self.assertIsInstance(data, dict)
        self.assertEqual(data["results"][0]["codice"], "LOTTO")
        repo_cls.return_value.list_tipi_entita.assert_called_once_with()


class LookupTipiEntitaDbTests(TestCase):
    # ⚠️ `unittest.TestCase` di proposito: questo test PARLA col DB provvisto
    #    (schema Liquibase completo), e `SimpleTestCase` glielo vieterebbe.
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # 3. La lettura reale: colonne per nome e catalogo vivo.
    def test_lettura_reale_del_catalogo(self) -> None:
        righe = LookupRepository().list_tipi_entita()
        codici = {r["codice"] for r in righe}
        self.assertTrue({"LOTTO", "FATTURA"} <= codici, codici)
        for r in righe:
            self.assertEqual(set(r), {"codice", "etichetta_key", "key_selector"})
            self.assertTrue(r["etichetta_key"].startswith("config.tipi_entita."), r)
        # Nessun obsoleto: lo stesso predicato del repository, letto a parte.
        with connection.cursor() as cur:
            cur.execute("SELECT count(*) FROM config.tipi_entita WHERE obsoleto_dal IS NULL")
            self.assertEqual(len(righe), cur.fetchone()[0])
