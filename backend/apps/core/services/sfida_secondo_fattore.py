# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La SFIDA del login a due passi (brief sicurezza §3.4-bis, T-2):
#        dopo la password giusta, a chi ha il secondo fattore attivo non si
#        da' un JWT ma questa, firmata e breve. Il secondo passo la presenta
#        col codice. Porta la credenziale, la veste gia' risolta dal primo
#        passo, la porta e la provenienza: il secondo passo non risolve di
#        nuovo niente, e una sfida portata altrove non vale.
# Note: ⚠️ Non e' monouso da sola: la rende tale l'anti-replay sul passo del
#       codice (`fn_totp_registra_uso`) e il consumo del codice di recupero.
#       Una sfida ripresentata con un codice sbagliato conta come tentativo
#       fallito della credenziale (D-T2), come la password.
#       Firmata con la SECRET_KEY (`django.core.signing`) e un sale proprio:
#       ruotare la SECRET_KEY invalida solo le sfide aperte, cioe' cinque
#       minuti di login a meta'.
# ------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass

from django.core import signing

from apps.core.services.service_errors import ServiceError

# Quanto vale una sfida: il tempo di aprire l'app e copiare un codice.
DURATA_SFIDA_SECONDI = 300

_SALE = "zeroerp.login.sfida-secondo-fattore"

E_TOTP_SFIDA_NON_VALIDA = "E_TOTP_SFIDA_NON_VALIDA"


# Scopo: Cio' che il primo passo ha gia' stabilito e il secondo eredita.
@dataclass(frozen=True)
class Sfida:
    auth_user_id: int
    identita_id: int
    porta: str
    provenienza: str


# Scopo: La sfida firmata da consegnare al client al posto del JWT.
def emetti_sfida(sfida: Sfida) -> str:
    return signing.dumps(
        {"u": sfida.auth_user_id, "i": sfida.identita_id, "p": sfida.porta, "o": sfida.provenienza},
        salt=_SALE,
        compress=True,
    )


# Scopo: Legge una sfida presentata al secondo passo e la rifiuta se e'
#        scaduta, manomessa, di un'altra porta o di un'altra provenienza.
#        ⛔ Una sola risposta per i quattro casi, 401 E_TOTP_SFIDA_NON_VALIDA:
#        a chi prova non si dice quale controllo e' fallito. Il motivo resta
#        nel `detail` del log, non nella frase.
def leggi_sfida(token: object, *, porta: str, provenienza: str) -> Sfida:
    def _rifiuta(motivo: str) -> ServiceError:
        return ServiceError(
            code=E_TOTP_SFIDA_NON_VALIDA,
            message="La verifica e' scaduta: accedere di nuovo con la password.",
            detail=motivo,
        )

    if not isinstance(token, str) or not token:
        raise _rifiuta("sfida assente")
    try:
        dati = signing.loads(token, salt=_SALE, max_age=DURATA_SFIDA_SECONDI)
    except signing.SignatureExpired:
        raise _rifiuta("sfida scaduta") from None
    except signing.BadSignature:
        raise _rifiuta("sfida con firma non valida") from None
    try:
        sfida = Sfida(
            auth_user_id=int(dati["u"]),
            identita_id=int(dati["i"]),
            porta=str(dati["p"]),
            provenienza=str(dati["o"]),
        )
    except (KeyError, TypeError, ValueError):
        raise _rifiuta("sfida di forma non valida") from None
    if sfida.porta != porta:
        raise _rifiuta("sfida di un'altra porta")
    if sfida.provenienza != provenienza:
        raise _rifiuta("sfida di un'altra provenienza")
    return sfida
