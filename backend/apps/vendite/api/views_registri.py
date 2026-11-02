# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API del CRUD dei REGISTRI DI NUMERAZIONE
#        (`vendite.registri_fatturazione`) — lista, dettatglio coi contatori,
#        create/update e il verbo `attivo`.
#        Brief: brief-be-fe-crud-registri-di-numerazione §10, fasi F1 e F2.
# ------------------------------------------------------------
#
# ⛔ LO SCOPE EMITTENTE E' A CARICO DI QUESTE VISTE, e non e' ridondante: su
#    `vendite.registri_fatturazione` **non c'e' la RLS** (riverificato il
#    2026-09-01). Qui non c'e' nessuna difesa sotto: se il filtro non parte da
#    qui, non parte da nessuna parte.
#
# ⚠️ Si usa `get_emittenti_sr_ids` e non `get_emittenti_pk_ids`: la colonna e'
#    `emittente_soggetto_ruolo_id`, cioe' il SOGGETTO-RUOLO e non la PK
#    dell'emittente fiscale (`feedback_emittente_pk_vs_soggetto_ruolo`).
#    Sbagliare famiglia di id non solleva niente: filtra su numeri che non
#    corrispondono e la lista esce vuota, che sembra «non ci sono registri».
#
# ⚠️ AREA `vendite`, MASCHERA IN `amministrazione`. Il dato e' di vendite (la
#    tabella, i vincoli, le due check), ma il tab vive nel drawer
#    dell'emittente fiscale. L'operatore che apre quel drawer deve quindi avere
#    il livello LETTURA su `vendite` per vedere i registri, e GESTIONE per
#    modificarli: e' una domanda di PERMESSI, non un motivo per spostare il
#    dominio dei dati.

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.payload_validators import (
    corpo_oggetto,
    optional_bool,
    optional_int,
    paginated_envelope,
    parse_list_params,
    qp_bool_optional,
    qp_int_optional,
    qp_str_upper,
)
from apps.core.api.success_responses import success_response
from apps.core.services.error_manager import ErrorManager
from apps.core.services.permissions_resolver import PermissionResolver
from apps.vendite.services.registri_service import (
    E_VENDITE_NOT_FOUND,
    E_VENDITE_VALIDATION,
    RegistriService,
)
from apps.core.api.openapi_params import param_ricerca_full

_LISTA_CODICE = "vendite.registri_numerazione"


