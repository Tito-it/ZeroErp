# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il presidio dei BB di scrittura dinamica di
#        `apps/core/db/sql_write_helpers.py`: `execute_dynamic_insert` e
#        `sql_set_clause` (estratti 2026-09-26, regola del 2),
#        `execute_dynamic_update` (allineato al RIFIUTO lo stesso giorno), la
#        regola comune valore -> (segnaposto, parametro), i `casts` e le
#        estensioni del 2026-09-26 (`letterali`, cast array, `espressioni`).
#
# ⛔ NON SERVE IL DATABASE: il cursore e' finto e si guarda la STRINGA e i
#    PARAMETRI prodotti. Le scritture vere le provano i test DB dei repository
#    consumatori (ZEROERP_TEST_DB_E2E=1).
# ------------------------------------------------------------
"""Indice test (0..N):

0. test_insert_compone_colonne_segnaposti_e_returning
1. test_insert_dict_e_list_escono_jsonb_serializzati
2. test_insert_colonna_jsonb_dichiarata_passa_il_testo_com_e
3. test_insert_stringhe_strip
4. test_insert_skip_none_omette_i_none
5. test_insert_senza_skip_none_scrive_null
6. test_insert_colonna_fuori_whitelist_rifiutata
7. test_insert_nome_non_identificatore_rifiutato_anche_senza_whitelist
8. test_insert_senza_colonne_rifiutato
9. test_set_clause_compone_e_rifiuta
10. test_set_clause_vuota_rifiutata
11. test_update_compone_set_e_where
12. test_update_colonna_fuori_whitelist_rifiutata   (non piu' scartata in silenzio)
13. test_update_nome_non_identificatore_rifiutato_anche_senza_whitelist
14. test_update_skip_none_e_vuoto
15. test_update_chiave_fuori_whitelist_rifiutata_anche_se_none
16. test_casts_generano_il_cast_nei_tre_bb
17. test_cast_non_identificatore_rifiutato_nei_tre_bb
18. test_colonna_sia_jsonb_sia_cast_rifiutata
19. test_letterali_non_si_strippano_nei_tre_bb
20. test_cast_array_passa_la_lista_com_e
21. test_insert_espressioni_letterali
22. test_insert_espressione_su_colonna_gia_in_values_rifiutata
23. test_insert_espressione_fuori_whitelist_rifiutata
"""

from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from apps.core.db.sql_write_helpers import (
    execute_dynamic_insert,
    execute_dynamic_update,
    sql_set_clause,
)

_MODULO = "apps.core.db.sql_write_helpers"


# Scopo: Un cursore finto che risponde a RETURNING con una riga.
def _cursore(riga: dict | None = None) -> MagicMock:
    riga = {"id": 7} if riga is None else riga
    cursore = MagicMock()
    cursore.description = [MagicMock(name=k) for k in riga]
    for colonna, k in zip(cursore.description, riga, strict=True):
        colonna.name = k
    cursore.fetchone.return_value = tuple(riga.values())
    cursore.rowcount = 1
    return cursore


