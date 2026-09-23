# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La ricerca libera delle liste sul DB VERO: il BB
#        `add_ricerca_full_condition` legge il catalogo con
#        `ui.fn_lista_colonne_ricerca_full` e la condizione che costruisce
#        parte sulla vista della lista. Gemello di `test_ricerca_full_seed`,
#        che confronta gli elenchi senza database.
#
#        ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI). Tutto in transazione
#        annullata: lo spegnimento di una colonna del test 3 non resta.
# ------------------------------------------------------------
"""Indice test (opt-in `ZEROERP_TEST_DB_E2E=1`):

1. test_la_condizione_parte_sulla_vista_di_ogni_lista
   Per ogni lista registrata, la condizione del BB applicata alla sua vista
   (`schema_dati.vista_sql` del catalogo) produce SQL valido. I mock del test
   gemello non eseguono la SQL: un `::text` mancante o un nome che la vista
   non ha sarebbe un 500 al primo operatore che cerca.

2. test_il_catalogo_non_accende_colonne_sconosciute
   Le colonne che il catalogo accende per l'operatore sono tutte dichiarate
   dal repository: nessun `warning` «colonne accese non dichiarate».

3. test_spegnere_una_colonna_la_toglie_subito
   Il motivo della lettura a runtime: si spegne `ricercabile_full` su una
   colonna, e la stessa chiamata non la cerca piu' — senza toccare il codice.
"""

from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.core.db._helpers import add_ricerca_full_condition
from apps.core.tests.db_e2e import apri_contesto_operatore, richiedi_db_provvisto
from apps.core.tests.test_liste_configurabili_seed import _seed
from apps.core.tests.test_ricerca_full_seed import _RICERCHE


class _Annulla(Exception):
    """Esce dal blocco atomico annullandolo."""


# Scopo: la vista qualificata di una lista, dal seed del catalogo.
def _vista(codice: str) -> str | None:
    for riga in _seed("lista_definizione.csv"):
        if riga["codice"] == codice:
            vista = riga["vista_sql"]
            if not vista or vista == "NULL":
                return None
            return f"{riga['schema_dati']}.{vista}"
    raise AssertionError(f"lista '{codice}' assente da lista_definizione.csv")


class RicercaFullDbTests(unittest.TestCase):
    def setUp(self):
        richiedi_db_provvisto("ui.fn_lista_colonne_ricerca_full(character varying)")

    def test_la_condizione_parte_sulla_vista_di_ogni_lista(self):
        for codice, risolvi in _RICERCHE:
            with self.subTest(lista=codice):
                vista = _vista(codice)
                # ⚠️ Le liste senza vista si esercitano dal repository: oggi
                #    le registrate ce l'hanno tutte. Chi ne registra una senza
                #    deve scrivere qui come esercitarla — fallisce, non salta.
                self.assertIsNotNone(
                    vista, f"{codice}: nessuna vista_sql, serve un esercizio dal repository",
                )
                with transaction.atomic(), connection.cursor() as cur:
                    apri_contesto_operatore(cur)
                    conditions: list[str] = []
                    params: list = []
                    add_ricerca_full_condition(conditions, params, "abc", risolvi())
                    self.assertTrue(conditions, codice)
                    cur.execute(
                        f"EXPLAIN SELECT 1 FROM {vista} v WHERE {' AND '.join(conditions)}",  # noqa: S608
                        params,
                    )

    def test_il_catalogo_non_accende_colonne_sconosciute(self):
        for codice, risolvi in _RICERCHE:
            with self.subTest(lista=codice):
                with transaction.atomic(), connection.cursor() as cur:
                    apri_contesto_operatore(cur)
                    with self.assertNoLogs("apps.core.db._helpers", level="WARNING"):
                        add_ricerca_full_condition([], [], "abc", risolvi())

    def test_spegnere_una_colonna_la_toglie_subito(self):
        # La dichiarazione che il repository passa davvero, non una sua copia.
        ricerca = dict(_RICERCHE)["vendite.preventivi"]()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                apri_contesto_operatore(cur)
                prima: list[str] = []
                add_ricerca_full_condition(prima, [], "abc", ricerca)
                self.assertIn("(v.ba_codice)::text", prima[0])

                cur.execute(
                    "UPDATE ui.lista_colonna lc SET ricercabile_full = false "
                    "  FROM ui.lista_definizione ld "
                    " WHERE ld.id = lc.lista_id AND ld.codice = %s "
                    "   AND lc.campo_sorgente = 'ba_codice'",
                    ["vendite.preventivi"],
                )
                self.assertEqual(cur.rowcount, 1)
                dopo: list[str] = []
                add_ricerca_full_condition(dopo, [], "abc", ricerca)
                self.assertNotIn("ba_codice", dopo[0])
                self.assertIn("(v.numero)::text", dopo[0])
                raise _Annulla
        except _Annulla:
            pass
