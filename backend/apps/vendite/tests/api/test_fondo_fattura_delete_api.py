# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test API del verbo sui fondi fattura — `DELETE /vendite/fondi-fattura/<id>/`
#        (BE-4 di brief-db-fondo-fattura-ricalcolo-e-governo §9.3).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) FondoFatturaDeleteApiTests.test_delete_ok_envelope
2) FondoFatturaDeleteApiTests.test_delete_senza_idempotency_key
3) FondoFatturaDeleteApiTests.test_delete_requires_jwt
4) FondoFatturaDeleteApiTests.test_id_dal_path_non_dal_corpo
5) FondoFatturaDeletePermessoTests.test_post_permission_dichiarato

⭐ PERCHE' QUESTO FILE ESISTE, quando il service ha gia' i suoi test.
I test del service girano sulla funzione: non attraversano la ROTTA, il metodo
HTTP, il controllo della `Idempotency-Key` ne' l'envelope. Il verbo qui e' un
`DELETE` con CORPO VUOTO passato a `handle_post_json`, che nasce per le POST e
fa `parse_json_body`: se quel parsing non reggesse il vuoto, ogni chiamata
tornerebbe 400 e tutti i test del service resterebbero verdi.
"""

from unittest.mock import Mock, patch

from django.test import Client

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest
from apps.vendite.api.views_fondi_fattura import ApiFondoFatturaDelete

_URL = "/api/v1/vendite/fondi-fattura/987/"
_ESITO = {
    "status": "deleted",
    "fondo_source_id": 987,
    "deleted_righe": 1,
    "deleted_fondi": 1,
    "deleted_source": 1,
}


class FondoFatturaDeleteApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    # Scopo: il giro completo — rotta, metodo, chiave, envelope e contatori.
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(), None),
    )
    @patch("apps.vendite.api.views_fondi_fattura.fn_cancella_fondo_fattura")
    def test_delete_ok_envelope(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _ESITO
        response = self.client.delete(_URL, headers={"idempotency-key": "k-1"})
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["status"], "deleted")
        self.assertEqual(data["deleted_source"], 1)

    # Scopo: ⭐ la chiave e' OBBLIGATORIA, e il gesto e' irreversibile: senza,
    #        un doppio invio riceverebbe un errore per un'operazione riuscita.
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(), None),
    )
    @patch("apps.vendite.api.views_fondi_fattura.fn_cancella_fondo_fattura")
    def test_delete_senza_idempotency_key(self, mocked_fn, _mock_auth):
        response = self.client.delete(_URL)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["error"]["code"], "E_IDEMPOTENCY_KEY_REQUIRED"
        )
        # ⛔ E il service NON dev'essere stato chiamato: un rifiuto che arriva
        #    DOPO la cancellazione sarebbe la peggiore delle risposte.
        mocked_fn.assert_not_called()

    # Scopo: nessun accesso anonimo a un gesto che cancella denaro.
    def test_delete_requires_jwt(self):
        response = self.client.delete(_URL, headers={"idempotency-key": "k-2"})
        self.assertEqual(response.status_code, 401)

    # Scopo: ⚠️ l'id viene dal PATH e il corpo si ignora. Un corpo che potesse
    #        dirottare il bersaglio sarebbe un modo per cancellare l'atto di un
    #        altro passando dal permesso sul proprio.
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(), None),
    )
    @patch("apps.vendite.api.views_fondi_fattura.fn_cancella_fondo_fattura")
    def test_id_dal_path_non_dal_corpo(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _ESITO
        response = self.client.delete(
            _URL,
            data='{"fondo_source_id": 1}',
            content_type="application/json",
            headers={"idempotency-key": "k-3"},
        )
        self.assertEqual(response.status_code, 200)
        mocked_fn.assert_called_once_with(fondo_source_id=987)


class FondoFatturaDeletePermessoTests(JwtMockedApiTest):
    # Scopo: ⭐ il cancello e' DICHIARATIVO, quindi si asserisce la
    #        dichiarazione. `governa_fondo_fattura` e' un'azione `pericolosa`:
    #        se qualcuno togliesse la riga, l'endpoint resterebbe aperto a
    #        chiunque abbia l'area vendite, e nessun altro test lo vedrebbe.
    def test_post_permission_dichiarato(self):
        self.assertEqual(
            ApiFondoFatturaDelete.post_permission, "governa_fondo_fattura"
        )
        self.assertEqual(ApiFondoFatturaDelete.area_funzionale, "vendite")
