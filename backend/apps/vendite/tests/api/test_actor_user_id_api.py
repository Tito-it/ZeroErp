# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le scritture passano al service l'utente che AGISCE
#        (`get_actor_user_id`), le liste il PERIMETRO (`get_scope_user_id`).
#        Mock service + JWT mockata. Nessun DB.
#
#        Il difetto (2026-10-07): le view di crea/modifica eccezione
#        dell'offerta e di crea riga del contratto passavano al gate prezzi
#        `get_scope_user_id`, che per il superuser vale `None` («nessun
#        limite di perimetro»). Il gate legge `None` come «chiamata senza
#        utente» e blocca: il super admin riceveva
#        E_PRICING_OVERRIDE_NON_AUTORIZZATO su ogni prezzo manuale.
#        ⚠️ I test API col `Mock()` nudo non lo vedevano: non guardavano
#        `auth_user_id`, e un `Mock()` e' superuser per caso (attributo truthy).
#        Qui l'utente e' dichiarato, e il superuser e' il caso che conta.
#        ⚠️ Lo stesso difetto c'era su crea riga di ordine e DDT (gate L1 degli
#        override dei componenti) e sulle preview componenti di contratto e
#        offerta, che risolvevano l'emittente dell'operatore con lo scope
#        mentre crea eccezione e preview del preventivo usavano l'attore.
#        Senza errore, invece, nei form-defaults e nelle note: lo scope del
#        superuser faceva saltare le sue preferenze personali (parametri per
#        utente, emittente dell'utente per la valuta), e valevano le generali.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) helper: get_actor_user_id da' l'id anche al superuser; None da anonimo
2) helper: get_scope_user_id resta None per il superuser (il perimetro)
3) offerta, crea eccezione: il service riceve l'id del superuser
4) offerta, modifica eccezione: il service riceve l'id del superuser
5) contratto, crea riga: il service riceve l'id del superuser
6) contratto, modifica riga: il service riceve l'id del superuser
7) ordine, modifica riga: il service riceve l'id del superuser
8) DDT, modifica riga: il service riceve l'id del superuser
9) contratti, lista: il perimetro del superuser resta None
10) ordine, crea riga: il service riceve l'id del superuser (gate L1 componenti)
11) DDT, crea riga: il service riceve l'id del superuser (gate L1 componenti)
12) contratto, preview componenti: l'id del superuser (emittente operatore)
13) offerta, preview componenti: l'id del superuser (come crea eccezione)
14) contratto, form-defaults: l'id del superuser (preferenze personali)
15) contratto, crea nota: l'id del superuser (stile e lingua personali)
"""

import json
from unittest import TestCase
from unittest.mock import Mock, patch

from django.core.cache import cache

from apps.core.tests._helpers.jwt_mock import ClientApi

from apps.core.api.endpoint_helpers import get_actor_user_id, get_scope_user_id
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_BASE = "/api/v1/vendite/"
_USER_ID = 7


def _utente(*, superuser: bool, autenticato: bool = True) -> Mock:
    return Mock(id=_USER_ID, is_superuser=superuser, is_authenticated=autenticato)


def _superuser_auth() -> tuple[Mock, None]:
    return (_utente(superuser=True), None)


class HelperUtenteTests(TestCase):
    # Scopo: l'attore e' l'utente, superuser compreso; anonimo = None.
    def test_actor_superuser_e_anonimo(self):
        self.assertEqual(get_actor_user_id(Mock(user=_utente(superuser=True))), _USER_ID)
        self.assertEqual(get_actor_user_id(Mock(user=_utente(superuser=False))), _USER_ID)
        self.assertIsNone(
            get_actor_user_id(Mock(user=_utente(superuser=False, autenticato=False))),
        )

    # Scopo: il perimetro del superuser resta «nessun limite».
    def test_scope_superuser_resta_none(self):
        self.assertIsNone(get_scope_user_id(Mock(user=_utente(superuser=True))))
        self.assertEqual(get_scope_user_id(Mock(user=_utente(superuser=False))), _USER_ID)


class ScrittureAttoreApiTests(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = ClientApi()

    def _send(self, method: str, url: str, body: dict) -> None:
        resp = getattr(self.client, method)(
            _BASE + url, data=json.dumps(body), content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)

    @patch(_AUTH, return_value=_superuser_auth())
    @patch("apps.vendite.api.views_offerte.OfferteService")
    def test_offerta_crea_eccezione(self, svc_cls, _auth):
        svc_cls.return_value.crea_eccezione.return_value = {"id": 1}
        self._send("post", "offerte/1/eccezioni/", {"articolo_id": "a", "tipo_eccezione": "OVERRIDE"})
        self.assertEqual(
            svc_cls.return_value.crea_eccezione.call_args.kwargs["auth_user_id"], _USER_ID,
        )

    @patch(_AUTH, return_value=_superuser_auth())
    @patch("apps.vendite.api.views_offerte.OfferteService")
    def test_offerta_modifica_eccezione(self, svc_cls, _auth):
        svc_cls.return_value.aggiorna_eccezione.return_value = {"id": 1}
        self._send("patch", "offerte/1/eccezioni/2/", {"prezzo_unitario": "10"})
        self.assertEqual(
            svc_cls.return_value.aggiorna_eccezione.call_args.kwargs["auth_user_id"], _USER_ID,
        )

    @patch(_AUTH, return_value=_superuser_auth())
    @patch("apps.vendite.api.views_contratti.ContrattiService")
    def test_contratto_crea_riga(self, svc_cls, _auth):
        svc_cls.return_value.create_riga.return_value = {"id": 1}
        self._send("post", "contratti/1/righe/", {"articolo_id": "a", "prezzo_unitario": "10"})
        self.assertEqual(
            svc_cls.return_value.create_riga.call_args.kwargs["auth_user_id"], _USER_ID,
        )

    @patch(_AUTH, return_value=_superuser_auth())
    @patch("apps.vendite.api.views_contratti.ContrattiService")
    def test_contratto_modifica_riga(self, svc_cls, _auth):
        svc_cls.return_value.update_riga.return_value = {"id": 1}
        self._send("patch", "contratti/1/righe/2/", {"prezzo_unitario": "10"})
        self.assertEqual(
            svc_cls.return_value.update_riga.call_args.kwargs["auth_user_id"], _USER_ID,
        )

    @patch(_AUTH, return_value=_superuser_auth())
    @patch("apps.vendite.api.views_ordini.ordini_service")
    def test_ordine_modifica_riga(self, svc, _auth):
        svc.aggiorna_riga.return_value = {"riga_id": 2}
        self._send("patch", "ordini/1/righe/2/", {"quantita": "1"})
        self.assertEqual(svc.aggiorna_riga.call_args.kwargs["auth_user_id"], _USER_ID)

    @patch(_AUTH, return_value=_superuser_auth())
    @patch("apps.vendite.api.views_ddt.ddt_service")
    def test_ddt_modifica_riga(self, svc, _auth):
        svc.aggiorna_riga.return_value = {"riga_id": 2}
        self._send("patch", "ddt/1/righe/2/", {"quantita": "1"})
        self.assertEqual(svc.aggiorna_riga.call_args.kwargs["auth_user_id"], _USER_ID)

    # Scopo: le LISTE restano sul perimetro: per il superuser None.
    @patch(_AUTH, return_value=_superuser_auth())
    @patch("apps.vendite.api.views_contratti.ContrattiService")
    def test_contratti_lista_perimetro_superuser(self, svc_cls, _auth):
        svc_cls.return_value.list_contratti.return_value = ([], 0)
        resp = self.client.get(_BASE + "contratti/")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertIsNone(svc_cls.return_value.list_contratti.call_args.kwargs["auth_user_id"])

    @patch(_AUTH, return_value=_superuser_auth())
    @patch("apps.vendite.api.views_ordini.ordini_service")
    def test_ordine_crea_riga(self, svc, _auth):
        svc.gestisci_riga.return_value = {"riga_id": 2}
        self._send("post", "ordini/1/righe/", {"articolo_id": "a", "componenti_overrides": {"1": "5"}})
        self.assertEqual(svc.gestisci_riga.call_args.kwargs["auth_user_id"], _USER_ID)

    @patch(_AUTH, return_value=_superuser_auth())
    @patch("apps.vendite.api.views_ddt.ddt_service")
    def test_ddt_crea_riga(self, svc, _auth):
        svc.gestisci_riga.return_value = {"riga_id": 2}
        self._send("post", "ddt/1/righe/", {"articolo_id": "a", "componenti_overrides": {"1": "5"}})
        self.assertEqual(svc.gestisci_riga.call_args.kwargs["auth_user_id"], _USER_ID)

    @patch(_AUTH, return_value=_superuser_auth())
    @patch("apps.vendite.api.views_contratti.ContrattiService")
    def test_contratto_preview_componenti(self, svc_cls, _auth):
        svc_cls.return_value.preview_componenti_riga.return_value = []
        self._send("post", "contratti/1/righe/preview-componenti/", {"articolo_id": "a"})
        self.assertEqual(
            svc_cls.return_value.preview_componenti_riga.call_args.kwargs["auth_user_id"], _USER_ID,
        )

    @patch(_AUTH, return_value=_superuser_auth())
    @patch("apps.vendite.api.views_offerte.OfferteService")
    def test_offerta_preview_componenti(self, svc_cls, _auth):
        svc_cls.return_value.preview_componenti_eccezione.return_value = []
        self._send("post", "offerte/1/eccezioni/preview-componenti/", {"articolo_id": "a"})
        self.assertEqual(
            svc_cls.return_value.preview_componenti_eccezione.call_args.kwargs["auth_user_id"],
            _USER_ID,
        )

    # Scopo: le preferenze personali sono dell'utente che agisce, superuser compreso.
    @patch(_AUTH, return_value=_superuser_auth())
    @patch("apps.vendite.api.views_form_defaults.fn_get_contratto_form_defaults")
    def test_contratto_form_defaults(self, fn, _auth):
        fn.return_value = {}
        resp = self.client.get(_BASE + "contratti/form-defaults/")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(fn.call_args.kwargs["auth_user_id"], _USER_ID)

    @patch(_AUTH, return_value=_superuser_auth())
    @patch("apps.vendite.api.note_views.PartitionedNoteService")
    def test_contratto_crea_nota(self, svc_cls, _auth):
        svc_cls.return_value.crea_nota.return_value = {"id": 1}
        resp = self.client.post(
            _BASE + "contratti/1/note/", data=json.dumps({"testo": "x"}),
            content_type="application/json", headers={"Idempotency-Key": "actor-nota-1"},
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(svc_cls.return_value.crea_nota.call_args.kwargs["auth_user_id"], _USER_ID)
