# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari delle view del portale: il cablaggio delle view di
#        attivazione sulla porta PORTALE (il comportamento e' del BB
#        invito_veste, test_invito_veste) e ProfileActivateShopView. Mock DB.
#        Compatibile CI.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1)  CablaggioTests.test_view_sulla_porta_portale
2)  ProfileActivateShopTests.test_fornitore_portale_rifiutato
3)  ProfileActivateShopTests.test_idempotente_se_gia_attiva
4)  ProfileActivateShopTests.test_cerca_la_veste_shop_della_persona_della_sessione — D-M7: per credenziale
"""

import json
from unittest import TestCase
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import RequestFactory


class CablaggioTests(TestCase):

    # Scopo: Le view pubbliche del portale sono il BB sulla porta PORTALE: il
    # comportamento (forma, conferma, veste accesa) si prova una volta in
    # apps/core/tests/services/test_invito_veste.py.
    def test_view_sulla_porta_portale(self):
        from apps.core.services.invito_veste import PORTA_PORTALE
        from apps.portale.api.views import (
            AttivazionePortaleValidateView,
            AttivazionePortaleView,
        )

        self.assertIs(AttivazionePortaleValidateView.porta, PORTA_PORTALE)
        self.assertIs(AttivazionePortaleView.porta, PORTA_PORTALE)


class ProfileActivateShopTests(TestCase):
    """B1 §13.7: cross-veste portale -> shop. Veste FORNITORE_PORTALE
    rifiutata; CLIENTE_PORTALE attiva idempotente."""

    def _post(self, payload: dict, *, user_id: int = 42):
        factory = RequestFactory()
        body = json.dumps(payload).encode("utf-8")
        request = factory.post(
            "/api/v1/portale/profile/activate-shop/",
            data=body,
            content_type="application/json",
        )

        # Un `User` vero, non salvato: la view legge chi agisce dal BB
        # `utente_autenticato`, che vuole l'utente autenticato col suo tipo.
        request.user = User(id=user_id)
        return request

    @patch("apps.portale.api.views.PermissionResolver.get_ruolo_applicativo")
    def test_fornitore_portale_rifiutato(self, mock_ruolo):
        # Solo CLIENTE_PORTALE puo' attivare shop. FORNITORE_PORTALE -> 400.
        from apps.portale.api.views import ProfileActivateShopView
        mock_ruolo.return_value = "FORNITORE_PORTALE"
        response = ProfileActivateShopView().post(self._post({}))
        self.assertEqual(response.status_code, 400)
        body = json.loads(response.content)
        self.assertEqual(body["error"]["code"], "E_ATTIVAZIONE_SHOP_CROSS")
        self.assertIn("clienti portale", body["error"]["message"])

    @patch(
        "apps.portale.api.views.PortaleRepository.find_veste_credenziale", autospec=True
    )
    @patch(
        "apps.portale.api.views.ProfileActivateShopView._read_soggetto_ruolo_from_guc"
    )
    @patch("apps.portale.api.views.PermissionResolver.get_ruolo_applicativo")
    def test_idempotente_se_gia_attiva(
        self, mock_ruolo, mock_guc, mock_find
    ):
        # Identita SHOP_CUSTOMER gia' attiva -> ritorna already_active=True
        # senza side-effect (nessun INSERT/UPDATE).
        from apps.portale.api.views import ProfileActivateShopView
        mock_ruolo.return_value = "CLIENTE_PORTALE"
        mock_guc.return_value = 999
        mock_find.return_value = {
            "identita_id": 555, "auth_user_id": 42, "attivo": True,
        }
        response = ProfileActivateShopView().post(self._post({}))
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertTrue(body["data"]["already_active"])
        self.assertEqual(body["data"]["identita_id"], 555)

    @patch(
        "apps.portale.api.views.PortaleRepository.find_veste_credenziale", autospec=True
    )
    @patch(
        "apps.portale.api.views.ProfileActivateShopView._read_soggetto_ruolo_from_guc"
    )
    @patch("apps.portale.api.views.PermissionResolver.get_ruolo_applicativo")
    def test_cerca_la_veste_shop_della_persona_della_sessione(
        self, mock_ruolo, mock_guc, mock_find
    ):
        # Un cliente ha piu' referenti (D-M7, giro 4 del brief-db-accessi-area-
        # clienti): la veste shop si cerca per (credenziale della sessione,
        # ruolo, tipo). Quella di un altro referente non e' di chi chiede, e
        # non si trova per costruzione. Fino al 2026-11-28 si cercava per
        # (ruolo, tipo), e la veste di un'altra persona fermava il gesto.
        from apps.portale.api.views import ProfileActivateShopView
        mock_ruolo.return_value = "CLIENTE_PORTALE"
        mock_guc.return_value = 999
        mock_find.return_value = {
            "identita_id": 555, "auth_user_id": 42, "attivo": True,
        }
        response = ProfileActivateShopView().post(self._post({}))
        self.assertEqual(response.status_code, 200)
        _repo, auth_user_id, soggetto_ruolo_id, ruolo = mock_find.call_args.args
        self.assertEqual((auth_user_id, soggetto_ruolo_id, ruolo), (42, 999, "SHOP_CUSTOMER"))
