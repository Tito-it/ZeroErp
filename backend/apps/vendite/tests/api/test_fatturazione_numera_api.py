# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke test HTTP dell'endpoint di numerazione di perimetro (C-4):
#        POST /vendite/fatturazione/numera/ (accoda FATTURAZIONE_NUMERA in
#        dbops.coda_lavori). Mock del repository coda + permission resolver
#        (nessun DB). Verifica auth, idempotency-key, parametri di accodamento
#        (run_as OPERATORE, identità completa nello scope, chiave business).
#        Il polling riusa GET .../run/<job_id>/ (già coperto da test_fatturazione_run_api).
#
# Indice test:
#   1) numera_richiede_jwt — 401
#   2) numera_richiede_idempotency_key — 400
#   3) numera_ok_accoda_operatore_scope_business_key — 200 + kwargs accoda
#   4) numera_senza_identita_400 — JWT senza claim identita_id
#   5) numera_lotto_dichiara_il_passaggio — l'azione dalla riga EMESSA -> DEFINITIVA
#   6) numera_perimetro_tiene_il_permesso — nessun documento da cui leggere la riga
# ------------------------------------------------------------

import json
from unittest.mock import Mock, patch

from django.test import Client

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_REPO = "apps.vendite.api.views.CodaLavoriRepository"
# ⭐ Dal 2026-09-15 la CATTURA dello scope all'enqueue sta nel BB
#    `coda_lavori.scope.scope_operatore_da_request`: i tre nomi si mockano LA',
#    non nella view — che non li importa piu' (questo verbo non fa polling,
#    quindi qui non serve il resolver della view).
_SCOPE = "apps.core.services.coda_lavori.scope"
_RESOLVER = f"{_SCOPE}.PermissionResolver"
_EXTRACT_IDENTITA = f"{_SCOPE}.extract_identita_id_from_request"
# Emittente attivo del JWT: congelato nello scope del job (impersonazione di
# scope). Mockato come l'identita' — il claim vero non passa dai test API.
_EXTRACT_EMITTENTE = f"{_SCOPE}.extract_emittente_attivo_from_request"

_NUMERA = "/api/v1/vendite/fatturazione/numera/"


# Scopo: user fittizio con identità reale (id/username usati dalla view per lo
#        scope catturato del job — anche superuser, che accoda col proprio id).
def _mock_user(user_id: int = 9, username: str = "op9") -> Mock:
    return Mock(id=user_id, username=username)


class FatturazioneNumeraApiTests(JwtMockedApiTest):

    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    # 1. Senza JWT → 401.
    def test_numera_richiede_jwt(self) -> None:
        resp = self.client.post(
            _NUMERA, data=json.dumps({"competenza_mese": "2026-06-01"}),
            content_type="application/json",
            headers={"Idempotency-Key": "n1"},
        )
        self.assertEqual(resp.status_code, 401)

    # 2. Senza Idempotency-Key → 400.
    @patch(_AUTH, return_value=(Mock(), None))
    def test_numera_richiede_idempotency_key(self, _auth) -> None:
        resp = self.client.post(
            _NUMERA, data=json.dumps({"competenza_mese": "2026-06-01"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    # 3. Accoda un job OPERATORE FATTURAZIONE_NUMERA con identità COMPLETA nello
    #    scope catturato e chiave BUSINESS (competenza + emittenti ordinati).
    @patch(_AUTH, return_value=(_mock_user(), None))
    @patch(_EXTRACT_EMITTENTE, return_value=3)
    @patch(_EXTRACT_IDENTITA, return_value=5)
    @patch(_RESOLVER)
    @patch(_REPO)
    def test_numera_ok_accoda_operatore_scope_business_key(
        self, repo_cls, resolver, _extract, _extract_ef, _auth,
    ) -> None:
        resolver.get_emittenti_pk_ids.return_value = [4, 3]  # non ordinati
        repo_cls.return_value.accoda.return_value = 777

        resp = self.client.post(
            _NUMERA, data=json.dumps({"competenza_mese": "2026-06-15"}),
            content_type="application/json",
            headers={"Idempotency-Key": "n-1"},
        )

        self.assertEqual(resp.status_code, 200)
        body = resp.json()["data"]
        self.assertEqual(body["job_id"], 777)
        self.assertEqual(body["stato"], "PENDING")

        kwargs = repo_cls.return_value.accoda.call_args.kwargs
        self.assertEqual(kwargs["job_type"], "FATTURAZIONE_NUMERA")
        self.assertEqual(kwargs["run_as"], "OPERATORE")
        self.assertEqual(kwargs["scope"], {
            "auth_user_id": 9, "username": "op9", "identita_id": 5,
            # Congelato all'enqueue: senza, il worker girerebbe in modalità
            # globale e il giro chiesto «dentro 3» toccherebbe anche il 4.
            "emittente_attivo_id": 3,
            "emittente_ids": [4, 3],
            "scope_key": "3,4",  # ownership scope-based del polling
        })
        # competenza normalizzata al 1° nel payload del job
        self.assertEqual(kwargs["payload"]["competenza_mese"], "2026-06-01")
        # chiave business = competenza + emittenti ORDINATI (dedup deterministico)
        self.assertEqual(
            kwargs["idempotency_key"], "FATTURAZIONE_NUMERA:2026-06-01:3,4",
        )

    # 4. JWT senza claim identita_id → 400 parlante, no accoda.
    @patch(_AUTH, return_value=(_mock_user(), None))
    @patch(_EXTRACT_IDENTITA, return_value=None)
    @patch(_RESOLVER)
    @patch(_REPO)
    def test_numera_senza_identita_400(
        self, repo_cls, _resolver, _extract, _auth,
    ) -> None:
        resp = self.client.post(
            _NUMERA, data=json.dumps({"competenza_mese": "2026-06-15"}),
            content_type="application/json",
            headers={"Idempotency-Key": "n-2"},
        )
        self.assertEqual(resp.status_code, 400)
        repo_cls.return_value.accoda.assert_not_called()


class NumeraPermessiTests(JwtMockedApiTest):
    # 5) «Numera» di UN lotto chiede l'azione dalla riga del passaggio
    #    EMESSA -> DEFINITIVA (M-3, brief-modello-documento-vendita §15.8
    #    punto 3), la stessa della capability e del verbo; nessun
    #    `post_permission` accanto.
    def test_numera_lotto_dichiara_il_passaggio(self) -> None:
        from apps.core.api.permissions import PassaggioDocumento
        from apps.vendite.api.views import ApiFatturazioneNumeraLotto

        self.assertEqual(ApiFatturazioneNumeraLotto.post_passaggio, PassaggioDocumento(
            testata="vendite.fatturazione_lotti", documento_kwarg="lotto_id",
            stato_chiesto="DEFINITIVA",
        ))
        self.assertIsNone(getattr(ApiFatturazioneNumeraLotto, "post_permission", None))

    # 6) La numerazione di PERIMETRO (tutti i lotti EMESSA del mese) non ha un
    #    documento da cui leggere la riga: tiene l'azione dichiarata, la stessa
    #    della riga (Q-F1).
    def test_numera_perimetro_tiene_il_permesso(self) -> None:
        from apps.vendite.api.views import ApiFatturazioneNumera

        self.assertEqual(ApiFatturazioneNumera.post_permission, "numera_fatture_lotti")
