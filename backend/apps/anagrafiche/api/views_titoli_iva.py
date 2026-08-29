# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API dei TITOLI IVA del soggetto (I7 / D10 di
#        brief-db-be-iva-risolutore-e-regime-cliente).
#        Grammatica di `api.md`: nessun verbo nel path, il metodo HTTP dice
#        l'operazione. Le rotte sono annidate sotto il soggetto perche' il
#        titolo E' del soggetto (D10-bis: proprietario il soggetto, destinatario
#        l'emittente).
#
# ⚠️ Il perimetro emittente lo fa la RLS sulle tre tabelle, non queste view.
#    L'ownership check «il titolo e' di QUESTO soggetto» sta nel service, ed e'
#    un'altra domanda: la RLS dice cosa l'operatore puo' vedere, l'ownership dice
#    che l'id nel path e quello nella riga combaciano.
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.anagrafiche.services.titoli_iva_service import TitoliIvaService
from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.success_responses import success_response

_AREA = "anagrafiche"
# ⚠️ Stesso oggetto di permesso del soggetto: un titolo IVA e' un dato
#    anagrafico del soggetto, non un'entita' con un suo ciclo autorizzativo.
#    Se un giorno servisse piu' fine, e' il tema dei permessi v3 (sotto-oggetti).
_MODEL = ("anagrafiche", "soggetto")


# =================================================================
# Titoli IVA del soggetto — lista + crea
# =================================================================

