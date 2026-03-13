# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views per il modulo Amm. Software — gestione utenti e reparti.
# ------------------------------------------------------------

from __future__ import annotations

from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.core.api.permissions import IsAdminZeroERP
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import optional_int
from apps.core.api.success_responses import success_response
from apps.core.services.error_manager import ErrorManager
from apps.core.services.permissions_cache import invalidate_department, invalidate_user
from apps.amm_software.db.amm_software_repository import AmmSoftwareRepository


# ================================================================== #
# Utenti — lista, dettaglio, modifica, disabilita                     #
# ================================================================== #


class UtentiListView(APIView):
    """Lista utenti con filtri e paginazione."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminZeroERP]
    skip_area_check = True
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="search", type=str, required=False, description="Ricerca su username, nome, cognome, email."),
            OpenApiParameter(name="ruolo_sistema", type=str, required=False, description="Filtro ruolo: ADMIN, OPERATIVO, DISABILITATO."),
            OpenApiParameter(name="unita_organizzativa_id", type=int, required=False, description="Filtro unita' organizzativa."),
            OpenApiParameter(name="is_active", type=bool, required=False, description="Filtro stato attivo auth_user."),
            OpenApiParameter(name="limit", type=int, required=False, description="Righe per pagina (default 50, max 200)."),
            OpenApiParameter(name="offset", type=int, required=False, description="Offset paginazione (default 0)."),
            OpenApiParameter(name="order_by", type=str, required=False, description="Colonna ordinamento."),
            OpenApiParameter(name="order_dir", type=str, required=False, description="Direzione: ASC o DESC."),
        ],
        responses={200: inline_serializer(
            name="UtentiListResponse",
            fields={
                "data": inline_serializer(name="UtentiListData", fields={
                    "count": serializers.IntegerField(),
                    "results": serializers.ListField(child=serializers.DictField()),
                }),
            },
        )},
    )
    # Scopo: Restituisce la lista paginata degli utenti con filtri opzionali.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        repo = AmmSoftwareRepository()

        search = qp.get("search") or None
        ruolo_sistema = qp.get("ruolo_sistema") or None
        uo_id = optional_int({"v": qp.get("unita_organizzativa_id")}, "v")
        # is_active: None se non specificato (nessun filtro), True/False altrimenti
        raw_active = qp.get("is_active")
        is_active: bool | None = None
        if raw_active is not None:
            is_active = raw_active.lower() in ("1", "true", "yes")
        limit = min(optional_int({"v": qp.get("limit")}, "v") or 50, 200)
        offset = optional_int({"v": qp.get("offset")}, "v") or 0
        order_by = qp.get("order_by") or None
        order_dir = qp.get("order_dir") or None

        results, total_count = repo.list_utenti(
            search=search,
            ruolo_sistema=ruolo_sistema,
            unita_organizzativa_id=uo_id,
            is_active=is_active,
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_dir=order_dir,
        )

        return success_response({"count": total_count, "results": results})

    @extend_schema(
        request=inline_serializer(
            name="UtentiCreateRequest",
            fields={
                "cognome": serializers.CharField(),
                "nome": serializers.CharField(),
                "codice_fiscale": serializers.CharField(),
                "data_nascita": serializers.CharField(required=False),
                "sesso": serializers.CharField(required=False, help_text="M|F, default M"),
                "username": serializers.CharField(),
                "email": serializers.CharField(),
                "password": serializers.CharField(),
                "qualifica_id": serializers.IntegerField(),
                "ruolo_sistema": serializers.CharField(required=False, help_text="ADMIN|OPERATIVO, default OPERATIVO"),
                "unita_organizzativa_id": serializers.IntegerField(required=False),
                "valido_dal": serializers.CharField(required=False),
                "valido_al": serializers.CharField(required=False),
                "comune_nascita_id": serializers.IntegerField(required=False),
                "indirizzo_resid_dettaglio_id": serializers.IntegerField(required=False),
                "indirizzo_domfisc_dettaglio_id": serializers.IntegerField(required=False),
            },
        ),
        responses={200: inline_serializer(
            name="UtentiCreateResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea un nuovo operatore con hash password e ritorna il dettaglio completo.
    # Valida i parametri obbligatori, hasha la password e delega al repository
    # che chiama l'orchestratore DB fn_crea_operatore (building block).
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict) -> dict:
            # Validazione campi obbligatori
            cognome = (payload.get("cognome") or "").strip()
            nome = (payload.get("nome") or "").strip()
            codice_fiscale = (payload.get("codice_fiscale") or "").strip()
            username = (payload.get("username") or "").strip()
            email = (payload.get("email") or "").strip()
            password = payload.get("password") or ""
            qualifica_id = payload.get("qualifica_id")
            uo_id = payload.get("unita_organizzativa_id")
            comune_nascita_id = optional_int(payload, "comune_nascita_id")
            indirizzo_resid_id = optional_int(payload, "indirizzo_resid_dettaglio_id")
            indirizzo_domfisc_id = optional_int(payload, "indirizzo_domfisc_dettaglio_id")

            ErrorManager.require(bool(cognome), code="E_AMM_VALIDAZIONE", message="Cognome obbligatorio.")
            ErrorManager.require(bool(nome), code="E_AMM_VALIDAZIONE", message="Nome obbligatorio.")
            ErrorManager.require(bool(codice_fiscale), code="E_AMM_VALIDAZIONE", message="Codice fiscale obbligatorio.")
            ErrorManager.require(bool(username), code="E_AMM_VALIDAZIONE", message="Username obbligatorio.")
            ErrorManager.require(bool(email), code="E_AMM_VALIDAZIONE", message="Email obbligatoria.")
            ErrorManager.require(bool(password), code="E_AMM_VALIDAZIONE", message="Password obbligatoria.")
            ErrorManager.require(qualifica_id is not None and int(qualifica_id) > 0, code="E_AMM_VALIDAZIONE", message="Qualifica obbligatoria.")

            repo = AmmSoftwareRepository()
            auth_user_id = repo.crea_operatore(
                cognome=cognome,
                nome=nome,
                codice_fiscale=codice_fiscale,
                username=username,
                email=email,
                password_hash=make_password(password),
                qualifica_id=int(qualifica_id),  # type: ignore[arg-type]
                unita_organizzativa_id=int(uo_id) if uo_id else None,
                data_nascita=payload.get("data_nascita"),
                sesso=payload.get("sesso", "M"),
                ruolo_sistema=payload.get("ruolo_sistema", "OPERATIVO"),
                valido_dal=payload.get("valido_dal"),
                valido_al=payload.get("valido_al"),
                comune_nascita_id=comune_nascita_id,
                indirizzo_resid_dettaglio_id=indirizzo_resid_id,
                indirizzo_domfisc_dettaglio_id=indirizzo_domfisc_id,
            )

            utente = repo.get_utente_detail(auth_user_id)
            return utente or {}

        return handle_post_json(request, handler=_handler)


class UtentiDetailView(APIView):
    """Dettaglio e modifica singolo utente."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminZeroERP]
    skip_area_check = True

    @extend_schema(
        responses={200: inline_serializer(
            name="UtenteDetailResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Restituisce il dettaglio completo di un utente con conteggi override.
    def get(self, request: Request, auth_user_id: int) -> JsonResponse:
        repo = AmmSoftwareRepository()
        utente = repo.get_utente_detail(auth_user_id)
        ErrorManager.require(
            utente is not None,
            code="E_AMM_UTENTE_NOT_FOUND",
            message=f"Utente {auth_user_id} non trovato.",
        )
        assert utente is not None
        return success_response(utente)

    @extend_schema(
        request=inline_serializer(
            name="UtentePatchRequest",
            fields={
                "email": serializers.CharField(required=False),
                "first_name": serializers.CharField(required=False),
                "last_name": serializers.CharField(required=False),
                "ruolo_sistema": serializers.CharField(required=False),
                "unita_organizzativa_id": serializers.IntegerField(required=False),
                "attivo": serializers.BooleanField(required=False),
                "valido_al": serializers.CharField(required=False),
            },
        ),
        responses={200: inline_serializer(
            name="UtentePatchResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Modifica i campi di un utente e invalida la cache permessi.
    def patch(self, request: Request, auth_user_id: int) -> JsonResponse:
        repo = AmmSoftwareRepository()

        # Verifica esistenza
        utente = repo.get_utente_detail(auth_user_id)
        ErrorManager.require(
            utente is not None,
            code="E_AMM_UTENTE_NOT_FOUND",
            message=f"Utente {auth_user_id} non trovato.",
        )
        assert utente is not None

        data = request.data
        repo.update_utente(
            auth_user_id,
            email=data.get("email"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            ruolo_sistema=data.get("ruolo_sistema"),
            unita_organizzativa_id=data.get("unita_organizzativa_id"),
            attivo=data.get("attivo"),
            valido_al=data.get("valido_al"),
        )

        # Invalida cache permessi
        invalidate_user(auth_user_id)

        # Ritorna dettaglio aggiornato
        updated = repo.get_utente_detail(auth_user_id)
        return success_response(updated or {})


class UtentiDisabilitaView(APIView):
    """Disabilita un utente (shortcut: ruolo_sistema=DISABILITATO + attivo=false)."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminZeroERP]
    skip_area_check = True

    @extend_schema(
        responses={200: inline_serializer(
            name="UtenteDisabilitaResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Disabilita un utente, invalida cache e token.
    def post(self, request: Request, auth_user_id: int) -> JsonResponse:
        repo = AmmSoftwareRepository()

        utente = repo.get_utente_detail(auth_user_id)
        ErrorManager.require(
            utente is not None,
            code="E_AMM_UTENTE_NOT_FOUND",
            message=f"Utente {auth_user_id} non trovato.",
        )
        assert utente is not None

        repo.disabilita_utente(auth_user_id)
        invalidate_user(auth_user_id)

        # Invalida token JWT via blacklist (best-effort)
        _blacklist_user_tokens(auth_user_id)

        updated = repo.get_utente_detail(auth_user_id)
        return success_response(updated or {})


class UtentiUOListView(APIView):
    """Lista unita' organizzative per dropdown filtro."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminZeroERP]
    skip_area_check = True

    @extend_schema(
        responses={200: inline_serializer(
            name="UOListResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Restituisce la lista unita' organizzative per il dropdown filtro.
    def get(self, request: Request) -> JsonResponse:
        repo = AmmSoftwareRepository()
        results = repo.list_unita_organizzative()
        return success_response({"results": results})


# ================================================================== #
# Override permessi utente                                              #
# ================================================================== #


class OverrideAreeView(APIView):
    """GET/PUT override aree funzionali per utente."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminZeroERP]
    skip_area_check = True

    @extend_schema(
        responses={200: inline_serializer(
            name="OverrideAreeGetResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Restituisce gli override aree per un utente.
    def get(self, request: Request, auth_user_id: int) -> JsonResponse:
        repo = AmmSoftwareRepository()
        results = repo.get_override_aree(auth_user_id)
        return success_response({"results": results})

    @extend_schema(
        request=inline_serializer(
            name="OverrideAreePutRequest",
            fields={"items": serializers.ListField(child=serializers.DictField())},
        ),
        responses={200: inline_serializer(
            name="OverrideAreePutResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Sostituisce gli override aree per un utente e invalida cache.
    def put(self, request: Request, auth_user_id: int) -> JsonResponse:
        repo = AmmSoftwareRepository()
        items = request.data.get("items", [])
        repo.put_override_aree(auth_user_id, items)
        invalidate_user(auth_user_id)
        results = repo.get_override_aree(auth_user_id)
        return success_response({"results": results})


class OverrideAzioniView(APIView):
    """GET/PUT override azioni processo per utente."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminZeroERP]
    skip_area_check = True

    @extend_schema(
        responses={200: inline_serializer(
            name="OverrideAzioniGetResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Restituisce gli override azioni per un utente.
    def get(self, request: Request, auth_user_id: int) -> JsonResponse:
        repo = AmmSoftwareRepository()
        results = repo.get_override_azioni(auth_user_id)
        return success_response({"results": results})

    @extend_schema(
        request=inline_serializer(
            name="OverrideAzioniPutRequest",
            fields={"items": serializers.ListField(child=serializers.DictField())},
        ),
        responses={200: inline_serializer(
            name="OverrideAzioniPutResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Sostituisce gli override azioni per un utente e invalida cache.
    def put(self, request: Request, auth_user_id: int) -> JsonResponse:
        repo = AmmSoftwareRepository()
        items = request.data.get("items", [])
        repo.put_override_azioni(auth_user_id, items)
        invalidate_user(auth_user_id)
        results = repo.get_override_azioni(auth_user_id)
        return success_response({"results": results})


class EmittentiScopeView(APIView):
    """GET/PUT scope emittenti fiscali per utente."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminZeroERP]
    skip_area_check = True

    @extend_schema(
        responses={200: inline_serializer(
            name="EmittentiScopeGetResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Restituisce gli emittenti fiscali associati a un utente.
    def get(self, request: Request, auth_user_id: int) -> JsonResponse:
        repo = AmmSoftwareRepository()
        results = repo.get_emittenti_scope(auth_user_id)
        return success_response({"results": results})

    @extend_schema(
        request=inline_serializer(
            name="EmittentiScopePutRequest",
            fields={"emittente_ids": serializers.ListField(child=serializers.IntegerField())},
        ),
        responses={200: inline_serializer(
            name="EmittentiScopePutResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Sostituisce lo scope emittenti di un utente e invalida cache.
    def put(self, request: Request, auth_user_id: int) -> JsonResponse:
        repo = AmmSoftwareRepository()
        emittente_ids = request.data.get("emittente_ids", [])
        repo.put_emittenti_scope(auth_user_id, emittente_ids)
        invalidate_user(auth_user_id)
        results = repo.get_emittenti_scope(auth_user_id)
        return success_response({"results": results})


# ================================================================== #
# Reparti e profili                                                    #
# ================================================================== #


class RepartiListView(APIView):
    """Lista reparti con conteggi profilo e operatori."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminZeroERP]
    skip_area_check = True

    @extend_schema(
        responses={200: inline_serializer(
            name="RepartiListResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Restituisce la lista reparti con flag profilo e conteggio operatori.
    def get(self, request: Request) -> JsonResponse:
        repo = AmmSoftwareRepository()
        results = repo.list_reparti()
        return success_response({"results": results})


class RepartoProfiloView(APIView):
    """GET/PUT profilo permessi di un reparto."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminZeroERP]
    skip_area_check = True

    @extend_schema(
        responses={200: inline_serializer(
            name="RepartoProfiloGetResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Restituisce il profilo completo di un reparto (aree + azioni).
    def get(self, request: Request, uo_id: int) -> JsonResponse:
        repo = AmmSoftwareRepository()
        profilo = repo.get_profilo_reparto(uo_id)
        return success_response(profilo)

    @extend_schema(
        request=inline_serializer(
            name="RepartoProfiloPutRequest",
            fields={
                "aree": serializers.ListField(child=serializers.DictField()),
                "azioni": serializers.ListField(child=serializers.DictField()),
            },
        ),
        responses={200: inline_serializer(
            name="RepartoProfiloPutResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Sostituisce il profilo di un reparto e invalida cache di tutti gli operatori.
    def put(self, request: Request, uo_id: int) -> JsonResponse:
        repo = AmmSoftwareRepository()
        aree = request.data.get("aree", [])
        azioni = request.data.get("azioni", [])
        repo.put_profilo_reparto(uo_id, aree, azioni)
        invalidate_department(uo_id)
        profilo = repo.get_profilo_reparto(uo_id)
        return success_response(profilo)


# ================================================================== #
# Lookup                                                               #
# ================================================================== #


class LookupAreeView(APIView):
    """Lista aree funzionali attive per selezione."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminZeroERP]
    skip_area_check = True

    @extend_schema(
        responses={200: inline_serializer(
            name="LookupAreeResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Restituisce la lista aree funzionali attive.
    def get(self, request: Request) -> JsonResponse:
        repo = AmmSoftwareRepository()
        return success_response({"results": repo.list_aree_funzionali()})


class LookupAzioniView(APIView):
    """Lista azioni processo attive per selezione."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminZeroERP]
    skip_area_check = True

    @extend_schema(
        responses={200: inline_serializer(
            name="LookupAzioniResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Restituisce la lista azioni processo attive.
    def get(self, request: Request) -> JsonResponse:
        repo = AmmSoftwareRepository()
        return success_response({"results": repo.list_azioni_processo()})


class LookupEmittentiView(APIView):
    """Lista emittenti fiscali attivi per selezione scope."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminZeroERP]
    skip_area_check = True

    @extend_schema(
        responses={200: inline_serializer(
            name="LookupEmittentiResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Restituisce la lista emittenti fiscali attivi.
    def get(self, request: Request) -> JsonResponse:
        repo = AmmSoftwareRepository()
        return success_response({"results": repo.list_emittenti_fiscali()})


# ================================================================== #
# Helpers                                                              #
# ================================================================== #


# Scopo: Invalida i token JWT dell'utente via blacklist SimpleJWT (best-effort).
def _blacklist_user_tokens(auth_user_id: int) -> None:
    try:
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
        tokens = OutstandingToken.objects.filter(user_id=auth_user_id)
        for token in tokens:
            try:
                from rest_framework_simplejwt.tokens import RefreshToken
                rt = RefreshToken(token.token)
                rt.blacklist()
            except Exception:
                pass  # Token gia' scaduto o gia' nella blacklist
    except ImportError:
        pass  # Blacklist non installata
