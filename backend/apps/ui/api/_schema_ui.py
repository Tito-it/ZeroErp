# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il dizionario dei TIPI delle chiavi dei contratti di amministrazione
#        delle liste configurabili (definizioni, colonne, preset), per il
#        building block `core/api/schema_da_contratto`.
# Note: ⭐ I tipi vengono dalle colonne (docs/it/dbzero/ui/tabelle/lista_*.md).
#       Gli enum del DB (`ambito`, `tipo_colonna`, `tipo_dato`,
#       `allineamento`) sono testo: i valori li dice il DB, non questo file.
# ------------------------------------------------------------

from __future__ import annotations

from apps.core.api.schema_da_contratto import Tipi, booleano, intero, json, testo

TIPI_UI: Tipi = {
    # ── comuni ───────────────────────────────────────────────
    "codice": (testo, False),
    "descrizione": (testo, False),
    "attivo": (booleano, False),
    # ── definizione ──────────────────────────────────────────
    "schema_dati": (testo, False),
    "vista_sql": (testo, True),
    "note": (testo, True),
    # ── preset ───────────────────────────────────────────────
    "lista_id": (intero, False),
    "ambito": (testo, False),
    "profilo_accesso_id": (intero, True),
    "emittente_fiscale_id": (intero, True),
    "is_default": (booleano, False),
    "pagina_dimensione": (intero, True),
    "ordinamento_default": (json, True),
    "filtri_default": (json, True),
    # ── colonna ──────────────────────────────────────────────
    "etichetta": (testo, False),
    "etichetta_estesa": (testo, True),
    "etichetta_i18n_key": (testo, True),
    "campo_sorgente": (testo, True),
    "tipo_colonna": (testo, False),
    "tipo_dato": (testo, False),
    "formato": (testo, True),
    "larghezza_default": (intero, True),
    "ordine_default": (intero, False),
    "allineamento": (testo, False),
    "gruppo": (testo, True),
    "gruppo_ordine": (intero, True),
    "filtrabile": (booleano, False),
    "ordinabile": (booleano, False),
    "esportabile": (booleano, False),
    "ricercabile_full": (booleano, False),
    "sensibile": (booleano, False),
}