class ExecuteDynamicInsertTests(unittest.TestCase):
    def _esegui(self, *args, riga=None, **kwargs):
        cursore = _cursore(riga)
        with patch(f"{_MODULO}.connection") as conn:
            conn.cursor.return_value.__enter__.return_value = cursore
            esito = execute_dynamic_insert(*args, **kwargs)
        sql, params = cursore.execute.call_args.args
        return esito, sql, params

    def test_insert_compone_colonne_segnaposti_e_returning(self) -> None:
        esito, sql, params = self._esegui(
            "s.t", {"a": 1, "b": 2}, allowed=None,
            returning="id, uid::text AS uid", riga={"id": 3, "uid": "u"},
        )
        self.assertEqual(
            sql, "INSERT INTO s.t (a, b) VALUES (%s, %s) RETURNING id, uid::text AS uid"
        )
        self.assertEqual(params, [1, 2])
        self.assertEqual(esito, {"id": 3, "uid": "u"})

    def test_insert_dict_e_list_escono_jsonb_serializzati(self) -> None:
        _, sql, params = self._esegui(
            "s.t", {"meta": {"k": 1}, "tag": [1, 2]}, allowed=None,
        )
        self.assertIn("VALUES (%s::jsonb, %s::jsonb)", sql)
        self.assertEqual(params, [json.dumps({"k": 1}), json.dumps([1, 2])])

    # ⚠️ La convenzione dei moduli che serializzano gia' nel service
    #    (pagamenti): la stringa e' testo JSON, e non va ri-serializzata — un
    #    secondo `json.dumps` salverebbe una STRINGA jsonb invece dell'oggetto.
    def test_insert_colonna_jsonb_dichiarata_passa_il_testo_com_e(self) -> None:
        _, sql, params = self._esegui(
            "s.t", {"regole": '{"a": 1}', "nota": " x "},
            allowed={"regole", "nota"}, jsonb=("regole",),
        )
        self.assertIn("VALUES (%s::jsonb, %s)", sql)
        self.assertEqual(params, ['{"a": 1}', "x"])

    def test_insert_stringhe_strip(self) -> None:
        _, _, params = self._esegui("s.t", {"codice": "  AB  "}, allowed=None)
        self.assertEqual(params, ["AB"])

    # I `create_*` dei documenti vendita: un None si omette, cosi' vale il
    # DEFAULT del DB (o il trigger BEFORE INSERT).
    def test_insert_skip_none_omette_i_none(self) -> None:
        _, sql, params = self._esegui(
            "s.t", {"a": 1, "data": None, "meta": {}}, allowed=None, skip_none=True,
        )
        self.assertEqual(
            sql, "INSERT INTO s.t (a, meta) VALUES (%s, %s::jsonb) RETURNING id"
        )
        self.assertEqual(params, [1, "{}"])

    def test_insert_senza_skip_none_scrive_null(self) -> None:
        _, sql, params = self._esegui("s.t", {"a": None}, allowed=None)
        self.assertIn("(a) VALUES (%s)", sql)
        self.assertEqual(params, [None])

    # ⛔ La politica RIGIDA: una colonna fuori whitelist e' un errore, e
    #    niente arriva al database.
    def test_insert_colonna_fuori_whitelist_rifiutata(self) -> None:
        with patch(f"{_MODULO}.connection") as conn:
            with self.assertRaises(RuntimeError) as ctx:
                execute_dynamic_insert("s.t", {"a": 1, "zz": 2}, allowed={"a"})
            conn.cursor.assert_not_called()
        self.assertIn("zz", str(ctx.exception))

    def test_insert_nome_non_identificatore_rifiutato_anche_senza_whitelist(self) -> None:
        for nome in ("a, b", "a) VALUES (1); --", "A", "1a", ""):
            with self.subTest(nome=nome), patch(f"{_MODULO}.connection") as conn:
                with self.assertRaises(RuntimeError):
                    execute_dynamic_insert("s.t", {nome: 1}, allowed=None)
                conn.cursor.assert_not_called()

    def test_insert_senza_colonne_rifiutato(self) -> None:
        with patch(f"{_MODULO}.connection"):
            with self.assertRaises(RuntimeError):
                execute_dynamic_insert("s.t", {}, allowed=None)
            with self.assertRaises(RuntimeError):
                execute_dynamic_insert("s.t", {"a": None}, allowed=None, skip_none=True)


class SqlSetClauseTests(unittest.TestCase):
    def test_set_clause_compone_e_rifiuta(self) -> None:
        clausola, params = sql_set_clause(
            {"descrizione": " d ", "meta": {"k": 1}, "attivo": False},
            allowed={"descrizione", "meta", "attivo"},
        )
        self.assertEqual(clausola, "descrizione = %s, meta = %s::jsonb, attivo = %s")
        self.assertEqual(params, ["d", json.dumps({"k": 1}), False])
        with self.assertRaises(RuntimeError):
            sql_set_clause({"codice": "x"}, allowed={"descrizione"})

    def test_set_clause_vuota_rifiutata(self) -> None:
        with self.assertRaises(RuntimeError):
            sql_set_clause({}, allowed=None)


