# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il secondo fattore (TOTP, RFC 6238) dal lato che il DB non puo'
#        fare: generare il segreto, verificare un codice e dire su QUALE
#        PASSO e' valido, fabbricare i codici di recupero e la loro impronta,
#        disegnare il QR della configurazione. Funzioni pure: lo stato
#        (device, anti-replay, codici consumati) e' del DB, dietro
#        `SecondoFattoreRepository`.
# Note: Brief sicurezza §3.4-bis (T-1); brief-db-secondo-fattore-totp §4 e
#       §9.5 punti 5 e 6. ⭐ Sede UNICA del periodo (30 secondi): il DB riceve
#       solo il passo gia' calcolato, e non ne conosce la durata.
# ------------------------------------------------------------

from __future__ import annotations

import hashlib
import hmac
import secrets
import time

import pyotp
import segno

# Il periodo di un codice e le sue cifre: i valori delle app di
# autenticazione (Google Authenticator, Authy, …), che non ne leggono altri in
# modo affidabile. ⛔ Sede unica: il passo si calcola solo qui.
PERIODO_SECONDI = 30
CIFRE = 6

# I passi accettati attorno a quello di adesso: il precedente e il successivo,
# per l'orologio del telefono che va un poco indietro o avanti (RFC 6238 §5.2).
# ⚠️ Non di piu': il DB non limita il passo verso il futuro (brief DB §9.5.6),
# e un passo accettato in avanti di N blocca i codici buoni per N periodi.
# L'ordine conta: a parita' di codice (una collisione su un milione) vince il
# passo di adesso.
_SCARTI_ACCETTATI: tuple[int, ...] = (0, -1, 1)

# Il nome con cui l'app di autenticazione mostra il conto.
EMITTENTE = "ZeroERP"

# Codici di recupero: dieci, di sedici caratteri Crockford base32 (80 bit
# casuali), mostrati a gruppi di quattro. Con quell'entropia l'impronta e' uno
# SHA-256 semplice, senza chiave del backend: ruotare la SECRET_KEY non li
# invalida (brief sicurezza §3.4-bis, «dichiarati»).
NUMERO_CODICI_RECUPERO = 10
_CARATTERI_CODICE_RECUPERO = 16
_ALFABETO_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
# Crockford: le lettere che si confondono con le cifre si leggono come quelle.
_EQUIVALENTI_CROCKFORD = str.maketrans({"O": "0", "I": "1", "L": "1"})


# Scopo: Un segreto nuovo, 160 bit in base32 (la lunghezza dell'HMAC-SHA1
#        dell'RFC 4226 §4). Va cifrato prima di uscire dal processo.
def nuovo_segreto() -> str:
    return pyotp.random_base32(length=32)


# Scopo: Il passo dell'istante dato (secondi Unix): `floor(t / 30)`.
def passo_di(istante: float) -> int:
    return int(istante // PERIODO_SECONDI)


# Scopo: Il passo di adesso.
def passo_corrente() -> int:
    return passo_di(time.time())


# Scopo: Il codice a sei cifre normalizzato come lo digita una persona
#        (spazi tolti), oppure None se non e' un codice possibile.
def _normalizza_codice(codice: str) -> str | None:
    pulito = "".join(codice.split())
    if len(pulito) != CIFRE or not pulito.isdigit():
        return None
    return pulito


# Scopo: Verifica `codice` sul `segreto` (in chiaro) e restituisce il PASSO su
#        cui e' valido, o None. E' il passo che va al DB per l'anti-replay
#        (`fn_totp_registra_uso`, `fn_totp_conferma_device`): il DB accetta
#        solo un passo successivo all'ultimo usato. Confronto a tempo costante.
def verifica_codice(segreto: str, codice: str, *, passo_attuale: int | None = None) -> int | None:
    normalizzato = _normalizza_codice(codice)
    if normalizzato is None:
        return None
    totp = pyotp.TOTP(segreto, digits=CIFRE, interval=PERIODO_SECONDI)
    adesso = passo_corrente() if passo_attuale is None else passo_attuale
    for scarto in _SCARTI_ACCETTATI:
        passo = adesso + scarto
        if passo >= 0 and hmac.compare_digest(totp.generate_otp(passo), normalizzato):
            return passo
    return None


# Scopo: L'indirizzo `otpauth://` che l'app di autenticazione legge dal QR.
def uri_configurazione(segreto: str, nome_account: str) -> str:
    return pyotp.TOTP(segreto, digits=CIFRE, interval=PERIODO_SECONDI).provisioning_uri(
        name=nome_account, issuer_name=EMITTENTE,
    )


# Scopo: Il QR dell'indirizzo, come data URI di un SVG: il frontend lo mette
#        in un `<img>`, dove nessuno script puo' girare — mai markup del server
#        con `v-html`. Generato qui perche' il frontend non aggiunga librerie
#        (decisione del 2026-09-28).
def qr_data_uri(uri: str) -> str:
    return segno.make(uri, error="m").svg_data_uri(scale=4)


# Scopo: Un mazzo di codici di recupero nuovi, nella forma da mostrare
#        (`XXXX-XXXX-XXXX-XXXX`). Si mostrano una volta sola: al DB va solo
#        l'impronta.
def nuovi_codici_recupero() -> list[str]:
    codici: list[str] = []
    while len(codici) < NUMERO_CODICI_RECUPERO:
        grezzo = "".join(secrets.choice(_ALFABETO_CROCKFORD) for _ in range(_CARATTERI_CODICE_RECUPERO))
        codice = "-".join(grezzo[i:i + 4] for i in range(0, _CARATTERI_CODICE_RECUPERO, 4))
        if codice not in codici:  # il DB vuole un mazzo di stringhe distinte
            codici.append(codice)
    return codici


# Scopo: L'impronta di un codice di recupero come lo digita una persona:
#        trattini e spazi tolti, maiuscole, le lettere ambigue lette come
#        Crockford. Lo stesso codice scritto in due modi ha la stessa impronta.
def impronta_codice_recupero(codice: str) -> str:
    normalizzato = "".join(c for c in codice.upper() if c not in "- \t").translate(_EQUIVALENTI_CROCKFORD)
    return hashlib.sha256(normalizzato.encode()).hexdigest()
