# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API del dominio `magazzino` — il documento interno (inventari e
#        rettifiche, dalla STESSA factory di view), i tre lookup di riga e la
#        consultazione (disponibilita', movimenti).
# Note: Grammatica URL di `api.md`: il metodo dice l'operazione, il path la
#       risorsa, il verbo compare SOLO per le azioni di dominio (`stato/`,
#       `registra/`), come ultimo segmento.
#
#       ⭐ Q-1 (Tid, 2026-09-18): `build_documento_interno_views(famiglia)`
#       costruisce le view di una famiglia — le due copie non si scrivono.
#       Stampo: `build_passaggi_view` / `make_note_views`.
#
#       ⚠️ Le liste sono OFFSET-based (`limit`/`offset`, `{count, results}`),
#       la lingua di `useSearchTable`; `order_by`/`order_dir` passano GREZZI
#       (non dal bundle `parse_list_params`, il cui `order_by` di default,
#       `"descrizione"`, qui non e' una colonna): assenti = `None`, e decide
#       il default del repository — per le date, DESC.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.http import HttpResponse, JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import get_scope_user_id, handle_post_json
from apps.core.api.payload_validators import (
    corpo_oggetto,
    parse_list_params,
    qp_bool_optional,
    qp_int_optional,
    qp_iso_date_optional,
    qp_str,
    qp_str_upper,
)
from apps.core.api.success_responses import success_response
from apps.magazzino.api._comuni import (
    AREA,
    PARAM_FORMATO,
    RISPOSTA_GENERICA,
    RISPOSTE_EXPORT,
    filtri_label,
    params_lista,
)
from apps.magazzino.db.famiglie import FAMIGLIE, FamigliaDocumentoInterno
from apps.magazzino.db.magazzino_repository import (
    DISPONIBILITA_ARTICOLI_SORT_COLUMNS,
    DISPONIBILITA_SORT_COLUMNS,
    DOCUMENTI_SORT_COLUMNS,
    MOVIMENTI_SORT_COLUMNS,
    PIANO_SORT_COLUMNS,
    righe_sort_columns,
)
from apps.magazzino.services import consultazione_service, magazzino_service
from apps.ui.api.export_helpers import build_export_response, parse_export_format
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS
from apps.core.api.openapi_params import param_ricerca_full

# `AREA`, `RISPOSTA_GENERICA`, `params_lista`, `PARAM_FORMATO`, `RISPOSTE_EXPORT`
# e `filtri_label` vivono in `api/_comuni.py` dal 2026-09-21 (seconda
# occorrenza: le view delle anagrafiche in `views_anagrafiche.py`).

# 🔴 Il cancello sull'unico gesto irreversibile del dominio. ⭐ A catalogo dal
#    2026-09-23 (R-3 del brief 2-bis): `config.azioni_processo`, area 6,
#    `pericolosa = t`. ⚠️ Una riga a catalogo non e' un permesso: finche'
#    l'azione non e' ASSEGNATA a un profilo, `fn_check_azione_processo`
#    risponde `false` per tutti tranne i super admin — fail-closed, che e' il
#    verso giusto in cui sbagliare.
# ⭐ Una sola azione per la famiglia (inventari e rettifiche): il verbo e'
#    lo stesso e la matrice e' la stessa.
PERMESSO_REGISTRA = "registra_magazzino"

# Il blocco manuale (Lotto 3 D-L3-j): un'azione sua, perche' un blocco e' una
# PROMESSA, non un fatto sulla merce — chi registra un inventario non e' per
# forza chi riserva merce a un cliente. Il verbo DB la chiede comunque nella
# prima riga (`fn_guard_azione`): qui il cancello e' il primo dei due, ed e'
# quello che risponde prima di toccare il DB.
PERMESSO_BLOCCA = "blocca_merce"


# La ricerca libera delle liste di magazzino (dal 2026-09-23, brief-be-ricerca-
# full-liste-residue §5.3). ⛔ Nessun 400 sotto soglia, testate e disponibilita'
# comprese (brief-db-be-fe-ricerca-soglia-per-lista §6 a, Tid 2026-09-26): il
# termine corto lo ignora il BB, sulla soglia del catalogo della lista.
_PARAM_SEARCH = param_ricerca_full()


# Scopo: i filtri della lista delle testate, letti dalla query string.
def _filtri_documenti(qp) -> dict:
    search = qp_str(qp.get("search"))
    return {
        "magazzino_id": qp_int_optional(qp.get("magazzino_id"), "magazzino_id"),
        "stato": qp_str_upper(qp.get("stato")),
        "data_da": qp_iso_date_optional(qp.get("data_da"), "data_da"),
        "data_a": qp_iso_date_optional(qp.get("data_a"), "data_a"),
        "search": search,
    }


# ══════════════════════════════════════════════════════════════════
#  La factory del documento interno
# ══════════════════════════════════════════════════════════════════

