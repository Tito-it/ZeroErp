# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il secondo fattore della propria credenziale e i comandi del
#        SUPER_ADMIN (brief sicurezza §3.4-bis, T-3), sul percorso client ->
#        middleware -> DRF -> view -> servizio. Veri: il servizio, la verifica
#        del codice (vettore RFC 6238), la cifratura. Finti: i repository.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_stato
 2) test_registra_da_qr_segreto_e_codici_una_volta — al DB il segreto cifrato e le impronte
 2b) test_registra_password_sbagliata_conta — D-T2, e il device non nasce
 2c) test_registra_senza_password_non_conta — 400, non e' un tentativo
 2d) test_registra_credenziale_bloccata_ferma_prima_della_password
 3) test_conferma_col_codice_giusto_registra_il_passo
 4) test_conferma_col_codice_sbagliato_non_conta — il segreto l'ha appena ricevuto
 5) test_conferma_senza_configurazione_avviata — 409 E_TOTP_DEVICE_ASSENTE
 5b) test_conferma_su_device_gia_attivo — 409 E_TOTP_DEVICE_GIA_ATTIVO, non «non attivo»
 6) test_codici_recupero_dietro_un_codice — rigenera e restituisce i nuovi
 7) test_codici_recupero_codice_sbagliato_conta — D-T2 anche qui
 8) test_disattiva_propria_col_codice_lascia_la_traccia — TOTP_DISABILITATO, via APP
 9) test_disattiva_propria_senza_prova_non_disattiva — decisione 7
