# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Una direzione di ordinamento ESTRANEA su una lista e' un 400, non un
#        500 e non una lista ordinata ASC (decisione Tid 2026-09-26).
#
#        Prima `sql_order_direction` trasformava in ASC, in silenzio, qualunque
#        `order_dir` non riconosciuto: `?order_dir=giu` rispondeva 200 con la
#        lista al contrario. Ora il BB solleva `ValueError("order_dir_invalid")`,
#        e questo modulo prova che la richiesta arriva al client come 400 sui
#        DUE percorsi che il censimento ha trovato:
#
#        A. nessun service valida la direzione: il `ValueError` del BB sale ad
#           `ApiExceptionMiddleware` -> 400 `E_VALIDATION_INPUT`, lo stesso di
#           `?page=abc`. Rappresentante: `/anagrafiche/comuni/`.
#        B. il service valida con `PayloadValidator.validate_order_by`, che dal
#           2026-09-26 guarda anche la direzione: 400 col codice di DOMINIO,
#           prima di arrivare al repository. Rappresentante:
#           `/anagrafiche/categorie-clienti/`.
#
#        ⛔ In entrambi i casi il database NON si tocca: il cursor e' un mock che
#        fallirebbe il test se venisse aperto (su A il BB solleva prima della
#        query; su B il service prima del repository).
# ------------------------------------------------------------
"""
Indice test eseguiti:
 1) test_comuni_order_dir_estranea_e_400_generico     — percorso A
 2) test_comuni_order_dir_assente_prende_il_default   — percorso A, `?order_dir=` vuoto
 3) test_categorie_order_dir_estranea_e_400_di_dominio — percorso B
 4) test_documenti_order_dir_estranea_e_400_generico  — copia a mano portata al BB
 5) test_lookup_order_dir_maiuscola_ammessa           — `list_helpers.validate_order_params`
 6) test_lookup_order_dir_estranea_e_400_di_dominio   — idem
 7) ParseListParamsOrderDirTests.test_assente_e_none          — il bundle non inventa "asc"
 8) ParseListParamsOrderDirTests.test_indicata_passa_ripulita — la valida chi ordina
"""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

from django.core.cache import cache
from django.http import QueryDict
from django.test import Client, SimpleTestCase

from apps.core.api.payload_validators import parse_list_params

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_PERM_DOMINIO = "apps.core.api.permissions.ZeroERPPermission.has_permission"
_PERM_ADMIN = "apps.core.api.permissions.IsAdminZeroERP.has_permission"
# ⚠️ La connessione delle liste geografiche e' quella del BB: dal 2026-09-27
#    `GeoRepository` legge con `fetch_paged_with_total` (`_helpers`), e un
#    patch sul modulo del repository non vedrebbe la query.
_CONN_GEO = "apps.core.db._helpers.connection"
_CONN_CATEGORIE = "apps.anagrafiche.db.categorie_clienti_repository.connection"
_CONN_DOCUMENTI = "apps.documenti.db.documenti_repository.connection"
_SCOPE_DOCUMENTI = "apps.documenti.services.template_service.TemplateService._resolve_emittente_scope"
_LOOKUP_REPO = "apps.core.services.lookup_service.DbopsRepository"


