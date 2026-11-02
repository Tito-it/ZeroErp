# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: L'area «Accessi» di Amm. Software (brief-db-be-fe-area-accessi):
#          GET  accessi/altri/                       le persone senza veste operatore
#          GET  accessi/sistema/                     le credenziali delle macchine
#          GET  credenziali/<id>/                    lo stato della credenziale
#          DELETE credenziali/<id>/                  elimina una credenziale senza vesti
#          POST credenziali/<id>/blocca/             blocco dell'amministratore
#          POST credenziali/<id>/sblocca/            toglie il blocco
#          GET  credenziali/<id>/secondo-fattore/    stato del secondo fattore
#          POST credenziali/<id>/secondo-fattore/obbligo/    obbligo sulla credenziale
#          POST credenziali/<id>/secondo-fattore/disattiva/  cancella il device
# Note: ⛔ Le azioni della CREDENZIALE non stanno sotto `/operatori/`: valgono
#       per tutte le sue vesti, e una persona senza veste operatore (un
#       cliente del portale) non si raggiunge da li' (A-4, A-5). Fino al
#       2026-10-02 il secondo fattore stava in `operatori/<id>/secondo-fattore/`:
#       ritirato nello stesso giro, niente rotte doppie.
#       `AdminAPIView` (binding SUPER_ADMIN); i verbi del DB lo ricontrollano
#       (`fn_guard_super_admin`). Le due liste sono `AdminAPIView` come quella
#       degli operatori: niente `lista_codice` (il cancello di perimetro e' di
#       `DomainAPIView`), le esenzioni stanno in `test_perimetro_emittente_copertura`.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.amm_software.constants import DEFAULT_LIMIT, MAX_LIMIT
from apps.amm_software.db.accessi_repository import (
    ACCESSI_ALTRI_ORDER_COLUMNS,
    ACCESSI_SISTEMA_ORDER_COLUMNS,
    STATI_ACCESSO,
    TIPI_SISTEMA,
)
from apps.amm_software.services.accessi_service import AccessiService
from apps.amm_software.services.amm_software_service import E_AMM_VALIDAZIONE
from apps.core.api.base_views import AdminAPIView
from apps.core.api.endpoint_helpers import handle_post_json, utente_autenticato_id
from apps.core.api.openapi_params import descrizione_order_by, param_ricerca_full
from apps.core.api.payload_validators import (
    paginated_envelope,
    parse_list_params,
    qp_bool_optional,
    qp_int_optional,
    qp_str,
    qp_str_upper,
)
from apps.core.api.success_responses import success_response
from apps.core.db.secondo_fattore_repository import STATI_DEVICE
from apps.core.services.auth_constants import CATEGORIA_ACCESSO
from apps.core.services.payload_helpers import PayloadValidator
from apps.core.services.request_context import richiesta_django
from apps.core.services.secondo_fattore_service import SecondoFattoreService

_PARAMS_PAGINA = [
    OpenApiParameter(name="limit", type=int, required=False),
    OpenApiParameter(name="offset", type=int, required=False),
    OpenApiParameter(name="order_dir", type=str, required=False, description="asc | desc."),
]


# ================================================================== #
# Le liste                                                             #
# ================================================================== #


