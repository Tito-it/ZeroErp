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
#   3) numera_ok_accoda_operatore_scope_business_key — 200 + kwargs accoda (azienda scelta)
#   3-bis) numera_selezione_divisa_per_azienda — BE10 a, modalità globale
#   3-ter) numera_lotto_senza_azienda_400 — niente accodato
#   4) numera_senza_identita_400 — JWT senza claim identita_id
#   5) numera_lotto_dichiara_il_passaggio — l'azione dalla riga EMESSA -> DEFINITIVA
#   6) numera_perimetro_tiene_il_permesso — nessun documento da cui leggere la riga
# ------------------------------------------------------------

import json
from unittest.mock import Mock, patch

from django.test import Client

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
# ⭐ Dal 2026-11-07 (BE10 a) l'accodamento sta nel service, un lavoro per
#    azienda; le aziende vengono dalla combo di topbar, e l'azienda dei lotti
#    spuntati dal repository di vendite.
_SVC = "apps.vendite.services.fatturazione_accodamento_service"
_REPO = f"{_SVC}.CodaLavoriRepository"
_VENDITE = f"{_SVC}.VenditeRepository"
_AZIENDE = "apps.core.services.coda_lavori.scope.EmittenteAttivoRepository"
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
    @patch(_AZIENDE)
    @patch(_REPO)
    def test_numera_ok_accoda_operatore_scope_business_key(
        self, repo_cls, aziende_cls, resolver, _extract, _extract_ef, _auth,
    ) -> None:
        resolver.get_emittenti_pk_ids.return_value = [3]
        aziende_cls.return_value.list_selezionabili.return_value = [
            {"emittente_fiscale_id": 3, "codice": "ACME", "soggetto_ruolo_id": 30},
        ]
        repo_cls.return_value.accoda.return_value = 777

        resp = self.client.post(
            _NUMERA, data=json.dumps({"competenza_mese": "2026-06-15"}),
            content_type="application/json",
            headers={"Idempotency-Key": "n-1"},
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"], {"lavori": [{
            "job_id": 777, "stato": "PENDING",
            "emittente_fiscale_id": 3, "emittente_codice": "ACME",
        }]})

        kwargs = repo_cls.return_value.accoda.call_args.kwargs
        self.assertEqual(kwargs["job_type"], "FATTURAZIONE_NUMERA")
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
        # chiave business = competenza + AZIENDA del lavoro
        self.assertEqual(
            kwargs["idempotency_key"], "FATTURAZIONE_NUMERA:2026-06-01:3",
        )

    # 3-bis. ⭐ BE10 (a): «Rendi definitive» su una SELEZIONE in modalità
    #    globale si divide per azienda — ogni lavoro con i soli suoi lotti, la
    #    sua chiave (il digest della SUA parte) e i lotti nell'handle, perché
    #    il frontend marchi le righe di ciascun giro.
    @patch(_AUTH, return_value=(_mock_user(), None))
    @patch(_EXTRACT_EMITTENTE, return_value=None)
    @patch(_EXTRACT_IDENTITA, return_value=5)
    @patch(_RESOLVER)
    @patch(_VENDITE)
    @patch(_AZIENDE)
    @patch(_REPO)
    def test_numera_selezione_divisa_per_azienda(
        self, repo_cls, aziende_cls, vendite_cls, resolver, _extract, _extract_ef, _auth,
    ) -> None:
        resolver.get_emittenti_pk_ids.return_value = [3, 4]
        aziende_cls.return_value.list_selezionabili.return_value = [
            {"emittente_fiscale_id": 3, "codice": "ACME", "soggetto_ruolo_id": 30},
            {"emittente_fiscale_id": 4, "codice": "BETA", "soggetto_ruolo_id": 40},
        ]
        vendite_cls.return_value.aziende_dei_lotti.return_value = {11: 40, 12: 30, 13: 40}
        repo_cls.return_value.accoda.side_effect = [801, 802]

        resp = self.client.post(
            _NUMERA,
            data=json.dumps({"competenza_mese": "2026-06-01", "lotti": [11, 12, 13]}),
            content_type="application/json",
            headers={"Idempotency-Key": "n-3"},
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["lavori"], [
            {"job_id": 801, "stato": "PENDING", "emittente_fiscale_id": 3,
             "emittente_codice": "ACME", "lotti": [12]},
            {"job_id": 802, "stato": "PENDING", "emittente_fiscale_id": 4,
             "emittente_codice": "BETA", "lotti": [11, 13]},
        ])
        chiamate = [c.kwargs for c in repo_cls.return_value.accoda.call_args_list]
        self.assertEqual([c["payload"]["lotti"] for c in chiamate], [[12], [11, 13]])
        self.assertEqual([c["scope"]["scope_key"] for c in chiamate], ["3", "4"])
        # Il digest è della PARTE di ciascuno: due chiavi diverse.
        self.assertNotEqual(chiamate[0]["idempotency_key"], chiamate[1]["idempotency_key"])

    # 3-ter. ⛔ Un lotto di cui non si trova l'azienda (inesistente o fuori
    #    perimetro) è un 400 parlante, e non si accoda NIENTE: il gesto è uno.
    @patch(_AUTH, return_value=(_mock_user(), None))
    @patch(_EXTRACT_EMITTENTE, return_value=None)
    @patch(_EXTRACT_IDENTITA, return_value=5)
    @patch(_RESOLVER)
    @patch(_VENDITE)
    @patch(_AZIENDE)
    @patch(_REPO)
    def test_numera_lotto_senza_azienda_400(
        self, repo_cls, aziende_cls, vendite_cls, resolver, _extract, _extract_ef, _auth,
    ) -> None:
        resolver.get_emittenti_pk_ids.return_value = [3]
        aziende_cls.return_value.list_selezionabili.return_value = [
            {"emittente_fiscale_id": 3, "codice": "ACME", "soggetto_ruolo_id": 30},
        ]
        vendite_cls.return_value.aziende_dei_lotti.return_value = {12: 30}

        resp = self.client.post(
            _NUMERA,
            data=json.dumps({"competenza_mese": "2026-06-01", "lotti": [12, 99]}),
            content_type="application/json",
            headers={"Idempotency-Key": "n-4"},
        )

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"]["code"], "E_VALIDATION_INPUT")
        repo_cls.return_value.accoda.assert_not_called()

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
