# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del BB get_client_ip (hop fidato di X-Forwarded-For) e
#        dell'ident dei throttle DRF che lo riusano. Senza DB.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) GetClientIpSenzaProxyTests.test_remote_addr
2) GetClientIpSenzaProxyTests.test_xff_forgiato_ignorato
3) GetClientIpSenzaProxyTests.test_remote_addr_assente_o_malformato
4) GetClientIpUnProxyTests.test_valore_giusto_fra_tre
5) GetClientIpUnProxyTests.test_un_solo_valore
6) GetClientIpUnProxyTests.test_xff_assente
7) GetClientIpUnProxyTests.test_xff_malformato
8) GetClientIpUnProxyTests.test_ipv6_normalizzato
9) GetClientIpDueProxyTests.test_secondo_da_destra
10) GetClientIpDueProxyTests.test_meno_valori_dei_proxy
11) ThrottleIdentTests.test_ident_dal_bb
12) ThrottleIdentTests.test_ident_ip_sconosciuto_condiviso
13) ThrottleIdentTests.test_limite_scattato_scrive_il_log_di_sicurezza
14) ThrottleIdentTests.test_richiesta_ammessa_non_scrive
15) ThrottleIdentTests.test_la_conferma_con_link_ha_il_suo_contatore
16) ThrottleIdentTests.test_un_blocco_una_riga_sola
17) ThrottleRitmiTests.test_login_e_secondo_passo_leggono_il_ritmo_dalle_impostazioni
18) ThrottleRitmiTests.test_il_default_resta_cinque_ogni_cinque_minuti
"""

from unittest.mock import patch

from django.core.cache.backends.locmem import LocMemCache
from django.test import RequestFactory, SimpleTestCase, override_settings
from rest_framework.throttling import SimpleRateThrottle

from apps.core.api.throttling import (
    ConfermaTokenRateThrottle,
    LoginRateThrottle,
    PasswordResetRateThrottle,
    SearchBurstRateThrottle,
)
from apps.core.services.request_context import get_client_ip


# Scopo: Costruisce una request con REMOTE_ADDR e, se dato, X-Forwarded-For.
def _request(remote_addr: str | None = "10.9.9.9", xff: str | None = None):
    meta = {}
    if xff is not None:
        meta["HTTP_X_FORWARDED_FOR"] = xff
    request = RequestFactory().get("/", **meta)
    if remote_addr is None:
        request.META.pop("REMOTE_ADDR", None)
    else:
        request.META["REMOTE_ADDR"] = remote_addr
    return request


@override_settings(TRUSTED_PROXY_COUNT=0)
class GetClientIpSenzaProxyTests(SimpleTestCase):
    """Nessun proxy dichiarato: conta solo il peer TCP."""

    # Scopo: Senza proxy l'IP e' REMOTE_ADDR.
    def test_remote_addr(self):
        self.assertEqual(get_client_ip(_request("172.16.0.1")), "172.16.0.1")

    # Scopo: Un X-Forwarded-For scritto dal client non sposta l'IP.
    def test_xff_forgiato_ignorato(self):
        request = _request("172.16.0.1", xff="1.2.3.4")
        self.assertEqual(get_client_ip(request), "172.16.0.1")

    # Scopo: REMOTE_ADDR assente, vuoto o non IP → None.
    def test_remote_addr_assente_o_malformato(self):
        self.assertIsNone(get_client_ip(_request(None)))
        self.assertIsNone(get_client_ip(_request("")))
        self.assertIsNone(get_client_ip(_request("non-un-ip")))


@override_settings(TRUSTED_PROXY_COUNT=1)
class GetClientIpUnProxyTests(SimpleTestCase):
    """Un proxy fidato (Nginx): vale l'ultimo valore, quello che ha accodato lui."""

    # Scopo: Con un proxy, fra tre valori vale quello a destra (i primi li scrive il client).
    def test_valore_giusto_fra_tre(self):
        request = _request("127.0.0.1", xff="1.1.1.1, 2.2.2.2, 203.0.113.7")
        self.assertEqual(get_client_ip(request), "203.0.113.7")

    # Scopo: Header con il solo valore di Nginx.
    def test_un_solo_valore(self):
        request = _request("127.0.0.1", xff="203.0.113.7")
        self.assertEqual(get_client_ip(request), "203.0.113.7")

    # Scopo: Senza header la richiesta non e' passata dal proxy: None, non REMOTE_ADDR.
    def test_xff_assente(self):
        self.assertIsNone(get_client_ip(_request("127.0.0.1")))
        self.assertIsNone(get_client_ip(_request("127.0.0.1", xff="")))

    # Scopo: Valore fidato malformato → None, senza ripiegare su un altro hop.
    def test_xff_malformato(self):
        self.assertIsNone(get_client_ip(_request("127.0.0.1", xff="1.1.1.1, pippo")))
        self.assertIsNone(get_client_ip(_request("127.0.0.1", xff="1.1.1.1,")))
        self.assertIsNone(get_client_ip(_request("127.0.0.1", xff="203.0.113.7:4431")))

    # Scopo: IPv6 riportato in forma canonica (stringa valida per inet).
    def test_ipv6_normalizzato(self):
        request = _request("127.0.0.1", xff="1.1.1.1, 2001:DB8:0:0::1")
        self.assertEqual(get_client_ip(request), "2001:db8::1")