# Scopo: Costruisce le view di UNA famiglia (inventari | rettifiche): lista +
#        export, crea, dettaglio/PATCH/DELETE, `stato/`, `registra/`, righe
#        (lista + export + CRUD) e — solo inventario — `piano/` + export.
#        Torna un dict `{nome: view}` che `urls_v1` monta sotto `<famiglia>/`.
def build_documento_interno_views(f: FamigliaDocumentoInterno) -> dict[str, type[DomainAPIView]]:
    prefisso = f.singolare.capitalize()          # Inventario | Rettifica
    op = f.singolare                             # per gli operation_id
    codice = f.codice

    class _Lista(DomainAPIView):
        area_funzionale = AREA
        is_search_endpoint = True
        lista_codice = f.lista_codice

        @extend_schema(
            operation_id=f"magazzino_{codice}_list",
            parameters=[
                OpenApiParameter(name="magazzino_id", type=int, location=OpenApiParameter.QUERY, required=False),
                OpenApiParameter(
                    name="stato", type=str, location=OpenApiParameter.QUERY, required=False,
                    description="DRAFT | CONFIRM | POSTED | CANCEL.",
                ),
                OpenApiParameter(name="data_da", type=str, location=OpenApiParameter.QUERY, required=False),
                OpenApiParameter(name="data_a", type=str, location=OpenApiParameter.QUERY, required=False),
                _PARAM_SEARCH,
                *params_lista(DOCUMENTI_SORT_COLUMNS, "Senza: data DESC, id DESC."),
            ],
            responses={200: RISPOSTA_GENERICA},
        )
        # Scopo: Restituisce via GET l'elenco paginato delle testate.
        def get(self, request: Request) -> JsonResponse:
            qp = request.query_params
            p = parse_list_params(qp)
            return success_response(magazzino_service.list_documenti(
                codice,
                auth_user_id=get_scope_user_id(request),
                **_filtri_documenti(qp),
                order_by=qp_str(qp.get("order_by")),
                order_dir=qp_str(qp.get("order_dir")),
                limit=p["limit"],
                offset=p["offset"],
            ))

        @extend_schema(
            operation_id=f"magazzino_{codice}_create",
            request=inline_serializer(
                name=f"Magazzino{prefisso}Create",
                fields={
                    "magazzino_id": serializers.IntegerField(),
                    "data": serializers.DateField(required=False),
                    **({"descrizione": serializers.CharField(required=False)} if f.ha_descrizione else {}),
                    "meta": serializers.DictField(required=False),
                },
            ),
            responses={200: RISPOSTA_GENERICA},
        )
        # Scopo: Crea via POST la BOZZA. Il magazzino si sceglie qui e basta.
        def post(self, request: Request) -> JsonResponse:
            return handle_post_json(
                request,
                handler=lambda payload: magazzino_service.crea_documento(codice, dict(payload)),
                require_idempotency_key=True,
            )

    class _ListaExport(DomainAPIView):
        area_funzionale = AREA
        # ⭐ LO STESSO `lista_codice` della lista, letto da lei (presidio
        #    `test_export_lista_codice_pari`).
        lista_codice = _Lista.lista_codice

        @extend_schema(
            operation_id=f"magazzino_{codice}_export",
            parameters=[PARAM_FORMATO, *params_lista(DOCUMENTI_SORT_COLUMNS, "")],
            responses=RISPOSTE_EXPORT,
        )
        # Scopo: Il file della lista, con gli stessi filtri e ordinamento.
        def get(self, request: Request) -> HttpResponse:
            fmt = parse_export_format(request)
            qp = request.query_params
            filtri = _filtri_documenti(qp)
            dati = magazzino_service.list_documenti(
                codice,
                auth_user_id=get_scope_user_id(request),
                **filtri,
                order_by=qp_str(qp.get("order_by")),
                order_dir=qp_str(qp.get("order_dir")),
                limit=EXPORT_MAX_ROWS + 1,
                offset=0,
            )
            return build_export_response(
                request, lista_codice=self.lista_codice,
                results=dati["results"], total=dati["count"],
                filtri_applicati=filtri_label(filtri) or None, fmt=fmt,
            )

    class _Dettaglio(DomainAPIView):
        area_funzionale = AREA

        @extend_schema(operation_id=f"magazzino_{op}_detail", responses={200: RISPOSTA_GENERICA})
        # Scopo: Testata + magazzino + conteggio righe + `capabilities` (+ il
        #        riepilogo del piano, solo inventario).
        # ⭐ Il blob della capability (R-1) e' cio' che il drawer legge per
        #    disegnare la barra: azioni di stato, terna di «registra», che cosa
        #    si puo' ancora modificare, la nota dello stato chiuso.
        def get(self, request: Request, doc_id: int) -> JsonResponse:
            return success_response(magazzino_service.get_documento(codice, doc_id))

        @extend_schema(
            operation_id=f"magazzino_{op}_update",
            request=inline_serializer(
                name=f"Magazzino{prefisso}Patch",
                fields={
                    "data": serializers.DateField(required=False),
                    **({"descrizione": serializers.CharField(required=False, allow_null=True)} if f.ha_descrizione else {}),
                    "meta": serializers.DictField(required=False),
                },
            ),
            responses={200: RISPOSTA_GENERICA},
        )
        # Scopo: Aggiorna via PATCH la testata. ⛔ Non lo stato (`stato/`), non
        #        il magazzino (si sceglie alla nascita).
        def patch(self, request: Request, doc_id: int) -> JsonResponse:
            return success_response(
                magazzino_service.aggiorna_documento(codice, doc_id, corpo_oggetto(request))
            )

        @extend_schema(
            operation_id=f"magazzino_{op}_delete",
            responses={200: inline_serializer(
                name=f"Magazzino{prefisso}Delete",
                fields={"id": serializers.IntegerField(), "eliminato": serializers.BooleanField()},
            )},
        )
        # Scopo: Elimina via DELETE una bozza. Il metodo dice il verbo; il DB
        #        dice se lo stato lo ammette (409).
        # ⚠️ `handle_post_json`: e' la sede unica dell'`Idempotency-Key`; il
        #    corpo di un DELETE e' vuoto e il payload si ignora.
        def delete(self, request: Request, doc_id: int) -> JsonResponse:
            return handle_post_json(
                request,
                handler=lambda _payload: magazzino_service.elimina_documento(codice, doc_id),
                require_idempotency_key=True,
            )

    class _Stato(DomainAPIView):
        area_funzionale = AREA

        @extend_schema(
            operation_id=f"magazzino_{op}_stato",
            request=inline_serializer(
                name=f"Magazzino{prefisso}Stato",
                fields={"stato": serializers.CharField(help_text="CONFIRM | CANCEL | DRAFT")},
            ),
            responses={200: RISPOSTA_GENERICA},
        )
        # Scopo: Chiede via POST un cambio di stato. ⛔ `POSTED` non si chiede:
        #        lo scrive `registra/`.
        def post(self, request: Request, doc_id: int) -> JsonResponse:
            return handle_post_json(
                request,
                handler=lambda payload: magazzino_service.cambia_stato_documento(codice, doc_id, dict(payload)),
                require_idempotency_key=True,
            )

    class _Registra(DomainAPIView):
        area_funzionale = AREA
        post_permission = PERMESSO_REGISTRA

        @extend_schema(
            operation_id=f"magazzino_{op}_registra",
            request=None,
            responses={200: inline_serializer(
                name=f"Magazzino{prefisso}Registra",
                fields={
                    "movimenti": serializers.ListField(child=serializers.DictField()),
                    "n_movimenti": serializers.IntegerField(),
                    "documento": serializers.DictField(),
                },
            )},
        )
        # Scopo: Il POSTING — una sola `SELECT` sulla madre; il DB e' la transazione.
        def post(self, request: Request, doc_id: int) -> JsonResponse:
            return handle_post_json(
                request,
                handler=lambda _payload: magazzino_service.registra_documento(codice, doc_id),
                require_idempotency_key=True,
            )

    class _Righe(DomainAPIView):
        area_funzionale = AREA
        is_search_endpoint = True
        lista_codice = f.lista_righe_codice

        @extend_schema(
            operation_id=f"magazzino_{op}_righe_list",
            parameters=[_PARAM_SEARCH, *params_lista(righe_sort_columns(f), "Senza: id ASC (l'ordine di digitazione).")],
            responses={200: RISPOSTA_GENERICA},
        )
        # Scopo: Le righe della testata, paginate.
        def get(self, request: Request, doc_id: int) -> JsonResponse:
            qp = request.query_params
            p = parse_list_params(qp)
            return success_response(magazzino_service.list_righe(
                codice, doc_id,
                search=qp_str(qp.get("search")),
                order_by=qp_str(qp.get("order_by")),
                order_dir=qp_str(qp.get("order_dir")),
                limit=p["limit"], offset=p["offset"],
            ))

        @extend_schema(
            operation_id=f"magazzino_{op}_righe_create",
            request=inline_serializer(
                name=f"Magazzino{prefisso}RigaCreate",
                fields={
                    "articolo_id": serializers.UUIDField(),
                    f.col_qta: serializers.DecimalField(max_digits=18, decimal_places=6),
                    **({"motivo": serializers.CharField(required=False, allow_null=True)} if f.con_motivo else {}),
                    "costo_unitario": serializers.DecimalField(max_digits=18, decimal_places=6, required=False, allow_null=True),
                    "ubicazione_id": serializers.IntegerField(required=False, allow_null=True),
                    "lotto_id": serializers.IntegerField(required=False, allow_null=True),
                    "asset_id": serializers.IntegerField(required=False, allow_null=True),
                    "meta": serializers.DictField(required=False),
                },
            ),
            responses={200: RISPOSTA_GENERICA},
        )
        # Scopo: Aggiunge via POST una riga (solo in `DRAFT`: lo dice il guard).
        def post(self, request: Request, doc_id: int) -> JsonResponse:
            return handle_post_json(
                request,
                handler=lambda payload: magazzino_service.crea_riga(codice, doc_id, dict(payload)),
                require_idempotency_key=True,
            )

    class _RigheExport(DomainAPIView):
        area_funzionale = AREA
        lista_codice = _Righe.lista_codice

        @extend_schema(
            operation_id=f"magazzino_{op}_righe_export",
            parameters=[PARAM_FORMATO, _PARAM_SEARCH, *params_lista(righe_sort_columns(f), "")],
            responses=RISPOSTE_EXPORT,
        )
        # Scopo: Il file delle righe di UN documento.
        def get(self, request: Request, doc_id: int) -> HttpResponse:
            fmt = parse_export_format(request)
            qp = request.query_params
            dati = magazzino_service.list_righe(
                codice, doc_id,
                search=qp_str(qp.get("search")),
                order_by=qp_str(qp.get("order_by")),
                order_dir=qp_str(qp.get("order_dir")),
                limit=EXPORT_MAX_ROWS + 1, offset=0,
            )
            return build_export_response(
                request, lista_codice=self.lista_codice,
                results=dati["results"], total=dati["count"],
                filtri_applicati=None, fmt=fmt,
            )

    class _Riga(DomainAPIView):
        area_funzionale = AREA

        @extend_schema(
            operation_id=f"magazzino_{op}_riga_update",
            request=inline_serializer(
                name=f"Magazzino{prefisso}RigaPatch",
                fields={
                    "articolo_id": serializers.UUIDField(required=False),
                    f.col_qta: serializers.DecimalField(max_digits=18, decimal_places=6, required=False),
                    **({"motivo": serializers.CharField(required=False, allow_null=True)} if f.con_motivo else {}),
                    "costo_unitario": serializers.DecimalField(max_digits=18, decimal_places=6, required=False, allow_null=True),
                    "ubicazione_id": serializers.IntegerField(required=False, allow_null=True),
                    "lotto_id": serializers.IntegerField(required=False, allow_null=True),
                    "asset_id": serializers.IntegerField(required=False, allow_null=True),
                    "meta": serializers.DictField(required=False),
                },
            ),
            responses={200: RISPOSTA_GENERICA},
        )
        # Scopo: Aggiorna via PATCH una riga (parziale; `null` azzera un nullable).
        def patch(self, request: Request, doc_id: int, riga_id: int) -> JsonResponse:
            return success_response(
                magazzino_service.aggiorna_riga(codice, doc_id, riga_id, corpo_oggetto(request))
            )

        @extend_schema(
            operation_id=f"magazzino_{op}_riga_delete",
            responses={200: inline_serializer(
                name=f"Magazzino{prefisso}RigaDelete",
                fields={"riga_id": serializers.IntegerField(), "eliminata": serializers.BooleanField()},
            )},
        )
        # Scopo: Elimina via DELETE una riga (solo in `DRAFT`: lo dice il guard).
        def delete(self, request: Request, doc_id: int, riga_id: int) -> JsonResponse:
            return handle_post_json(
                request,
                handler=lambda _payload: magazzino_service.elimina_riga(codice, doc_id, riga_id),
                require_idempotency_key=True,
            )

    viste: dict[str, type[DomainAPIView]] = {
        "lista": _Lista,
        "lista_export": _ListaExport,
        "dettaglio": _Dettaglio,
        "stato": _Stato,
        "registra": _Registra,
        "righe": _Righe,
        "righe_export": _RigheExport,
        "riga": _Riga,
    }

    if f.ha_piano:
        class _Piano(DomainAPIView):
            area_funzionale = AREA
            is_search_endpoint = True
            lista_codice = "magazzino.inventario_piano"

            @extend_schema(
                operation_id=f"magazzino_{op}_piano",
                parameters=[_PARAM_SEARCH, *params_lista(PIANO_SORT_COLUMNS, "Senza: articolo, poi la posizione.")],
                responses={200: RISPOSTA_GENERICA},
            )
            # Scopo: Il piano dell'inventario: che cosa il posting scrivera'.
            def get(self, request: Request, doc_id: int) -> JsonResponse:
                qp = request.query_params
                p = parse_list_params(qp)
                return success_response(magazzino_service.list_piano(
                    codice, doc_id,
                    search=qp_str(qp.get("search")),
                    order_by=qp_str(qp.get("order_by")),
                    order_dir=qp_str(qp.get("order_dir")),
                    limit=p["limit"], offset=p["offset"],
                ))

        class _PianoExport(DomainAPIView):
            area_funzionale = AREA
            lista_codice = _Piano.lista_codice

            @extend_schema(
                operation_id=f"magazzino_{op}_piano_export",
                parameters=[PARAM_FORMATO, _PARAM_SEARCH, *params_lista(PIANO_SORT_COLUMNS, "")],
                responses=RISPOSTE_EXPORT,
            )
            # Scopo: Il file del piano.
            def get(self, request: Request, doc_id: int) -> HttpResponse:
                fmt = parse_export_format(request)
                qp = request.query_params
                dati = magazzino_service.list_piano(
                    codice, doc_id,
                    search=qp_str(qp.get("search")),
                    order_by=qp_str(qp.get("order_by")),
                    order_dir=qp_str(qp.get("order_dir")),
                    limit=EXPORT_MAX_ROWS + 1, offset=0,
                )
                return build_export_response(
                    request, lista_codice=self.lista_codice,
                    results=dati["results"], total=dati["count"],
                    filtri_applicati=None, fmt=fmt,
                )

        viste["piano"] = _Piano
        viste["piano_export"] = _PianoExport

    # I nomi delle classi: per lo schema OpenAPI e per i messaggi.
    for nome, vista in viste.items():
        vista.__name__ = f"Api{prefisso}{''.join(p.capitalize() for p in nome.split('_'))}"
        vista.__qualname__ = vista.__name__
        vista.__module__ = __name__
    return viste