class ApiRegistriList(DomainAPIView):
    """GET/POST /api/v1/vendite/registri/ — lista e creazione."""

    area_funzionale = "vendite"
    is_search_endpoint = True
    lista_codice = _LISTA_CODICE
    # ⭐ Il tab dentro il drawer apre questa lista con l'emittente GIA' scelto:
    #    e' l'oggetto stesso che l'operatore sta guardando. Senza questa riga il
    #    cancello di perimetro rifiuterebbe (422) chi ha piu' emittenti nello
    #    scope — chiedendogli di scegliere l'emittente che ha gia' aperto — e la
    #    lista a catalogo NON e' certificata multi-emittente (`multi_emittente
    #    = f`), perche' le sue colonne non dicono da quale emittente arriva la
    #    riga. Le due cose sono entrambe vere: e' la richiesta a scioglierle.
    lista_emittente_param = "emittente_soggetto_ruolo_id"

    @extend_schema(
        operation_id="vendite_registri_list",
        parameters=[
            OpenApiParameter(
                name="emittente_soggetto_ruolo_id", type=int,
                location=OpenApiParameter.QUERY, required=False,
                description=(
                    "Restringe a UN emittente (è il caso del tab dentro il "
                    "drawer). ⚠️ Non allarga: si applica DENTRO lo scope "
                    "dell'operatore, mai al suo posto."
                ),
            ),
            OpenApiParameter(
                name="famiglia_documento", type=str,
                location=OpenApiParameter.QUERY, required=False,
                description="FATTURA | DDT | ORDINE | COMMESSA | RESO.",
            ),
            OpenApiParameter(
                name="attivo", type=bool,
                location=OpenApiParameter.QUERY, required=False,
                description=(
                    "Filtro stato. ⛔ Omesso = TUTTI, ed è voluto: un registro "
                    "spento continua a occupare il suo slot (famiglia/emittente/"
                    "utility e prefisso/suffisso), quindi una lista che di "
                    "default nasconde gli spenti nasconde proprio le righe che "
                    "spiegano un rifiuto in creazione."
                ),
            ),
            param_ricerca_full(),
            OpenApiParameter(name="limit", type=int, location=OpenApiParameter.QUERY,
                             required=False),
            OpenApiParameter(name="offset", type=int, location=OpenApiParameter.QUERY,
                             required=False),
            OpenApiParameter(name="order_by", type=str, location=OpenApiParameter.QUERY,
                             required=False,
                             description="Whitelist; fuori whitelist → ordine di default."),
            OpenApiParameter(name="order_dir", type=str, location=OpenApiParameter.QUERY,
                             required=False, description="asc (default) | desc"),
        ],
        responses={200: inline_serializer(
            name="VenditeRegistriListResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista paginata dei registri visibili all'operatore, con in riga i
    #        motivi dei DUE verbi bloccabili (spegnere, cambiare la forma).
    def get(self, request: Request) -> JsonResponse:
        p = parse_list_params(request.query_params, default_order="codice")
        qp = request.query_params
        results, total = RegistriService().list_registri(
            PermissionResolver.get_emittenti_sr_ids(request.user),
            emittente_soggetto_ruolo_id=qp_int_optional(
                qp.get("emittente_soggetto_ruolo_id"), "emittente_soggetto_ruolo_id",
            ),
            famiglia_documento=qp_str_upper(qp.get("famiglia_documento")),
            attivo=qp_bool_optional(qp.get("attivo"), "attivo"),
            search=p["search"],
            limit=p["limit"], offset=p["offset"],
            order_by=p["order_by"], order_dir=p["order_dir"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(
        operation_id="vendite_registri_create",
        request=inline_serializer(name="VenditeRegistroCreateReq", fields={
            "emittente_soggetto_ruolo_id": serializers.IntegerField(),
            "codice": serializers.CharField(),
            "descrizione": serializers.CharField(),
            "famiglia_documento": serializers.CharField(required=False),
            "utility_id": serializers.IntegerField(required=False, allow_null=True),
            "serie_default": serializers.CharField(required=False, allow_null=True),
            "prefisso": serializers.CharField(required=False, allow_null=True),
            "suffisso": serializers.CharField(required=False, allow_null=True),
            "lunghezza_numero": serializers.IntegerField(required=False),
            "politica_data_documento": serializers.CharField(required=False),
            "reset_policy": serializers.CharField(
                required=False,
                help_text=(
                    "ANNUALE (il progressivo riparte a ogni anno) o NESSUNA "
                    "(un contatore solo, che non riparte mai). Omesso: ANNUALE, "
                    "dal default della colonna. Solo in creazione."
                ),
            ),
            "limite_emissione_giorni": serializers.IntegerField(
                required=False, allow_null=True,
                help_text="Solo famiglia FATTURA: il CHECK lo rifiuta altrove.",
            ),
            "limite_emissione_giorno_mese": serializers.IntegerField(
                required=False, allow_null=True,
                help_text="Solo famiglia FATTURA.",
            ),
        }),
        responses={200: inline_serializer(
            name="VenditeRegistroCreateResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea un registro per l'emittente indicato.
    # ⚠️ L'emittente arriva nel payload ma NON è creduto sulla parola: deve
    #    stare nello scope dell'operatore, o la creazione è un modo di scrivere
    #    fuori perimetro su una tabella senza RLS.
    def post(self, request: Request) -> JsonResponse:
        payload = corpo_oggetto(request)
        # ⛔ `optional_int` e NON `qp_int_optional`: il secondo e' per la QUERY
        #    STRING e fa `raw.strip()` sul valore. Un id che arriva come NUMERO
        #    dal corpo JSON — cioe' sempre, dal frontend — gli fa sollevare
        #    `AttributeError`, che diventa un 500 su OGNI creazione. Il difetto
        #    non si vede nei test che passano stringhe: si vede al primo salva.
        emittente_sr_id = optional_int(payload, "emittente_soggetto_ruolo_id")
        payload.pop("emittente_soggetto_ruolo_id", None)
        self._verifica_scope(request, emittente_sr_id)
        assert emittente_sr_id is not None  # `_verifica_scope` rifiuta l'assente
        result = RegistriService().create_registro(emittente_sr_id, payload)
        return success_response(result)

    # Scopo: l'emittente scelto è fra quelli che l'operatore può vedere.
    # ⚠️ `None` dallo scope = nessuna restrizione, e allora passa qualunque
    #    emittente esistente (a rifiutare gli inesistenti c'è la FK).
    def _verifica_scope(self, request: Request, emittente_sr_id: int | None) -> None:
        if not emittente_sr_id:
            ErrorManager.raise_error(
                code=E_VENDITE_VALIDATION,
                message="Emittente fiscale mancante.",
                context={"field": "emittente_soggetto_ruolo_id"},
            )
        ammessi = PermissionResolver.get_emittenti_sr_ids(request.user)
        if ammessi is not None and emittente_sr_id not in ammessi:
            # ⚠️ NOT_FOUND e non FORBIDDEN: distinguere «non esiste» da «non e'
            #    tuo» racconta l'esistenza di un emittente altrui.
            ErrorManager.raise_error(
                code=E_VENDITE_NOT_FOUND,
                message="Emittente fiscale non trovato.",
                context={"emittente_soggetto_ruolo_id": emittente_sr_id},
            )


class ApiRegistroDetail(DomainAPIView):
    """GET/PATCH /api/v1/vendite/registri/<id>/ — dettaglio e modifica."""

    area_funzionale = "vendite"

    @extend_schema(
        operation_id="vendite_registri_detail",
        responses={200: inline_serializer(
            name="VenditeRegistroDetailResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Dettaglio del registro + i suoi CONTATORI in sola lettura.
    # ⛔ I progressivi si leggono e basta: non esiste nessun endpoint che li
    #    scriva, e non ne esiste uno "per l'amministratore". Cambiare
    #    `last_numero` a mano significa riassegnare un numero già uscito.
    def get(self, request: Request, registro_id: int) -> JsonResponse:
        result = RegistriService().get_registro(
            registro_id, PermissionResolver.get_emittenti_sr_ids(request.user),
        )
        return success_response(result)

    @extend_schema(
        operation_id="vendite_registri_update",
        request=inline_serializer(name="VenditeRegistroUpdateReq", fields={
            "codice": serializers.CharField(required=False),
            "descrizione": serializers.CharField(required=False),
            "prefisso": serializers.CharField(required=False, allow_null=True),
            "suffisso": serializers.CharField(required=False, allow_null=True),
            "lunghezza_numero": serializers.IntegerField(required=False),
            "politica_data_documento": serializers.CharField(required=False),
            "limite_emissione_giorni": serializers.IntegerField(
                required=False, allow_null=True),
            "limite_emissione_giorno_mese": serializers.IntegerField(
                required=False, allow_null=True),
        }),
        responses={200: inline_serializer(
            name="VenditeRegistroUpdateResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiorna le colonne ammesse del registro.
    # ⭐ I TRE CAMPI DI FORMA SONO AMMESSI, dal 2026-09-01: a rifiutare è il
    #    guard `trg_registri_fatturazione_a10_guard_forma_numero_upd` sul
    #    registro che ha già consegnato un numero, e il client sa in anticipo
    #    quali righe sono bloccate da `forma_blocco_reason`.
    # ⛔ `serie_default`, `reset_policy`, `famiglia_documento`, `utility_id` e
    #    l'emittente NON sono modificabili, e le ragioni sono TRE, non una: le
    #    prime due non hanno un guard che le presidi; `reset_policy` in più è un
    #    asse della chiave del contatore, quindi cambiarla su un registro che ha
    #    già numerato fa ripartire il progressivo da 1 su un secchio nuovo; le
    #    altre tre sposterebbero il registro di slot — che è una creazione, non
    #    una modifica.
    # ⭐ `reset_policy` si SCEGLIE in creazione dal 2026-09-08: sta nel corpo
    #    della POST, non qui. Vedi `_CAMPI_CREATE` in `registri_repository.py`.
    def patch(self, request: Request, registro_id: int) -> JsonResponse:
        result = RegistriService().update_registro(
            registro_id,
            PermissionResolver.get_emittenti_sr_ids(request.user),
            corpo_oggetto(request),
        )
        return success_response(result)


class ApiRegistroAttivo(DomainAPIView):
    """POST /api/v1/vendite/registri/<id>/attivo/ — accende o spegne."""

    area_funzionale = "vendite"

    @extend_schema(
        operation_id="vendite_registri_set_attivo",
        request=inline_serializer(name="VenditeRegistroAttivoReq", fields={
            "attivo": serializers.BooleanField(),
        }),
        responses={200: inline_serializer(
            name="VenditeRegistroAttivoResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Un verbo suo, non un PATCH generico su `attivo`.
    # ⭐ È il verbo della RIATTIVAZIONE, ed è quello che rende praticabile la
    #    regola del §0: per una terna già occupata da un registro spento non si
    #    crea, si RIACCENDE quello che c'è.
    # ⛔ Lo spegnimento non viene ricontrollato qui: a rifiutare sono i SEI
    #    trigger di disattivazione. La check che la lista legge serve a spegnere
    #    il pulsante e a dire perché, non a decidere al posto del database.
    def post(self, request: Request, registro_id: int) -> JsonResponse:
        payload = corpo_oggetto(request)
        # ⛔ Nessun default silenzioso: un corpo senza `attivo` e' una richiesta
        #    incompleta, non «accendilo». Il verbo ha due direzioni e una delle
        #    due e' distruttiva — indovinare quale, su un payload vuoto, e'
        #    esattamente il genere di scelta che non deve fare il backend.
        if payload.get("attivo") is None:
            ErrorManager.raise_error(
                code=E_VENDITE_VALIDATION,
                message="Il campo `attivo` è obbligatorio.",
                context={"field": "attivo"},
            )
        result = RegistriService().set_attivo(
            registro_id,
            PermissionResolver.get_emittenti_sr_ids(request.user),
            optional_bool(payload, "attivo"),
        )
        return success_response(result)
