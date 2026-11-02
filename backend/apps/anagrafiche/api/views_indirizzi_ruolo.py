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
from apps.anagrafiche.db._helpers import resolve_soggetto_id
from apps.anagrafiche.db.soggetti_repository import SoggettiRepository
from apps.anagrafiche.services.soggetti_service import SoggettiService
from apps.anagrafiche.error_codes import E_ANAG_NOT_FOUND

_repo = SoggettiRepository()

# Colonne selezionate dalle viste resolved (subset utile per la UI).
# Fonte: vw_indirizzi_resolved_ruolo / vw_indirizzi_resolved_soggetto
# (changeset 20260325-04-recreate-indirizzi-chain-istanza-mctit.yaml)
_RESOLVE_UTILITY = """(SELECT u.codice FROM config.utilities u
            WHERE u.id = COALESCE(
              (SELECT idp.utility_id FROM anagrafiche.istanze_dati_precontrattuali idp
                WHERE idp.istanza_utility_id = v.istanza_utility_id LIMIT 1),
              (SELECT ba.utility_id FROM anagrafiche.billing_account ba
                WHERE ba.istanza_utility_id = v.istanza_utility_id LIMIT 1)
            )) AS utility_codice"""

_COLS = """v.indirizzo_id AS id,
           v.soggetto_ruolo_id,
           v.istanza_utility_id,
           v.tipo_indirizzo_id,
           v.tipo_indirizzo_codice,
           v.tipo_indirizzo_codice_interno,
           v.tipo_indirizzo_descrizione,
           v.is_normalizzato,
           v.indirizzo_dettaglio_id,
           v.indirizzo_display,
           v.indirizzo_libero,
           v.comune_id,
           v.comune_id AS det_comune_id,
           v.comune_descrizione,
           v.comune_descrizione AS descrizione_comune,
           v.cap,
           v.provincia_sigla,
           v.stato_id,
           v.stato_descrizione,
           v.stato_iso2,
           v.codice_postale_id,
           v.cap_codice,
           v.stradario_id,
           v.via_norm AS stradario_display,
           v.civico,
           v.estensione_civico,
           v.palazzina,
           v.scala,
           v.piano,
           v.interno"""


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
                    SELECT {_COLS}, {_RESOLVE_UTILITY}, 'istanza' AS fonte
                      FROM anagrafiche.vw_indirizzi_resolved_ruolo v
                     WHERE v.soggetto_ruolo_id = %s
                       AND v.istanza_utility_id = %s
                     ORDER BY v.tipo_indirizzo_id, v.indirizzo_id
                """  # noqa: S608 — _COLS/_RESOLVE_UTILITY costanti di modulo, valori come parametri
                cursor.execute(sql_ist, [soggetto_ruolo_id, istanza_utility_id])
                l1 = rows_to_list(cursor)
                results.extend(l1)
                tipi_coperti.update(
                    c["tipo_indirizzo_id"] for c in l1
                    if c["tipo_indirizzo_id"] is not None
                )

            # Livello 2: indirizzi ruolo senza istanza (generici del ruolo)
            sql_ruolo = f"""
                SELECT {_COLS}, {_RESOLVE_UTILITY}, 'ruolo' AS fonte
                  FROM anagrafiche.vw_indirizzi_resolved_ruolo v
                 WHERE v.soggetto_ruolo_id = %s
                   AND v.istanza_utility_id IS NULL
                 ORDER BY v.tipo_indirizzo_id, v.indirizzo_id
            """  # noqa: S608 — _COLS/_RESOLVE_UTILITY costanti di modulo, valori come parametri
            cursor.execute(sql_ruolo, [soggetto_ruolo_id])
            l2 = rows_to_list(cursor)
            for c in l2:
                tipo = c["tipo_indirizzo_id"]
                if tipo is not None and tipo not in tipi_coperti:
                    results.append(c)
                    tipi_coperti.add(tipo)

            # Livello 3: indirizzi soggetto (fallback readonly)
            sql_sogg = f"""
                SELECT {_COLS}, {_RESOLVE_UTILITY}, 'soggetto' AS fonte
                  FROM anagrafiche.vw_indirizzi_resolved_soggetto v
                 WHERE v.soggetto_id = %s::uuid
                 ORDER BY v.tipo_indirizzo_id, v.indirizzo_id
            """  # noqa: S608 — _COLS/_RESOLVE_UTILITY costanti di modulo, valori come parametri
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
# Indirizzo ruolo — dettaglio (PATCH, DELETE)
# =================================================================

class RuoloIndirizziDetailView(DomainAPIView):
    """PATCH aggiorna, DELETE elimina indirizzo del ruolo."""
    area_funzionale = "anagrafiche"

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
