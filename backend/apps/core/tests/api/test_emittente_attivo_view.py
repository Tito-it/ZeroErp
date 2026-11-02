# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test API dell'endpoint dell'emittente attivo (impersonazione di
#        scope). Copre il CONTRATTO che il frontend consuma — forma della
#        risposta, claim riemesso, guard sul refresh — non le regole di
#        scelta, che stanno in test_emittente_attivo_service.
#
#        Nasce anche da un difetto reale: al primo accesso di Tid
#        (2026-08-04) la combo era vuota. La causa era lato Vue, ma senza un
#        test sul contratto non c'era modo di escludere l'endpoint a colpo
#        sicuro — e mezz'ora di diagnosi è andata a distinguere «non
#        risponde» da «non è stato chiamato».
#
# Indice test (0..N):
#   0. get_ritorna_le_opzioni
#   1. post_senza_refresh_rifiuta
#   2. post_con_refresh_di_un_altro_utente_rifiuta
#   3. post_imposta_emittente_e_riemette_il_claim
#   4. post_globale_rimuove_il_claim
#   5. post_emittente_non_numerico_rifiuta_400
# ------------------------------------------------------------

from __future__ import annotations

from unittest.mock import MagicMock, patch

import json

from django.test import SimpleTestCase
from rest_framework.request import Request

from apps.core.api.emittente_attivo_views import EmittenteAttivoView
from apps.core.api.refresh_cookie import REFRESH_COOKIE_NAME
from apps.core.services.auth_constants import JWT_CLAIM_EMITTENTE_ATTIVO_ID

_SERVICE = "apps.core.api.emittente_attivo_views.EmittenteAttivoService"
_REFRESH = "apps.core.api.emittente_attivo_views.RefreshToken"
_UTENTE = 7


# Scopo: envelope della risposta. `success_response` produce una JsonResponse
#        (non una Response DRF), quindi il corpo si legge dal contenuto JSON.
def _corpo(response) -> dict:
    return json.loads(response.content)["data"]


# Scopo: envelope d'errore di `handle_post_json` — `{"error": {"code": ...}}`,
#        anche per i payload rotti dal 2026-10-07 (E-6).
def _errore(response):
    return json.loads(response.content)["error"]


# Scopo: request DRF minimale con utente autenticato e payload dato.
#        `spec=Request` non è un vezzo: `parse_json_body` (dentro
#        `handle_post_json`) legge `request.data` SOLO se la request è una
#        DRF Request — senza spec cadrebbe sul ramo `request.body`.
#        Il refresh arriva nel cookie HttpOnly (brief sicurezza §2), non nel
#        payload.
def _request(payload: dict | None = None, *, refresh: str | None = None) -> MagicMock:
    request = MagicMock(spec=Request)
    request.user = MagicMock()
    request.user.id = _UTENTE
    request.data = payload if payload is not None else {}
    request.COOKIES = {REFRESH_COOKIE_NAME: refresh} if refresh else {}
    return request


# Scopo: finto RefreshToken che si comporta come quello di SimpleJWT per le
#        due cose che ci servono: `get('user_id')` e il payload mutabile.
def _refresh_token(user_id: int = _UTENTE) -> MagicMock:
    token = MagicMock()
    token.payload = {"user_id": user_id, JWT_CLAIM_EMITTENTE_ATTIVO_ID: 99}
    token.get = MagicMock(side_effect=lambda k, d=None: token.payload.get(k, d))
    token.__setitem__ = MagicMock(
        side_effect=lambda k, v: token.payload.__setitem__(k, v)
    )
    return token


