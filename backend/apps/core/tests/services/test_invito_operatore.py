# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
3) InvitoTests.test_non_invitabile_solleva_col_codice_del_db
4) InvitoTests.test_reinvio_e_la_stessa_strada
5) InvitoTests.test_piu_vesti_spente_rifiuta
6) InvitoTests.test_nessuna_veste_spenta_rifiuta
7) InvitoTests.test_email_non_partita_risponde_inviato_false (F-3)
8) InvitoTests.test_invito_riapre_il_rapporto_nella_transazione_dell_emissione (D-3)
9) InvitoTests.test_non_invitabile_non_riapre_il_rapporto (D-3)
10) InvitoTests.test_operatore_non_trovato_404 — UTENTE_NON_TROVATO e SENZA_VESTE_OPERATORE → E_AMM_OPERATORE_NOT_FOUND (E-4)
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.invito_veste import PORTA_OPERATORE, EmissioneInvito
from apps.core.services.service_errors import ServiceError

_SVC_PATH = "apps.anagrafiche.services.invito_operatore_service"


def _servizio(*, invitabile=True, reason=None, reason_key=None, vesti=None):
    """Scopo: Il service con repository e BB finti. `vesti` = le OPERATORE."""
    with patch(f"{_SVC_PATH}.AuthRepository", autospec=True) as MockAuth, \
         patch(f"{_SVC_PATH}.RisorseUmaneCoreRepository", autospec=True) as MockRu, \
         patch(f"{_SVC_PATH}.InvitoVeste") as MockInvito:
        from apps.anagrafiche.services.invito_operatore_service import InvitoOperatoreService
        svc = InvitoOperatoreService()
    # Operatore mai attivato: il rapporto e' gia' aperto, niente da riaprire.
    MockRu.return_value.riapri_risorsa_umana_della_veste.return_value = 0
    auth = MockAuth.return_value
    invito = MockInvito.return_value
    auth.find_identita_per_ruolo.return_value = (
        vesti if vesti is not None else [{"id": 700, "attivo": False}]
    )
    auth.get_unita_organizzativa_id.return_value = 5
    invito.emetti.return_value = EmissioneInvito(token="tok", is_cross=False)
    # Esplicito: un MagicMock e' «vero» per caso, e `inviato` lo copierebbe.
    invito.spedisci.return_value = True
    svc._check_invitabile = MagicMock(return_value={
        "invitabile": invitabile, "reason": reason, "reason_key": reason_key,
        "email": "mario@test.com",
    })
    auth.get_nomi_credenziale.return_value = {
        "first_name": "Mario", "last_name": "Rossi", "username": "mrossi",
    }
    return svc, auth, invito


