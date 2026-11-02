# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari RequestContextMiddleware — l'`X-Request-ID` del client
#        si accetta solo se e' un UUID (S-1).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_uuid_del_client_accettato_in_forma_canonica
2) test_valore_non_uuid_sostituito
3) test_header_assente_genera_uuid
"""

from unittest import TestCase
from uuid import UUID

from django.http import HttpResponse
from django.test import RequestFactory

from apps.core.middleware.request_context_middleware import RequestContextMiddleware


# Scopo: Passa una richiesta dal middleware e ritorna il request_id assegnato
#        e quello rimandato nella risposta.
def _giro(**headers: str) -> tuple[str, str]:
    request = RequestFactory().get("/api/v1/test/", headers=headers)
    mw = RequestContextMiddleware(lambda r: HttpResponse())
    mw.process_request(request)
    response = mw.process_response(request, HttpResponse())
    return request.request_id, response["X-Request-ID"]


class RequestIdDalClientTests(TestCase):

    # Scopo: Un UUID valido si tiene (in forma canonica): e' la correlazione
    # che il client ha chiesto.
    def test_uuid_del_client_accettato_in_forma_canonica(self):
        assegnato, rimandato = _giro(**{"X-Request-ID": "  6F9619FF-8B86-D011-B42D-00C04FC964FF "})
        self.assertEqual(assegnato, "6f9619ff-8b86-d011-b42d-00c04fc964ff")
        self.assertEqual(rimandato, assegnato)

    # Scopo: Un valore che non e' un UUID finirebbe in colonne `uuid` e ne
    # farebbe fallire l'INSERT (audit perso): si sostituisce, senza
    # rifiutare la richiesta, e non si rimanda indietro.
    def test_valore_non_uuid_sostituito(self):
        for valore in ("abc", "x" * 5000, "1; DROP TABLE t"):
            with self.subTest(valore=valore[:20]):
                assegnato, rimandato = _giro(**{"X-Request-ID": valore})
                self.assertNotEqual(assegnato, valore)
                UUID(assegnato)  # solleva se non e' un UUID
                self.assertEqual(rimandato, assegnato)

    # Scopo: Senza header se ne genera uno.
    def test_header_assente_genera_uuid(self):
        assegnato, _ = _giro()
        UUID(assegnato)
