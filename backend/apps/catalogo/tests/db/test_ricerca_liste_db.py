# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La ricerca libera della lista articoli e della lookup articoli sul
#        DATABASE VERO. La lista cerca col BB `add_ricerca_full_condition`
#        (colonne dal catalogo `catalogo.articoli`); la lookup NON e' una lista
#        e cerca per conto suo, con escape e strip (brief-be-ricerca-full-liste-
#        residue §7-bis, ultimo paragrafo).
# Note: ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI). Il mondo si
#       COSTRUISCE (regola zero, .codex/AGENTS.md): azienda e operatore da
#       `fn_pgtap_crea_emittente_operatore`, poi il CONTESTO, poi gli articoli
#       da `fn_pgtap_crea_articolo`. Tutto in transazione ANNULLATA.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) RicercaListeCatalogoDbTests.test_la_ricerca_trova_ogni_colonna_accesa
   Lista `catalogo.articoli`: su un articolo costruito, per ogni colonna che
   il catalogo accende la ricerca dal repository lo trova
   (`verifica_ricerca_colonna_per_colonna`); un termine inesistente no.
2) RicercaListeCatalogoDbTests.test_la_lookup_articoli_escapa_e_toglie_gli_spazi
   La lookup articoli: `_` nel termine e' un carattere, non un jolly (prima
   del 2026-09-24 «RICLK_1» trovava anche «RICLKX1»); gli spazi ai bordi non
   contano.
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.core.tests.db_e2e import (
    Annulla,
    richiedi_db_provvisto,
    verifica_ricerca_colonna_per_colonna,
)

_FIXTURE: tuple[str, ...] = (
    """
    CREATE TEMP TABLE _mondo AS
    SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m
    """,
    "SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo))",
)


# Scopo: costruisce il mondo (azienda, operatore, contesto) sul cursore.
def _apri_mondo(cur) -> None:
    for passo in _FIXTURE:
        cur.execute(passo)


# Scopo: un articolo costruito, con la descrizione scelta dal test.
def _crea_articolo(cur, codice: str, descrizione: str):
    cur.execute("SELECT dbops.fn_pgtap_crea_articolo(%s)", [codice])
    articolo = cur.fetchone()[0]
    cur.execute(
        "UPDATE catalogo.articoli SET descrizione = %s WHERE id = %s",
        [descrizione, articolo],
    )
    return articolo


class RicercaListeCatalogoDbTests(unittest.TestCase):
    def setUp(self):
        richiedi_db_provvisto("ui.fn_lista_colonne_ricerca_full(character varying)")

    # 1. Lista articoli: ogni colonna accesa a catalogo trova la sua riga.
    def test_la_ricerca_trova_ogni_colonna_accesa(self):
        from apps.catalogo.db.catalogo_repository import CatalogoRepository

        _filtri = {
            "attivo": None, "is_composito": None, "tipo_voce_id": None,
            "gruppo_voce_id": None, "listino_tipologia_id": None,
            "data_da": None, "data_a": None,
            "order_by": "codice", "order_dir": "asc", "limit": 200, "offset": 0,
        }
        try:
            with transaction.atomic(), connection.cursor() as cur:
                _apri_mondo(cur)
                articolo = _crea_articolo(cur, "RICCODART", "Articolo ricdescart")
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "catalogo.articoli", articolo,
                    {"codice": "riccodart", "descrizione": "ricdescart"},
                    lambda t: CatalogoRepository().list_articoli(search=t, **_filtri)[0],
                )
                raise Annulla
        except Annulla:
            pass

    # 2. Lookup articoli: escape dei metacaratteri e strip del termine.
    def test_la_lookup_articoli_escapa_e_toglie_gli_spazi(self):
        from apps.catalogo.db.catalogo_repository import CatalogoRepository

        try:
            with transaction.atomic(), connection.cursor() as cur:
                _apri_mondo(cur)
                esatto = _crea_articolo(cur, "RICLK_1", "Articolo lookup esatto")
                jolly = _crea_articolo(cur, "RICLKX1", "Articolo lookup jolly")

                righe, _troncato = CatalogoRepository().lookup_articoli(
                    search="  riclk_1  ", attivo=None, is_composito=None, limit=50,
                )
                ids = [r["id"] for r in righe]
                self.assertIn(esatto, ids)
                # ⛔ Senza escape `_` vale «un carattere qualsiasi».
                self.assertNotIn(jolly, ids)

                righe, _troncato = CatalogoRepository().lookup_articoli(
                    search="riclk%1", attivo=None, is_composito=None, limit=50,
                )
                self.assertEqual(righe, [], "`%` nel termine e' un carattere, non un jolly")
                raise Annulla
        except Annulla:
            pass
