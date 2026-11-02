# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il dizionario dei TIPI delle chiavi dei contratti delle anagrafiche di
#        magazzino (magazzini, ubicazioni, lotti), per il building block
#        `core/api/schema_da_contratto`.
# Note: ⭐ I tipi vengono dalle colonne (docs/it/dbzero/magazzino/tabelle).
# ------------------------------------------------------------

from __future__ import annotations

from apps.core.api.schema_da_contratto import Tipi, booleano, data, intero, json, testo, uuid

TIPI_MAGAZZINO: Tipi = {
    # ── comuni ───────────────────────────────────────────────
    "codice": (testo, False),
    "descrizione": (testo, True),
    "attivo": (booleano, False),
    "meta": (json, True),
    # ── magazzino ────────────────────────────────────────────
    "indirizzo_dettaglio_id": (intero, False),
    "usa_ubicazioni": (booleano, False),
    "predefinito": (booleano, False),
    # ── ubicazione ───────────────────────────────────────────
    "tipo_id": (intero, False),
    "parent_id": (intero, True),
    "area": (testo, True),
    "corsia": (testo, True),
    "scaffale": (testo, True),
    "piano": (testo, True),
    "posizione": (testo, True),
    # ── lotto ────────────────────────────────────────────────
    "articolo_id": (uuid, False),
    "data_arrivo": (data, False),
    "data_scadenza": (data, True),
}
