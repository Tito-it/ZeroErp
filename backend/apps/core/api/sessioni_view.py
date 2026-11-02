# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint sessioni attive utente:
#        GET  /api/v1/core/me/sessioni/           — lista altre sessioni attive
#        POST /api/v1/core/me/sessioni/revoca-tutte/ — revoca tutte le altre sessioni
#        POST /api/v1/core/me/sessioni/<jti>/revoca/ — revoca sessione specifica
# ------------------------------------------------------------

from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request
from django.http import JsonResponse
from rest_framework.response import Response
from apps.core.api.base_views import DomainAPIView
from apps.core.api.openapi_params import param_ricerca_full
from apps.core.api.payload_validators import paginated_envelope, parse_list_params

from apps.core.api.success_responses import success_response
from apps.core.db.session_audit_repository import SessionAuditRepository
from apps.core.services import session_audit_service
from apps.core.services.request_context import sid_corrente
from apps.core.services.revoca_token import blocca_token_sessioni
from apps.core.services.service_errors import ServiceError
from apps.core.api.endpoint_helpers import utente_autenticato_id


class SessioniAttiveListView(DomainAPIView):
    """Lista sessioni attive dell'utente corrente, escludendo quella corrente.

    E' la lista a catalogo `core.sessioni_attive` (lista 83): envelope
    paginato standard, ordinamento sulla whitelist del repository, ricerca
    libera sulle colonne che il catalogo accende.
    ⛔ Nessun `lista_codice`: la lista e' GLOBALE (`perimetro_emittente =
    false`) — sono le sessioni dell'utente collegato, non dati di un'azienda —
    e il suo posto e' `_ESENZIONI` di `test_perimetro_emittente_copertura`.
    """

    skip_area_check = True
    is_search_endpoint = True

    @extend_schema(
        summary="Lista altre sessioni attive utente",
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={
            200: inline_serializer(
                name="SessioniAttiveResponse",
                fields={
                    "data": inline_serializer(
                        name="SessioniAttiveData",
                        fields={
                            "results": serializers.ListField(
                                help_text="Pagina di sessioni attive (esclusa la corrente)."
                            ),
                            "count": serializers.IntegerField(
                                help_text="Sessioni che rispondono alla ricerca (tutte le pagine)."
                            ),
                            "page": serializers.IntegerField(),
                            "page_size": serializers.IntegerField(),
                            "total_pages": serializers.IntegerField(),
                            "totale_attive": serializers.IntegerField(
                                help_text=(
                                    "Altre sessioni attive a prescindere dalla ricerca: "
                                    "quelle che «revoca tutte» chiude."
                                )
                            ),
                        },
                    ),
                },
            )
        },
    )
    # Scopo: Lista paginata delle sessioni attive dell'utente corrente, esclusa
    #        la corrente. Il frontend mostra il pannello solo se ce n'e' almeno una.
    # ⭐ `totale_attive` accanto a `count`, e non e' un doppione: `count` conta
    #    le righe TROVATE, `totale_attive` le sessioni che esistono. Il badge
    #    del pannello e la conferma di «revoca tutte» parlano del secondo — una
    #    ricerca che trova una sessione su tre non deve far dire al dialog
    #    «revocherai 1 sessione» mentre ne revoca tre. Senza ricerca coincidono,
    #    e la seconda lettura non si fa.
    def get(self, request: Request) -> JsonResponse:
        p = parse_list_params(request.query_params, default_order="data_ultimo_evento")
        repo = SessionAuditRepository()
        current_sid = sid_corrente(request)
        user_id = utente_autenticato_id(request)
        results, total = repo.list_sessioni_attive_paginata(
            user_id,
            escludi_jti=current_sid,
            search=p["search"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            limit=p["limit"],
            offset=p["offset"],
        )
        envelope = paginated_envelope(results, total, p["page"], p["limit"])
        envelope["totale_attive"] = (
            repo.conta_sessioni_attive(user_id, escludi_jti=current_sid)
            if p["search"] else total
        )
        return success_response(envelope)


class SessioneRevocaView(DomainAPIView):
    """Revoca una sessione specifica (non la corrente) — blacklist + evento REVOCA."""

    skip_area_check = True

    @extend_schema(request=None, summary="Revoca sessione specifica", responses={204: None})
    # Scopo: Revoca una sessione per sid — blacklista tutti i token JWT associati.
    def post(self, request: Request, jti: str) -> Response:
        sid = jti  # il parametro URL si chiama jti ma ora contiene un sid
        current_sid = sid_corrente(request)
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
        user_id = utente_autenticato_id(request)
        if blocca_token_sessioni(user_id, lambda s: s == sid) == 0:
            raise ServiceError(
                code="E_SESSIONE_NOT_FOUND",
                message="Sessione non trovata o gia' revocata.",
            )
        session_audit_service.record_revoca(
            user_id=user_id,
            request=request._request,
            jti=sid,
        )
        return Response(status=204)


class SessioniRevocaTutteView(DomainAPIView):
    """Revoca tutte le sessioni remote dell'utente corrente."""

    skip_area_check = True

    @extend_schema(
        request=None,
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
    def post(self, request: Request) -> JsonResponse:
        current_sid = sid_corrente(request)

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
        user_id = utente_autenticato_id(request)
        sessioni_attive = {
            str(s["jti"])
            for s in repo.list_sessioni_attive(user_id)
            if s["jti"] and str(s["jti"]) != current_sid
        }

        # Tutti i token che non sono della sessione corrente.
        blocca_token_sessioni(
            user_id, lambda s: bool(s) and s != current_sid
        )

        for sid in sorted(sessioni_attive):
            session_audit_service.record_revoca(
                user_id=user_id,
                request=request._request,
                jti=sid,
            )

        return success_response({"revoked": len(sessioni_attive)})