VISTE_INVENTARI = build_documento_interno_views(FAMIGLIE["inventari"])
VISTE_RETTIFICHE = build_documento_interno_views(FAMIGLIE["rettifiche"])


# ⚠️ Le quattro view di LISTA con il `lista_codice` LETTERALE nel corpo della
#    classe: lo pretende `test_perimetro_emittente_copertura`, che legge il
#    SORGENTE con `ast` (senza importare le view) e non puo' vedere un
#    attributo assegnato da una factory — per lui `lista_codice = f.lista_codice`
#    e' un cancello che non c'e'. La factory resta la sede del comportamento;
#    queste sottoclassi aggiungono la sola riga che il presidio sa leggere, e
#    il controllo sotto le tiene inchiodate alla config (una stringa ripetuta e'
#    gia' divergente il giorno in cui una delle due cambia).

class ApiInventariList(VISTE_INVENTARI["lista"]):  # type: ignore[valid-type, misc, name-defined]  # base costruita da una fabbrica
    lista_codice = "magazzino.inventari"


class ApiInventarioRigheList(VISTE_INVENTARI["righe"]):  # type: ignore[valid-type, misc, name-defined]  # base costruita da una fabbrica
    lista_codice = "magazzino.inventario_righe"


class ApiRettificheList(VISTE_RETTIFICHE["lista"]):  # type: ignore[valid-type, misc, name-defined]  # base costruita da una fabbrica
    lista_codice = "magazzino.rettifiche"


