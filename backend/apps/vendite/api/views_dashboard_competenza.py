# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API read-only Lente 1 Competenza (aggregata mensile + drill-down
#        attivita' + errori vivi) — cruscotti fatturazione a due lenti.
# ------------------------------------------------------------

# Tre endpoint GET sottili sopra le viste vendite.vw_dash_competenza_*
# (brief brief-design-fatturazione-due-lenti §4, DB in
# brief-db-fatturazione-due-lenti §4). Livello LETTURA sufficiente;
# lo scope emittente e' interamente DB-side (GUC fail-closed nelle viste).

from datetime import date
from typing import Any

from django.http import HttpResponse, JsonResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.core.api.base_views import DomainAPIView
from apps.core.api.openapi_params import parametri_finestra, param_ricerca_full
from apps.core.api.payload_validators import (
    pagina_da_query,
    qp_bool_optional,
    qp_int_optional,
    qp_int_strict,
    qp_iso_date_optional,
    qp_str,
    qp_str_upper,
)
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.success_responses import success_response
from apps.vendite.api.dash_export_helpers import build_dash_export_response
from apps.core.services.error_manager import ErrorManager
from apps.vendite.services.vendite_service import (
    fn_check_attivita_riportabili,
    fn_riporta_attivita_da_emettere,
    fn_dash_competenza_residui,
    fn_dash_competenza_attivita,
    fn_dash_competenza_commesse,
    fn_dash_competenza_errori,
    fn_dash_competenza_gruppi,
    fn_dash_competenza_mensile,
    fn_get_registro_codice,
)


