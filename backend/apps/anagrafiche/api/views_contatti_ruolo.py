# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API views contatti a livello ruolo — CRUD contatti
#        con soggetto_ruolo_id. Riusa SoggettiRepository per le
#        operazioni base, aggiungendo il filtro/set del ruolo.
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.success_responses import success_response
from apps.core.services.error_manager import ErrorManager
from apps.anagrafiche.db.soggetti_repository import SoggettiRepository
from apps.anagrafiche.error_codes import E_ANAG_NOT_FOUND


_repo = SoggettiRepository()


# =================================================================
# Contatti ruolo — lista + crea
# =================================================================

class RuoloContattiView(DomainAPIView):
    """GET lista contatti del ruolo, POST crea contatto per il ruolo."""
    area_funzionale = "anagrafiche"

    @extend_schema(
        responses={200: inline_serializer(name="RuoloContattiListResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Lista contatti con cascata a 3 livelli per tipo_contatto_id:
    #        1. Contatti ruolo + utility specifica → VINCE (fonte='utility')
    #        2. Contatti ruolo + utility NULL      → fallback ruolo (fonte='ruolo')
    #           mostrati solo se tipo non coperto dal livello 1
    #        3. Contatti soggetto (ruolo NULL)      → fallback soggetto (fonte='soggetto')
    #           mostrati solo se tipo non coperto dai livelli 1 e 2
    #        Query param opzionale: utility_id (se assente, nessun filtro utility).
    def get(self, request: Request, soggetto_ruolo_id: int) -> JsonResponse:
        from django.db import connection
        from apps.core.db._helpers import rows_to_list
        utility_id = request.query_params.get("utility_id")
        utility_id = int(utility_id) if utility_id else None
        # Recupera soggetto_id dal ruolo
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT soggetto_id FROM anagrafiche.soggetti_ruoli WHERE id = %s",
                [soggetto_ruolo_id])
            row = cursor.fetchone()
        ErrorManager.require(row is not None, code=E_ANAG_NOT_FOUND,
                             message="Ruolo non trovato.")
        assert row is not None
        soggetto_id = str(row[0])
        _COLS = """c.id, c.nominativo, c.email, c.telefono, c.cellulare,
                   c.pec, c.note, c.tipo_contatto_id,
                   tc.descrizione AS tipo_contatto_descrizione,
                   c.unita_organizzativa_id, c.utility_id,
                   u.codice AS utility_codice"""
        _JOIN = """LEFT JOIN config.tipi_contatti tc ON tc.id = c.tipo_contatto_id
                   LEFT JOIN config.utilities u ON u.id = c.utility_id"""
        with connection.cursor() as cursor:
            results = []
            tipi_coperti = set()
            # Livello 1: contatti ruolo + utility specifica
            if utility_id is not None:
                sql_util = f"""
                    SELECT {_COLS}, 'utility' AS fonte FROM anagrafiche.contatti c {_JOIN}
                     WHERE c.soggetto_ruolo_id = %s AND c.utility_id = %s ORDER BY c.id
                """
                cursor.execute(sql_util, [soggetto_ruolo_id, utility_id])
                l1 = rows_to_list(cursor)
                results.extend(l1)
                tipi_coperti.update(c["tipo_contatto_id"] for c in l1 if c["tipo_contatto_id"])
            # Livello 2: contatti ruolo senza utility (generici del ruolo)
            sql_ruolo = f"""
                SELECT {_COLS}, 'ruolo' AS fonte FROM anagrafiche.contatti c {_JOIN}
                 WHERE c.soggetto_ruolo_id = %s AND c.utility_id IS NULL ORDER BY c.id
            """
            cursor.execute(sql_ruolo, [soggetto_ruolo_id])
            l2 = rows_to_list(cursor)
            for c in l2:
                if c["tipo_contatto_id"] not in tipi_coperti:
                    results.append(c)
                    if c["tipo_contatto_id"]:
                        tipi_coperti.add(c["tipo_contatto_id"])
            # Livello 3: contatti soggetto (fallback)
            sql_sogg = f"""
                SELECT {_COLS}, 'soggetto' AS fonte FROM anagrafiche.contatti c {_JOIN}
                 WHERE c.soggetto_id = %s::uuid AND c.soggetto_ruolo_id IS NULL ORDER BY c.id
            """
            cursor.execute(sql_sogg, [soggetto_id])
            l3 = rows_to_list(cursor)
            for c in l3:
                if c["tipo_contatto_id"] not in tipi_coperti:
                    results.append(c)
                    if c["tipo_contatto_id"]:
                        tipi_coperti.add(c["tipo_contatto_id"])
        # Separa per fonte per la UI
        contatti_editabili = [c for c in results if c["fonte"] in ('utility', 'ruolo')]
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
        }),
        responses={200: inline_serializer(name="RuoloContattoCreateResp", fields={"data": serializers.DictField()})},
    )
    # Scopo: Crea contatto associato al ruolo.
    #        Recupera soggetto_id dal ruolo per popolare la FK obbligatoria.
    def post(self, request: Request, soggetto_ruolo_id: int) -> JsonResponse:
        def _handler(payload):
            from django.db import connection
            from apps.core.db._helpers import row_to_dict
            # Recupera soggetto_id dal ruolo
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT soggetto_id FROM anagrafiche.soggetti_ruoli WHERE id = %s",
                    [soggetto_ruolo_id])
                row = cursor.fetchone()
            ErrorManager.require(row is not None, code=E_ANAG_NOT_FOUND,
                                 message="Ruolo non trovato.")
            assert row is not None
            soggetto_id = str(row[0])
            # Crea contatto con soggetto_ruolo_id e utility_id opzionale
            utility_id = payload.get("utility_id")
            if utility_id is not None:
                utility_id = int(utility_id)
            result = _repo.crea_contatto(
                soggetto_id,
                nominativo=payload.get("nominativo", ""),
                email=payload.get("email"),
                telefono=payload.get("telefono"),
                cellulare=payload.get("cellulare"),
                pec=payload.get("pec"),
                tipo_contatto_id=payload.get("tipo_contatto_id"),
                unita_organizzativa_id=payload.get("unita_organizzativa_id"),
                note=payload.get("note"),
                soggetto_ruolo_id=soggetto_ruolo_id,
                utility_id=utility_id,
            )
            return result
        return handle_post_json(request, handler=_handler)


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
        updated = _repo.update_contatto(contatto_id, request.data, soggetto_ruolo_id=soggetto_ruolo_id)
        ErrorManager.require(updated, code=E_ANAG_NOT_FOUND,
                             message="Contatto non trovato o non appartiene al ruolo.")
        return success_response({"updated": True})

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