class ApiRettificaRigheList(VISTE_RETTIFICHE["righe"]):  # type: ignore[valid-type, misc, name-defined]  # base costruita da una fabbrica
    lista_codice = "magazzino.rettifica_righe"


for _viste, _lista, _righe in (
    (VISTE_INVENTARI, ApiInventariList, ApiInventarioRigheList),
    (VISTE_RETTIFICHE, ApiRettificheList, ApiRettificaRigheList),
):
    for _classe, _chiave in ((_lista, "lista"), (_righe, "righe")):
        if _classe.lista_codice != _viste[_chiave].lista_codice:
            raise RuntimeError(
                f"{_classe.__name__}: lista_codice {_classe.lista_codice!r} "
                f"diverso dalla config {_viste[_chiave].lista_codice!r}"
            )
    _viste["lista"] = _lista
    _viste["righe"] = _righe


# ══════════════════════════════════════════════════════════════════
#  I motivi di riga e i lookup dedicati
# ══════════════════════════════════════════════════════════════════

class ApiRigheMotivi(DomainAPIView):
    """GET /api/v1/magazzino/righe/motivi/ — i motivi per cui una riga non sarebbe postabile."""

    area_funzionale = AREA

    @extend_schema(
        operation_id="magazzino_righe_motivi",
        parameters=[
            OpenApiParameter(name="magazzino_id", type=int, location=OpenApiParameter.QUERY, required=True),
            OpenApiParameter(name="articolo_id", type=str, location=OpenApiParameter.QUERY, required=True),
            OpenApiParameter(name="lotto_id", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="asset_id", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="ubicazione_id", type=int, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={200: inline_serializer(
            name="MagazzinoRigheMotivi",
            fields={"motivi": serializers.ListField(child=serializers.DictField())},
        )},
    )
    # Scopo: L'anteprima del form di riga: `script.fn_check_riga_magazzino`
    #        cosi' com'e' — «cio' che si vede e' cio' che verra' scritto».
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        articolo_id = qp_str(qp.get("articolo_id"))
        return success_response(magazzino_service.motivi_riga(
            magazzino_id=qp_int_optional(qp.get("magazzino_id"), "magazzino_id") or 0,
            articolo_id=articolo_id or "",
            lotto_id=qp_int_optional(qp.get("lotto_id"), "lotto_id"),
            asset_id=qp_int_optional(qp.get("asset_id"), "asset_id"),
            ubicazione_id=qp_int_optional(qp.get("ubicazione_id"), "ubicazione_id"),
        ))


# I tre lookup di riga: envelope `{"results": [...]}` (api.md §L'ENVELOPE DI UN
# LOOKUP), consumati DENTRO il dominio (area `magazzino`), non il lookup
# generico: il filtro per padre non e' nel suo contratto.

class ApiMagazzinoUbicazioniLookup(DomainAPIView):
    """GET /api/v1/magazzino/magazzini/<id>/ubicazioni/lookup/ — le ubicazioni attive."""

    area_funzionale = AREA
    is_search_endpoint = True

    @extend_schema(operation_id="magazzino_ubicazioni_lookup", responses={200: RISPOSTA_GENERICA})
    # Scopo: Le ubicazioni attive di un magazzino, per il form di riga.
    def get(self, request: Request, magazzino_id: int) -> JsonResponse:
        return success_response(magazzino_service.lookup_ubicazioni(magazzino_id))


class ApiLottiLookup(DomainAPIView):
    """GET /api/v1/magazzino/lotti/lookup/?articolo_id=&search= — i lotti attivi dell'articolo."""

    area_funzionale = AREA
    is_search_endpoint = True

    @extend_schema(
        operation_id="magazzino_lotti_lookup",
        parameters=[
            OpenApiParameter(name="articolo_id", type=str, location=OpenApiParameter.QUERY, required=True),
            OpenApiParameter(name="search", type=str, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={200: RISPOSTA_GENERICA},
    )
    # Scopo: I lotti attivi di un articolo.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        return success_response(magazzino_service.lookup_lotti(
            articolo_id=qp_str(qp.get("articolo_id")) or "",
            search=qp_str(qp.get("search")),
        ))


class ApiAssetsLookup(DomainAPIView):
    """GET /api/v1/magazzino/assets/lookup/?articolo_id=&magazzino_id= — i seriali attivi."""

    area_funzionale = AREA
    is_search_endpoint = True

    @extend_schema(
        operation_id="magazzino_assets_lookup",
        parameters=[
            OpenApiParameter(name="articolo_id", type=str, location=OpenApiParameter.QUERY, required=True),
            OpenApiParameter(name="magazzino_id", type=int, location=OpenApiParameter.QUERY, required=True),
        ],
        responses={200: RISPOSTA_GENERICA},
    )
    # Scopo: I seriali attivi di un articolo, dell'emittente del magazzino.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        return success_response(magazzino_service.lookup_assets(
            articolo_id=qp_str(qp.get("articolo_id")) or "",
            magazzino_id=qp_int_optional(qp.get("magazzino_id"), "magazzino_id") or 0,
        ))


