# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Crittografia simmetrica con Fernet per i segreti salvati nel DB
#        (password SMTP; domani i segreti TOTP).
# Note: ⭐ Le chiavi sono `settings.FIELD_ENCRYPTION_KEYS`, SEPARATE dalla
#       SECRET_KEY (dal 2026-09-28, brief-be-fe-sicurezza-header-token-mfa
#       §3.5): si cifra con la prima, si decifra con tutte (`MultiFernet`).
#       Ruotare la SECRET_KEY non tocca piu' i dati cifrati; ruotare queste
#       chiavi si fa con `manage.py ricifra_campi_cifrati`.
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings


# Scopo: Una colonna del DB che contiene un token di questo servizio, e come
#        la si riscrive alla rotazione delle chiavi.
#        `verbo` None: la tabella e' scrivibile dall'app, `ricifra_campi_cifrati`
#        la legge con FOR UPDATE e la riscrive con un UPDATE diretto sulla `chiave`.
#        `verbo` dato: la tabella e' CHIUSA all'app (solo SELECT), e si riscrive
#        con quella funzione `(chiave, token_atteso, token_nuovo) -> boolean`,
#        che confronta e sostituisce: `false` = il segreto e' cambiato fra la
#        lettura e la scrittura, e resta com'e' (gia' sulla chiave buona).
@dataclass(frozen=True)
class CampoCifrato:
    tabella: str
    colonna: str
    chiave: str = "id"
    verbo: str | None = None


# ⛔ OGNI colonna cifrata con `encrypt` si iscrive qui: e' l'elenco che
#    `ricifra_campi_cifrati` percorre quando le chiavi ruotano. Una colonna
#    dimenticata resta cifrata con la chiave vecchia, e diventa illeggibile nel
#    momento in cui quella chiave si toglie.
CAMPI_CIFRATI: tuple[CampoCifrato, ...] = (
    CampoCifrato("config.email_account", "smtp_password_encrypted"),
    # Il segreto del secondo fattore: tabella chiusa all'app, si riscrive col
    # verbo (brief-db-totp-ricifra-segreto, consegnato il 2026-10-01).
    CampoCifrato(
        "config.auth_totp_device", "secret_encrypted",
        chiave="auth_user_id", verbo="script.fn_totp_ricifra_segreto",
    ),
)


# Scopo: Le chiavi configurate, la prima e' quella che cifra. `chiavi_extra`
#        si aggiungono IN CODA, solo per decifrare (la migrazione dalla chiave
#        derivata dalla SECRET_KEY, in `ricifra_campi_cifrati`).
def _multi_fernet(chiavi_extra: Sequence[bytes] = ()) -> MultiFernet:
    chiavi = [Fernet(k) for k in settings.FIELD_ENCRYPTION_KEYS]
    chiavi.extend(Fernet(k) for k in chiavi_extra)
    return MultiFernet(chiavi)


def encrypt(plaintext: str) -> str:
    """Scopo: Crittografa una stringa con la prima chiave e ritorna il token Fernet."""
    return _multi_fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    """Scopo: Decrittografa un token Fernet con una qualunque delle chiavi.

    Lancia ValueError se il token e' vuoto/nullo o nessuna chiave lo apre.
    """
    if not token:
        raise ValueError("Token vuoto o nullo — impossibile decrittografare.")
    try:
        return _multi_fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        raise ValueError("Impossibile decrittografare: token invalido o chiave cambiata.") from None


def ricifra(token: str, *, chiavi_extra: Sequence[bytes] = ()) -> str:
    """Scopo: Ri-cifra un token con la prima chiave, qualunque chiave lo apra.

    Lancia ValueError se il token e' vuoto/nullo o nessuna chiave lo apre.
    """
    if not token:
        raise ValueError("Token vuoto o nullo — impossibile ri-cifrare.")
    try:
        return _multi_fernet(chiavi_extra).rotate(token.encode()).decode()
    except InvalidToken:
        raise ValueError("Impossibile ri-cifrare: nessuna chiave apre il token.") from None
