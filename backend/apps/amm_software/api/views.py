# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views Amm. Software — view sottili, logica nel service.
#        Contratto: docs/it/dev/api.md
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.http import HttpResponse, JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.openapi_params import param_ricerca_full
from apps.amm_software.constants import DEFAULT_LIMIT, MAX_LIMIT

from apps.core.api.base_views import AdminAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.openapi_params import descrizione_order_by
from apps.core.api.payload_validators import (
    corpo_oggetto,
    optional_int,
    optional_uuid,
    paginated_envelope,
    parse_list_params,
    qp_bool_optional,
    qp_int,
    qp_iso_date_optional,
    qp_str,
    qp_str_upper,
)
from apps.core.api.success_responses import success_response
from apps.amm_software.db.amm_software_repository import REPARTI_ORDER_COLUMNS
from apps.amm_software.services.amm_software_service import E_AMM_VALIDAZIONE, AmmSoftwareService
from apps.core.db.dbops_repository import ERROR_LOG_SORT_COLUMNS
from apps.core.services.coda_lavori.scope import scope_operatore_da_request
from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import INTEGER_MAX
from apps.core.services.processi_service import ProcessiService
from apps.core.services.tracciamento_service import fn_list_error_logs
from apps.ui.api.export_helpers import build_export_response, parse_export_format
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS


# Scopo: Decodifica query param a bool opzionale. Valori True: 1|true|yes|on
# (case-insensitive). Valori False: qualsiasi altra stringa non vuota. None
# se il param non e' presente. Usato per filtri di lista.
def _parse_optional_bool(raw: str | None) -> bool | None:
    if raw is None:
        return None
    return raw.lower() in ("1", "true", "yes", "on")


# ================================================================== #
# Operatori                                                            #
# ================================================================== #