# ══════════════════════════════════════════════════════════════════
#  Consultazione
# ══════════════════════════════════════════════════════════════════

# Scopo: i filtri della disponibilita', per magazzino e per articolo.
def _filtri_disponibilita(qp, *, con_magazzino: bool) -> dict:
    search = qp_str(qp.get("search"))
    filtri: dict[str, Any] = {
        "articolo_id": qp_str(qp.get("articolo_id")),
        "solo_negativa": bool(qp_bool_optional(qp.get("solo_negativa"), "solo_negativa")),
        "solo_con_giacenza": bool(qp_bool_optional(qp.get("solo_con_giacenza"), "solo_con_giacenza")),
        "search": search,
    }
    if con_magazzino:
        filtri["magazzino_id"] = qp_int_optional(qp.get("magazzino_id"), "magazzino_id")
    return filtri


_PARAMS_DISPONIBILITA = [
    OpenApiParameter(name="articolo_id", type=str, location=OpenApiParameter.QUERY, required=False),
    OpenApiParameter(
        name="solo_negativa", type=bool, location=OpenApiParameter.QUERY, required=False,
        description="Solo disponibile < 0: le promesse non piu' mantenibili (D-L2-d).",
    ),
    OpenApiParameter(name="solo_con_giacenza", type=bool, location=OpenApiParameter.QUERY, required=False),
    _PARAM_SEARCH,
]


