# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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
from apps.core.services.error_manager import ErrorManager
from apps.anagrafiche.db._helpers import resolve_soggetto_id
from apps.anagrafiche.db.soggetti_repository import SoggettiRepository
from apps.anagrafiche.error_codes import E_ANAG_NOT_FOUND
from apps.anagrafiche.services._validators import create_with_dedup

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
           v.tipo_indirizzo_descrizione,
           v.is_normalizzato,
           v.indirizzo_dettaglio_id,
           v.indirizzo_display,
           v.indirizzo_libero,
           v.comune_id,
           v.comune_descrizione,
           v.cap,
           v.provincia_sigla,
           v.stato_id,
           v.stato_descrizione,
           v.stato_iso2,
           v.codice_postale_id,
           v.cap_codice"""


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

        istanza_str = request.query_params.get("istanza_utility_id")
        istanza_utility_id = int(istanza_str) if istanza_str and istanza_str.strip() else None

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
                """
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
            """
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
            """
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
        request=inline_serializer(name="RuoloIndirizzoCreateReq", fields={
            "tipo_indirizzo_id": serializers.IntegerField(),
            "istanza_utility_id": serializers.IntegerField(required=False),
            "indirizzo_dettaglio_id": serializers.IntegerField(required=False),
            "indirizzo_libero": serializers.CharField(required=False),
            "stato_id": serializers.IntegerField(required=False),
            "comune_id": serializers.IntegerField(required=False),
            "codice_postale_id": serializers.IntegerField(required=False),
        }),
        responses={200: inline_serializer(
            name="RuoloIndirizzoCreateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Crea indirizzo associato al ruolo.
    #        Accetta modalita' normalizzata (indirizzo_dettaglio_id)
    #        o libera (indirizzo_libero + stato_id).
    #        Il trigger DB valida tipo_indirizzo_id contro la matrice ammessi.
    def post(self, request: Request, soggetto_ruolo_id: int) -> JsonResponse:
        def _handler(payload: dict) -> dict:
            istanza_utility_id = payload.get("istanza_utility_id")
            if istanza_utility_id is not None:
                istanza_utility_id = int(istanza_utility_id)
            result = create_with_dedup(
                lambda: _repo.crea_indirizzo_ruolo(
                    soggetto_ruolo_id,
                    tipo_indirizzo_id=int(payload["tipo_indirizzo_id"]),
                    istanza_utility_id=istanza_utility_id,
                    indirizzo_dettaglio_id=payload.get("indirizzo_dettaglio_id"),
                    indirizzo_libero=payload.get("indirizzo_libero"),
                    stato_id=payload.get("stato_id"),
                    comune_id=payload.get("comune_id"),
                    codice_postale_id=payload.get("codice_postale_id"),
                ),
                "Indirizzo con questo tipo gia' presente per il ruolo/istanza.",
            )
            return result
        return handle_post_json(request, handler=_handler)


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
        updated = _repo.update_indirizzo_ruolo(
            indirizzo_id, soggetto_ruolo_id, request.data,
        )
        ErrorManager.require(
            updated, code=E_ANAG_NOT_FOUND,
            message="Indirizzo non trovato o non appartiene al ruolo.",
        )
        return success_response({"updated": True})

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
