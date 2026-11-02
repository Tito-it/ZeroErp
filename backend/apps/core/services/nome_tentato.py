# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block del NOME TENTATO al login (R-7 del piano accessi,
#        brief-db-blocco-login-per-credenziale §13): l'impronta che il DB usa
#        come chiave del freno quando il nome non trova una credenziale, e
#        l'etichetta con cui il nome compare nei log di sicurezza.
#        Uno solo per le tre porte (operatore, portale, shop: B-10).
# Note: il nome in chiaro non entra nel DB e non entra nei log. Chi digita la
#       password nel campo username la lascerebbe li' (B-11).
# ------------------------------------------------------------

from __future__ import annotations

from django.utils.crypto import salted_hmac

# ⭐ La chiave dell'HMAC e' del BACKEND e non arriva mai al DB (§13.3): con
# un hash semplice una password digitata come username si ricaverebbe dal
# digest per forza bruta, perche' le password umane hanno poca entropia.
# `salted_hmac` la deriva da SECRET_KEY con un sale proprio: nessuna variabile
# d'ambiente in piu'. A differenza di `crypto_service` (chiavi proprie dal
# 2026-09-28) qui la derivazione va bene: cambiare SECRET_KEY (o il sale)
# azzera i contatori dei nomi inesistenti, stato che dura minuti, non si perde
# niente.
_SALE = "zeroerp.login.nome_tentato"

# Quanti caratteri esadecimali dell'impronta vanno nei log: abbastanza per
# riconoscere la stessa raffica, troppo pochi per risalire al nome.
_PREFISSO_LOG = 12


# Scopo: Impronta del nome tentato, 32 byte (HMAC-SHA256), come la vuole il DB
# (`p_nome_digest`, controllato in lunghezza). Il nome arriva GIA' normalizzato
# da chi fa il lookup della credenziale: ⛔ due normalizzazioni diverse (una
# per il lookup, una qui) riaprirebbero l'oracolo «il nome esiste» (§13.3).
def digest_nome_tentato(nome: str) -> bytes:
    return salted_hmac(_SALE, nome, algorithm="sha256").digest()


# Scopo: Come il tentativo compare nei log di sicurezza (B-11): la credenziale
# per id quando c'e', altrimenti un prefisso dell'impronta. Mai il nome.
def etichetta_log(auth_user_id: int | None, nome_digest: bytes) -> str:
    if auth_user_id is not None:
        return f"user_id={auth_user_id}"
    return f"nome={nome_digest.hex()[:_PREFISSO_LOG]}"
