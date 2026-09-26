# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint sessioni attive utente:
#        GET  /api/v1/core/me/sessioni/           — lista altre sessioni attive
#        POST /api/v1/core/me/sessioni/revoca-tutte/ — revoca tutte le altre sessioni
#        POST /api/v1/core/me/sessioni/<jti>/revoca/ — revoca sessione specifica
# ------------------------------------------------------------

from __future__ import annotations

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from apps.core.api.base_views import DomainAPIView

from apps.core.api.success_responses import success_response
from apps.core.db.session_audit_repository import SessionAuditRepository
from apps.core.services import session_audit_service
from apps.core.services.auth_constants import JWT_CLAIM_SID
from apps.core.services.revoca_token import blocca_token_sessioni
from apps.core.services.service_errors import ServiceError


# Scopo: Estrae il SID (session ID) dal token JWT di accesso nella request corrente.
def _get_current_sid(request: Request) -> str | None:
    auth = request.auth
    return str(auth.get(JWT_CLAIM_SID, "")) if auth else None


class SessioniAttiveListView(DomainAPIView):
    """Lista sessioni attive dell'utente corrente, escludendo quella corrente."""

    skip_area_check = True

    @extend_schema(
        summary="Lista altre sessioni attive utente",
        responses={
            200: inline_serializer(
                name="SessioniAttiveResponse",
                fields={
                    "data": inline_serializer(
                        name="SessioniAttiveData",
                        fields={
                            "sessioni": serializers.ListField(
                                help_text="Lista sessioni attive (esclusa la corrente)."
                            ),
                            "count": serializers.IntegerField(
                                help_text="Numero sessioni restituite."
                            ),
                        },
                    ),
                },
            )
        },
    )
    # Scopo: Lista le sessioni attive dell'utente corrente, escludendo quella corrente.
    # Il frontend mostra il pannello solo se la lista non e' vuota.
    def get(self, request: Request) -> Response:
        repo = SessionAuditRepository()
        sessioni = repo.list_sessioni_attive(request.user.id)
        current_sid = _get_current_sid(request)
        altre = [s for s in sessioni if s["jti"] != current_sid]
        return success_response({"sessioni": altre, "count": len(altre)})


class SessioneRevocaView(DomainAPIView):
    """Revoca una sessione specifica (non la corrente) — blacklist + evento REVOCA."""

    skip_area_check = True

    @extend_schema(summary="Revoca sessione specifica", responses={204: None})
    # Scopo: Revoca una sessione per sid — blacklista tutti i token JWT associati.
    def post(self, request: Request, jti: str) -> Response:
        sid = jti  # il parametro URL si chiama jti ma ora contiene un sid
        current_sid = _get_current_sid(request)
        # ⛔ Niente `current_sid and ...`: con un sid vuoto quel cortocircuito
        #    rendeva il rifiuto sempre falso, cioe' si poteva revocare la
        #    PROPRIA sessione dal pannello delle altre. Oggi il vuoto non arriva
        #    piu' fin qui (guard in autenticazione), e il confronto e' diretto.
        if sid == current_sid:
            raise ServiceError(
                code="E_SESSIONE_REVOCA_CORRENTE",
                message="Non puoi revocare la sessione corrente. Usa il logout.",
            )
        # ⚠️ Zero token con quel sid = la sessione non esiste. Se invece i suoi
        #    token c'erano ed erano gia' bloccati, la risposta resta 204: una
        #    revoca ripetuta e' idempotente, non un errore.
        if blocca_token_sessioni(request.user.id, lambda s: s == sid) == 0:
            raise ServiceError(
                code="E_SESSIONE_NOT_FOUND",
                message="Sessione non trovata o gia' revocata.",
            )
        session_audit_service.record_revoca(
            user_id=request.user.id,
            request=request._request,
            jti=sid,
        )
        return Response(status=204)


class SessioniRevocaTutteView(DomainAPIView):
    """Revoca tutte le sessioni remote dell'utente corrente."""

    skip_area_check = True

    @extend_schema(
        summary="Revoca tutte le altre sessioni",
        responses={200: inline_serializer(
            name="SessioniRevocaTutteResponse",
            fields={"revoked": serializers.IntegerField()},
        )},
    )
    # Scopo: Revoca tutte le sessioni dell'utente tranne quella corrente.
    #        Blacklista i token remoti e registra un evento REVOCA per ogni
    #        SESSIONE ATTIVA revocata — quelle che il pannello mostra.
    #
    # ⛔ Il perimetro dell'AUDIT non e' «tutti i sid mai emessi», ed e' la
    #    correzione del 2026-09-04. Prima si scriveva una riga REVOCA per ogni
    #    sid trovato negli OutstandingToken, cioe' per ogni sessione mai
    #    esistita: misurato sul database di sviluppo, **1138 righe e 2,2
    #    secondi per un click** con due sole sessioni a video, e
    #    `dbops.sessioni_utente` arrivata a **8262 REVOCA su 10344 righe** —
    #    l'80% del diario e' rumore prodotto da questo verbo, che rende
    #    illeggibile proprio la tabella su cui si indaga «chi e' entrato».
    #    ⚠️ E i 2,2 secondi sono anche il motivo per cui il pannello sembrava
    #    non fare niente: nessun segnale a video per il tempo dell'operazione.
    #
    # ⭐ Il perimetro giusto e' quello che l'operatore vede: le sessioni
    #    ATTIVE (`list_sessioni_attive`, la stessa lettura della lista) meno la
    #    corrente. Una sessione non piu' in elenco non ha niente da revocare.
    #
    # ⚠️ La BLACKLIST invece resta larga (tutti i token non correnti): il
    #    diario dice cosa e' successo, la blacklist e' un presidio, e i due non
    #    devono avere lo stesso perimetro. La finestra della lista (1 giorno) e
    #    `REFRESH_TOKEN_LIFETIME` (1 giorno) oggi coincidono — quindi fuori
    #    elenco i token sono gia' scaduti — ma sono due costanti in due file
    #    diversi: restringere anche la blacklist legherebbe un presidio a una
    #    coincidenza non presidiata.
    def post(self, request: Request) -> Response:
        current_sid = _get_current_sid(request)

        # ⚠️ `current_sid` non puo' essere vuoto: dal 2026-09-04 il claim `sid` e'
        #    verificato in autenticazione (`JwtAuditAuthentication`, eccezione
        #    `JwtSenzaSidError`) come gia' accadeva per `identita_id`. Prima non
        #    lo verificava nessuno, e un token senza `sid` faceva scavalcare il
        #    confronto qui sotto: «revoca le altre» revocava anche la propria.
        #    ⛔ Il guard sta LI' e non qui: le view che leggono il sid sono tre
        #    (revoca, revoca-tutte, lista) piu' logout e audit del refresh — un
        #    controllo per view ne copre una e lascia scoperte le altre.
        #    Correzione del team DB al brief, e aveva ragione.

        # Le sessioni che il pannello mostra: e' questo che si sta revocando.
        repo = SessionAuditRepository()
        sessioni_attive = {
            str(s["jti"])
            for s in repo.list_sessioni_attive(request.user.id)
            if s["jti"] and str(s["jti"]) != current_sid
        }

        # Tutti i token che non sono della sessione corrente.
        blocca_token_sessioni(
            request.user.id, lambda s: bool(s) and s != current_sid
        )

        for sid in sorted(sessioni_attive):
            session_audit_service.record_revoca(
                user_id=request.user.id,
                request=request._request,
                jti=sid,
            )

        return success_response({"revoked": len(sessioni_attive)})