class SoggettoTitoliIvaView(DomainAPIView):
    """GET lista titoli IVA del soggetto, POST registra un titolo."""
    area_funzionale = _AREA
    model_permission = _MODEL

    @extend_schema(
        responses={200: inline_serializer(
            name="SoggettoTitoliIvaListResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Titoli IVA del soggetto. Ogni riga porta `residuo` (tetto meno
    #        imponibile gia' applicato) e `ambito_incompleto` (Q2).
    def get(self, request: Request, soggetto_id: str) -> JsonResponse:
        results = TitoliIvaService().list_titoli_soggetto(soggetto_id)
        return success_response({"results": results})

    @extend_schema(
        request=inline_serializer(name="SoggettoTitoloIvaCreateReq", fields={
            "emittente_fiscale_id": serializers.IntegerField(),
            "tipo_titolo_iva_id": serializers.IntegerField(),
            "iva_id": serializers.IntegerField(),
            "ambito": serializers.CharField(required=False),
            "valido_dal": serializers.DateField(),
            "valido_al": serializers.DateField(required=False, allow_null=True),
            "protocollo": serializers.CharField(required=False, allow_null=True),
            "data_ricezione": serializers.DateField(required=False, allow_null=True),
            "riferimento": serializers.CharField(required=False, allow_null=True),
            "plafond": serializers.DecimalField(
                max_digits=18, decimal_places=2, required=False, allow_null=True,
            ),
            "note": serializers.CharField(required=False, allow_null=True),
        }),
        responses={200: inline_serializer(
            name="SoggettoTitoloIvaCreateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Registra un titolo IVA per il soggetto.
    def post(self, request: Request, soggetto_id: str) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda p: TitoliIvaService().create_titolo(soggetto_id, p),
        )


# =================================================================
# Titolo IVA — dettaglio, aggiorna, elimina
# =================================================================

class SoggettoTitoliIvaDetailView(DomainAPIView):
    """GET dettaglio (con ambiti e movimenti), PATCH aggiorna, DELETE elimina."""
    area_funzionale = _AREA
    model_permission = _MODEL

    @extend_schema(
        responses={200: inline_serializer(
            name="SoggettoTitoloIvaDetailResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Dettaglio del titolo, con le righe di ambito e il registro.
    def get(self, request: Request, soggetto_id: str, titolo_id: int) -> JsonResponse:
        return success_response(
            TitoliIvaService().get_titolo(soggetto_id, titolo_id),
        )

    @extend_schema(
        request=inline_serializer(name="SoggettoTitoloIvaUpdateReq", fields={
            "tipo_titolo_iva_id": serializers.IntegerField(required=False),
            "iva_id": serializers.IntegerField(required=False),
            "ambito": serializers.CharField(required=False),
            "valido_dal": serializers.DateField(required=False),
            "valido_al": serializers.DateField(required=False, allow_null=True),
            "protocollo": serializers.CharField(required=False, allow_null=True),
            "data_ricezione": serializers.DateField(required=False, allow_null=True),
            "riferimento": serializers.CharField(required=False, allow_null=True),
            "plafond": serializers.DecimalField(
                max_digits=18, decimal_places=2, required=False, allow_null=True,
            ),
            "attivo": serializers.BooleanField(required=False),
            "note": serializers.CharField(required=False, allow_null=True),
        }),
        responses={200: inline_serializer(
            name="SoggettoTitoloIvaUpdateResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiorna il titolo.
    # ⛔ `emittente_fiscale_id` NON e' nel serializer, ed e' la decisione Q5:
    #    spostare il destinatario sposterebbe sotto un altro fornitore anche il
    #    plafond gia' consumato, perche' i movimenti sono attaccati al titolo.
    def patch(self, request: Request, soggetto_id: str, titolo_id: int) -> JsonResponse:
        return success_response(
            TitoliIvaService().update_titolo(soggetto_id, titolo_id, request.data),
        )

    @extend_schema(
        responses={200: inline_serializer(
            name="SoggettoTitoloIvaDeleteResp",
            fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Elimina il titolo, ammesso solo senza movimenti (Q6).
    def delete(self, request: Request, soggetto_id: str, titolo_id: int) -> JsonResponse:
        return success_response(
            TitoliIvaService().delete_titolo(soggetto_id, titolo_id),
        )


# =================================================================
# Ambiti del titolo — l'oggetto su cui il titolo si applica (D12)
# =================================================================

class SoggettoTitoloIvaAmbitiView(DomainAPIView):
    """GET righe di ambito, POST aggiunge una riga."""
    area_funzionale = _AREA
    model_permission = _MODEL

    @extend_schema(
        responses={200: inline_serializer(
            name="TitoloIvaAmbitiListResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Righe di ambito del titolo.
    def get(self, request: Request, soggetto_id: str, titolo_id: int) -> JsonResponse:
        results = TitoliIvaService().list_ambiti(soggetto_id, titolo_id)
        return success_response({"results": results})

    @extend_schema(
        request=inline_serializer(name="TitoloIvaAmbitoCreateReq", fields={
            "livello": serializers.CharField(),
            "articolo_id": serializers.UUIDField(required=False, allow_null=True),
            "gruppo_voce_id": serializers.IntegerField(required=False, allow_null=True),
            "tipo_voce_id": serializers.IntegerField(required=False, allow_null=True),
            "note": serializers.CharField(required=False, allow_null=True),
        }),
        responses={200: inline_serializer(
            name="TitoloIvaAmbitoCreateResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Aggiunge una riga di ambito (ARTICOLO / GRUPPO_VOCE / TIPO_VOCE).
    def post(self, request: Request, soggetto_id: str, titolo_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda p: TitoliIvaService().create_ambito(soggetto_id, titolo_id, p),
        )


class SoggettoTitoloIvaAmbitoDetailView(DomainAPIView):
    """DELETE toglie una riga di ambito."""
    area_funzionale = _AREA
    model_permission = _MODEL

    @extend_schema(
        responses={200: inline_serializer(
            name="TitoloIvaAmbitoDeleteResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Toglie una riga di ambito.
    def delete(
        self, request: Request, soggetto_id: str, titolo_id: int, ambito_id: int,
    ) -> JsonResponse:
        return success_response(
            TitoliIvaService().delete_ambito(soggetto_id, titolo_id, ambito_id),
        )


# =================================================================
# Registro movimenti del titolo (D5)
# =================================================================

class SoggettoTitoloIvaMovimentiView(DomainAPIView):
    """GET registro movimenti, POST registra una FORZATURA manuale."""
    area_funzionale = _AREA
    model_permission = _MODEL

    @extend_schema(
        responses={200: inline_serializer(
            name="TitoloIvaMovimentiListResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Il registro del titolo: fatture, note di credito e forzature.
    def get(self, request: Request, soggetto_id: str, titolo_id: int) -> JsonResponse:
        results = TitoliIvaService().list_movimenti(soggetto_id, titolo_id)
        return success_response({"results": results})

    @extend_schema(
        request=inline_serializer(name="TitoloIvaForzaturaCreateReq", fields={
            "imponibile": serializers.DecimalField(max_digits=18, decimal_places=2),
            "data_movimento": serializers.DateField(),
            "motivo": serializers.CharField(),
        }),
        responses={200: inline_serializer(
            name="TitoloIvaForzaturaCreateResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Registra una forzatura manuale sul plafond.
    # ⛔ SOLO forzature (Q3): `FATTURA` e `NOTA_CREDITO` li produce la
    #    fatturazione con I4, dalla primitiva che tiene il lock di D15-bis. Il
    #    guard sta nel service, dove puo' dare il messaggio giusto — qui il
    #    serializer non espone nemmeno `tipo_movimento`.
    def post(self, request: Request, soggetto_id: str, titolo_id: int) -> JsonResponse:
        return handle_post_json(
            request,
            handler=lambda p: TitoliIvaService().create_forzatura(
                soggetto_id, titolo_id, p,
            ),
        )


# =================================================================
# Presidio: i titoli con il plafond sfondato (Q4)
# =================================================================

class TitoliIvaSfondatiView(DomainAPIView):
    """GET i titoli il cui consumo ha superato il tetto."""
    area_funzionale = _AREA
    model_permission = _MODEL

    @extend_schema(
        responses={200: inline_serializer(
            name="TitoliIvaSfondatiResp", fields={"data": serializers.DictField()},
        )},
    )
    # Scopo: Lista di presidio, cross-soggetto.
    # ⭐ Esiste perche' il DB ha deciso di NON bloccare il superamento sulle
    #    forzature: «una forzatura esiste per registrare fatturazioni fuori dal
    #    sistema, e impedire di scriverla impedirebbe di accorgersene». Questa
    #    lista e' l'altra meta' di quella decisione.
    def get(self, request: Request) -> JsonResponse:
        results = TitoliIvaService().list_titoli_sfondati()
        return success_response({"results": results})
