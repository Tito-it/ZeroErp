# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il building block dello SCOPE dei job OPERATORE
#        (`apps.core.services.coda_lavori.scope`): la chiave canonica e la
#        cattura dello scope intero dalla richiesta di chi accoda.
# Note: ⭐ `scope_operatore_da_request` e' nato il 2026-09-15 alla seconda
#        occorrenza (giro di fatturazione dal cockpit, «Esegui ora» dal drawer
#        dei processi). I test del cockpit provano che la view lo USI; qui si
#        prova che cosa PRODUCE, una volta per tutti i consumatori.
#        ⛔ Nessun database: identita' ed emittenti sono mockati sul modulo.
#
# Indice test:
#   1. la chiave canonica: "ALL" per l'admin globale, emittenti ORDINATI altrimenti
#   2. lo scope porta la terna, l'emittente attivo, la whitelist e la scope_key
#   3. senza identita' nel token si rifiuta PRIMA di accodare, col codice della
#      terna incompleta (lo stesso del drenatore)
#   4. l'id e' quello VERO dell'utente, anche per un superuser
# ------------------------------------------------------------

from __future__ import annotations

from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.core.services.coda_lavori.context import E_SCOPE_OPERATORE
from apps.core.services.coda_lavori.scope import (
    SCOPE_KEY_ALL,
    scope_key_da_emittenti,
    scope_operatore_da_request,
)
from apps.core.services.service_errors import ServiceError

_SCOPE = "apps.core.services.coda_lavori.scope"


# Scopo: una richiesta finta con l'utente dato; il token lo simulano i mock
#        degli estrattori (il claim vero non passa da un test unitario).
def _request(user_id: int = 9, username: str = "op9", superuser: bool = False) -> Mock:
    return Mock(user=Mock(id=user_id, username=username, is_superuser=superuser))


class ScopeKeyTests(SimpleTestCase):
    # 1. La chiave e' un DATO canonico: ordinata, cosi' [4, 3] e [3, 4] sono lo
    #    stesso scope — e la dedup dei job vivi lo vede come tale.
    def test_chiave_canonica(self) -> None:
        self.assertEqual(scope_key_da_emittenti(None), SCOPE_KEY_ALL)
        self.assertEqual(scope_key_da_emittenti([4, 3]), "3,4")
        self.assertEqual(scope_key_da_emittenti([]), "")


class ScopeOperatoreDaRequestTests(SimpleTestCase):
    # 2. Il dict completo, nella forma che `CodaLavoriRepository.accoda` e
    #    `operator_identity_context` si aspettano.
    @patch(f"{_SCOPE}.PermissionResolver")
    @patch(f"{_SCOPE}.extract_emittente_attivo_from_request", return_value=3)
    @patch(f"{_SCOPE}.extract_identita_id_from_request", return_value=5)
    def test_scope_completo(self, _ident, _ef, resolver) -> None:
        resolver.get_emittenti_pk_ids.return_value = [4, 3]
        scope = scope_operatore_da_request(_request())
        self.assertEqual(scope, {
            "auth_user_id": 9,
            "username": "op9",
            "identita_id": 5,
            "emittente_attivo_id": 3,
            "emittente_ids": [4, 3],
            "scope_key": "3,4",
        })

    # 3. ⛔ Senza `identita_id` il lavoro nascerebbe e morirebbe nel drenatore
    #    (`operator_identity_context`, stesso codice): si rifiuta QUI, e non si
    #    interroga nemmeno la whitelist.
    @patch(f"{_SCOPE}.PermissionResolver")
    @patch(f"{_SCOPE}.extract_identita_id_from_request", return_value=None)
    def test_senza_identita_rifiuta_prima(self, _ident, resolver) -> None:
        with self.assertRaises(ServiceError) as ctx:
            scope_operatore_da_request(_request())
        self.assertEqual(ctx.exception.code, E_SCOPE_OPERATORE)
        resolver.get_emittenti_pk_ids.assert_not_called()

    # 4. L'admin globale accoda col PROPRIO id (non `get_scope_user_id`, che per
    #    lui e' None) e con la chiave «vede tutto».
    @patch(f"{_SCOPE}.PermissionResolver")
    @patch(f"{_SCOPE}.extract_emittente_attivo_from_request", return_value=None)
    @patch(f"{_SCOPE}.extract_identita_id_from_request", return_value=1)
    def test_superuser_ha_id_vero_e_chiave_all(self, _ident, _ef, resolver) -> None:
        resolver.get_emittenti_pk_ids.return_value = None
        scope = scope_operatore_da_request(_request(user_id=1, username="root", superuser=True))
        self.assertEqual(scope["auth_user_id"], 1)
        self.assertIsNone(scope["emittente_attivo_id"])
        self.assertIsNone(scope["emittente_ids"])
        self.assertEqual(scope["scope_key"], SCOPE_KEY_ALL)