class InvitoTests(TestCase):

    def setUp(self):
        # La transazione dell'emissione (riapertura del rapporto + token):
        # finta, il test non parla col DB.
        patcher = patch(f"{_SVC_PATH}.transaction")
        self.mock_tx = patcher.start()
        self.addCleanup(patcher.stop)

    # Scopo: ⭐ D-3 (2026-10-04) — l'invito e' la strada per riaccendere un
    # operatore spento: riapre il rapporto (risorsa umana) DENTRO la
    # transazione dell'emissione, prima del token; la veste resta al BB, che
    # non la accende.
    def test_invito_riapre_il_rapporto_nella_transazione_dell_emissione(self):
        svc, _, invito = _servizio()
        ordine = MagicMock()
        ordine.attach_mock(self.mock_tx.atomic.return_value.__enter__, "entra")
        ordine.attach_mock(svc._ru_repo.riapri_risorsa_umana_della_veste, "riapri")
        ordine.attach_mock(invito.emetti, "emetti")
        ordine.attach_mock(self.mock_tx.atomic.return_value.__exit__, "esci")
        svc.invia_invito(42, invitato_da_user_id=1)

        nomi = [c[0] for c in ordine.mock_calls]
        self.assertEqual(nomi, ["entra", "riapri", "emetti", "esci"])
        # Il rapporto della veste che si sta invitando, non un secondo selettore.
        svc._ru_repo.riapri_risorsa_umana_della_veste.assert_called_once_with(700)

    # Scopo: Un operatore non invitabile non riapre niente: il check viene prima.
    def test_non_invitabile_non_riapre_il_rapporto(self):
        svc, _, _ = _servizio(invitabile=False, reason="VESTE_GIA_ATTIVA")
        with self.assertRaises(ServiceError):
            svc.invia_invito(42, invitato_da_user_id=1)
        svc._ru_repo.riapri_risorsa_umana_della_veste.assert_not_called()

    # Scopo: Invito sulla veste OPERATORE spenta: emissione e spedizione del
    # BB con la porta OPERATORE, email mascherata nella risposta.
    def test_invia_invito_emette_sulla_veste_spenta(self):
        svc, _, invito = _servizio()
        result = svc.invia_invito(42, invitato_da_user_id=1)

        self.assertIs(result["inviato"], True)
        self.assertEqual(result["email"], "m***@test.com")
        kwargs = invito.emetti.call_args.kwargs
        self.assertIs(invito.emetti.call_args.args[0], PORTA_OPERATORE)
        self.assertEqual(kwargs["identita_id"], 700)
        self.assertEqual(kwargs["ruolo_applicativo"], "OPERATORE")
        spedisci = invito.spedisci.call_args.kwargs
        self.assertEqual(spedisci["destinatario"], "mario@test.com")
        # Lo username entra fra le variabili (D-9, B-15): senza valore il
        # template mostrerebbe «{{username}}» letterale.
        self.assertEqual(
            spedisci["variabili"],
            {"nome": "Mario", "cognome": "Rossi", "username": "mrossi"},
        )
        self.assertEqual(spedisci["unita_organizzativa_id"], 5)

    # Scopo: ⭐ F-3 — `inviato` e' l'esito della MAIL: se non e' partita la
    # risposta lo dice (il token c'e' comunque, non si solleva), invece di
    # dichiarare inviato un invito che la persona non ricevera'.
    def test_email_non_partita_risponde_inviato_false(self):
        svc, _, invito = _servizio()
        invito.spedisci.return_value = False
        result = svc.invia_invito(42, invitato_da_user_id=1)
        self.assertIs(result["inviato"], False)
        invito.emetti.assert_called_once()

    # Scopo: A-1 — l'invito non sovrascrive la password e non accende il
    # cambio obbligatorio: la credenziale puo' essere anche di un cliente.
    def test_invito_non_tocca_la_password(self):
        svc, auth, _ = _servizio()
        with patch(f"{_SVC_PATH}.connection") as mock_conn:
            svc.invia_invito(42, invitato_da_user_id=1)
        mock_conn.cursor.assert_not_called()
        auth.set_deve_cambiare_password.assert_not_called()

    # Scopo: Il rifiuto porta il messaggio del catalogo e, nel contesto, il
    # codice e la chiave del DB (§16: il DB non manda piu' una frase), e non
    # si emette niente.
    def test_non_invitabile_solleva_col_codice_del_db(self):
        svc, _, invito = _servizio(
            invitabile=False,
            reason="VESTE_GIA_ATTIVA",
            reason_key="amministrazione.operatori.invito_reason.veste_gia_attiva",
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.invia_invito(42, invitato_da_user_id=1)
        self.assertEqual(ctx.exception.code, "E_INVITO_OPERATORE")
        self.assertEqual(ctx.exception.message, "Operatore non invitabile.")
        self.assertEqual(ctx.exception.context["reason"], "VESTE_GIA_ATTIVA")
        self.assertEqual(
            ctx.exception.context["reason_key"],
            "amministrazione.operatori.invito_reason.veste_gia_attiva",
        )
        invito.emetti.assert_not_called()

    # Scopo: E-4 — un id che non nomina un operatore (credenziale inesistente,
    # o senza veste OPERATORE) e' un 404, non il 400 del rifiuto d'invito.
    def test_operatore_non_trovato_404(self):
        for reason in ("UTENTE_NON_TROVATO", "SENZA_VESTE_OPERATORE"):
            with self.subTest(reason=reason):
                svc, _, invito = _servizio(invitabile=False, reason=reason)
                with self.assertRaises(ServiceError) as ctx:
                    svc.invia_invito(42, invitato_da_user_id=1)
                self.assertEqual(ctx.exception.code, "E_AMM_OPERATORE_NOT_FOUND")
                self.assertEqual(ctx.exception.context["reason"], reason)
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
