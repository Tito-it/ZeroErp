# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke test HTTP degli endpoint del giro fatturazione on-demand (C-3):
#        POST /vendite/fatturazione/run/ (accoda in dbops.coda_lavori) e GET
#        .../run/<job_id>/ (polling). Mock del repository coda + permission
#        resolver (nessun DB). Verifica auth, idempotency-key, parametri di
#        accodamento (run_as OPERATORE, scope catturato, chiave business),
#        ownership del polling.
#
# Indice test:
#   1) run_richiede_jwt — 401
#   2) run_richiede_idempotency_key — 400
#   3) run_ok_accoda_operatore_scope_business_key — 200 + kwargs accoda
#      (identità completa nello scope: auth_user_id+username+identita_id)
#   4) run_senza_identita_400 — JWT senza claim identita_id
#   5) stato_ok_ritorna_job — 200 (scoped all'operatore)
#   6) stato_non_trovato_404 — job altrui/inesistente
# ------------------------------------------------------------

import json
from unittest.mock import Mock, patch

from django.test import Client

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_REPO = "apps.vendite.api.views.CodaLavoriRepository"
_RESOLVER = "apps.vendite.api.views.PermissionResolver"
_SCOPE_UID = "apps.vendite.api.views.get_scope_user_id"
_EXTRACT_IDENTITA = "apps.vendite.api.views.extract_identita_id_from_request"

_RUN = "/api/v1/vendite/fatturazione/run/"


# Scopo: user fittizio con identità reale (id/username usati dalla view per lo
#        scope catturato del job — anche superuser, che accoda col proprio id).
def _mock_user(user_id: int = 9, username: str = "op9") -> Mock:
    return Mock(id=user_id, username=username)


class FatturazioneRunApiTests(JwtMockedApiTest):

    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    # 1. Senza JWT → 401.
    def test_run_richiede_jwt(self) -> None:
        resp = self.client.post(
            _RUN, data=json.dumps({"competenza_mese": "2026-06-01"}),
            content_type="application/json",
            headers={"Idempotency-Key": "k1"},
        )
        self.assertEqual(resp.status_code, 401)

    # 2. Senza Idempotency-Key → 400.
    @patch(_AUTH, return_value=(Mock(), None))
    def test_run_richiede_idempotency_key(self, _auth) -> None:
        resp = self.client.post(
            _RUN, data=json.dumps({"competenza_mese": "2026-06-01"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    # 3. Accoda un job OPERATORE con identità COMPLETA nello scope catturato
    #    (auth_user_id + username + identita_id dal JWT) e chiave BUSINESS.
    #    Token None = pattern test pre-§8.3.4 (bypassa la validazione claim
    #    della subclass); il claim è coperto dal mock dell'extract della view.
    @patch(_AUTH, return_value=(_mock_user(), None))
    @patch(_EXTRACT_IDENTITA, return_value=5)
    @patch(_RESOLVER)
    @patch(_REPO)
    def test_run_ok_accoda_operatore_scope_business_key(
        self, repo_cls, resolver, _extract, _auth,
    ) -> None:
        resolver.get_emittenti_ids.return_value = [4, 3]  # non ordinati
        repo_cls.return_value.accoda.return_value = 555

        resp = self.client.post(
            _RUN, data=json.dumps({"competenza_mese": "2026-06-15"}),
            content_type="application/json",
            headers={"Idempotency-Key": "k-run-1"},
        )

        self.assertEqual(resp.status_code, 200)
        body = resp.json()["data"]
        self.assertEqual(body["job_id"], 555)
        self.assertEqual(body["stato"], "PENDING")

        kwargs = repo_cls.return_value.accoda.call_args.kwargs
        self.assertEqual(kwargs["job_type"], "FATTURAZIONE_GIRO")
        self.assertEqual(kwargs["run_as"], "OPERATORE")
        self.assertEqual(kwargs["scope"], {
            "auth_user_id": 9, "username": "op9", "identita_id": 5,
            "emittente_ids": [4, 3],
        })
        # competenza normalizzata al 1° nel payload del job
        self.assertEqual(kwargs["payload"]["competenza_mese"], "2026-06-01")
        # chiave business = competenza + emittenti ORDINATI (dedup deterministico)
        self.assertEqual(kwargs["idempotency_key"], "FATTURAZIONE_GIRO:2026-06-01:3,4")

    # 4. JWT senza claim identita_id (token anomalo) → 400 parlante, no accoda.
    @patch(_AUTH, return_value=(_mock_user(), None))
    @patch(_EXTRACT_IDENTITA, return_value=None)
    @patch(_RESOLVER)
    @patch(_REPO)
    def test_run_senza_identita_400(
        self, repo_cls, _resolver, _extract, _auth,
    ) -> None:
        resp = self.client.post(
            _RUN, data=json.dumps({"competenza_mese": "2026-06-15"}),
            content_type="application/json",
            headers={"Idempotency-Key": "k-run-2"},
        )
        self.assertEqual(resp.status_code, 400)
        repo_cls.return_value.accoda.assert_not_called()

    # 5. Polling: ritorna lo stato del job (scoped all'operatore).
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SCOPE_UID, return_value=9)
    @patch(_REPO)
    def test_stato_ok_ritorna_job(self, repo_cls, _scope_uid, _auth) -> None:
        repo_cls.return_value.get_stato.return_value = {
            "id": 555, "job_type": "FATTURAZIONE_GIRO", "stato": "FATTO",
            "tentativi": 0, "max_tentativi": 5,
            "result": {"lane": 3}, "ultimo_errore": None, "job_run_id": 12,
        }

        resp = self.client.get(f"{_RUN}555/")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["stato"], "FATTO")
        # get_stato invocato con ownership (auth_user_id dell'operatore)
        repo_cls.return_value.get_stato.assert_called_once_with(555, auth_user_id=9)

    # 6. Job inesistente o di altro operatore → 404 (get_stato None).
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SCOPE_UID, return_value=9)
    @patch(_REPO)
    def test_stato_non_trovato_404(self, repo_cls, _scope_uid, _auth) -> None:
        repo_cls.return_value.get_stato.return_value = None
        resp = self.client.get(f"{_RUN}999/")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"]["code"], "E_JOB_NON_TROVATO")
