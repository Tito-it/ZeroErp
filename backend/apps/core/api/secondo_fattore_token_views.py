# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il SECONDO PASSO del login (brief sicurezza §3.4-bis, T-2):
#        `POST /api/v1/{admin|portale|shop}/token/secondo-fattore/` con la
#        sfida del primo passo e un codice dell'app di autenticazione, oppure
#        un codice di recupero. Riuscito, apre la sessione nella veste che il
#        primo passo aveva gia' risolto: access nel corpo, refresh nel cookie.
# Note: Freno della credenziale anche qui (D-T2 del brief DB): blocco
#       ricontrollato (un blocco dell'admin arrivato fra i due passi vale), e
#       un codice sbagliato, ripresentato o di recupero non valido conta come
#       un tentativo fallito, come una password sbagliata. Il SUCCESSO sul
#       freno si registra solo qui (`chiudi_accesso_riuscito`): la password
#       giusta del primo passo non azzera i tentativi del codice.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import User
from django.http import HttpResponseBase
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.core.api.auth_views import chiudi_accesso_riuscito
from apps.core.api.multi_veste_token_serializer import emetti_refresh_veste
from apps.core.api.refresh_cookie import handle_post_json_con_refresh
from apps.core.api.throttling import SecondoFattoreRateThrottle
from apps.core.db.auth_repository import AuthRepository
from apps.core.db.secondo_fattore_repository import STATO_DEVICE_ATTIVO
from apps.core.services.auth_constants import JWT_CLAIM_SID
from apps.core.services.nome_tentato import digest_nome_tentato
from apps.core.services.request_context import provenienza_obbligatoria, richiesta_django
from apps.core.services.secondo_fattore_service import SecondoFattoreService
from apps.core.services.service_errors import ServiceError
from apps.core.services.sfida_secondo_fattore import (
    E_TOTP_SFIDA_NON_VALIDA,
    Sfida,
    leggi_sfida,
)


_auth_repo = AuthRepository()
_secondo_fattore = SecondoFattoreService()

_RICHIESTA = inline_serializer(
    name="CoreSecondoFattoreTokenReq",
    fields={
        "sfida": serializers.CharField(),
        "codice": serializers.CharField(required=False),
        "codice_recupero": serializers.CharField(required=False),
    },
)
_RISPOSTA = inline_serializer(
    name="CoreSecondoFattoreTokenResp",
    fields={
        "access": serializers.CharField(),
        "password_change_required": serializers.BooleanField(required=False),
        "codici_recupero_rimasti": serializers.IntegerField(required=False),
    },
)


# Scopo: La sfida rifiutata per uno stato cambiato fra i due passi (veste
#        spenta, device disabilitato, credenziale disattivata): la stessa
#        risposta di una sfida scaduta, perche' il rimedio e' lo stesso —
#        ripartire dalla password, dove il primo passo decidera' di nuovo.
def _sfida_superata(motivo: str) -> ServiceError:
    return ServiceError(
        code=E_TOTP_SFIDA_NON_VALIDA,
        message="La verifica e' scaduta: accedere di nuovo con la password.",
        detail=motivo,
    )


class AuditSecondoFattoreTokenView(APIView):
    """Base astratta del secondo passo: le sottoclassi fissano la `porta`,
    che deve essere quella della sfida."""

    permission_classes = [AllowAny]
    authentication_classes: list[Any] = []
    # Un contatore suo, non quello del login: vedi SecondoFattoreRateThrottle.
    throttle_classes = [SecondoFattoreRateThrottle]
    porta: str = ""

    @extend_schema(
        request=_RICHIESTA,
        responses={200: _RISPOSTA},
        summary="Login, secondo passo: codice del secondo fattore",
    )
    # Scopo: Chiude il login a due passi. Flusso: provenienza → sfida →
    #        credenziale, veste e device ancora validi → blocco → codice (o
    #        codice di recupero) → sessione nella veste della sfida.
    def post(self, request: Request) -> HttpResponseBase:
        if not self.porta:
            raise RuntimeError(
                "AuditSecondoFattoreTokenView e' astratta: usa le sottoclassi per porta."
            )
        django_request = richiesta_django(request)

        def _handler(payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
            provenienza = provenienza_obbligatoria(django_request)
            sfida = leggi_sfida(payload.get("sfida"), porta=self.porta, provenienza=provenienza)
            return self._chiudi(sfida, payload, provenienza, django_request)

        return handle_post_json_con_refresh(request, _handler)

    # Scopo: La parte che segue una sfida valida: rilegge cio' che puo' essere
    #        cambiato fra i due passi, verifica la prova e apre la sessione.
    def _chiudi(
        self, sfida: Sfida, payload: dict[str, Any], provenienza: str, django_request: Any,
    ) -> tuple[dict[str, Any], str]:
        user = User.objects.filter(id=sfida.auth_user_id, is_active=True).first()
        if user is None:
            raise _sfida_superata("credenziale assente o disattivata")
        digest = digest_nome_tentato(user.get_username())

        # La veste deve valere ANCHE al secondo passo: fra i due passi puo'
        # essere stata spenta o essere uscita dalle sue date. Decide il DB.
        identita = _auth_repo.get_veste_utilizzabile(sfida.identita_id, user.id)
        if identita is None:
            raise _sfida_superata("veste della sfida non piu' utilizzabile")
        device = _secondo_fattore.device(user.id)
        if device["stato"] != STATO_DEVICE_ATTIVO:
            raise _sfida_superata("secondo fattore non piu' attivo")

        prova = _secondo_fattore.verifica_prova(
            user,
            device,
            codice=payload.get("codice"),
            codice_recupero=payload.get("codice_recupero"),
            provenienza=provenienza,
        )
        dettaglio = {"secondo_fattore": prova.tipo}
        rimasti = prova.recupero_rimasti

        refresh = emetti_refresh_veste(user, identita)
        cambio_password = chiudi_accesso_riuscito(
            user=user,
            digest=digest,
            provenienza=provenienza,
            identita_id=int(identita["id"]),
            sid=str(refresh[JWT_CLAIM_SID]),
            django_request=django_request,
            dettaglio=dettaglio,
        )
        dati: dict[str, Any] = {"access": str(refresh.access_token)}
        if cambio_password:
            dati["password_change_required"] = True
        if rimasti is not None:
            dati["codici_recupero_rimasti"] = rimasti
        return dati, str(refresh)


class AdminSecondoFattoreTokenView(AuditSecondoFattoreTokenView):
    """Secondo passo di /api/v1/admin/token/."""

    porta = "admin"


class PortaleSecondoFattoreTokenView(AuditSecondoFattoreTokenView):
    """Secondo passo di /api/v1/portale/token/."""

    porta = "portale"


class ShopSecondoFattoreTokenView(AuditSecondoFattoreTokenView):
    """Secondo passo di /api/v1/shop/token/."""

    porta = "shop"
