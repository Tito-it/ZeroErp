# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari endpoint API gestione code (tracciamento/code/*,
#        brief-be-fe-gestione-code-lavori-stampa FASE BE). Mock del service
#        (nessun DB): parsing query param, delega, envelope, idempotency.
#
# Indice test:
#   1) conteggi_200 — delega a conteggi_code con auth_user_id scope
#   2) coda_lavori_list_200 — parsing filtri (ambito/stato/tipo/limit)
#   3) coda_lavori_list_default_miei — tutti=False di default
#   4) coda_stampa_list_200 — lotto_id + parsing condiviso
#   5) coda_lavori_detail_200 — delega dettaglio_job
#   6) annulla_richiede_idempotency_key — 400 senza header
#   7) annulla_200 — delega annulla_job
#   8) requeue_200_extra_tentativi — payload propagato (default 3 se assente)
# ------------------------------------------------------------

import json
from datetime import date
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.test import Client, RequestFactory

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest


# Scopo: Crea una request GET con DRF wrapper per test di view unit-level.
def _make_get_request(path: str = "/", query_params: dict | None = None):
    from rest_framework.request import Request
    factory = RequestFactory()
    url = path
    if query_params:
        qs = "&".join(f"{k}={v}" for k, v in query_params.items())
        url = f"{path}?{qs}"
    django_request = factory.get(url)
    django_request.user = MagicMock(is_authenticated=True)
    return Request(django_request)


_VIEWS = "apps.core.api.views_tracciamento"


class TestApiCodeConteggi(TestCase):

    # 1. Delega al service con lo user della request + auth_user_id di scope.
    @patch(f"{_VIEWS}.get_scope_user_id", return_value=9)
    @patch(f"{_VIEWS}.gestione_service")
    def test_conteggi_200(self, mock_svc, _scope):
        from apps.core.api.views_tracciamento import ApiCodeConteggi

        mock_svc.conteggi_code.return_value = {
            "coda_lavori": {"pending": 1, "in_corso": 0},
            "coda_stampa": {"pending": 0, "in_corso": 0},
            "worker": {},
        }
        request = _make_get_request("/api/v1/core/tracciamento/code/conteggi/")
        response = ApiCodeConteggi().get(request)
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertEqual(body["data"]["coda_lavori"]["pending"], 1)
        mock_svc.conteggi_code.assert_called_once_with(
            request.user, auth_user_id=9,
        )


class TestApiCodaLavoriList(TestCase):

    # 2. Parsing filtri: ambito=tutti, stato upper, tipo upper, date, limit.
    @patch(f"{_VIEWS}.gestione_service")
    def test_coda_lavori_list_200(self, mock_svc):
        from apps.core.api.views_tracciamento import ApiCodaLavoriList

        mock_svc.elenca_coda_lavori.return_value = {"count": 0, "results": []}
        request = _make_get_request(
            "/api/v1/core/tracciamento/coda-lavori/",
            {
                "ambito": "tutti", "stato": "errore",
                "tipo": "fatturazione_giro", "data_da": "2026-07-01",
                "limit": "10", "offset": "20",
            },
        )
        response = ApiCodaLavoriList().get(request)
        self.assertEqual(response.status_code, 200)
        kwargs = mock_svc.elenca_coda_lavori.call_args.kwargs
        self.assertTrue(kwargs["tutti"])
        self.assertEqual(kwargs["stato"], "ERRORE")
        self.assertEqual(kwargs["job_type"], "FATTURAZIONE_GIRO")
        self.assertEqual(kwargs["data_da"], date(2026, 7, 1))
        self.assertEqual(kwargs["limit"], 10)
        self.assertEqual(kwargs["offset"], 20)

    # 3. Default: ambito assente → tutti=False (solo i propri).
    @patch(f"{_VIEWS}.gestione_service")
    def test_coda_lavori_list_default_miei(self, mock_svc):
        from apps.core.api.views_tracciamento import ApiCodaLavoriList

        mock_svc.elenca_coda_lavori.return_value = {"count": 0, "results": []}
        request = _make_get_request("/api/v1/core/tracciamento/coda-lavori/")
        ApiCodaLavoriList().get(request)
        self.assertFalse(mock_svc.elenca_coda_lavori.call_args.kwargs["tutti"])


