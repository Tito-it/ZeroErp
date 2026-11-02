# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: GET /amm-software/error-log/ (+ export/) — la consultazione di
#        `dbops.error_log` per i tecnici (pezzo E del piano BE/FE
#        dell'osservabilita', 2026-09-19). Repository mockato, nessun DB:
#        qui si presidia la PORTA, la normalizzazione dei filtri e che la
#        view passi al repository esattamente cio' che ha letto.
#
# Indice test:
#   1. senza JWT -> 401
#   2. la view e' una AdminAPIView, e nessuna delle due dichiara `lista_codice`
#      (il codice della lista e' la costante di modulo che legge l'export)
#   3. filtri normalizzati: date ISO, tx_id uuid, codice MAIUSCOLO, function_name
#      strip; `order_dir` GREZZO (None senza parametro, non 'asc')
#   4. `tx_id` non uuid -> 400 (mai un `%s::uuid` su una stringa qualunque)
#   5. `data_da` malformata -> 400
#   6. l'envelope e' quello paginato standard, `context` com'e'
# ------------------------------------------------------------
from unittest.mock import Mock, patch

from django.test import Client
from django.urls import resolve

from apps.amm_software.api.views import (
    _LISTA_CODICE_ERROR_LOG,
    ErrorLogExportView,
    ErrorLogListView,
)
from apps.core.api.base_views import AdminAPIView
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_REPO = "apps.core.services.tracciamento_service.DbopsRepository"
_URL = "/api/v1/amm-software/error-log/"
_TX = "123e4567-e89b-12d3-a456-426614174000"


# Scopo: un superuser: `AdminAPIView` lo fa passare da `is_superuser`.
def _mock_user() -> Mock:
    return Mock(id=9, username="op9", is_superuser=True, is_authenticated=True)


def _riga(**override) -> dict:
    base = {
        "id": 1, "occurred_at": "2026-09-19T10:00:00+02:00", "area": "vendite",
        "function_name": "fn_get_lotto", "codice": "E_PARAMETRO_INVALIDO",
        "classe": "DATO_ERRATO", "messaggio": "m", "causa": None, "soluzione": None,
        "tx_id": _TX, "context": {"parametro": "p_lotto_id", "valore": -1},
    }
    return {**base, **override}


class ErrorLogApiTests(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    # 1. Senza JWT -> 401.
    def test_richiede_jwt(self) -> None:
        self.assertEqual(self.client.get(_URL).status_code, 401)
        self.assertEqual(self.client.get(_URL + "export/?formato=csv").status_code, 401)

    # 2. La porta e' `AdminAPIView` (D-E1), le rotte portano alle due view, e
    #    il codice di lista che l'export legge e' UNO (costante di modulo).
    def test_porta_admin_e_rotte(self) -> None:
        self.assertTrue(issubclass(ErrorLogListView, AdminAPIView))
        self.assertTrue(issubclass(ErrorLogExportView, AdminAPIView))
        self.assertIs(resolve(_URL).func.view_class, ErrorLogListView)
        self.assertIs(resolve(_URL + "export/").func.view_class, ErrorLogExportView)
        self.assertEqual(_LISTA_CODICE_ERROR_LOG, "dbops.error_log")
        # ⛔ NON `lista_codice`, su nessuna delle due: su AdminAPIView il
        #    cancello di perimetro non esiste, e quell'attributo direbbe al
        #    presidio «coperta» su niente.
        self.assertIsNone(getattr(ErrorLogListView, "lista_codice", None))
        self.assertIsNone(getattr(ErrorLogExportView, "lista_codice", None))

    # 3. I filtri arrivano al repository normalizzati, e `order_dir` grezzo.
    @patch(_AUTH, return_value=(_mock_user(), None))
    @patch(_REPO)
    def test_filtri_normalizzati(self, repo_cls, _auth) -> None:
        repo_cls.return_value.list_error_logs.return_value = ([], 0)
        resp = self.client.get(_URL, {
            "area": " vendite ", "function_name": " fn_get_lotto ",
            "codice": "e_parametro_invalido", "tx_id": _TX,
            "data_da": "2026-09-01", "data_a": "2026-09-19",
            "limit": "10", "offset": "20", "order_by": "area",
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        repo_cls.return_value.list_error_logs.assert_called_once_with(
            area="vendite", function_name="fn_get_lotto",
            codice="E_PARAMETRO_INVALIDO", tx_id=_TX,
            data_da="2026-09-01", data_a="2026-09-19",
            limit=10, offset=20, order_by="area", order_dir=None,
        )
        # La pagina si deriva da offset/limit: la terza.
        self.assertEqual(resp.json()["data"]["page"], 3)

    # 4. `tx_id` che non e' un uuid -> 400, non un 500 dal cast SQL.
    @patch(_AUTH, return_value=(_mock_user(), None))
    @patch(_REPO)
    def test_tx_id_non_uuid_400(self, repo_cls, _auth) -> None:
        resp = self.client.get(_URL, {"tx_id": "non-un-uuid"})
        self.assertEqual(resp.status_code, 400, resp.content)
        repo_cls.return_value.list_error_logs.assert_not_called()

    # 5. Data malformata -> 400.
    @patch(_AUTH, return_value=(_mock_user(), None))
    @patch(_REPO)
    def test_data_malformata_400(self, repo_cls, _auth) -> None:
        resp = self.client.get(_URL, {"data_da": "19/09/2026"})
        self.assertEqual(resp.status_code, 400, resp.content)
        repo_cls.return_value.list_error_logs.assert_not_called()

    # 6. Envelope paginato standard; il `context` passa com'e'.
    @patch(_AUTH, return_value=(_mock_user(), None))
    @patch(_REPO)
    def test_envelope_e_context_intero(self, repo_cls, _auth) -> None:
        repo_cls.return_value.list_error_logs.return_value = ([_riga()], 1)
        resp = self.client.get(_URL)
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()["data"]
        self.assertEqual({"count", "page", "page_size", "total_pages", "results"}, set(data))
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["context"], {"parametro": "p_lotto_id", "valore": -1})
        self.assertEqual(data["results"][0]["classe"], "DATO_ERRATO")
