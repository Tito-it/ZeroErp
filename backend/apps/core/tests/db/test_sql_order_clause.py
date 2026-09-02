# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il presidio del BB `sql_order_clause`, estratto il 2026-09-02 (ok Tid)
#        dalle **46 ripetizioni** della stessa espressione nel backend.
#
#        ⚠️ PERCHE' UN BB VUOLE PIU' PRESIDIO DEI SUOI CALL-SITE, non meno: un
#        difetto qui non sbaglia una lista, le sbaglia tutte insieme — e nel
#        verso peggiore, perche' ogni chiamante lo eredita senza averlo scritto.
#
# ⛔ NON SERVE IL DATABASE: qui si guarda la STRINGA prodotta. Le query vere le
#    prova gia' `test_lista_proiezione_campo_sorgente` contro il database, colonna
#    per colonna e in entrambi i versi; questo modulo prova la REGOLA, che li'
#    non si vedrebbe (una clausola sbagliata nel verso e' SQL validissimo).
# ------------------------------------------------------------
"""Indice test (0..N):

0. test_senza_ordinamento_usa_il_default
1. test_ordinamento_esplicito_vince_sul_default
2. test_colonna_fuori_whitelist_ricade_sul_default
3. test_il_tiebreak_segue_la_direzione_primaria
4. test_il_tiebreak_non_si_ripete_quando_e_gia_la_colonna
5. test_le_colonne_data_partono_desc          (regola Tid 2026-09-02)
6. test_una_direzione_esplicita_vince_anche_su_una_colonna_data
7. test_default_clause_non_prende_una_seconda_direzione
8. test_default_e_default_clause_si_escludono
"""

from __future__ import annotations

import unittest

from apps.core.db._helpers import sql_order_clause

_COLONNE = {
    "codice": "t.codice",
    "data_evento": "t.data_evento",
}


class SqlOrderClauseTests(unittest.TestCase):
    def test_senza_ordinamento_usa_il_default(self) -> None:
        clausola = sql_order_clause(
            None, None, colonne=_COLONNE, default="t.creato_il", tiebreak="t.id",
        )
        self.assertEqual(clausola, "t.creato_il ASC NULLS FIRST, t.id ASC")

    def test_ordinamento_esplicito_vince_sul_default(self) -> None:
        clausola = sql_order_clause(
            "codice", "desc", colonne=_COLONNE, default="t.creato_il", tiebreak="t.id",
        )
        self.assertEqual(clausola, "t.codice DESC NULLS LAST, t.id DESC")

    def test_colonna_fuori_whitelist_ricade_sul_default(self) -> None:
        # ⚠️ Ricade in SILENZIO, ed e' il comportamento storico di tutti i
        #    repository: il 400 su un `order_by` sconosciuto lo dà, dove serve,
        #    `validate_order_params` a monte. Qui si fissa che il ripiego sia il
        #    DEFAULT e non la prima colonna della whitelist, che sarebbe un
        #    ordine deciso dall'ordine di scrittura di un dizionario.
        clausola = sql_order_clause(
            "colonna_inventata", None,
            colonne=_COLONNE, default="t.creato_il", tiebreak="t.id",
        )
        self.assertTrue(clausola.startswith("t.creato_il "), clausola)

    def test_il_tiebreak_segue_la_direzione_primaria(self) -> None:
        # ⛔ Decisione Tid 2026-08-03: a parita' di valore l'elenco non deve
        #    andare al contrario di come e' stato chiesto.
        for direzione, atteso in (("asc", "t.id ASC"), ("desc", "t.id DESC")):
            with self.subTest(direzione=direzione):
                clausola = sql_order_clause(
                    "codice", direzione,
                    colonne=_COLONNE, default="t.creato_il", tiebreak="t.id",
                )
                self.assertTrue(clausola.endswith(atteso), clausola)

    def test_il_tiebreak_non_si_ripete_quando_e_gia_la_colonna(self) -> None:
        # ⛔ Il caso reale: una lista il cui ordinamento di partenza E' `id`
        #    produceva `ORDER BY s.id ASC, s.id ASC` — la colonna e il suo
        #    stesso spareggio. Non sbaglia il risultato, ma e' una clausola che
        #    dice due volte la stessa cosa.
        clausola = sql_order_clause(
            None, None, colonne=_COLONNE, default="s.id", tiebreak="s.id",
        )
        self.assertEqual(clausola, "s.id ASC NULLS FIRST")

    def test_le_colonne_data_partono_desc(self) -> None:
        # ⭐ Regola di Tid del 2026-09-02: «gli ordinamenti per data hanno sempre
        #    default DESC». Una data si legge dalla piu' recente.
        clausola = sql_order_clause(
            "data_evento", None,
            colonne=_COLONNE, default="t.codice", tiebreak="t.id",
            colonne_desc={"data_evento"},
        )
        self.assertEqual(clausola, "t.data_evento DESC NULLS LAST, t.id DESC")
        # E una colonna NON data resta ASC: la regola vale per le date, non per
        # tutto — altrimenti sarebbe `default_desc` con un altro nome.
        clausola_codice = sql_order_clause(
            "codice", None,
            colonne=_COLONNE, default="t.codice", tiebreak="t.id",
            colonne_desc={"data_evento"},
        )
        self.assertEqual(clausola_codice, "t.codice ASC NULLS FIRST, t.id ASC")

    def test_una_direzione_esplicita_vince_anche_su_una_colonna_data(self) -> None:
        # ⚠️ Senza questo, l'operatore non potrebbe INVERTIRE l'ordine di una
        #    colonna data: il secondo click resterebbe DESC come il primo.
        clausola = sql_order_clause(
            "data_evento", "asc",
            colonne=_COLONNE, default="t.codice", tiebreak="t.id",
            colonne_desc={"data_evento"},
        )
        self.assertEqual(clausola, "t.data_evento ASC NULLS FIRST, t.id ASC")

    def test_default_clause_non_prende_una_seconda_direzione(self) -> None:
        # 🔴 Difetto reale della prima stesura del BB, trovato in giornata: un
        #    ordinamento di partenza a piu' criteri porta le direzioni DENTRO di
        #    se', e trattarlo come una colonna gli appiccicava una seconda
        #    direzione in coda — `... DESC DESC NULLS LAST`, che PostgreSQL
        #    rifiuta. Da qui i due parametri distinti.
        clausola = sql_order_clause(
            None, None,
            colonne=_COLONNE,
            default_clause="COALESCE(t.fine, 'infinity'::date) DESC, t.inizio DESC",
            tiebreak="t.id",
            default_desc=True,
        )
        self.assertEqual(
            clausola,
            "COALESCE(t.fine, 'infinity'::date) DESC, t.inizio DESC, t.id DESC",
        )
        self.assertNotIn("DESC DESC", clausola)

    def test_default_e_default_clause_si_escludono(self) -> None:
        # ⛔ Solleva invece di scegliere: passarli entrambi significa che chi
        #    scrive non sa quale dei due sta usando, e un BB che decide al posto
        #    suo trasforma un dubbio in un ordinamento sbagliato silenzioso.
        with self.assertRaises(ValueError):
            sql_order_clause(
                None, None, colonne=_COLONNE,
                default="t.codice", default_clause="t.codice DESC", tiebreak="t.id",
            )
        with self.assertRaises(ValueError):
            sql_order_clause(None, None, colonne=_COLONNE, tiebreak="t.id")
