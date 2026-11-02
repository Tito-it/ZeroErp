# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per cf_validator_it — validazione congruenza CF italiano.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_estrai_dati_cf_maschio — estrazione corretta dati PF maschio
 2) test_estrai_dati_cf_femmina — giorno +40 per femmine
 3) test_estrai_dati_cf_omocodia — decodifica omocodia
 4) test_congruenza_ok — tutti i dati congruenti
 5) test_congruenza_anno_errato — anno non corrisponde
 6) test_congruenza_mese_errato — mese non corrisponde
 7) test_congruenza_giorno_errato — giorno non corrisponde
 8) test_congruenza_sesso_errato — sesso non corrisponde
 9) test_congruenza_comune_errato — codice catastale non corrisponde
10) test_congruenza_parziale — verifica solo dati forniti
11) test_cf_invalido — CF troppo corto
12) test_omocodia_reale — CF omocodico reale (BLLDNL62H30A9Q4D)
"""

from datetime import date
from unittest import TestCase

from apps.anagrafiche.services.cf_validator_it import (
    _estrai_dati_cf,
    valida_cf_congruenza_it,
)


class TestEstraiDatiCF(TestCase):
    """Test estrazione dati da CF."""

    def test_estrai_dati_cf_maschio(self):
        """RSSMRA80A01H501U — Mario Rossi, M, 01/01/1980, Roma (H501)."""
        dati = _estrai_dati_cf("RSSMRA80A01H501U")
        self.assertIsNotNone(dati)
        self.assertEqual(dati["anno"], 1980)
        self.assertEqual(dati["mese"], 1)
        self.assertEqual(dati["giorno"], 1)
        self.assertEqual(dati["sesso"], "M")
        self.assertEqual(dati["codice_catastale"], "H501")

    def test_estrai_dati_cf_femmina(self):
        """RSSMRA80A41H501X — Maria Rossi, F, 01/01/1980, Roma (H501)."""
        dati = _estrai_dati_cf("RSSMRA80A41H501X")
        self.assertIsNotNone(dati)
        self.assertEqual(dati["giorno"], 1)
        self.assertEqual(dati["sesso"], "F")

    def test_estrai_dati_cf_omocodia(self):
        """Omocodia: cifre sostituite con lettere nelle posizioni standard.
        RSSMRA8LA01H5L1 — posizione 7 (0→L), posizione 14 (0→L)."""
        # Posizione 7: '8' → invariato, posizione 8: '0' → 'L'
        # Anno: 8L → 80 (L=0). Codice catastale: H5L1 → H501 (L=0)
        dati = _estrai_dati_cf("RSSMRA8LA01H5L1E")
        self.assertIsNotNone(dati)
        self.assertEqual(dati["anno"], 1980)
        self.assertEqual(dati["giorno"], 1)
        self.assertEqual(dati["codice_catastale"], "H501")


class TestValidaCFCongruenza(TestCase):
    """Test congruenza CF con dati anagrafici."""

    def test_congruenza_ok(self):
        """Tutti i dati congruenti → nessun errore."""
        errors = valida_cf_congruenza_it(
            "RSSMRA80A01H501U",
            data_nascita=date(1980, 1, 1),
            sesso="M",
            codice_catastale_comune="H501",
        )
        self.assertEqual(errors, [])

    def test_congruenza_anno_errato(self):
        """Anno diverso → errore."""
        errors = valida_cf_congruenza_it(
            "RSSMRA80A01H501U",
            data_nascita=date(1985, 1, 1),
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("Anno", errors[0])

    def test_congruenza_mese_errato(self):
        """Mese diverso → errore."""
        errors = valida_cf_congruenza_it(
            "RSSMRA80A01H501U",
            data_nascita=date(1980, 3, 1),
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("Mese", errors[0])

    def test_congruenza_giorno_errato(self):
        """Giorno diverso → errore."""
        errors = valida_cf_congruenza_it(
            "RSSMRA80A01H501U",
            data_nascita=date(1980, 1, 15),
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("Giorno", errors[0])

    def test_congruenza_sesso_errato(self):
        """Sesso diverso → errore."""
        errors = valida_cf_congruenza_it(
            "RSSMRA80A01H501U",
            sesso="F",
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("Sesso", errors[0])

    def test_congruenza_comune_errato(self):
        """Codice catastale diverso → errore."""
        errors = valida_cf_congruenza_it(
            "RSSMRA80A01H501U",
            codice_catastale_comune="F205",
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("catastale", errors[0])

    def test_congruenza_parziale(self):
        """Solo sesso fornito e congruente → ok."""
        errors = valida_cf_congruenza_it(
            "RSSMRA80A01H501U",
            sesso="M",
        )
        self.assertEqual(errors, [])

    def test_cf_invalido(self):
        """CF troppo corto → errore formato."""
        errors = valida_cf_congruenza_it("ABC123")
        self.assertEqual(len(errors), 1)
        self.assertIn("Formato", errors[0])

    def test_omocodia_reale(self):
        """CF omocodico reale: BLLDNL62H30A9Q4D — Q in posizione 13 (Q→4)."""
        dati = _estrai_dati_cf("BLLDNL62H30A9Q4D")
        self.assertIsNotNone(dati)
        self.assertEqual(dati["anno"], 1962)
        self.assertEqual(dati["mese"], 6)
        self.assertEqual(dati["giorno"], 30)
        self.assertEqual(dati["sesso"], "M")
        self.assertEqual(dati["codice_catastale"], "A944")
        # Congruenza completa
        errors = valida_cf_congruenza_it(
            "BLLDNL62H30A9Q4D",
            data_nascita=date(1962, 6, 30),
            sesso="M",
            codice_catastale_comune="A944",
        )
        self.assertEqual(errors, [])
