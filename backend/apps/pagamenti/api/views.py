# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API del dominio `pagamenti` — le distinte contabili, le loro righe e
#        la registrazione.
# Note: Grammatica URL di `api.md`: il metodo dice l'operazione, il path la
#       risorsa, e il verbo compare SOLO per le azioni di dominio, come ultimo
#       segmento. ⛔ Niente `/distinte/crea/`.
#
#       ⚠️ La risorsa si chiama `distinte` e non `contabili`: sul filo si usa
#       la parola che l'operatore legge sulla schermata.
# ------------------------------------------------------------

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import (
    qp_int_optional,
    qp_int_strict,
    qp_iso_date_optional,
    qp_str,
    qp_str_upper,
)
from apps.core.api.success_responses import success_response
from apps.pagamenti.services import pagamenti_service

AREA = "pagamenti"

# Risposta generica: il contenuto e' documentato per endpoint nel service, e
# gli schemi di dettaglio arriveranno col consolidamento OpenAPI del dominio.
_RISPOSTA_GENERICA = inline_serializer(
    name="PagamentiRispostaGenerica",
    fields={
        "data": serializers.DictField(),
        "meta": serializers.DictField(required=False),
    },
)


# ══════════════════════════════════════════════════════════════════
#  Distinte
# ══════════════════════════════════════════════════════════════════