class ApiDisponibilita(DomainAPIView):
    """GET /api/v1/magazzino/disponibilita/ — per articolo e magazzino."""

    area_funzionale = AREA
    is_search_endpoint = True
    lista_codice = "magazzino.disponibilita"

    @extend_schema(
        operation_id="magazzino_disponibilita_list",
        parameters=[
            OpenApiParameter(name="magazzino_id", type=int, location=OpenApiParameter.QUERY, required=False),
            *_PARAMS_DISPONIBILITA,
            *params_lista(DISPONIBILITA_SORT_COLUMNS, "Senza: articolo, magazzino."),
        ],
        responses={200: RISPOSTA_GENERICA},
    )
    # Scopo: La disponibilita' per (articolo, magazzino), paginata.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp)
        return success_response(consultazione_service.list_disponibilita(
            auth_user_id=get_scope_user_id(request),
            **_filtri_disponibilita(qp, con_magazzino=True),
            order_by=qp_str(qp.get("order_by")),
            order_dir=qp_str(qp.get("order_dir")),
            limit=p["limit"], offset=p["offset"],
        ))


class ApiDisponibilitaExport(DomainAPIView):
    """GET /api/v1/magazzino/disponibilita/export/ — CSV/XLSX."""

    area_funzionale = AREA
    lista_codice = ApiDisponibilita.lista_codice

    @extend_schema(
        operation_id="magazzino_disponibilita_export",
        parameters=[PARAM_FORMATO, *_PARAMS_DISPONIBILITA, *params_lista(DISPONIBILITA_SORT_COLUMNS, "")],
        responses=RISPOSTE_EXPORT,
    )
    # Scopo: Il file della disponibilita'.
    def get(self, request: Request) -> HttpResponse:
        fmt = parse_export_format(request)
        qp = request.query_params
        filtri = _filtri_disponibilita(qp, con_magazzino=True)
        dati = consultazione_service.list_disponibilita(
            auth_user_id=get_scope_user_id(request), **filtri,
            order_by=qp_str(qp.get("order_by")), order_dir=qp_str(qp.get("order_dir")),
            limit=EXPORT_MAX_ROWS + 1, offset=0,
        )
        return build_export_response(
            request, lista_codice=self.lista_codice,
            results=dati["results"], total=dati["count"],
            filtri_applicati=filtri_label(filtri) or None, fmt=fmt,
        )