class EmittenteAttivoViewTests(SimpleTestCase):

    # 0. GET: le opzioni arrivano dentro l'envelope, sotto `opzioni`. È
    #    esattamente la forma che la combo legge.
    @patch(_SERVICE)
    def test_get_ritorna_le_opzioni(self, MockService) -> None:
        MockService.return_value.opzioni.return_value = [
            {"emittente_fiscale_id": 32, "codice": "EF1", "ragione_sociale": "Alfa"},
        ]
        response = EmittenteAttivoView().get(_request())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(_corpo(response)["opzioni"][0]["emittente_fiscale_id"], 32)
        MockService.return_value.opzioni.assert_called_once_with(_UTENTE)

    # 1. POST senza cookie di refresh: rifiuto parlante. Senza token non si può
    #    riemettere il claim, e salvare soltanto lascerebbe la sessione a
    #    lavorare dove non deve. `handle_post_json` traduce il ServiceError
    #    nell'envelope d'errore (policy E_EMITTENTE_ATTIVO_TOKEN → 400).
    @patch(_SERVICE)
    def test_post_senza_refresh_rifiuta(self, MockService) -> None:
        MockService.return_value.imposta.return_value = 32
        response = EmittenteAttivoView().post(
            _request({"emittente_fiscale_id": 32})
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(_errore(response)["code"], "E_EMITTENTE_ATTIVO_TOKEN")

    # 2. Guard anti-scambio: il refresh nel cookie deve appartenere all'utente
    #    autenticato. L'access token dice CHI sei, il refresh è un dato in
    #    ingresso: senza confronto si farebbe riemettere a un token altrui il
    #    claim scelto qui.
    @patch(_REFRESH)
    @patch(_SERVICE)
    def test_post_con_refresh_di_un_altro_utente_rifiuta(
        self, MockService, MockRefresh,
    ) -> None:
        MockService.return_value.imposta.return_value = 32
        MockRefresh.return_value = _refresh_token(user_id=_UTENTE + 1)
        response = EmittenteAttivoView().post(
            _request({"emittente_fiscale_id": 32}, refresh="tok")
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(_errore(response)["code"], "E_EMITTENTE_ATTIVO_TOKEN")

    # 3. Percorso felice: claim aggiornato sul refresh, access nuovo nel
    #    corpo e refresh nuovo nel COOKIE (mai nel corpo). Senza i token la
    #    combo cambierebbe e i dati no.
    @patch(_REFRESH)
    @patch(_SERVICE)
    def test_post_imposta_emittente_e_riemette_il_claim(
        self, MockService, MockRefresh,
    ) -> None:
        MockService.return_value.imposta.return_value = 32
        MockService.return_value.descrivi.return_value = {"emittente_fiscale_id": 32}
        token = _refresh_token()
        MockRefresh.return_value = token

        response = EmittenteAttivoView().post(
            _request({"emittente_fiscale_id": 32}, refresh="tok")
        )

        MockService.return_value.imposta.assert_called_once_with(_UTENTE, 32)
        self.assertEqual(token.payload[JWT_CLAIM_EMITTENTE_ATTIVO_ID], 32)
        corpo = _corpo(response)
        self.assertIn("access", corpo)
        self.assertNotIn("refresh", corpo)
        self.assertEqual(response.cookies[REFRESH_COOKIE_NAME].value, str(token))
        self.assertTrue(response.cookies[REFRESH_COOKIE_NAME]["httponly"])

    # 4. «Tutti gli emittenti»: il claim va RIMOSSO, non messo a null —
    #    l'assenza è la convenzione con cui set_jwt_gucs lascia la GUC vuota,
    #    e un null esplicito finirebbe in `int(None)`.
    @patch(_REFRESH)
    @patch(_SERVICE)
    def test_post_globale_rimuove_il_claim(self, MockService, MockRefresh) -> None:
        MockService.return_value.imposta.return_value = None
        MockService.return_value.descrivi.return_value = {"modalita_globale": True}
        token = _refresh_token()
        MockRefresh.return_value = token

        EmittenteAttivoView().post(_request({"emittente_fiscale_id": None}, refresh="tok"))

        MockService.return_value.imposta.assert_called_once_with(_UTENTE, None)
        self.assertNotIn(JWT_CLAIM_EMITTENTE_ATTIVO_ID, token.payload)

    # 5. `emittente_fiscale_id` non numerico: 400 `E_VALIDATION_INPUT` dal
    #    validator (`optional_int` → ValueError → handle_post_json), non un
    #    `int()` che esplode in 500 — il bug della prima stesura. Il service
    #    non deve nemmeno essere interpellato.
    @patch(_SERVICE)
    def test_post_emittente_non_numerico_rifiuta_400(self, MockService) -> None:
        response = EmittenteAttivoView().post(
            _request({"emittente_fiscale_id": "abc"}, refresh="tok")
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(_errore(response)["code"], "E_VALIDATION_INPUT")
        MockService.return_value.imposta.assert_not_called()