class ApiDashboardCompetenza(DomainAPIView):
    """GET /api/v1/vendite/dashboard-competenza/ — 12 mesi × 4 stadi funnel."""

    area_funzionale = "vendite"

    @extend_schema(
        operation_id="vendite_dashboard_competenza",
        parameters=[
            OpenApiParameter(
                name="anno",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Anno di competenza (default: anno corrente; range 2000-2100).",
            ),
        ],
        responses={
            200: inline_serializer(
                name="VenditeDashCompetenzaResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeDashCompetenzaData",
                        fields={
                            "anno": serializers.IntegerField(),
                            "mesi": serializers.ListField(child=serializers.DictField()),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce via GET l'aggregata annuale della Lente Competenza
    #        (12 mesi sempre presenti, 4 stadi per mese con breakdown stato
    #        fattura sul FATTURATA + conteggio errori vivi per mese).
    def get(self, request: Request) -> JsonResponse:
        anno = qp_int_strict(
            request.query_params.get("anno"), "anno", oggi_aziendale().year
        )
        data = fn_dash_competenza_mensile(anno=anno)
        return success_response(data)


class ApiDashboardCompetenzaAttivita(DomainAPIView):
    """GET /api/v1/vendite/dashboard-competenza/attivita/ — drill-down attivita'."""

    area_funzionale = "vendite"
    is_search_endpoint = True

    @extend_schema(
        operation_id="vendite_dashboard_competenza_attivita",
        parameters=[
            OpenApiParameter(
                name="competenza_mese",
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Mese di competenza ISO (YYYY-MM-DD, normalizzato al 1° del mese).",
            ),
            OpenApiParameter(
                name="stadio",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Filtro stadio funnel: DA_APPROVARE | DA_EMETTERE | "
                    "EMESSA_NON_FATTURATA | FATTURATA (default: tutti)."
                ),
            ),
            OpenApiParameter(
                name="solo_ritardo",
                type=bool,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Se true, solo attivita' emesse in ritardo (recuperi tardivi).",
            ),
            OpenApiParameter(
                name="order_by",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Colonna di ordinamento (whitelist): commessa_codice | "
                    "cliente_display | articolo_codice (ordina per la descrizione "
                    "mostrata) | data_attivita (default) | valore. Ordinamento "
                    "server-side su tutte le pagine. Colonna non ammessa -> 400."
                ),
            ),
            OpenApiParameter(
                name="order_dir",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Direzione ordinamento: asc | desc. Valore diverso -> 400 "
                    "(E_VENDITE_VALIDATION)."
                ),
            ),
            *parametri_finestra(),
        ],
        responses={
            200: inline_serializer(
                name="VenditeDashCompetenzaAttivitaResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeDashCompetenzaAttivitaData",
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
    # Scopo: Restituisce via GET la lista paginata delle attivita' del mese di
    #        competenza richiesto (drill-down card stadio della Lente 1).
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        competenza_mese = qp_iso_date_optional(qp.get("competenza_mese"), "competenza_mese")
        ErrorManager.require(
            competenza_mese is not None,
            code="E_VENDITE_VALIDATION",
            message="Parametro competenza_mese obbligatorio.",
            function_name="vendite.api.views_dashboard_competenza.attivita",
        )
        assert competenza_mese is not None
        stadio = qp_str_upper(qp.get("stadio"))
        solo_ritardo = qp_bool_optional(qp.get("solo_ritardo"), "solo_ritardo")
        # Ordinamento (convenzione order_by/order_dir): whitelist + direzione
        # validate nel service (unica definizione, fail-fast 400).
        order_by = qp_str(qp.get("order_by"))
        order_dir = qp_str(qp.get("order_dir"))
        limit, offset = pagina_da_query(qp)

        # Scope emittente interamente DB-side (GUC fail-closed nella vista):
        # la view non passa alcun auth_user_id.
        data = fn_dash_competenza_attivita(
            competenza_mese=competenza_mese,
            stadio=stadio,
            solo_ritardo=bool(solo_ritardo),
            order_by=order_by,
            order_dir=order_dir,
            limit=limit,
            offset=offset,
        )
        return success_response(data)


class ApiDashboardCompetenzaCommesse(DomainAPIView):
    """GET /api/v1/vendite/dashboard-competenza/commesse/ — drill-down per commessa."""

    area_funzionale = "vendite"
    is_search_endpoint = True
    lista_codice = "vendite.dash_competenza_commesse"

    @extend_schema(
        operation_id="vendite_dashboard_competenza_commesse",
        parameters=[
            OpenApiParameter(
                name="competenza_mese",
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Mese di competenza ISO (YYYY-MM-DD, normalizzato al 1° del mese).",
            ),
            OpenApiParameter(
                name="stadio",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Filtro stadio funnel: DA_APPROVARE | DA_EMETTERE | "
                    "EMESSA_NON_FATTURATA | FATTURATA (default: tutti)."
                ),
            ),
            OpenApiParameter(
                name="solo_ritardo",
                type=bool,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Se true, solo attivita' emesse in ritardo (recuperi tardivi).",
            ),
            OpenApiParameter(
                name="order_by",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Colonna di ordinamento (whitelist): commessa_codice | "
                    "cliente_display | n_attivita | valore_tot (default) | "
                    "data_attivita_max. Colonna non ammessa -> 400."
                ),
            ),
            OpenApiParameter(
                name="order_dir",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Direzione ordinamento: asc | desc. Valore diverso -> 400.",
            ),
            *parametri_finestra(),
        ],
        responses={
            200: inline_serializer(
                name="VenditeDashCompetenzaCommesseResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeDashCompetenzaCommesseData",
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
    # Scopo: Restituisce via GET la lista paginata AGGREGATA per commessa del
    #        mese/stadio di competenza (DEC-4: una riga per commessa; il dettaglio
    #        a grana attivita' resta nel drawer di gestione).
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        competenza_mese = qp_iso_date_optional(qp.get("competenza_mese"), "competenza_mese")
        ErrorManager.require(
            competenza_mese is not None,
            code="E_VENDITE_VALIDATION",
            message="Parametro competenza_mese obbligatorio.",
            function_name="vendite.api.views_dashboard_competenza.commesse",
        )
        assert competenza_mese is not None
        stadio = qp_str_upper(qp.get("stadio"))
        solo_ritardo = qp_bool_optional(qp.get("solo_ritardo"), "solo_ritardo")
        order_by = qp_str(qp.get("order_by"))
        order_dir = qp_str(qp.get("order_dir"))
        limit, offset = pagina_da_query(qp)

        data = fn_dash_competenza_commesse(
            competenza_mese=competenza_mese,
            stadio=stadio,
            solo_ritardo=bool(solo_ritardo),
            order_by=order_by,
            order_dir=order_dir,
            limit=limit,
            offset=offset,
        )
        return success_response(data)


# Scopo: i filtri di dominio della lista GRUPPI, letti dalla query string una
#        volta sola.
#
# ⛔ ESISTE PERCHE' LE COPIE ERANO DUE, e la seconda ha davvero sbagliato.
#    Lista ed export leggevano gli stessi parametri in due punti diversi;
#    aggiungendo il filtro sezionale l'ho messo nella lista e **dimenticato
#    nell'export**, che avrebbe prodotto un file con TUTTE le righe mentre a
#    video ne restavano 32 — e chi lo apre non ha modo di accorgersene, perche'
#    crede di avere davanti il perimetro che aveva a schermo. E' l'esatto
#    difetto che il commento dell'export dichiarava di voler evitare.
#    Una sede sola: il prossimo filtro nasce in tutti e due i posti o in
#    nessuno.
#
# ⚠️ `qp_bool_optional` e non `qp_bool` sui due flag: il secondo torna True
#    quando il parametro e' ASSENTE (`default=True`), quindi la lista si
#    aprirebbe mostrando i soli gruppi «non determinabili» — cioe' quasi nulla,
#    senza che nessun filtro risulti attivo a video.
# ⚠️ Gli id sono validati (`qp_int_optional`): un non-numero fa 400, non un
#    filtro ignorato in silenzio che mostrerebbe tutto facendo credere di aver
#    scelto qualcosa.
# ℹ️ `tipo_gruppo` resta senza whitelist Python di proposito: il vocabolario e'
#    estensibile lato DB (`config.sorgenti.codice_interno` + `ONERI_COMMESSA`) e
#    una copia qui si disallineerebbe al primo tipo aggiunto. E' un bind param,
#    e le voci valide le dichiara il blocco `tipi` della risposta.
# ⛔ NON legge paginazione ne' `formato`: sono di trasporto, non di dominio, e i
#    due chiamanti li trattano diversamente.
def _filtri_gruppi_da_query(qp: Any) -> dict[str, Any]:
    return {
        "stadio": qp_str_upper(qp.get("stadio")),
        "tipo_gruppo": qp_str_upper(qp.get("tipo_gruppo")),
        "ba_fatturazione_id": qp_int_optional(
            qp.get("ba_fatturazione_id"), "ba_fatturazione_id",
        ),
        "ba_non_determinabile": bool(
            qp_bool_optional(qp.get("ba_non_determinabile"), "ba_non_determinabile")
        ),
        "registro_id": qp_int_optional(qp.get("registro_id"), "registro_id"),
        "registro_non_risolvibile": bool(
            qp_bool_optional(
                qp.get("registro_non_risolvibile"), "registro_non_risolvibile",
            )
        ),
        "search": qp_str(qp.get("search")),
        "order_by": qp_str(qp.get("order_by")),
        "order_dir": qp_str(qp.get("order_dir")),
    }


class ApiDashboardCompetenzaResidui(DomainAPIView):
    """GET /api/v1/vendite/dashboard-competenza/residui/ — l'elenco dei residui.

    ⛔ Non e' un filtro della lista attivita': e' una lista sua, e la ragione e'
    di dominio. Lo stadio `EMESSA_NON_FATTURATA` contiene TRE situazioni con
    rimedi opposti, e solo `RESIDUO` chiede un'azione — le altre due sono
    «niente da fare». Esporre un parametro per scegliere il motivo darebbe a chi
    chiama l'illusione di poter allargare il perimetro del verbo, che invece e'
    deciso dal modello.
    """

    area_funzionale = "vendite"
    is_search_endpoint = True
    lista_codice = "vendite.dash_competenza_residui"

    @extend_schema(
        operation_id="vendite_dashboard_competenza_residui",
        parameters=[
            OpenApiParameter(
                name="competenza_mese",
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Mese di competenza ISO (YYYY-MM-DD, normalizzato al 1° del mese).",
            ),
            OpenApiParameter(
                name="order_by",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Colonna di ordinamento (whitelist): commessa_codice | "
                    "cliente_display | articolo_codice | articolo_descrizione | "
                    "competenza_mese (default, asc) | data_attivita | valore | "
                    "lotto_provenienza_codice | motivo_non_fatturata | "
                    "emittente_ragione_sociale. Colonna non ammessa -> 400."
                ),
            ),
            OpenApiParameter(
                name="order_dir",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Direzione ordinamento: asc | desc. Valore diverso -> 400.",
            ),
            *parametri_finestra(),
        ],
        responses={
            200: inline_serializer(
                name="VenditeDashCompetenzaResiduiResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeDashCompetenzaResiduiData",
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
    # Scopo: Restituisce via GET l'elenco paginato dei RESIDUI del mese — le
    #        attivita' su cui il verbo «Riporta da emettere» e' proponibile.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        # ⚠️ `_competenza_mese_obbligatoria` e non una copia del guard: il
        #    messaggio e il codice di rifiuto del parametro obbligatorio sono
        #    gia' scritti una volta, e due copie divergono senza fallire — la
        #    stessa richiesta malfatta risponderebbe due frasi diverse a
        #    seconda di quale endpoint la riceve.
        competenza_mese = _competenza_mese_obbligatoria(
            request,
            function_name="vendite.api.views_dashboard_competenza.residui",
        )
        limit, offset = pagina_da_query(qp)
        data = fn_dash_competenza_residui(
            competenza_mese=competenza_mese,
            order_by=qp_str(qp.get("order_by")),
            order_dir=qp_str(qp.get("order_dir")),
            limit=limit,
            offset=offset,
        )
        return success_response(data)


class ApiAttivitaRiportaDaEmettere(DomainAPIView):
    """POST /api/v1/vendite/attivita-fatturabili/riporta-da-emettere/

    Il verbo «Riporta da emettere»: rimette in coda di fatturazione un elenco di
    attivita' RESIDUE. Non ricrea lotti ne' fatture — il lavoro ricompare in
    «Da emettere» e segue il giro normale.

    ⛔ Permesso DEDICATO `riporta_da_emettere` (`config.azioni_processo` 33) e
    non `reset_lotto_fattura_draft`: legare un verbo di RECUPERO a chi puo'
    cancellare documenti sarebbe mettere insieme due mestieri diversi.
    """

    area_funzionale = "vendite"
    post_permission = "riporta_da_emettere"

    @extend_schema(
        operation_id="vendite_attivita_riporta_da_emettere",
        parameters=[
            OpenApiParameter(
                name="Idempotency-Key",
                type=str,
                location=OpenApiParameter.HEADER,
                required=True,
                description="Chiave idempotenza obbligatoria per endpoint write.",
            )
        ],
        request=inline_serializer(
            name="VenditeRiportaDaEmettereRequest",
            fields={
                "attivita_fatturabili_ids": serializers.ListField(
                    child=serializers.IntegerField(),
                ),
            },
        ),
        responses={
            200: inline_serializer(
                name="VenditeRiportaDaEmettereResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeRiportaDaEmettereData",
                        fields={
                            "riportate": serializers.IntegerField(),
                            "riemesse_attivita": serializers.IntegerField(),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Riporta «da emettere» le attivita' indicate (elenco di id).
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return fn_riporta_attivita_da_emettere(
                attivita_fatturabili_ids=payload.get("attivita_fatturabili_ids"),  # type: ignore[arg-type]
            )

        return handle_post_json(request, handler=_handler, require_idempotency_key=True)


class ApiAttivitaRiportabili(DomainAPIView):
    """POST /api/v1/vendite/attivita-fatturabili/riportabili/ — i motivi ostativi.

    ⚠️ E' un POST pur essendo una LETTURA, e la ragione e' l'elenco di id: una
    selezione di 200 righe non sta in una query string. Nessun side-effect,
    nessuna `Idempotency-Key` — non modifica niente.

    ⭐ Serve a SPIEGARE invece di far fallire: il catalogo dichiara che
    incontrare `E_ATTIVITA_GIA_DA_EMETTERE` significa che l'elenco a schermo era
    invecchiato, quindi l'interfaccia ri-guarda prima di agire su una selezione
    che ha in mano da un po'.

    ⛔ Porta lo STESSO permesso del verbo, `riporta_da_emettere`, e va dichiarato
    a mano: senza, `ZeroERPPermission` cade sul mestiere del metodo HTTP e un
    POST chiede `add` sull'area. Sarebbe il gate sbagliato nei DUE versi — chi
    puo' riportare ma non creare si vedrebbe negare la spiegazione di un verbo
    che gli e' concesso, e chi puo' creare senza poter riportare potrebbe
    interrogare un verbo che non gli spetta. Chi puo' agire puo' chiedere: e'
    la stessa porta, guardata prima di aprirla.
    """

    area_funzionale = "vendite"
    post_permission = "riporta_da_emettere"
    # Una LETTURA che viaggia in POST: permesso di lettura e niente
    # `Idempotency-Key` (brief-be-verifica-documentazione-api §A5).
    post_accesso = "view"

    @extend_schema(
        operation_id="vendite_attivita_riportabili",
        request=inline_serializer(
            name="VenditeAttivitaRiportabiliRequest",
            fields={
                "attivita_fatturabili_ids": serializers.ListField(
                    child=serializers.IntegerField(),
                ),
            },
        ),
        responses={
            200: inline_serializer(
                name="VenditeAttivitaRiportabiliResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeAttivitaRiportabiliData",
                        fields={"motivi": serializers.ListField(child=serializers.DictField())},
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce i motivi che impediscono il riporto, senza tentarlo.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            return fn_check_attivita_riportabili(
                attivita_fatturabili_ids=payload.get("attivita_fatturabili_ids"),  # type: ignore[arg-type]
            )

        return handle_post_json(request, handler=_handler)


class ApiDashboardCompetenzaGruppi(DomainAPIView):
    """GET /api/v1/vendite/dashboard-competenza/gruppi/ — gruppi fatturabili.

    L'unita' su cui l'operatore decide nella card «Da emettere»: un documento
    sorgente (PRV-0012, CTR-0007…) **oppure** gli oneri di una commessa, che
    documento non hanno e senza questa lista resterebbero lavoro conteggiato ma
    invisibile e non azionabile.

    La `gruppo_key` di ogni riga e' la stessa che si rimanda a
    `POST /vendite/fatturazione/run/` nel campo `gruppi`: non va costruita ne'
    trasformata dal client."""

    area_funzionale = "vendite"
    is_search_endpoint = True
    # ⚠️ Da qui parte l'EMISSIONE MIRATA — si spuntano i gruppi e si fattura:
    #    una lista che mescola emittenti senza dirlo, con un pulsante
    #    «fattura» sotto, e' il caso peggiore che il cancello esiste per
    #    impedire. (Il meccanismo e' su `DomainAPIView.lista_codice`.)
    lista_codice = "vendite.dash_competenza_gruppi"

    @extend_schema(
        operation_id="vendite_dashboard_competenza_gruppi",
        parameters=[
            OpenApiParameter(
                name="competenza_mese",
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Mese di competenza ISO (YYYY-MM-DD, normalizzato al 1° del mese).",
            ),
            OpenApiParameter(
                name="stadio",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Filtro stadio funnel: DA_APPROVARE | DA_EMETTERE | "
                    "EMESSA_NON_FATTURATA | FATTURATA (default: tutti). Il "
                    "cockpit usa DA_EMETTERE."
                ),
            ),
            OpenApiParameter(
                name="tipo_gruppo",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Filtro tipo documento/sorgente (assente = tutti): "
                    "codice_interno della sorgente (PREVENTIVO, ORDINE_VENDITA, "
                    "CONTRATTO, DDT_VENDITA, ...) oppure ONERI_COMMESSA per le "
                    "righe manuali senza documento. Le voci disponibili nel "
                    "perimetro sono nel blocco `tipi` della risposta."
                ),
            ),
            OpenApiParameter(
                name="ba_fatturazione_id",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Filtro CLIENTE: id del billing account di FATTURAZIONE "
                    "(padre se esiste, altrimenti se stesso) — lo stesso "
                    "elemento che la chiave della fattura usa. NON e' un filtro "
                    "per ragione sociale: lo stesso soggetto puo' avere piu' "
                    "alberi BA che finiscono su fatture diverse. Le voci "
                    "disponibili sono nel blocco `clienti` della risposta."
                ),
            ),
            OpenApiParameter(
                name="ba_non_determinabile",
                type=bool,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "true = solo i gruppi il cui cliente di fatturazione NON e' "
                    "determinabile (padre fuori scope). E' l'alternativa a "
                    "`ba_fatturazione_id`, non un valore aggiuntivo: se "
                    "valorizzato, `ba_fatturazione_id` viene ignorato."
                ),
            ),
            OpenApiParameter(
                name="registro_id",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Filtro SEZIONALE: id del registro di fatturazione su cui il "
                    "gruppo finirebbe. Un gruppo che ne tocca piu' di uno "
                    "compare sotto OGNI voce che lo riguarda — il filtro lavora "
                    "sull'insieme dei sezionali del gruppo, non sul codice "
                    "unico, che in quel caso e' vuoto. Le voci disponibili sono "
                    "nel blocco `registri` della risposta."
                ),
            ),
            OpenApiParameter(
                name="registro_non_risolvibile",
                type=bool,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "true = solo i gruppi il cui sezionale NON e' determinabile "
                    "(tipo documento non ancora scelto sulle righe). E' "
                    "l'alternativa a `registro_id`, non un valore aggiuntivo: se "
                    "valorizzato, `registro_id` viene ignorato."
                ),
            ),
            param_ricerca_full(),
            OpenApiParameter(
                name="order_by",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Colonna di ordinamento, da WHITELIST "
                    "(`VenditeRepository.DASH_COMPETENZA_GRUPPI_SORT_COLUMNS`); "
                    "la chiave e' il `campo_sorgente` del catalogo liste, non "
                    "il `codice` logico. Default: `valore` discendente. Colonna "
                    "non ammessa -> 400. "
                    "⚠️ L'elenco NON e' ricopiato qui di proposito: la copia "
                    "precedente si era fermata a nove voci su undici."
                ),
            ),
            OpenApiParameter(
                name="order_dir",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Direzione ordinamento: asc | desc. Valore diverso -> 400.",
            ),
            *parametri_finestra(),
        ],
        responses={
            200: inline_serializer(
                name="VenditeDashCompetenzaGruppiResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeDashCompetenzaGruppiData",
                        fields={
                            "count": serializers.IntegerField(),
                            "page": serializers.IntegerField(),
                            "page_size": serializers.IntegerField(),
                            "total_pages": serializers.IntegerField(),
                            "results": serializers.ListField(child=serializers.DictField()),
                            "riepilogo": serializers.DictField(),
                            "tipi": serializers.ListField(child=serializers.DictField()),
                            "clienti": serializers.ListField(child=serializers.DictField()),
                            "registri": serializers.ListField(child=serializers.DictField()),
                            "n_gruppi_perimetro": serializers.IntegerField(),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce via GET la lista paginata dei gruppi fatturabili del
    #        mese/stadio richiesto PIU' il riepilogo di perimetro (n gruppi, n
    #        attivita', valore, di cui oneri) nella stessa risposta.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        competenza_mese = qp_iso_date_optional(qp.get("competenza_mese"), "competenza_mese")
        ErrorManager.require(
            competenza_mese is not None,
            code="E_VENDITE_VALIDATION",
            message="Parametro competenza_mese obbligatorio.",
            function_name="vendite.api.views_dashboard_competenza.gruppi",
        )
        assert competenza_mese is not None
        limit, offset = pagina_da_query(qp)

        data = fn_dash_competenza_gruppi(
            competenza_mese=competenza_mese,
            **_filtri_gruppi_da_query(qp),
            limit=limit,
            offset=offset,
        )
        return success_response(data)


class ApiDashboardCompetenzaErrori(DomainAPIView):
    """GET /api/v1/vendite/dashboard-competenza/errori/ — errori vivi fatturazione."""

    area_funzionale = "vendite"
    is_search_endpoint = True
    lista_codice = "vendite.dash_competenza_errori"

    @extend_schema(
        operation_id="vendite_dashboard_competenza_errori",
        parameters=[
            OpenApiParameter(
                name="competenza_mese",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Mese di competenza ISO (YYYY-MM-DD, normalizzato al 1° del mese); "
                    "assente = errori vivi di tutti i mesi."
                ),
            ),
            OpenApiParameter(
                name="order_by",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Colonna di ordinamento (tipo_evento, lotto_codice, "
                    "fattura_numero, error_code, data_evento). Assente = "
                    "eventi recenti prima."
                ),
            ),
            OpenApiParameter(
                name="order_dir",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Direzione ordinamento: asc | desc.",
            ),
            *parametri_finestra(),
        ],
        responses={
            200: inline_serializer(
                name="VenditeDashCompetenzaErroriResponse",
                fields={
                    "data": inline_serializer(
                        name="VenditeDashCompetenzaErroriData",
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
    # Scopo: Restituisce via GET la lista paginata degli errori vivi della
    #        fatturazione (task run in ERRORE non superati + fatture critical),
    #        opzionalmente filtrata per mese di competenza (blocco 4 Lente 1).
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        competenza_mese = qp_iso_date_optional(qp.get("competenza_mese"), "competenza_mese")
        # Ordinamento (convenzione order_by/order_dir): whitelist + direzione
        # validate nel service (unica definizione, fail-fast 400).
        order_by = qp_str(qp.get("order_by"))
        order_dir = qp_str(qp.get("order_dir"))
        limit, offset = pagina_da_query(qp)

        data = fn_dash_competenza_errori(
            competenza_mese=competenza_mese,
            order_by=order_by,
            order_dir=order_dir,
            limit=limit,
            offset=offset,
        )
        return success_response(data)


# Scopo: Guard comune delle tre export di competenza per il mese obbligatorio.
#        Le liste gruppi/commesse non hanno senso senza perimetro: senza mese
#        esporterebbero «tutto», che non e' cio' che l'operatore ha a video.
def _competenza_mese_obbligatoria(request: Request, *, function_name: str) -> date:
    competenza_mese = qp_iso_date_optional(
        request.query_params.get("competenza_mese"), "competenza_mese",
    )
    ErrorManager.require(
        competenza_mese is not None,
        code="E_VENDITE_VALIDATION",
        message="Parametro competenza_mese obbligatorio.",
        function_name=function_name,
    )
    assert competenza_mese is not None
    return competenza_mese


# Scopo: il codice del sezionale per la riga «Filtri applicati» dell'export.
#        `None` quando il filtro non e' impostato o l'id non esiste: in entrambi
#        i casi il merge lascia il valore grezzo, che e' meglio di un'etichetta
#        inventata.
def _etichetta_registro(registro_id: int | None) -> str | None:
    if registro_id is None:
        return None
    return fn_get_registro_codice(registro_id)


class ApiDashboardCompetenzaGruppiExport(DomainAPIView):
    """GET /api/v1/vendite/dashboard-competenza/gruppi/export/?formato=csv|xlsx

    Esporta la STESSA lista dei gruppi fatturabili, con gli stessi filtri.
    Colonne e ordine dal catalogo `vendite.dash_competenza_gruppi` risolto
    sulla configurazione dell'operatore. Hard cap 10.000 righe.

    NB: il parametro si chiama `formato` (italiano) NON `format` — magic
    parameter DRF (content-negotiation) che intercetterebbe la chiamata.
    """

    area_funzionale = "vendite"
    is_search_endpoint = True
    lista_codice = "vendite.dash_competenza_gruppi"

    @extend_schema(
        operation_id="vendite_dashboard_competenza_gruppi_export",
        parameters=[
            OpenApiParameter(name="formato", type=str, required=False,
                             description="csv (default) | xlsx"),
            OpenApiParameter(name="competenza_mese", type=str, required=True),
            OpenApiParameter(name="stadio", type=str, required=False),
            OpenApiParameter(name="tipo_gruppo", type=str, required=False),
            OpenApiParameter(name="ba_fatturazione_id", type=int, required=False),
            OpenApiParameter(name="ba_non_determinabile", type=bool, required=False),
            OpenApiParameter(name="registro_id", type=int, required=False),
            OpenApiParameter(name="registro_non_risolvibile", type=bool, required=False),
            param_ricerca_full(),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={(200, "text/csv"): OpenApiTypes.BINARY},
    )
    # Scopo: Genera il file (CSV/XLSX) dei gruppi fatturabili del mese.
    # ⚠️ I filtri sono gli STESSI della lista, filtro cliente e ricerca compresi:
    #        un export che non corrisponde a cio' che si vede a video e' peggio
    #        di nessun export — chi lo apre crede di avere il perimetro che
    #        aveva davanti, e non ha modo di accorgersi che non e' cosi'.
    def get(self, request: Request) -> HttpResponse:
        qp = request.query_params
        competenza_mese = _competenza_mese_obbligatoria(
            request,
            function_name="vendite.api.views_dashboard_competenza.gruppi_export",
        )
        filtri = _filtri_gruppi_da_query(qp)
        return build_dash_export_response(
            request,
            lista_codice="vendite.dash_competenza_gruppi",
            fetch=fn_dash_competenza_gruppi,
            filtri={"competenza_mese": competenza_mese, **filtri},
            # ⚠️ L'etichetta risolta, e non l'id: la riga «Filtri applicati» in
            # testa al file e' l'unica cosa che dice a chi apre il foglio QUALE
            # perimetro ha davanti, e `registro_id=4` non glielo dice — la
            # apre un mese dopo, su una macchina che il catalogo non ce l'ha.
            etichette_filtri={
                "registro_id": _etichetta_registro(filtri["registro_id"]),
            },
        )


class ApiDashboardCompetenzaCommesseExport(DomainAPIView):
    """GET /api/v1/vendite/dashboard-competenza/commesse/export/?formato=csv|xlsx

    Esporta la STESSA lista aggregata per commessa, con gli stessi filtri.
    Colonne e ordine dal catalogo `vendite.dash_competenza_commesse`.
    Hard cap 10.000 righe. Parametro `formato`, non `format`.
    """

    area_funzionale = "vendite"
    is_search_endpoint = True
    lista_codice = "vendite.dash_competenza_commesse"

    @extend_schema(
        operation_id="vendite_dashboard_competenza_commesse_export",
        parameters=[
            OpenApiParameter(name="formato", type=str, required=False,
                             description="csv (default) | xlsx"),
            OpenApiParameter(name="competenza_mese", type=str, required=True),
            OpenApiParameter(name="stadio", type=str, required=False),
            OpenApiParameter(name="solo_ritardo", type=bool, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={(200, "text/csv"): OpenApiTypes.BINARY},
    )
    # Scopo: Genera il file (CSV/XLSX) del drill-down per commessa del mese.
    def get(self, request: Request) -> HttpResponse:
        qp = request.query_params
        competenza_mese = _competenza_mese_obbligatoria(
            request,
            function_name="vendite.api.views_dashboard_competenza.commesse_export",
        )
        return build_dash_export_response(
            request,
            lista_codice="vendite.dash_competenza_commesse",
            fetch=fn_dash_competenza_commesse,
            filtri={
                "competenza_mese": competenza_mese,
                "stadio": qp_str_upper(qp.get("stadio")),
                "solo_ritardo": bool(
                    qp_bool_optional(qp.get("solo_ritardo"), "solo_ritardo"),
                ),
                "order_by": qp_str(qp.get("order_by")),
                "order_dir": qp_str(qp.get("order_dir")),
            },
        )


class ApiDashboardCompetenzaResiduiExport(DomainAPIView):
    """GET /api/v1/vendite/dashboard-competenza/residui/export/?formato=csv|xlsx

    Esporta la STESSA lista dei residui che si ha a video, con lo stesso
    ordinamento. Colonne e ordine dal catalogo `vendite.dash_competenza_residui`.
    Hard cap 10.000 righe. Parametro `formato`, non `format` (quest'ultimo è
    magic per DRF).

    ⚠️ Esiste perché la lista ha le azioni di utility come le sorelle, e
    «Esporta» senza endpoint aprirebbe un dialog inerte. ⛔ E soprattutto perché
    senza questo ramo l'export della card cadeva su quello delle COMMESSE: un
    file che non corrisponde a ciò che si ha davanti è peggio di nessun file —
    chi lo apre crede di avere quel perimetro e non ha modo di accorgersene.
    """

    area_funzionale = "vendite"
    is_search_endpoint = True
    lista_codice = "vendite.dash_competenza_residui"

    @extend_schema(
        operation_id="vendite_dashboard_competenza_residui_export",
        parameters=[
            OpenApiParameter(name="formato", type=str, required=False,
                             description="csv (default) | xlsx"),
            OpenApiParameter(name="competenza_mese", type=str, required=True),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={(200, "text/csv"): OpenApiTypes.BINARY},
    )
    # Scopo: Genera il file (CSV/XLSX) dei residui del mese.
    def get(self, request: Request) -> HttpResponse:
        qp = request.query_params
        competenza_mese = _competenza_mese_obbligatoria(
            request,
            function_name="vendite.api.views_dashboard_competenza.residui_export",
        )
        return build_dash_export_response(
            request,
            lista_codice="vendite.dash_competenza_residui",
            fetch=fn_dash_competenza_residui,
            filtri={
                "competenza_mese": competenza_mese,
                "order_by": qp_str(qp.get("order_by")),
                "order_dir": qp_str(qp.get("order_dir")),
            },
        )


class ApiDashboardCompetenzaErroriExport(DomainAPIView):
    """GET /api/v1/vendite/dashboard-competenza/errori/export/?formato=csv|xlsx

    Esporta la STESSA lista degli errori del mese. Colonne e ordine dal
    catalogo `vendite.dash_competenza_errori`. Hard cap 10.000 righe.
    `competenza_mese` e' OPZIONALE qui, come nel GET di lista gemello.
    Parametro `formato`, non `format`.
    """

    area_funzionale = "vendite"
    is_search_endpoint = True
    lista_codice = "vendite.dash_competenza_errori"

    @extend_schema(
        operation_id="vendite_dashboard_competenza_errori_export",
        parameters=[
            OpenApiParameter(name="formato", type=str, required=False,
                             description="csv (default) | xlsx"),
            OpenApiParameter(name="competenza_mese", type=str, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={(200, "text/csv"): OpenApiTypes.BINARY},
    )
    # Scopo: Genera il file (CSV/XLSX) della lista errori del mese.
    def get(self, request: Request) -> HttpResponse:
        qp = request.query_params
        return build_dash_export_response(
            request,
            lista_codice="vendite.dash_competenza_errori",
            fetch=fn_dash_competenza_errori,
            filtri={
                "competenza_mese": qp_iso_date_optional(
                    qp.get("competenza_mese"), "competenza_mese",
                ),
                "order_by": qp_str(qp.get("order_by")),
                "order_dir": qp_str(qp.get("order_dir")),
            },
        )
