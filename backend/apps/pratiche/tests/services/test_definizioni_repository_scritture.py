# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit delle scritture dinamiche di `DefinizioniRepository`
#        (step, figli per-nodo, archi) sui BB `execute_dynamic_insert` /
#        `sql_set_clause` (migrazione 2026-09-26). Mocka `connection.cursor`,
#        nessun DB reale. `unittest.TestCase`, non `SimpleTestCase`: quello
#        avvolge `connection.cursor` e il patch ne rompe il teardown.
# Note: ⛔ Il caso nuovo e' il RIFIUTO: fino al 2026-09-26 una chiave fuori
#       allowlist veniva scartata in silenzio; ora e' RuntimeError e nessuna
#       SQL parte. Il service passa solo chiavi ripulite da `_clean_writable`,
#       quindi dal client il caso non e' raggiungibile: e' un invariante.
# ------------------------------------------------------------
"""
Indice test:
1) create_step: le chiavi del BE (definizione/tipo) vincono su `data`, RETURNING id.
2) create_step: chiave fuori STEP_CORE_FIELDS -> RuntimeError, nessuna SQL.
3) update_step: SET dal BB + WHERE (id, definizione_id) posizionale.
4) update_step: `data` vuoto -> RuntimeError (precondizione del service).
5) create_child: template_flusso_id imposto dal BE, colonne dallo spec.
6) update_child: fuori spec.writable -> RuntimeError, nessuna SQL.
7) create_edge: tipo_col ammesso in INSERT; update_edge: tipo_col NO.
"""
from __future__ import annotations

from typing import Any
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.pratiche.db.definizioni_repository import DefinizioniRepository

_CURSOR = "apps.pratiche.db.definizioni_repository.connection.cursor"


# Scopo: cursor mock con una riga di RETURNING (`id`) e un rowcount.
def _mk_cursor(*, riga: tuple | None = (1,), rowcount: int = 1) -> MagicMock:
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    colonna = MagicMock()
    colonna.name = "id"
    cursor.description = [colonna]
    cursor.fetchone.return_value = riga
    cursor.rowcount = rowcount
    return cursor


def _sql_params(cursor: MagicMock) -> tuple[str, Any]:
    return cursor.execute.call_args.args


class DefinizioniRepositoryScrittureTests(TestCase):
    # 1. Le due chiavi imposte dal BE vincono anche se `data` le portasse.
    @patch(_CURSOR)
    def test_create_step_chiavi_del_be_vincono(self, factory):
        cursor = _mk_cursor(riga=(555,))
        factory.return_value = cursor
        new_id = DefinizioniRepository().create_step(
            419, 9004, {"codice": " S1 ", "descrizione": "Step", "sequenza": 10},
        )
        self.assertEqual(new_id, 555)
        sql, params = _sql_params(cursor)
        self.assertIn("INSERT INTO pratiche.template_flussi", sql)
        self.assertIn("RETURNING id", sql)
        self.assertEqual(
            params, ["S1", "Step", 10, 419, 9004],
        )

    # 2. ⛔ Fuori allowlist: RuntimeError, nessuna SQL (prima: scarto silenzioso).
    @patch(_CURSOR)
    def test_create_step_chiave_estranea_rifiutata(self, factory):
        with self.assertRaises(RuntimeError) as ctx:
            DefinizioniRepository().create_step(
                419, 9004, {"codice": "S1", "handler_id": 3},
            )
        self.assertIn("handler_id", str(ctx.exception))
        factory.assert_not_called()

    # 3. SET dal BB, WHERE posizionale in coda ai valori del SET.
    @patch(_CURSOR)
    def test_update_step_set_e_where(self, factory):
        cursor = _mk_cursor(rowcount=1)
        factory.return_value = cursor
        n = DefinizioniRepository().update_step(419, 100, {"descrizione": "nuova"})
        self.assertEqual(n, 1)
        sql, params = _sql_params(cursor)
        self.assertIn("SET descrizione = %s", sql)
        self.assertIn("WHERE id = %s AND definizione_id = %s", sql)
        self.assertEqual(params, ["nuova", 100, 419])

    # 4. `data` vuoto: errore di programmazione (RuntimeError), non un no-op.
    @patch(_CURSOR)
    def test_update_step_vuoto_rifiutato(self, factory):
        with self.assertRaises(RuntimeError):
            DefinizioniRepository().update_step(419, 100, {})
        factory.assert_not_called()

    # 5. template_flusso_id dal BE; colonne dello spec `canali`.
    @patch(_CURSOR)
    def test_create_child_template_flusso_dal_be(self, factory):
        cursor = _mk_cursor(riga=(77,))
        factory.return_value = cursor
        new_id = DefinizioniRepository().create_child(
            "canali", 100, {"canale_id": 3, "attivo": True},
        )
        self.assertEqual(new_id, 77)
        sql, params = _sql_params(cursor)
        self.assertIn(
            "INSERT INTO pratiche.template_flussi_canali "
            "(canale_id, attivo, template_flusso_id)",
            sql,
        )
        self.assertEqual(params, [3, True, 100])

    # 6. ⛔ update_child fuori spec.writable (template_flusso_id non e' writable).
    @patch(_CURSOR)
    def test_update_child_chiave_estranea_rifiutata(self, factory):
        with self.assertRaises(RuntimeError) as ctx:
            DefinizioniRepository().update_child(
                "canali", 419, 100, 5, {"template_flusso_id": 999},
            )
        self.assertIn("template_flusso_id", str(ctx.exception))
        factory.assert_not_called()

    # 7. formule_tempo: `tipo_prestazione_id` (tipo_col) ammesso in INSERT,
    #    rifiutato in UPDATE (non e' writable).
    @patch(_CURSOR)
    def test_edge_tipo_col_solo_in_insert(self, factory):
        cursor = _mk_cursor(riga=(88,))
        factory.return_value = cursor
        repo = DefinizioniRepository()
        new_id = repo.create_edge("formule_tempo", {
            "template_flusso_da_id": 1, "template_flusso_a_id": 2,
            "giorni_esecuzione": 5, "giorni_warning": 3, "giorni_critico": 1,
            "tipo_prestazione_id": 9004,
        })
        self.assertEqual(new_id, 88)
        sql, _ = _sql_params(cursor)
        self.assertIn("tipo_prestazione_id", sql)

        with self.assertRaises(RuntimeError):
            repo.update_edge("formule_tempo", 419, 88, {"tipo_prestazione_id": 1})

        cursor.execute.reset_mock()
        n = repo.update_edge("formule_tempo", 419, 88, {"giorni_warning": 4})
        self.assertEqual(n, 1)
        sql, params = _sql_params(cursor)
        self.assertIn("SET giorni_warning = %s", sql)
        self.assertIn("tf.id = e.template_flusso_da_id", sql)
        self.assertEqual(params, [4, 88, 419])
