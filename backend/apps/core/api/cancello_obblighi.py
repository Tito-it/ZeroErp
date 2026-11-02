# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il cancello degli OBBLIGHI della credenziale: cio' che una persona
#        deve fare prima di poter usare l'applicazione (cambiare la password,
#        configurare il secondo fattore). Lo chiama JwtAuditAuthentication a
#        ogni richiesta col Bearer, dopo le GUC: e' il solo punto che conosce
#        l'utente del token E che ogni view attraversa, qualunque sia la sua
#        permission (Domain, Admin, Portale, Shop, IsAuthenticated).
# Note: Brief sicurezza §3.4-bis, lotto T-0 (chiude A-8 del piano accessi).
#       Sostituisce PasswordChangeRequiredMiddleware, che guardava
#       `request.user` in `process_view`: prima dell'autenticazione DRF, cioe'
#       sempre anonimo per un Bearer. ⛔ Un obbligo nuovo si aggiunge QUI, non
#       con un secondo cancello.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any

from rest_framework import status
from rest_framework.exceptions import PermissionDenied

from apps.core.db.auth_repository import AuthRepository
from apps.core.db.secondo_fattore_repository import STATO_DEVICE_ATTIVO

logger = logging.getLogger(__name__)

_auth_repo = AuthRepository()

OBBLIGO_CAMBIO_PASSWORD = "CAMBIO_PASSWORD"  # noqa: S105 — codice dell'obbligo, non un segreto
OBBLIGO_SECONDO_FATTORE = "SECONDO_FATTORE"

# Per le view che servono qualunque obbligo sia pendente: il logout (si deve
# poter uscire) e il profilo `/core/me/` (il frontend ci legge gli obblighi).
TUTTI_GLI_OBBLIGHI: frozenset[str] = frozenset({OBBLIGO_CAMBIO_PASSWORD, OBBLIGO_SECONDO_FATTORE})

# ⭐ Gli obblighi che il cancello FA RISPETTARE: quelli per cui esiste la
# strada per soddisfarli, cioe' una view che li ammette e li chiude (il cambio
# password: `ChangePasswordView`). Un obbligo senza strada non e' un obbligo,
# e' un'utenza murata: il 2026-09-30 il SUPER_ADMIN, che ha sempre l'obbligo
# del secondo fattore (`script.fn_totp_obbligatorio`, motivo PROFILO), non
# apriva piu' nessuna pagina, perche' la configurazione del secondo fattore
# non esisteva ancora. ``SECONDO_FATTORE`` e' in vigore dal 2026-10-02 (T-4
# del brief sicurezza §3.4-bis): gli endpoint self-service (T-3) lo
# dichiarano in `obblighi_ammessi`, e la pagina «Sicurezza» col guard del
# frontend (`obblighi_pendenti` di `/core/me/`) porta la persona a chiuderlo.
# Presidio: `test_ogni_obbligo_in_vigore_ha_la_sua_strada`.
# `obblighi_pendenti` resta la regola sui fatti e li dice tutti: e' il
# cancello a scegliere quali fermano una richiesta.
OBBLIGHI_IN_VIGORE: frozenset[str] = frozenset({OBBLIGO_CAMBIO_PASSWORD, OBBLIGO_SECONDO_FATTORE})


class CambioPasswordRichiestoError(PermissionDenied):
    """La credenziale deve cambiare la password prima di continuare."""

    status_code = status.HTTP_403_FORBIDDEN
    default_code = "E_CAMBIO_PASSWORD_RICHIESTO"
    default_detail = "Prima di continuare e' necessario cambiare la password."


class SecondoFattoreDaConfigurareError(PermissionDenied):
    """Il secondo fattore e' obbligatorio per la credenziale e non e' attivo."""

    status_code = status.HTTP_403_FORBIDDEN
    default_code = "E_TOTP_CONFIGURAZIONE_RICHIESTA"
    default_detail = (
        "Prima di continuare e' necessario configurare il secondo fattore di autenticazione."
    )


_ERRORE_PER_OBBLIGO: dict[str, type[PermissionDenied]] = {
    OBBLIGO_CAMBIO_PASSWORD: CambioPasswordRichiestoError,
    OBBLIGO_SECONDO_FATTORE: SecondoFattoreDaConfigurareError,
}


# Scopo: Dai fatti letti dal DB (`AuthRepository.get_fatti_obblighi`) gli
# obblighi pendenti, NELL'ORDINE in cui si soddisfano: prima la password (il
# secondo fattore si configura con la password definitiva), poi il secondo
# fattore. Sede unica della regola «il secondo fattore e' pendente quando e'
# obbligatorio e il device non e' ATTIVO»: un device DA_CONFERMARE e' una
# configurazione a meta', non un secondo fattore.
def obblighi_pendenti(fatti: dict[str, Any]) -> tuple[str, ...]:
    pendenti: list[str] = []
    if fatti["deve_cambiare_password"]:
        pendenti.append(OBBLIGO_CAMBIO_PASSWORD)
    if fatti["totp_obbligatorio"] and fatti["totp_stato"] != STATO_DEVICE_ATTIVO:
        pendenti.append(OBBLIGO_SECONDO_FATTORE)
    return tuple(pendenti)


# Scopo: Gli obblighi pendenti E in vigore della credenziale, nell'ordine:
#        quelli che il cancello fa rispettare. ⭐ Li pubblica anche `/core/me/`
#        (`obblighi_pendenti`), e il guard del frontend porta alla pagina che
#        chiude il primo: una regola, letta da due parti.
def obblighi_in_vigore(auth_user_id: int) -> tuple[str, ...]:
    return tuple(
        o for o in obblighi_pendenti(_auth_repo.get_fatti_obblighi(auth_user_id))
        if o in OBBLIGHI_IN_VIGORE
    )


# Scopo: Il cancello. Solleva l'errore del PRIMO obbligo pendente e in vigore
# (`OBBLIGHI_IN_VIGORE`) che la view non ammette (`obblighi_ammessi`, attributo
# di classe; assente = nessuno).
# ⚠️ Il primo pendente, non il primo non ammesso: con la password da cambiare
# la pagina del secondo fattore resta chiusa, perche' l'ordine e' quello.
# Fail-closed: un DB che non risponde e' un errore della richiesta, non un
# «nessun obbligo».
def verifica_obblighi(view: Any, auth_user_id: int) -> None:
    pendenti = obblighi_in_vigore(auth_user_id)
    if not pendenti:
        return
    ammessi: frozenset[str] = getattr(view, "obblighi_ammessi", frozenset())
    primo = pendenti[0]
    if primo in ammessi:
        return
    logger.info(
        "security.obbligo_pendente user_id=%s obbligo=%s view=%s",
        auth_user_id, primo, type(view).__name__ if view is not None else None,
    )
    raise _ERRORE_PER_OBBLIGO[primo]()