class OperatoriListView(AdminAPIView):
    """GET lista, POST crea operatore."""
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="is_super_admin", type=bool, required=False),
            OpenApiParameter(name="unita_organizzativa_id", type=int, required=False),
            OpenApiParameter(name="is_active", type=bool, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(name="OperatoriListResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Lista paginata operatori con filtri.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        is_active = _parse_optional_bool(qp.get("is_active"))
        is_super_admin = _parse_optional_bool(qp.get("is_super_admin"))

        repo = AmmSoftwareService()
        results, total_count = repo.list_operatori(
            search=qp.get("search") or None,
            is_super_admin=is_super_admin,
            unita_organizzativa_id=optional_int({"v": qp.get("unita_organizzativa_id")}, "v"),
            is_active=is_active,
            limit=optional_int({"v": qp.get("limit")}, "v") or DEFAULT_LIMIT,  # clamp nel repository
            offset=optional_int({"v": qp.get("offset")}, "v") or 0,
            order_by=qp.get("order_by") or None,
            order_dir=qp.get("order_dir") or None,
        )
        return success_response({"count": total_count, "results": results})

    @extend_schema(
        summary="Crea operatore (soggetto nuovo o esistente)",
        description=(
            "Due flussi: se soggetto_id presente, associa soggetto esistente "
            "(cognome/nome/CF non richiesti). Se assente, crea soggetto PF nuovo "
            "(cognome/nome/CF obbligatori). La veste operatore nasce spenta: la "
            "accende l'attivazione dell'invito, dove la persona sceglie la "
            "password (`password` non e' ammesso). Se l'email e' gia' di una "
            "credenziale, la si riusa: `credenziale_riusata` e `username` "
            "nella risposta lo dicono. Il riuso vuole il consenso: senza "
            "`riusa_auth_user_id` (o con un altro id) risponde 409 "
            "`E_CREDENZIALE_DA_CONFERMARE`; si rimanda con l'id della "
            "credenziale confermata."
        ),
        request=inline_serializer(name="OperatoriCreateReq", fields={
            "soggetto_id": serializers.CharField(required=False, help_text="UUID soggetto esistente (flusso B). Se assente, crea nuovo (flusso A)."),
            "cognome": serializers.CharField(required=False, help_text="Obbligatorio solo flusso A."),
            "nome": serializers.CharField(required=False, help_text="Obbligatorio solo flusso A."),
            "codice_fiscale": serializers.CharField(required=False, help_text="Obbligatorio solo flusso A."),
            "username": serializers.CharField(),
            "email": serializers.CharField(),
            "qualifica_id": serializers.IntegerField(),
            "is_super_admin": serializers.BooleanField(required=False),
            "unita_organizzativa_id": serializers.IntegerField(required=False),
            "riusa_auth_user_id": serializers.IntegerField(required=False, help_text="Consenso al riuso: l'id della credenziale gia' esistente per l'email, confermato dall'admin."),
        }),
        responses={200: inline_serializer(name="OperatoriCreateResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Crea operatore. Flusso A (soggetto nuovo) o B (soggetto esistente).
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(request, handler=AmmSoftwareService().create_operatore)


class CredenzialePerEmailView(AdminAPIView):
    """GET la credenziale che porta un'email: i dati del dialog di conferma del riuso."""

    @extend_schema(
        summary="Credenziale di un'email (dialog del consenso al riuso)",
        description=(
            "La credenziale che porta l'email, con username e vesti: e' cio' "
            "che il pannello mostra all'admin sul 409 "
            "`E_CREDENZIALE_DA_CONFERMARE` della creazione. Confermato, la "
            "creazione si rimanda con `riusa_auth_user_id` = `auth_user_id` "
            "letto qui. `data.credenziale` e' null se l'email non ha "
            "credenziale (anche assente o vuota). Legge `script.fn_get_credenziale_per_email`, la "
            "stessa lettura del rifiuto."
        ),
        parameters=[OpenApiParameter(
            name="email", type=str, required=False,
            description="L'email del modulo di creazione. Assente o vuota = nessuna credenziale (null, nessun 400).",
        )],
        responses={200: inline_serializer(name="CredenzialePerEmailResp", fields={
            "data": inline_serializer(name="CredenzialePerEmailData", fields={
                "credenziale": serializers.DictField(allow_null=True),
            }),
        })},
    )
    # Scopo: Legge la credenziale di un'email; None se non ne ha.
    def get(self, request: Request) -> JsonResponse:
        email = qp_str(request.query_params.get("email"))
        return success_response(
            {"credenziale": AmmSoftwareService().get_credenziale_per_email(email)}
        )


class OperatoriDetailView(AdminAPIView):
    """GET dettaglio, PATCH aggiorna."""

    @extend_schema(responses={200: inline_serializer(name="OperatoreDetailResp", fields={"data": serializers.DictField()})})
    def get(self, request: Request, auth_user_id: int) -> JsonResponse:
        return success_response(AmmSoftwareService().get_operatore(auth_user_id))

    @extend_schema(
        request=inline_serializer(name="OperatorePatchReq", fields={
            "email": serializers.CharField(required=False),
            "first_name": serializers.CharField(required=False),
            "last_name": serializers.CharField(required=False),
            # Contract Fase 7 multi-face: is_super_admin + attivo
            # sostituiscono il legacy ruolo_sistema (rimosso).
            "is_super_admin": serializers.BooleanField(required=False),
            "attivo": serializers.BooleanField(required=False),
            "unita_organizzativa_id": serializers.IntegerField(required=False),
            # Fine del rapporto: `null` la toglie, assente non la tocca.
            "valido_al": serializers.DateField(required=False, allow_null=True),
        }),
        responses={200: inline_serializer(name="OperatorePatchResp", fields={"data": serializers.DictField()})},
    )
    def patch(self, request: Request, auth_user_id: int) -> JsonResponse:
        result = AmmSoftwareService().update_operatore(auth_user_id, corpo_oggetto(request))
        return success_response(result)


class OperatoriDisabilitaView(AdminAPIView):
    """POST disabilita operatore."""

    @extend_schema(request=None, responses={200: inline_serializer(name="OperatoreDisabilitaResp", fields={"data": serializers.DictField()})})
    def post(self, request: Request, auth_user_id: int) -> JsonResponse:
        return success_response(AmmSoftwareService().disabilita_operatore(auth_user_id))


# ================================================================== #
# Override permessi                                                    #
# ================================================================== #


class OverrideAreeView(AdminAPIView):
    """GET/PUT override aree."""

    @extend_schema(responses={200: inline_serializer(name="OverrideAreeGetResp", fields={"data": serializers.DictField()})})
    def get(self, request: Request, auth_user_id: int) -> JsonResponse:
        return success_response({"results": AmmSoftwareService().get_override_aree(auth_user_id)})

    @extend_schema(
        request=inline_serializer(name="OverrideAreePutReq", fields={"items": serializers.ListField()}),
        responses={200: inline_serializer(name="OverrideAreePutResp", fields={"data": serializers.DictField()})},
    )
    def put(self, request: Request, auth_user_id: int) -> JsonResponse:
        results = AmmSoftwareService().put_override_aree(auth_user_id, corpo_oggetto(request).get("items", []))
        return success_response({"results": results})


class OverrideAzioniView(AdminAPIView):
    """GET/PUT override azioni."""

    @extend_schema(responses={200: inline_serializer(name="OverrideAzioniGetResp", fields={"data": serializers.DictField()})})
    def get(self, request: Request, auth_user_id: int) -> JsonResponse:
        return success_response({"results": AmmSoftwareService().get_override_azioni(auth_user_id)})

    @extend_schema(
        request=inline_serializer(name="OverrideAzioniPutReq", fields={"items": serializers.ListField()}),
        responses={200: inline_serializer(name="OverrideAzioniPutResp", fields={"data": serializers.DictField()})},
    )
    def put(self, request: Request, auth_user_id: int) -> JsonResponse:
        results = AmmSoftwareService().put_override_azioni(auth_user_id, corpo_oggetto(request).get("items", []))
        return success_response({"results": results})


class OverrideOggettiView(AdminAPIView):
    """GET/PUT override oggetti (v2 permessi — livello model)."""

    @extend_schema(responses={200: inline_serializer(name="OverrideOggettiGetResp", fields={"data": serializers.DictField()})})
    # Scopo: Lista override oggetto per un operatore.
    def get(self, request: Request, auth_user_id: int) -> JsonResponse:
        return success_response({"results": AmmSoftwareService().get_override_oggetti(auth_user_id)})

    @extend_schema(
        request=inline_serializer(name="OverrideOggettiPutReq", fields={"items": serializers.ListField()}),
        responses={200: inline_serializer(name="OverrideOggettiPutResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Sostituisce override oggetti di un operatore.
    def put(self, request: Request, auth_user_id: int) -> JsonResponse:
        results = AmmSoftwareService().put_override_oggetti(auth_user_id, corpo_oggetto(request).get("items", []))
        return success_response({"results": results})


class ModelOverridesLookupView(AdminAPIView):
    """GET lookup model registrati per dropdown override oggetti."""

    @extend_schema(responses={200: inline_serializer(name="ModelOverridesLookupResp", fields={"data": serializers.DictField()})})
    # Scopo: Lista model registrati in area_model_overrides.
    def get(self, request: Request) -> JsonResponse:
        return success_response({"results": AmmSoftwareService().list_model_overrides()})


class EmittentiScopeView(AdminAPIView):
    """GET/PUT scope emittenti dichiarativo (Fase 2 multi-face).

    GET: ritorna `{scope_mode, emittenti_ids, emittente_descrizione,
                  allowed_scope_modes, can_change_scope, change_scope_reason}`.
    PUT: payload `{scope_mode: 'GLOBAL'|'SINGLE', emittenti_ids: list[int]}`.
         GLOBAL -> emittenti_ids ignorato; SINGLE -> esattamente 1 elemento.
         Errore strutturato `E_AMM_SCOPE_NON_AMMESSO` (HTTP 400) per shape
         invalido (incluso 'MULTI' ed eventuali futuri scope mode).
    """

    @extend_schema(responses={200: inline_serializer(
        name="EmittentiScopeGetResp",
        fields={"data": inline_serializer(name="EmittentiScopeData", fields={
            "scope_mode": serializers.ChoiceField(choices=["GLOBAL", "SINGLE"]),
            "emittenti_ids": serializers.ListField(child=serializers.IntegerField()),
            "emittente_descrizione": serializers.CharField(allow_null=True),
            "allowed_scope_modes": serializers.ListField(child=serializers.CharField()),
            "can_change_scope": serializers.BooleanField(),
            "change_scope_reason": serializers.CharField(allow_null=True),
        })},
    )})
    def get(self, request: Request, auth_user_id: int) -> JsonResponse:
        return success_response(AmmSoftwareService().get_emittenti_scope(auth_user_id))

    @extend_schema(
        request=inline_serializer(name="EmittentiScopePutReq", fields={
            "scope_mode": serializers.ChoiceField(choices=["GLOBAL", "SINGLE"]),
            "emittenti_ids": serializers.ListField(
                child=serializers.IntegerField(),
                required=False,
                help_text="Vuoto/omesso per GLOBAL; lista di 1 id per SINGLE.",
            ),
        }),
        responses={200: inline_serializer(name="EmittentiScopePutResp", fields={"data": serializers.DictField()})},
    )
    def put(self, request: Request, auth_user_id: int) -> JsonResponse:
        result = AmmSoftwareService().put_emittenti_scope(auth_user_id, corpo_oggetto(request))
        return success_response(result)


# ================================================================== #
# Reparti e profili                                                    #
# ================================================================== #


class RepartiListView(AdminAPIView):
    """GET lista reparti (`amm.reparti`, lista 87): envelope paginato standard.

    ⛔ Nessun `lista_codice`: su `AdminAPIView` il cancello di perimetro non
    c'e', e la lista e' GLOBALE (`config.unita_organizzative`,
    `perimetro_emittente = false`) — l'esenzione sta in
    `test_perimetro_emittente_copertura._ESENZIONI`.
    """

    is_search_endpoint = True

    @extend_schema(
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(
                name="order_by", type=str, required=False,
                description=descrizione_order_by(REPARTI_ORDER_COLUMNS, "Default: descrizione."),
            ),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(name="RepartiListResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Lista paginata dei reparti attivi con profilo e operatori.
    def get(self, request: Request) -> JsonResponse:
        p = parse_list_params(request.query_params, default_order="descrizione")
        results, total = AmmSoftwareService().list_reparti(
            search=p["search"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
            limit=p["limit"],
            offset=p["offset"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))


class PermessiEreditatiView(AdminAPIView):
    """GET livelli EREDITATI dal profilo per un operatore (sola lettura).

    Cosa l'operatore avrebbe **senza** override individuali: e' la colonna
    «ereditato» del pannello permessi, che evita di scrivere un override che
    ripete il profilo — e un override che ripete il profilo congela la riga,
    perche' da quel momento non segue piu' il reparto quando il reparto cambia.

    ⛔ Non e' `reparti/<uo_id>/profilo/`: quello legge il solo binding REPARTO,
    mentre i bindings sono tre (AD_HOC prio 1, REPARTO prio 2, PORTALE di
    veste prio 3) e i resolver prendono il primo per priorita'. Il calcolo sta
    a DB (`script.fn_get_permessi_ereditati_aree` / `..._azioni`), la stessa
    funzione che i resolver chiamano.
    """

    @extend_schema(
        responses={200: inline_serializer(
            name="PermessiEreditatiGetResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Livelli ereditati dal profilo, per area e per azione.
    def get(self, request: Request, auth_user_id: int) -> JsonResponse:
        return success_response(
            AmmSoftwareService().get_permessi_ereditati(auth_user_id)
        )


class PermessiEffettiviOperatoreView(AdminAPIView):
    """GET permessi EFFETTIVI di un operatore su azioni e oggetti (sola lettura).

    Per ogni voce: il valore senza tetto, quello applicato e se il tetto
    d'area lo ferma (`limitata_da_area` / `limitato_da_area`). Serve al
    pannello permessi per dire «abilitata, ma limitata dall'area»: un override
    sotto un'area che non lo consente resta scritto e dormiente
    (brief-db-permessi-tetto-area, D-3), e senza questa lettura il pannello lo
    mostrerebbe come valido.

    ⛔ Non e' `core` `users/<id>/permessi-effettivi/` (riepilogo per area,
    senza azioni ne' tetto). Il calcolo sta a DB
    (`script.fn_get_permessi_effettivi_azioni` / `..._oggetti`), la stessa
    funzione che leggono i resolver.
    """

    @extend_schema(
        responses={200: inline_serializer(
            name="PermessiEffettiviOperatoreGetResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Azioni e oggetti effettivi dell'operatore, col tetto d'area.
    def get(self, request: Request, auth_user_id: int) -> JsonResponse:
        return success_response(
            AmmSoftwareService().get_permessi_effettivi(auth_user_id)
        )


class RepartoProfiloView(AdminAPIView):
    """GET/PUT profilo reparto."""

    @extend_schema(responses={200: inline_serializer(name="RepartoProfiloGetResp", fields={"data": serializers.DictField()})})
    def get(self, request: Request, uo_id: int) -> JsonResponse:
        return success_response(AmmSoftwareService().get_profilo_reparto(uo_id))

    @extend_schema(
        request=inline_serializer(name="RepartoProfiloPutReq", fields={
            "aree": serializers.ListField(), "azioni": serializers.ListField(),
            "richiede_secondo_fattore": serializers.BooleanField(required=False),
        }),
        responses={200: inline_serializer(name="RepartoProfiloPutResp", fields={"data": serializers.DictField()})},
    )
    def put(self, request: Request, uo_id: int) -> JsonResponse:
        corpo = corpo_oggetto(request)
        result = AmmSoftwareService().put_profilo_reparto(
            uo_id, corpo.get("aree", []), corpo.get("azioni", []),
            payload=corpo,
        )
        return success_response(result)


# ================================================================== #
# Riepilogo permessi                                                   #
# ================================================================== #


class ProcessiListView(AdminAPIView):
    """GET registro dei PROCESSI AUTOMATICI (`dbops.processi`).

    ⭐ Prima schermata che rende leggibile da dentro l'applicazione cio' che
    fino al 2026-09-05 si vedeva solo da `psql`: quali programmi girano da
    soli, di che classe sono, con quale identita' e per quali aziende.
    ⛔ `AdminAPIView` e non `DomainAPIView`: le viste di presidio che alimentano
    questa area nominano TUTTI gli emittenti e non hanno RLS.
    """

    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="classe", type=str, required=False),
            OpenApiParameter(name="canale", type=str, required=False),
            OpenApiParameter(name="attivo", type=bool, required=False),
            param_ricerca_full(),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: inline_serializer(
            name="ProcessiListResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Elenco paginato dei processi automatici con filtri di pannello.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        return success_response(ProcessiService().list_processi(
            classe=qp_str_upper(qp.get("classe")),
            canale=qp_str_upper(qp.get("canale")),
            attivo=qp_bool_optional(qp.get("attivo"), "attivo"),
            search=qp_str(qp.get("search")),
            limit=qp_int(qp.get("limit"), DEFAULT_LIMIT),
            offset=qp_int(qp.get("offset"), 0),
            order_by=qp_str(qp.get("order_by")),
            order_dir=qp_str(qp.get("order_dir")),
        ))


class ProcessiPresidiView(AdminAPIView):
    """GET stato dei presidi del cantiere «nessun processo senza operatore».

    ⭐ La natura di ogni presidio — «deve restare vuota» oppure «registro di
    debito che deve calare» — arriva dal COMMENTO della vista a database, non
    da un elenco nel backend: e' il team DB a dichiararla, e a dirla e' una
    sede sola.
    ⭐ E DAL 2026-09-10 NEMMENO QUALI SIANO: le viste sono quelle che il
    catalogo `dbops.presidi` marca di natura `ZERO` (decisione di Tid). Erano
    una tupla di dieci nomi nel backend, e le due gia' non coincidevano —
    cinque `ZERO` a catalogo non le guardava nessuno, e una `LAVORAZIONE` stava
    fra gli allarmi. ⚠️ Una vista `LAVORAZIONE` non e' un allarme: una coda con
    righe e' lavoro in corso, e un pannello che mostra righe verdi insegna a
    leggere il verde come debito.
    ⚠️ QUANTI SIANO non si scrive qui, e non e' pignoleria: fino al 2026-09-07
    questa riga diceva «SEI», e alla stessa data la tupla ne elencava dieci. Un
    numero copiato accanto a un elenco che cresce invecchia in silenzio — la
    sede e' il catalogo, e si legge da li'.
    ⛔ E un presidio che non si e' potuto LEGGERE arriva con il suo `errore` e
    `conteggio` a `null`: non e' «zero righe», ed e' l'unica differenza che
    conta su una schermata dove il verde vuol dire «tutto a posto».
    """

    @extend_schema(
        responses={200: inline_serializer(
            name="ProcessiPresidiResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: I presidi in un round-trip: conteggio, prime righe, descrizione.
    def get(self, request: Request) -> JsonResponse:
        return success_response(ProcessiService().stato_presidi())


class ProcessiPresidiConteggiView(AdminAPIView):
    """GET la SOLA testata dei presidi: quanti, quanti accesi, quanti non letti.

    ⭐ E' il pallino della topbar (decisione #8 di Tid, 2026-09-18 —
    piano-be-fe-osservabilita-pallino-e-superfici §2.2): lo stesso giro del
    pannello senza le prime righe, letto ogni cinque minuti da ogni scheda
    aperta. Per questo esiste un endpoint a parte e non un parametro su
    `presidi/`: un contatore ambientale non deve pagare le righe di esempio.
    ⛔ Stessa porta del pannello (`AdminAPIView`): le viste nominano tutte le
    aziende. Chi non la passa riceve 403 e il pallino NON compare — come il
    badge delle code per chi non ha l'area core.
    ⚠️ Un presidio che non si legge non e' un errore di questa risposta: e'
    `non_letti`, e il pallino lo mostra come «chiede un occhio».
    """

    @extend_schema(
        responses={200: inline_serializer(
            name="ProcessiPresidiConteggiResp",
            fields={"data": inline_serializer(
                name="ProcessiPresidiConteggiData",
                fields={
                    "totale": serializers.IntegerField(),
                    "con_righe": serializers.IntegerField(),
                    "non_letti": serializers.IntegerField(),
                },
            )},
        )},
    )
    # Scopo: I tre numeri della testata, senza righe.
    def get(self, request: Request) -> JsonResponse:
        return success_response(ProcessiService().conteggi_presidi())


class ProcessiDetailView(AdminAPIView):
    """GET dettaglio di un processo: bersagli dichiarati e identita' tecniche."""

    @extend_schema(
        responses={200: inline_serializer(
            name="ProcessiDetailResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Dettaglio completo del processo (404 se il codice non esiste).
    def get(self, request: Request, codice: str) -> JsonResponse:
        return success_response(ProcessiService().get_processo(codice))


class ProcessiRunView(AdminAPIView):
    """GET le corse recenti di un processo (`maintenance.job_run_log`)."""

    @extend_schema(
        parameters=[
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
        ],
        responses={200: inline_serializer(
            name="ProcessiRunResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Storia recente delle corse di un processo.
    def get(self, request: Request, codice: str) -> JsonResponse:
        qp = request.query_params
        return success_response(ProcessiService().list_run(
            codice,
            limit=qp_int(qp.get("limit"), DEFAULT_LIMIT),
            offset=qp_int(qp.get("offset"), 0),
        ))


# Scopo: il pezzo comune ai due verbi sull'utente tecnico (crea / riattiva):
#        stesso header obbligatorio, stesso corpo, stessa traduzione del
#        payload. I due endpoint restano SEPARATI — sono due intenzioni — ma
#        cio' che hanno in comune sta scritto una volta.
# ⚠️ `_IDEMPOTENCY_HEADER_PARAM` esiste identico in `core/api/views_tracciamento.py`:
#    e' la seconda copia. Portarla in `core/api` e' un'estrazione di building
#    block, e si fa quando Tid dice di si', non di passaggio.
_IDEMPOTENCY_HEADER_PARAM = OpenApiParameter(
    name="Idempotency-Key", type=str,
    location=OpenApiParameter.HEADER, required=True,
    description="Chiave idempotenza obbligatoria per endpoint write.",
)
_IDENTITA_REQ_FIELDS: dict[str, serializers.Field] = {"emittente_codice": serializers.CharField()}


def _post_verbo_identita(request: Request, codice: str, verbo) -> JsonResponse:
    def _handler(payload: dict[str, Any]) -> dict[str, Any]:
        return verbo(codice, emittente_codice=str(payload.get("emittente_codice") or ""))

    return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ProcessiIdentitaView(AdminAPIView):
    """POST crea l'utente tecnico di un processo PER UN EMITTENTE.

    ⛔ D-9: il sistema non SCEGLIE l'emittente, lo riceve da una persona. Non
    esiste un verbo «crea tutti quelli che mancano»: il pannello mostra chi non
    e' servito, la decisione resta di chi guarda.
    """

    @extend_schema(
        parameters=[_IDEMPOTENCY_HEADER_PARAM],
        request=inline_serializer(name="ProcessiIdentitaReq", fields=_IDENTITA_REQ_FIELDS),
        responses={200: inline_serializer(
            name="ProcessiIdentitaResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea l'utente tecnico (processo x emittente) via fabbrica di dominio.
    def post(self, request: Request, codice: str) -> JsonResponse:
        return _post_verbo_identita(request, codice, ProcessiService().crea_utente_tecnico)


class ProcessiIdentitaRiattivaView(AdminAPIView):
    """POST riaccende l'utente tecnico SPENTO di un processo per un emittente.

    ⭐ Endpoint SEPARATO dalla creazione, e non un flag su quello: sono due
    intenzioni diverse davanti a due stati del mondo diversi — «non c'e'» e
    «c'e' ed e' spento». Un `POST … /identita/` che a volte crea e a volte
    riaccende sarebbe un verbo che decide da solo quale, e chi lo chiama non
    saprebbe piu' quale dei due e' avvenuto.
    ⚠️ Ci si arriva da un rifiuto parlante: `fn_crea_utente_tecnico` risponde
    `E_UTENTE_TECNICO_DA_RIATTIVARE` e manda qui.
    """

    @extend_schema(
        parameters=[_IDEMPOTENCY_HEADER_PARAM],
        request=inline_serializer(name="ProcessiIdentitaRiattivaReq", fields=_IDENTITA_REQ_FIELDS),
        responses={200: inline_serializer(
            name="ProcessiIdentitaRiattivaResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Riattiva l'utente tecnico (processo x emittente) via fabbrica.
    def post(self, request: Request, codice: str) -> JsonResponse:
        return _post_verbo_identita(request, codice, ProcessiService().riattiva_utente_tecnico)


class ProcessiEseguiOraView(AdminAPIView):
    """POST «Esegui ora» su una SVEGLIA di deploy di un processo.

    Il web non esegue niente: ACCODA un lavoro `ESEGUI_PROCESSO` su
    `dbops.coda_lavori` con lo scope di chi preme (`run_as = OPERATORE`), e il
    drenatore lancia `run-command.sh <comando>` — la stessa riga del timer,
    meno l'orario — alla corsa successiva. Risposta: l'handle del lavoro
    (`job_id`, `stato`, `unit`), la stessa forma del giro di fatturazione.
    Il corpo porta la sola `unit`: il comando si risolve dal dichiarato di
    deploy (`sveglie.json`), che e' la whitelist — mai dal client.

    ⚠️ LA SEDE DELLA FIDUCIA E' `AdminAPIView` (decisione 1 di brief §8.5: v1
    solo `SUPER_ADMIN`). L'azione `processo_avvia` esiste a catalogo
    (`config.azioni_processo`, id 35) ma NON e' dichiarata qui come
    `post_permission`: `AdminAPIView` non la leggerebbe, e un attributo che
    sembra un cancello e non lo e' sarebbe peggio di nessun attributo. Il
    giorno in cui il verbo si aprira' agli operatori, la view cambia base e
    quell'azione diventa il permesso — con la stessa riga di catalogo.
    """

    @extend_schema(
        parameters=[_IDEMPOTENCY_HEADER_PARAM],
        request=inline_serializer(
            name="ProcessiEseguiOraReq", fields={"unit": serializers.CharField()},
        ),
        responses={200: inline_serializer(
            name="ProcessiEseguiOraResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Accoda «Esegui ora» sulla sveglia indicata, con lo scope di chi
    #        preme catturato dalla richiesta (terna rifiutata PRIMA di accodare).
    def post(self, request: Request, codice: str) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            # Lo scope si cattura QUI, dalla richiesta, con il BB della coda:
            # e' cio' con cui il drenatore ripropone l'identita' di chi ha
            # premuto, minuti dopo e senza token. Senza `identita_id` il BB
            # rifiuta con `E_CODA_SCOPE_OPERATORE_INVALIDO` — 400 adesso, a chi
            # puo' fare qualcosa, invece di un lavoro che muore nel drenatore.
            scope = scope_operatore_da_request(request)
            return ProcessiService().esegui_ora(
                codice, unit=payload.get("unit"), scope=scope,
            )

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ProcessiAccensioneView(AdminAPIView):
    """POST la scelta a mano sull'ACCENSIONE di un processo, su questa
    installazione: `{"acceso": true|false|null, "motivo": "..."}`. `true`
    accende, `false` spegne, `null` toglie la scelta e torna il default per
    ambiente del catalogo. Risposta: l'accensione rinfrescata, nella forma di
    `accensione` del dettaglio.

    I limiti (processo non spegnibile, senza sveglia, motivo) li dice il guard
    di `dbops.processi_accensione`; il service li traduce
    (brief-db-processi-accensione-per-ambiente §6.0 punto 5).
    ⚠️ La sede della fiducia e' `AdminAPIView`, come per «Esegui ora» («il
    permesso e' vostro, come per Esegui ora», dal brief DB): v1 solo
    SUPER_ADMIN.
    """

    @extend_schema(
        parameters=[_IDEMPOTENCY_HEADER_PARAM],
        request=inline_serializer(
            name="ProcessiAccensioneReq",
            fields={
                "acceso": serializers.BooleanField(allow_null=True),
                "motivo": serializers.CharField(),
            },
        ),
        responses={200: inline_serializer(
            name="ProcessiAccensioneResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Accende, spegne o riporta al default il processo, col motivo.
    def post(self, request: Request, codice: str) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return ProcessiService().imposta_accensione(
                codice, payload, attore=request.user.get_username(),
            )

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class AuditLogView(AdminAPIView):
    """GET audit log globale modifiche permessi."""

    @extend_schema(
        parameters=[
            OpenApiParameter(name="data_da", type=str, required=False),
            OpenApiParameter(name="data_a", type=str, required=False),
            OpenApiParameter(name="tabella", type=str, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
        ],
        responses={200: inline_serializer(name="AuditLogResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Timeline globale eventi audit permessi.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        events, total_count = AmmSoftwareService().list_audit_log(
            data_da=qp_iso_date_optional(qp.get("data_da"), "data_da"),
            data_a=qp_iso_date_optional(qp.get("data_a"), "data_a"),
            tabella=qp.get("tabella") or None,
            order_by=qp.get("order_by") or None,
            order_dir=qp.get("order_dir") or None,
            limit=optional_int({"v": qp.get("limit")}, "v") or DEFAULT_LIMIT,  # clamp nel repository
            offset=optional_int({"v": qp.get("offset")}, "v") or 0,
        )
        return success_response({"count": total_count, "results": events})


# I filtri della consultazione di `dbops.error_log`, dichiarati UNA volta per
# la lista e per il suo export (stessa whitelist, stesso file).
_PARAMS_FILTRI_ERROR_LOG = [
    OpenApiParameter(name="area", type=str, required=False,
                     description="Area funzionale, esatta (catalogo `config.aree_funzionali`)."),
    OpenApiParameter(name="function_name", type=str, required=False,
                     description="PREFISSO del nome funzione (`LIKE 'x%'`, `_` letterale, "
                                 "case-sensitive: i nomi sono minuscoli per convenzione)."),
    OpenApiParameter(name="codice", type=str, required=False,
                     description="Codice errore esatto (`config.codici_errore`)."),
    OpenApiParameter(name="tx_id", type=str, required=False,
                     description="UUID di transazione esatto: il ponte dal giornale di dominio."),
    OpenApiParameter(name="data_da", type=str, required=False, description="Data inizio (YYYY-MM-DD)."),
    OpenApiParameter(name="data_a", type=str, required=False, description="Data fine inclusa (YYYY-MM-DD)."),
    OpenApiParameter(
        name="order_by", type=str, required=False,
        description=descrizione_order_by(
            ERROR_LOG_SORT_COLUMNS,
            "Default `occurred_at DESC`; le frasi (`messaggio`, `causa`, `soluzione`) e "
            "`context` non ordinano.",
        ),
    ),
    OpenApiParameter(name="order_dir", type=str, required=False, description="asc | desc."),
]


# Scopo: i filtri della consultazione di `error_log`, letti dalla query string
#        e NORMALIZZATI: date ISO strict (400 se malformate), `tx_id` uuid
#        (400 se non lo e' — un `%s::uuid` su una stringa qualunque sarebbe
#        un 500), testi strip. Una sede per la lista e per l'export.
def _filtri_error_log(qp) -> dict[str, Any]:
    tx_id = optional_uuid({"tx_id": qp_str(qp.get("tx_id"))}, "tx_id")
    data_da = qp_iso_date_optional(qp.get("data_da"), "data_da")
    data_a = qp_iso_date_optional(qp.get("data_a"), "data_a")
    return {
        "area": qp_str(qp.get("area")),
        "function_name": qp_str(qp.get("function_name")),
        "codice": qp_str_upper(qp.get("codice")),
        "tx_id": str(tx_id) if tx_id is not None else None,
        "data_da": data_da.isoformat() if data_da else None,
        "data_a": data_a.isoformat() if data_a else None,
    }


# Il codice di lista della consultazione (`ui.lista_definizione`): lo legge il
# solo EXPORT, per risolvere le colonne che l'operatore vede.
# ⛔ NON e' un attributo `lista_codice` sulle view, ed e' una scelta: quello e'
#    il cancello di perimetro emittente di `DomainAPIView`, che su
#    `AdminAPIView` NON esiste — dichiararlo direbbe al presidio
#    `test_perimetro_emittente_copertura` «lista coperta» su un cancello
#    inerte. La lista `dbops.error_log` e' ESENTE (un errore tecnico non ha
#    un'azienda da cui arrivare) e l'esenzione e' scritta la', con la ragione.
#    Stessa forma di `_LISTA_CODICE` dell'export delle famiglie documento
#    (`vendite/api/views_famiglie.py`), l'altro export su `AdminAPIView`.
_LISTA_CODICE_ERROR_LOG = "dbops.error_log"


class ErrorLogListView(AdminAPIView):
    """GET /api/v1/amm-software/error-log/ — la consultazione di `dbops.error_log`."""

    # ⭐ `AdminAPIView` (vincolo del Passo A dell'osservabilita', D-E1): oggi il
    #    permesso dei tecnici e' questo, come per `audit-log/` ed `email-log/`.
    #    Il giorno che nascera' un livello «tecnici», si sposta con quelli.
    # ⛔ Nessun `lista_codice`: vedi `_LISTA_CODICE_ERROR_LOG` qui sopra.
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            *_PARAMS_FILTRI_ERROR_LOG,
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
        ],
        responses={200: inline_serializer(name="ErrorLogListResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Restituisce via GET l'elenco paginato degli errori tecnici col
    #        catalogo dei messaggi (codice, classe, frase, causa, soluzione) e
    #        il `context` com'e'.
    # ⭐ `order_dir` assente = `None`: decide il ripiego DESC della data.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(
            qp, default_order="occurred_at",
            default_limit=DEFAULT_LIMIT, max_limit=MAX_LIMIT,
        )
        return success_response(fn_list_error_logs(
            **_filtri_error_log(qp),
            limit=p["limit"],
            offset=p["offset"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
        ))


class ErrorLogExportView(AdminAPIView):
    """GET /api/v1/amm-software/error-log/export/ — CSV/XLSX della consultazione."""

    # ⭐ Il codice di lista e' UNO, `_LISTA_CODICE_ERROR_LOG`: le colonne del
    #    file sono quelle che l'operatore VEDE (preferenza + preset + permessi).
    #    ⚠️ Su `AdminAPIView` la coppia lista/export non ha un `lista_codice`
    #    da cui il presidio `test_export_lista_codice_pari` possa leggerla: e'
    #    fuori dal suo perimetro per costruzione, come `famiglie/`, ed e' la
    #    ragione della costante unica — non c'e' un secondo letterale da
    #    tenere allineato.

    @extend_schema(
        parameters=[
            OpenApiParameter(name="formato", type=str, required=True, description="csv | xlsx."),
            *_PARAMS_FILTRI_ERROR_LOG,
        ],
        responses={
            (200, "text/csv"): bytes,
            (200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): bytes,
        },
    )
    # Scopo: Il file della consultazione, con gli stessi filtri della lista.
    # ⚠️ `limit=EXPORT_MAX_ROWS + 1`: l'export esporta il DATASET, non la
    #    pagina, e il `+1` fa scattare il guard di `build_export_response`
    #    PRIMA di serializzare, invece di consegnare un file troncato.
    # ⚠️ `?formato=`, non `?format=` (parametro magico di DRF).
    def get(self, request: Request) -> HttpResponse:
        fmt = parse_export_format(request)
        qp = request.query_params
        filtri = _filtri_error_log(qp)
        dati = fn_list_error_logs(
            **filtri,
            limit=EXPORT_MAX_ROWS + 1,
            offset=0,
            order_by=qp_str(qp.get("order_by")),
            order_dir=qp_str(qp.get("order_dir")),
        )
        return build_export_response(
            request,
            lista_codice=_LISTA_CODICE_ERROR_LOG,
            results=dati["results"],
            total=dati["count"],
            filtri_applicati={k: v for k, v in filtri.items() if v is not None} or None,
            fmt=fmt,
        )


class PermessiRiepilogoView(AdminAPIView):
    """GET riepilogo permessi per area degli operatori indicati."""

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="auth_user_ids", type=str, required=True,
                description="Id degli operatori, separati da virgola (le righe di una pagina della lista).",
            ),
        ],
        responses={200: inline_serializer(name="PermessiRiepilogoResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Le chip della lista operatori con i permessi aperti: una riga per
    #        (operatore, area attiva) con livello effettivo, override scritti e
    #        voci fermate dal tetto (brief riepilogo-permessi, 2026-10-06).
    # ⚠️ Gli id sono quelli della PAGINA: la lista e' la sorgente degli
    #    operatori, filtri compresi. Fino al 2026-10-06 questo endpoint aveva
    #    filtri suoi e restituiva tutti gli operatori.
    def get(self, request: Request) -> JsonResponse:
        ids = _parse_auth_user_ids(request.query_params.get("auth_user_ids"))
        return success_response({"results": AmmSoftwareService().get_permessi_riepilogo(ids)})


# Scopo: `?auth_user_ids=1,2,3` → `[1, 2, 3]`, senza duplicati e nell'ordine dato.
#        Un pezzo che non e' un intero positivo e' un 400, non un id ignorato:
#        la pagina chiede righe precise, e una che manca in silenzio sarebbe
#        un operatore senza chip. Nessun id e' un 400 (il parametro e'
#        obbligatorio): una chiamata senza operatori e' un chiamante rotto.
# ⚠️ Il pezzo lo legge `optional_int` (cifre ASCII); qui si aggiunge il tetto
#    di un `integer` PG (`auth_user.id`, argomento `integer[]` della funzione,
#    `INTEGER_MAX` di payload_helpers): oltre, il cast fallirebbe a DB — un 500
#    al posto di un 400.


def _parse_auth_user_ids(raw: str | None) -> list[int]:
    ids: list[int] = []
    for pezzo in (raw or "").split(","):
        if not pezzo.strip():
            continue
        try:
            valore = optional_int({"v": pezzo}, "v")
        except ValueError:
            valore = None
        ErrorManager.require(
            valore is not None and 0 < valore <= INTEGER_MAX,
            code=E_AMM_VALIDAZIONE,
            message="auth_user_ids: attesi id interi positivi separati da virgola.",
            context={"field": "auth_user_ids"},
        )
        assert valore is not None
        if valore not in ids:
            ids.append(valore)
    ErrorManager.require(
        bool(ids),
        code=E_AMM_VALIDAZIONE,
        message="auth_user_ids: obbligatorio, almeno un id.",
        context={"field": "auth_user_ids"},
    )
    return ids


# ================================================================== #
# Lookup                                                               #
# ================================================================== #


class UtentiUOListView(AdminAPIView):
    """GET lista UO per dropdown."""
    @extend_schema(responses={200: inline_serializer(name="UOListResp", fields={"data": serializers.DictField()})})
    def get(self, request: Request) -> JsonResponse:
        return success_response({"results": AmmSoftwareService().list_unita_organizzative()})


class LookupAreeView(AdminAPIView):
    """GET aree funzionali."""
    @extend_schema(responses={200: inline_serializer(name="LookupAreeResp", fields={"data": serializers.DictField()})})
    def get(self, request: Request) -> JsonResponse:
        return success_response({"results": AmmSoftwareService().list_aree_funzionali()})


class LookupAzioniView(AdminAPIView):
    """GET azioni processo."""
    @extend_schema(responses={200: inline_serializer(name="LookupAzioniResp", fields={"data": serializers.DictField()})})
    def get(self, request: Request) -> JsonResponse:
        return success_response({"results": AmmSoftwareService().list_azioni_processo()})


class LookupEmittentiView(AdminAPIView):
    """GET emittenti fiscali."""
    @extend_schema(responses={200: inline_serializer(name="LookupEmittentiResp", fields={"data": serializers.DictField()})})
    def get(self, request: Request) -> JsonResponse:
        return success_response({"results": AmmSoftwareService().list_emittenti_fiscali()})



# ================================================================== #
# Setup status (refactor operatore-emittenti)                          #
# ================================================================== #


class SetupStatusView(AdminAPIView):
    """GET stato setup refactor operatore-emittenti.

    Conta emittenti attivi, operatori totali/assegnati/admin globali/non
    assegnati. Usato dal banner UI "operatori non assegnati" che avvisa
    l'admin durante la transizione (decisione D1 del WIP).
    """

    @extend_schema(
        responses={200: inline_serializer(
            name="SetupStatusResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Restituisce i 5 contatori di setup status.
    def get(self, request: Request) -> JsonResponse:
        del request
        return success_response(AmmSoftwareService().get_setup_status())


# ================================================================== #
# Form-defaults emittente fiscale (Fase 3)                             #
# ================================================================== #


class EmittentiFormDefaultsView(AdminAPIView):
    """GET defaults pre-compilazione form anagrafica emittente fiscale.

    Centralizza il consumo dei `config.parameters` `EMITTENTE_DEFAULT_*`
    (BOLLO_AUTO, BOLLO_SOGLIA, ROUNDING_POLICY) con cast tipi gia'
    applicato lato BE. Il FE non duplica il cast generico di
    `/core/parameters/defaults/`. Pattern allineato a
    `ApiArticoliFormDefaults` (catalogo Fase 8 — A5).

    Response: {defaults: {bollo_auto, bollo_soglia, rounding_policy},
               non_editable_fields: [...]}.
    """

    @extend_schema(
        responses={200: inline_serializer(
            name="AmmEmittentiFormDefaultsResp",
            fields={
                "data": inline_serializer(
                    name="AmmEmittentiFormDefaultsData",
                    fields={
                        "defaults": serializers.DictField(),
                        "non_editable_fields": serializers.ListField(
                            child=serializers.CharField(),
                        ),
                    },
                ),
                "meta": serializers.DictField(required=False),
            },
        )},
    )
    # Scopo: Restituisce defaults form emittente fiscale (Fase 3 — A5).
    def get(self, request: Request) -> JsonResponse:
        from apps.core.api.views_parameters import get_user_context
        from apps.core.services.parameter_service import ParameterService

        ctx = get_user_context(request, ParameterService())
        return success_response(
            AmmSoftwareService().get_emittente_form_defaults(**ctx)
        )


class EmittenteRoundingModesLookupView(AdminAPIView):
    """GET lookup statico modi di arrotondamento per emittente fiscale.

    Single source of truth in
    `amm_software_service._ROUNDING_MODE_VALIDI_EMITTENTE` +
    `_ROUNDING_MODE_DESCRIZIONI_EMITTENTE`. Niente DB: 4 codici fissi
    (UP/DOWN/HALF_UP/HALF_DOWN) allineati al CHECK
    `chk_emittenti_fiscali_rounding_policy`. Pattern simmetrico a
    `ApiUomRoundingModesLookup` di catalogo (che ha 5 codici, include
    HALF_EVEN — quello e' un altro enum).
    """

    @extend_schema(
        responses={200: inline_serializer(
            name="AmmEmittenteRoundingModesLookupResp",
            fields={
                "data": serializers.ListField(child=serializers.DictField()),
                "meta": serializers.DictField(required=False),
            },
        )},
    )
    # Scopo: Restituisce la lista statica dei modi di arrotondamento.
    def get(self, request: Request) -> JsonResponse:
        del request
        return success_response(
            AmmSoftwareService().list_emittente_rounding_modes()
        )


# ================================================================== #
# Lookup audit + email log stati (Fase 5)                              #
# ================================================================== #


class AuditSourcesLookupView(AdminAPIView):
    """GET lookup sorgenti audit ammesse (Fase 5 — A13).

    Single source of truth lato DB: `script.vw_audit_sources`. Sostituisce
    `buildAuditTabellaOptions` hardcoded del FE legacy. Risposta arricchita
    con `area_funzionale` (5 valori: PERMESSI/AUTH/ANAGRAFICHE/EMITTENTI/
    FATTURAZIONE) per raggruppamento UI opzionale.

    Cardinalita' bassa (8 righe attuali): no paginazione, lista nuda in `data`.
    Pattern coerente con altri lookup statici amm-software.
    """

    @extend_schema(
        responses={200: inline_serializer(
            name="AmmAuditSourcesLookupResp",
            fields={
                "data": serializers.ListField(child=serializers.DictField()),
                "meta": serializers.DictField(required=False),
            },
        )},
    )
    # Scopo: Restituisce la lista delle sorgenti audit ammesse.
    def get(self, request: Request) -> JsonResponse:
        del request
        return success_response(AmmSoftwareService().list_audit_sources())


