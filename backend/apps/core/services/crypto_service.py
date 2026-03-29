# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Crittografia simmetrica con Fernet per dati sensibili
#        (password SMTP, secret TOTP). Chiave derivata da SECRET_KEY.
# ------------------------------------------------------------

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _derive_key() -> bytes:
    """Scopo: Deriva una chiave Fernet 32-byte da Django SECRET_KEY via SHA-256."""
    digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt(plaintext: str) -> str:
    """Scopo: Crittografa una stringa e ritorna il token Fernet come stringa."""
    f = Fernet(_derive_key())
    return f.encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    """Scopo: Decrittografa un token Fernet e ritorna la stringa originale.

    Lancia InvalidToken se la chiave non corrisponde o il token e' corrotto.
    """
    f = Fernet(_derive_key())
    try:
        return f.decrypt(token.encode()).decode()
    except InvalidToken:
        raise ValueError("Impossibile decrittografare: token invalido o chiave cambiata.")
