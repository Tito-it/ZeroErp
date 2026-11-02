# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il secondo passo del login (brief sicurezza §3.4-bis, T-2) sul
#        percorso client -> middleware -> view. Veri: la sfida firmata, la
#        verifica del codice (vettore RFC 6238), la cifratura del segreto.
#        Finti: i repository, la credenziale, l'emissione della sessione.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_sfida_assente_401
 2) test_sfida_di_un_altra_porta_401
 3) test_sfida_di_un_altra_provenienza_401
 4) test_sfida_scaduta_401
 5) test_codice_giusto_apre_la_sessione — access, cookie, passo al DB, successo solo qui
 6) test_codice_sbagliato_conta_come_tentativo — D-T2, niente cookie, niente sessione
 7) test_codice_ripresentato_conta_come_tentativo — E_TOTP_PASSO_GIA_USATO dal DB
 8) test_codice_di_recupero_apre_e_dice_quanti_ne_restano
 9) test_recupero_non_valido_conta_come_tentativo
10) test_blocco_fra_i_due_passi_ferma_prima_del_codice
11) test_device_disabilitato_fra_i_due_passi_401
12) test_veste_spenta_fra_i_due_passi_401
13) test_senza_prova_non_e_un_tentativo
14) test_segreto_illeggibile_non_e_un_tentativo — chiave tolta prima della rotazione
15) test_cambio_password_pendente_nella_risposta
16) test_il_secondo_passo_ha_un_contatore_suo — non dimezza i login di un IP
"""

import base64
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.db import DatabaseError
from django.test import Client

from apps.core.api.refresh_cookie import REFRESH_COOKIE_NAME
from apps.core.api.secondo_fattore_token_views import AuditSecondoFattoreTokenView, _secondo_fattore
from apps.core.services import crypto_service
from apps.core.services.sfida_secondo_fattore import Sfida, emetti_sfida
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_MOD = "apps.core.api.secondo_fattore_token_views"
# Letto all'import, prima che il setUp lo spenga coi patch.
_THROTTLE_DEL_SECONDO_PASSO = list(AuditSecondoFattoreTokenView.throttle_classes)
_URL = "/api/v1/admin/token/secondo-fattore/"
_IP = "203.0.113.7"
# Il vettore dell'RFC 6238 (SHA1): al passo 1 il codice e' 287082.
_SEGRETO = base64.b32encode(b"12345678901234567890").decode()
_CODICE = "287082"
_PASSO = 1


# Scopo: Una sfida come la emette il primo passo della porta admin.
def _sfida(*, porta: str = "admin", provenienza: str = _IP) -> str:
    return emetti_sfida(Sfida(auth_user_id=42, identita_id=7, porta=porta, provenienza=provenienza))


# Scopo: Un rifiuto del DB col codice del catalogo, come lo solleva
#        `fn_log_and_raise_error` (SQLSTATE P0001, codice in constraint_name).
class _CausaPsycopg(Exception):
    sqlstate = "P0001"

    def __init__(self, codice: str) -> None:
        super().__init__(codice)
        self.diag = SimpleNamespace(
            constraint_name=codice, message_primary=codice, message_detail=None,
            message_hint=None, column_name=None, datatype_name=None,
        )


def _rifiuto_db(codice: str) -> DatabaseError:
    exc = DatabaseError(codice)
    exc.__cause__ = _CausaPsycopg(codice)
    return exc


class SecondoPassoTests(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()
        # La provenienza la legge il BB `provenienza_obbligatoria`.
        for bersaglio, valore in (
            ("apps.core.services.request_context.get_client_ip", _IP),
            (f"{_MOD}.chiudi_accesso_riuscito", False),
        ):
            p = patch(bersaglio, return_value=valore)
            setattr(self, f"mock_{bersaglio.rsplit('.', 1)[1]}", p.start())
            self.addCleanup(p.stop)
        # Lo stesso secchio del primo passo: qui farebbe scattare il 429.
        throttle = patch.object(AuditSecondoFattoreTokenView, "throttle_classes", [])
        throttle.start()
        self.addCleanup(throttle.stop)
        # Il savepoint attorno alla prova vuole una connessione: qui non c'e'.
        # Il suo motivo (il rifiuto del DB non deve perdere il tentativo) lo
        # prova il login a due passi sul DB vero (test_login_credenziale_db, 10).
        savepoint = patch("apps.core.services.secondo_fattore_service.transaction")
        savepoint.start()
        self.addCleanup(savepoint.stop)
        # Il passo di adesso, fissato sul vettore dell'RFC.
        passo = patch("apps.core.services.totp_service.passo_corrente", return_value=_PASSO)
        passo.start()
        self.addCleanup(passo.stop)

        utente = MagicMock(id=42, is_active=True)
        utente.get_username.return_value = "alice"
        user_cls = patch(f"{_MOD}.User")
        user_cls.start().objects.filter.return_value.first.return_value = utente
        self.addCleanup(user_cls.stop)

        # Lo stesso finto per le due sedi che lo usano: la view (la veste) e
        # il servizio (freno e tentativi).
        auth_repo = patch(f"{_MOD}._auth_repo")
        self.auth_repo = auth_repo.start()
        servizio_auth = patch.object(_secondo_fattore, "_auth_repo", self.auth_repo)
        servizio_auth.start()
        self.addCleanup(servizio_auth.stop)
        self.auth_repo.get_veste_utilizzabile.return_value = {
            "id": 7, "ruolo_applicativo": "OPERATORE", "attivo": True,
        }
        self.auth_repo.registra_tentativo_login.return_value = {"bloccato": False}
        self.addCleanup(auth_repo.stop)

        sf_repo = patch.object(_secondo_fattore, "_repo")
        self.sf_repo = sf_repo.start()
        self.sf_repo.get_device.return_value = {
            "stato": "ATTIVO",
            "secret_encrypted": crypto_service.encrypt(_SEGRETO),
            "ultimo_passo_usato": 0,
            "recovery_rimasti": 10,
        }
        self.addCleanup(sf_repo.stop)

        refresh = MagicMock()
        refresh.__getitem__.side_effect = lambda k: "sid-nuovo" if k == "sid" else None
        refresh.__str__.return_value = "refresh.nuovo"
        refresh.access_token.__str__.return_value = "access.nuovo"
        emetti = patch(f"{_MOD}.emetti_refresh_veste", return_value=refresh)
        self.mock_emetti = emetti.start()
        self.addCleanup(emetti.stop)

    def _post(self, corpo: dict):
        return self.client.post(_URL, corpo, content_type="application/json")

    # Scopo: Il rifiuto della sfida: 401, e nessuno strato sotto toccato.
    def _assert_sfida_rifiutata(self, resp) -> None:
        self.assertEqual(resp.status_code, 401, resp.content)
        self.assertEqual(resp.json()["error"]["code"], "E_TOTP_SFIDA_NON_VALIDA")
        self.assertNotIn(REFRESH_COOKIE_NAME, resp.cookies)

    def _assert_tentativo_fallito(self) -> None:
        self.auth_repo.registra_tentativo_login.assert_called_once()
        self.assertFalse(self.auth_repo.registra_tentativo_login.call_args.kwargs["successo"])
        self.mock_chiudi_accesso_riuscito.assert_not_called()

    def test_sfida_assente_401(self):
        self._assert_sfida_rifiutata(self._post({"codice": _CODICE}))
        self.auth_repo.check_blocco_login.assert_not_called()

    def test_sfida_di_un_altra_porta_401(self):
        self._assert_sfida_rifiutata(self._post({"sfida": _sfida(porta="portale"), "codice": _CODICE}))

    def test_sfida_di_un_altra_provenienza_401(self):
        self._assert_sfida_rifiutata(
            self._post({"sfida": _sfida(provenienza="198.51.100.9"), "codice": _CODICE})
        )

    def test_sfida_scaduta_401(self):
        sfida = _sfida()
        with patch("apps.core.services.sfida_secondo_fattore.DURATA_SFIDA_SECONDI", -1):
            self._assert_sfida_rifiutata(self._post({"sfida": sfida, "codice": _CODICE}))

    def test_codice_giusto_apre_la_sessione(self):
        resp = self._post({"sfida": _sfida(), "codice": _CODICE})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["data"], {"access": "access.nuovo"})
        self.assertEqual(resp.cookies[REFRESH_COOKIE_NAME].value, "refresh.nuovo")
        self.sf_repo.registra_uso.assert_called_once_with(42, passo=_PASSO)
        # La sessione si apre nella veste della sfida, e il successo sul
        # freno si registra solo qui.
        self.assertEqual(self.mock_emetti.call_args.args[1]["id"], 7)
        chiusura = self.mock_chiudi_accesso_riuscito.call_args.kwargs
        self.assertEqual(chiusura["identita_id"], 7)
        self.assertEqual(chiusura["sid"], "sid-nuovo")
        self.assertEqual(chiusura["provenienza"], _IP)
        self.assertEqual(chiusura["dettaglio"], {"secondo_fattore": "TOTP"})
        self.auth_repo.registra_tentativo_login.assert_not_called()

    def test_codice_sbagliato_conta_come_tentativo(self):
        resp = self._post({"sfida": _sfida(), "codice": "000000"})
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["error"]["code"], "E_TOTP_CODICE_NON_VALIDO")
        self.assertNotIn(REFRESH_COOKIE_NAME, resp.cookies)
        self._assert_tentativo_fallito()
        self.sf_repo.registra_uso.assert_not_called()

    def test_codice_ripresentato_conta_come_tentativo(self):
        self.sf_repo.registra_uso.side_effect = _rifiuto_db("E_TOTP_PASSO_GIA_USATO")
        resp = self._post({"sfida": _sfida(), "codice": _CODICE})
        self.assertEqual(resp.json()["error"]["code"], "E_TOTP_PASSO_GIA_USATO")
        self._assert_tentativo_fallito()

    def test_codice_di_recupero_apre_e_dice_quanti_ne_restano(self):
        self.sf_repo.consuma_recovery.return_value = 3
        resp = self._post({"sfida": _sfida(), "codice_recupero": "ab01-cd23-ef45-gh67"})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["data"]["codici_recupero_rimasti"], 3)
        self.assertRegex(self.sf_repo.consuma_recovery.call_args.kwargs["impronta"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            self.mock_chiudi_accesso_riuscito.call_args.kwargs["dettaglio"],
            {"secondo_fattore": "CODICE_RECUPERO"},
        )

    def test_recupero_non_valido_conta_come_tentativo(self):
        self.sf_repo.consuma_recovery.side_effect = _rifiuto_db("E_TOTP_RECOVERY_NON_VALIDO")
        resp = self._post({"sfida": _sfida(), "codice_recupero": "AB01-CD23-EF45-GH67"})
        self.assertEqual(resp.json()["error"]["code"], "E_TOTP_RECOVERY_NON_VALIDO")
        self._assert_tentativo_fallito()

    def test_blocco_fra_i_due_passi_ferma_prima_del_codice(self):
        self.auth_repo.check_blocco_login.side_effect = _rifiuto_db("E_CREDENZIALE_BLOCCATA")
        resp = self._post({"sfida": _sfida(), "codice": _CODICE})
        self.assertEqual(resp.json()["error"]["code"], "E_CREDENZIALE_BLOCCATA")
        self.sf_repo.registra_uso.assert_not_called()
        self.mock_chiudi_accesso_riuscito.assert_not_called()

    def test_device_disabilitato_fra_i_due_passi_401(self):
        self.sf_repo.get_device.return_value = {"stato": "ASSENTE"}
        self._assert_sfida_rifiutata(self._post({"sfida": _sfida(), "codice": _CODICE}))

    def test_veste_spenta_fra_i_due_passi_401(self):
        self.auth_repo.get_veste_utilizzabile.return_value = None
        self._assert_sfida_rifiutata(self._post({"sfida": _sfida(), "codice": _CODICE}))

    def test_senza_prova_non_e_un_tentativo(self):
        resp = self._post({"sfida": _sfida()})
        self.assertEqual(resp.status_code, 400, resp.content)
        self.auth_repo.registra_tentativo_login.assert_not_called()

    def test_segreto_illeggibile_non_e_un_tentativo(self):
        self.sf_repo.get_device.return_value["secret_encrypted"] = "non-un-token-fernet"
        resp = self._post({"sfida": _sfida(), "codice": _CODICE})
        self.assertEqual(resp.status_code, 500, resp.content)
        self.auth_repo.registra_tentativo_login.assert_not_called()

    def test_cambio_password_pendente_nella_risposta(self):
        self.mock_chiudi_accesso_riuscito.return_value = True
        resp = self._post({"sfida": _sfida(), "codice": _CODICE})
        self.assertTrue(resp.json()["data"]["password_change_required"])

    # Scopo: Il secondo passo ha un contatore di frequenza SUO. Condiviso con
    #        quello del login, ogni accesso col secondo fattore ne consumava
    #        due e lo smoke col secondo login si fermava a 429 (collaudo del
    #        2026-10-02); da un ufficio con un solo IP, due o tre persone.
    def test_il_secondo_passo_ha_un_contatore_suo(self):
        from apps.core.api.auth_views import AdminTokenView
        from apps.core.api.throttling import SecondoFattoreRateThrottle

        self.assertEqual(_THROTTLE_DEL_SECONDO_PASSO, [SecondoFattoreRateThrottle])
        scope_login = {t.scope for t in AdminTokenView.throttle_classes}
        self.assertNotIn(SecondoFattoreRateThrottle.scope, scope_login)
