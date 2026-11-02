# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: BB unico della revoca dei refresh token JWT di un utente: scorre gli
#        `OutstandingToken` e li mette in blacklist, tutti o solo quelli delle
#        sessioni scelte (per `sid`) o di una veste (per `identita_id`). Lo
#        usano le view di revoca sessioni, il cambio password, il blocco della
#        credenziale, il refresh di una veste spenta e lo spegnimento di una
#        veste (operatore, portale, shop).
#
# ⭐ Portato qui da `core/api/sessioni_view.py` il 2026-09-26: il giro esisteva
#    in QUATTRO copie — le due view di revoca (gia' unificate il 2026-09-04),
#    `auth_helpers.apply_new_password` e `amm_software._blacklist_user_tokens`.
#    La copia della disattivazione operatore ingoiava QUALUNQUE errore
#    (`except Exception: pass`): se la scrittura falliva, l'operatore risultava
#    disattivato e le sue sessioni restavano vive, senza una riga di log. E'
#    lo stesso difetto che l'estrazione del 04-09 aveva gia' tolto dalla
#    revoca singola — rimasto vivo nella copia che nessuno guardava.
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Callable

import jwt
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from apps.core.services.auth_constants import JWT_CLAIM_IDENTITA_ID, JWT_CLAIM_SID


# Scopo: blocca i token JWT delle sessioni scelte da `vale_sid` (con `None`:
#        TUTTI i token dell'utente), e ritorna quanti token le APPARTENGONO —
#        non quanti ne ha scritti adesso.
#
# ⛔ La differenza fra i due conteggi e' l'IDEMPOTENZA, e la prima stesura di
#    questo helper l'aveva persa: contando le sole scritture, revocare una
#    sessione i cui token erano gia' tutti bloccati tornava zero, e il
#    chiamante rispondeva «sessione non trovata» a un gesto che aveva gia'
#    funzionato (un doppio click bastava). Chi chiede «questa sessione
#    esiste?» non sta chiedendo «ho scritto qualcosa?».
#
# ⛔ Il `try` copre SOLO la decodifica. Un errore di scrittura PROPAGA: una
#    revoca fallita e' un guasto, non un «best-effort». Le copie che
#    avvolgevano anche la scrittura trasformavano il guasto in un 404 (revoca
#    singola) o in niente del tutto (disattivazione operatore).
#
# ⚠️ Una query per i token gia' bloccati e una `bulk_create`, non una
#    `get_or_create` per token: sul database di sviluppo l'utente ha ~1400
#    token storici, e la forma per-token erano ~1400 SELECT per revocarne uno.
#
# ⚠️ Con `vale_sid=None` non si decodifica niente: si blocca anche il token
#    scaduto o illeggibile. E' innocuo (non era piu' usabile) e toglie il
#    caso in cui una revoca «di tutto» lasci fuori qualcosa per un errore di
#    lettura. Le copie precedenti saltavano i token scaduti con
#    `RefreshToken(...)` che li rifiutava: una riga in meno, nessun effetto.
#
# ⚠️ `vale_sid` riceve sempre una stringa (mai `None`): il claim assente arriva
#    qui come `""` e i chiamanti non devono ripetere il controllo.
#
# ⭐ `identita_id` (D-5, 2026-10-02): le sessioni di UNA veste, cioe' i token
#    il cui claim `identita_id` e' quello dato. Spegnere una veste chiude le
#    sue sessioni e non quelle delle altre vesti della stessa credenziale:
#    fino a quel giorno «Disabilita» su un operatore chiudeva anche la sessione
#    shop della stessa persona, che restava accesa. Si combina con `vale_sid`
#    (devono valere tutti e due). Un token senza il claim non appartiene a
#    nessuna veste, e resta fuori.
def blocca_token_sessioni(
    user_id: int,
    vale_sid: Callable[[str], bool] | None = None,
    *,
    identita_id: int | None = None,
) -> int:
    gia_bloccati = set(
        BlacklistedToken.objects.filter(token__user_id=user_id).values_list(
            "token_id", flat=True
        )
    )
    da_bloccare: list[BlacklistedToken] = []
    corrispondenti = 0
    for ot in OutstandingToken.objects.filter(user_id=user_id):
        if vale_sid is not None or identita_id is not None:
            try:
                payload = jwt.decode(
                    ot.token, options={"verify_exp": False, "verify_signature": False}
                )
            except jwt.PyJWTError:
                # Token illeggibile: non appartiene a nessuna sessione riconoscibile.
                continue
            if vale_sid is not None and not vale_sid(str(payload.get(JWT_CLAIM_SID, "") or "")):
                continue
            if identita_id is not None and str(payload.get(JWT_CLAIM_IDENTITA_ID)) != str(identita_id):
                continue
        corrispondenti += 1
        # Gia' bloccato: conta come «esiste», non come «da scrivere».
        if ot.id not in gia_bloccati:
            da_bloccare.append(BlacklistedToken(token=ot))

    if da_bloccare:
        BlacklistedToken.objects.bulk_create(da_bloccare, ignore_conflicts=True)
    return corrispondenti
