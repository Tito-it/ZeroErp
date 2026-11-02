# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I pezzi che i moduli di view del dominio `magazzino` condividono —
#        l'area funzionale, la risposta generica OpenAPI, i parametri di lista
#        offset-based, il parametro `formato` e le risposte dell'export, le
#        etichette dei filtri per l'intestazione del file.
# Note: Stampo `magazzino/services/_helpers.py`: materiale INTERNO del dominio.
#       Nato il 2026-09-21 alla seconda occorrenza (`views_anagrafiche.py`
#       accanto a `views.py`).
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date

from drf_spectacular.utils import OpenApiParameter, inline_serializer
from rest_framework import serializers

from apps.core.api.constants import DEFAULT_LIMIT, MAX_LIMIT
from apps.core.api.openapi_params import descrizione_order_by

AREA = "magazzino"

RISPOSTA_GENERICA = inline_serializer(
    name="MagazzinoRispostaGenerica",
    fields={
        "data": serializers.DictField(),
        "meta": serializers.DictField(required=False),
    },
)


# Scopo: i parametri di lista offset-based dichiarati una volta.
def params_lista(colonne: dict[str, str], nota: str) -> list[OpenApiParameter]:
    return [
        OpenApiParameter(
            name="order_by", type=str, location=OpenApiParameter.QUERY, required=False,
            description=descrizione_order_by(colonne, nota),
        ),
        OpenApiParameter(
            name="order_dir", type=str, location=OpenApiParameter.QUERY, required=False,
            description="asc | desc (le colonne data partono DESC).",
        ),
        OpenApiParameter(
            name="limit", type=int, location=OpenApiParameter.QUERY, required=False,
            description=f"Righe per pagina (default {DEFAULT_LIMIT}, max {MAX_LIMIT}).",
        ),
        OpenApiParameter(
            name="offset", type=int, location=OpenApiParameter.QUERY, required=False,
        ),
    ]


PARAM_FORMATO = OpenApiParameter(
    name="formato", type=str, location=OpenApiParameter.QUERY, required=True,
    description="csv | xlsx. ⚠️ `formato`, non `format`: quello e' un parametro magico di DRF.",
)

RISPOSTE_EXPORT = {
    (200, "text/csv"): bytes,
    (200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): bytes,
}


# Scopo: i filtri applicati, per l'intestazione del file (riga `# Filtri
#        applicati:` del CSV, foglio «Filtri applicati» dell'XLSX).
# ⚠️ Le date si passano in ISO: il renderer le serializza con `json.dumps`
#    senza `default=`, e un `date` lo farebbe fallire — cioe' un export con un
#    filtro di data sarebbe un 500 su un caso che il contratto ammette.
def filtri_label(filtri: dict) -> dict:
    return {
        k: (v.isoformat() if isinstance(v, date) else v)
        for k, v in filtri.items()
        if v is not None
    }
