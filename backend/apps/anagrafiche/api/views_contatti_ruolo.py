# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views contatti a livello ruolo — CRUD contatti
#        con soggetto_ruolo_id. Riusa SoggettiRepository per le
#        operazioni base, aggiungendo il filtro/set del ruolo.
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.success_responses import success_response
from apps.core.api.payload_validators import corpo_oggetto, qp_int_optional
from apps.core.services.error_manager import ErrorManager
from apps.anagrafiche.db._helpers import resolve_soggetto_id
from apps.anagrafiche.db.soggetti_repository import SoggettiRepository
from apps.anagrafiche.services.soggetti_service import SoggettiService
from apps.anagrafiche.error_codes import E_ANAG_NOT_FOUND


_repo = SoggettiRepository()


# =================================================================
# Contatti ruolo — lista + crea
# =================================================================

class RuoloContattiView(DomainAPIView):
    """GET lista contatti del ruolo, POST crea contatto per il ruolo."""
    area_funzionale = "anagrafiche"

    @extend_schema(
        parameters=[
            OpenApiParameter(name="istanza_utility_id", type=int, required=False),
        ],
        responses={200: inline_serializer(name="RuoloContattiListResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Lista contatti con cascata a 3 livelli per tipo_contatto_id:
    #        1. Contatti ruolo + istanza specifica → VINCE (fonte='istanza')
    #        2. Contatti ruolo + istanza NULL      → fallback ruolo (fonte='ruolo')
    #           mostrati solo se tipo non coperto dal livello 1
    #        3. Contatti soggetto (ruolo NULL)      → fallback soggetto (fonte='soggetto')
    #           mostrati solo se tipo non coperto dai livelli 1 e 2
    #        Query param opzionale: istanza_utility_id (se assente, nessun filtro istanza).
    def get(self, request: Request, soggetto_ruolo_id: int) -> JsonResponse:
        from django.db import connection
        from apps.core.db._helpers import rows_to_list
        istanza_str = request.query_params.get("istanza_utility_id")
        # BB `qp_int_optional`: vuoto = assente, un non intero e' un 400 (fino al
        # 2026-10-09 `int()` grezzo, cioe' un 500).
        istanza_utility_id = qp_int_optional(istanza_str, "istanza_utility_id")
        with connection.cursor() as cursor:
            soggetto_id = resolve_soggetto_id(cursor, soggetto_ruolo_id)
        _COLS = """c.id, c.nominativo, c.email, c.telefono, c.cellulare,
                   c.pec, c.note, c.tipo_contatto_id,
                   tc.descrizione AS tipo_contatto_descrizione,
                   c.unita_organizzativa_id, c.istanza_utility_id,
                   (SELECT u.codice FROM config.utilities u
                    WHERE u.id = COALESCE(
                      (SELECT idp.utility_id FROM anagrafiche.istanze_dati_precontrattuali idp
                        WHERE idp.istanza_utility_id = c.istanza_utility_id LIMIT 1),
                      (SELECT ba.utility_id FROM anagrafiche.billing_account ba
                        WHERE ba.istanza_utility_id = c.istanza_utility_id LIMIT 1)
                    )) AS utility_codice"""
        _JOIN = """LEFT JOIN config.tipi_contatti tc ON tc.id = c.tipo_contatto_id"""
        with connection.cursor() as cursor:
            results = []
            tipi_coperti: set[int] = set()
            # Livello 1: contatti ruolo + istanza specifica
            if istanza_utility_id is not None:
                sql_ist = f"""
                    SELECT {_COLS}, 'istanza' AS fonte FROM anagrafiche.contatti c {_JOIN}
                     WHERE c.soggetto_ruolo_id = %s AND c.istanza_utility_id = %s ORDER BY c.id
                """  # noqa: S608 — _COLS/_JOIN letterali locali, valori come parametri
                cursor.execute(sql_ist, [soggetto_ruolo_id, istanza_utility_id])
                l1 = rows_to_list(cursor)
                results.extend(l1)
                tipi_coperti.update(
                    c["tipo_contatto_id"] for c in l1
                    if c["tipo_contatto_id"] is not None
                )
            # Livello 2: contatti ruolo senza istanza (generici del ruolo)
            sql_ruolo = f"""
                SELECT {_COLS}, 'ruolo' AS fonte FROM anagrafiche.contatti c {_JOIN}
                 WHERE c.soggetto_ruolo_id = %s AND c.istanza_utility_id IS NULL ORDER BY c.id
            """  # noqa: S608 — _COLS/_JOIN letterali locali, valori come parametri
            cursor.execute(sql_ruolo, [soggetto_ruolo_id])
            l2 = rows_to_list(cursor)
            for c in l2:
                tipo = c["tipo_contatto_id"]
                if tipo is not None and tipo not in tipi_coperti:
                    results.append(c)
                    tipi_coperti.add(tipo)
            # Livello 3: contatti soggetto (fallback)
            sql_sogg = f"""
                SELECT {_COLS}, 'soggetto' AS fonte FROM anagrafiche.contatti c {_JOIN}
                 WHERE c.soggetto_id = %s::uuid AND c.soggetto_ruolo_id IS NULL ORDER BY c.id
            """  # noqa: S608 — _COLS/_JOIN letterali locali, valori come parametri
            cursor.execute(sql_sogg, [soggetto_id])
            l3 = rows_to_list(cursor)
            for c in l3:
                tipo = c["tipo_contatto_id"]
                if tipo is not None and tipo not in tipi_coperti:
                    results.append(c)
                    tipi_coperti.add(tipo)
        # Separa per fonte per la UI
        contatti_editabili = [c for c in results if c["fonte"] in ('istanza', 'ruolo')]
        contatti_readonly = [c for c in results if c["fonte"] == 'soggetto']
        return success_response({
            "contatti_ruolo": contatti_editabili,
            "contatti_soggetto": contatti_readonly,
        })

    @extend_schema(
        request=inline_serializer(name="RuoloContattoCreateReq", fields={
            "nominativo": serializers.CharField(),
            "email": serializers.CharField(required=False),
            "telefono": serializers.CharField(required=False),
            "tipo_contatto_id": serializers.IntegerField(),
            "istanza_utility_id": serializers.IntegerField(required=False),
        }),
        responses={200: inline_serializer(name="RuoloContattoCreateResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Crea contatto associato al ruolo (`SoggettiService.create_contatto_ruolo`).
    def post(self, request: Request, soggetto_ruolo_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda p: SoggettiService().create_contatto_ruolo(soggetto_ruolo_id, p),
        )


# =================================================================
# Contatto ruolo — dettaglio (PATCH, DELETE)
# =================================================================

class RuoloContattiDetailView(DomainAPIView):
    """PATCH aggiorna, DELETE elimina contatto del ruolo."""
    area_funzionale = "anagrafiche"

    @extend_schema(
        request=inline_serializer(name="RuoloContattoUpdateReq", fields={
            "nominativo": serializers.CharField(required=False),
            "email": serializers.CharField(required=False),
        }),
        responses={200: inline_serializer(name="RuoloContattoUpdateResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Aggiorna contatto con ownership check sul ruolo.
    def patch(self, request: Request, soggetto_ruolo_id: int, contatto_id: int) -> JsonResponse:
        # Dal service (2026-09-26): e' li' che si validano le chiavi del payload.
        return success_response(
            SoggettiService().update_contatto_ruolo(soggetto_ruolo_id, contatto_id, corpo_oggetto(request))
        )

    @extend_schema(
        responses={200: inline_serializer(name="RuoloContattoDeleteResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Elimina contatto con ownership check sul ruolo.
    def delete(self, request: Request, soggetto_ruolo_id: int, contatto_id: int) -> JsonResponse:
        from django.db import connection
        sql = """
            DELETE FROM anagrafiche.contatti
             WHERE id = %s AND soggetto_ruolo_id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [contatto_id, soggetto_ruolo_id])
            deleted = cursor.rowcount > 0
        ErrorManager.require(deleted, code=E_ANAG_NOT_FOUND,
                             message="Contatto non trovato o non appartiene al ruolo.")
        return success_response({"deleted": True})
