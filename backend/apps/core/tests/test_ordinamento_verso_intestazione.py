# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il verso di ordinamento che parte da un'intestazione di lista e' quello
#        che la freccia mostra. Regola di Tid del 2026-11-24: il giro di ogni
#        intestazione, date comprese, e' niente -> crescente -> decrescente ->
#        niente, cioe' quello di PrimeVue, senza ritocchi.
#
#        ⭐ PERCHE' UN PRESIDIO SUL SORGENTE. Fino al 2026-11-24
#        `<ListaConfigurabile>` girava a DESC il primo click su una colonna data
#        (regola del 2026-09-02, ritirata). Il ritocco avveniva DOPO la scelta di
#        PrimeVue, che aggiorna la propria freccia solo quando la prop
#        `sortOrder` cambia valore: su una lista aperta gia' DESC la prop restava
#        -1 e la freccia diceva «crescente» su dati decrescenti, mentre il click
#        dopo mandava di nuovo `desc`. 🔴 Visto da Tid sulla validita' dei
#        preventivi. Il difetto e' MUTO — la lista risponde 200, ordinata, solo
#        al contrario di cio' che dice — e torna il giorno in cui qualcuno
#        rimette un verso di partenza dentro `onSort`.
#
# ⚠️ Il comportamento lo prova il test 14 di `ListaConfigurabile.spec.js`
#    (montaggio vero di PrimeVue). Qui si presidia il sorgente, perche' gira
#    nella suite BE accanto ai test della catena catalogo -> lista.
# ⚠️ NON SERVE IL DATABASE: si leggono i sorgenti del frontend.
# ------------------------------------------------------------
"""Indice test (1..N):

1. test_la_lista_non_ritocca_il_verso
   `ListaConfigurabile.onSort` inoltra l'evento di PrimeVue cosi' com'e':
   nessun `sortOrder` riscritto.

2. test_lo_stato_senza_ordinamento_non_dichiara_una_direzione
   Con l'ordinamento RIMOSSO (`removable-sort`) la direzione e' `null`, non
   `desc`: dichiararla teneva la freccia disallineata dai dati. Difetto
   trovato in collaudo sui DDT il 2026-09-02.
"""

from __future__ import annotations

import re
import unittest

from apps.core.tests._repo import repo_root


def _sorgente(relativo: str) -> str:
    return (repo_root() / relativo).read_text(encoding="utf-8")


class OrdinamentoVersoIntestazioneTests(unittest.TestCase):
    """Il verso inviato al backend e' quello che l'intestazione mostra."""

    def test_la_lista_non_ritocca_il_verso(self) -> None:
        src = _sorgente("frontend/src/core/components/ListaConfigurabile.vue")
        corpo = re.search(r"function onSort\(event\) \{(.*?)\n\}", src, re.S)
        self.assertIsNotNone(corpo, "`onSort` non si trova piu' in ListaConfigurabile")
        assert corpo is not None
        # ⛔ Un verso riscritto nell'evento e' esattamente il difetto del
        #    2026-11-24: la freccia di PrimeVue resta su quello che aveva
        #    scelto lei.
        self.assertNotRegex(
            corpo.group(1),
            r"sortOrder\s*:",
            "`onSort` riscrive il verso dell'evento: la freccia di PrimeVue "
            "non lo sa, e su una lista aperta DESC mostra un verso diverso da "
            "quello che parte verso il backend",
        )
        self.assertRegex(
            corpo.group(1),
            r"emit\('sort',\s*event\)",
            "`onSort` non inoltra piu' l'evento di PrimeVue cosi' com'e'",
        )

    def test_lo_stato_senza_ordinamento_non_dichiara_una_direzione(self) -> None:
        # ⛔ Con l'ordinamento RIMOSSO la direzione e' `null`, non `desc`.
        #    Scriverla `desc` teneva la prop `sortOrder` a -1 mentre il campo
        #    era sparito: al click seguente la prop non cambiava valore, il
        #    watcher di PrimeVue non scattava, e la freccia diceva una cosa
        #    mentre i dati ne dicevano un'altra.
        src = _sorgente("frontend/src/core/composables/useSearchTable.js")
        self.assertNotRegex(
            src,
            r"order_dir\s*=\s*event\.sortOrder\s*===\s*1\s*\?\s*'asc'\s*:\s*'desc'",
            "lo stato «ordinamento rimosso» torna a dichiarare `desc`: la "
            "freccia si desincronizza dai dati al click successivo",
        )
        self.assertRegex(
            src,
            r"store\.filters\.order_dir\s*=\s*event\.sortField",
            "la direzione non e' piu' condizionata alla PRESENZA del campo: "
            "senza campo non c'e' nessuna direzione da dichiarare",
        )
