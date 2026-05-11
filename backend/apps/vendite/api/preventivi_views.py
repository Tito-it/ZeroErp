# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views per preventivi vendita (lista, dettaglio, righe, stato, integrazione).
# ------------------------------------------------------------

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import get_scope_user_id, handle_post_json
from apps.core.api.payload_validators import (
    optional_bool,
    optional_int,
    optional_iso_date,
    qp_bool,
    qp_int,
    qp_str,
)
from apps.core.api.success_responses import success_response
from apps.vendite.services import preventivi_service


# ── Lista + Creazione ──


class ApiPreventiviList(DomainAPIView):
    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="stato", type=str, required=False),
            OpenApiParameter(name="billing_account_id", type=int, required=False),
            OpenApiParameter(name="utility_id", type=int, required=False),
            OpenApiParameter(name="data_da", type=str, required=False, description="ISO date"),
            OpenApiParameter(name="data_al", type=str, required=False, description="ISO date"),
            OpenApiParameter(name="search", type=str, required=False),
            OpenApiParameter(
                name="solo_revisione_attiva", type=bool, required=False,
                description="Default true: mostra solo l'ultima revisione per numero. "
                            "Passare false per includere lo storico revisioni superseded.",
            ),
            OpenApiParameter(name="page", type=int, required=False),
            OpenApiParameter(name="page_size", type=int, required=False),
        ],
        responses={200: inline_serializer(
            name="PreventiviListResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Restituisce via GET l'elenco paginato dei preventivi vendita.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        auth_user_id = get_scope_user_id(request)
        data = preventivi_service.list_preventivi(
            stato_codice=qp_str(qp.get("stato")),
            billing_account_id=optional_int({"v": qp.get("billing_account_id")}, "v"),
            utility_id=optional_int({"v": qp.get("utility_id")}, "v"),
            data_da=optional_iso_date({"v": qp.get("data_da")}, "v"),
            data_al=optional_iso_date({"v": qp.get("data_al")}, "v"),
            search=qp_str(qp.get("search")),
            # Default true: lista pulita senza storico revisioni. Il FE
            # passa "false" esplicito col toggle "Mostra storico".
            solo_revisione_attiva=qp_bool(qp.get("solo_revisione_attiva"), default=True),
            auth_user_id=auth_user_id,
            page=qp_int(qp.get("page"), 1),
            page_size=qp_int(qp.get("page_size"), 50),
        )
        return success_response(data)

    @extend_schema(
        request=inline_serializer(
            name="PreventivoCreateRequest",
            fields={
                "utility_id": serializers.IntegerField(),
                "billing_account_id": serializers.IntegerField(required=False, allow_null=True),
                "istanza_utility_id": serializers.IntegerField(required=False, allow_null=True),
                "valuta_id": serializers.IntegerField(required=False, allow_null=True),
                "termine_pagamento_id": serializers.IntegerField(required=False, allow_null=True),
                "validita_dal": serializers.DateField(required=False, allow_null=True),
                "validita_al": serializers.DateField(required=False, allow_null=True),
                "competenza_mese": serializers.DateField(required=False, allow_null=True),
                "fatturazione_immediata": serializers.BooleanField(required=False),
            },
        ),
        responses={200: inline_serializer(
            name="PreventivoCreateResponse",
            fields={
                "data": inline_serializer(name="PreventivoCreateData", fields={
                    "id": serializers.IntegerField(),
                    "uid": serializers.CharField(),
                    "numero": serializers.CharField(),
                }),
            },
        )},
    )
    # Scopo: Crea un nuovo preventivo vendita via POST.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return preventivi_service.crea_preventivo(payload)
        return handle_post_json(request, handler=_handler)


# ── Dettaglio + Aggiornamento ──


class ApiPreventivoDetail(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        responses={200: inline_serializer(
            name="PreventivoDetailResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Restituisce via GET il dettaglio completo di un preventivo.
    def get(self, request: Request, preventivo_id: int) -> JsonResponse:
        data = preventivi_service.get_preventivo(preventivo_id)
        return success_response(data)

    @extend_schema(
        request=inline_serializer(
            name="PreventivoUpdateRequest",
            fields={
                "billing_account_id": serializers.IntegerField(required=False, allow_null=True),
                "validita_dal": serializers.DateField(required=False, allow_null=True),
                "validita_al": serializers.DateField(required=False, allow_null=True),
                "competenza_mese": serializers.DateField(required=False, allow_null=True),
                "fatturazione_immediata": serializers.BooleanField(required=False),
            },
        ),
        responses={200: inline_serializer(
            name="PreventivoUpdateResponse",
            fields={"data": inline_serializer(name="PreventivoUpdateData", fields={
                "status": serializers.CharField(),
                "preventivo_id": serializers.IntegerField(),
            })},
        )},
    )
    # Scopo: Aggiorna un preventivo via PATCH.
    def patch(self, request: Request, preventivo_id: int) -> JsonResponse:
        result = preventivi_service.aggiorna_preventivo(preventivo_id, request.data)
        return success_response(result)

    @extend_schema(
        responses={200: inline_serializer(
            name="PreventivoDeleteResponse",
            fields={"data": inline_serializer(name="PreventivoDeleteData", fields={
                "status": serializers.CharField(),
                "preventivo_id": serializers.IntegerField(),
            })},
        )},
    )
    # Scopo: Hard-delete preventivo BOZZA orfano (zero righe, zero pratiche).
    #        Supporto al pattern "abbandono bozza" del drawer FE.
    #        Per preventivi gia' propagati o con stato avanzato, usare invece
    #        POST /preventivi/<id>/stato/ con nuovo_stato=ANNULLATO.
    def delete(self, request: Request, preventivo_id: int) -> JsonResponse:
        del request
        result = preventivi_service.elimina_preventivo(preventivo_id)
        return success_response(result)


# ── Cambio stato ──


class ApiPreventivoStato(DomainAPIView):
    area_funzionale = "vendite"
    post_permission = "cambia_stato_preventivi"

    @extend_schema(
        request=inline_serializer(
            name="PreventivoStatoRequest",
            fields={
                "nuovo_stato": serializers.CharField(),
                # Obbligatori solo su transizione EMESSO/ACCETTATO → ACCETTATO
                # (modalita' fatturazione del preventivo accettato). Ignorati
                # sulle altre transizioni.
                "fatturazione_immediata": serializers.BooleanField(
                    required=False, allow_null=True,
                ),
                "competenza_mese": serializers.DateField(
                    required=False, allow_null=True,
                ),
            },
        ),
        responses={200: inline_serializer(
            name="PreventivoStatoResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Cambia stato preventivo via POST.
    def post(self, request: Request, preventivo_id: int) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            nuovo_stato = str(payload.get("nuovo_stato", ""))
            # fatturazione_immediata: distinguere "non passato" (None → ignora
            # gate accettazione) da "False esplicito" (richiede competenza).
            # optional_bool(default=False) non distingue: usiamo lookup raw.
            raw_fi = payload.get("fatturazione_immediata")
            if raw_fi is None:
                fatturazione_immediata = None
            else:
                fatturazione_immediata = optional_bool(
                    payload, "fatturazione_immediata",
                )
            competenza_mese = optional_iso_date(payload, "competenza_mese")
            return preventivi_service.cambia_stato(
                preventivo_id, nuovo_stato,
                fatturazione_immediata=fatturazione_immediata,
                competenza_mese=competenza_mese,
                # user serve al hook atomico EMESSO per scope emittente +
                # audit `generato_da_user_id` su documenti_generati.
                user=request.user,
            )
        return handle_post_json(request, handler=_handler)


# ── Revisione ──


class ApiPreventivoRevisione(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        responses={200: inline_serializer(
            name="PreventivoRevisioneResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea nuova revisione preventivo via POST.
    def post(self, request: Request, preventivo_id: int) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return preventivi_service.crea_revisione(preventivo_id)
        return handle_post_json(request, handler=_handler)


# ── Righe: lista + creazione ──


class ApiPreventivoRigheList(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        responses={200: inline_serializer(
            name="PreventivoRigheListResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Restituisce via GET le righe del preventivo.
    def get(self, request: Request, preventivo_id: int) -> JsonResponse:
        data = preventivi_service.list_righe(preventivo_id)
        return success_response(data)

    @extend_schema(
        request=inline_serializer(
            name="PreventivoRigaCreateRequest",
            fields={
                "articolo_id": serializers.CharField(),
                "descrizione": serializers.CharField(required=False, allow_null=True),
                "quantita": serializers.DecimalField(max_digits=22, decimal_places=6, required=False),
                "prezzo_unitario": serializers.DecimalField(max_digits=22, decimal_places=10, required=False),
                "sconto_percentuale": serializers.DecimalField(max_digits=5, decimal_places=2, required=False),
                "iva_id": serializers.IntegerField(required=False, allow_null=True),
                "uom_operativa_id": serializers.IntegerField(required=False, allow_null=True),
                "ordine": serializers.IntegerField(required=False, allow_null=True),
            },
        ),
        responses={200: inline_serializer(
            name="PreventivoRigaCreateResponse",
            fields={"data": inline_serializer(name="PreventivoRigaCreateData", fields={
                "id": serializers.IntegerField(),
            })},
        )},
    )
    # Scopo: Aggiunge riga al preventivo via POST.
    #        Auto-fill prezzo da resolver v5 + check L1 override: vedi
    #        sviluppo-autorizzazioni-prezzi.md §3. auth_user_id e' passato
    #        al service per risolvere emittente + verificare permesso.
    def post(self, request: Request, preventivo_id: int) -> JsonResponse:
        auth_user_id = request.user.id if request.user and request.user.is_authenticated else None
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return preventivi_service.gestisci_riga(
                preventivo_id, payload, auth_user_id=auth_user_id,
            )
        return handle_post_json(request, handler=_handler)


# ── Righe: aggiornamento + eliminazione ──


class ApiPreventivoRigaDetail(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        request=inline_serializer(
            name="PreventivoRigaUpdateRequest",
            fields={
                "quantita": serializers.DecimalField(max_digits=22, decimal_places=6, required=False),
                "prezzo_unitario": serializers.DecimalField(max_digits=22, decimal_places=10, required=False),
                "sconto_percentuale": serializers.DecimalField(max_digits=5, decimal_places=2, required=False),
            },
        ),
        responses={200: inline_serializer(
            name="PreventivoRigaUpdateResponse",
            fields={"data": inline_serializer(name="PreventivoRigaUpdateData", fields={
                "status": serializers.CharField(),
                "riga_id": serializers.IntegerField(),
            })},
        )},
    )
    # Scopo: Aggiorna riga preventivo via PATCH.
    #        Se il payload tocca `prezzo_unitario`, scatta il check L1
    #        (permesso prezzo_override_manuale se diverso dal resolver).
    def patch(self, request: Request, preventivo_id: int, riga_id: int) -> JsonResponse:
        auth_user_id = request.user.id if request.user and request.user.is_authenticated else None
        result = preventivi_service.aggiorna_riga(
            preventivo_id, riga_id, request.data, auth_user_id=auth_user_id,
        )
        return success_response(result)

    @extend_schema(
        responses={200: inline_serializer(
            name="PreventivoRigaDeleteResponse",
            fields={"data": inline_serializer(name="PreventivoRigaDeleteData", fields={
                "status": serializers.CharField(),
                "riga_id": serializers.IntegerField(),
            })},
        )},
    )
    # Scopo: Elimina (soft delete) riga preventivo via DELETE.
    def delete(self, request: Request, preventivo_id: int, riga_id: int) -> JsonResponse:
        result = preventivi_service.elimina_riga(preventivo_id, riga_id)
        return success_response(result)


# ── Componenti BoM CASO A (refactor componenti 2026-05-11) ──
#
# Endpoint nidificati sotto riga padre:
#   GET    /preventivi/<id>/righe/<riga_id>/componenti/
#   PATCH  /preventivi/<id>/righe/<riga_id>/componenti/<componente_id>/
#   DELETE /preventivi/<id>/righe/<riga_id>/componenti/<componente_id>/
# Init e' implicito post-create_riga via `gestisci_riga` — niente POST
# pubblico dedicato. Vedi `refactor-componenti.md`.


class ApiPreventivoRigaComponentiList(DomainAPIView):
    """GET /api/v1/vendite/preventivi/<id>/righe/<riga_id>/componenti/

    Lista i componenti BoM CASO A di una riga padre composita.
    Restituisce array vuoto se la riga non e' CASO A (no componenti).
    """

    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        responses={200: inline_serializer(
            name="PreventivoRigaComponentiListResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Restituisce via GET la lista componenti di una riga padre.
    def get(
        self, request: Request, preventivo_id: int, riga_id: int,
    ) -> JsonResponse:
        result = preventivi_service.list_componenti_riga(preventivo_id, riga_id)
        return success_response(result)


class ApiPreventivoRigaComponenteDetail(DomainAPIView):
    """PATCH/DELETE /api/v1/vendite/preventivi/<id>/righe/<riga_id>/componenti/<componente_id>/

    Modifica fine (prezzo override, ecc.) e soft delete del singolo
    componente. Il trigger DB di ricalcolo aggiorna automaticamente il
    `prezzo_unitario` della riga padre come SUM(componenti × coeff_qta).
    """

    area_funzionale = "vendite"

    @extend_schema(
        request=inline_serializer(
            name="PreventivoRigaComponenteUpdateRequest",
            fields={
                "prezzo_unitario": serializers.DecimalField(
                    max_digits=22, decimal_places=10, required=False,
                ),
                "origine_prezzo": serializers.CharField(required=False),
                "iva_id": serializers.IntegerField(required=False),
                "ordine": serializers.IntegerField(required=False),
            },
        ),
        responses={200: inline_serializer(
            name="PreventivoRigaComponenteUpdateResponse",
            fields={"data": inline_serializer(
                name="PreventivoRigaComponenteUpdateData", fields={
                    "status": serializers.CharField(),
                    "componente_id": serializers.IntegerField(),
                },
            )},
        )},
    )
    # Scopo: Aggiorna componente via PATCH. Solo campi nella whitelist
    #        repo `_COMPONENTE_UPDATE_ALLOWED` sono applicati: gli altri
    #        vengono ignorati silenziosamente (defense-in-depth).
    #        `riga_id` URL passato al service per check anti-tampering
    #        (deve matchare la riga padre reale del componente).
    def patch(
        self,
        request: Request,
        preventivo_id: int,
        riga_id: int,
        componente_id: int,
    ) -> JsonResponse:
        auth_user_id = (
            request.user.id if request.user and request.user.is_authenticated else None
        )
        result = preventivi_service.update_componente(
            preventivo_id, riga_id, componente_id, request.data,
            auth_user_id=auth_user_id,
        )
        return success_response(result)

    @extend_schema(
        responses={200: inline_serializer(
            name="PreventivoRigaComponenteDeleteResponse",
            fields={"data": inline_serializer(
                name="PreventivoRigaComponenteDeleteData", fields={
                    "status": serializers.CharField(),
                    "componente_id": serializers.IntegerField(),
                    "deleted": serializers.BooleanField(),
                },
            )},
        )},
    )
    # Scopo: Soft delete componente via DELETE. `riga_id` URL passato al
    #        service per check anti-tampering (deve matchare la riga padre
    #        reale del componente).
    def delete(
        self,
        request: Request,  # noqa: ARG002 — DRF richiede signature
        preventivo_id: int,
        riga_id: int,
        componente_id: int,
    ) -> JsonResponse:
        result = preventivi_service.delete_componente(
            preventivo_id, riga_id, componente_id,
        )
        return success_response(result)


# ── Suggerimento prezzo riga via pricing resolver v5 ──


class ApiPreventivoRigaSuggerisciPrezzo(DomainAPIView):
    """POST /api/v1/vendite/preventivi/<id>/righe/suggerisci-prezzo/

    Wrappa `preventivi_service.suggerisci_prezzo_riga`. Non modifica nulla:
    legge testata preventivo (BA, utility, data) + articolo + UoM dal
    payload, deriva emittente dal JWT operatore, delega al pricing
    resolver v5. Usato dal FE per pre-compilare il campo prezzo
    all'apertura del drawer riga.

    Area `vendite` livello LETTURA sufficiente (no scrittura).
    Vedi docs/it/dev/work-in-progress/sviluppo-autorizzazioni-prezzi.md.
    """

    area_funzionale = "vendite"

    @extend_schema(
        request=inline_serializer(
            name="PreventivoRigaSuggerisciPrezzoRequest",
            fields={
                "articolo_id": serializers.UUIDField(),
                "uom_id": serializers.IntegerField(),
            },
        ),
        responses={200: inline_serializer(
            name="PreventivoRigaSuggerisciPrezzoResponse",
            fields={"data": inline_serializer(
                name="PreventivoRigaSuggerisciPrezzoData",
                fields={
                    "prezzo_finale": serializers.DecimalField(max_digits=22, decimal_places=10),
                    "prezzo_base_snapshot": serializers.DecimalField(max_digits=22, decimal_places=10, allow_null=True),
                    "origine": serializers.CharField(),
                    "listino_id": serializers.IntegerField(allow_null=True),
                    "contratto_id": serializers.IntegerField(allow_null=True),
                    "promo_id": serializers.IntegerField(allow_null=True),
                    "tipo_variazione_applicata": serializers.CharField(allow_null=True),
                    "valore_variazione_applicata": serializers.DecimalField(max_digits=10, decimal_places=4, allow_null=True),
                },
            )},
        )},
    )
    def post(self, request: Request, preventivo_id: int) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            articolo_id = payload.get("articolo_id")
            uom_id = payload.get("uom_id")
            auth_user_id = request.user.id if request.user and request.user.is_authenticated else None
            return preventivi_service.suggerisci_prezzo_riga(
                preventivo_id,
                articolo_id=str(articolo_id) if articolo_id else None,
                uom_id=int(uom_id) if uom_id is not None else None,
                auth_user_id=auth_user_id,
            )
        return handle_post_json(request, handler=_handler)


# ── Riepilogo IVA aggregato (regola fiscale art. 21 DPR 633/72) ──


class ApiPreventivoRiepilogoIva(DomainAPIView):
    """GET /api/v1/vendite/preventivi/<id>/riepilogo-iva/

    Restituisce il riepilogo IVA del preventivo: una riga per gruppo
    (iva_id, natura, esigibilita, split_payment) con imponibile e imposta
    aggregati e arrotondati a 2 decimali sull'aggregato per aliquota
    (regola fiscale: DPR 633/72 art. 21 + DM 24/12/93). Lettura pura dalla
    view denormalizzata `vendite.vw_preventivi_riepilogo_iva_dettaglio`,
    nessun side-effect: il riepilogo e' mantenuto dal trigger AFTER su
    preventivi_righe via fn_ricalcola_riepilogo_iva_preventivo.

    Area `vendite` livello LETTURA sufficiente.
    """

    area_funzionale = "vendite"

    @extend_schema(
        responses={200: inline_serializer(
            name="PreventivoRiepilogoIvaResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Restituisce via GET il riepilogo IVA aggregato del preventivo.
    def get(self, request: Request, preventivo_id: int) -> JsonResponse:
        data = preventivi_service.list_riepilogo_iva(preventivo_id)
        return success_response(data)


# ── Indirizzi ──


class ApiPreventivoIndirizzi(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        responses={200: inline_serializer(
            name="PreventivoIndirizziListResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Restituisce via GET gli indirizzi del preventivo.
    def get(self, request: Request, preventivo_id: int) -> JsonResponse:
        data = preventivi_service.list_indirizzi(preventivo_id)
        return success_response(data)

    @extend_schema(
        request=inline_serializer(
            name="PreventivoIndirizzoUpsertRequest",
            fields={
                "tipo_indirizzo_id": serializers.IntegerField(),
                "snapshot": serializers.DictField(),
                "origine_indirizzo_id": serializers.IntegerField(required=False, allow_null=True),
                "origine_soggetto_ruolo_id": serializers.IntegerField(required=False, allow_null=True),
            },
        ),
        responses={200: inline_serializer(
            name="PreventivoIndirizzoUpsertResponse",
            fields={"data": inline_serializer(name="PreventivoIndirizzoUpsertData", fields={
                "id": serializers.IntegerField(),
            })},
        )},
    )
    # Scopo: Upsert indirizzo preventivo via POST.
    def post(self, request: Request, preventivo_id: int) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return preventivi_service.upsert_indirizzo(preventivo_id, payload)
        return handle_post_json(request, handler=_handler)


# ── Integrazione: push commessa ──


class ApiPreventivoPushCommessa(DomainAPIView):
    area_funzionale = "vendite"
    post_permission = "push_commessa_preventivi"

    @extend_schema(
        responses={200: inline_serializer(
            name="PreventivoPushCommessaResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Push preventivo in commessa per fatturazione via POST. Ritorna
    # report dell'orchestrator: stato (COMPLETATO/PARZIALE/ERRORE), push_log_id,
    # durata_ms, handlers (dettaglio per handler con counters e errors), e
    # righe_pushable (diagnostico pre-push). Idempotency-Key obbligatoria
    # (write-once: evita doppio push su retry/click multipli).
    def post(self, request: Request, preventivo_id: int) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return preventivi_service.push_a_commessa(preventivo_id)
        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


# ── Integrazione: stato fatturazione ──


class ApiPreventivoStatoFatturazione(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        responses={200: inline_serializer(
            name="PreventivoStatoFatturazioneResponse",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Restituisce via GET lo stato fatturazione del preventivo.
    def get(self, request: Request, preventivo_id: int) -> JsonResponse:
        data = preventivi_service.stato_fatturazione(preventivo_id)
        return success_response(data)


# ── Integrazione: genera pratica ──


class ApiPreventivoGeneraPratica(DomainAPIView):
    area_funzionale = "vendite"
    post_permission = "genera_pratica_preventivi"

    @extend_schema(
        request=inline_serializer(
            name="PreventivoGeneraPraticaRequest",
            fields={
                "tipo_prestazione_id": serializers.IntegerField(),
                "priorita_id": serializers.IntegerField(),
                "descrizione": serializers.CharField(required=False, allow_null=True),
            },
        ),
        responses={200: inline_serializer(
            name="PreventivoGeneraPraticaResponse",
            fields={"data": inline_serializer(name="PreventivoGeneraPraticaData", fields={
                "pratica_id": serializers.IntegerField(),
                "preventivo_id": serializers.IntegerField(),
            })},
        )},
    )
    # Scopo: Genera pratica esecutiva da preventivo via POST.
    def post(self, request: Request, preventivo_id: int) -> JsonResponse:
        def _handler(payload: dict[str, object]) -> dict[str, object]:
            return preventivi_service.genera_pratica(
                preventivo_id,
                tipo_prestazione_id=int(payload["tipo_prestazione_id"]),
                priorita_id=int(payload["priorita_id"]),
                descrizione=payload.get("descrizione"),
            )
        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


# ── Integrazione: pratiche collegate ──


class ApiPreventivoPratiche(DomainAPIView):
    area_funzionale = "vendite"

    @extend_schema(
        responses={200: inline_serializer(
            name="PreventivoPraticheResponse",
            fields={"data": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: Restituisce via GET le pratiche collegate al preventivo.
    def get(self, request: Request, preventivo_id: int) -> JsonResponse:
        data = preventivi_service.list_pratiche(preventivo_id)
        return success_response(data)
