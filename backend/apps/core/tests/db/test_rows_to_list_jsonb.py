# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I lettori a dizionari della sede comune (`row_to_dict`,
#        `rows_to_list`, `extract_paginated` e chi li usa) consegnano le
#        colonne `jsonb` DECODIFICATE, scelte dal tipo che il cursore dichiara
#        (brief-modello-documento-vendita §15.17.3, 2026-10-28).
# Note: ⛔ PERCHE' ESISTE. Il backend Django per psycopg 3 consegna il jsonb
#       come TESTO fuori dall'ORM, e fino al 2026-10-28 se ne ricordava ogni
#       query da se': chi se ne dimenticava serviva `meta` come stringa alle
#       API e ai modelli di stampa, e la ristampa fedele rifiutava ogni
#       documento. Gli unitari provano la regola su un cursore finto; l'ultimo
#       gira sul DATABASE PROVVISTO, perche' e' il driver vero a decidere che
#       cosa e' testo (i finti non lo vedono: e' cosi' che il difetto e'
#       vissuto).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_jsonb_decodificato_il_resto_intatto
2) test_null_resta_null
3) test_jsonb_array_elemento_per_elemento
4) test_row_to_dict_e_extract_paginated_uguali
5) test_descrittore_senza_tipo_non_si_tocca
6) test_db_vero_i_tipi_del_driver
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from django.db import connection

from apps.core.db._helpers import extract_paginated, row_to_dict, rows_to_list
from apps.core.tests.db_e2e import richiedi_db_provvisto

_JSONB = 3802
_JSONB_ARRAY = 3807
_TEXT = 25


# Scopo: un cursore finto con le colonne `(nome, tipo)` e le righe date.
def _cursore(colonne: list[tuple[str, int | None]], righe: list[tuple]) -> MagicMock:
    cur = MagicMock()
    cur.description = [
        SimpleNamespace(name=n) if t is None else SimpleNamespace(name=n, type_code=t)
        for n, t in colonne
    ]
    cur.fetchall.return_value = list(righe)
    cur.fetchone.return_value = righe[0] if righe else None
    return cur


class LettoriJsonbTests(unittest.TestCase):

    # 1. Il jsonb (oggetto, lista, scalare) esce decodificato; un testo che
    #    SEMBRA JSON ma sta in una colonna `text` resta testo: decide il tipo,
    #    non il contenuto.
    def test_jsonb_decodificato_il_resto_intatto(self) -> None:
        cur = _cursore(
            [("meta", _JSONB), ("componenti", _JSONB), ("etichetta", _JSONB), ("nota", _TEXT)],
            [('{"a": 1}', '[{"x": 2}]', '"testo"', '{"non": "decodificare"}')],
        )
        self.assertEqual(rows_to_list(cur), [{
            "meta": {"a": 1}, "componenti": [{"x": 2}], "etichetta": "testo",
            "nota": '{"non": "decodificare"}',
        }])

    # 2. NULL resta NULL (`None`, non `{}`): «non c'e'» e' un valore.
    def test_null_resta_null(self) -> None:
        cur = _cursore([("meta", _JSONB)], [(None,)])
        self.assertEqual(rows_to_list(cur), [{"meta": None}])

    # 3. `jsonb[]` arriva come lista di testi: ogni elemento decodificato.
    def test_jsonb_array_elemento_per_elemento(self) -> None:
        cur = _cursore([("v", _JSONB_ARRAY), ("n", _JSONB_ARRAY)], [(['{"a": 1}', None], None)])
        self.assertEqual(rows_to_list(cur), [{"v": [{"a": 1}, None], "n": None}])

    # 4. I tre lettori dicono la stessa cosa: una regola, una sede.
    def test_row_to_dict_e_extract_paginated_uguali(self) -> None:
        colonne = [("meta", _JSONB), ("total_count", 20)]
        riga = ('{"a": 1}', 7)
        self.assertEqual(row_to_dict(_cursore(colonne, [riga])), {"meta": {"a": 1}, "total_count": 7})
        self.assertEqual(extract_paginated(_cursore(colonne, [riga])), ([{"meta": {"a": 1}}], 7))

    # 5. Un descrittore senza tipo (i cursori finti di altri test) non ha
    #    colonne jsonb: il valore passa com'e'.
    def test_descrittore_senza_tipo_non_si_tocca(self) -> None:
        cur = _cursore([("meta", None)], [('{"a": 1}',)])
        self.assertEqual(rows_to_list(cur), [{"meta": '{"a": 1}'}])


class LettoriJsonbDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    # 6. Sul driver vero: jsonb e jsonb[] decodificati, `json` gia' oggetto
    #    (il driver lo decodifica da se'), il testo resta testo.
    def test_db_vero_i_tipi_del_driver(self) -> None:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT '{"a": 1}'::jsonb          AS jb,
                       ARRAY['[1]'::jsonb]        AS jba,
                       '{"b": 2}'::json           AS js,
                       '{"c": 3}'::text           AS t,
                       NULL::jsonb                AS n
                """
            )
            riga = row_to_dict(cur)
        self.assertEqual(riga, {
            "jb": {"a": 1}, "jba": [[1]], "js": {"b": 2}, "t": '{"c": 3}', "n": None,
        })
