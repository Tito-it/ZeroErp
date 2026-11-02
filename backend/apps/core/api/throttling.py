# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Throttling DRF per endpoint search/lista, login e reset password.
# ------------------------------------------------------------
from __future__ import annotations

import logging
import math

from django.conf import settings
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle

from apps.core.services.request_context import get_client_ip

# Throttling DRF: limita endpoint sensibili.

logger = logging.getLogger("security")

# Chiave comune delle richieste di cui l'IP non si ricava: condividono UN
# contatore (fail-closed), invece di sfuggire al limite.
_IDENT_IP_SCONOSCIUTO = "ip-sconosciuto"

# Il segnaposto «questo blocco e' gia' nel log» (vedi `allow_request`).
_CHIAVE_LOG_LIMITE = "throttle_log_%(scope)s_%(ident)s"


# ⭐ Eredita da `SimpleRateThrottle` (dal 2026-10-09) perche' ne USA il
#    contratto — `wait`, `cache`, `scope` in `allow_request` — e il type checker
#    lo deve sapere. L'MRO dei due consumatori resta quello di prima: il mixin
#    viene prima della classe DRF, quindi il suo `get_ident` vince ancora.
class _ClientIpIdentMixin(SimpleRateThrottle):
    """L'IP del throttle viene dal BB `get_client_ip`, non da DRF.

    ⛔ `SimpleRateThrottle.get_ident` di DRF legge `X-Forwarded-For` per conto
    suo (con `NUM_PROXIES` non impostato usa l'header INTERO, scritto dal
    client): chi cambia l'header a ogni richiesta avrebbe un contatore nuovo
    ogni volta. La regola dell'hop fidato sta in un solo posto.
    """

    # Scopo: Identifica il chiamante con l'IP fidato del BB `get_client_ip`.
    def get_ident(self, request):
        return get_client_ip(request) or _IDENT_IP_SCONOSCIUTO

    # Scopo: Un limite che scatta lascia traccia nel log di sicurezza.
    #        ⛔ Fino al 2026-10-02 un 429 non si vedeva da nessuna parte: il
    #        gestore degli errori DRF lo traduce senza scriverlo, e
    #        `request_log` registra le sole richieste AUTENTICATE — login,
    #        secondo passo e reset sono anonimi, cioe' proprio gli endpoint
    #        dove una raffica di tentativi va vista (rilievo di Tid: tre
    #        password rifiutate al reset, poi «troppi tentativi», e nel log
    #        niente). Qui, nella base comune, vale per ogni limite.
    #        ⭐ UNA riga per episodio di blocco, non una per richiesta
    #        respinta (2026-10-02, decisione di Tid): sotto una raffica la riga
    #        per richiesta riempiva il log con la stessa notizia, e chi
    #        martella un endpoint decideva quanto log scrivere. Il segnaposto
    #        in cache dura quanto l'attesa: finito il blocco, il blocco
    #        successivo ha di nuovo la sua riga.
    def allow_request(self, request, view):
        if super().allow_request(request, view):
            return True
        ident = self.get_ident(request)
        attesa = self.wait() or 0
        # `add` scrive solo se la chiave non c'e': e' il test-and-set atomico
        # della cache (Redis), quindi due worker non scrivono la stessa riga.
        primo = self.cache.add(
            _CHIAVE_LOG_LIMITE % {"scope": self.scope, "ident": ident},
            True,
            timeout=max(1, math.ceil(attesa)),
        )
        if primo:
            logger.warning(
                "security.limite_frequenza scope=%s provenienza=%s path=%s attesa_s=%s",
                self.scope, ident, request.path, round(attesa),
            )
        return False


class _CustomRateAnonThrottle(_ClientIpIdentMixin, AnonRateThrottle):
    """Base con parsing rate custom (supporta minuti "Nm" e ore "Nh")."""

    # Scopo: Parsing custom per rate con minuti/ore (es. "5/5m", "3/1h").
    # DRF supporta solo second/minute/hour/day. Qui convertiamo "Nm"/"Nh" in secondi.
    def parse_rate(self, rate):
        if rate is None:
            return (None, None)
        num_requests, duration = rate.split("/")
        num_requests = int(num_requests)
        if duration.endswith("m"):
            period = int(duration[:-1]) * 60
        elif duration.endswith("h"):
            period = int(duration[:-1]) * 3600
        else:
            return super().parse_rate(rate)
        return (num_requests, period)


class LoginRateThrottle(_CustomRateAnonThrottle):
    """Limita tentativi login per IP: 5 ogni 5 minuti (default).

    Il ritmo e' `settings.API_LOGIN_THROTTLE_RATE` (env
    `DJANGO_API_LOGIN_THROTTLE_RATE`): si alza solo in sviluppo, per gli smoke.
    """
    scope = "login"
    rate = settings.API_LOGIN_THROTTLE_RATE


class SecondoFattoreRateThrottle(_CustomRateAnonThrottle):
    """Limita il SECONDO PASSO del login per IP: 5 ogni 5 minuti.

    ⭐ Contatore proprio, non quello del login (fino al 2026-10-02 era lo
    stesso): col secondo fattore ogni accesso costa due richieste, e un
    contatore condiviso dimezzava i login possibili da un IP — dietro un
    ufficio con un solo indirizzo, due o tre persone insieme ricevevano 429
    (collaudo di Tid: lo smoke col secondo login fermato al secondo passo).
    Chi prova codici a raffica resta frenato tre volte: da questo limite, dal
    freno della credenziale a DB (ogni codice sbagliato e' un tentativo fallito,
    D-T2) e dalla sfida, che scade in 5 minuti. Lo stesso ritmo del login per
    scelta, non per copia: i due limiti possono divergere.
    """
    scope = "login_secondo_fattore"
    rate = settings.API_SECONDO_FATTORE_THROTTLE_RATE   # default "5/5m"


class PasswordResetRateThrottle(_CustomRateAnonThrottle):
    """Limita le RICHIESTE del link di reset per IP: 3 ogni 15 minuti.

    E' il limite che serve dove si manda un'email a chiunque digiti un nome:
    stretto, contro l'invio a raffica di email. La conferma col link ha il suo
    (`ConfermaTokenRateThrottle`).
    """
    scope = "password_reset"
    rate = "3/15m"


class ConfermaTokenRateThrottle(_CustomRateAnonThrottle):
    """Limita le CONFERME con un link per IP: 10 ogni 15 minuti.

    La conferma del reset e l'attivazione dell'invito: chi le chiama presenta
    un token lungo, monouso e con scadenza, e ci sceglie la password.
    ⭐ Contatore proprio (2026-10-02, decisione di Tid): fino ad allora era
    quello della richiesta del link (3/15m), e una password rifiutata dalle
    regole di Django — un errore di digitazione, non un attacco — consumava un
    tentativo: con il link gia' in mano, due password sbagliate e il quarto
    d'ora era fermo. Indovinare il token resta impraticabile anche a 10:
    il limite frena solo le raffiche.
    """
    scope = "conferma_token"
    rate = "10/15m"


class SearchBurstRateThrottle(_ClientIpIdentMixin, SimpleRateThrottle):
    scope = "search_burst"

    # Scopo: Recupera `cache_key` dal contesto applicativo o dal database.
    def get_cache_key(self, request, view):
        if not getattr(view, "is_search_endpoint", False):
            return None
        ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}