@override_settings(TRUSTED_PROXY_COUNT=2)
class GetClientIpDueProxyTests(SimpleTestCase):
    """Due proxy fidati (es. bilanciatore + Nginx)."""

    # Scopo: Con due proxy vale il secondo valore da destra.
    def test_secondo_da_destra(self):
        request = _request("127.0.0.1", xff="1.1.1.1, 203.0.113.7, 10.0.0.2")
        self.assertEqual(get_client_ip(request), "203.0.113.7")

    # Scopo: Meno valori dei proxy dichiarati → None (catena non attraversata).
    def test_meno_valori_dei_proxy(self):
        self.assertIsNone(get_client_ip(_request("127.0.0.1", xff="203.0.113.7")))


@override_settings(TRUSTED_PROXY_COUNT=1)
class ThrottleIdentTests(SimpleTestCase):
    """I throttle prendono l'IP dal BB, non dalla lettura propria di DRF."""

    _THROTTLES = (LoginRateThrottle, PasswordResetRateThrottle, ConfermaTokenRateThrottle, SearchBurstRateThrottle)

    # Scopo: L'ident e' l'IP fidato: cambiare i valori scritti dal client non cambia contatore.
    def test_ident_dal_bb(self):
        for throttle_cls in self._THROTTLES:
            with self.subTest(throttle=throttle_cls.__name__):
                throttle = throttle_cls()
                a = throttle.get_ident(_request("127.0.0.1", xff="1.1.1.1, 203.0.113.7"))
                b = throttle.get_ident(_request("127.0.0.1", xff="9.9.9.9, 203.0.113.7"))
                self.assertEqual(a, "203.0.113.7")
                self.assertEqual(b, a)

    # Scopo: IP non ricavabile → un contatore comune, non una via di fuga dal limite.
    def test_ident_ip_sconosciuto_condiviso(self):
        for throttle_cls in self._THROTTLES:
            with self.subTest(throttle=throttle_cls.__name__):
                throttle = throttle_cls()
                a = throttle.get_ident(_request("127.0.0.1"))
                b = throttle.get_ident(_request("127.0.0.1", xff="1.1.1.1, pippo"))
                self.assertEqual(a, "ip-sconosciuto")
                self.assertEqual(b, a)

    # Scopo: Un 429 su un endpoint anonimo non lo registra nessun altro
    #        (`request_log` vede solo le richieste autenticate): il limite
    #        scrive nel log di sicurezza, con scope, provenienza e attesa.
    def test_limite_scattato_scrive_il_log_di_sicurezza(self):
        throttle = self._con_cache_propria(PasswordResetRateThrottle())
        richiesta = _request("127.0.0.1", xff="203.0.113.7")
        with patch.object(SimpleRateThrottle, "allow_request", return_value=False), \
                patch.object(SimpleRateThrottle, "wait", return_value=421.6), \
                self.assertLogs("security", level="WARNING") as log:
            self.assertFalse(throttle.allow_request(richiesta, view=None))
        self.assertIn("security.limite_frequenza scope=password_reset", log.output[0])
        self.assertIn("provenienza=203.0.113.7", log.output[0])
        self.assertIn("attesa_s=422", log.output[0])

    # Scopo: Il throttle con una cache in memoria SUA: il segnaposto «blocco
    #        gia' nel log» non deve passare da un test all'altro, ne' finire
    #        nella cache vera (Redis) della macchina.
    @staticmethod
    def _con_cache_propria(throttle):
        throttle.cache = LocMemCache(f"throttle-test-{id(throttle)}", {})
        return throttle

    def test_richiesta_ammessa_non_scrive(self):
        throttle = LoginRateThrottle()
        with patch.object(SimpleRateThrottle, "allow_request", return_value=True), \
                self.assertNoLogs("security", level="WARNING"):
            self.assertTrue(throttle.allow_request(_request("127.0.0.1"), view=None))

    # Scopo: La richiesta del link e la conferma col link (reset e attivazione
    #        dell'invito) contano su contatori DIVERSI: una password rifiutata
    #        alla conferma non consuma le richieste del link (2026-10-02).
    def test_la_conferma_con_link_ha_il_suo_contatore(self):
        from apps.core.api.attivazione_veste_views import AttivazioneVesteView
        from apps.core.api.password_reset_views import PasswordResetConfirmView, PasswordResetRequestView

        self.assertEqual(PasswordResetRequestView.throttle_classes, [PasswordResetRateThrottle])
        self.assertEqual(PasswordResetConfirmView.throttle_classes, [ConfermaTokenRateThrottle])
        self.assertEqual(AttivazioneVesteView.throttle_classes, [ConfermaTokenRateThrottle])
        self.assertNotEqual(PasswordResetRateThrottle.scope, ConfermaTokenRateThrottle.scope)

    # Scopo: Un blocco, UNA riga: le richieste respinte dopo la prima, nella
    #        stessa attesa, non riscrivono la stessa notizia; un'altra
    #        provenienza bloccata ha la sua (2026-10-02).
    def test_un_blocco_una_riga_sola(self):
        throttle = self._con_cache_propria(LoginRateThrottle())
        da_a = _request("127.0.0.1", xff="203.0.113.7")
        da_b = _request("127.0.0.1", xff="198.51.100.9")
        with patch.object(SimpleRateThrottle, "allow_request", return_value=False), \
                patch.object(SimpleRateThrottle, "wait", return_value=120), \
                self.assertLogs("security", level="WARNING") as log:
            for _ in range(5):
                self.assertFalse(throttle.allow_request(da_a, view=None))
            self.assertFalse(throttle.allow_request(da_b, view=None))
        self.assertEqual(len(log.output), 2)
        self.assertIn("provenienza=203.0.113.7", log.output[0])
        self.assertIn("provenienza=198.51.100.9", log.output[1])


