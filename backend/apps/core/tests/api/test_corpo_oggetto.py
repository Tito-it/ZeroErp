# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del BB `corpo_oggetto` (F-9): il corpo di una richiesta DRF e'
#        un oggetto, o un 400 E_VALIDATION_INPUT nell'envelope — mai un 500,
#        mai un `{}` al posto del corpo sbagliato.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_oggetto_passa_com_e
2) test_form_passa
3) test_lista_rifiutata
4) test_lista_di_coppie_rifiutata
5) test_json_illeggibile_rifiutato
6) test_logout_con_lista_e_un_400_nell_envelope
"""

from unittest import TestCase

from rest_framework.parsers import FormParser, JSONParser
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from apps.core.api.payload_validators import corpo_oggetto
from apps.core.services.service_errors import ServiceError


# Scopo: Una Request DRF col corpo dato (JSON grezzo o form).
def _richiesta(corpo: str, content_type: str = "application/json") -> Request:
    grezza = APIRequestFactory().post("/api/v1/x/", corpo, content_type=content_type)
    return Request(grezza, parsers=[JSONParser(), FormParser()])


class CorpoOggettoTests(TestCase):

    def test_oggetto_passa_com_e(self):
        self.assertEqual(corpo_oggetto(_richiesta('{"a": 1}')), {"a": 1})

    # Scopo: Un form (`QueryDict`) e' un dict: non si rifiuta.
    def test_form_passa(self):
        corpo = corpo_oggetto(_richiesta("a=1", "application/x-www-form-urlencoded"))
        self.assertEqual(corpo.get("a"), "1")

    def test_lista_rifiutata(self):
        with self.assertRaises(ServiceError) as ctx:
            corpo_oggetto(_richiesta("[1, 2]"))
        self.assertEqual(ctx.exception.code, "E_VALIDATION_INPUT")
        self.assertIn("oggetto JSON", ctx.exception.message)

    # Scopo: `dict([["refresh", "x"]])` diventava un oggetto, in silenzio.
    def test_lista_di_coppie_rifiutata(self):
        with self.assertRaises(ServiceError):
            corpo_oggetto(_richiesta('[["refresh", "x"]]'))

    def test_json_illeggibile_rifiutato(self):
        with self.assertRaises(ServiceError) as ctx:
            corpo_oggetto(_richiesta("{non json"))
        self.assertEqual(ctx.exception.code, "E_VALIDATION_INPUT")
        self.assertIn("JSON valido", ctx.exception.message)


class LogoutCorpoListaTests(TestCase):

    # Scopo: F-9 dal percorso vero: logout (autenticato) con una lista nel
    # corpo. Era un 500 (`request.data.get` su una lista).
    def test_logout_con_lista_e_un_400_nell_envelope(self):
        from unittest.mock import MagicMock

        from apps.core.api.error_responses import exception_to_error_response
        from apps.core.api.logout_view import LogoutView

        request = _richiesta('[{"refresh": "x"}]')
        request.user = MagicMock(id=1)
        with self.assertRaises(ServiceError) as ctx:
            LogoutView().post(request)
        risposta = exception_to_error_response(ctx.exception)
        self.assertEqual(risposta.status_code, 400)
        self.assertIn(b"E_VALIDATION_INPUT", risposta.content)
