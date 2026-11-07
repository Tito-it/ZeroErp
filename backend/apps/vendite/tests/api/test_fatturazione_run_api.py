# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
#      (identità completa, scope DENTRO l'azienda scelta, chiave per azienda)
#   3-bis) run_modalita_globale_un_lavoro_per_azienda — BE10 a: N aziende,
#      N lavori, ognuno con la sua scope_key e la sua chiave
#   4) run_senza_identita_400 — JWT senza claim identita_id
#   5) stato_ok_ritorna_job — 200; il perimetro d'azienda lo fa la RLS (BE9):
#      la view non filtra
#   6) stato_non_trovato_404 — job di altra azienda (RLS) / inesistente
#   7) stato_non_restringe_ai_miei — un collega della stessa azienda segue il
#      giro condiviso via dedup: il polling non filtra per chi ha accodato
# ------------------------------------------------------------

import json
from unittest.mock import Mock, patch

from django.test import Client

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_REPO = "apps.vendite.api.views.CodaLavoriRepository"
# ⭐ Dal 2026-11-07 (BE10 a) l'ACCODAMENTO sta nel service, un lavoro per
#    azienda: il repository della coda si mocka la'; le aziende vengono dalla
#    combo di topbar (`EmittenteAttivoRepository.list_selezionabili`).
_REPO_ACCODA = "apps.vendite.services.fatturazione_accodamento_service.CodaLavoriRepository"
_AZIENDE = "apps.core.services.coda_lavori.scope.EmittenteAttivoRepository"
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
    #    (auth_user_id + username + identita_id dal JWT), DENTRO l'azienda
    #    scelta, e chiave BUSINESS di quell'azienda.
    #    Token None = pattern test pre-§8.3.4 (bypassa la validazione claim
    #    della subclass); il claim è coperto dal mock dell'extract della view.
    @patch(_AUTH, return_value=(_mock_user(), None))
    @patch(_EXTRACT_EMITTENTE, return_value=3)
    @patch(_EXTRACT_IDENTITA, return_value=5)
    @patch(_RESOLVER_SCOPE)
    @patch(_AZIENDE)
    @patch(_REPO_ACCODA)
    def test_run_ok_accoda_operatore_scope_business_key(
        self, repo_cls, aziende_cls, resolver, _extract, _extract_ef, _auth,
    ) -> None:
        resolver.get_emittenti_pk_ids.return_value = [3]
        aziende_cls.return_value.list_selezionabili.return_value = [
            {"emittente_fiscale_id": 3, "codice": "ACME", "soggetto_ruolo_id": 30},
        ]
        repo_cls.return_value.accoda.return_value = 555
        repo_cls.return_value.stati_dopo_accodamento.return_value = {555: "PENDING"}

        resp = self.client.post(
            _RUN, data=json.dumps({"competenza_mese": "2026-06-15"}),
            content_type="application/json",
            headers={"Idempotency-Key": "k-run-1"},
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"], {"lavori": [{
            "job_id": 555, "stato": "PENDING",
            "emittente_fiscale_id": 3, "emittente_codice": "ACME",
        }]})
        # Con un'azienda scelta la combo si chiede per QUELLA sola.
        aziende_cls.return_value.list_selezionabili.assert_called_once_with(9, solo_id=3)

        kwargs = repo_cls.return_value.accoda.call_args.kwargs
        self.assertEqual(kwargs["job_type"], "FATTURAZIONE_GIRO")
        self.assertEqual(kwargs["run_as"], "OPERATORE")
        self.assertEqual(kwargs["scope"], {
            "auth_user_id": 9, "username": "op9", "identita_id": 5,
            # Congelato all'enqueue: senza, il worker girerebbe in modalità
            # globale e il giro chiesto «dentro 3» toccherebbe anche il 4.
            "emittente_attivo_id": 3,
            "emittente_ids": [3],
            "scope_key": "3",
        })
        # competenza normalizzata al 1° nel payload del job
        self.assertEqual(kwargs["payload"]["competenza_mese"], "2026-06-01")
        # ⭐ Chiave business = tipo + CORSIA + competenza + AZIENDA. La corsia
        #    e' entrata il 2026-09-05 (opzione A); l'azienda e' la scope_key del
        #    lavoro, la stessa del giro notturno per quell'azienda.
        self.assertEqual(
            kwargs["idempotency_key"],
            "FATTURAZIONE_GIRO:differita:2026-06-01:3",
        )

    # 3-bis. ⭐ BE10 (a): in modalità globale (nessun emittente attivo) un
    #    lavoro PER AZIENDA della combo, ognuno nella sua azienda e con la sua
    #    chiave. Un lavoro senza azienda la porta lo rifiuterebbe
    #    (`E_CODA_LAVORO_SENZA_EMITTENTE`).
    @patch(_AUTH, return_value=(_mock_user(), None))
    @patch(_EXTRACT_EMITTENTE, return_value=None)
    @patch(_EXTRACT_IDENTITA, return_value=5)
    @patch(_RESOLVER_SCOPE)
    @patch(_AZIENDE)
    @patch(_REPO_ACCODA)
    def test_run_modalita_globale_un_lavoro_per_azienda(
        self, repo_cls, aziende_cls, resolver, _extract, _extract_ef, _auth,
    ) -> None:
        resolver.get_emittenti_pk_ids.return_value = [4, 3]
        aziende_cls.return_value.list_selezionabili.return_value = [
            {"emittente_fiscale_id": 3, "codice": "ACME", "soggetto_ruolo_id": 30},
            {"emittente_fiscale_id": 4, "codice": "BETA", "soggetto_ruolo_id": 40},
        ]
        repo_cls.return_value.accoda.side_effect = [555, 556]
        repo_cls.return_value.stati_dopo_accodamento.return_value = {555: "PENDING", 556: "PENDING"}

        resp = self.client.post(
            _RUN, data=json.dumps({"competenza_mese": "2026-06-15"}),
            content_type="application/json",
            headers={"Idempotency-Key": "k-run-3"},
        )

        self.assertEqual(resp.status_code, 200)
        lavori = resp.json()["data"]["lavori"]
        self.assertEqual(
            [(lv["job_id"], lv["emittente_codice"]) for lv in lavori],
            [(555, "ACME"), (556, "BETA")],
        )
        aziende_cls.return_value.list_selezionabili.assert_called_once_with(9, solo_id=None)
        chiamate = [c.kwargs for c in repo_cls.return_value.accoda.call_args_list]
        self.assertEqual(
            [(c["scope"]["emittente_attivo_id"], c["scope"]["scope_key"]) for c in chiamate],
            [(3, "3"), (4, "4")],
        )
        self.assertEqual(
            [c["idempotency_key"] for c in chiamate],
            ["FATTURAZIONE_GIRO:differita:2026-06-01:3",
             "FATTURAZIONE_GIRO:differita:2026-06-01:4"],
        )

    # 4. JWT senza claim identita_id (token anomalo) → 400 parlante, no accoda.
    @patch(_AUTH, return_value=(_mock_user(), None))
    @patch(_EXTRACT_IDENTITA, return_value=None)
    @patch(_RESOLVER_SCOPE)
    @patch(_REPO_ACCODA)
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

    # 5. Polling: ritorna lo stato del job. ⭐ Dal blocco 5b (BE9) il perimetro
    #    d'azienda lo fa la RLS della coda: la view non passa nessun filtro, e
    #    non legge la whitelist.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_REPO)
    def test_stato_ok_ritorna_job(self, repo_cls, _auth) -> None:
        repo_cls.return_value.get_stato.return_value = {
            "id": 555, "job_type": "FATTURAZIONE_GIRO", "stato": "FATTO",
            "tentativi": 0, "max_tentativi": 5,
            "result": {"lane": 3}, "ultimo_errore": None, "job_run_id": 12,
        }

        resp = self.client.get(f"{_RUN}555/")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["stato"], "FATTO")
        repo_cls.return_value.get_stato.assert_called_once_with(555)

    # 6. Job inesistente o di un'altra azienda (la RLS non lo mostra) → 404.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_REPO)
    def test_stato_non_trovato_404(self, repo_cls, _auth) -> None:
        repo_cls.return_value.get_stato.return_value = None
        resp = self.client.get(f"{_RUN}999/")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"]["code"], "E_JOB_NON_TROVATO")

    # 7. ⛔ Il polling NON restringe ai lavori «miei»: un collega della stessa
    #    azienda (qui user_id 99 ≠ chi ha accodato) segue il giro che la dedup
    #    gli ha restituito. «Miei» è un filtro della lista code, non del
    #    polling.
    @patch(_AUTH, return_value=(_mock_user(user_id=99, username="altro_op"), None))
    @patch(_REPO)
    def test_stato_non_restringe_ai_miei(self, repo_cls, _auth) -> None:
        repo_cls.return_value.get_stato.return_value = {
            "id": 555, "job_type": "FATTURAZIONE_GIRO", "stato": "IN_CORSO",
            "tentativi": 0, "max_tentativi": 5,
            "result": None, "ultimo_errore": None, "job_run_id": 1,
        }
        resp = self.client.get(f"{_RUN}555/")
        self.assertEqual(resp.status_code, 200)
        repo_cls.return_value.get_stato.assert_called_once_with(555)
