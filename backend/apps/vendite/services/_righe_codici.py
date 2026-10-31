# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I codici a vocabolario di una riga di contratto o di offerta
#        (come si eroga, da dove viene la quantita', la periodicita' e
#        l'addebito del canone), letti nella stessa forma sulle due tabelle.
# Note: ⭐ Regola del 2 (2026-10-31, ok Tid). Fino a quel giorno il contratto
#       aveva il suo ciclo locale (strip + maiuscolo, ma '' restava '') e
#       l'offerta passava i valori GREZZI: «trimestrale» o «» passavano sul
#       contratto e finivano nella FK sull'offerta, o viceversa. Una chiave
#       letta in due modi risponde in due modi.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.core.services.payload_helpers import PayloadValidator

# Le colonne di `contratti_righe` e `offerte_commerciali_eccezioni` che
# portano un codice del vocabolario (CHECK o FK verso `config.*`). ⛔ Solo la
# FORMA: il valore ammesso lo giudica il DB, tradotto sul campo dal service.
CAMPI_CODICE_RIGA: tuple[str, ...] = (
    "tipo_erogazione",
    "fonte_quantita_attesa",
    "periodicita",
    "generazione_canone",
)


# Scopo: Normalizza i `CAMPI_CODICE_RIGA` presenti nel payload col BB
#        `PayloadValidator.optional_upper`: strip e maiuscolo; null o vuota →
#        NULL; un non-stringa → 400 col campo. ⭐ Una chiave ASSENTE resta
#        assente: in PATCH «non mandata» non e' «azzerata».
#        Ritorna un payload NUOVO, quello in ingresso non si tocca.
def normalizza_codici_riga(
    validator: PayloadValidator,
    payload: dict[str, Any],
    *,
    function_name: str | None = None,
) -> dict[str, Any]:
    out = dict(payload)
    for campo in CAMPI_CODICE_RIGA:
        if campo in out:
            out[campo] = validator.optional_upper(out, campo, function_name=function_name)
    return out