class ApiDistinteList(DomainAPIView):
    """GET/POST /api/v1/pagamenti/distinte/ — elenco e apertura."""

    area_funzionale = AREA
    is_search_endpoint = True
    # 📮 `lista_codice = "pagamenti.distinte"` si dichiara INSIEME al seed di
    #    `ui.lista_definizione`, non prima: il cancello di perimetro emittente
    #    risolve il codice a catalogo e, se non lo trova, rifiuta la lista a
    #    un utente multi-emittente. Dichiararlo adesso spegnerebbe la
    #    schermata per chi ha piu' di un emittente.

    @extend_schema(
        operation_id="pagamenti_distinte_list",
        parameters=[
            OpenApiParameter(
                name="stato", type=str, location=OpenApiParameter.QUERY, required=False,
                description=(
                    "Filtro stato (codice interno): BOZZA | IMPORTATA | VALIDATA | "
                    "CHIUSA | ANNULLATA."
                ),
            ),
            OpenApiParameter(
                name="origine", type=str, location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Filtro origine: MANUALE (la digita una persona) | GENERATA "
                    "(la scrive il giro dei fondi fattura) | AUTOMATICA (import). "
                    "⭐ Non e' un dettaglio tecnico: dice a chi guarda se sta "
                    "vedendo il lavoro di qualcuno o la contabilita' interna."
                ),
            ),
            OpenApiParameter(
                name="centro_riscossione_id", type=int,
                location=OpenApiParameter.QUERY, required=False,
                description="Filtro centro di riscossione.",
            ),
            OpenApiParameter(
                name="ente_incasso_id", type=int, location=OpenApiParameter.QUERY,
                required=False, description="Filtro canale di incasso.",
            ),
            OpenApiParameter(
                name="data_da", type=str, location=OpenApiParameter.QUERY,
                required=False,
                description="Data contabile da (ISO). Il floor standard delle liste lo applica il frontend.",
            ),
            OpenApiParameter(
                name="data_a", type=str, location=OpenApiParameter.QUERY,
                required=False, description="Data contabile a (ISO).",
            ),
            OpenApiParameter(
                name="order_by", type=str, location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Whitelist: data_contabile (default) | codice | stato | "
                    "origine | centro | totale_righe."
                ),
            ),
            OpenApiParameter(
                name="order_dir", type=str, location=OpenApiParameter.QUERY,
                required=False, description="asc | desc (default desc).",
            ),
            OpenApiParameter(
                name="page", type=int, location=OpenApiParameter.QUERY,
                required=False, description="Numero pagina (default 1).",
            ),
            OpenApiParameter(
                name="page_size", type=int, location=OpenApiParameter.QUERY,
                required=False, description="Dimensione pagina (default 50, max 200).",
            ),
        ],
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Restituisce via GET l'elenco paginato delle distinte contabili.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        data = pagamenti_service.list_distinte(
            stato=qp_str_upper(qp.get("stato")),
            origine=qp_str_upper(qp.get("origine")),
            centro_riscossione_id=qp_int_optional(
                qp.get("centro_riscossione_id"), "centro_riscossione_id"
            ),
            ente_incasso_id=qp_int_optional(qp.get("ente_incasso_id"), "ente_incasso_id"),
            data_da=qp_iso_date_optional(qp.get("data_da"), "data_da"),
            data_a=qp_iso_date_optional(qp.get("data_a"), "data_a"),
            order_by=qp_str(qp.get("order_by")),
            order_dir=qp_str(qp.get("order_dir")),
            page=qp_int_strict(qp.get("page"), "page", 1),
            page_size=qp_int_strict(qp.get("page_size"), "page_size", 50),
        )
        return success_response(data)

    @extend_schema(
        operation_id="pagamenti_distinte_create",
        request=inline_serializer(
            name="PagamentiDistintaCreate",
            fields={
                "centro_riscossione_id": serializers.IntegerField(),
                "data_contabile": serializers.DateField(),
                "ente_incasso_id": serializers.IntegerField(required=False),
                "importo_dichiarato": serializers.DecimalField(
                    max_digits=18, decimal_places=2, required=False
                ),
                "meta": serializers.DictField(required=False),
            },
        ),
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Apre (o ritrova) via POST la distinta manuale dell'operatore.
    # ⚠️ La risposta porta `gia_popolata`: il *get or create* puo' aver
    #    restituito la distinta di stamattina, e la schermata deve dirlo —
    #    entrarci in silenzio e' il modo in cui si registra due volte credendo
    #    di cominciare.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return pagamenti_service.crea_distinta(dict(payload))

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiDistintaDetail(DomainAPIView):
    """GET/PATCH /api/v1/pagamenti/distinte/<id>/ — dettaglio e compilazione."""

    area_funzionale = AREA

    @extend_schema(
        operation_id="pagamenti_distinta_detail",
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Restituisce via GET testata, totali derivati, righe e i due
    #        cataloghi di stato in un round-trip solo.
    def get(self, request: Request, contabile_id: int) -> JsonResponse:
        return success_response(pagamenti_service.get_distinta(contabile_id))

    @extend_schema(
        operation_id="pagamenti_distinta_update",
        request=inline_serializer(
            name="PagamentiDistintaPatch",
            fields={
                "data_contabile": serializers.DateField(required=False),
                "ente_incasso_id": serializers.IntegerField(required=False),
                "importo_dichiarato": serializers.DecimalField(
                    max_digits=18, decimal_places=2, required=False
                ),
                "meta": serializers.DictField(required=False),
            },
        ),
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Aggiorna via PATCH i campi che una persona compila.
    # ⛔ Lo stato non passa di qui: e' un'azione, e ha il suo endpoint.
    def patch(self, request: Request, contabile_id: int) -> JsonResponse:
        return success_response(
            pagamenti_service.aggiorna_distinta(contabile_id, dict(request.data))
        )


class ApiDistintaStato(DomainAPIView):
    """POST /api/v1/pagamenti/distinte/<id>/stato/ — il percorso della distinta."""

    area_funzionale = AREA

    @extend_schema(
        operation_id="pagamenti_distinta_stato",
        request=inline_serializer(
            name="PagamentiDistintaStato",
            fields={"nuovo_stato": serializers.CharField()},
        ),
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Chiede via POST un cambio di stato sulla testata.
    # ⛔ `CHIUSA` non e' fra i valori ammessi: la chiusura e' una CONSEGUENZA
    #    del registrare, non un gesto a parte.
    def post(self, request: Request, contabile_id: int) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return pagamenti_service.cambia_stato_distinta(contabile_id, dict(payload))

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


# ══════════════════════════════════════════════════════════════════
#  Righe
# ══════════════════════════════════════════════════════════════════


class ApiDistintaRighe(DomainAPIView):
    """GET/POST /api/v1/pagamenti/distinte/<id>/righe/ — le righe della distinta."""

    area_funzionale = AREA

    @extend_schema(
        operation_id="pagamenti_distinta_righe_list",
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Restituisce via GET le righe attive della distinta.
    def get(self, request: Request, contabile_id: int) -> JsonResponse:
        return success_response(pagamenti_service.list_righe(contabile_id))

    @extend_schema(
        operation_id="pagamenti_distinta_righe_create",
        request=inline_serializer(
            name="PagamentiRigaCreate",
            fields={
                "importo": serializers.DecimalField(max_digits=18, decimal_places=2),
                "riferimento_ente": serializers.CharField(required=False),
                "data_pagamento": serializers.DateField(required=False),
                "data_valuta": serializers.DateField(required=False),
                "data_operazione": serializers.DateField(required=False),
                "motivo_sospeso": serializers.CharField(required=False),
                "meta": serializers.DictField(required=False),
            },
        ),
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Aggiunge via POST una riga — un importo arrivato.
    # ⭐ Nasce `DA_ABBINARE`: quando il denaro arriva non si sa ancora di chi
    #    sia, e quello stato dice esattamente questo.
    def post(self, request: Request, contabile_id: int) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return pagamenti_service.crea_riga(contabile_id, dict(payload))

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiRigaDetail(DomainAPIView):
    """PATCH /api/v1/pagamenti/righe/<id>/ — i fatti della riga."""

    area_funzionale = AREA

    @extend_schema(
        operation_id="pagamenti_riga_update",
        request=inline_serializer(
            name="PagamentiRigaPatch",
            fields={
                "importo": serializers.DecimalField(
                    max_digits=18, decimal_places=2, required=False
                ),
                "riferimento_ente": serializers.CharField(required=False),
                "data_pagamento": serializers.DateField(required=False),
                "data_valuta": serializers.DateField(required=False),
                "data_operazione": serializers.DateField(required=False),
                "motivo_sospeso": serializers.CharField(required=False),
                "meta": serializers.DictField(required=False),
            },
        ),
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Aggiorna via PATCH i FATTI di una riga (com'e' arrivato il denaro).
    # ⛔ Non l'abbinamento: quello e' un verbo, perche' porta con se' la rata e
    #    la forzatura, e perche' e' una decisione — non la correzione di un
    #    dato digitato male.
    def patch(self, request: Request, riga_id: int) -> JsonResponse:
        return success_response(
            pagamenti_service.aggiorna_riga(riga_id, dict(request.data))
        )


class ApiRigaStato(DomainAPIView):
    """POST /api/v1/pagamenti/righe/<id>/stato/ — il percorso della riga."""

    area_funzionale = AREA

    @extend_schema(
        operation_id="pagamenti_riga_stato",
        request=inline_serializer(
            name="PagamentiRigaStato",
            fields={
                "nuovo_stato": serializers.CharField(),
                "motivo_sospeso": serializers.CharField(required=False),
            },
        ),
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Chiede via POST un cambio di stato sulla riga.
    # ⚠️ Il motivo viaggia nello stesso giro della sospensione: sospendere
    #    senza dire perche' lascia la riga in una coda dove il prossimo che la
    #    guarda non sa che cosa si era gia' capito.
    def post(self, request: Request, riga_id: int) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return pagamenti_service.cambia_stato_riga(riga_id, dict(payload))

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


# ══════════════════════════════════════════════════════════════════
#  Registrazione
# ══════════════════════════════════════════════════════════════════


class ApiDistintaAnteprimaRegistrazione(DomainAPIView):
    """GET /api/v1/pagamenti/distinte/<id>/anteprima-registrazione/."""

    area_funzionale = AREA

    @extend_schema(
        operation_id="pagamenti_distinta_anteprima_registrazione",
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: La fotografia di che cosa succede se si registra adesso.
    # ⭐ I due numeri di questa risposta (`righe_registrabili`,
    #    `totale_registrabile`) sono quelli da rimandare indietro come
    #    dichiarazione: e' cosi' che il database verifica di registrare
    #    esattamente cio' che l'operatore ha approvato.
    def get(self, request: Request, contabile_id: int) -> JsonResponse:
        return success_response(pagamenti_service.anteprima_registrazione(contabile_id))


class ApiDistintaRegistra(DomainAPIView):
    """POST /api/v1/pagamenti/distinte/<id>/registra/ — il gesto irreversibile."""

    area_funzionale = AREA
    # 🔴 Il cancello sull'unico gesto di questo dominio che non si puo' disfare.
    # ⚠️ L'azione `registra_distinta` va seminata a catalogo e ASSEGNATA a un
    #    profilo: finche' non lo e', `fn_check_azione_processo` risponde
    #    `false` per tutti tranne i super admin — fail-closed, che e' il verso
    #    giusto in cui sbagliare su un gesto irreversibile.
    post_permission = "registra_distinta"

    @extend_schema(
        operation_id="pagamenti_distinta_registra",
        request=inline_serializer(
            name="PagamentiDistintaRegistra",
            fields={
                "righe_attese": serializers.IntegerField(required=False),
                "totale_atteso": serializers.DecimalField(
                    max_digits=18, decimal_places=2, required=False
                ),
            },
        ),
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Registra la distinta — una sola `SELECT` sulla funzione madre.
    # ⛔ L'esito risale INTATTO: `NULLA_DA_POSTARE` non e' un errore, e il
    #    backend non lo trasforma in uno. La frase la sceglie il frontend.
    def post(self, request: Request, contabile_id: int) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return dict(
                pagamenti_service.registra_distinta(contabile_id, dict(payload))
            )

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)