class TestOrderDirEstraneaApi(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        self.client = Client(raise_request_exception=False)
        # La cache del throttle e' condivisa dalla suite: senza, un budget
        # consumato altrove risponderebbe 429 invece del codice atteso.
        cache.clear()

    # 1. Percorso A: nessuna validazione a monte, il 400 lo da' la catena
    #    BB -> middleware. Prima era 200 con la lista in ASC.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM_DOMINIO, return_value=True)
    @patch(_CONN_GEO)
    def test_comuni_order_dir_estranea_e_400_generico(self, mock_conn, _perm, _auth):
        resp = self.client.get("/api/v1/anagrafiche/comuni/?order_by=descrizione&order_dir=giu")
        self.assertEqual(resp.status_code, 400, resp.content)
        errore = resp.json()["error"]
        self.assertEqual(errore["code"], "E_VALIDATION_INPUT")
        self.assertEqual(errore["message"], "order_dir_invalid")
        mock_conn.cursor.assert_not_called()

    # 2. L'assenza resta ammessa: `?order_dir=` vuoto prende il default.
    # ⚠️ Prova che l'assenza NON e' un 400, non QUALE default si applica: il
    #    default dei comuni e' ASC, uguale al vecchio ripiego di
    #    `parse_list_params`. Che l'assenza arrivi come `None` lo provano i
    #    test 7-8; che `None` + `default_desc` dia DESC, `test_sql_order_helpers`.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM_DOMINIO, return_value=True)
    @patch(_CONN_GEO)
    def test_comuni_order_dir_assente_prende_il_default(self, mock_conn, _perm, _auth):
        cursor = MagicMock()
        cursor.description = []
        cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        resp = self.client.get("/api/v1/anagrafiche/comuni/?order_dir=")
        self.assertEqual(resp.status_code, 200, resp.content)
        sql = cursor.execute.call_args[0][0]
        self.assertIn("ORDER BY descrizione ASC NULLS FIRST, id ASC", sql)

    # 3. Percorso B: il service valida colonna E direzione, e il 400 porta il
    #    codice del dominio. Il repository non viene raggiunto.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM_ADMIN, return_value=True)
    @patch(_CONN_CATEGORIE)
    def test_categorie_order_dir_estranea_e_400_di_dominio(self, mock_conn, _perm, _auth):
        resp = self.client.get(
            "/api/v1/anagrafiche/categorie-clienti/?order_by=codice&order_dir=giu"
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["error"]["code"], "E_ANAG_VALIDAZIONE")
        mock_conn.cursor.assert_not_called()

    # 4. La lista template aveva la direzione scritta a mano (`"DESC" if
    #    order_dir.lower() == "desc" else "ASC"`): `giu` diventava ASC con un
    #    200. Portata al BB, e' il 400 del percorso A.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SCOPE_DOCUMENTI, return_value=None)
    @patch(_CONN_DOCUMENTI)
    def test_documenti_order_dir_estranea_e_400_generico(self, mock_conn, _scope, _auth):
        resp = self.client.get("/api/v1/documenti/templates/?order_by=codice&order_dir=giu")
        self.assertEqual(resp.status_code, 400, resp.content)
        errore = resp.json()["error"]
        self.assertEqual(errore["code"], "E_VALIDATION_INPUT")
        self.assertEqual(errore["message"], "order_dir_invalid")
        mock_conn.cursor.assert_not_called()

    # 5. `list_helpers.validate_order_params` confrontava case-sensitive:
    #    `DESC` era un 400 sulla lookup e passava sulle liste. Ora e' ammesso
    #    ovunque, e al repository arriva la forma che l'SQL vuole.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_LOOKUP_REPO, autospec=True)
    def test_lookup_order_dir_maiuscola_ammessa(self, repo_cls, _auth):
        repo_cls.return_value.list_lookup_codici.return_value = ([], 0)
        resp = self.client.get("/api/v1/core/lookup/codici/?rel=config.stati_sdi&order_dir=DESC")
        self.assertEqual(resp.status_code, 200, resp.content)
        kwargs = repo_cls.return_value.list_lookup_codici.call_args.kwargs
        self.assertEqual(kwargs["order_dir"], "DESC")

    # 6. Un valore estraneo resta il 400 del dominio, prima del repository.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_LOOKUP_REPO, autospec=True)
    def test_lookup_order_dir_estranea_e_400_di_dominio(self, repo_cls, _auth):
        resp = self.client.get("/api/v1/core/lookup/codici/?rel=config.stati_sdi&order_dir=giu")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["error"]["code"], "E_CORE_VALIDATION")
        repo_cls.return_value.list_lookup_codici.assert_not_called()


# 7-8. Il contratto del bundle sulla direzione (2026-09-26). ⛔ Fino a quel
#      giorno l'assenza diventava "asc", e il default DESC dei repository
#      (`default_desc`, `colonne_desc`) non si accendeva mai sulle liste che
#      passano da qui: si aprivano al contrario, senza errore.
class ParseListParamsOrderDirTests(SimpleTestCase):

    def test_assente_e_none(self) -> None:
        for query in ("", "order_dir=", "order_dir=%20%20"):
            with self.subTest(query=query):
                self.assertIsNone(parse_list_params(QueryDict(query))["order_dir"])

    # Il bundle non valida: la direzione estranea la rifiuta chi ordina
    # (service o BB SQL, test 1-6), con la stessa regola `order_dir_ammessa`.
    def test_indicata_passa_ripulita(self) -> None:
        self.assertEqual(parse_list_params(QueryDict("order_dir=%20desc%20"))["order_dir"], "desc")
        self.assertEqual(parse_list_params(QueryDict("order_dir=giu"))["order_dir"], "giu")
