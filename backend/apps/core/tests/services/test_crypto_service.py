# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per crypto_service — encrypt/decrypt con Fernet.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) CryptoServiceTests.test_encrypt_decrypt_roundtrip
2) CryptoServiceTests.test_decrypt_invalid_token_raises
3) CryptoServiceTests.test_encrypt_produces_different_tokens
4) CryptoServiceTests.test_empty_string_roundtrip
"""

from unittest import TestCase
from unittest.mock import patch

from apps.core.services import crypto_service


class CryptoServiceTests(TestCase):

    # Scopo: Verifica che encrypt + decrypt restituisca il testo originale.
    @patch("apps.core.services.crypto_service.settings")
    def test_encrypt_decrypt_roundtrip(self, mock_settings):
        mock_settings.SECRET_KEY = "test-secret-key-for-fernet-derivation"
        plaintext = "mia-password-smtp-segreta"
        encrypted = crypto_service.encrypt(plaintext)
        self.assertNotEqual(encrypted, plaintext)
        decrypted = crypto_service.decrypt(encrypted)
        self.assertEqual(decrypted, plaintext)

    # Scopo: Verifica che decrypt con token invalido lanci ValueError.
    @patch("apps.core.services.crypto_service.settings")
    def test_decrypt_invalid_token_raises(self, mock_settings):
        mock_settings.SECRET_KEY = "test-secret-key"
        with self.assertRaises(ValueError):
            crypto_service.decrypt("token-invalido-non-fernet")

    # Scopo: Verifica che due encrypt dello stesso testo producano token diversi (nonce).
    @patch("apps.core.services.crypto_service.settings")
    def test_encrypt_produces_different_tokens(self, mock_settings):
        mock_settings.SECRET_KEY = "test-secret-key"
        t1 = crypto_service.encrypt("stessa-password")
        t2 = crypto_service.encrypt("stessa-password")
        self.assertNotEqual(t1, t2)

    # Scopo: Verifica roundtrip con stringa vuota.
    @patch("apps.core.services.crypto_service.settings")
    def test_empty_string_roundtrip(self, mock_settings):
        mock_settings.SECRET_KEY = "test-secret-key"
        encrypted = crypto_service.encrypt("")
        self.assertEqual(crypto_service.decrypt(encrypted), "")
