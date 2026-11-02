# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per TokenService — mock DB,
#        compatibile CI senza database reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) TokenServiceTests.test_create_returns_plain_token
2) TokenServiceTests.test_create_non_invalida_i_precedenti
3) TokenServiceTests.test_validate_valid_token
4) TokenServiceTests.test_validate_invalid_token
5) TokenServiceTests.test_consume_valid_token
6) TokenServiceTests.test_consume_invalid_raises
7) TokenServiceTests.test_invalidate_all
8) TokenServiceTests.test_hash_deterministic
"""

from unittest import TestCase
from unittest.mock import patch

from apps.core.services.token_service import TokenService
from apps.core.services.service_errors import ServiceError

_REPO = "apps.core.services.token_service.TokenRepository"


class TokenServiceTests(TestCase):

    # Scopo: Verifica che create ritorni un token in chiaro (64 hex chars).
    @patch(_REPO)
    def test_create_returns_plain_token(self, MockRepo):
        repo = MockRepo.return_value
        repo.create.return_value = 1

        service = TokenService()
        token = service.create(tipo="RESET_PASSWORD", auth_user_id=42, scadenza_ore=24)

        self.assertEqual(len(token), 64)
        repo.create.assert_called_once()
        call_kwargs = repo.create.call_args[1]
        self.assertEqual(call_kwargs["tipo"], "RESET_PASSWORD")
        self.assertEqual(call_kwargs["auth_user_id"], 42)
        # token_hash deve essere diverso dal token in chiaro
        self.assertNotEqual(call_kwargs["token_hash"], token)

    # Scopo: create NON invalida i token precedenti: quali spegnere lo decide
    # il chiamante (per tipo, o per veste). La prova che nemmeno il repository
    # lo fa e' sul DB vero: test_token_veste_db.
    @patch(_REPO)
    def test_create_non_invalida_i_precedenti(self, MockRepo):
        repo = MockRepo.return_value
        repo.create.return_value = 2

        service = TokenService()
        service.create(tipo="INVITO_OPERATORE", auth_user_id=10)

        repo.create.assert_called_once()
        repo.invalidate_all.assert_not_called()
        repo.invalidate_for_identita.assert_not_called()

    # Scopo: Verifica validate con token valido.
    @patch(_REPO)
    def test_validate_valid_token(self, MockRepo):
        repo = MockRepo.return_value

        service = TokenService()
        token_plain = "a" * 64
        expected_hash = service._hash(token_plain)
        repo.find_valid.return_value = {
            "id": 1, "auth_user_id": 42, "meta": {"invitato_da": "admin"},
        }

        result = service.validate(token_plain, "RESET_PASSWORD")

        self.assertIsNotNone(result)
        auth_user_id, meta = result
        self.assertEqual(auth_user_id, 42)
        self.assertEqual(meta["invitato_da"], "admin")
        repo.find_valid.assert_called_once_with(expected_hash, "RESET_PASSWORD")

    # Scopo: Verifica validate con token non trovato.
    @patch(_REPO)
    def test_validate_invalid_token(self, MockRepo):
        repo = MockRepo.return_value
        repo.find_valid.return_value = None

        service = TokenService()
        result = service.validate("token_invalido", "RESET_PASSWORD")

        self.assertIsNone(result)

    # Scopo: Verifica consume con token valido.
    @patch(_REPO)
    def test_consume_valid_token(self, MockRepo):
        repo = MockRepo.return_value
        repo.find_valid.return_value = {"id": 5, "auth_user_id": 42, "meta": {}}
        repo.consume.return_value = True

        service = TokenService()
        auth_user_id = service.consume("token_valido", "RESET_PASSWORD", ip="192.168.1.1")

        self.assertEqual(auth_user_id, 42)
        repo.consume.assert_called_once_with(5, ip="192.168.1.1")

    # Scopo: Verifica che consume con token invalido lanci ServiceError.
    @patch(_REPO)
    def test_consume_invalid_raises(self, MockRepo):
        repo = MockRepo.return_value
        repo.find_valid.return_value = None

        service = TokenService()
        with self.assertRaises(ServiceError):
            service.consume("token_scaduto", "RESET_PASSWORD")

    # Scopo: Verifica invalidate_all.
    @patch(_REPO)
    def test_invalidate_all(self, MockRepo):
        repo = MockRepo.return_value
        repo.invalidate_all.return_value = 3

        service = TokenService()
        count = service.invalidate_all("RESET_PASSWORD", 42)

        self.assertEqual(count, 3)
        repo.invalidate_all.assert_called_once_with("RESET_PASSWORD", 42)

    # Scopo: Verifica che hash sia deterministico (stesso input = stesso output).
    def test_hash_deterministic(self):
        h1 = TokenService._hash("test_token")
        h2 = TokenService._hash("test_token")
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)
