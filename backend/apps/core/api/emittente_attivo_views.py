# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint dell'EMITTENTE ATTIVO — la combo di topbar con cui il super
#        admin sceglie dentro quale emittente lavorare (impersonazione di
#        scope, brief-db-impersonazione-scope-emittente).
#
#          GET  /api/v1/core/me/emittente-attivo/  → opzioni selezionabili
#          POST /api/v1/core/me/emittente-attivo/  → cambia + riemette i token
#
#        Perché il POST riemette i token invece di limitarsi a salvare: la
#        verità della richiesta in corso è il claim JWT, da cui nasce la GUC
#        `app.current_emittente_id`. Senza token nuovi la scelta avrebbe
#        effetto solo al login successivo, e l'utente vedrebbe la combo
#        cambiare senza che i dati si restringano — cioè il difetto peggiore
#        di tutti, l'interfaccia che mente.
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import optional_int
from apps.core.api.success_responses import success_response
from apps.core.services.auth_constants import JWT_CLAIM_EMITTENTE_ATTIVO_ID
from apps.core.services.emittente_attivo_service import EmittenteAttivoService
from apps.core.services.service_errors import ServiceError

E_EMITTENTE_ATTIVO_TOKEN = "E_EMITTENTE_ATTIVO_TOKEN"


class EmittenteAttivoView(DomainAPIView):
    """Opzioni e cambio dell'emittente attivo di sessione."""

    # Non è un'area funzionale: è l'identità con cui si lavora, e serve a
    # qualunque operatore autenticato (che però vede una sola opzione).
    skip_area_check = True

    @extend_schema(
        summary="Emittenti selezionabili per l'utente corrente",
        description=(
            "Elenco degli emittenti fiscali attivi dentro cui l'utente può "
            "lavorare. Per l'operatore è al più uno (il suo, per permesso); "
            "per il super admin sono tutti gli attivi. Alimenta la combo di "
            "topbar e il dialog di scelta iniziale."
        ),
        responses={
            200: inline_serializer(
                name="EmittenteAttivoOpzioniResponse",
                fields={
                    "data": inline_serializer(
                        name="EmittenteAttivoOpzioni",
                        fields={
                            "opzioni": serializers.ListField(
                                child=serializers.DictField(),
                                help_text="emittente_fiscale_id, codice, ragione_sociale.",
                            ),
                        },
                    ),
                },
            ),
        },
    )
    # Scopo: Opzioni della combo, già filtrate dal DB sullo scope di diritto.
    def get(self, request: Request) -> JsonResponse:
        return success_response(
            {"opzioni": EmittenteAttivoService().opzioni(request.user.id)}
        )

    @extend_schema(
        summary="Cambia l'emittente attivo e riemette i token",
        description=(
            "Imposta l'emittente dentro cui lavorare. `emittente_fiscale_id` "
            "null = «Tutti gli emittenti» (modalità di sola lettura: senza "
            "emittente attivo il DB non può valorizzare i documenti). "
            "Richiede il refresh token corrente e ne restituisce una coppia "
            "nuova con il claim aggiornato: il client deve sostituire "
            "entrambi i token e ricaricare lo stato applicativo."
        ),
        request=inline_serializer(
            name="EmittenteAttivoRequest",
            fields={
                "emittente_fiscale_id": serializers.IntegerField(
                    required=False, allow_null=True,
                ),
                "refresh": serializers.CharField(),
            },
        ),
        responses={200: dict},
    )
    # Scopo: Valida la scelta, la persiste e riemette la coppia di token con
    #        il claim aggiornato. La persistenza avviene PRIMA della
    #        riemissione: se il token fallisce, la preferenza è comunque
    #        salvata e il prossimo login parte dall'emittente giusto — il
    #        contrario (token nuovo, preferenza vecchia) sarebbe una sessione
    #        che lavora dove il profilo dice altro.
    #
    #        Pattern `handle_post_json` come ogni POST: parsing, errori e
    #        envelope uniformi. Niente `require_idempotency_key`: l'operazione
    #        è idempotente per costruzione (UPSERT della preferenza + claim
    #        riscritto), come per gli altri endpoint della famiglia token.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            # Stringa vuota = assente (stesso contratto dei filtri opzionali);
            # garbage → ValueError → 400 `invalid_payload` di handle_post_json,
            # non un `int()` che esplode in 500.
            emittente_id = (
                None
                if payload.get("emittente_fiscale_id") in (None, "")
                else optional_int(payload, "emittente_fiscale_id")
            )

            attivo = EmittenteAttivoService().imposta(request.user.id, emittente_id)

            refresh_str = payload.get("refresh")
            if not refresh_str or not isinstance(refresh_str, str):
                raise ServiceError(
                    code=E_EMITTENTE_ATTIVO_TOKEN,
                    message="Refresh token richiesto per applicare il cambio emittente.",
                )
            try:
                refresh = RefreshToken(refresh_str)
            except TokenError as exc:
                raise ServiceError(
                    code=E_EMITTENTE_ATTIVO_TOKEN,
                    message="Sessione non più valida: rifai il login.",
                    detail=str(exc),
                ) from exc

            # Guard anti-scambio: il refresh presentato deve essere dell'utente
            # autenticato. L'access token dice chi sei, il refresh nel body è un
            # dato in ingresso — senza questo confronto si potrebbe far riemettere
            # a un token altrui il claim scelto qui.
            if int(refresh.get("user_id", 0)) != int(request.user.id):
                raise ServiceError(
                    code=E_EMITTENTE_ATTIVO_TOKEN,
                    message="Sessione non coerente con l'utente autenticato.",
                )

            # Claim aggiornato sul refresh; SimpleJWT lo copia sull'access.
            # Modalità globale = claim RIMOSSO, non messo a null: l'assenza è la
            # convenzione con cui `set_jwt_gucs` lascia la GUC vuota.
            if attivo is None:
                refresh.payload.pop(JWT_CLAIM_EMITTENTE_ATTIVO_ID, None)
            else:
                refresh[JWT_CLAIM_EMITTENTE_ATTIVO_ID] = int(attivo)

            return {
                "emittente_attivo": EmittenteAttivoService().descrivi(
                    request.user.id, attivo,
                ),
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }

        return handle_post_json(request, handler=_handler)
