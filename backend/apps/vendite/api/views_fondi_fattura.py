# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API read-only dell'elenco «fondi fattura da decidere» — i casi in cui
#        il giro automatico si ferma e la scelta resta a una persona.
# ------------------------------------------------------------

# Un solo endpoint GET sottile sopra `vendite.vw_fondi_fattura_da_decidere`
# (BE-3 di brief-db-fondo-fattura-ricalcolo-e-governo §8.3, vista scritta in
# §8.2-quinquies D-10). Livello LETTURA sufficiente: l'elenco PRESENTA e non
# sana, quindi non e' un'azione di processo.
#
# ⚠️ La vista e' `security_invoker=on`: il perimetro emittente lo applica la RLS
# di `vendite.fatture` con l'identita' della richiesta. Va quindi letta con la
# connessione dell'utente e MAI da un canale di sistema (ruolo BYPASSRLS), o il
# perimetro salta. Il filtro applicativo (`auth_user_id` -> scope SR nel
# repository) resta come defense-in-depth, com'e' la convenzione del progetto.
#
# ⚠️ Nessuna capability per riga: le liste non chiamano `fn_available_actions_*`
# riga per riga. Il gating delle azioni lo fa il FE sui codici che la vista
# porta gia' in riga (`motivo`, e lo stato dell'atto dove esiste).

from django.http import HttpResponse, JsonResponse
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.constants import DEFAULT_LIMIT, MAX_LIMIT
from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import get_scope_user_id, handle_post_json
from apps.core.api.payload_validators import parse_list_params, qp_str, qp_str_upper
from apps.core.api.success_responses import success_response
from apps.ui.api.export_helpers import build_export_response, parse_export_format
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS
from apps.vendite.services.vendite_service import (
    fn_cancella_fondo_fattura,
    fn_fondi_fattura_da_decidere,
)


