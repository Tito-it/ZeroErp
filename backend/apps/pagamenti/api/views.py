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
    qp_bool_optional,
    qp_int_optional,
    qp_int_strict,
    qp_iso_date_optional,
    qp_str,
    qp_str_upper,
)
from apps.core.api.success_responses import success_response
from apps.pagamenti.services import (
    enti_incasso_service,
    pagamenti_service,
    saldi_service,
    sistemazioni_service,
)

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
    # ✅ Dichiarabile dal 2026-08-27: il codice e' a catalogo (lotto 9, seed di
    # `ui.lista_definizione`). Prima non si poteva, ed e' il verso in cui vale
    # la pena ricordarlo: il cancello di perimetro emittente risolve il codice a
    # catalogo e, non trovandolo, rifiuta la lista a un utente MULTI-emittente —
    # cioe' dichiararlo troppo presto spegneva la schermata invece di prepararla.
    # ⚠️ La lista nasce `multi_emittente = f` (default: non certificata): chi ha
    # piu' di un emittente deve sceglierne uno prima di entrare.
    lista_codice = "pagamenti.distinte"

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


# ══════════════════════════════════════════════════════════════════
#  Abbinamento, code e saldi (slice 3)
# ══════════════════════════════════════════════════════════════════


class ApiRigaAbbina(DomainAPIView):
    """POST /api/v1/pagamenti/righe/<id>/abbina/ — il denaro trova il suo posto."""

    area_funzionale = AREA

    @extend_schema(
        operation_id="pagamenti_riga_abbina",
        request=inline_serializer(
            name="PagamentiRigaAbbina",
            fields={
                "fattura_id": serializers.IntegerField(),
                "billing_account_id": serializers.IntegerField(),
                "scadenza_id": serializers.IntegerField(required=False),
                "forzata": serializers.BooleanField(required=False),
                "motivo_forzatura": serializers.CharField(required=False),
            },
        ),
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Imputa via POST una riga a una fattura, e quando c'e' a una rata.
    # 🔴 Il DOPPIO TEMPO della capienza passa di qui: il primo tentativo arriva
    #    senza `forzata`, il database rifiuta con `E_RIGA_CONTABILE_CAPIENZA_SUPERATA`
    #    (409) e un messaggio che porta gia' i numeri, e la conferma
    #    dell'operatore torna con `forzata = true`. ⚠️ Il frontend riconosce quel
    #    rifiuto dall'`ui_action` `confirm_and_retry`, non da un elenco di
    #    codici cablato.
    def post(self, request: Request, riga_id: int) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return pagamenti_service.abbina_riga(riga_id, dict(payload))

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiRigheCoda(DomainAPIView):
    """GET /api/v1/pagamenti/righe/ — la coda del riconciliatore."""

    area_funzionale = AREA
    is_search_endpoint = True
    # ⭐ Una definizione sola per DUE porte (Q-4 → c): «da abbinare» e «sospese»
    # sono la stessa lista col filtro `coda` gia' impostato, quindi condividono
    # la configurazione di colonne — che e' il motivo per cui il seed e' uno.
    lista_codice = "pagamenti.righe"

    @extend_schema(
        operation_id="pagamenti_righe_coda",
        parameters=[
            OpenApiParameter(
                name="coda", type=str, location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Quale coda: DA_ABBINARE (lavoro non ancora fatto) | "
                    "SOSPESE (lavoro fatto che ha trovato un ostacolo) | TUTTE. "
                    "⭐ Sono due mestieri diversi e due voci di menu, ma la "
                    "stessa lista con il filtro gia' impostato."
                ),
            ),
            OpenApiParameter(
                name="billing_account_id", type=int,
                location=OpenApiParameter.QUERY, required=False,
                description="Filtro cliente.",
            ),
            OpenApiParameter(
                name="data_da", type=str, location=OpenApiParameter.QUERY,
                required=False, description="Data contabile della distinta, da (ISO).",
            ),
            OpenApiParameter(
                name="data_a", type=str, location=OpenApiParameter.QUERY,
                required=False, description="Data contabile della distinta, a (ISO).",
            ),
            OpenApiParameter(
                name="order_by", type=str, location=OpenApiParameter.QUERY,
                required=False,
                description="Whitelist: data_pagamento (default) | importo | stato | distinta.",
            ),
            OpenApiParameter(
                name="order_dir", type=str, location=OpenApiParameter.QUERY,
                required=False, description="asc | desc (default desc).",
            ),
            OpenApiParameter(
                name="page", type=int, location=OpenApiParameter.QUERY, required=False,
                description="Numero pagina (default 1).",
            ),
            OpenApiParameter(
                name="page_size", type=int, location=OpenApiParameter.QUERY,
                required=False, description="Dimensione pagina (default 50, max 200).",
            ),
        ],
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Restituisce via GET le righe da lavorare, di tutte le distinte.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        data = pagamenti_service.list_coda_righe(
            coda=qp_str_upper(qp.get("coda")),
            billing_account_id=qp_int_optional(
                qp.get("billing_account_id"), "billing_account_id"
            ),
            data_da=qp_iso_date_optional(qp.get("data_da"), "data_da"),
            data_a=qp_iso_date_optional(qp.get("data_a"), "data_a"),
            order_by=qp_str(qp.get("order_by")),
            order_dir=qp_str(qp.get("order_dir")),
            page=qp_int_strict(qp.get("page"), "page", 1),
            page_size=qp_int_strict(qp.get("page_size"), "page_size", 50),
        )
        return success_response(data)


class ApiRateFuoriCapienza(DomainAPIView):
    """GET /api/v1/pagamenti/rate/fuori-capienza/ — l'elenco che rende onesta la forzatura."""

    area_funzionale = AREA
    is_search_endpoint = True
    lista_codice = "pagamenti.rate_fuori_capienza"

    @extend_schema(
        operation_id="pagamenti_rate_fuori_capienza",
        parameters=[
            OpenApiParameter(
                name="motivo", type=str, location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "SOVRA_INCASSATA (e' entrato piu' del dovuto) | "
                    "MOVIMENTO_CONTRARIO (un rimborso dove non era entrato "
                    "niente). ⭐ Sono due popolazioni diverse in un elenco solo, "
                    "e il motivo e' la prima colonna da guardare. "
                    "Motivo fuori vocabolario -> 400."
                ),
            ),
            OpenApiParameter(
                name="billing_account_id", type=int,
                location=OpenApiParameter.QUERY, required=False,
                description="Filtro cliente.",
            ),
            OpenApiParameter(
                name="order_by", type=str, location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Whitelist: data_scadenza (default) | motivo | residuo | "
                    "importo_rata | fattura."
                ),
            ),
            OpenApiParameter(
                name="order_dir", type=str, location=OpenApiParameter.QUERY,
                required=False, description="asc | desc (default desc).",
            ),
            OpenApiParameter(
                name="page", type=int, location=OpenApiParameter.QUERY, required=False,
                description="Numero pagina (default 1).",
            ),
            OpenApiParameter(
                name="page_size", type=int, location=OpenApiParameter.QUERY,
                required=False, description="Dimensione pagina (default 50, max 200).",
            ),
        ],
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Restituisce via GET le rate uscite dalla banda di capienza.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        data = pagamenti_service.list_rate_fuori_capienza(
            motivo=qp_str_upper(qp.get("motivo")),
            billing_account_id=qp_int_optional(
                qp.get("billing_account_id"), "billing_account_id"
            ),
            order_by=qp_str(qp.get("order_by")),
            order_dir=qp_str(qp.get("order_dir")),
            page=qp_int_strict(qp.get("page"), "page", 1),
            page_size=qp_int_strict(qp.get("page_size"), "page_size", 50),
        )
        return success_response(data)


