# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `handle_post_json` rifiuta un corpo sbagliato NELL'ENVELOPE, con la
#        stessa forma delle view DRF (`corpo_oggetto`): 400 `E_VALIDATION_INPUT`
#        con `context.motivo` (E-6 e F-10 di
#        analisi-be-difetti-emersi-verifica-doc-api-core, 2026-10-07). Prima
#        rispondeva `{"error": "invalid_json"}` / `{"error": "invalid_payload"}`
#        fuori envelope, una lista usciva `invalid_json`, e ogni `ValueError`
#        dell'handler perdeva codice e messaggio.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_json_illeggibile             — 400 E_VALIDATION_INPUT, motivo invalid_json
2) test_lista_e_invalid_payload      — una lista e' un JSON valido ma non un oggetto
3) test_corpo_non_utf8               — F-10: invalid_json, non il testo del decoder
4) test_drf_lista_e_invalid_payload  — stessa risposta sul percorso DRF Request
5) test_value_error_dell_handler     — 400 E_VALIDATION_INPUT col suo messaggio
6) test_oggetto_passa                — l'handler riceve il corpo, 200
"""

import json

from django.test import RequestFactory, SimpleTestCase
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from apps.core.api.endpoint_helpers import handle_post_json


# Scopo: una richiesta Django col corpo grezzo dato (il ramo `request.body`).
def _grezza(corpo: bytes | str):
    return RequestFactory().post("/api/v1/x/", data=corpo, content_type="application/json")


# Scopo: l'errore dell'envelope, o fallisce se la risposta non lo e'.
def _errore(response) -> dict:
    corpo = json.loads(response.content)
    assert isinstance(corpo.get("error"), dict), corpo
    return corpo["error"]


# Scopo: l'handler che restituisce il corpo ricevuto.
def _eco(payload: dict) -> dict:
    return payload


# ⭐ `SimpleTestCase`: nessuno di questi percorsi deve toccare il DB (api.md).
class HandlePostJsonCorpoTests(SimpleTestCase):

    def test_json_illeggibile(self):
        response = handle_post_json(_grezza("{rotto"), handler=_eco)
        self.assertEqual(response.status_code, 400)
        errore = _errore(response)
        self.assertEqual(errore["code"], "E_VALIDATION_INPUT")
        self.assertEqual(errore["message"], "Il corpo della richiesta non e' un JSON valido.")

    def test_lista_e_invalid_payload(self):
        response = handle_post_json(_grezza("[1, 2]"), handler=_eco)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            _errore(response)["message"],
            "Il corpo della richiesta deve essere un oggetto JSON.",
        )

    def test_corpo_non_utf8(self):
        response = handle_post_json(_grezza(b'{"a": "\xff"}'), handler=_eco)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(_errore(response)["message"], "Il corpo della richiesta non e' un JSON valido.")

    def test_drf_lista_e_invalid_payload(self):
        grezza = APIRequestFactory().post("/api/v1/x/", "[1]", content_type="application/json")
        response = handle_post_json(Request(grezza, parsers=[JSONParser()]), handler=_eco)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            _errore(response)["message"],
            "Il corpo della richiesta deve essere un oggetto JSON.",
        )

    def test_value_error_dell_handler(self):
        def _handler(_payload: dict) -> dict:
            raise ValueError("data_invalid")

        response = handle_post_json(_grezza('{"a": 1}'), handler=_handler)
        self.assertEqual(response.status_code, 400)
        errore = _errore(response)
        self.assertEqual(errore["code"], "E_VALIDATION_INPUT")
        self.assertEqual(errore["message"], "data_invalid")

    def test_oggetto_passa(self):
        response = handle_post_json(_grezza('{"a": 1}'), handler=_eco)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["data"], {"a": 1})