class ThrottleRitmiTests(SimpleTestCase):
    """I ritmi del login e del secondo passo vengono dalle impostazioni (env
    DJANGO_API_LOGIN_THROTTLE_RATE / _SECONDO_FATTORE_), e il default e' il
    presidio di produzione: si alzano solo in sviluppo, per gli smoke."""

    # 17. Le classi non hanno un ritmo proprio scritto a mano.
    def test_login_e_secondo_passo_leggono_il_ritmo_dalle_impostazioni(self):
        from django.conf import settings

        from apps.core.api.throttling import SecondoFattoreRateThrottle

        self.assertEqual(LoginRateThrottle.rate, settings.API_LOGIN_THROTTLE_RATE)
        self.assertEqual(
            SecondoFattoreRateThrottle.rate, settings.API_SECONDO_FATTORE_THROTTLE_RATE,
        )

    # 18. Senza variabile d'ambiente il ritmo e' quello di sempre: chi tocca il
    #     default allenta il freno anche in produzione, e questo test lo dice.
    #     (Si legge il sorgente: le impostazioni sono gia' caricate, e in un
    #     ambiente con la variabile impostata il valore non direbbe il default.)
    def test_il_default_resta_cinque_ogni_cinque_minuti(self):
        from zeroerp_backend import settings as modulo

        with open(modulo.__file__, encoding="utf-8") as f:
            sorgente = f.read()
        self.assertIn('env("DJANGO_API_LOGIN_THROTTLE_RATE", "5/5m")', sorgente)
        self.assertIn('env("DJANGO_API_SECONDO_FATTORE_THROTTLE_RATE", "5/5m")', sorgente)

