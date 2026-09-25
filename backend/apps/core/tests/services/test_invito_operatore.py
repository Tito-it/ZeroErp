# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per InvitoOperatoreService: la parte dell'operatore
#        (check del DB, veste spenta da invitare) e la consegna al building
#        block `InvitoVeste` (emissione, reinvio, email). L'attivazione e'
#        del BB: test_invito_veste. Mock DB e BB, compatibile CI.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) InvitoTests.test_invia_invito_emette_sulla_veste_spenta
2) InvitoTests.test_invito_non_tocca_la_password
3) InvitoTests.test_non_invitabile_solleva_col_motivo_del_db
4) InvitoTests.test_reinvio_e_la_stessa_strada
5) InvitoTests.test_piu_vesti_spente_rifiuta
6) InvitoTests.test_nessuna_veste_spenta_rifiuta
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.invito_veste import PORTA_OPERATORE, EmissioneInvito
from apps.core.services.service_errors import ServiceError

_SVC_PATH = "apps.anagrafiche.services.invito_operatore_service"


def _servizio(*, invitabile=True, motivo=None, vesti=None):
    """Scopo: Il service con repository e BB finti. `vesti` = le OPERATORE."""
    with patch(f"{_SVC_PATH}.AuthRepository") as MockAuth, \
         patch(f"{_SVC_PATH}.InvitoVeste") as MockInvito:
        from apps.anagrafiche.services.invito_operatore_service import InvitoOperatoreService
        svc = InvitoOperatoreService()
    auth = MockAuth.return_value
    invito = MockInvito.return_value
    auth.find_identita_per_ruolo.return_value = (
        vesti if vesti is not None else [{"id": 700, "attivo": False}]
    )
    auth.get_unita_organizzativa_id.return_value = 5
    invito.emetti.return_value = EmissioneInvito(token="tok", is_cross=False)
    svc._check_invitabile = MagicMock(return_value={
        "invitabile": invitabile, "motivo": motivo, "email": "mario@test.com",
    })
    auth.get_nomi_credenziale.return_value = {
        "first_name": "Mario", "last_name": "Rossi", "username": "mrossi",
    }
    return svc, auth, invito


class InvitoTests(TestCase):

    # Scopo: Invito sulla veste OPERATORE spenta: emissione e spedizione del
    # BB con la porta OPERATORE, email mascherata nella risposta.
    def test_invia_invito_emette_sulla_veste_spenta(self):
        svc, _, invito = _servizio()
        result = svc.invia_invito(42, invitato_da_user_id=1)

        self.assertTrue(result["inviato"])
        self.assertEqual(result["email"], "m***@test.com")
        kwargs = invito.emetti.call_args.kwargs
        self.assertIs(invito.emetti.call_args.args[0], PORTA_OPERATORE)
        self.assertEqual(kwargs["identita_id"], 700)
        self.assertEqual(kwargs["ruolo_applicativo"], "OPERATORE")
        spedisci = invito.spedisci.call_args.kwargs
        self.assertEqual(spedisci["destinatario"], "mario@test.com")
        self.assertEqual(spedisci["variabili"], {"nome": "Mario", "cognome": "Rossi"})
        self.assertEqual(spedisci["unita_organizzativa_id"], 5)

    # Scopo: A-1 — l'invito non sovrascrive la password e non accende il
    # cambio obbligatorio: la credenziale puo' essere anche di un cliente.
    def test_invito_non_tocca_la_password(self):
        svc, auth, _ = _servizio()
        with patch(f"{_SVC_PATH}.connection") as mock_conn:
            svc.invia_invito(42, invitato_da_user_id=1)
        mock_conn.cursor.assert_not_called()
        auth.set_deve_cambiare_password.assert_not_called()

    # Scopo: Il motivo del rifiuto e' quello del DB (regola nuova: veste gia'
    # attiva), e non si emette niente.
    def test_non_invitabile_solleva_col_motivo_del_db(self):
        svc, _, invito = _servizio(invitabile=False, motivo="Veste OPERATORE gia' attiva")
        with self.assertRaises(ServiceError) as ctx:
            svc.invia_invito(42, invitato_da_user_id=1)
        self.assertEqual(ctx.exception.code, "E_INVITO_OPERATORE")
        self.assertIn("gia' attiva", ctx.exception.message)
        invito.emetti.assert_not_called()

    # Scopo: A-4 — il reinvio non invalida da se', fuori transazione: passa
    # dalla stessa emissione del BB, che invalida i token della veste dentro
    # la propria transazione.
    def test_reinvio_e_la_stessa_strada(self):
        svc, _, invito = _servizio()
        svc.reinvia_invito(42, invitato_da_user_id=1)
        invito.emetti.assert_called_once()
        self.assertEqual(invito.emetti.call_args.kwargs["identita_id"], 700)
        invito.invalida.assert_not_called()

    # Scopo: Il modello ammette piu' vesti spente: non se ne sceglie una a caso.
    def test_piu_vesti_spente_rifiuta(self):
        svc, _, invito = _servizio(vesti=[{"id": 1, "attivo": False}, {"id": 2, "attivo": False}])
        with self.assertRaises(ServiceError) as ctx:
            svc.invia_invito(42, invitato_da_user_id=1)
        self.assertIn("intervento manuale", ctx.exception.message)
        invito.emetti.assert_not_called()

    def test_nessuna_veste_spenta_rifiuta(self):
        svc, _, invito = _servizio(vesti=[{"id": 1, "attivo": True}])
        with self.assertRaises(ServiceError):
            svc.invia_invito(42, invitato_da_user_id=1)
        invito.emetti.assert_not_called()