class ApiRataSaldo(DomainAPIView):
    """GET /api/v1/pagamenti/rate/<id>/saldo/ — i tre numeri di una rata."""

    area_funzionale = AREA

    @extend_schema(
        operation_id="pagamenti_rata_saldo",
        parameters=[
            OpenApiParameter(
                name="escludi_riga_id", type=int, location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Esclude una riga contabile dal conto: serve a chiedere lo "
                    "spazio PRIMA DI SE', cioe' a sapere se quella riga ci sta "
                    "senza contarsi addosso."
                ),
            ),
        ],
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Restituisce via GET residuo, in lavorazione e incassato di una rata.
    def get(self, request: Request, scadenza_id: int) -> JsonResponse:
        return success_response(
            saldi_service.saldo_rata(
                scadenza_id,
                escludi_riga_id=qp_int_optional(
                    request.query_params.get("escludi_riga_id"), "escludi_riga_id"
                ),
            )
        )


class ApiFatturaSaldo(DomainAPIView):
    """GET /api/v1/pagamenti/fatture/<id>/saldo/ — il saldo di un documento."""

    area_funzionale = AREA
    # ⭐ Lo consuma il drawer FATTURA, che vive in `vendite`: senza questo, per
    #    vedere se una fattura e' pagata servirebbe la LETTURA su `pagamenti` —
    #    cioe' allargare un permesso per comodita'. E' lo stesso pattern del
    #    lookup cross-dominio: risponde il MINIMO su un documento gia' scelto.
    # ⚠️ E sta qui e non in `vendite` per un vincolo, non per gusto: le chiamate
    #    laterali fra moduli di pari livello non sono ammesse (api.md), quindi
    #    `vendite` non puo' chiedere un saldo a `pagamenti`.
    skip_area_check = True

    @extend_schema(
        operation_id="pagamenti_fattura_saldo",
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Restituisce via GET residuo e in lavorazione di una fattura.
    # ⚠️ `incassato` risponde `null`: a questo livello il database non lo sa
    #    ancora dire, e ⛔ non si somma dalle rate (una riga puo' avere fattura
    #    senza rata: il fondo fattura e' cosi').
    def get(self, request: Request, fattura_id: int) -> JsonResponse:
        return success_response(saldi_service.saldo_documento(fattura_id))


class ApiFatturaRateSaldo(DomainAPIView):
    """GET /api/v1/pagamenti/fatture/<id>/rate/ — le rate con il loro saldo."""

    area_funzionale = AREA
    # Stessa ragione del saldo documento: lo consuma il form dell'abbinamento,
    # e risponde il minimo su una fattura gia' scelta.
    skip_area_check = True

    @extend_schema(
        operation_id="pagamenti_fattura_rate",
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Restituisce via GET le rate di una fattura, ciascuna col suo saldo.
    # ⭐ Un giro solo e non uno per rata: il form le mostra tutte insieme, e N
    #    chiamate per disegnare un menu sono N modi di essere lenti.
    def get(self, request: Request, fattura_id: int) -> JsonResponse:
        return success_response(saldi_service.saldi_rate_documento(fattura_id))


# ══════════════════════════════════════════════════════════════════
#  Le sistemazioni — che cosa si fa del denaro di troppo (slice 5)
# ══════════════════════════════════════════════════════════════════


class ApiEccedenze(DomainAPIView):
    """GET /api/v1/pagamenti/eccedenze/ — i documenti che hanno incassato più del dovuto."""

    area_funzionale = AREA
    is_search_endpoint = True
    lista_codice = "pagamenti.eccedenze"

    @extend_schema(
        operation_id="pagamenti_eccedenze",
        parameters=[
            OpenApiParameter(
                name="chi_e_in_credito", type=str, location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "CLIENTE (ha pagato più del dovuto) | AZIENDA (un documento "
                    "a credito su cui è entrato denaro). Valore fuori "
                    "vocabolario -> 400."
                ),
            ),
            OpenApiParameter(
                name="billing_account_id", type=int,
                location=OpenApiParameter.QUERY, required=False,
                description="Filtro cliente.",
            ),
            OpenApiParameter(
                name="order_by", type=str, location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Whitelist: eccedenza_cliente (default) | cliente | "
                    "eccedenza | fattura_data | fattura. ⭐ Il default è per "
                    "CLIENTE, non per documento: la decisione si prende "
                    "guardando il cliente."
                ),
            ),
            OpenApiParameter(
                name="order_dir", type=str, location=OpenApiParameter.QUERY,
                required=False, description="asc | desc (default desc).",
            ),
            OpenApiParameter(
                name="page", type=int, location=OpenApiParameter.QUERY, required=False,
                description="Numero pagina (default 1).",
            ),
            OpenApiParameter(
                name="page_size", type=int, location=OpenApiParameter.QUERY,
                required=False, description="Dimensione pagina (default 50, max 200).",
            ),
        ],
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Restituisce via GET l'elenco delle eccedenze da sistemare.
    # ⭐ La vista porta già il raggruppamento per cliente in finestra
    #    (`eccedenza_cliente`, `documenti_cliente`): il backend non somma niente.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        data = sistemazioni_service.list_eccedenze(
            chi_e_in_credito=qp_str_upper(qp.get("chi_e_in_credito")),
            billing_account_id=qp_int_optional(
                qp.get("billing_account_id"), "billing_account_id"
            ),
            order_by=qp_str(qp.get("order_by")),
            order_dir=qp_str(qp.get("order_dir")),
            page=qp_int_strict(qp.get("page"), "page", 1),
            page_size=qp_int_strict(qp.get("page_size"), "page_size", 50),
        )
        return success_response(data)


