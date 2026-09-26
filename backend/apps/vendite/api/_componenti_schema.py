# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Lo schema OpenAPI UNICO della PATCH di un componente BoM, per i cinque
#        documenti (preventivi, contratti, offerte, ordini, ddt). Si LEGGE dal
#        contratto dell'operatore `COMPONENTE_PATCH_OPERATORE`, non si ricopia.
# Note: ⛔ Estratto il 2026-09-26 (regola del 2, ok Tid). Fino a quel giorno lo
#       schema era scritto a mano in tre view — e in tutte e tre pubblicava
#       ancora `iva_id`, `origine_prezzo`, `stato_approvazione_prezzo`, ...,
#       campi che il service rifiuta con un 400 dal giorno in cui il contratto
#       si e' ristretto — e mancava in ordini e ddt. Un client generato dalla
#       doc li avrebbe mandati e avrebbe ricevuto un 400 non documentato.
#       ⭐ `_CAMPI` descrive il TIPO di ogni chiave; le chiavi le decide il
#       contratto. Una chiave del contratto senza tipo qui e' un errore
#       all'import, e il presidio `test_componenti_patch_operatore` confronta i
#       due insiemi: non possono divergere in silenzio.
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Callable

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

from apps.vendite.services._componenti_service_helpers import COMPONENTE_PATCH_OPERATORE

# Scopo: il tipo di ogni chiave del contratto. `allow_null` dove il dominio
#        ammette di togliere il valore (il prezzo solo nei ddt: lo decide il
#        service, lo schema non lo ripete).
_CAMPI: dict[str, Callable[[], serializers.Field]] = {
    "prezzo_unitario": lambda: serializers.DecimalField(
        max_digits=22, decimal_places=10, required=False, allow_null=True,
    ),
    "attivo": lambda: serializers.BooleanField(required=False),
    "meta": lambda: serializers.JSONField(required=False, allow_null=True),
}

_senza_tipo = sorted(COMPONENTE_PATCH_OPERATORE - _CAMPI.keys())
if _senza_tipo:
    raise RuntimeError(f"_componenti_schema: chiavi del contratto senza tipo: {_senza_tipo}")

COMPONENTE_PATCH_REQUEST = inline_serializer(
    name="VenditeComponentePatchReq",
    fields={k: _CAMPI[k]() for k in sorted(COMPONENTE_PATCH_OPERATORE)},
)
