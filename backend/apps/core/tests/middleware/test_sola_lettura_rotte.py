# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Nessuna GET resta fuori dalla sola lettura
#        (brief-be-letture-in-transazione-sola-lettura §4, presidio 2).
#        L'elenco si ricava dalle ROTTE registrate, non da una lista scritta a
#        mano: per ogni rotta la decisione e' quella del middleware
#        (`va_in_sola_lettura`, una sede sola), e le eccezioni si elencano qui
#        PER NOME, col motivo dichiarato sulla view (§2.2).
# Note: Non tocca il DB: legge l'urlconf e gli attributi delle view.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) SolaLetturaRotteTests.test_il_middleware_e_l_ultimo_della_catena
2) SolaLetturaRotteTests.test_ogni_get_delle_api_va_in_sola_lettura_salvo_le_eccezioni_dichiarate
3) SolaLetturaRotteTests.test_fuori_dalle_api_solo_le_rotte_dichiarate
4) SolaLetturaRotteTests.test_una_dichiarazione_senza_motivo_non_vale
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from django.conf import settings
from django.test import RequestFactory, SimpleTestCase
from django.urls import URLResolver, get_resolver

from apps.core.middleware.sola_lettura_middleware import (
    PREFISSO_API,
    motivo_scrittura_in_get,
    nome_della_view,
    va_in_sola_lettura,
)

_MIDDLEWARE = "apps.core.middleware.sola_lettura_middleware.SolaLetturaMiddleware"

# ⛔ Le GET delle API che scrivono, con la view che dichiara il motivo
# (`scrittura_in_get`). Vuoto al 2026-09-25: la suite intera col DB vero non ne
# ha trovata nessuna. Aggiungerne una e' una decisione, non un rimedio.
_ECCEZIONI_DICHIARATE: frozenset[str] = frozenset()

# Le rotte fuori da `/api/`, dove la sola lettura non si monta.
_FUORI_DALLE_API: frozenset[str] = frozenset({"health"})


# Scopo: (percorso, callback) di ogni rotta registrata, risolvendo gli include.
def _rotte(pattern: list[Any] | None = None, prefisso: str = "") -> Iterator[tuple[str, Any]]:
    for p in pattern if pattern is not None else get_resolver().url_patterns:
        if isinstance(p, URLResolver):
            yield from _rotte(p.url_patterns, prefisso + str(p.pattern))
        else:
            yield prefisso + str(p.pattern), p.callback


class SolaLetturaRotteTests(SimpleTestCase):

    # 1. Ultimo: tutti gli altri middleware (il log della richiesta per primo)
    #    stanno FUORI dalla transazione di sola lettura (§2.1 punto 3).
    def test_il_middleware_e_l_ultimo_della_catena(self) -> None:
        self.assertEqual(settings.MIDDLEWARE[-1], _MIDDLEWARE)

    # 2.
    def test_ogni_get_delle_api_va_in_sola_lettura_salvo_le_eccezioni_dichiarate(self) -> None:
        fabbrica = RequestFactory()
        eccezioni: set[str] = set()
        controllate = 0
        for percorso, callback in _rotte():
            if not percorso.startswith(PREFISSO_API.lstrip("/")):
                continue
            controllate += 1
            if motivo_scrittura_in_get(callback) is not None:
                eccezioni.add(nome_della_view(callback))
                continue
            for metodo in ("get", "head"):
                richiesta = getattr(fabbrica, metodo)(f"/{percorso}")
                self.assertTrue(
                    va_in_sola_lettura(richiesta, callback),
                    f"{metodo.upper()} /{percorso} ({nome_della_view(callback)}) fuori dalla sola lettura",
                )
        self.assertGreater(controllate, 0, "nessuna rotta letta: l'urlconf non e' stato percorso")
        self.assertEqual(eccezioni, set(_ECCEZIONI_DICHIARATE))

    # 3.
    def test_fuori_dalle_api_solo_le_rotte_dichiarate(self) -> None:
        fuori = {p for p, _ in _rotte() if not p.startswith(PREFISSO_API.lstrip("/"))}
        self.assertEqual(fuori, set(_FUORI_DALLE_API))

    # 4. Il motivo va scritto: un flag senza testo non e' una dichiarazione.
    def test_una_dichiarazione_senza_motivo_non_vale(self) -> None:
        for valore in (True, "", "   ", None):
            vista = type("V", (), {"scrittura_in_get": valore})
            self.assertIsNone(motivo_scrittura_in_get(vista), repr(valore))
        vista = type("V", (), {"scrittura_in_get": "scrive il contatore delle viste"})
        self.assertEqual(motivo_scrittura_in_get(vista), "scrive il contatore delle viste")