class ApiDisponibilitaArticoli(DomainAPIView):
    """GET /api/v1/magazzino/disponibilita/articoli/ — per articolo, somma sui magazzini."""

    area_funzionale = AREA
    is_search_endpoint = True
    lista_codice = "magazzino.disponibilita_articoli"

    @extend_schema(
        operation_id="magazzino_disponibilita_articoli_list",
        parameters=[*_PARAMS_DISPONIBILITA, *params_lista(DISPONIBILITA_ARTICOLI_SORT_COLUMNS, "Senza: articolo.")],
        responses={200: RISPOSTA_GENERICA},
    )
    # Scopo: La disponibilita' per articolo, paginata.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp)
        return success_response(consultazione_service.list_disponibilita_articoli(
            **_filtri_disponibilita(qp, con_magazzino=False),
            order_by=qp_str(qp.get("order_by")),
            order_dir=qp_str(qp.get("order_dir")),
            limit=p["limit"], offset=p["offset"],
        ))


class ApiDisponibilitaArticoliExport(DomainAPIView):
    """GET /api/v1/magazzino/disponibilita/articoli/export/ — CSV/XLSX."""

    area_funzionale = AREA
    lista_codice = ApiDisponibilitaArticoli.lista_codice

    @extend_schema(
        operation_id="magazzino_disponibilita_articoli_export",
        parameters=[PARAM_FORMATO, *_PARAMS_DISPONIBILITA, *params_lista(DISPONIBILITA_ARTICOLI_SORT_COLUMNS, "")],
        responses=RISPOSTE_EXPORT,
    )
    # Scopo: Il file della disponibilita' per articolo.
    def get(self, request: Request) -> HttpResponse:
        fmt = parse_export_format(request)
        qp = request.query_params
        filtri = _filtri_disponibilita(qp, con_magazzino=False)
        dati = consultazione_service.list_disponibilita_articoli(
            **filtri,
            order_by=qp_str(qp.get("order_by")), order_dir=qp_str(qp.get("order_dir")),
            limit=EXPORT_MAX_ROWS + 1, offset=0,
        )
        return build_export_response(
            request, lista_codice=self.lista_codice,
            results=dati["results"], total=dati["count"],
            filtri_applicati=filtri_label(filtri) or None, fmt=fmt,
        )


class ApiDisponibilitaBlocchi(DomainAPIView):
    """GET /api/v1/magazzino/disponibilita/blocchi/?articolo_id&magazzino_id — il drill-down di `n_blocchi`.
    POST stesso path — APRE un blocco manuale (Lotto 3 R-5, verbo `magazzino.fn_apri_blocco`)."""

    area_funzionale = AREA
    post_permission = PERMESSO_BLOCCA

    @extend_schema(
        operation_id="magazzino_disponibilita_blocchi",
        parameters=[
            OpenApiParameter(name="articolo_id", type=str, location=OpenApiParameter.QUERY, required=True),
            OpenApiParameter(name="magazzino_id", type=int, location=OpenApiParameter.QUERY, required=True),
        ],
        responses={200: RISPOSTA_GENERICA},
    )
    # Scopo: Gli attesi APERTA in uscita su (articolo, magazzino).
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        return success_response(consultazione_service.list_blocchi(
            articolo_id=qp_str(qp.get("articolo_id")) or "",
            magazzino_id=qp_int_optional(qp.get("magazzino_id"), "magazzino_id") or 0,
        ))

    @extend_schema(
        operation_id="magazzino_disponibilita_blocco_apri",
        request=inline_serializer(
            name="MagazzinoBloccoApriReq",
            fields={
                "magazzino_id": serializers.IntegerField(),
                "articolo_id": serializers.UUIDField(),
                "qta": serializers.DecimalField(max_digits=18, decimal_places=6),
                "soggetto_ruolo_id": serializers.IntegerField(required=False, allow_null=True),
                "nota": serializers.CharField(required=False, allow_null=True),
                "lotto_id": serializers.IntegerField(required=False, allow_null=True),
                "asset_id": serializers.IntegerField(required=False, allow_null=True),
                "ubicazione_id": serializers.IntegerField(required=False, allow_null=True),
            },
        ),
        responses={200: RISPOSTA_GENERICA},
    )
    # Scopo: Apre il blocco (una sola `SELECT` sul verbo).
    def post(self, request: Request) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda payload: magazzino_service.apri_blocco(dict(payload)),
            require_idempotency_key=True,
        )


