# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Factory della API view "passaggi" (genealogia/lineage) dei
#        documenti vendita + le 6 view di dominio. Il flusso e' identico
#        per tutti i domini (cambiano solo nomi OpenAPI, kwarg URL e
#        tipo sorgente): stessa architettura di riepilogo_iva_views.
#
#        Testabilita': la view risolve `vendite_service` come modulo a
#        call-time — i patch dei test su
#        `apps.vendite.services.vendite_service.get_documento_passaggi`
#        continuano a funzionare.
# ------------------------------------------------------------

from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.config.sorgenti import (
    SORGENTE_COMMESSA,
    SORGENTE_CONTRATTO,
    SORGENTE_DDT_VENDITA,
    SORGENTE_FATTURA,
    SORGENTE_OFFERTA_COMMERCIALE,
    SORGENTE_ORDINE_VENDITA,
    SORGENTE_PREVENTIVO,
    SORGENTE_RESO_VENDITA,
)
from apps.core.api.base_views import DomainAPIView
from apps.core.api.success_responses import success_response
from apps.vendite.services import vendite_service


# Scopo: Costruisce la view GET /vendite/<dominio>/<id>/passaggi/ per un
#        dominio documento. Parametri:
#         - schema_prefix: prefisso nomi OpenAPI (es. "Ordine" ->
#                          "OrdinePassaggiResponse")
#         - url_kwarg:     nome del kwarg URL del documento (es. "ordine_id")
#         - tipo_codice:   codice_interno config.sorgenti del dominio
#         - model_permission: oggetto del catalogo permessi del documento
#                          (es. ("vendite", "preventivo")): la view e' una
#                          parte dell'oggetto e ne chiede il livello
#                          (brief-db-be-fe-catalogo-oggetti-permessi §3.2).
#                          None = solo l'area.
def build_passaggi_view(
    *,
    schema_prefix: str,
    url_kwarg: str,
    tipo_codice: str,
    model_permission: tuple[str, str] | None = None,
) -> type[DomainAPIView]:
    class _PassaggiView(DomainAPIView):
        area_funzionale = "vendite"

        @extend_schema(
            responses={200: inline_serializer(
                name=f"{schema_prefix}PassaggiResponse",
                fields={"data": inline_serializer(
                    name=f"{schema_prefix}PassaggiData",
                    fields={
                        "nodo": serializers.DictField(),
                        "pratica": serializers.DictField(allow_null=True),
                        "frontiera": serializers.DictField(allow_null=True),
                        "avanti": serializers.ListField(
                            child=serializers.DictField()),
                        "indietro": serializers.ListField(
                            child=serializers.DictField()),
                    },
                )},
            )},
        )
        # Scopo: Restituisce via GET la genealogia del documento (nodo +
        #        pratica + frontiera + catena avanti/indietro).
        def get(self, request: Request, **kwargs: int) -> JsonResponse:
            return success_response(
                vendite_service.get_documento_passaggi(
                    tipo_codice, int(kwargs[url_kwarg])
                )
            )

    _PassaggiView.__doc__ = f"""GET /api/v1/vendite/.../<id>/passaggi/

    Genealogia/lineage del documento ({tipo_codice}): pratica collegata,
    frontiera (documento piu' prossimo in esecuzione) e catena completa dei
    passaggi in entrambe le direzioni (origine + destinazioni), dal grafo
    vendite.fn_documento_lineage / fn_documento_lineage_sintesi (RLS invoker).
    I rami di RITORNO arrivano con is_ramo_inverso=true ed esclusi dalla
    frontiera forward: arco R (DDT->Reso, merce che torna) e arco N (fattura
    rettificata->nota di credito, valore che torna).
    """
    _PassaggiView.__name__ = f"Api{schema_prefix}Passaggi"
    _PassaggiView.__qualname__ = _PassaggiView.__name__
    if model_permission is not None:
        _PassaggiView.model_permission = model_permission
    return _PassaggiView


# Le view di dominio (decisione P-1 brief lineage: endpoint per-dominio, FE
# ignaro della convenzione key_selector): 6 documenti + commessa (Fase C).
ApiPreventivoPassaggi = build_passaggi_view(
    schema_prefix="Preventivo",
    url_kwarg="preventivo_id",
    tipo_codice=SORGENTE_PREVENTIVO,
    model_permission=("vendite", "preventivo"),
)

ApiOffertaPassaggi = build_passaggi_view(
    schema_prefix="Offerta",
    url_kwarg="offerta_id",
    tipo_codice=SORGENTE_OFFERTA_COMMERCIALE,
    model_permission=("vendite", "offerta_commerciale"),
)

ApiOrdinePassaggi = build_passaggi_view(
    schema_prefix="Ordine",
    url_kwarg="ordine_id",
    tipo_codice=SORGENTE_ORDINE_VENDITA,
    model_permission=("vendite", "ordine"),
)

ApiContrattoPassaggi = build_passaggi_view(
    schema_prefix="Contratto",
    url_kwarg="contratto_id",
    tipo_codice=SORGENTE_CONTRATTO,
    model_permission=("vendite", "contratto"),
)

ApiDdtPassaggi = build_passaggi_view(
    schema_prefix="Ddt",
    url_kwarg="ddt_id",
    tipo_codice=SORGENTE_DDT_VENDITA,
    model_permission=("vendite", "ddt"),
)

ApiResoPassaggi = build_passaggi_view(
    schema_prefix="Reso",
    url_kwarg="reso_id",
    tipo_codice=SORGENTE_RESO_VENDITA,
    model_permission=("vendite", "reso"),
)

# Fattura (2026-08-21): la decisione Q4 la teneva fuori come «capolinea senza
# superficie propria». Il drawer di consultazione esiste dal 2026-07-29 e
# l'arco N (fattura rettificata -> nota di credito) le da' un discendente,
# quindi nessuna delle due meta' di quella frase regge piu'.
# ⚠️ Qui il pannello si legge AL CONTRARIO degli altri sei: la frontiera di una
# fattura e' sempre se' stessa (nessun arco forward uscente), e cio' che serve
# e' la direzione INDIETRO — da quali commesse, ordini e preventivi viene.
ApiFatturaPassaggi = build_passaggi_view(
    schema_prefix="Fattura",
    url_kwarg="fattura_id",
    tipo_codice=SORGENTE_FATTURA,
    model_permission=("vendite", "fattura"),
)

# Commessa (Fase C, genealogia inversa): la commessa non ha lista/CRUD propria
# ma il suo nodo lineage è consultabile — le tappe COMMESSA nei pannelli
# "Passaggi" dei documenti aprono un drawer leggero su questo endpoint.
ApiCommessaPassaggi = build_passaggi_view(
    schema_prefix="Commessa",
    url_kwarg="commessa_id",
    tipo_codice=SORGENTE_COMMESSA,
)
