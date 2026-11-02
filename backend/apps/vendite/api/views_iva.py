# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Anteprima del trattamento IVA di una riga, per il form.
#        Espone `IvaResolverService.risolvi_anteprima` — cioe' il risolutore
#        DB `vendite.fn_resolve_iva_riga` — cosi' che i tre `*RigaForm.vue`
#        possano SOSTITUIRE l'auto-fill dall'articolo con una risposta che
#        viene dalla sede unica.
#        Nessun side-effect: la funzione DB e' `STABLE` e non consuma plafond.
#
#        Calco di `PricingResolveView` (`/vendite/pricing/resolve/`): stesso
#        mestiere — esporre un resolver DB a un form — stessa area, stessa
#        forma. Non si inventa un pattern dove ce n'e' gia' uno in servizio.
#
#        Brief: docs/it/dev/work-in-progress/
#               brief-be-fe-iva-fase-3-consumatori-risolutore.md (F2-b)
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import get_actor_user_id, handle_post_json
from apps.core.services.error_manager import ErrorManager
from apps.vendite.api._serialize_helpers import serialize_value
from apps.vendite.services._iva_contesto_documento import (
    TIPI_DOCUMENTO_AMMESSI,
    carica_testata,
    contesto_da_testata,
)
from apps.vendite.services.iva_resolver_service import IvaResolverService

_E_VALIDATION = "E_VENDITE_VALIDATION"
_FN = "vendite.views_iva.IvaResolveView"


_IVA_RESOLVE_REQUEST = inline_serializer(
    name="VenditeIvaResolveReq",
    fields={
        "articolo_id": serializers.UUIDField(),
        # ⛔ Niente `data_riferimento` nel contratto, ed e' voluto: la data la
        #    porta la TESTATA. Accettarla dal client vorrebbe dire ammettere
        #    che l'anteprima risponda per una data diversa da quella su cui il
        #    salvataggio calcolera' — cioe' costruire il disaccordo che questo
        #    endpoint esiste per togliere.
        "documento_tipo": serializers.ChoiceField(
            choices=list(TIPI_DOCUMENTO_AMMESSI),
            help_text=(
                "Il documento su cui si sta scrivendo la riga. Da qui il "
                "backend deriva emittente, billing account, utility e data — "
                "cioe' dalla STESSA testata che leggera' al salvataggio."
            ),
        ),
        "documento_id": serializers.IntegerField(),
    },
)


_IVA_RESOLVE_RESPONSE = inline_serializer(
    name="VenditeIvaResolveResp",
    fields={
        "iva_id": serializers.IntegerField(allow_null=True),
        "aliquota": serializers.CharField(allow_null=True),
        "natura_codice": serializers.CharField(allow_null=True),
        "is_reverse_charge": serializers.BooleanField(allow_null=True),
        "esigibilita": serializers.CharField(allow_null=True),
        "split_payment": serializers.BooleanField(allow_null=True),
        "riferimento_normativo": serializers.CharField(allow_null=True),
        "origine": serializers.CharField(allow_null=True),
        "titolo_iva_id": serializers.IntegerField(allow_null=True),
    },
)


class IvaResolveView(DomainAPIView):
    """POST /api/v1/vendite/iva/resolve/ — anteprima del trattamento IVA.

    Area `vendite`, livello LETTURA. Nessuna scrittura: il risolutore e'
    `STABLE` e **non consuma** il plafond — la risposta e' una proiezione.

    ⛔ **Non accetta un imponibile, ed e' una scelta del contratto.** Il
    risolutore, quando gli si passa l'importo, puo' rispondere con DUE
    parti — la quota coperta da un titolo e il resto ad aliquota
    ordinaria. Sui documenti quella spezzatura non si fa (decisione di
    Tid: il titolo si applica a tutta la riga finche' c'e' capienza), e
    il modo piu' solido di tenere quella regola non e' ricordarsela: e'
    non dare al client il parametro con cui romperla. La ripartizione
    vera la calcola la fattura, dove serve e dove il plafond si consuma.
    """

    area_funzionale = "vendite"
    # Una LETTURA che viaggia in POST: permesso di lettura e niente
    # `Idempotency-Key` (brief-be-verifica-documentazione-api §A5).
    post_accesso = "view"

    @extend_schema(
        request=_IVA_RESOLVE_REQUEST,
        responses={200: _IVA_RESOLVE_RESPONSE},
        tags=["vendite"],
        summary="Anteprima trattamento IVA di riga (stadio A + titoli del soggetto)",
    )
    def post(self, request: Request):
        # Scopo: handler chiuso sul request per il ripiego dell'emittente
        #        sull'operatore. Ritorna un dict: `handle_post_json` lo
        #        avvolge in `success_response`.
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            articolo_id = payload.get("articolo_id")
            ErrorManager.require(
                articolo_id is not None,
                code=_E_VALIDATION,
                message="articolo_id obbligatorio.",
                context={"field": "articolo_id"},
            )
            # ⭐ IL CONTESTO VIENE DAL DOCUMENTO, non dal client (decisione di
            #    Tid, opzione «c»). Il form conosce l'id del proprio documento e
            #    nient'altro: e' il backend a sapere quali campi servono al
            #    risolutore, ed e' la STESSA testata che leggera' al
            #    salvataggio. Cosi' cio' che l'operatore vede e cio' che viene
            #    scritto non «coincidono oggi»: vengono dalla stessa fonte.
            # ⛔ L'alternativa scartata era far scendere il billing account come
            #    prop attraverso due livelli di componenti: avrebbe messo nel
            #    client la conoscenza di quali campi servono al risolutore —
            #    cioe' la conoscenza destinata a invecchiare per prima.
            testata = carica_testata(
                documento_tipo=str(payload.get("documento_tipo") or ""),
                documento_id=int(payload.get("documento_id") or 0),
                error_code=_E_VALIDATION,
                function_name=_FN,
            )
            auth_user_id = get_actor_user_id(request)
            ctx = contesto_da_testata(
                testata,
                auth_user_id=auth_user_id,
                error_code=_E_VALIDATION,
                function_name=_FN,
            )

            parte = IvaResolverService().risolvi_anteprima(
                articolo_id=str(articolo_id), **ctx,
            )
            # ⚠️ `quota` NON esce: in anteprima vale sempre `NULL` (la
            #    spezzatura non e' calcolabile senza importo) e un campo
            #    sempre nullo nel payload e' una promessa che qualcuno prima
            #    o poi prova a leggere.
            return {
                k: serialize_value(v) for k, v in parte.items() if k != "quota"
            }

        return handle_post_json(request, handler=_handler)
