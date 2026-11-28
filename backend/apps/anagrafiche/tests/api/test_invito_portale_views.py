# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari delle tre view di disattivazione della veste di un
#        referente (`views_invito_portale`): il corpo porta `identita_id`, la
#        view lo passa al service col tipo dell'endpoint, e senza la chiave
#        risponde 400 `E_VALIDATION_INPUT` senza toccare il service. Mock del
#        service. Compatibile CI.
# Note: ⭐ Nato il 2026-11-28 (giro 4 del brief-db-accessi-area-clienti, D-M7):
#       `identita_id` e' la chiave nuova del contratto fra il pannello FE
#       (`portaleAdminApi.disattiva*`) e il BE. I test del service la ricevono
#       gia' come argomento: il punto che la traduce dal corpo si prova qui.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) DisattivaVesteViewsTests.test_identita_id_dal_corpo_al_service — le tre view, col tipo dell'endpoint
2) DisattivaVesteViewsTests.test_senza_identita_id_400 — le tre view, il service non si chiama
"""

import json
from unittest import TestCase
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import RequestFactory

_SERVICE = "apps.anagrafiche.api.views_invito_portale.InvitoPortaleService"


class DisattivaVesteViewsTests(TestCase):

    def _post(self, payload: dict):
        request = RequestFactory().post(
            "/api/v1/anagrafiche/x/disattiva/",
            data=json.dumps(payload).encode("utf-8"),
            content_type="application/json",
        )
        # Un `User` vero, non salvato: la view legge chi agisce dal BB
        # `utente_autenticato`, che vuole l'utente autenticato col suo tipo.
        request.user = User(id=42)
        return request

    # Scopo: (view, argomenti dell'URL, metodo del service, kwargs attesi
    #        oltre a `identita_id` e `disattivato_da_user_id`).
    def _casi(self):
        from apps.anagrafiche.api.views_invito_portale import (
            ClientiDisattivaPortaleView,
            ClientiDisattivaShopView,
            FornitoriDisattivaPortaleView,
        )
        return [
            (ClientiDisattivaPortaleView, {"cliente_id": 5}, "disattiva_veste_cliente",
             {"cliente_id": 5, "ruolo_applicativo": "CLIENTE_PORTALE"}),
            (ClientiDisattivaShopView, {"cliente_id": 5}, "disattiva_veste_cliente",
             {"cliente_id": 5, "ruolo_applicativo": "SHOP_CUSTOMER"}),
            (FornitoriDisattivaPortaleView, {"fornitore_id": 9}, "disattiva_veste_fornitore",
             {"fornitore_id": 9}),
        ]

    def test_identita_id_dal_corpo_al_service(self):
        for view_cls, url_kwargs, metodo, attesi in self._casi():
            with self.subTest(view=view_cls.__name__), patch(_SERVICE) as MockSvc:
                getattr(MockSvc.return_value, metodo).return_value = {
                    "disattivato": True, "stato": "REVOCATA", "identita_id": 77,
                }
                response = view_cls().post(self._post({"identita_id": 77}), **url_kwargs)
                self.assertEqual(response.status_code, 200)
                getattr(MockSvc.return_value, metodo).assert_called_once_with(
                    **attesi, identita_id=77, disattivato_da_user_id=42,
                )

    def test_senza_identita_id_400(self):
        for view_cls, url_kwargs, metodo, _attesi in self._casi():
            with self.subTest(view=view_cls.__name__), patch(_SERVICE) as MockSvc:
                response = view_cls().post(self._post({}), **url_kwargs)
                self.assertEqual(response.status_code, 400)
                body = json.loads(response.content)
                self.assertEqual(body["error"]["code"], "E_VALIDATION_INPUT")
                getattr(MockSvc.return_value, metodo).assert_not_called()
