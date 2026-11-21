# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views indirizzi a livello ruolo — CRUD indirizzi
#        con soggetto_ruolo_id e cascata 3 livelli:
#        istanza → ruolo generico → soggetto (readonly).
#        Pattern analogo a views_contatti_ruolo.py.
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.success_responses import success_response
from apps.core.api.payload_validators import corpo_oggetto
from apps.core.services.error_manager import ErrorManager
from apps.anagrafiche.api.schema_indirizzo import campi_indirizzo_madre
from apps.anagrafiche.db._helpers import (
    COLONNE_INDIRIZZO_RESOLVED,
    resolve_soggetto_id,
)
from apps.anagrafiche.db.soggetti_repository import SoggettiRepository
from apps.anagrafiche.services.soggetti_service import SoggettiService
from apps.anagrafiche.error_codes import E_ANAG_NOT_FOUND

_repo = SoggettiRepository()

_RESOLVE_UTILITY = """(SELECT u.codice FROM config.utilities u
            WHERE u.id = COALESCE(
              (SELECT idp.utility_id FROM anagrafiche.istanze_dati_precontrattuali idp
                WHERE idp.istanza_utility_id = v.istanza_utility_id LIMIT 1),
              (SELECT ba.utility_id FROM anagrafiche.billing_account ba
                WHERE ba.istanza_utility_id = v.istanza_utility_id LIMIT 1)
            )) AS utility_codice"""


# =================================================================
# Indirizzi ruolo — lista + crea
# =================================================================

