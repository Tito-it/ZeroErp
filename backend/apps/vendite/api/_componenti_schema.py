# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Gli schemi OpenAPI UNICI dei componenti BoM, per i cinque documenti
#        (preventivi, contratti, offerte, ordini, ddt): la PATCH di un
#        componente — che si LEGGE dal contratto dell'operatore
#        `COMPONENTE_PATCH_OPERATORE`, non si ricopia — e il preview dei
#        componenti di una riga composita PRIMA del salvataggio.
# Note: ⛔ Estratto il 2026-09-26 (regola del 2, ok Tid). Fino a quel giorno lo
#       schema era scritto a mano in tre view — e in tutte e tre pubblicava
#       ancora `iva_id`, `origine_prezzo`, `stato_approvazione_prezzo`, ...,
#       campi che il service rifiuta con un 400 dal giorno in cui il contratto
#       si e' ristretto — e mancava in ordini e ddt. Un client generato dalla
#       doc li avrebbe mandati e avrebbe ricevuto un 400 non documentato.
#       ⭐ Le chiavi le decide il contratto, i tipi `_schema_da_contratto`
#       (dal 2026-09-26, quando il meccanismo e' stato esteso a tutte le
#       scritture di ordini, ddt e resi). Una chiave senza tipo e' un errore
#       all'import, e il presidio `test_componenti_patch_operatore` confronta i
#       due insiemi: non possono divergere in silenzio.
#       ⭐ Il preview e' entrato il 2026-09-26 (regola del 2, ok Tid): era
#       scritto uguale in tre view (preventivi, contratti, offerte) e mancava in
#       ordini e ddt, dove il gestore legge le stesse tre chiavi. Lo stesso
#       giorno l'elenco componenti di una riga (`solo_attivi`, tre copie) e il
#       campo `componenti_overrides` della creazione riga.
# ------------------------------------------------------------

from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, inline_serializer
from rest_framework import serializers

from apps.vendite.api._schema_da_contratto import TIPI, schema_da_contratto
from apps.vendite.services._componenti_service_helpers import COMPONENTE_PATCH_OPERATORE

# Le chiavi le decide il contratto; il tipo di ognuna sta nel building block
# `_schema_da_contratto.TIPI` (una chiave senza tipo e' un errore all'import).
COMPONENTE_PATCH_REQUEST = schema_da_contratto(
    "VenditeComponentePatchReq", COMPONENTE_PATCH_OPERATORE,
)

# Il preview dei componenti di una riga (o eccezione) composita, prima del
# salvataggio: l'articolo padre e la quantita' che il dialog sta per salvare.
PREVIEW_COMPONENTI_REQUEST = schema_da_contratto(
    "VenditeRigaPreviewComponentiReq",
    ("articolo_id", "uom_operativa_id", "quantita"),
    obbligatorie=("articolo_id", "quantita"),
)

# I componenti BoM con il prezzo suggerito dal resolver, uno per riga.
PREVIEW_COMPONENTI_RESPONSE = inline_serializer(
    name="VenditeRigaPreviewComponentiResp",
    fields={"data": serializers.ListField(child=serializers.DictField())},
)

# L'elenco dei componenti di una riga (o eccezione): parametro e risposta.
COMPONENTI_LIST_PARAMETERS = [
    OpenApiParameter(
        name="solo_attivi",
        type=bool,
        location=OpenApiParameter.QUERY,
        required=False,
        default=True,
        description=(
            "Default true: solo componenti `attivo=TRUE` (expander della "
            "tabella righe). false: include anche gli opzionali disattivati "
            "(EDIT panel)."
        ),
    ),
]
COMPONENTI_LIST_RESPONSE = inline_serializer(
    name="VenditeRigaComponentiListResp",
    fields={"data": serializers.ListField(child=serializers.DictField())},
)


# Scopo: il campo `componenti_overrides` della creazione di una riga composita
#        (fuori dal contratto delle colonne: non e' una colonna della riga).
#        Fabbrica, non istanza: un campo DRF non si condivide fra serializer.
def componenti_overrides_field() -> serializers.Field:
    fabbrica, nullable = TIPI["componenti_overrides"]
    return fabbrica(required=False, allow_null=nullable)
