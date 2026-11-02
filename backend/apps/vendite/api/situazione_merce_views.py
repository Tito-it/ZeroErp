# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Factory della API view "situazione merce" dei documenti vendita
#        (pannello del cantiere 2, brief-design-situazione-merce-ordine).
#        Estrazione regola-del-2 autorizzata da Tid il 2026-08-17: i domini
#        sono DUE dal primo giorno — il §5.1 del brief pannello decide
#        «sull'ordine E sul DDT», quindi la seconda copia nascerebbe nello
#        stesso commit della prima. Stessa forma di
#        `build_riepilogo_iva_view` e `build_passaggi_view`.
#
#        Cambia SOLO il filtro: per ordine o per DDT. Sono due letture della
#        stessa fonte, non due fonti — ed e' testualmente la richiesta BE-1
#        del brief della partita generalizzata (§19.1).
#
#        Testabilita': il service arriva come CLOSURE definita qui sotto, che
#        legge il global di modulo a call-time — i patch dei test su
#        `apps.vendite.services.vendite_service.get_situazione_merce`
#        continuano a funzionare (stesso contratto di riepilogo_iva_views).
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.success_responses import success_response
from apps.vendite.services import vendite_service

# Docstring condivisa: il contratto e' lo stesso per i due domini, e il delta
# (quale documento) e' gia' nel path. Ripeterla due volte la farebbe divergere.
_DOC_COMUNE = """Situazione della merce del documento (sola lettura).

Un round-trip solo, quattro sezioni piu' il contesto:

* `contesto` — `"ORDINE_VENDITA"` o `"DDT_VENDITA"` (i codici di
  `config.sorgenti`; fino al 2026-10-19 `"ORDINE"` o `"DDT"`): **quale delle
  due liste e' il saldo di questo documento**. Dedurlo dal fatto che `righe_ordine` sia vuota non e' piu'
  possibile (e' popolata su entrambi i lati), e sbagliarlo significa contare sul
  DDT il saldo dell'intera riga d'ordine invece che di questa spedizione.
* `righe_ordine` — il riassunto per riga d'ordine:
  ordinato, consegnato, reso, tenuti, fatturato, `fatturato_anticipato`,
  `da_spedire` e lo `stato` gia' tradotto. Comprende le righe **mai spedite**
  (`stato = 'NON_SPEDITA'`), che il contatore non contiene affatto.
  Sul lato **DDT** contiene le righe d'ordine che *quella spedizione ha
  toccato* — piu' corta delle `partite` quando una riga di DDT non ha origine
  ordine.
* `partite` — le partite di merce (grana: riga di DDT), con `origine`,
  `sospetto_duplicato_ordine` e lo `stato` della partita.
* `accrediti` — la coda «da accreditare» del documento, con l'etichetta
  DOVUTA|FACOLTATIVA identica a quella della coda di lavoro.
* `riconsegne` — la coda «da ri-consegnare» del documento, col residuo aperto.

⚠️ `differenza` puo' essere **null**, e non significa zero: significa che il
conto non si applica (riga mai spedita, causale di trasporto non fatturabile,
conto non calcolabile). Chi consuma non deve fare `COALESCE(..., 0)`.

⚠️ `fatturato_anticipato` **non e' un accredito**: e' merce fatturata e non
ancora uscita. Sommarlo alla differenza rimette il falso allarme che il modello
della partita generalizzata ha tolto.

Scope: la testata e' il cancello (RLS su `vendite.ordini` / `vendite.ddt`). Un
documento fuori perimetro risponde 404, indistinguibile da uno inesistente.
"""


# Scopo: Costruisce la view GET situazione-merce per un dominio documento.
#        Parametri:
#         - schema_prefix: prefisso nomi OpenAPI (es. "Ordine" ->
#                          "OrdineSituazioneMerceResponse")
#         - url_kwarg:     nome del kwarg URL del documento (es. "ordine_id")
#         - get_call:      closure dominio (documento_id) -> dict sezioni
#         - model_permission: oggetto del catalogo permessi del documento
#                          (es. ("vendite", "ordine")): il pannello e' una
#                          parte dell'oggetto e ne chiede il livello
#                          (brief-db-be-fe-catalogo-oggetti-permessi §3.2).
#                          Obbligatorio: i due documenti che lo servono sono
#                          entrambi oggetti del catalogo.
def build_situazione_merce_view(
    *,
    schema_prefix: str,
    url_kwarg: str,
    get_call: Callable[[int], dict[str, Any]],
    model_permission: tuple[str, str],
) -> type[DomainAPIView]:
    class _SituazioneMerceView(DomainAPIView):
        area_funzionale = "vendite"

        @extend_schema(
            responses={200: inline_serializer(
                name=f"{schema_prefix}SituazioneMerceResponse",
                fields={"data": inline_serializer(
                    name=f"{schema_prefix}SituazioneMerceData",
                    fields={
                        "contesto": serializers.CharField(),
                        "righe_ordine": serializers.ListField(
                            child=serializers.DictField()
                        ),
                        "partite": serializers.ListField(
                            child=serializers.DictField()
                        ),
                        "accrediti": serializers.ListField(
                            child=serializers.DictField()
                        ),
                        "riconsegne": serializers.ListField(
                            child=serializers.DictField()
                        ),
                    },
                )},
            )},
        )
        # Scopo: Restituisce via GET la situazione merce del documento.
        def get(self, request: Request, **kwargs: int) -> JsonResponse:
            return success_response(get_call(int(kwargs[url_kwarg])))

    _SituazioneMerceView.__doc__ = _DOC_COMUNE
    _SituazioneMerceView.__name__ = f"Api{schema_prefix}SituazioneMerce"
    _SituazioneMerceView.__qualname__ = _SituazioneMerceView.__name__
    _SituazioneMerceView.model_permission = model_permission
    return _SituazioneMerceView


# Le due view di dominio. Il delta e' il solo filtro — che e' il punto della
# richiesta BE-1: «sono due filtri, non due letture».
ApiOrdineSituazioneMerce = build_situazione_merce_view(
    schema_prefix="Ordine",
    url_kwarg="ordine_id",
    get_call=lambda doc_id: vendite_service.get_situazione_merce(ordine_id=doc_id),
    model_permission=("vendite", "ordine"),
)

ApiDdtSituazioneMerce = build_situazione_merce_view(
    schema_prefix="Ddt",
    url_kwarg="ddt_id",
    get_call=lambda doc_id: vendite_service.get_situazione_merce(ddt_id=doc_id),
    model_permission=("vendite", "ddt"),
)
