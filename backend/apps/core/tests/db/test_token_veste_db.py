# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test su DB reale dei token monouso di una VESTE (L-3 del
#        piano-be-fe-accessi-credenziale-e-vesti). Due vesti della stessa
#        porta (cliente e fornitore portale della stessa persona) condividono i
#        tipi di token: l'invito dell'una non deve spegnere quello dell'altra.
#        ⛔ Fino al 2026-09-25 `TokenRepository.create` invalidava per tipo e
#        credenziale, e la regola «per veste» del building block era vera solo
#        nei test con i mock. Qui i token si fabbricano sul DB vero, dentro una
#        transazione annullata; la credenziale e' finta, le vesti sono solo
#        l'`identita_id` nel meta (il repository non ne guarda altro).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) TokenVesteDbTests.test_create_non_spegne_il_token_di_un_altra_veste
2) TokenVesteDbTests.test_invalida_la_veste_e_non_l_altra
3) TokenVesteDbTests.test_emissione_bb_spegne_solo_il_link_precedente_della_veste
4) ResetPasswordDbTests.test_vale_solo_l_ultimo_link
5) ResetPasswordDbTests.test_reset_chiesto_con_l_email_senza_maiuscole (L-4)
"""

from __future__ import annotations

import unittest
import uuid
from unittest.mock import patch

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.db import connection
from django.test import override_settings
from rest_framework.test import APIClient

from apps.core.api.throttling import ConfermaTokenRateThrottle, PasswordResetRateThrottle
from apps.core.services.invito_veste import PORTA_PORTALE, InvitoVeste
from apps.core.services.token_service import TokenService
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto

# Due vesti finte della stessa porta: bastano due identita_id distinti.
_VESTE_CLIENTE = 900_001
_VESTE_FORNITORE = 900_002


# Scopo: Credenziale fabbricata senza password vera (come quella di un invito).
def _credenziale() -> User:
    nome = f"test_token_{uuid.uuid4().hex[:12]}"
    return User.objects.create(
        username=nome, email=f"{nome}@example.invalid", password=make_password(None),
    )


class _TransazioneAnnullata(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)


class TokenVesteDbTests(_TransazioneAnnullata):
    tokens = TokenService()

    def _crea(self, uid: int, identita_id: int) -> str:
        return self.tokens.create(
            tipo=PORTA_PORTALE.token_invito, auth_user_id=uid, scadenza_ore=1,
            meta={"identita_id": identita_id},
        )

    def _vale(self, token: str) -> bool:
        return self.tokens.validate(token, PORTA_PORTALE.token_invito) is not None

    # Scopo: Il token della seconda veste non spegne quello della prima.
    def test_create_non_spegne_il_token_di_un_altra_veste(self):
        uid = _credenziale().id
        cliente = self._crea(uid, _VESTE_CLIENTE)
        fornitore = self._crea(uid, _VESTE_FORNITORE)
        self.assertTrue(self._vale(cliente))
        self.assertTrue(self._vale(fornitore))

    # Scopo: L'invalidazione per veste spegne quella veste e non l'altra.
    def test_invalida_la_veste_e_non_l_altra(self):
        uid = _credenziale().id
        cliente = self._crea(uid, _VESTE_CLIENTE)
        fornitore = self._crea(uid, _VESTE_FORNITORE)
        n = self.tokens.invalidate_for_identita(PORTA_PORTALE.token_tipi, uid, _VESTE_CLIENTE)
        self.assertEqual(n, 1)
        self.assertFalse(self._vale(cliente))
        self.assertTrue(self._vale(fornitore))

    # Scopo: Il BB emette sulla veste: il link precedente di QUELLA veste si
    # spegne (uno vivo per veste), quello dell'altra veste resta.
    def test_emissione_bb_spegne_solo_il_link_precedente_della_veste(self):
        uid = _credenziale().id
        fornitore = self._crea(uid, _VESTE_FORNITORE)
        invito = InvitoVeste()
        primo = invito.emetti(
            PORTA_PORTALE, auth_user_id=uid, identita_id=_VESTE_CLIENTE,
            ruolo_applicativo="CLIENTE_PORTALE", invitato_da_user_id=uid,
        )
        secondo = invito.emetti(
            PORTA_PORTALE, auth_user_id=uid, identita_id=_VESTE_CLIENTE,
            ruolo_applicativo="CLIENTE_PORTALE", invitato_da_user_id=uid,
        )
        self.assertFalse(self._vale(primo.token))
        self.assertTrue(self._vale(secondo.token))
        self.assertTrue(self._vale(fornitore))


# Il reset password si appoggiava all'invalidazione dentro `create`: ora la fa
# da se', e qui si prova che il link precedente smette di valere.
class ResetPasswordDbTests(_TransazioneAnnullata):

    def setUp(self) -> None:
        super().setUp()
        self.enterContext(override_settings(TRUSTED_PROXY_COUNT=0, REQUEST_LOG_ENABLED=False))
        self.enterContext(patch.object(PasswordResetRateThrottle, "allow_request", return_value=True))
        self.enterContext(patch.object(ConfermaTokenRateThrottle, "allow_request", return_value=True))
        self.email = self.enterContext(
            patch("apps.core.api.password_reset_views._email_service")
        )

    def _chiedi(self, identificativo: str) -> str:
        r = APIClient().post(
            "/api/v1/auth/password-reset-request/", {"identificativo": identificativo}, format="json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        link = self.email.send_email.call_args.kwargs["variabili"]["link"]
        return link.rstrip("/").rsplit("/", 1)[1]

    def test_vale_solo_l_ultimo_link(self):
        utente = _credenziale()
        primo = self._chiedi(utente.username)
        secondo = self._chiedi(utente.username)
        svc = TokenService()
        self.assertIsNone(svc.validate(primo, "RESET_PASSWORD"))
        self.assertIsNotNone(svc.validate(secondo, "RESET_PASSWORD"))
        with connection.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM config.token_monouso "
                "WHERE auth_user_id = %s AND tipo = 'RESET_PASSWORD' AND NOT utilizzato",
                [utente.id],
            )
            self.assertEqual(cur.fetchone()[0], 1)

    # Scopo: L-4, D-9: il reset si chiede anche con l'email, senza badare alle
    # maiuscole (la regola del DB, `fn_get_auth_user_id_for_email`), e il link
    # e' della credenziale di quell'email.
    def test_reset_chiesto_con_l_email_senza_maiuscole(self):
        utente = _credenziale()
        token = self._chiedi(f"  {utente.email.upper()} ")
        self.assertEqual(self.email.send_email.call_args.kwargs["destinatario"], utente.email)
        trovato = TokenService().validate(token, "RESET_PASSWORD")
        self.assertIsNotNone(trovato)
        assert trovato is not None
        self.assertEqual(trovato[0], utente.id)