class TestApiCodaStampaList(TestCase):

    # 4. Parsing condiviso + lotto_id. L'ambito per-operatore vive nel service
    #    (user_insert vs username del request.user): la view passa solo `user`.
    @patch(f"{_VIEWS}.gestione_service")
    def test_coda_stampa_list_200(self, mock_svc):
        from apps.core.api.views_tracciamento import ApiCodaStampaList

        mock_svc.elenca_coda_stampa.return_value = {"count": 0, "results": []}
        request = _make_get_request(
            "/api/v1/core/tracciamento/coda-stampa/",
            {"lotto_id": "117", "solo_vivi": "1"},
        )
        response = ApiCodaStampaList().get(request)
        self.assertEqual(response.status_code, 200)
        kwargs = mock_svc.elenca_coda_stampa.call_args.kwargs
        self.assertNotIn("auth_user_id", kwargs)
        self.assertEqual(kwargs["lotto_id"], 117)
        self.assertTrue(kwargs["solo_vivi"])


class TestApiCodaLavoriDetail(TestCase):

    # 5. Delega a dettaglio_job (ownership nel service).
    @patch(f"{_VIEWS}.gestione_service")
    def test_coda_lavori_detail_200(self, mock_svc):
        from apps.core.api.views_tracciamento import ApiCodaLavoriDetail

        mock_svc.dettaglio_job.return_value = {"id": 5, "stato": "FATTO"}
        request = _make_get_request("/api/v1/core/tracciamento/coda-lavori/5/")
        response = ApiCodaLavoriDetail().get(request, job_id=5)
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertEqual(body["data"]["id"], 5)
        mock_svc.dettaglio_job.assert_called_once_with(request.user, 5)


_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"


# Base SimpleTestCase (via JwtMockedApiTest): un TestCase unittest puro qui è
# PERICOLOSO — senza il guard DatabaseOperationForbidden, con
# DJANGO_API_STRONG_IDEMPOTENCY_ENABLED=1 il claim idempotenza scriverebbe sul
# DB DEV reale (successo, 2026-07-22: chiavi a-1/r-1 finite in
# dbops.idempotency_keys). Il flag lo spegne il runner per tutta la suite
# (`zeroerp_backend/test_runner.py`): qui si testa la delega al service, lo
# store ha i suoi test dedicati.
class TestAzioniHttp(JwtMockedApiTest):
    """Azioni annulla/requeue a livello HTTP (idempotency + delega)."""

    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    # 6. POST annulla senza Idempotency-Key → 400.
    @patch(_AUTH, return_value=(MagicMock(is_authenticated=True), None))
    @patch(f"{_VIEWS}.gestione_service")
    def test_annulla_richiede_idempotency_key(self, mock_svc, _auth):
        with patch(
            "apps.core.api.permissions.ZeroERPPermission.has_permission",
            return_value=True,
        ):
            resp = self.client.post(
                "/api/v1/core/tracciamento/coda-lavori/5/annulla/",
                content_type="application/json",
            )
        self.assertEqual(resp.status_code, 400)
        mock_svc.annulla_job.assert_not_called()

    # 7. POST annulla ok → delega al service.
    @patch(_AUTH, return_value=(MagicMock(is_authenticated=True), None))
    @patch(f"{_VIEWS}.gestione_service")
    def test_annulla_200(self, mock_svc, _auth):
        mock_svc.annulla_job.return_value = {"job_id": 5, "stato": "ANNULLATO"}
        with patch(
            "apps.core.api.permissions.ZeroERPPermission.has_permission",
            return_value=True,
        ):
            resp = self.client.post(
                "/api/v1/core/tracciamento/coda-lavori/5/annulla/",
                data="{}", content_type="application/json",
                headers={"Idempotency-Key": "a-1"},
            )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["stato"], "ANNULLATO")

    # 8. POST requeue: extra_tentativi dal payload (default 3 se assente).
    @patch(_AUTH, return_value=(MagicMock(is_authenticated=True), None))
    @patch(f"{_VIEWS}.gestione_service")
    def test_requeue_200_extra_tentativi(self, mock_svc, _auth):
        mock_svc.requeue_job.return_value = {"job_id": 5, "stato": "PENDING"}
        with patch(
            "apps.core.api.permissions.ZeroERPPermission.has_permission",
            return_value=True,
        ):
            resp = self.client.post(
                "/api/v1/core/tracciamento/coda-lavori/5/requeue/",
                data=json.dumps({"extra_tentativi": 5}),
                content_type="application/json",
                headers={"Idempotency-Key": "r-1"},
            )
        self.assertEqual(resp.status_code, 200)
        kwargs = mock_svc.requeue_job.call_args.kwargs
        self.assertEqual(kwargs["extra_tentativi"], 5)