class AccessiAltriListView(AdminAPIView):
    """GET /amm-software/accessi/altri/ — il tab «Altri accessi» (lista 104)."""

    is_search_endpoint = True

    @extend_schema(
        summary="Altri accessi: le persone senza veste operatore",
        description=(
            "Una riga per credenziale di categoria ALTRO (`script.fn_categoria_accesso`): "
            "clienti e fornitori del portale, clienti dello shop, e le credenziali senza "
            "alcuna veste (`nessun_accesso`). `vesti` porta una voce per veste, anche spenta, "
            "con lo stato di `script.fn_stato_veste` e il soggetto collegato (`cliente_ids` "
            "e' un array). Legge `anagrafiche.vw_accessi_altri`."
        ),
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="ruolo_applicativo", type=str, required=False,
                             description="Una veste di quel tipo fra le vesti della credenziale."),
            OpenApiParameter(name="stato_accesso", type=str, required=False,
                             description=f"Il migliore fra le vesti: {', '.join(STATI_ACCESSO)}."),
            OpenApiParameter(name="nessun_accesso", type=bool, required=False),
            OpenApiParameter(name="secondo_fattore_stato", type=str, required=False,
                             description=f"{', '.join(STATI_DEVICE)}."),
            OpenApiParameter(name="secondo_fattore_obbligatorio", type=bool, required=False),
            OpenApiParameter(name="bloccata", type=bool, required=False),
            OpenApiParameter(
                name="order_by", type=str, required=False,
                description=descrizione_order_by(ACCESSI_ALTRI_ORDER_COLUMNS, "Default: nome_visualizzato."),
            ),
            *_PARAMS_PAGINA,
        ],
        responses={200: inline_serializer(name="AccessiAltriListResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Lista paginata delle credenziali di categoria ALTRO.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp, default_order="nome_visualizzato",
                              default_limit=DEFAULT_LIMIT, max_limit=MAX_LIMIT)
        results, total = AccessiService().list_accessi_altri(
            search=p["search"],
            ruolo_applicativo=qp_str_upper(qp.get("ruolo_applicativo")),
            stato_accesso=qp_str_upper(qp.get("stato_accesso")),
            nessun_accesso=qp_bool_optional(qp.get("nessun_accesso"), "nessun_accesso"),
            secondo_fattore_stato=qp_str_upper(qp.get("secondo_fattore_stato")),
            secondo_fattore_obbligatorio=qp_bool_optional(
                qp.get("secondo_fattore_obbligatorio"), "secondo_fattore_obbligatorio",
            ),
            bloccata=qp_bool_optional(qp.get("bloccata"), "bloccata"),
            limit=p["limit"],
            offset=p["offset"],
            order_by=qp_str(qp.get("order_by")),
            order_dir=p["order_dir"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))


class AccessiSistemaListView(AdminAPIView):
    """GET /amm-software/accessi/sistema/ — il tab «Di sistema» (lista 105), sola lettura."""

    is_search_endpoint = True

    @extend_schema(
        summary="Accessi di sistema: le credenziali delle macchine",
        description=(
            "Una riga per credenziale di categoria SISTEMA: gli utenti tecnici dei processi "
            "automatici (`tipo = PROCESSO`, con `processo_id` da aprire) e le credenziali "
            "`API_CLIENT` (`processo_id` null). Sola lettura (A-6): il proprietario di "
            "queste credenziali e' il pannello dei processi. Legge `anagrafiche.vw_accessi_sistema`."
        ),
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="tipo", type=str, required=False, description=f"{', '.join(TIPI_SISTEMA)}."),
            OpenApiParameter(name="emittente_fiscale_id", type=int, required=False),
            OpenApiParameter(name="identita_attiva", type=bool, required=False),
            OpenApiParameter(name="bloccata", type=bool, required=False),
            OpenApiParameter(
                name="order_by", type=str, required=False,
                description=descrizione_order_by(ACCESSI_SISTEMA_ORDER_COLUMNS, "Default: username."),
            ),
            *_PARAMS_PAGINA,
        ],
        responses={200: inline_serializer(name="AccessiSistemaListResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Lista paginata delle credenziali di categoria SISTEMA.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp, default_order="username",
                              default_limit=DEFAULT_LIMIT, max_limit=MAX_LIMIT)
        results, total = AccessiService().list_accessi_sistema(
            search=p["search"],
            tipo=qp_str_upper(qp.get("tipo")),
            emittente_fiscale_id=qp_int_optional(qp.get("emittente_fiscale_id"), "emittente_fiscale_id"),
            identita_attiva=qp_bool_optional(qp.get("identita_attiva"), "identita_attiva"),
            bloccata=qp_bool_optional(qp.get("bloccata"), "bloccata"),
            limit=p["limit"],
            offset=p["offset"],
            order_by=qp_str(qp.get("order_by")),
            order_dir=p["order_dir"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))


# ================================================================== #
# La credenziale                                                       #
# ================================================================== #

_CREDENZIALE = inline_serializer(
    name="CredenzialeResp",
    fields={
        "auth_user_id": serializers.IntegerField(),
        "username": serializers.CharField(),
        "email": serializers.CharField(allow_null=True),
        "categoria": serializers.ChoiceField(choices=CATEGORIA_ACCESSO),
        "bloccata": serializers.BooleanField(),
        "bloccata_dal": serializers.DateTimeField(allow_null=True),
        "bloccata_da": serializers.CharField(allow_null=True),
        "motivo_blocco": serializers.CharField(allow_null=True),
        "can_block": serializers.BooleanField(),
        "block_reason": serializers.CharField(allow_null=True),
        "block_reason_key": serializers.CharField(allow_null=True),
        "can_delete": serializers.BooleanField(),
        "delete_reason": serializers.CharField(allow_null=True),
        "delete_reason_key": serializers.CharField(allow_null=True),
        "delete_dettaglio": serializers.DictField(allow_null=True),
    },
)


class CredenzialeDetailView(AdminAPIView):
    """GET / DELETE /amm-software/credenziali/<id>/ — stato della credenziale, eliminazione."""

    @extend_schema(
        summary="Stato di una credenziale (blocco dell'amministratore)",
        description=(
            "Categoria (il tab dell'area Accessi), blocco dell'amministratore (quando, chi, "
            "perche') e la capability del blocco: `can_block = false` con `block_reason` "
            "`ULTIMO_SUPER_ADMIN` sull'ultimo SUPER_ADMIN raggiungibile (il guard del DB "
            "rifiuterebbe con `E_PROFILO_ULTIMO_SUPER_ADMIN`). Porta anche la capability "
            "dell'eliminazione (`can_delete`, `delete_reason`, `delete_reason_key`, "
            "`delete_dettaglio`): il primo motivo di `script.fn_check_credenziale_eliminabile`."
        ),
        responses={200: _CREDENZIALE},
    )
    # Scopo: Lo stato della credenziale per il pannello delle sue azioni.
    def get(self, request: Request, auth_user_id: int) -> JsonResponse:
        return success_response(AccessiService().get_credenziale(auth_user_id))

    @extend_schema(
        summary="Elimina una credenziale senza vesti",
        description=(
            "Elimina una credenziale che non ha mai avuto una veste "
            "(`script.fn_elimina_credenziale`): e' il gesto che chiede il presidio "
            "`dbops.vw_credenziali_da_sanare` (`NESSUNA_VESTE`). Il verbo rifiuta col primo "
            "motivo della check: `E_CREDENZIALE_CON_VESTI` (409, anche una veste spenta), "
            "`E_CREDENZIALE_CON_STORIA` (409, la credenziale compare gia' fra i dati: il "
            "messaggio dice dove), `E_CREDENZIALE_STORIA_NON_VERIFICABILE` (500, mancano i "
            "legami del database verso le credenziali). La traccia resta in "
            "`config.credenziali_eliminate`."
        ),
        parameters=[
            OpenApiParameter(
                name="Idempotency-Key", type=str, location=OpenApiParameter.HEADER, required=True,
                description=(
                    "Obbligatoria: il gesto e' irreversibile e un doppio invio riceverebbe "
                    "altrimenti un 404 per un'operazione riuscita."
                ),
            ),
        ],
        request=None,
        responses={200: inline_serializer(
            name="CredenzialeEliminaResp",
            fields={"status": serializers.CharField(), "auth_user_id": serializers.IntegerField()},
        )},
    )
    # Scopo: Elimina la credenziale, o riporta il motivo del rifiuto.
    # ⚠️ `handle_post_json` e non una chiamata diretta: e' la sede unica del
    #    controllo `Idempotency-Key`. Il corpo di un DELETE e' vuoto e il
    #    payload si ignora: quello che serve e' nel path.
    def delete(self, request: Request, auth_user_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda _payload: AccessiService().elimina_credenziale(auth_user_id),
            require_idempotency_key=True,
        )


class CredenzialeBloccaView(AdminAPIView):
    """POST /amm-software/credenziali/<id>/blocca/ — blocco dell'amministratore."""

    @extend_schema(
        summary="Blocca una credenziale",
        description=(
            "Blocca la credenziale su tutte le porte (`script.fn_blocca_credenziale`: non "
            "scade, il reset password non lo toglie) e chiude tutte le sue sessioni, nella "
            "stessa transazione. Motivo obbligatorio (`E_CREDENZIALE_MOTIVO_OBBLIGATORIO`); "
            "l'ultimo SUPER_ADMIN raggiungibile non si blocca (`E_PROFILO_ULTIMO_SUPER_ADMIN`). "
            "`Idempotency-Key` obbligatoria."
        ),
        request=inline_serializer(name="CredenzialeBloccaReq", fields={"motivo": serializers.CharField()}),
        responses={200: _CREDENZIALE},
    )
    # Scopo: Blocca la credenziale e ne chiude le sessioni.
    def post(self, request: Request, auth_user_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            motivo = PayloadValidator(validation_code=E_AMM_VALIDAZIONE).optional_string(payload, "motivo")
            return AccessiService().blocca_credenziale(auth_user_id, motivo)

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class CredenzialeSbloccaView(AdminAPIView):
    """POST /amm-software/credenziali/<id>/sblocca/ — toglie il blocco."""

    @extend_schema(
        summary="Sblocca una credenziale",
        description=(
            "Toglie il blocco dell'amministratore (`script.fn_sblocca_credenziale`, "
            "idempotente). Non tocca i tentativi. `Idempotency-Key` obbligatoria."
        ),
        request=None,
        responses={200: _CREDENZIALE},
    )
    # Scopo: Toglie il blocco della credenziale.
    def post(self, request: Request, auth_user_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda _payload: AccessiService().sblocca_credenziale(auth_user_id),
            require_idempotency_key=True,
        )


# ================================================================== #
# Il secondo fattore della credenziale (brief sicurezza §3.4-bis, T-3) #
# ================================================================== #

_STATO_SECONDO_FATTORE = inline_serializer(
    name="AmmSecondoFattoreStatoResp",
    fields={
        "stato": serializers.ChoiceField(choices=STATI_DEVICE),
        "obbligatorio": serializers.BooleanField(),
        "motivo": serializers.CharField(allow_null=True),
        "obbligo_sulla_credenziale": serializers.BooleanField(),
        "codici_recupero_rimasti": serializers.IntegerField(),
    },
)


# Scopo: La credenziale deve esistere: su un id inesistente il DB risponderebbe
#        «nessun obbligo, nessun device», plausibile e sbagliato.
def _credenziale_esistente(auth_user_id: int) -> None:
    AccessiService().get_credenziale(auth_user_id)


class CredenzialeSecondoFattoreView(AdminAPIView):
    @extend_schema(responses={200: _STATO_SECONDO_FATTORE}, summary="Secondo fattore di una credenziale")
    # Scopo: Lo stato del secondo fattore della credenziale.
    def get(self, request: Request, auth_user_id: int) -> JsonResponse:
        _credenziale_esistente(auth_user_id)
        return success_response(SecondoFattoreService().stato_per_admin(auth_user_id))


class CredenzialeSecondoFattoreObbligoView(AdminAPIView):
    @extend_schema(
        request=inline_serializer(name="AmmSecondoFattoreObbligoReq", fields={"valore": serializers.BooleanField()}),
        responses={200: _STATO_SECONDO_FATTORE},
        summary="Secondo fattore: obbligo sulla credenziale",
    )
    # Scopo: Accende o spegne l'obbligo sulla credenziale.
    def post(self, request: Request, auth_user_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            valore = PayloadValidator(validation_code=E_AMM_VALIDAZIONE).require_bool(payload, "valore")
            _credenziale_esistente(auth_user_id)
            return SecondoFattoreService().imposta_obbligo(auth_user_id, valore)

        return handle_post_json(request, handler=_handler)


class CredenzialeSecondoFattoreDisattivaView(AdminAPIView):
    @extend_schema(
        request=inline_serializer(name="AmmSecondoFattoreDisattivaReq", fields={"motivo": serializers.CharField()}),
        responses={200: _STATO_SECONDO_FATTORE},
        summary="Secondo fattore: disattiva il device di una credenziale",
    )
    # Scopo: Cancella il device della credenziale (telefono perso). Il motivo lo
    #        pretende il DB (E_TOTP_MOTIVO_OBBLIGATORIO); la traccia la scrive
    #        il servizio, nella stessa transazione. Disattivare NON chiude le
    #        sessioni aperte (decisione 8, Tid 2026-09-30).
    def post(self, request: Request, auth_user_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            _credenziale_esistente(auth_user_id)
            return SecondoFattoreService().disattiva_da_admin(
                auth_user_id,
                motivo=payload.get("motivo"),
                chi_agisce=utente_autenticato_id(request),
                request=richiesta_django(request),
            )

        return handle_post_json(request, handler=_handler)