class ExecuteDynamicUpdateTests(unittest.TestCase):
    def _esegui(self, *args, **kwargs):
        cursore = _cursore()
        with patch(f"{_MODULO}.connection") as conn:
            conn.cursor.return_value.__enter__.return_value = cursore
            esito = execute_dynamic_update(*args, **kwargs)
        if not cursore.execute.called:
            return esito, None, None
        sql, params = cursore.execute.call_args.args
        return esito, sql, params

    def test_update_compone_set_e_where(self) -> None:
        esito, sql, params = self._esegui(
            "s.t", 5, {"a": " v ", "meta": {"k": 1}}, allowed={"a", "meta"},
            extra_set="data_update = now()",
        )
        self.assertTrue(esito)
        self.assertEqual(
            sql,
            "UPDATE s.t SET a = %s, meta = %s::jsonb, data_update = now() WHERE id = %s",
        )
        self.assertEqual(params, ["v", json.dumps({"k": 1}), 5])

    # ⛔ Fino al 2026-09-26 `zz` veniva SCARTATA in silenzio e l'UPDATE
    #    «riusciva» senza scriverla. Ora e' un errore, e al DB non arriva nulla.
    def test_update_colonna_fuori_whitelist_rifiutata(self) -> None:
        with patch(f"{_MODULO}.connection") as conn:
            with self.assertRaises(RuntimeError) as ctx:
                execute_dynamic_update("s.t", 5, {"a": 1, "zz": 2}, allowed={"a"})
            conn.cursor.assert_not_called()
        self.assertIn("zz", str(ctx.exception))

    def test_update_nome_non_identificatore_rifiutato_anche_senza_whitelist(self) -> None:
        for nome in ("a = 1, b", "a = now() --", "A", ""):
            with self.subTest(nome=nome), patch(f"{_MODULO}.connection") as conn:
                with self.assertRaises(RuntimeError):
                    execute_dynamic_update("s.t", 5, {nome: 1})
                conn.cursor.assert_not_called()

    def test_update_skip_none_e_vuoto(self) -> None:
        esito, sql, params = self._esegui(
            "s.t", 5, {"a": None, "b": 2}, allowed={"a", "b"}, skip_none=True,
        )
        self.assertEqual(sql, "UPDATE s.t SET b = %s WHERE id = %s")
        self.assertEqual(params, [2, 5])
        esito, sql, _ = self._esegui("s.t", 5, {}, allowed={"a"})
        self.assertFalse(esito)
        self.assertIsNone(sql)

    # Una chiave fuori contratto e' un errore QUALUNQUE valore porti: che
    # `skip_none` l'avrebbe omessa non la rende ammessa.
    def test_update_chiave_fuori_whitelist_rifiutata_anche_se_none(self) -> None:
        with patch(f"{_MODULO}.connection"):
            with self.assertRaises(RuntimeError):
                execute_dynamic_update(
                    "s.t", 5, {"a": 1, "zz": None}, allowed={"a"}, skip_none=True,
                )
            with self.assertRaises(RuntimeError):
                execute_dynamic_insert(
                    "s.t", {"a": 1, "zz": None}, allowed={"a"}, skip_none=True,
                )


class CastsTests(unittest.TestCase):
    _CASTS = {"tipo": "ui.tipo_colonna", "n": "numeric"}

    def test_casts_generano_il_cast_nei_tre_bb(self) -> None:
        valori = {"tipo": " azione ", "n": 3, "a": "x"}
        cursore = _cursore()
        with patch(f"{_MODULO}.connection") as conn:
            conn.cursor.return_value.__enter__.return_value = cursore
            execute_dynamic_update("s.t", 5, valori, allowed=None, casts=self._CASTS)
            sql_upd, params_upd = cursore.execute.call_args.args
            execute_dynamic_insert("s.t", valori, allowed=None, casts=self._CASTS)
            sql_ins, params_ins = cursore.execute.call_args.args
        self.assertEqual(
            sql_upd,
            "UPDATE s.t SET tipo = %s::ui.tipo_colonna, n = %s::numeric, a = %s WHERE id = %s",
        )
        self.assertEqual(params_upd, ["azione", 3, "x", 5])
        self.assertIn(
            "(tipo, n, a) VALUES (%s::ui.tipo_colonna, %s::numeric, %s)", sql_ins,
        )
        self.assertEqual(params_ins, ["azione", 3, "x"])
        clausola, params = sql_set_clause(valori, allowed=None, casts=self._CASTS)
        self.assertEqual(clausola, "tipo = %s::ui.tipo_colonna, n = %s::numeric, a = %s")
        self.assertEqual(params, ["azione", 3, "x"])

    # Il nome del tipo entra nel testo SQL: se non e' un identificatore
    # (qualificato o no) e' rifiutato, anche se il payload non porta la colonna.
    def test_cast_non_identificatore_rifiutato_nei_tre_bb(self) -> None:
        for tipo in ("text; DROP TABLE x", "ui.tipo.colonna", "Ui.Tipo", "", "a b"):
            casts = {"tipo": tipo}
            with self.subTest(tipo=tipo), patch(f"{_MODULO}.connection") as conn:
                with self.assertRaises(RuntimeError):
                    execute_dynamic_update("s.t", 5, {"a": 1}, allowed=None, casts=casts)
                with self.assertRaises(RuntimeError):
                    execute_dynamic_insert("s.t", {"a": 1}, allowed=None, casts=casts)
                with self.assertRaises(RuntimeError):
                    sql_set_clause({"a": 1}, allowed=None, casts=casts)
                conn.cursor.assert_not_called()

    def test_colonna_sia_jsonb_sia_cast_rifiutata(self) -> None:
        with patch(f"{_MODULO}.connection"):
            with self.assertRaises(RuntimeError):
                execute_dynamic_update(
                    "s.t", 5, {"m": "{}"}, allowed=None, jsonb=("m",), casts={"m": "jsonb"},
                )



