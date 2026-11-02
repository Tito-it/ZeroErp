# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Pacchetto registry context_builder. Espone l'interfaccia
#        DocumentContextBuilder e il dict CODE -> Builder consultato
#        dal render service quando deve materializzare il contesto
#        del template per una sorgente di dominio (PREVENTIVO,
#        CONTRATTO, ORDINE, ...). Vincolo: nessuna esecuzione
#        dinamica libera dal DB (Decisione 18 + 74).
# ------------------------------------------------------------

from apps.documenti.services.context_builders.base import (
    DocumentContextBuilder,
)
from apps.documenti.services.context_builders.registry import (
    get_builder,
    get_builder_del_template,
    register_builder,
    registered_codes,
    versione_contesto_registrata,
)

__all__ = [
    "DocumentContextBuilder",
    "get_builder",
    "get_builder_del_template",
    "register_builder",
    "registered_codes",
    "versione_contesto_registrata",
]
