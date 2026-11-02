# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block per l'estrazione dei filtri lista comuni dei
#        documenti vendita dalla query string (BB estratto 2026-07-13,
#        regola del 2 alla 3a copia: views_ordini/views_ddt/views_resi).
# ------------------------------------------------------------

from typing import Any

from apps.core.api.payload_validators import (
    qp_int_optional,
    qp_iso_date_optional,
    qp_str,
)


# Scopo: Estrae i filtri lista comuni dei documenti vendita (list + export):
#        stato (codice_interno dal LookupSelect FE -> kwarg `stato_codice`),
#        cliente BA, range date (`data_a` in query -> kwarg `data_al`) e,
#        per i domini che la espongono, la utility. NESSUN default temporale
#        backend: il default `data_da` (anno-1) lo applica la UI (evita
#        non-determinismo `date.today()` lato API). Le chiavi del dict
#        combaciano coi kwargs dei `list_*_rows` di dominio (spread `**f`).
def extract_doc_list_filters(qp: Any, *, with_utility: bool = False) -> dict[str, Any]:
    filters: dict[str, Any] = {
        "stato_codice": qp_str(qp.get("stato_codice_interno")),
        "billing_account_id": qp_int_optional(
            qp.get("billing_account_id"), "billing_account_id",
        ),
        "data_da": qp_iso_date_optional(qp.get("data_da"), "data_da"),
        "data_al": qp_iso_date_optional(qp.get("data_a"), "data_a"),
    }
    if with_utility:
        filters["utility_id"] = qp_int_optional(qp.get("utility_id"), "utility_id")
    return filters