10) test_le_view_restano_aperte_con_l_obbligo_pendente
11) test_admin_obbligo_vuole_un_booleano
12) test_admin_obbligo_sulla_credenziale
13) test_admin_disattiva_lascia_la_traccia_col_motivo
14) test_admin_credenziale_inesistente_non_legge_il_device
15) test_admin_non_disattiva_il_proprio — senza prova, solo dalla pagina Sicurezza (decisione 7)
"""

import base64
from unittest.mock import MagicMock, patch


from apps.core.tests._helpers.jwt_mock import ClientApi

from apps.core.services import crypto_service
from apps.core.services.service_errors import ServiceError
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_SERVIZIO = "apps.core.services.secondo_fattore_service"
_SEGRETO = base64.b32encode(b"12345678901234567890").decode()
_CODICE = "287082"  # RFC 6238, passo 1
_IP = "203.0.113.7"
_PASSWORD = "Giusta-2026!"


class _Base(JwtMockedApiTest):
    """Utente autenticato 42 e i repository del servizio finti."""

    def setUp(self) -> None:
        super().setUp()
        self.client = ClientApi()
        self.user = MagicMock(id=42, is_authenticated=True, is_superuser=False)
        self.user.get_username.return_value = "alice"
        self.user.check_password.side_effect = lambda p: p == _PASSWORD
        auth = patch(
            "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
            return_value=(self.user, None),
        )
        auth.start()
        self.addCleanup(auth.stop)
        for nome, attr in (("SecondoFattoreRepository", "repo"), ("AuthRepository", "auth_repo"),
                           ("SessionAuditRepository", "audit")):
            p = patch(f"{_SERVIZIO}.{nome}")
            setattr(self, attr, p.start().return_value)
            self.addCleanup(p.stop)
        self.auth_repo.registra_tentativo_login.return_value = {"bloccato": False}
        self.repo.get_obbligo.return_value = {"obbligatorio": False, "motivo": None}
        self.repo.get_device.return_value = self._device("ATTIVO")
        for target, valore in (("apps.core.api.permissions.ZeroERPPermission.has_permission", True),
                               (f"{_SERVIZIO}.get_client_ip", _IP),
                               ("apps.core.services.request_context.get_client_ip", _IP),
                               ("apps.core.services.totp_service.passo_corrente", 1)):
            p = patch(target, return_value=valore)
            p.start()
            self.addCleanup(p.stop)
        # Il savepoint vuole una connessione: il suo motivo lo prova il DB vero.
        for modulo in (_SERVIZIO, "apps.core.services.password_con_freno"):
            savepoint = patch(f"{modulo}.transaction")
            savepoint.start()
            self.addCleanup(savepoint.stop)

    @staticmethod
    def _device(stato: str) -> dict:
        return {
            "stato": stato,
            "secret_encrypted": crypto_service.encrypt(_SEGRETO),
            "ultimo_passo_usato": 0,
            "recovery_rimasti": 10,
        }

    def _post(self, url: str, corpo: dict | None = None):
        return self.client.post(url, corpo or {}, content_type="application/json")

    def _assert_tentativo_fallito(self) -> None:
        self.auth_repo.registra_tentativo_login.assert_called_once()
        self.assertFalse(self.auth_repo.registra_tentativo_login.call_args.kwargs["successo"])


class SecondoFattoreProprioTests(_Base):
    _URL = "/api/v1/auth/secondo-fattore/"

    def test_stato(self):
        self.repo.get_obbligo.return_value = {"obbligatorio": True, "motivo": "PROFILO"}
        resp = self.client.get(self._URL)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(
            resp.json()["data"],
            {"stato": "ATTIVO", "obbligatorio": True, "motivo": "PROFILO", "codici_recupero_rimasti": 10},
        )

    def test_registra_da_qr_segreto_e_codici_una_volta(self):
        resp = self._post(self._URL + "registra/", {"password": _PASSWORD})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.auth_repo.check_blocco_login.assert_called_once()
        # La password giusta non e' un login: non azzera i tentativi.
        self.auth_repo.registra_tentativo_login.assert_not_called()
        dati = resp.json()["data"]
        self.assertTrue(dati["qr_data_uri"].startswith("data:image/svg+xml;"))
        self.assertEqual(len(dati["codici_recupero"]), 10)
        scritto = self.repo.registra_device.call_args
        self.assertEqual(scritto.args, (42,))
        # Al DB il segreto CIFRATO (e' quello mostrato, senza spazi) e le impronte.
        self.assertEqual(
            crypto_service.decrypt(scritto.kwargs["secret_encrypted"]), dati["segreto"].replace(" ", ""),
        )
        impronte = scritto.kwargs["impronte_recupero"]
        self.assertEqual(len(impronte), 10)
        self.assertTrue(all(len(i) == 64 for i in impronte))
        self.assertNotIn(dati["codici_recupero"][0], impronte)

    # Scopo: Chi tiene la sessione non prova password senza freno.
    def test_registra_password_sbagliata_conta(self):
        resp = self._post(self._URL + "registra/", {"password": "Sbagliata-2026!"})
        self.assertEqual(resp.status_code, 400, resp.content)
        errore = resp.json()["error"]
        self.assertEqual(errore["code"], "E_TOTP_PASSWORD_NON_VALIDA")
        self._assert_tentativo_fallito()
        self.repo.registra_device.assert_not_called()

    def test_registra_senza_password_non_conta(self):
        resp = self._post(self._URL + "registra/", {})
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["error"]["code"], "E_TOTP_PASSWORD_NON_VALIDA")
        self.auth_repo.registra_tentativo_login.assert_not_called()
        self.repo.registra_device.assert_not_called()

    # Scopo: Il freno prima della password: a credenziale bloccata la password
    #        non si verifica nemmeno (il codice del DB lo prova il test DB).
    def test_registra_credenziale_bloccata_ferma_prima_della_password(self):
        self.auth_repo.check_blocco_login.side_effect = ServiceError(
            code="E_UTENTE_BLOCCATO", message="bloccato",
        )
        resp = self._post(self._URL + "registra/", {"password": _PASSWORD})
        self.assertEqual(resp.json()["error"]["code"], "E_UTENTE_BLOCCATO")
        self.user.check_password.assert_not_called()
        self.repo.registra_device.assert_not_called()

    def test_conferma_col_codice_giusto_registra_il_passo(self):
        self.repo.get_device.return_value = self._device("DA_CONFERMARE")
        resp = self._post(self._URL + "conferma/", {"codice": _CODICE})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.repo.conferma_device.assert_called_once_with(42, passo=1)

    def test_conferma_col_codice_sbagliato_non_conta(self):
        self.repo.get_device.return_value = self._device("DA_CONFERMARE")
        resp = self._post(self._URL + "conferma/", {"codice": "000000"})
        self.assertEqual(resp.json()["error"]["code"], "E_TOTP_CODICE_NON_VALIDO")
        self.repo.conferma_device.assert_not_called()
        self.auth_repo.registra_tentativo_login.assert_not_called()

    def test_conferma_senza_configurazione_avviata(self):
        self.repo.get_device.return_value = self._device("ASSENTE")
        resp = self._post(self._URL + "conferma/", {"codice": _CODICE})
        self.assertEqual(resp.status_code, 409, resp.content)
        self.assertEqual(resp.json()["error"]["code"], "E_TOTP_DEVICE_ASSENTE")

    # Scopo: Il secondo clic su «Conferma»: il device e' gia' attivo.
    def test_conferma_su_device_gia_attivo(self):
        resp = self._post(self._URL + "conferma/", {"codice": _CODICE})
        self.assertEqual(resp.status_code, 409, resp.content)
        self.assertEqual(resp.json()["error"]["code"], "E_TOTP_DEVICE_GIA_ATTIVO")
        self.repo.conferma_device.assert_not_called()

    def test_codici_recupero_dietro_un_codice(self):
        resp = self._post(self._URL + "codici-recupero/", {"codice": _CODICE})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(len(resp.json()["data"]["codici_recupero"]), 10)
        self.repo.registra_uso.assert_called_once_with(42, passo=1)
        self.repo.rigenera_recovery.assert_called_once()

    def test_codici_recupero_codice_sbagliato_conta(self):
        resp = self._post(self._URL + "codici-recupero/", {"codice": "000000"})
        self.assertEqual(resp.json()["error"]["code"], "E_TOTP_CODICE_NON_VALIDO")
        self._assert_tentativo_fallito()
        self.repo.rigenera_recovery.assert_not_called()

    def test_disattiva_propria_col_codice_lascia_la_traccia(self):
        resp = self._post(self._URL + "disattiva/", {"codice": _CODICE})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.repo.disabilita_device.assert_called_once_with(42, motivo=None)
        traccia = self.audit.log_session_event.call_args.kwargs
        self.assertEqual(traccia["evento"], "TOTP_DISABILITATO")
        self.assertEqual(traccia["dettaglio"], {"via": "APP", "chi_agisce": 42, "motivo": None})

    def test_disattiva_propria_senza_prova_non_disattiva(self):
        resp = self._post(self._URL + "disattiva/", {})
        self.assertEqual(resp.status_code, 400, resp.content)
        self.repo.disabilita_device.assert_not_called()

    # Scopo: Sono la strada che soddisfa l'obbligo: il cancello le lascia aperte.
    def test_le_view_restano_aperte_con_l_obbligo_pendente(self):
        from apps.core.api import secondo_fattore_views as v
        from apps.core.api.cancello_obblighi import OBBLIGO_SECONDO_FATTORE

        for view in (v.SecondoFattoreStatoView, v.SecondoFattoreRegistraView, v.SecondoFattoreConfermaView,
                     v.SecondoFattoreCodiciRecuperoView, v.SecondoFattoreDisattivaView):
            self.assertIn(OBBLIGO_SECONDO_FATTORE, view.obblighi_ammessi, view.__name__)


class SecondoFattoreAdminTests(_Base):
    # ⭐ La sede e' la CREDENZIALE (brief-db-be-fe-area-accessi, 2026-10-02):
    #    il secondo fattore vale per tutte le sue vesti. Prima stava sotto
    #    `operatori/<id>/`.
    _URL = "/api/v1/amm-software/credenziali/77/secondo-fattore/"

    def setUp(self) -> None:
        super().setUp()
        for target, valore in (("apps.core.api.permissions.IsAdminZeroERP.has_permission", True),):
            p = patch(target, return_value=valore)
            p.start()
            self.addCleanup(p.stop)
        esiste = patch("apps.amm_software.api.accessi_views.AccessiService")
        self.accessi = esiste.start().return_value
        self.addCleanup(esiste.stop)

    def test_admin_obbligo_vuole_un_booleano(self):
        resp = self._post(self._URL + "obbligo/", {"valore": "si"})
        self.assertEqual(resp.status_code, 400, resp.content)
        self.repo.imposta_obbligo.assert_not_called()

    def test_admin_obbligo_sulla_credenziale(self):
        self.repo.get_obbligo.return_value = {"obbligatorio": True, "motivo": "CREDENZIALE"}
        resp = self._post(self._URL + "obbligo/", {"valore": True})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.repo.imposta_obbligo.assert_called_once_with(77, valore=True)
        self.assertTrue(resp.json()["data"]["obbligo_sulla_credenziale"])

    def test_admin_disattiva_lascia_la_traccia_col_motivo(self):
        resp = self._post(self._URL + "disattiva/", {"motivo": "  telefono perso  "})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.repo.disabilita_device.assert_called_once_with(77, motivo="telefono perso")
        self.assertEqual(
            self.audit.log_session_event.call_args.kwargs["dettaglio"],
            {"via": "APP", "chi_agisce": 42, "motivo": "telefono perso"},
        )

    def test_admin_credenziale_inesistente_non_legge_il_device(self):
        from apps.core.services.service_errors import ServiceError

        self.accessi.get_credenziale.side_effect = ServiceError(
            code="E_CREDENZIALE_NON_TROVATA", message="Credenziale 77 non trovata.",
        )
        resp = self.client.get(self._URL)
        self.assertEqual(resp.status_code, 404, resp.content)
        self.assertEqual(resp.json()["error"]["code"], "E_CREDENZIALE_NON_TROVATA", resp.content)
        self.repo.get_device.assert_not_called()

    # Scopo: Per il DB «la credenziale stessa» disattiva senza motivo e senza
    #        prova: dall'endpoint dell'amministratore, con la sola sessione,
    #        il SUPER_ADMIN non spegne il proprio (decisione 7).
    def test_admin_non_disattiva_il_proprio(self):
        resp = self._post("/api/v1/amm-software/credenziali/42/secondo-fattore/disattiva/", {"motivo": "x"})
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(resp.json()["error"]["code"], "E_PERMESSO_NEGATO")
        self.repo.disabilita_device.assert_not_called()
        self.audit.log_session_event.assert_not_called()
