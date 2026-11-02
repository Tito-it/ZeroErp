# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La password della credenziale chiesta DENTRO una sessione (cambio
#        password, avvio della configurazione del secondo fattore), col freno
#        della credenziale: chi tiene una sessione rubata non deve poter provare
#        password senza attesa, e quando il freno scatta perde la sessione.
# Note: ⭐ Regola del 2 (2026-10-03, ok Tid): la verifica stava nel servizio del
#       secondo fattore e mancava al cambio password, che controllava la
#       password con `check_password` e nient'altro — il buco che questa sede
#       chiude. Il login NON passa di qui: ha la sua catena (nome tentato per
#       una credenziale che non esiste, azzeramento al successo, audit).
# ------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any

from django.contrib.auth.models import User
from django.db import DatabaseError, transaction

from apps.core.db.auth_repository import AuthRepository
from apps.core.services import session_audit_service
from apps.core.services.db_error_fields import structured_db_error_code
from apps.core.services.nome_tentato import digest_nome_tentato, etichetta_log
from apps.core.services.request_context import provenienza_obbligatoria, richiesta_django, sid_corrente
from apps.core.services.revoca_token import blocca_token_sessioni
from apps.core.services.service_errors import ServiceError

logger = logging.getLogger("security")

# Il freno sulla coppia credenziale + provenienza (`script.fn_check_blocco_login`).
# ⛔ Solo questo chiude la sessione: `E_LOGIN_ATTESA` rallenta senza bloccare, e
#    `E_CREDENZIALE_BLOCCATA` (l'amministratore) le sessioni le ha gia' chiuse
#    tutte (`AccessiService.blocca_credenziale`).
E_UTENTE_BLOCCATO = "E_UTENTE_BLOCCATO"

# Il motivo nella riga LOGOUT di `dbops.sessioni_utente`.
_MOTIVO_CHIUSURA = "FRENO_PASSWORD"


# Scopo: Verifica la password di `user` col freno della credenziale, e
#        nell'ordine che lo rende un freno:
#          1. il blocco (`script.fn_check_blocco_login`): a credenziale frenata
#             o bloccata la password non si guarda nemmeno;
#          2. assente → `codice` con `messaggio_assente`, e NON e' un tentativo
#             (non c'e' niente da indovinare);
#          3. sbagliata → tentativo fallito (D-T2,
#             `script.fn_registra_tentativo_login` con `successo = false`), poi
#             `codice` con `messaggio`.
#        Giusta: non azzera i tentativi — non e' un login.
#        ⭐ La sessione da cui arriva la prova si CHIUDE (decisione A di Tid,
#        2026-10-03) quando la coppia credenziale + provenienza e' frenata:
#        trovata gia' frenata al punto 1, o frenata dal tentativo sbagliato del
#        punto 3 — e allora la risposta e' il freno stesso, con la frase del
#        DB (i minuti), non «password sbagliata». Solo QUELLA sessione: chiudere
#        tutte le sessioni della credenziale darebbe a chi ne tiene una rubata
#        il modo di buttare fuori il titolare dai suoi dispositivi.
#        ⚠️ «Chiudere» e' cio' che fa il logout: i refresh del `sid` in
#        blacklist. L'access gia' emesso vive fino alla sua scadenza (10
#        minuti), come dopo ogni logout; il frontend lo butta subito.
#        ⛔ Va chiamata PRIMA di ogni altra validazione del chiamante: un
#        errore che arriva prima (una password nuova debole) lascerebbe provare
#        la password senza che il tentativo conti.
def verifica_password_con_freno(
    user: User,
    password: object,
    *,
    request: Any,
    auth_repo: AuthRepository,
    codice: str,
    messaggio: str,
    messaggio_assente: str | None = None,
    campo: str = "password",
) -> None:
    provenienza = provenienza_obbligatoria(request)
    digest = digest_nome_tentato(user.get_username())
    chi = etichetta_log(user.id, digest)

    # ⛔ In un SAVEPOINT: il rifiuto del DB interrompe la transazione in cui
    #    cade, e sotto una transazione del chiamante si porterebbe via il
    #    tentativo appena registrato e la chiusura della sessione (stessa
    #    lezione di `SecondoFattoreService._prova_al_db`; trovato dal test sul
    #    DB vero, 2026-10-03).
    def _freno() -> None:
        try:
            with transaction.atomic():
                auth_repo.check_blocco_login(user.id, nome_digest=digest, provenienza=provenienza)
        except DatabaseError as exc:
            if structured_db_error_code(exc) == E_UTENTE_BLOCCATO:
                _chiudi_sessione(user.id, request, chi)
            raise

    _freno()
    if not isinstance(password, str) or not password:
        raise ServiceError(
            code=codice, message=messaggio_assente or messaggio, detail="password assente", fields=(campo,),
        )
    if user.check_password(password):
        return
    esito = auth_repo.registra_tentativo_login(
        user.id, nome_digest=digest, provenienza=provenienza, successo=False,
    )
    logger.warning(
        "security.password_in_sessione_fallita %s provenienza=%s codice=%s bloccato=%s",
        chi, provenienza, codice, esito.get("bloccato"),
    )
    if esito.get("bloccato"):
        # Il freno scatta con questo tentativo: lo dice il DB, con i minuti.
        _freno()
    raise ServiceError(code=codice, message=messaggio, fields=(campo,))


# Scopo: Chiude la sessione della richiesta (refresh del `sid` in blacklist,
#        come il logout) e lascia la riga LOGOUT col motivo. Senza `sid` (una
#        chiamata fuori da una sessione) non c'e' niente da chiudere.
def _chiudi_sessione(auth_user_id: int, request: Any, chi: str) -> None:
    sid = sid_corrente(request)
    if not sid:
        return
    blocca_token_sessioni(auth_user_id, lambda s: s == sid)
    session_audit_service.record_logout(
        user_id=auth_user_id,
        request=richiesta_django(request),
        jti=sid,
        dettaglio={"motivo": _MOTIVO_CHIUSURA},
    )
    # Il sid accorciato: basta per correlare con la riga LOGOUT.
    logger.warning("security.sessione_chiusa_dal_freno %s sid=%s", chi, sid[:8])
