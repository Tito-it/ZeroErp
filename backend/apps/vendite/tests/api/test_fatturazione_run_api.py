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
#      (identità completa + scope_key nello scope)
#   4) run_senza_identita_400 — JWT senza claim identita_id
#   5) stato_ok_ritorna_job — 200, ownership scope-based (scope_key richiedente)
#   6) stato_non_trovato_404 — job di altro scope/inesistente
#   7) stato_admin_vede_tutto — whitelist None → owner_scope_key None (no filtro)
#   8) stato_ownership_scope_non_enqueuer — fix cross-operatore (filtro per scope)
# ------------------------------------------------------------

import json
from unittest.mock import Mock, patch

from django.test import Client

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_REPO = "apps.vendite.api.views.CodaLavoriRepository"
# Il resolver del POLLING (ownership scope-based) vive nella view di vendite.
_RESOLVER = "apps.vendite.api.views.PermissionResolver"
# ⭐ Dal 2026-09-15 la CATTURA dello scope all'enqueue sta nel BB
#    `coda_lavori.scope.scope_operatore_da_request` (seconda occorrenza: «Esegui
#    ora» dal drawer dei processi): i tre nomi dell'enqueue si mockano LA', non
#    nella view — che non li importa piu'.
_SCOPE = "apps.core.services.coda_lavori.scope"
_RESOLVER_SCOPE = f"{_SCOPE}.PermissionResolver"
_EXTRACT_IDENTITA = f"{_SCOPE}.extract_identita_id_from_request"
# Emittente attivo del JWT: congelato nello scope del job (impersonazione di
# scope). Mockato come l'identita' — il claim vero non passa dai test API.
_EXTRACT_EMITTENTE = f"{_SCOPE}.extract_emittente_attivo_from_request"

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
    @patch(_EXTRACT_EMITTENTE, return_value=3)
    @patch(_EXTRACT_IDENTITA, return_value=5)
    @patch(_RESOLVER_SCOPE)
    @patch(_REPO)
    def test_run_ok_accoda_operatore_scope_business_key(
        self, repo_cls, resolver, _extract, _extract_ef, _auth,
    ) -> None:
        resolver.get_emittenti_pk_ids.return_value = [4, 3]  # non ordinati
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
            # Congelato all'enqueue: senza, il worker girerebbe in modalità
            # globale e il giro chiesto «dentro 3» toccherebbe anche il 4.
            "emittente_attivo_id": 3,
            "emittente_ids": [4, 3],
            # scope_key = componente-scope della chiave business (emittenti
            # ORDINATI) = token di ownership del polling (scope-based)
            "scope_key": "3,4",
        })
        # competenza normalizzata al 1° nel payload del job
        self.assertEqual(kwargs["payload"]["competenza_mese"], "2026-06-01")
        # ⭐ Chiave business = tipo + CORSIA + competenza + emittenti ORDINATI.
        #    La corsia e' entrata il 2026-09-05 (opzione A): senza, il batch
        #    notturno avrebbe visto «immediata» e «differita» dello stesso mese e
        #    della stessa azienda come lo stesso lavoro, e ne avrebbe scartata
        #    una in silenzio. Qui il valore e' «differita» — il giro on-demand di
        #    massa — quindi per il verbo web cambia la FORMA, non il
        #    comportamento: nessun giro che si deduplicava smette di farlo.
        self.assertEqual(
            kwargs["idempotency_key"],
            "FATTURAZIONE_GIRO:differita:2026-06-01:3,4",
        )

    # 4. JWT senza claim identita_id (token anomalo) → 400 parlante, no accoda.
    @patch(_AUTH, return_value=(_mock_user(), None))
    @patch(_EXTRACT_IDENTITA, return_value=None)
    @patch(_RESOLVER_SCOPE)
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
        # ⭐ Il codice e' quello della terna incompleta — lo stesso che il
        #    drenatore solleverebbe un minuto dopo — detto adesso.
        self.assertEqual(
            resp.json()["error"]["code"], "E_CODA_SCOPE_OPERATORE_INVALIDO",
        )
        repo_cls.return_value.accoda.assert_not_called()

    # 5. Polling: ritorna lo stato del job, ownership SCOPE-based (la scope_key
    #    del richiedente, non l'id di chi ha accodato).
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_RESOLVER)
    @patch(_REPO)
    def test_stato_ok_ritorna_job(self, repo_cls, resolver, _auth) -> None:
        resolver.get_emittenti_pk_ids.return_value = [72]  # operatore scoped
        repo_cls.return_value.get_stato.return_value = {
            "id": 555, "job_type": "FATTURAZIONE_GIRO", "stato": "FATTO",
            "tentativi": 0, "max_tentativi": 5,
            "result": {"lane": 3}, "ultimo_errore": None, "job_run_id": 12,
        }

        resp = self.client.get(f"{_RUN}555/")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["stato"], "FATTO")
        # get_stato invocato con la scope_key del richiedente (ownership scope)
        repo_cls.return_value.get_stato.assert_called_once_with(
            555, owner_scope_key="72",
        )

    # 6. Job inesistente o di altro SCOPE → 404 (get_stato None).
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_RESOLVER)
    @patch(_REPO)
    def test_stato_non_trovato_404(self, repo_cls, resolver, _auth) -> None:
        resolver.get_emittenti_pk_ids.return_value = [72]
        repo_cls.return_value.get_stato.return_value = None
        resp = self.client.get(f"{_RUN}999/")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"]["code"], "E_JOB_NON_TROVATO")

    # 7. Admin globale (whitelist None) → owner_scope_key=None: nessun filtro,
    #    vede ogni job.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_RESOLVER)
    @patch(_REPO)
    def test_stato_admin_vede_tutto(self, repo_cls, resolver, _auth) -> None:
        resolver.get_emittenti_pk_ids.return_value = None  # admin globale
        repo_cls.return_value.get_stato.return_value = {
            "id": 555, "job_type": "FATTURAZIONE_GIRO", "stato": "IN_CORSO",
            "tentativi": 0, "max_tentativi": 5,
            "result": None, "ultimo_errore": None, "job_run_id": 1,
        }
        resp = self.client.get(f"{_RUN}555/")
        self.assertEqual(resp.status_code, 200)
        repo_cls.return_value.get_stato.assert_called_once_with(
            555, owner_scope_key=None,
        )

    # 8. Fix cross-operatore: l'ownership del polling dipende dalla SCOPE_KEY del
    #    richiedente (whitelist), NON dall'id di chi ha accodato → un altro
    #    operatore con la stessa whitelist risolve la stessa ownership e vede il
    #    job condiviso via dedup (qui user_id 99 ≠ enqueuer, ma stessa scope 3,4).
    @patch(_AUTH, return_value=(_mock_user(user_id=99, username="altro_op"), None))
    @patch(_RESOLVER)
    @patch(_REPO)
    def test_stato_ownership_scope_non_enqueuer(
        self, repo_cls, resolver, _auth,
    ) -> None:
        resolver.get_emittenti_pk_ids.return_value = [4, 3]  # stessa whitelist
        repo_cls.return_value.get_stato.return_value = {
            "id": 555, "job_type": "FATTURAZIONE_GIRO", "stato": "IN_CORSO",
            "tentativi": 0, "max_tentativi": 5,
            "result": None, "ultimo_errore": None, "job_run_id": 1,
        }
        resp = self.client.get(f"{_RUN}555/")
        self.assertEqual(resp.status_code, 200)
        # filtrato per SCOPE (3,4), non per user_id 99
        repo_cls.return_value.get_stato.assert_called_once_with(
            555, owner_scope_key="3,4",
        )
