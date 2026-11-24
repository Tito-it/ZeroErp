# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: la CATENA di «dove va il vuoto quando una lista ordina» sul DB vero
#        (brief-db-lista-colonna-vuoto-in-ordine, 2026-11-24): la lettura del
#        catalogo (`fetch_colonne_vuoto_massimo`) dice cio' che il seed
#        dichiara, e la clausola del BB, eseguita da PostgreSQL, mette il vuoto
#        in fondo nel crescente e in testa nel decrescente.
# Note: ⭐ Le righe da ordinare si COSTRUISCONO (`VALUES`), non si cercano
#       fra i dati: il caso «una riga col vuoto» c'e' per costruzione.
#       Sola lettura: nessuna transazione da annullare. La regola della
#       stringa, senza DB, e' in
#       `core/tests/api/test_vuoto_come_massimo.py`.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) test_il_catalogo_dice_cio_che_il_seed_dichiara
2) test_la_colonna_dichiarata_ordina_il_vuoto_come_il_massimo
3) test_una_colonna_non_dichiarata_ordina_il_vuoto_come_il_minimo
"""
from __future__ import annotations

import unittest

from django.db import connection

from apps.core.db._helpers import sql_order_clause
from apps.core.db.lista_catalogo_repository import fetch_colonne_vuoto_massimo
from apps.core.services.request_context import imposta_vuoti_come_massimo, set_request_context
from apps.core.tests._seed_csv import seed_ui
from apps.core.tests.db_e2e import richiedi_db_provvisto

# Una lista che dichiara `valido_al` (D-2: ogni `valido_al` accesa lo dichiara)
# e ha `numero` sulla regola generale.
_LISTA = "vendite.contratti"
_COLONNE = {"valido_al": "t.d", "numero": "t.d"}


class VuotoComeMassimoDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    def setUp(self) -> None:
        set_request_context(request_id=None, idempotency_key=None)
        self.addCleanup(set_request_context, request_id=None, idempotency_key=None)

    def _ordina(self, order_by: str, order_dir: str) -> list[int]:
        imposta_vuoti_come_massimo(lambda: fetch_colonne_vuoto_massimo(_LISTA))
        clausola = sql_order_clause(
            order_by, order_dir, colonne=_COLONNE, default="t.id", tiebreak="t.id",
        )
        with connection.cursor() as cur:
            cur.execute(
                "SELECT t.id FROM (VALUES (1, NULL::date), (2, DATE '2026-01-01'), "
                f"(3, DATE '2027-01-01')) AS t(id, d) ORDER BY {clausola}"
            )
            return [r[0] for r in cur.fetchall()]

    def test_il_catalogo_dice_cio_che_il_seed_dichiara(self) -> None:
        liste = {r["id"]: r["codice"] for r in seed_ui("lista_definizione.csv") if r["id"]}
        attese: dict[str, set[str]] = {}
        for r in seed_ui("lista_colonna.csv"):
            if r["vuoto_ordinato_come_massimo"] == "t":
                attese.setdefault(liste[r["lista_id"]], set()).add(str(r["campo_sorgente"]))
        self.assertIn(_LISTA, attese)
        for lista, colonne in attese.items():
            with self.subTest(lista=lista):
                self.assertTrue(colonne <= fetch_colonne_vuoto_massimo(lista))

    def test_la_colonna_dichiarata_ordina_il_vuoto_come_il_massimo(self) -> None:
        self.assertEqual(self._ordina("valido_al", "asc"), [2, 3, 1])
        self.assertEqual(self._ordina("valido_al", "desc"), [1, 3, 2])

    def test_una_colonna_non_dichiarata_ordina_il_vuoto_come_il_minimo(self) -> None:
        self.assertEqual(self._ordina("numero", "asc"), [1, 2, 3])
        self.assertEqual(self._ordina("numero", "desc"), [3, 2, 1])