# 19-23. Le tre estensioni del 2026-09-26 (migrazione D2): colonne dove lo
#        spazio e' contenuto, colonne array, espressioni letterali.
class EstensioniTests(unittest.TestCase):
    def _insert(self, *args, **kwargs):
        cursore = _cursore()
        with patch(f"{_MODULO}.connection") as conn:
            conn.cursor.return_value.__enter__.return_value = cursore
            execute_dynamic_insert(*args, **kwargs)
        return cursore.execute.call_args.args

    def _update(self, *args, **kwargs):
        cursore = _cursore()
        with patch(f"{_MODULO}.connection") as conn:
            conn.cursor.return_value.__enter__.return_value = cursore
            execute_dynamic_update(*args, **kwargs)
        return cursore.execute.call_args.args

    # 19. Il corpo di un template: lo spazio ai bordi e' contenuto.
    def test_letterali_non_si_strippano_nei_tre_bb(self) -> None:
        valori = {"html": "  <p>x</p>\n", "codice": " A "}
        _, params = self._insert("s.t", valori, allowed=None, letterali=("html",))
        self.assertEqual(params, ["  <p>x</p>\n", "A"])
        _, params = self._update("s.t", 5, valori, allowed=None, letterali=("html",))
        self.assertEqual(params[:2], ["  <p>x</p>\n", "A"])
        _, params = sql_set_clause(valori, allowed=None, letterali=("html",))
        self.assertEqual(params, ["  <p>x</p>\n", "A"])

    # 20. ⛔ Senza, la lista finiva serializzata in JSON: il tipo sbagliato.
    def test_cast_array_passa_la_lista_com_e(self) -> None:
        clausola, params = sql_set_clause(
            {"cc": ["a@x.it", "b@x.it"]}, allowed=None, casts={"cc": "text[]"},
        )
        self.assertEqual(clausola, "cc = %s::text[]")
        self.assertEqual(params, [["a@x.it", "b@x.it"]])

    # 21. Il gemello di `extra_set`: l'espressione entra nel testo, non nei
    #     parametri.
    def test_insert_espressioni_letterali(self) -> None:
        sql, params = self._insert(
            "s.t", {"a": 1}, allowed=None, espressioni={"valido_dal": "script.fn_data_operativa()"},
        )
        self.assertEqual(
            sql, "INSERT INTO s.t (a, valido_dal) VALUES (%s, script.fn_data_operativa()) RETURNING id",
        )
        self.assertEqual(params, [1])

    # 22. Due risposte alla stessa domanda: rifiutata.
    def test_insert_espressione_su_colonna_gia_in_values_rifiutata(self) -> None:
        with patch(f"{_MODULO}.connection") as conn, self.assertRaises(RuntimeError):
            execute_dynamic_insert(
                "s.t", {"a": 1}, allowed=None, espressioni={"a": "script.fn_data_operativa()"},
            )
        conn.cursor.assert_not_called()

    # 23. La colonna di un'espressione passa la stessa whitelist dei valori.
    def test_insert_espressione_fuori_whitelist_rifiutata(self) -> None:
        with patch(f"{_MODULO}.connection") as conn, self.assertRaises(RuntimeError):
            execute_dynamic_insert(
                "s.t", {"a": 1}, allowed={"a"}, espressioni={"b": "script.fn_data_operativa()"},
            )
        conn.cursor.assert_not_called()


if __name__ == "__main__":
    unittest.main()
