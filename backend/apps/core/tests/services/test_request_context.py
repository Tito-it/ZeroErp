# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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
"""

from django.test import RequestFactory, SimpleTestCase, override_settings

from apps.core.api.throttling import (
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

    _THROTTLES = (LoginRateThrottle, PasswordResetRateThrottle, SearchBurstRateThrottle)

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
