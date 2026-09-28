# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio di HSTS e redirect HTTPS in Django
#        (brief-be-fe-sicurezza-header-token-mfa §1.6): il redirect scatta su
#        HTTP, non su `/health` e non su chi arriva da Nginx; l'header HSTS
#        porta il valore scelto e niente sottodomini/preload; la variabile
#        d'ambiente non ha ripiego fuori da DEBUG; ogni smoke bash si dichiara
#        HTTPS.
# Note: il runner spegne `SECURE_SSL_REDIRECT` per tutta la suite
#       (`test_runner.py`): qui lo si riaccende apposta.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) RedirectHttpsTests.test_http_rediretto_in_https
2) RedirectHttpsTests.test_health_non_rediretto
3) RedirectHttpsTests.test_da_nginx_non_rediretto
4) HstsTests.test_header_col_valore_scelto_senza_sottodomini_ne_preload
5) HstsTests.test_zero_nessun_header
6) HstsSettingsTests.test_obbligatoria_fuori_da_debug
7) HstsSettingsTests.test_in_debug_ripiega_su_zero
8) HstsSettingsTests.test_valori_non_validi_rifiutati
9) HstsSettingsTests.test_valori_validi
10) SmokeBashTests.test_ogni_smoke_si_dichiara_https
11) HstsSettingsTests.test_intero_non_negativo_nomina_variabile_e_valore
"""

import re
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, SimpleTestCase, override_settings

from zeroerp_backend.settings import parse_hsts_seconds, parse_intero_non_negativo

# Una rotta qualunque che non e' `/health`: il redirect scatta prima di
# risolverla, quindi non serve che esista.
_ROTTA = "/api/v1/core/me/"


@override_settings(SECURE_SSL_REDIRECT=True)
class RedirectHttpsTests(SimpleTestCase):
    def setUp(self) -> None:
        self.client = Client()

    # Scopo: Una richiesta HTTP va in HTTPS sulla stessa rotta.
    def test_http_rediretto_in_https(self):
        risposta = self.client.get(_ROTTA)
        self.assertEqual(risposta.status_code, 301)
        self.assertTrue(risposta["Location"].startswith("https://"))
        self.assertTrue(risposta["Location"].endswith(_ROTTA))

    # Scopo: `/health` risponde anche in HTTP diretto (controlli locali, smoke
    #        del container in CI): e' in `SECURE_REDIRECT_EXEMPT`.
    def test_health_non_rediretto(self):
        self.assertEqual(self.client.get("/health").status_code, 200)

    # Scopo: Dietro Nginx (`X-Forwarded-Proto: https`) la richiesta e' gia'
    #        sicura: nessun redirect, arriva alla rotta.
    def test_da_nginx_non_rediretto(self):
        risposta = self.client.get("/non-esiste/", headers={"X-Forwarded-Proto": "https"})
        self.assertEqual(risposta.status_code, 404)


class HstsTests(SimpleTestCase):
    def setUp(self) -> None:
        self.client = Client()

    # Scopo: Su HTTPS l'header porta il valore scelto; sottodomini e preload
    #        restano fuori (riguardano il dominio intero, non ZeroErp).
    @override_settings(SECURE_HSTS_SECONDS=300)
    def test_header_col_valore_scelto_senza_sottodomini_ne_preload(self):
        risposta = self.client.get("/health", secure=True)
        self.assertEqual(risposta["Strict-Transport-Security"], "max-age=300")
        self.assertFalse(settings.SECURE_HSTS_INCLUDE_SUBDOMAINS)
        self.assertFalse(settings.SECURE_HSTS_PRELOAD)

    # Scopo: `0` dichiarato (macchina con certificato auto-firmato): nessun header.
    @override_settings(SECURE_HSTS_SECONDS=0)
    def test_zero_nessun_header(self):
        risposta = self.client.get("/health", secure=True)
        self.assertNotIn("Strict-Transport-Security", risposta)


class HstsSettingsTests(SimpleTestCase):
    # Scopo: Fuori da DEBUG nessun ripiego: chi installa deve scegliere.
    def test_obbligatoria_fuori_da_debug(self):
        for valore in (None, "", "  "):
            with self.subTest(valore=valore), self.assertRaises(ImproperlyConfigured):
                parse_hsts_seconds(valore, debug=False)

    # Scopo: In DEBUG (sviluppo col solo Vite) l'assenza vale 0.
    def test_in_debug_ripiega_su_zero(self):
        self.assertEqual(parse_hsts_seconds(None, debug=True), 0)

    # Scopo: Un numero negativo o non intero ferma l'avvio.
    def test_valori_non_validi_rifiutati(self):
        for valore in ("-1", "un anno", "1.5"):
            with self.subTest(valore=valore), self.assertRaises(ImproperlyConfigured):
                parse_hsts_seconds(valore, debug=False)

    # Scopo: `0` e' una scelta valida (dichiarata), non un'assenza.
    def test_valori_validi(self):
        self.assertEqual(parse_hsts_seconds("0", debug=False), 0)
        self.assertEqual(parse_hsts_seconds("31536000", debug=False), 31536000)


    # Scopo: il BB condiviso con DJANGO_TRUSTED_PROXY_COUNT: il messaggio dice
    #        QUALE variabile e cosa e' arrivato.
    def test_intero_non_negativo_nomina_variabile_e_valore(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            parse_intero_non_negativo("DJANGO_TRUSTED_PROXY_COUNT", "due")
        self.assertIn("DJANGO_TRUSTED_PROXY_COUNT", str(ctx.exception))
        self.assertIn("'due'", str(ctx.exception))
        self.assertEqual(parse_intero_non_negativo("X", "1"), 1)


class SmokeBashTests(SimpleTestCase):
    # Scopo: Ogni smoke bash che chiama Gunicorn (`BASE_URL`) include
    #        `_smoke_https.sh` DOPO la riga `BASE_URL=`, e non aggira la
    #        funzione `curl` con `command curl`: altrimenti col redirect acceso
    #        ogni sua chiamata sarebbe un 301.
    def test_ogni_smoke_si_dichiara_https(self):
        cartella = Path(settings.BASE_DIR) / "scripts" / "tests"
        smoke = sorted(p for p in cartella.glob("*.sh") if not p.name.startswith("_"))
        inclusione = re.compile(r'^source .*_smoke_https\.sh"?\s*$', re.MULTILINE)
        controllati = 0
        for script in smoke:
            testo = script.read_text(encoding="utf-8")
            base_url = re.search(r"^BASE_URL=", testo, re.MULTILINE)
            if base_url is None:
                continue
            controllati += 1
            with self.subTest(script=script.name):
                trovata = inclusione.search(testo, base_url.end())
                self.assertIsNotNone(trovata, "manca `source .../_smoke_https.sh` dopo BASE_URL=")
                self.assertNotIn("command curl", testo)
        # Il test non deve passare a vuoto se la cartella si sposta.
        self.assertGreater(controllati, 0)
