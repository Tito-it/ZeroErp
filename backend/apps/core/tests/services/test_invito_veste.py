# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari del building block `invito_veste` (L-3): le porte,
#        l'emissione e la spedizione dell'invito, l'attivazione e le due view
#        generiche. ⭐ Sostituiscono le tre copie dei test di attivazione
#        (portale, shop, operatore): il comportamento si prova UNA volta qui,
#        e per ogni porta resta solo il test del cablaggio (quale porta usa
#        la view), nei test dell'app della veste. Mock di repository, token
#        ed email: compatibile CI.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1)  PorteTests.test_ogni_veste_invitabile_ha_la_sua_porta
2)  PorteTests.test_veste_senza_porta_esplode
3)  PorteTests.test_maschera_email
3b) PorteTests.test_nome_visualizzato_* — ragione sociale, poi nome e cognome, poi username
4)  EmettiTests.test_senza_password_vera_token_invito
5)  EmettiTests.test_con_password_vera_token_cross
6)  EmettiTests.test_invalida_la_veste_prima_del_token_nuovo
7)  EmettiTests.test_veste_fuori_dalla_porta_esplode
8)  SpedisciTests.test_email_partita_segna_l_invito
8a) SpedisciTests.test_email_non_partita_non_segna_l_invito (F-3)
8c) SpedisciTests.test_email_con_eccezione_non_solleva_e_non_segna_l_invito
8b) SpedisciTests.test_il_flusso_sceglie_il_template_della_porta
9)  AttivaTests.test_con_password_consuma_imposta_e_accende
10) AttivaTests.test_veste_sparita_solleva_dopo_il_consumo
11) AttivaTests.test_con_password_senza_password_solleva_senza_consumare
12) AttivaTests.test_conferma_diversa_solleva_senza_consumare
13) AttivaTests.test_policy_password_rifiutata_non_brucia_il_token
14) AttivaTests.test_cross_non_tocca_la_password_anche_se_passata
15) AttivaTests.test_token_invito_ma_password_vera_diventa_un_clic
16) AttivaTests.test_token_mancante_solleva
17) AttivaTests.test_token_non_valido_solleva
18) AttivaTests.test_meta_senza_identita_solleva
19) ViewTests.test_validate_dice_se_chiedere_la_password
20) ViewTests.test_validate_token_non_valido
21) ChiudiVesteSpentaTests.test_inviti_sessioni_della_veste_e_cache_a_commit
22) ChiudiVesteSpentaTests.test_chiusura_fallita_propaga_e_non_tocca_la_cache
"""

from __future__ import annotations

import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.core.exceptions import ValidationError as DjangoValidationError
from django.test import override_settings

from apps.core.services.invito_veste import (
    PORTA_OPERATORE,
    PORTA_PORTALE,
    PORTA_SHOP,
    InvitoVeste,
    attiva_veste,
    maschera_email,
    nome_visualizzato,
    porta_della_veste,
)
from apps.core.services.service_errors import ServiceError

_BB = "apps.core.services.invito_veste"


class PorteTests(TestCase):

    # Scopo: Ogni veste che si invita ha una porta, e quella giusta.
    def test_ogni_veste_invitabile_ha_la_sua_porta(self):
        self.assertIs(porta_della_veste("OPERATORE"), PORTA_OPERATORE)
        self.assertIs(porta_della_veste("CLIENTE_PORTALE"), PORTA_PORTALE)
        self.assertIs(porta_della_veste("FORNITORE_PORTALE"), PORTA_PORTALE)
        self.assertIs(porta_della_veste("SHOP_CUSTOMER"), PORTA_SHOP)

    # Scopo: Una veste senza porta e' un errore del chiamante: esplode.
    def test_veste_senza_porta_esplode(self):
        with self.assertRaises(ValueError):
            porta_della_veste("API_CLIENT")

    def test_maschera_email(self):
        self.assertEqual(maschera_email("mario@x.it"), "m***@x.it")
        self.assertEqual(maschera_email("a@x.it"), "*@x.it")
        self.assertEqual(maschera_email(""), "***")

    # Scopo: Il nome delle email: la ragione sociale del soggetto prima di
    #        tutto (decisione di Tid, 2026-10-02), poi i ripieghi.
    def test_nome_visualizzato_ragione_sociale_prima(self):
        repo = MagicMock()
        nomi = {"first_name": "Soggetto1773959838", "last_name": "SmokeTest", "username": "smoke"}
        repo.get_nomi_credenziale.return_value = {**nomi, "ragione_sociale_completa": "Test Smoke"}
        self.assertEqual(nome_visualizzato(7, repo), "Test Smoke")
        repo.get_nomi_credenziale.return_value = {**nomi, "ragione_sociale_completa": ""}
        self.assertEqual(nome_visualizzato(7, repo), "Soggetto1773959838 SmokeTest")

    def test_nome_visualizzato_ripieghi(self):
        repo = MagicMock()
        repo.get_nomi_credenziale.return_value = {
            "first_name": "", "last_name": "", "username": "smoke", "ragione_sociale_completa": "",
        }
        self.assertEqual(nome_visualizzato(7, repo), "smoke")
        repo.get_nomi_credenziale.return_value = None
        self.assertEqual(nome_visualizzato(7, repo), "Amministratore")


def _invito(ha_password: bool) -> tuple[InvitoVeste, MagicMock, MagicMock, MagicMock]:
    repo, tokens, email = MagicMock(), MagicMock(), MagicMock()
    repo.auth_user_ha_password.return_value = ha_password
    tokens.create.return_value = "tok-in-chiaro"
    # `(log_id, partita)`, come il vero: un MagicMock qui non si spacchetta.
    email.send_email.return_value = (1, True)
    return InvitoVeste(auth_repo=repo, token_service=tokens, email_service=email), repo, tokens, email


@patch(f"{_BB}.transaction")
class EmettiTests(TestCase):

    # Scopo: Credenziale senza password vera → token INVITO (la sceglie).
    def test_senza_password_vera_token_invito(self, _tx):
        invito, _, tokens, _ = _invito(ha_password=False)
        esito = invito.emetti(
            PORTA_OPERATORE, auth_user_id=42, identita_id=700,
            ruolo_applicativo="OPERATORE", invitato_da_user_id=1,
        )
        self.assertFalse(esito.is_cross)
        kwargs = tokens.create.call_args.kwargs
        self.assertEqual(kwargs["tipo"], "INVITO_OPERATORE")
        self.assertEqual(kwargs["meta"]["identita_id"], 700)
        self.assertEqual(kwargs["meta"]["ruolo_applicativo"], "OPERATORE")
        tokens.invalidate_for_identita.assert_called_once_with(
            PORTA_OPERATORE.token_tipi, 42, 700,
        )

    # Scopo: Credenziale con password vera → token CROSS (un clic).
    def test_con_password_vera_token_cross(self, _tx):
        invito, _, tokens, _ = _invito(ha_password=True)
        esito = invito.emetti(
            PORTA_PORTALE, auth_user_id=42, identita_id=500,
            ruolo_applicativo="FORNITORE_PORTALE", invitato_da_user_id=1,
            meta={"entita": "Fornitore 9"},
        )
        self.assertTrue(esito.is_cross)
        kwargs = tokens.create.call_args.kwargs
        self.assertEqual(kwargs["tipo"], "ATTIVAZIONE_PORTALE_CROSS")
        self.assertEqual(kwargs["meta"]["entita"], "Fornitore 9")

    # Scopo: Ogni emissione (primo invito o reinvio: sono la stessa cosa)
    # invalida i token della VESTE, non della credenziale, prima del nuovo e
    # dentro la stessa transazione. `TokenService.create` non invalida niente.
    def test_invalida_la_veste_prima_del_token_nuovo(self, mock_tx):
        invito, _, tokens, _ = _invito(ha_password=False)
        ordine = MagicMock()
        mock_tx.atomic.return_value.__enter__.side_effect = lambda: ordine.entra()
        mock_tx.atomic.return_value.__exit__.side_effect = lambda *a: ordine.esce()
        tokens.invalidate_for_identita.side_effect = lambda *a: ordine.invalida(*a)
        tokens.create.side_effect = lambda **k: (ordine.crea(), "tok")[1]

        invito.emetti(
            PORTA_SHOP, auth_user_id=42, identita_id=600,
            ruolo_applicativo="SHOP_CUSTOMER", invitato_da_user_id=1,
        )
        self.assertEqual(
            [c[0] for c in ordine.mock_calls], ["entra", "invalida", "crea", "esce"],
        )
        ordine.invalida.assert_called_once_with(PORTA_SHOP.token_tipi, 42, 600)

    # Scopo: Una veste che non e' della porta e' un errore del chiamante.
    def test_veste_fuori_dalla_porta_esplode(self, _tx):
        invito, _, tokens, _ = _invito(ha_password=False)
        with self.assertRaises(ValueError):
            invito.emetti(
                PORTA_SHOP, auth_user_id=42, identita_id=1,
                ruolo_applicativo="OPERATORE", invitato_da_user_id=1,
            )
        tokens.create.assert_not_called()


class SpedisciTests(TestCase):

    # Scopo: Email partita → `True`, e la veste segna l'invito. Link dalla porta.
    @patch(f"{_BB}.nome_visualizzato", return_value="Admin")
    def test_email_partita_segna_l_invito(self, _nome):
        from apps.core.services.invito_veste import EmissioneInvito

        invito, repo, _, email = _invito(ha_password=False)
        with override_settings(FRONTEND_URL="https://erp.example"):
            partita = invito.spedisci(
                PORTA_PORTALE, EmissioneInvito(token="abc", is_cross=True),
                auth_user_id=42, identita_id=500, destinatario="m@x.it",
                invitato_da_user_id=1, variabili={"nome": "Mario"},
            )
        self.assertTrue(partita)
        variabili = email.send_email.call_args.kwargs["variabili"]
        self.assertEqual(variabili["link"], "https://erp.example/attivazione-portale/abc")
        self.assertEqual(variabili["nome"], "Mario")
        repo.set_invito_inviato_at.assert_called_once_with(42, identita_id=500)

    # Scopo: ⭐ F-3 — l'email che NON parte senza eccezione (SMTP fallito,
    # canale non configurato: `send_email` torna `False`) non e' un invito
    # inviato. Non solleva (il token vale), ma torna `False`, lo logga e non
    # segna `invito_inviato_at`. Fino al 2026-09-28 l'esito si scartava.
    @patch(f"{_BB}.nome_visualizzato", return_value="Admin")
    def test_email_non_partita_non_segna_l_invito(self, _nome):
        from apps.core.services.invito_veste import EmissioneInvito

        invito, repo, _, email = _invito(ha_password=False)
        email.send_email.return_value = (7, False)
        with self.assertLogs("security", level="ERROR"):
            partita = invito.spedisci(
                PORTA_OPERATORE, EmissioneInvito(token="abc", is_cross=False),
                auth_user_id=42, identita_id=500, destinatario="m@x.it",
                invitato_da_user_id=1, variabili={},
            )
        self.assertFalse(partita)
        repo.set_invito_inviato_at.assert_not_called()

    # Scopo: L'eccezione (template o account che mancano) e' la stessa cosa:
    # non solleva, torna `False`, non segna l'invito.
    @patch(f"{_BB}.nome_visualizzato", return_value="Admin")
    def test_email_con_eccezione_non_solleva_e_non_segna_l_invito(self, _nome):
        from apps.core.services.invito_veste import EmissioneInvito

        invito, repo, _, email = _invito(ha_password=False)
        email.send_email.side_effect = RuntimeError("smtp giu'")
        with self.assertLogs("security", level="ERROR"):
            partita = invito.spedisci(
                PORTA_PORTALE, EmissioneInvito(token="abc", is_cross=True),
                auth_user_id=42, identita_id=500, destinatario="m@x.it",
                invitato_da_user_id=1, variabili={"nome": "Mario"},
            )
        self.assertFalse(partita)
        repo.set_invito_inviato_at.assert_not_called()

    # Scopo: B-16 — il flusso sceglie il TESTO, non una variabile: nuovo →
    # template della porta, un clic → il suo `_CROSS`. `is_cross` non viaggia
    # piu' fra le variabili (il motore non ha rami, il testo non la usava).
    @patch(f"{_BB}.nome_visualizzato", return_value="Admin")
    def test_il_flusso_sceglie_il_template_della_porta(self, _nome):
        from apps.core.services.invito_veste import EmissioneInvito

        casi = (
            (PORTA_OPERATORE, False, "INVITO_OPERATORE"),
            (PORTA_OPERATORE, True, "INVITO_OPERATORE_CROSS"),
            (PORTA_PORTALE, False, "INVITO_PORTALE"),
            (PORTA_PORTALE, True, "INVITO_PORTALE_CROSS"),
            (PORTA_SHOP, False, "INVITO_SHOP"),
            (PORTA_SHOP, True, "INVITO_SHOP_CROSS"),
        )
        for porta, is_cross, atteso in casi:
            with self.subTest(porta=porta.nome, is_cross=is_cross):
                invito, _, _, email = _invito(ha_password=False)
                with override_settings(FRONTEND_URL="https://erp.example"):
                    invito.spedisci(
                        porta, EmissioneInvito(token="abc", is_cross=is_cross),
                        auth_user_id=42, identita_id=500, destinatario="m@x.it",
                        invitato_da_user_id=1, variabili={},
                    )
                kwargs = email.send_email.call_args.kwargs
                self.assertEqual(kwargs["codice_template"], atteso)
                self.assertNotIn("is_cross", kwargs["variabili"])


@patch(f"{_BB}.transaction")
@patch(f"{_BB}.apply_new_password")
@patch("apps.core.services.auth_helpers.validate_password")
@patch(f"{_BB}.User")
class AttivaTests(TestCase):

    def _mocks(self, *, tipo: str, identita_id: int | None = 700, ha_password: bool = False):
        repo, tokens = MagicMock(), MagicMock()
        meta = {"identita_id": identita_id} if identita_id is not None else {}
        # risolvi_token cerca i due tipi in ordine: risponde solo quello giusto.
        tokens.validate.side_effect = lambda tok, t: (42, meta) if t == tipo else None
        repo.auth_user_ha_password.return_value = ha_password
        repo.attiva_identita.return_value = True
        return repo, tokens

    def _attiva(self, repo, tokens, *, token="tk", pw="Str0ng!pass", conferma=None):
        return attiva_veste(
            PORTA_OPERATORE, token=token, new_password=pw,
            new_password_confirm=pw if conferma is None else conferma,
            ip="203.0.113.7", auth_repo=repo, token_service=tokens,
        )

    # Scopo: Flusso con password: consuma, imposta la password, ACCENDE la
    # veste (A-3) con il guard su credenziale e porta.
    def test_con_password_consuma_imposta_e_accende(self, MockUser, _vp, mock_apply, _tx):
        repo, tokens = self._mocks(tipo="INVITO_OPERATORE")
        esito = self._attiva(repo, tokens)
        self.assertFalse(esito.is_cross)
        self.assertEqual(esito.identita_id, 700)
        tokens.consume.assert_called_once_with("tk", "INVITO_OPERATORE", ip="203.0.113.7")
        mock_apply.assert_called_once()
        self.assertFalse(mock_apply.call_args.kwargs["blacklist_tokens"])
        repo.attiva_identita.assert_called_once_with(
            700, auth_user_id=42, ruoli_applicativi=("OPERATORE",),
        )

    # Scopo: Veste sparita fra invito e consumo → errore (la transazione
    # annulla consumo e password insieme).
    def test_veste_sparita_solleva_dopo_il_consumo(self, MockUser, _vp, _apply, _tx):
        repo, tokens = self._mocks(tipo="INVITO_OPERATORE")
        repo.attiva_identita.return_value = False
        with self.assertRaises(ServiceError) as ctx:
            self._attiva(repo, tokens)
        self.assertEqual(ctx.exception.code, "E_ATTIVAZIONE")

    def test_con_password_senza_password_solleva_senza_consumare(self, MockUser, _vp, _apply, _tx):
        repo, tokens = self._mocks(tipo="INVITO_OPERATORE")
        with self.assertRaises(ServiceError):
            self._attiva(repo, tokens, pw="")
        tokens.consume.assert_not_called()

    def test_conferma_diversa_solleva_senza_consumare(self, MockUser, _vp, _apply, _tx):
        repo, tokens = self._mocks(tipo="INVITO_OPERATORE")
        with self.assertRaises(ServiceError):
            self._attiva(repo, tokens, conferma="altra")
        tokens.consume.assert_not_called()

    # Scopo: Una password rifiutata dalla policy non brucia il link.
    def test_policy_password_rifiutata_non_brucia_il_token(self, MockUser, mock_vp, _apply, _tx):
        repo, tokens = self._mocks(tipo="INVITO_OPERATORE")
        mock_vp.side_effect = DjangoValidationError(["Troppo corta."])
        with self.assertRaises(ServiceError) as ctx:
            self._attiva(repo, tokens)
        self.assertIn("Troppo corta", ctx.exception.message)
        tokens.consume.assert_not_called()

    # Scopo: Con un clic la password passata si IGNORA: mai sovrascrivere
    # quella che la persona usa gia'.
    def test_cross_non_tocca_la_password_anche_se_passata(self, MockUser, _vp, mock_apply, _tx):
        repo, tokens = self._mocks(tipo="ATTIVAZIONE_OPERATORE_CROSS", ha_password=True)
        esito = self._attiva(repo, tokens, pw="Digitata-per-sbaglio1")
        self.assertTrue(esito.is_cross)
        mock_apply.assert_not_called()
        tokens.consume.assert_called_once_with("tk", "ATTIVAZIONE_OPERATORE_CROSS", ip="203.0.113.7")
        repo.attiva_identita.assert_called_once()

    # Scopo: Token INVITO, ma nel frattempo la credenziale ha una password
    # vera (ha attivato un'altra veste): decide la credenziale ADESSO, e
    # quella password non si sovrascrive.
    def test_token_invito_ma_password_vera_diventa_un_clic(self, MockUser, _vp, mock_apply, _tx):
        repo, tokens = self._mocks(tipo="INVITO_OPERATORE", ha_password=True)
        esito = self._attiva(repo, tokens)
        self.assertTrue(esito.is_cross)
        mock_apply.assert_not_called()
        tokens.consume.assert_called_once_with("tk", "INVITO_OPERATORE", ip="203.0.113.7")

    def test_token_mancante_solleva(self, MockUser, _vp, _apply, _tx):
        repo, tokens = self._mocks(tipo="INVITO_OPERATORE")
        with self.assertRaises(ServiceError):
            self._attiva(repo, tokens, token="")
        tokens.validate.assert_not_called()

    def test_token_non_valido_solleva(self, MockUser, _vp, _apply, _tx):
        repo, tokens = self._mocks(tipo="NESSUNO")
        with self.assertRaises(ServiceError) as ctx:
            self._attiva(repo, tokens)
        self.assertIn("non valido", ctx.exception.message)

    # Scopo: Senza `identita_id` il token non e' di nessuna veste: rifiuto.
    def test_meta_senza_identita_solleva(self, MockUser, _vp, _apply, _tx):
        repo, tokens = self._mocks(tipo="INVITO_OPERATORE", identita_id=None)
        with self.assertRaises(ServiceError):
            self._attiva(repo, tokens)
        tokens.consume.assert_not_called()
        repo.attiva_identita.assert_not_called()


class ViewTests(TestCase):

    # Scopo: La verifica dice alla pagina se chiedere la password: la
    # decide la credenziale (INVITO + nessuna password vera).
    @patch("apps.core.api.attivazione_veste_views.richiede_password")
    @patch("apps.core.api.attivazione_veste_views.risolvi_token")
    def test_validate_dice_se_chiedere_la_password(self, mock_risolvi, mock_richiede):
        from apps.shop.api.views_attivazione import AttivazioneShopValidateView

        mock_risolvi.return_value = (42, {"identita_id": 600}, "INVITO_SHOP")
        for richiede in (True, False):
            mock_richiede.return_value = richiede
            body = json.loads(AttivazioneShopValidateView().get(MagicMock(), token="tk").content)["data"]
            self.assertTrue(body["valid"])
            self.assertEqual(body["token_type"], "INVITO_SHOP")
            self.assertIs(body["requires_password"], richiede)
        mock_richiede.assert_called_with(PORTA_SHOP, "INVITO_SHOP", 42)

    @patch("apps.core.api.attivazione_veste_views.risolvi_token", return_value=None)
    def test_validate_token_non_valido(self, _risolvi):
        from apps.portale.api.views import AttivazionePortaleValidateView

        body = json.loads(AttivazionePortaleValidateView().get(MagicMock(), token="x").content)["data"]
        self.assertFalse(body["valid"])
        self.assertNotIn("token_type", body)


# Scopo: `chiudi_veste_spenta` — cio' che resta aperto di una veste spenta, per
#        ogni porta (regola del 2, 2026-10-03: operatore e portale/shop).
@patch(f"{_BB}.invalidate_user")
@patch(f"{_BB}.blocca_token_sessioni")
@patch(f"{_BB}.transaction")
class ChiudiVesteSpentaTests(TestCase):

    # Scopo: Inviti della veste (tipi della porta), sessioni della SOLA veste
    #        (per `identita_id`), cache della credenziale a COMMIT avvenuto.
    def test_inviti_sessioni_della_veste_e_cache_a_commit(self, mock_tx, mock_blocca, mock_invalidate):
        invito, _, tokens, _ = _invito(ha_password=True)
        invito.chiudi_veste_spenta(PORTA_SHOP, auth_user_id=42, identita_id=700)

        tokens.invalidate_for_identita.assert_called_once_with(PORTA_SHOP.token_tipi, 42, 700)
        mock_blocca.assert_called_once_with(42, identita_id=700)
        # La cache aspetta il commit: prima, una richiesta concorrente la
        # ricaricherebbe dalla veste ancora accesa.
        mock_invalidate.assert_not_called()
        (callback,), _ = mock_tx.on_commit.call_args
        callback()
        mock_invalidate.assert_called_once_with(42)

    # Scopo: Una chiusura fallita PROPAGA (il chiamante annulla anche lo
    #        spegnimento) e non prenota l'invalidazione della cache.
    def test_chiusura_fallita_propaga_e_non_tocca_la_cache(self, mock_tx, mock_blocca, _invalidate):
        invito, _, _, _ = _invito(ha_password=True)
        mock_blocca.side_effect = RuntimeError("scrittura blacklist fallita")
        with self.assertRaises(RuntimeError):
            invito.chiudi_veste_spenta(PORTA_OPERATORE, auth_user_id=42, identita_id=700)
        mock_tx.on_commit.assert_not_called()
