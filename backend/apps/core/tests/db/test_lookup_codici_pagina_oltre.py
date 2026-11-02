# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Lookup codici, pagina OLTRE l'ultima: il `count` resta il totale
#        vero, non 0 (F-8 dell'analisi difetti doc API core, 2026-09-28). In
#        ENTRAMBI i rami di `list_lookup_codici` — il generico
#        (`dbops.fn_get_lookup_codici`) e lo specializzato
#        (`_LOOKUP_SPECIALIZZATE`) — sul DATABASE PROVVISTO.
# Note: ⚠️ `COUNT(*) OVER ()` non vede righe su una pagina vuota: il totale lo
#        ricalcola il conteggio di ripiego del BB `fetch_paged_with_total`, con
#        lo stesso frammento FROM+WHERE della pagina. Il test chiede prima la
#        prima pagina (il totale di riferimento), poi una pagina ben oltre.
#        ⛔ Una rel senza righe non prova niente: si sceglie una rel del seed
#        che ne ha, e se nessuna ne ha il test FALLISCE (seed mancante), non
#        salta.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) LookupCodiciPaginaOltreTests.test_ramo_generico
2) LookupCodiciPaginaOltreTests.test_ramo_specializzato
"""

from __future__ import annotations

import unittest

from apps.core.db.dbops_repository import _LOOKUP_SPECIALIZZATE, DbopsRepository
from apps.core.db.tabelle_gestibili_repository import TabelleGestibiliRepository
from apps.core.tests.db_e2e import richiedi_db_provvisto


class LookupCodiciPaginaOltreTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    # Scopo: Prima rel (in ordine) del gruppo con almeno una riga, e il suo
    # totale letto dalla prima pagina.
    def _rel_con_righe(self, candidate: list[str]) -> tuple[str, int]:
        repo = DbopsRepository()
        for rel in sorted(candidate):
            _righe, totale = repo.list_lookup_codici(rel=rel, attivo_only=False, limit=1)
            if totale > 0:
                return rel, totale
        self.fail(f"nessuna rel con righe fra {sorted(candidate)}: il seed manca")

    # Scopo: Il totale oltre l'ultima pagina e' quello della prima.
    def _prova(self, rel: str, totale: int) -> None:
        righe, count = DbopsRepository().list_lookup_codici(
            rel=rel, attivo_only=False, limit=10, offset=totale + 100,
        )
        self.assertEqual(righe, [], rel)
        self.assertEqual(count, totale, f"{rel}: oltre l'ultima pagina il totale e' {count}")

    def test_ramo_generico(self):
        generiche = list(TabelleGestibiliRepository().rel_lookup() - set(_LOOKUP_SPECIALIZZATE))
        self._prova(*self._rel_con_righe(generiche))

    def test_ramo_specializzato(self):
        self._prova(*self._rel_con_righe(list(_LOOKUP_SPECIALIZZATE)))
