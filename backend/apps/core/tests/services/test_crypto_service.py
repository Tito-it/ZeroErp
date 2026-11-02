# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per crypto_service — encrypt/decrypt/ricifra con
#        MultiFernet sulle chiavi `FIELD_ENCRYPTION_KEYS`, e la lettura della
#        variabile d'ambiente in `settings.parse_chiavi_cifratura`.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) CryptoServiceTests.test_encrypt_decrypt_roundtrip
2) CryptoServiceTests.test_decrypt_invalid_token_raises
3) CryptoServiceTests.test_encrypt_produces_different_tokens
4) CryptoServiceTests.test_empty_string_roundtrip
5) CryptoServiceTests.test_cifra_con_la_prima_chiave
6) CryptoServiceTests.test_decifra_con_una_chiave_non_prima
7) CryptoServiceTests.test_la_secret_key_non_tocca_i_dati_cifrati
8) CryptoServiceTests.test_ricifra_porta_il_token_sulla_prima_chiave
9) CryptoServiceTests.test_ricifra_con_chiave_extra_legge_e_non_scrive_con_quella
10) CryptoServiceTests.test_ricifra_token_illeggibile_solleva
11) ChiaviCifraturaSettingsTests.test_elenco_valido_in_ordine
12) ChiaviCifraturaSettingsTests.test_vuota_rifiutata
13) ChiaviCifraturaSettingsTests.test_chiave_non_fernet_rifiutata_senza_mostrarla
14) ChiaviCifraturaSettingsTests.test_chiave_duplicata_rifiutata
"""

from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from apps.core.services import crypto_service
from zeroerp_backend.settings import parse_chiavi_cifratura

_NUOVA = Fernet.generate_key().decode()
_VECCHIA = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEYS=[_NUOVA, _VECCHIA])
class CryptoServiceTests(SimpleTestCase):

    # Scopo: Verifica che encrypt + decrypt restituisca il testo originale.
    def test_encrypt_decrypt_roundtrip(self):
        plaintext = "mia-password-smtp-segreta"
        encrypted = crypto_service.encrypt(plaintext)
        self.assertNotEqual(encrypted, plaintext)
        self.assertEqual(crypto_service.decrypt(encrypted), plaintext)

    # Scopo: Verifica che decrypt con token invalido lanci ValueError.
    def test_decrypt_invalid_token_raises(self):
        with self.assertRaises(ValueError):
            crypto_service.decrypt("token-invalido-non-fernet")

    # Scopo: Verifica che due encrypt dello stesso testo producano token diversi (nonce).
    def test_encrypt_produces_different_tokens(self):
        t1 = crypto_service.encrypt("stessa-password")
        t2 = crypto_service.encrypt("stessa-password")
        self.assertNotEqual(t1, t2)

    # Scopo: Verifica roundtrip con stringa vuota.
    def test_empty_string_roundtrip(self):
        encrypted = crypto_service.encrypt("")
        self.assertEqual(crypto_service.decrypt(encrypted), "")

    # Scopo: Il token nasce con la PRIMA chiave: la sola prima lo apre.
    def test_cifra_con_la_prima_chiave(self):
        token = crypto_service.encrypt("segreto")
        self.assertEqual(Fernet(_NUOVA).decrypt(token.encode()), b"segreto")

    # Scopo: Un token della chiave in seconda posizione si legge ancora: e'
    #        cio' che rende la rotazione indolore.
    def test_decifra_con_una_chiave_non_prima(self):
        token = Fernet(_VECCHIA).encrypt(b"di prima").decode()
        self.assertEqual(crypto_service.decrypt(token), "di prima")

    # Scopo: ⭐ La ragione del cambio: ruotare la SECRET_KEY non rende
    #        illeggibili i dati cifrati.
    def test_la_secret_key_non_tocca_i_dati_cifrati(self):
        token = crypto_service.encrypt("smtp")
        with override_settings(SECRET_KEY="un-altra-secret-key-del-tutto-diversa"):
            self.assertEqual(crypto_service.decrypt(token), "smtp")

    # Scopo: ricifra prende un token della chiave vecchia e lo riscrive con la
    #        nuova: tolta la vecchia, si legge ancora.
    def test_ricifra_porta_il_token_sulla_prima_chiave(self):
        vecchio = Fernet(_VECCHIA).encrypt(b"da ruotare").decode()
        nuovo = crypto_service.ricifra(vecchio)
        with override_settings(FIELD_ENCRYPTION_KEYS=[_NUOVA]):
            self.assertEqual(crypto_service.decrypt(nuovo), "da ruotare")

    # Scopo: Una chiave extra serve solo a LEGGERE: il token ri-cifrato non
    #        dipende da lei, e decrypt senza di lei non apre il vecchio.
    def test_ricifra_con_chiave_extra_legge_e_non_scrive_con_quella(self):
        extra = Fernet.generate_key()
        vecchio = Fernet(extra).encrypt(b"legacy").decode()
        with self.assertRaises(ValueError):
            crypto_service.decrypt(vecchio)
        nuovo = crypto_service.ricifra(vecchio, chiavi_extra=[extra])
        self.assertEqual(Fernet(_NUOVA).decrypt(nuovo.encode()), b"legacy")

    # Scopo: Un token che nessuna chiave apre e' ValueError, anche vuoto.
    def test_ricifra_token_illeggibile_solleva(self):
        estraneo = Fernet(Fernet.generate_key()).encrypt(b"x").decode()
        for token in (estraneo, "", "non-fernet"):
            with self.subTest(token=token), self.assertRaises(ValueError):
                crypto_service.ricifra(token)


class ChiaviCifraturaSettingsTests(SimpleTestCase):

    # Scopo: Virgole e spazi ai bordi si tollerano; l'ordine resta quello
    #        scritto, perche' la prima e' quella che cifra.
    def test_elenco_valido_in_ordine(self):
        self.assertEqual(
            parse_chiavi_cifratura(f" {_NUOVA} , {_VECCHIA},"), [_NUOVA, _VECCHIA],
        )

    # Scopo: Nessun default: vuota o solo virgole non avvia il backend.
    def test_vuota_rifiutata(self):
        for valore in ("", " ", ",,"):
            with self.subTest(valore=valore), self.assertRaises(ImproperlyConfigured):
                parse_chiavi_cifratura(valore)

    # Scopo: Una chiave non Fernet (es. una SECRET_KEY incollata per sbaglio)
    #        e' rifiutata, e il messaggio dice la posizione, non la chiave.
    def test_chiave_non_fernet_rifiutata_senza_mostrarla(self):
        sbagliata = "una-secret-key-di-django-non-una-chiave-fernet"
        with self.assertRaises(ImproperlyConfigured) as ctx:
            parse_chiavi_cifratura(f"{_NUOVA},{sbagliata}")
        self.assertIn("posizione 2", str(ctx.exception))
        self.assertNotIn(sbagliata, str(ctx.exception))

    # Scopo: La stessa chiave due volte e' un errore di rotazione, non un'ovvieta'.
    def test_chiave_duplicata_rifiutata(self):
        with self.assertRaises(ImproperlyConfigured):
            parse_chiavi_cifratura(f"{_NUOVA},{_NUOVA}")