class RuoloIndirizziView(DomainAPIView):
    """GET lista indirizzi del ruolo con cascata, POST crea indirizzo per il ruolo."""
    area_funzionale = "anagrafiche"

    @extend_schema(
        parameters=[
            OpenApiParameter(name="istanza_utility_id", type=int, required=False),
        ],
        responses={200: inline_serializer(
            name="RuoloIndirizziListResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista indirizzi con cascata a 3 livelli per tipo_indirizzo_id:
    #        1. Indirizzi ruolo + istanza specifica (fonte='istanza')
    #        2. Indirizzi ruolo + istanza NULL (fonte='ruolo')
    #           mostrati solo se tipo non coperto dal livello 1
    #        3. Indirizzi soggetto (fonte='soggetto', readonly)
    #           mostrati solo se tipo non coperto dai livelli 1 e 2
    #        Query param opzionale: istanza_utility_id.
    # ⚠️ Le righe non portano il motivo di «Copia come…» (D-4 di
    #    brief-db-copia-indirizzo-destinazione): in contesto ruolo la copia va
    #    sulla chiave aperta, e se quella non ammette tipi lo dice il picker
    #    (`ruoli/<id>/indirizzi/tipi/`), uguale per ogni riga.
    def get(self, request: Request, soggetto_ruolo_id: int) -> JsonResponse:
        from django.db import connection
        from apps.core.db._helpers import rows_to_list

        from apps.core.api.payload_validators import qp_int_optional
        # BB `qp_int_optional`, come la gemella `RuoloContattiView`: vuoto =
        # assente, un non intero e' un 400. Niente default fittizio da passare.
        istanza_utility_id = qp_int_optional(
            request.query_params.get("istanza_utility_id"), "istanza_utility_id",
        )

        with connection.cursor() as cursor:
            soggetto_id = resolve_soggetto_id(cursor, soggetto_ruolo_id)

            results: list[dict] = []
            tipi_coperti: set[int] = set()

            # Livello 1: indirizzi ruolo + istanza specifica
            if istanza_utility_id is not None:
                sql_ist = f"""
                    SELECT {COLONNE_INDIRIZZO_RESOLVED}, {_RESOLVE_UTILITY}, 'istanza' AS fonte
                      FROM anagrafiche.vw_indirizzi_resolved_ruolo v
                     WHERE v.soggetto_ruolo_id = %s
                       AND v.istanza_utility_id = %s
                     ORDER BY v.tipo_indirizzo_id, v.indirizzo_id
                """  # noqa: S608 — colonne costanti di modulo, valori come parametri
                cursor.execute(sql_ist, [soggetto_ruolo_id, istanza_utility_id])
                l1 = rows_to_list(cursor)
                results.extend(l1)
                tipi_coperti.update(
                    c["tipo_indirizzo_id"] for c in l1
                    if c["tipo_indirizzo_id"] is not None
                )

            # Livello 2: indirizzi ruolo senza istanza (generici del ruolo)
            sql_ruolo = f"""
                SELECT {COLONNE_INDIRIZZO_RESOLVED}, {_RESOLVE_UTILITY}, 'ruolo' AS fonte
                  FROM anagrafiche.vw_indirizzi_resolved_ruolo v
                 WHERE v.soggetto_ruolo_id = %s
                   AND v.istanza_utility_id IS NULL
                 ORDER BY v.tipo_indirizzo_id, v.indirizzo_id
            """  # noqa: S608 — colonne costanti di modulo, valori come parametri
            cursor.execute(sql_ruolo, [soggetto_ruolo_id])
            l2 = rows_to_list(cursor)
            for c in l2:
                tipo = c["tipo_indirizzo_id"]
                if tipo is not None and tipo not in tipi_coperti:
                    results.append(c)
                    tipi_coperti.add(tipo)

            # Livello 3: indirizzi soggetto (fallback readonly)
            sql_sogg = f"""
                SELECT {COLONNE_INDIRIZZO_RESOLVED}, {_RESOLVE_UTILITY}, 'soggetto' AS fonte
                  FROM anagrafiche.vw_indirizzi_resolved_soggetto v
                 WHERE v.soggetto_id = %s::uuid
                 ORDER BY v.tipo_indirizzo_id, v.indirizzo_id
            """  # noqa: S608 — colonne costanti di modulo, valori come parametri
            cursor.execute(sql_sogg, [soggetto_id])
            l3 = rows_to_list(cursor)
            for c in l3:
                tipo = c["tipo_indirizzo_id"]
                if tipo is not None and tipo not in tipi_coperti:
                    results.append(c)
                    tipi_coperti.add(tipo)

        # Separa per fonte per la UI
        indirizzi_editabili = [c for c in results if c["fonte"] in ("istanza", "ruolo")]
        indirizzi_readonly = [c for c in results if c["fonte"] == "soggetto"]
        return success_response({
            "indirizzi_ruolo": indirizzi_editabili,
            "indirizzi_soggetto": indirizzi_readonly,
        })

    @extend_schema(
        request=inline_serializer(name="RuoloIndirizzoCreateReq", fields=campi_indirizzo_madre(
            istanza_utility_id=serializers.IntegerField(required=False),
        )),
        responses={200: inline_serializer(
            name="RuoloIndirizzoCreateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea indirizzo associato al ruolo (anche di un'istanza): tipo per
    #        codice, forma libera, dettaglio gia' risolto o via da risolvere.
    #        Lo scrive la madre del DB `anagrafiche.fn_crea_indirizzo_ruolo`,
    #        dal service (R-DB-16b, 2026-10-19).
    def post(self, request: Request, soggetto_ruolo_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda payload: SoggettiService().create_indirizzo_ruolo(soggetto_ruolo_id, payload),
        )


# =================================================================
# Indirizzo ruolo — dettaglio (PUT, PATCH, DELETE)
# =================================================================

class RuoloIndirizziTipiView(DomainAPIView):
    """GET i tipi di indirizzo proponibili per il ruolo, o una sua istanza (picker)."""
    area_funzionale = "anagrafiche"

    @extend_schema(
        parameters=[
            OpenApiParameter(name="istanza_utility_id", type=int, required=False),
        ],
        responses={200: inline_serializer(
            name="RuoloIndirizziTipiResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Il picker dei tipi di «Aggiungi» e della copia in contesto ruolo:
    #        senza `istanza_utility_id` il ruolo, con l'istanza la sua chiave.
    def get(self, request: Request, soggetto_ruolo_id: int) -> JsonResponse:
        from apps.core.api.payload_validators import qp_int_optional

        istanza_utility_id = qp_int_optional(
            request.query_params.get("istanza_utility_id"), "istanza_utility_id",
        )
        return success_response({
            "results": SoggettiService().get_tipi_indirizzo_proponibili_ruolo(
                soggetto_ruolo_id, istanza_utility_id,
            ),
        })


# Scopo: Il corpo delle due copie verso il ruolo: i tipi, e la chiave di
#        destinazione (assente o null = il ruolo, altrimenti una sua istanza).
# ⛔ Una FACTORY, non un dizionario di modulo: un campo DRF si lega al primo
#    serializer che lo riceve, e il secondo `inline_serializer` uscirebbe dallo
#    schema OpenAPI senza corpo, senza nessun errore (stessa ragione di
#    `campi_indirizzo_madre`). Presidio: `test_indirizzi_ruolo_api`,
#    `TestSchemaCopiaSuRuolo`.
def _campi_copia_su_ruolo() -> dict[str, serializers.Field]:
    return {
        "tipi_indirizzo_codice_interno": serializers.ListField(child=serializers.CharField()),
        "istanza_utility_id": serializers.IntegerField(required=False, allow_null=True),
    }


class RuoloIndirizziCopiaView(DomainAPIView):
    """POST copia un indirizzo del ruolo in altri tipi («Copia come…»)."""
    area_funzionale = "anagrafiche"

    @extend_schema(
        request=inline_serializer(name="IndirizzoRuoloCopiaReq", fields=_campi_copia_su_ruolo()),
        responses={200: inline_serializer(name="IndirizzoRuoloCopiaResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Il verbo `anagrafiche.fn_copia_indirizzo_ruolo`: la sorgente in
    #        qualunque chiave del ruolo, la copia sulla chiave di destinazione
    #        del corpo (`istanza_utility_id`; assente = il ruolo).
    #        `{"ids": [...]}` (R-1 di brief-db-copia-indirizzo-destinazione).
    def post(self, request: Request, soggetto_ruolo_id: int, indirizzo_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda p: SoggettiService().copia_indirizzo_ruolo(
                soggetto_ruolo_id, indirizzo_id, p,
            ),
        )


class RuoloIndirizziSoggettoCopiaView(DomainAPIView):
    """POST copia un indirizzo del soggetto del ruolo sul ruolo («Copia come…»)."""
    area_funzionale = "anagrafiche"

    @extend_schema(
        request=inline_serializer(name="IndirizzoSoggettoSuRuoloCopiaReq", fields=_campi_copia_su_ruolo()),
        responses={200: inline_serializer(
            name="IndirizzoSoggettoSuRuoloCopiaResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Il gemello dal soggetto al ruolo (D-2): le righe del livello
    #        soggetto della cascata, in contesto ruolo, si copiano sulla chiave
    #        del ruolo col verbo `anagrafiche.fn_copia_indirizzo_soggetto_su_ruolo`.
    #        Stesso corpo e stessa risposta della copia del ruolo.
    def post(self, request: Request, soggetto_ruolo_id: int, indirizzo_soggetto_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda p: SoggettiService().copia_indirizzo_soggetto_su_ruolo(
                soggetto_ruolo_id, indirizzo_soggetto_id, p,
            ),
        )


class RuoloIndirizziDetailView(DomainAPIView):
    """PUT sostituisce, PATCH aggiorna, DELETE elimina indirizzo del ruolo."""
    area_funzionale = "anagrafiche"

    @extend_schema(
        request=inline_serializer(name="RuoloIndirizzoReplaceReq", fields=campi_indirizzo_madre(
            istanza_utility_id=serializers.IntegerField(required=False),
        )),
        responses={200: inline_serializer(
            name="RuoloIndirizzoReplaceResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Sostituisce un indirizzo del ruolo (delete vecchio + create nuovo,
    #        una transazione): la «modifica» del form, gemella del PUT
    #        dell'indirizzo del soggetto.
    def put(self, request: Request, soggetto_ruolo_id: int, indirizzo_id: int) -> JsonResponse:
        return success_response(SoggettiService().replace_indirizzo_ruolo(
            soggetto_ruolo_id, indirizzo_id, corpo_oggetto(request),
        ))

    @extend_schema(
        request=inline_serializer(name="RuoloIndirizzoUpdateReq", fields={
            "tipo_indirizzo_id": serializers.IntegerField(required=False),
            "istanza_utility_id": serializers.IntegerField(required=False),
            "indirizzo_dettaglio_id": serializers.IntegerField(required=False),
            "indirizzo_libero": serializers.CharField(required=False),
            "stato_id": serializers.IntegerField(required=False),
            "comune_id": serializers.IntegerField(required=False),
            "codice_postale_id": serializers.IntegerField(required=False),
        }),
        responses={200: inline_serializer(
            name="RuoloIndirizzoUpdateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiorna indirizzo con ownership check sul ruolo.
    def patch(self, request: Request, soggetto_ruolo_id: int, indirizzo_id: int) -> JsonResponse:
        # Dal service (2026-09-26): e' li' che si validano le chiavi del payload.
        return success_response(
            SoggettiService().update_indirizzo_ruolo(soggetto_ruolo_id, indirizzo_id, corpo_oggetto(request))
        )

    @extend_schema(
        responses={200: inline_serializer(
            name="RuoloIndirizzoDeleteResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Elimina indirizzo con ownership check sul ruolo.
    def delete(self, request: Request, soggetto_ruolo_id: int, indirizzo_id: int) -> JsonResponse:
        deleted = _repo.delete_indirizzo_ruolo(indirizzo_id, soggetto_ruolo_id)
        ErrorManager.require(
            deleted, code=E_ANAG_NOT_FOUND,
            message="Indirizzo non trovato o non appartiene al ruolo.",
        )
        return success_response({"deleted": True})