class ApiSistemazioni(DomainAPIView):
    """POST /api/v1/pagamenti/sistemazioni/ — registra la decisione."""

    area_funzionale = AREA

    @extend_schema(
        operation_id="pagamenti_sistemazione_create",
        request=inline_serializer(
            name="PagamentiSistemazioneCreate",
            fields={
                "fattura_origine_id": serializers.IntegerField(),
                "destinazione": serializers.CharField(),
                "importo": serializers.DecimalField(max_digits=18, decimal_places=2),
                "fattura_destinazione_id": serializers.IntegerField(required=False),
                "motivo": serializers.CharField(required=False),
                "meta": serializers.DictField(required=False),
            },
        ),
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Registra via POST che cosa si è deciso di fare di un'eccedenza.
    # ⚠️ **Registrare non è eseguire**: l'atto nasce in bozza e il denaro si
    #    muove alla conferma. Fra i due momenti può arrivare un altro incasso —
    #    ed è la ragione per cui il controllo dell'eccedenza sta là.
    # 🔴 Cliente ed emittente NON si passano: li deriva il backend dalla fattura
    #    di origine, perché non sono una scelta di chi compila.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return sistemazioni_service.crea_sistemazione(dict(payload))

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiSistemazioneDetail(DomainAPIView):
    """GET /api/v1/pagamenti/sistemazioni/<id>/ — il dettaglio dell'atto."""

    area_funzionale = AREA

    @extend_schema(
        operation_id="pagamenti_sistemazione_detail",
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Restituisce via GET l'atto, col suo esito quando c'è.
    def get(self, request: Request, sistemazione_id: int) -> JsonResponse:
        return success_response(
            sistemazioni_service.get_sistemazione(sistemazione_id)
        )


class ApiFatturaSistemazioni(DomainAPIView):
    """GET /api/v1/pagamenti/fatture/<id>/sistemazioni/ — gli atti su un documento."""

    area_funzionale = AREA
    # Stessa ragione del saldo: lo consuma il drawer fattura, che vive in
    # `vendite`, e risponde il minimo su un documento già scelto.
    skip_area_check = True

    @extend_schema(
        operation_id="pagamenti_fattura_sistemazioni",
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Restituisce via GET gli atti registrati su una fattura.
    # ⭐ Sono più di uno per natura: si può rimborsare una parte e riportare il
    #    resto.
    def get(self, request: Request, fattura_id: int) -> JsonResponse:
        return success_response(
            sistemazioni_service.list_sistemazioni_fattura(fattura_id)
        )


class ApiSistemazioneConferma(DomainAPIView):
    """POST /api/v1/pagamenti/sistemazioni/<id>/conferma/ — l'atto diventa un fatto."""

    area_funzionale = AREA

    @extend_schema(
        operation_id="pagamenti_sistemazione_conferma",
        request=inline_serializer(
            name="PagamentiSistemazioneConferma",
            fields={"ente_incasso_id": serializers.IntegerField(required=False)},
        ),
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Esegue via POST l'atto: una sola `SELECT` sulla funzione madre, che
    #        sceglie la strada (fondo, distinta negativa, compensazione) e ci
    #        mette sopra il denaro.
    # ⚠️ Il **canale del rimborso** si chiede QUI e non alla registrazione: da
    #    quale conto esce il bonifico è una decisione del momento in cui si paga.
    def post(self, request: Request, sistemazione_id: int) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return sistemazioni_service.conferma_sistemazione(
                sistemazione_id, dict(payload)
            )

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiSistemazioneAnnulla(DomainAPIView):
    """POST /api/v1/pagamenti/sistemazioni/<id>/annulla/ — la decisione si scarta."""

    area_funzionale = AREA

    @extend_schema(
        operation_id="pagamenti_sistemazione_annulla",
        request=inline_serializer(
            name="PagamentiSistemazioneAnnulla",
            fields={"motivo": serializers.CharField(required=False)},
        ),
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Scarta via POST l'atto, lasciandolo a registro con la sua ragione.
    # ⚠️ Il motivo è obbligatorio se l'atto non ne aveva già uno: lo dice il
    #    guard del database, che sa se ce n'era uno — il backend non lo replica.
    def post(self, request: Request, sistemazione_id: int) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return sistemazioni_service.annulla_sistemazione(
                sistemazione_id, dict(payload)
            )

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


# ══════════════════════════════════════════════════════════════════
#  I canali di incasso — da dove arrivano i soldi (slice 4)
# ══════════════════════════════════════════════════════════════════


class ApiEntiIncasso(DomainAPIView):
    """GET/POST /api/v1/pagamenti/enti-incasso/ — i canali di incasso."""

    area_funzionale = AREA
    is_search_endpoint = True

    @extend_schema(
        operation_id="pagamenti_enti_incasso_list",
        parameters=[
            OpenApiParameter(
                name="tipo", type=str, location=OpenApiParameter.QUERY, required=False,
                description="BANCA | POSTE | PSP | ALTRO. Fuori vocabolario -> 400.",
            ),
            OpenApiParameter(
                name="centro_riscossione_id", type=int,
                location=OpenApiParameter.QUERY, required=False,
                description="Filtro centro di riscossione.",
            ),
            OpenApiParameter(
                name="attivo", type=bool, location=OpenApiParameter.QUERY,
                required=False, description="Filtro attivo/disattivo.",
            ),
            OpenApiParameter(
                name="order_by", type=str, location=OpenApiParameter.QUERY,
                required=False,
                description="Whitelist: codice (default) | descrizione | tipo | centro.",
            ),
            OpenApiParameter(
                name="order_dir", type=str, location=OpenApiParameter.QUERY,
                required=False, description="asc (default) | desc.",
            ),
            OpenApiParameter(
                name="page", type=int, location=OpenApiParameter.QUERY, required=False,
                description="Numero pagina (default 1).",
            ),
            OpenApiParameter(
                name="page_size", type=int, location=OpenApiParameter.QUERY,
                required=False, description="Dimensione pagina (default 50, max 200).",
            ),
        ],
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Restituisce via GET l'elenco dei canali di incasso.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        data = enti_incasso_service.list_enti_incasso(
            tipo=qp_str_upper(qp.get("tipo")),
            centro_riscossione_id=qp_int_optional(
                qp.get("centro_riscossione_id"), "centro_riscossione_id"
            ),
            attivo=qp_bool_optional(qp.get("attivo"), "attivo"),
            order_by=qp_str(qp.get("order_by")),
            order_dir=qp_str(qp.get("order_dir")),
            page=qp_int_strict(qp.get("page"), "page", 1),
            page_size=qp_int_strict(qp.get("page_size"), "page_size", 50),
        )
        return success_response(data)

    @extend_schema(
        operation_id="pagamenti_enti_incasso_create",
        request=inline_serializer(
            name="PagamentiEnteIncassoCreate",
            fields={
                "codice": serializers.CharField(),
                "descrizione": serializers.CharField(),
                "tipo": serializers.CharField(),
                "soggetto_ruolo_conto_bancario_id": serializers.IntegerField(),
                "centro_riscossione_id": serializers.IntegerField(required=False),
                "soggetto_ruolo_id": serializers.IntegerField(required=False),
                "bank_branch_id": serializers.IntegerField(required=False),
                "formato_flusso": serializers.CharField(required=False),
                "regole_match": serializers.DictField(required=False),
                "meta": serializers.DictField(required=False),
                "attivo": serializers.BooleanField(required=False),
            },
        ),
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Crea via POST un canale di incasso.
    # 🔴 Il **conto** è obbligatorio su TUTTI i tipi, non solo su BANCA: un
    #    canale senza conto produrrebbe una coda di denaro che nessuno vede — e
    #    il conto è il punto da cui il database ricava di chi sono i soldi.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return enti_incasso_service.crea_ente_incasso(dict(payload))

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiEnteIncassoDetail(DomainAPIView):
    """GET/PATCH /api/v1/pagamenti/enti-incasso/<id>/ — il canale."""

    area_funzionale = AREA

    @extend_schema(
        operation_id="pagamenti_ente_incasso_detail",
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Restituisce via GET il canale, col suo conto in chiaro.
    def get(self, request: Request, ente_incasso_id: int) -> JsonResponse:
        return success_response(
            enti_incasso_service.get_ente_incasso(ente_incasso_id)
        )

    @extend_schema(
        operation_id="pagamenti_ente_incasso_update",
        request=inline_serializer(
            name="PagamentiEnteIncassoPatch",
            fields={
                "codice": serializers.CharField(required=False),
                "descrizione": serializers.CharField(required=False),
                "tipo": serializers.CharField(required=False),
                "attivo": serializers.BooleanField(required=False),
                "centro_riscossione_id": serializers.IntegerField(required=False),
                "soggetto_ruolo_id": serializers.IntegerField(required=False),
                "bank_branch_id": serializers.IntegerField(required=False),
                "soggetto_ruolo_conto_bancario_id": serializers.IntegerField(
                    required=False
                ),
                "formato_flusso": serializers.CharField(required=False),
                "regole_match": serializers.DictField(required=False),
                "meta": serializers.DictField(required=False),
            },
        ),
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Aggiorna via PATCH i campi del canale.
    # ⛔ `codice_interno` non è aggiornabile: è la chiave stabile con cui il
    #    resto del sistema lo nomina.
    def patch(self, request: Request, ente_incasso_id: int) -> JsonResponse:
        return success_response(
            enti_incasso_service.aggiorna_ente_incasso(
                ente_incasso_id, dict(request.data)
            )
        )


class ApiContiIncasso(DomainAPIView):
    """GET /api/v1/pagamenti/conti-incasso/ — i conti agganciabili a un canale."""

    area_funzionale = AREA

    @extend_schema(
        operation_id="pagamenti_conti_incasso",
        parameters=[
            OpenApiParameter(
                name="soggetto_ruolo_id", type=int, location=OpenApiParameter.QUERY,
                required=True,
                description="Il soggetto (ruolo) di cui elencare i conti di incasso.",
            ),
        ],
        responses={200: _RISPOSTA_GENERICA},
    )
    # Scopo: Restituisce via GET i soli conti con `uso = 'INCASSO'` del soggetto.
    # 🔴 **BE-8**: il database rifiuta gli altri con un errore parlante, ma un
    #    elenco che li propone fa sbagliare — e chi sbaglia se ne accorge dopo
    #    aver compilato tutto il resto.
    # ⚠️ Un elenco VUOTO non è un guasto: quel soggetto non ha ancora un conto
    #    di incasso censito **a livello di ruolo**. La risposta lo dice con
    #    `nessun_conto_di_incasso`, perché un menu vuoto senza spiegazione
    #    sembra un errore dell'applicazione.
    def get(self, request: Request) -> JsonResponse:
        soggetto_ruolo_id = qp_int_strict(
            request.query_params.get("soggetto_ruolo_id"), "soggetto_ruolo_id", 0
        )
        return success_response(
            enti_incasso_service.list_conti_incasso(soggetto_ruolo_id)
        )