class ApiDisponibilitaBloccoLibera(DomainAPIView):
    """POST /api/v1/magazzino/disponibilita/blocchi/<blocco_id>/libera/ — libera
    un blocco (verbo `magazzino.fn_libera_blocco`: autore, momento, nota)."""

    area_funzionale = AREA
    post_permission = PERMESSO_BLOCCA

    @extend_schema(
        operation_id="magazzino_disponibilita_blocco_libera",
        request=inline_serializer(
            name="MagazzinoBloccoLiberaReq",
            fields={"nota": serializers.CharField(required=False, allow_null=True)},
        ),
        responses={200: RISPOSTA_GENERICA},
    )
    # Scopo: Libera il blocco.
    def post(self, request: Request, blocco_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda payload: magazzino_service.libera_blocco(int(blocco_id), dict(payload)),
            require_idempotency_key=True,
        )


# Scopo: i filtri del registro dei movimenti.
def _filtri_movimenti(qp) -> dict:
    return {
        "magazzino_id": qp_int_optional(qp.get("magazzino_id"), "magazzino_id"),
        "articolo_id": qp_str(qp.get("articolo_id")),
        "causale_id": qp_int_optional(qp.get("causale_id"), "causale_id"),
        "data_da": qp_iso_date_optional(qp.get("data_da"), "data_da"),
        "data_a": qp_iso_date_optional(qp.get("data_a"), "data_a"),
        "sorgente_codice_interno": qp_str_upper(qp.get("sorgente_tipo")),
        "inventario_id": qp_int_optional(qp.get("inventario_id"), "inventario_id"),
        "rettifica_id": qp_int_optional(qp.get("rettifica_id"), "rettifica_id"),
        "search": qp_str(qp.get("search")),
    }


_PARAMS_MOVIMENTI = [
    OpenApiParameter(name="magazzino_id", type=int, location=OpenApiParameter.QUERY, required=False),
    OpenApiParameter(name="articolo_id", type=str, location=OpenApiParameter.QUERY, required=False),
    OpenApiParameter(name="causale_id", type=int, location=OpenApiParameter.QUERY, required=False),
    OpenApiParameter(
        name="data_da", type=str, location=OpenApiParameter.QUERY, required=False,
        description="Su `data_mov` (ISO). Il floor standard delle liste lo applica il frontend.",
    ),
    OpenApiParameter(name="data_a", type=str, location=OpenApiParameter.QUERY, required=False),
    OpenApiParameter(
        name="sorgente_tipo", type=str, location=OpenApiParameter.QUERY, required=False,
        description="`config.sorgenti.codice_interno` (INVENTARIO_RIGA, RETTIFICA_RIGA, …).",
    ),
    OpenApiParameter(
        name="inventario_id", type=int, location=OpenApiParameter.QUERY, required=False,
        description="I movimenti nati dalle righe di QUESTO inventario (deep-link dal documento POSTED).",
    ),
    OpenApiParameter(name="rettifica_id", type=int, location=OpenApiParameter.QUERY, required=False),
    _PARAM_SEARCH,
]


class ApiMovimenti(DomainAPIView):
    """GET /api/v1/magazzino/movimenti/ — il registro."""

    area_funzionale = AREA
    is_search_endpoint = True
    lista_codice = "magazzino.movimenti"

    @extend_schema(
        operation_id="magazzino_movimenti_list",
        parameters=[*_PARAMS_MOVIMENTI, *params_lista(MOVIMENTI_SORT_COLUMNS, "Senza: data_mov DESC, id DESC.")],
        responses={200: RISPOSTA_GENERICA},
    )
    # Scopo: Il registro dei movimenti, paginato. Sola lettura per costruzione.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(qp)
        return success_response(consultazione_service.list_movimenti(
            auth_user_id=get_scope_user_id(request),
            **_filtri_movimenti(qp),
            order_by=qp_str(qp.get("order_by")),
            order_dir=qp_str(qp.get("order_dir")),
            limit=p["limit"], offset=p["offset"],
        ))


class ApiMovimentiExport(DomainAPIView):
    """GET /api/v1/magazzino/movimenti/export/ — CSV/XLSX del registro."""

    area_funzionale = AREA
    lista_codice = ApiMovimenti.lista_codice

    @extend_schema(
        operation_id="magazzino_movimenti_export",
        parameters=[PARAM_FORMATO, *_PARAMS_MOVIMENTI, *params_lista(MOVIMENTI_SORT_COLUMNS, "")],
        responses=RISPOSTE_EXPORT,
    )
    # Scopo: Il file del registro, con gli stessi filtri e ordinamento.
    def get(self, request: Request) -> HttpResponse:
        fmt = parse_export_format(request)
        qp = request.query_params
        filtri = _filtri_movimenti(qp)
        dati = consultazione_service.list_movimenti(
            auth_user_id=get_scope_user_id(request), **filtri,
            order_by=qp_str(qp.get("order_by")), order_dir=qp_str(qp.get("order_dir")),
            limit=EXPORT_MAX_ROWS + 1, offset=0,
        )
        return build_export_response(
            request, lista_codice=self.lista_codice,
            results=dati["results"], total=dati["count"],
            filtri_applicati=filtri_label(filtri) or None, fmt=fmt,
        )
