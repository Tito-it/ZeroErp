# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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

import logging
from typing import Any

from django.contrib.auth.models import User
from django.db import DatabaseError, transaction
from django.http import HttpResponseBase
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.core.api.auth_views import chiudi_accesso_riuscito
from apps.core.api.multi_veste_token_serializer import emetti_refresh_veste
from apps.core.api.refresh_cookie import handle_post_json_con_refresh
from apps.core.api.throttling import LoginRateThrottle
from apps.core.db.auth_repository import AuthRepository
from apps.core.db.secondo_fattore_repository import SecondoFattoreRepository
from apps.core.services import crypto_service, totp_service
from apps.core.services.auth_constants import JWT_CLAIM_SID
from apps.core.services.db_error_fields import structured_db_error_code
from apps.core.services.nome_tentato import digest_nome_tentato, etichetta_log
from apps.core.services.request_context import get_client_ip
from apps.core.services.service_errors import ServiceError
from apps.core.services.sfida_secondo_fattore import (
    E_TOTP_SFIDA_NON_VALIDA,
    Sfida,
    leggi_sfida,
)

logger = logging.getLogger("security")

_auth_repo = AuthRepository()
_secondo_fattore_repo = SecondoFattoreRepository()

E_TOTP_CODICE_NON_VALIDO = "E_TOTP_CODICE_NON_VALIDO"
# I rifiuti del DB che, come il codice sbagliato, sono un tentativo fallito:
# lo stesso codice ripresentato (o uno piu' vecchio) e un codice di recupero
# che non c'e'.
_RIFIUTI_CHE_CONTANO = frozenset({"E_TOTP_PASSO_GIA_USATO", "E_TOTP_RECOVERY_NON_VALIDO"})

# Con quale prova si e' chiuso l'accesso: va nella riga LOGIN di
# `dbops.sessioni_utente` (`dettaglio.secondo_fattore`).
_PROVA_CODICE = "TOTP"
_PROVA_RECUPERO = "CODICE_RECUPERO"

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
    # Lo stesso secchio del primo passo (scope `login`, per IP): password e
    # codici insieme.
    throttle_classes = [LoginRateThrottle]
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
        django_request = request._request if hasattr(request, "_request") else request

        def _handler(payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
            provenienza = get_client_ip(django_request)
            if provenienza is None:
                raise ServiceError(
                    code="E_AUTH_CHIAMATA_NON_VALIDA",
                    message="Chiamata non valida al login: provenienza assente.",
                    detail="IP del chiamante non ricavabile dalla catena di proxy dichiarata.",
                )
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
        chi = etichetta_log(user.id, digest)

        # Blocco dell'admin, freno sulla provenienza, attesa: come al primo
        # passo, e PRIMA di guardare il codice.
        _auth_repo.check_blocco_login(user.id, nome_digest=digest, provenienza=provenienza)

        identita = _auth_repo.get_identita_dettaglio(sfida.identita_id, user.id)
        if identita is None or not identita.get("attivo"):
            raise _sfida_superata("veste della sfida non piu' attiva")
        device = _secondo_fattore_repo.get_device(user.id)
        if device["stato"] != "ATTIVO":
            raise _sfida_superata("secondo fattore non piu' attivo")

        codice = payload.get("codice")
        recupero = payload.get("codice_recupero")
        if not (isinstance(codice, str) and codice) and not (isinstance(recupero, str) and recupero):
            # Una richiesta senza prova non e' un tentativo: non conta.
            raise ServiceError(
                code=E_TOTP_CODICE_NON_VALIDO,
                message="Codice non valido.",
                detail="ne' codice ne' codice di recupero",
                fields=("codice",),
            )

        dettaglio: dict[str, Any]
        rimasti: int | None = None
        if isinstance(codice, str) and codice:
            passo = totp_service.verifica_codice(self._segreto(device, user.id), codice)
            if passo is None:
                self._tentativo_fallito(user.id, digest, provenienza, chi)
                raise ServiceError(
                    code=E_TOTP_CODICE_NON_VALIDO,
                    message="Codice non valido.",
                    fields=("codice",),
                )
            self._prova_al_db(
                lambda: _secondo_fattore_repo.registra_uso(user.id, passo=passo),
                user.id, digest, provenienza, chi,
            )
            dettaglio = {"secondo_fattore": _PROVA_CODICE}
        else:
            assert isinstance(recupero, str)
            rimasti = self._prova_al_db(
                lambda: _secondo_fattore_repo.consuma_recovery(
                    user.id, impronta=totp_service.impronta_codice_recupero(recupero),
                ),
                user.id, digest, provenienza, chi,
            )
            dettaglio = {"secondo_fattore": _PROVA_RECUPERO}

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
            logger.warning("security.login_con_codice_recupero %s rimasti=%s", chi, rimasti)
        return dati, str(refresh)

    # Scopo: Presenta la prova al DB (anti-replay sul passo, consumo del
    #        codice di recupero). Se il DB la rifiuta per un codice
    #        ripresentato o non valido, e' un tentativo fallito (D-T2).
    #        ⛔ In un SAVEPOINT: il rifiuto interrompe la transazione in cui
    #        cade, e la registrazione del tentativo che lo segue non
    #        passerebbe — sotto una transazione esterna il tentativo non
    #        verrebbe contato e il codice d'errore diventerebbe E_DATABASE
    #        (trovato dal login a due passi sul DB vero, 2026-10-01).
    @classmethod
    def _prova_al_db(cls, verbo, auth_user_id: int, digest: bytes, provenienza: str, chi: str):
        try:
            with transaction.atomic():
                return verbo()
        except DatabaseError as exc:
            if structured_db_error_code(exc) in _RIFIUTI_CHE_CONTANO:
                cls._tentativo_fallito(auth_user_id, digest, provenienza, chi)
            raise

    # Scopo: Il segreto in chiaro. ⛔ Un segreto che nessuna chiave apre non
    #        e' un codice sbagliato: e' una chiave tolta prima della rotazione
    #        (brief-db-totp-ricifra-segreto). Errore tecnico, non un tentativo.
    @staticmethod
    def _segreto(device: dict[str, Any], auth_user_id: int) -> str:
        try:
            return crypto_service.decrypt(device["secret_encrypted"])
        except ValueError:
            logger.error("security.totp_segreto_illeggibile user_id=%s", auth_user_id)
            raise RuntimeError("segreto del secondo fattore illeggibile con le chiavi configurate") from None

    # Scopo: D-T2. Un codice sbagliato conta come una password sbagliata:
    #        stesso freno sulla provenienza, stessa attesa crescente.
    @staticmethod
    def _tentativo_fallito(auth_user_id: int, digest: bytes, provenienza: str, chi: str) -> None:
        esito = _auth_repo.registra_tentativo_login(
            auth_user_id, nome_digest=digest, provenienza=provenienza, successo=False,
        )
        logger.warning(
            "security.secondo_fattore_fallito %s provenienza=%s bloccato=%s",
            chi, provenienza, esito.get("bloccato"),
        )


class AdminSecondoFattoreTokenView(AuditSecondoFattoreTokenView):
    """Secondo passo di /api/v1/admin/token/."""

    porta = "admin"


class PortaleSecondoFattoreTokenView(AuditSecondoFattoreTokenView):
    """Secondo passo di /api/v1/portale/token/."""

    porta = "portale"


class ShopSecondoFattoreTokenView(AuditSecondoFattoreTokenView):
    """Secondo passo di /api/v1/shop/token/."""

    porta = "shop"
