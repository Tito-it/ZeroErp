# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test di `totp_service`: la verifica del codice e il PASSO che
#        restituisce (quello che va al DB per l'anti-replay), i codici di
#        recupero e la loro impronta, il QR. Funzioni pure, niente DB.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_vettori_rfc_6238 — il codice dell'RFC (SHA1, 6 cifre) nei suoi istanti
 2) test_passo_di — floor(t / 30), sede unica del periodo
 3) test_verifica_restituisce_il_passo_accettato — passo di adesso
 4) test_verifica_accetta_il_passo_precedente_e_successivo
 5) test_verifica_rifiuta_due_passi_di_distanza — il DB non limita il futuro (§9.5.6)
 6) test_verifica_codice_malformato — lettere, lunghezza, vuoto
 7) test_verifica_tollera_gli_spazi — «123 456»
 8) test_nuovo_segreto_160_bit_base32
 9) test_codici_recupero_forma_e_distinti
10) test_impronta_uguale_per_lo_stesso_codice_scritto_diversamente
11) test_impronta_diversa_per_codici_diversi
12) test_uri_e_qr — emittente nell'indirizzo, SVG in linea
"""

import base64
import re

from django.test import SimpleTestCase

from apps.core.services import totp_service

# Il segreto dei vettori dell'RFC 6238 (Appendice B, SHA1): "12345678901234567890".
_SEGRETO_RFC = base64.b32encode(b"12345678901234567890").decode()


class TotpServiceTests(SimpleTestCase):
    # Scopo: Appendice B dell'RFC 6238 (SHA1), troncata alle 6 cifre
    # (RFC 4226: le ultime cifre del valore a 8).
    def test_vettori_rfc_6238(self):
        for istante, codice_8 in (
            (59, "94287082"),
            (1111111109, "07081804"),
            (1234567890, "89005924"),
            (2000000000, "69279037"),
        ):
            passo = totp_service.passo_di(istante)
            self.assertEqual(
                totp_service.verifica_codice(_SEGRETO_RFC, codice_8[-6:], passo_attuale=passo),
                passo,
                istante,
            )

    def test_passo_di(self):
        self.assertEqual(totp_service.passo_di(0), 0)
        self.assertEqual(totp_service.passo_di(29.9), 0)
        self.assertEqual(totp_service.passo_di(30), 1)
        self.assertEqual(totp_service.passo_di(59), 1)

    def test_verifica_restituisce_il_passo_accettato(self):
        # 59 s -> passo 1, codice 287082.
        self.assertEqual(totp_service.verifica_codice(_SEGRETO_RFC, "287082", passo_attuale=1), 1)

    # Scopo: L'orologio del telefono un passo indietro o avanti: si accetta,
    # e il passo restituito e' quello del CODICE, non quello di adesso.
    def test_verifica_accetta_il_passo_precedente_e_successivo(self):
        self.assertEqual(totp_service.verifica_codice(_SEGRETO_RFC, "287082", passo_attuale=2), 1)
        self.assertEqual(totp_service.verifica_codice(_SEGRETO_RFC, "287082", passo_attuale=0), 1)

    # Scopo: Due passi di distanza no. Verso il futuro conta di piu': il DB
    # non lo limita, e un passo accettato in avanti blocca i codici buoni.
    def test_verifica_rifiuta_due_passi_di_distanza(self):
        self.assertIsNone(totp_service.verifica_codice(_SEGRETO_RFC, "287082", passo_attuale=3))
        self.assertIsNone(totp_service.verifica_codice(_SEGRETO_RFC, "287082", passo_attuale=-1))

    def test_verifica_codice_malformato(self):
        for codice in ("", "28708", "2870822", "28708a", "abcdef"):
            self.assertIsNone(
                totp_service.verifica_codice(_SEGRETO_RFC, codice, passo_attuale=1), codice,
            )

    def test_verifica_tollera_gli_spazi(self):
        self.assertEqual(totp_service.verifica_codice(_SEGRETO_RFC, " 287 082 ", passo_attuale=1), 1)

    def test_nuovo_segreto_160_bit_base32(self):
        segreto = totp_service.nuovo_segreto()
        self.assertEqual(len(base64.b32decode(segreto)), 20)
        self.assertNotEqual(segreto, totp_service.nuovo_segreto())

    def test_codici_recupero_forma_e_distinti(self):
        codici = totp_service.nuovi_codici_recupero()
        self.assertEqual(len(codici), totp_service.NUMERO_CODICI_RECUPERO)
        self.assertEqual(len(set(codici)), len(codici))
        for codice in codici:
            self.assertRegex(codice, r"^[0-9A-HJKMNP-TV-Z]{4}(-[0-9A-HJKMNP-TV-Z]{4}){3}$")

    # Scopo: Minuscole, senza trattini, con O al posto di 0 e L al posto
    # di 1: per chi digita e' lo stesso codice, quindi la stessa impronta.
    def test_impronta_uguale_per_lo_stesso_codice_scritto_diversamente(self):
        attesa = totp_service.impronta_codice_recupero("AB01-CD23-EF45-GH67")
        for scritto in ("ab01cd23ef45gh67", "AB O1-CD23-EF45-GH67", "ABOL-CD23-EF45-GH67"):
            self.assertEqual(totp_service.impronta_codice_recupero(scritto), attesa, scritto)
        self.assertRegex(attesa, r"^[0-9a-f]{64}$")

    def test_impronta_diversa_per_codici_diversi(self):
        self.assertNotEqual(
            totp_service.impronta_codice_recupero("AB01-CD23-EF45-GH67"),
            totp_service.impronta_codice_recupero("AB01-CD23-EF45-GH68"),
        )

    def test_uri_e_qr(self):
        uri = totp_service.uri_configurazione(_SEGRETO_RFC, "mctit")
        self.assertTrue(uri.startswith("otpauth://totp/"), uri)
        self.assertIn(f"issuer={totp_service.EMITTENTE}", uri)
        self.assertIn(f"secret={_SEGRETO_RFC}", uri)
        qr = totp_service.qr_data_uri(uri)
        self.assertTrue(re.match(r"^data:image/svg\+xml;", qr), qr[:40])
