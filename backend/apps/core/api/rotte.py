# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block — le rotte dell'URLconf con la loro classe di view,
#        lette dal PERCORSO REALE (il resolver di Django), comprese, su
#        richiesta, quelle montate solo quando una flag e' accesa.
# Note: ⭐ Estratto il 2026-09-25 (regola del 2, ok Tid): lo stesso cammino
#       sull'URLconf era scritto TRE volte — `test_skip_area_check_registro`,
#       `test_export_lista_codice_pari`, `copertura_doc_api` — e il presidio
#       delle aree a catalogo sarebbe stato la quarta. Le tre copie sono
#       ritirate nello stesso giro.
#       ⭐ Le rotte condizionali: con la flag spenta (in CI l'AI lo e') le rotte
#       non sono nell'URLconf, e un presidio letto dal percorso reale non le
#       vedrebbe — nel caso delle aree, proprio `AIQueryView`, da cui quel
#       presidio nasce. Si leggono da `ROTTE_CONDIZIONALI` nell'URLconf radice,
#       la stessa tupla con cui `urls.py` le monta: una sede sola, quindi una
#       rotta condizionale nuova entra da sola anche qui.
# ------------------------------------------------------------

from __future__ import annotations

import importlib
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.urls import URLPattern, URLResolver, get_resolver


# Scopo: una rotta servita. `percorso` e' il pattern composto come lo compone
#        il resolver (senza `/` iniziale, es. `api/v1/pratiche/<int:pk>/`);
#        `view` e' la classe (APIView o ViewSet), None per una view funzione.
@dataclass(frozen=True)
class Rotta:
    percorso: str
    view: type | None


# Scopo: cammina una lista di pattern e rende le rotte, col prefisso composto.
def _cammina(patterns: Iterable[Any], prefisso: str) -> list[Rotta]:
    rotte: list[Rotta] = []
    for pattern in patterns:
        percorso = prefisso + str(pattern.pattern)
        if isinstance(pattern, URLResolver):
            rotte += _cammina(pattern.url_patterns, percorso)
        elif isinstance(pattern, URLPattern):
            cb = pattern.callback
            view = getattr(cb, "view_class", None) or getattr(cb, "cls", None)
            rotte.append(Rotta(percorso=percorso, view=view))
    return rotte


# Scopo: le rotte dell'URLconf radice, e con `anche_condizionali=True` anche
#        quelle di `ROTTE_CONDIZIONALI` la cui flag oggi e' spenta (quelle con
#        la flag accesa sono gia' nell'URLconf: non si contano due volte).
# ⚠️ Serve a chi presidia il CODICE (tutte le view che il prodotto puo'
#    servire), non a chi descrive questa macchina: per quello basta il default.
def rotte_servite(*, anche_condizionali: bool = False) -> list[Rotta]:
    rotte = _cammina(get_resolver().url_patterns, "")
    if anche_condizionali:
        radice = importlib.import_module(settings.ROOT_URLCONF)
        for prefisso, urlconf, flag in getattr(radice, "ROTTE_CONDIZIONALI", ()):
            if not getattr(settings, flag, False):
                rotte += _cammina(get_resolver(urlconf).url_patterns, prefisso)
    return rotte


# Scopo: le classi di view distinte fra le rotte, una volta ciascuna.
def classi_view(*, anche_condizionali: bool = False) -> set[type]:
    return {
        r.view for r in rotte_servite(anche_condizionali=anche_condizionali)
        if r.view is not None
    }
