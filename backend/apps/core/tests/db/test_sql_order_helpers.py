# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test degli helper di ordinamento SQL (`apps/core/db/_helpers.py`):
#        `sql_order_direction` (verso + NULLS) e `sql_tiebreak_direction`
#        (verso del tiebreak, allineato alla colonna primaria).
#
#        Perche' esistono: entrambi gli helper decidono un pezzo di ORDER BY
#        interpolato in ~30 query. Un difetto qui non rompe nulla in modo
#        visibile — produce un ELENCO ORDINATO MALE, che e' il tipo di bug che
#        si scopre solo guardando una lista vera e chiedendosi perche' i
#        documenti dello stesso giorno sono al contrario.
#
# Indice test (0..N):
#   0. direzione_desc_mette_i_null_in_coda
#   1. direzione_asc_mette_i_null_in_testa
#   2. direzione_default_e_asc_salvo_default_desc
#   3. direzione_case_insensitive_e_tollera_spazi
#   4. tiebreak_segue_la_direzione
#   5. tiebreak_non_porta_mai_i_nulls
#   6. tiebreak_da_direzione_grezza
#   7. repository_produce_order_by_col_tiebreak_allineato (end-to-end)
#   8. repository_asc_produce_tiebreak_asc (end-to-end)
# ------------------------------------------------------------

from __future__ import annotations

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.db._helpers import sql_order_direction, sql_tiebreak_direction


class SqlOrderDirectionTests(TestCase):
    """Verso della colonna primaria + posizione dei NULL."""

    # 0-1. I NULL vanno dove starebbe lo zero, in entrambi i versi: e' la
    #      correzione del 2026-07-19 (il default PostgreSQL e' l'opposto e
    #      portava i campi vuoti in cima proprio ordinando dal piu' recente).
    def test_direzione_desc_mette_i_null_in_coda(self) -> None:
        self.assertEqual(sql_order_direction("desc"), "DESC NULLS LAST")

    def test_direzione_asc_mette_i_null_in_testa(self) -> None:
        self.assertEqual(sql_order_direction("asc"), "ASC NULLS FIRST")

    # 2. Senza indicazione si sale, salvo le liste che nascono dal piu' recente.
    def test_direzione_default_e_asc_salvo_default_desc(self) -> None:
        self.assertEqual(sql_order_direction(None), "ASC NULLS FIRST")
        self.assertEqual(sql_order_direction(""), "ASC NULLS FIRST")
        self.assertEqual(
            sql_order_direction(None, default_desc=True), "DESC NULLS LAST",
        )

    # 3. Il valore arriva da query string: maiuscole e spazi non devono
    #    cambiare l'esito (silenziosamente sarebbe un ordine sbagliato).
    def test_direzione_case_insensitive_e_tollera_spazi(self) -> None:
        for grezzo in ("DESC", " desc ", "Desc", "DeSc\n"):
            with self.subTest(valore=grezzo):
                self.assertEqual(sql_order_direction(grezzo), "DESC NULLS LAST")


class SqlTiebreakDirectionTests(TestCase):
    """Il tiebreak segue la colonna primaria (decisione Tid 2026-08-03)."""

    # 4. Il punto della modifica: prima era inchiodato ad ASC, quindi a parita'
    #    di data l'elenco si ribaltava dentro il giorno.
    def test_tiebreak_segue_la_direzione(self) -> None:
        self.assertEqual(
            sql_tiebreak_direction(sql_order_direction("desc")), "DESC",
        )
        self.assertEqual(
            sql_tiebreak_direction(sql_order_direction("asc")), "ASC",
        )

    # 5. Niente NULLS sul tiebreak: e' una chiave tecnica non nullable (`id`),
    #    e un `NULLS` di troppo qui sarebbe SQL valido ma ridondante — mentre
    #    su una colonna nullable reintrodurrebbe i vuoti in cima in DESC. E'
    #    il motivo per cui il tiebreak dev'essere `id` e non `numero`.
    def test_tiebreak_non_porta_mai_i_nulls(self) -> None:
        for order_dir in ("asc", "desc", None):
            with self.subTest(order_dir=order_dir):
                verso = sql_tiebreak_direction(sql_order_direction(order_dir))
                self.assertNotIn("NULLS", verso)
                self.assertIn(verso, ("ASC", "DESC"))

    # 6. Accetta anche una direzione grezza (i repository che la calcolano
    #    inline invece di passare da sql_order_direction).
    def test_tiebreak_da_direzione_grezza(self) -> None:
        self.assertEqual(sql_tiebreak_direction("DESC"), "DESC")
        self.assertEqual(sql_tiebreak_direction("asc"), "ASC")
        # Qualunque cosa non-DESC vale ASC: nessun terzo stato silenzioso.
        self.assertEqual(sql_tiebreak_direction("qualsiasi"), "ASC")


class OrderByEndToEndTests(TestCase):
    """L'ORDER BY che arriva davvero al database, da un repository reale.

    Gli unit sugli helper non bastano: il difetto stava nei TEMPLATE SQL, dove
    il tiebreak era scritto a mano. Questi due test guardano la stringa
    eseguita, che e' il punto in cui il difetto si manifestava.
    """

    # Scopo: cursor finto che cattura la SQL eseguita.
    def _repo_con_cursor(self):
        cursor = MagicMock()
        cursor.__enter__ = MagicMock(return_value=cursor)
        cursor.__exit__ = MagicMock(return_value=False)
        cursor.fetchone.return_value = (0,)
        cursor.fetchall.return_value = []
        cursor.description = []
        return cursor

    # 7. Ordinando DESC, a parita' di valore vince l'id piu' ALTO (il record
    #    piu' recente): e' cio' che l'operatore si aspetta guardando una lista
    #    ordinata dal piu' recente.
    def test_repository_produce_order_by_col_tiebreak_allineato(self) -> None:
        from apps.anagrafiche.db.categorie_clienti_repository import (
            CategorieClientiRepository,
        )

        cursor = self._repo_con_cursor()
        with patch(
            "apps.anagrafiche.db.categorie_clienti_repository.connection.cursor",
            return_value=cursor,
        ):
            CategorieClientiRepository().list_categorie(
                order_by="descrizione", order_dir="desc",
            )
        sql = cursor.execute.call_args_list[-1][0][0]
        self.assertIn("ORDER BY cc.descrizione DESC NULLS LAST, cc.id DESC", sql)

    # 8. Simmetrico in salita: il tiebreak non resta inchiodato al verso
    #    opposto (che era il difetto).
    def test_repository_asc_produce_tiebreak_asc(self) -> None:
        from apps.anagrafiche.db.categorie_clienti_repository import (
            CategorieClientiRepository,
        )

        cursor = self._repo_con_cursor()
        with patch(
            "apps.anagrafiche.db.categorie_clienti_repository.connection.cursor",
            return_value=cursor,
        ):
            CategorieClientiRepository().list_categorie(
                order_by="descrizione", order_dir="asc",
            )
        sql = cursor.execute.call_args_list[-1][0][0]
        self.assertIn("ORDER BY cc.descrizione ASC NULLS FIRST, cc.id ASC", sql)