class ApiFondiFatturaDaDecidere(DomainAPIView):
    """GET /api/v1/vendite/fondi-fattura/da-decidere/ — i casi che chiedono una persona."""

    area_funzionale = "vendite"
    is_search_endpoint = True
    lista_codice = "vendite.fondi_fattura_da_decidere"

    @extend_schema(
        operation_id="vendite_fondi_fattura_da_decidere",
        parameters=[
            OpenApiParameter(
                name="motivo",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Filtro motivo (whitelist chiusa, default: tutti): "
                    "PROPOSTA_SENZA_ATTO = la fattura merita un fondo e non ce "
                    "l'ha | IMPORTO_NON_CORRISPONDENTE = il residuo non "
                    "assomiglia al documento e l'automatismo tace | "
                    "NON_PIU_CAPIENTE = l'atto esiste ma la sorgente non lo "
                    "regge piu' | UTILITY_NON_ATTRIBUIBILE = e' nella banda ma "
                    "senza utility, irraggiungibile da qualunque giro. "
                    "Motivo fuori vocabolario -> 400 (E_VENDITE_VALIDATION)."
                ),
            ),
            OpenApiParameter(
                name="order_by",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Colonna di ordinamento (whitelist): data (default) | "
                    "motivo | anno | numero | totale_a_pagare | "
                    "importo_proposto | capienza_attuale | stato_atto. "
                    "Colonna non ammessa -> 400. "
                    "⚠️ `stato_atto` e' valorizzato sul solo ramo "
                    "NON_PIU_CAPIENTE e NULL sugli altri: ordinarlo separa i "
                    "casi con un atto vivo da quelli senza (i vuoti in coda "
                    "su desc, in testa su asc — regola unica di progetto)."
                ),
            ),
            OpenApiParameter(
                name="order_dir",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Direzione ordinamento: asc | desc (default desc: le "
                    "fatture piu' recenti prima). Valore diverso -> 400."
                ),
            ),
            OpenApiParameter(
                name="limit",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description=f"Righe per pagina (default {DEFAULT_LIMIT}, max {MAX_LIMIT}).",
            ),
            OpenApiParameter(
                name="offset",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Offset paginazione (default 0). `page`/`page_size` sono un 400 (dal 2026-10-20).",
            ),
        ],
        responses={
            200: inline_serializer(
                name="VenditeFondiFatturaDaDecidereResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeFondiFatturaDaDecidereData",
                        fields={
                            "count": serializers.IntegerField(),
                            "page": serializers.IntegerField(),
                            "page_size": serializers.IntegerField(),
                            "total_pages": serializers.IntegerField(),
                            "results": serializers.ListField(child=serializers.DictField()),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce via GET l'elenco paginato dei fondi fattura che
    #        chiedono una decisione, filtrabile per motivo.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        motivo = qp_str_upper(qp.get("motivo"))
        order_by = qp_str(qp.get("order_by"))
        order_dir = qp_str(qp.get("order_dir"))
        # ⛔ `limit`/`offset` dal bundle, come ogni lista (Tid, 2026-10-20, §A4):
        #    `page`/`page_size` sono un 400 (`richiedi_limit_offset`).
        p = parse_list_params(qp, default_order="")

        data = fn_fondi_fattura_da_decidere(
            motivo=motivo,
            # Defense-in-depth sopra la RLS invoker della vista: None per
            # superuser (che la RLS gia' non filtra).
            auth_user_id=get_scope_user_id(request),
            order_by=order_by,
            order_dir=order_dir,
            limit=p["limit"],
            offset=p["offset"],
        )
        return success_response(data)


class ApiFondiFatturaDaDecidereExport(DomainAPIView):
    """GET /api/v1/vendite/fondi-fattura/da-decidere/export/?formato=csv|xlsx

    Esporta la STESSA lista, con gli stessi filtri e lo stesso ordinamento.
    Colonne, ordine e visibilita' vengono dalla configurazione dell'operatore
    sul catalogo `vendite.fondi_fattura_da_decidere` — non da un elenco fisso
    scritto qui: un export che mostra colonne diverse da quelle a video e' un
    secondo elenco da riconciliare a mano.

    ⚠️ Il parametro e' `formato` (italiano) e NON `format`: quest'ultimo e'
    magic per la content-negotiation DRF e intercetterebbe la chiamata prima
    della view.

    ⚠️ Nessun canale di sistema: come il GET di lista, la vista e'
    `security_invoker` e va letta con l'identita' della richiesta.
    """

    area_funzionale = "vendite"
    is_search_endpoint = True
    lista_codice = "vendite.fondi_fattura_da_decidere"

    @extend_schema(
        operation_id="vendite_fondi_fattura_da_decidere_export",
        parameters=[
            OpenApiParameter(
                name="formato", type=str, location=OpenApiParameter.QUERY,
                required=False, description="csv (default) | xlsx",
            ),
            OpenApiParameter(
                name="motivo", type=str, location=OpenApiParameter.QUERY,
                required=False,
                description="Stesso filtro del GET di lista (whitelist chiusa).",
            ),
            OpenApiParameter(
                name="order_by", type=str, location=OpenApiParameter.QUERY,
                required=False, description="Stessa whitelist del GET di lista.",
            ),
            OpenApiParameter(
                name="order_dir", type=str, location=OpenApiParameter.QUERY,
                required=False, description="asc | desc (default desc).",
            ),
        ],
        responses={(200, "text/csv"): bytes},
    )
    # Scopo: Genera il file (CSV/XLSX) dell'elenco «da decidere».
    def get(self, request: Request) -> HttpResponse:
        # Formato PRIMA della query: su formato invalido non si paga il fetch.
        fmt = parse_export_format(request)
        qp = request.query_params
        motivo = qp_str_upper(qp.get("motivo"))
        data = fn_fondi_fattura_da_decidere(
            motivo=motivo,
            auth_user_id=get_scope_user_id(request),
            order_by=qp_str(qp.get("order_by")),
            order_dir=qp_str(qp.get("order_dir")),
            # `max_rows` e non `page_size`: l'export SALTA la paginazione
            # invece di violarne il tetto. Il +1 fa scattare il guard di
            # limite del BB quando il perimetro supera EXPORT_MAX_ROWS,
            # invece di troncare in silenzio.
            max_rows=EXPORT_MAX_ROWS + 1,
        )
        return build_export_response(
            request,
            lista_codice="vendite.fondi_fattura_da_decidere",
            results=data["results"],
            total=data["count"],
            filtri_applicati={"motivo": motivo} if motivo else {},
            fmt=fmt,
        )


# ── Il verbo: cancellare un atto che non è ancora diventato un fatto ──
#
# BE-4 di brief-db-fondo-fattura-ricalcolo-e-governo §9.3, su `D-21`.
#
# ⭐ IL METODO DICE IL VERBO. `api.md` §Grammatica URL vieta di scriverlo nel
# path: la rotta e' la risorsa (`fondi-fattura/<id>/`) e la cancellazione e' il
# `DELETE`. Non esiste un `POST .../cancella/`.
#
# ⛔ Questo endpoint NON serve al riporto sbagliato. Quello si disfa annullando
# la sistemazione che lo ha creato — `POST /pagamenti/sistemazioni/{id}/annulla/`,
# che esiste gia' — e se qualcuno prova a passare di qui il database rifiuta con
# `E_FONDO_TRATTENUTO_DA_SISTEMAZIONE`, che NOMINA quell'alternativa invece di
# dire «non si puo'». Qui si serve l'ALTRA popolazione dell'elenco «da decidere»:
# il fondo `AUTOMATICA` non piu' capiente, che nessuna sistemazione trattiene.
class ApiFondoFatturaDelete(DomainAPIView):
    """DELETE /api/v1/vendite/fondi-fattura/<fondo_source_id>/ — cancella l'atto."""

    area_funzionale = "vendite"
    # ⚠️ Il cancello e' l'azione di processo `governa_fondo_fattura` (D-23,
    # `pericolosa = true`): un gesto che cancella denaro non puo' avere una
    # porta piu' larga di quello che lo ha scritto. ⛔ Seminarla non e'
    # concederla: finche' non e' assegnata a un profilo resta chiusa per tutti
    # tranne il super admin, ed e' voluto.
    post_permission = "governa_fondo_fattura"

    @extend_schema(
        operation_id="vendite_fondo_fattura_delete",
        parameters=[
            OpenApiParameter(
                name="Idempotency-Key",
                type=str,
                location=OpenApiParameter.HEADER,
                required=True,
                description=(
                    "Obbligatoria: il gesto e' irreversibile e un doppio invio "
                    "riceverebbe altrimenti un errore per un'operazione "
                    "riuscita."
                ),
            ),
        ],
        responses={200: inline_serializer(
            name="FondoFatturaDeleteResponse",
            fields={"data": inline_serializer(name="FondoFatturaDeleteData", fields={
                "status": serializers.CharField(),
                "fondo_source_id": serializers.IntegerField(),
                "deleted_righe": serializers.IntegerField(),
                "deleted_fondi": serializers.IntegerField(),
                "deleted_source": serializers.IntegerField(),
            })},
        )},
    )
    # Scopo: Cancella l'atto di fondo indicato, o riporta il motivo del rifiuto.
    # ⚠️ `handle_post_json` e non una chiamata diretta: e' la sede unica del
    # controllo `Idempotency-Key` e del replay in strong mode. Il corpo di un
    # DELETE e' vuoto, e il payload viene ignorato di proposito — quello che
    # serve e' nel path.
    def delete(self, request: Request, fondo_source_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda _payload: fn_cancella_fondo_fattura(
                fondo_source_id=fondo_source_id,
            ),
            require_idempotency_key=True,
        )
