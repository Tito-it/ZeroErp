# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit per DocumentiRepository. Mocka `connection.cursor`
#        per non richiedere DB reale (regola CI). Verifica:
#        - costruzione SQL corretta (count + data) con paginazione
#          deterministica (id come tiebreaker);
#        - filtri attivi vs assenti;
#        - scope emittente_ids;
#        - get_template con scope: ritorna None se row vuota;
#        - list_versioni filtra per template_id e attivo/stato;
#        - get_versione binda template_id (defense-in-depth).
#
# Indice test (0..N):
#   0. list_templates_basic_no_filters
#   1. list_templates_applies_filters_and_search
#   2. list_templates_applies_emittente_scope_anyarray
#   3. list_templates_paginazione_deterministica_id_tiebreaker
#   4. get_template_returns_row_or_none
#   5. get_template_with_scope_passes_anyarray
#   6. list_versioni_filters_by_template_and_state
#   7. get_versione_binds_template_id
#   8. list_templates_invalid_order_by_raises_validation_no_db
#   9. create_template_inserts_only_whitelisted_columns_returns_id
#  10. update_template_returns_true_on_success
#  11. update_template_returns_false_on_empty_data_no_sql
#  12. update_template_filters_by_id_in_where
#  13. next_versione_num_uses_coalesce_max
#  14. create_versione_inserts_only_whitelisted_columns
#  15. update_versione_returns_true_on_success
#  16. delete_versione_returns_true_on_success
#  17. pubblica_versione_filters_by_stato_bozza
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from unittest import TestCase

from apps.core.services.service_errors import ServiceError
from apps.documenti.db.documenti_repository import DocumentiRepository


def _mk_cursor(
    *,
    fetchone_results: list[Any] | None = None,
    fetchall_results: list[list[tuple]] | None = None,
    descriptions: list[list[Any]] | None = None,
) -> MagicMock:
    """Cursor mock con context manager + sequenza programmata di execute.

    `description` viene aggiornato per attributo a ogni execute (no
    PropertyMock su `type(cursor)`: modificherebbe la classe MagicMock
    globale e leakerebbe stato cross-test, causando errori al teardown).
    """
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    state = {"call": -1}

    def _on_execute(_sql, _params=None):
        state["call"] += 1
        if descriptions and state["call"] < len(descriptions):
            cursor.description = descriptions[state["call"]]
        else:
            cursor.description = []

    cursor.execute.side_effect = _on_execute
    cursor.fetchone.side_effect = lambda: (
        fetchone_results[state["call"]]
        if fetchone_results and state["call"] < len(fetchone_results)
        else None
    )
    cursor.fetchall.side_effect = lambda: (
        fetchall_results[state["call"]]
        if fetchall_results and state["call"] < len(fetchall_results)
        else []
    )
    return cursor


def _columns(*names: str) -> list[Any]:
    """psycopg expone description come lista di Column con attributo `.name`."""
    cols = []
    for n in names:
        m = MagicMock()
        m.name = n
        cols.append(m)
    return cols


class DocumentiRepositoryListTemplatesTests(TestCase):
    """Test list_templates: count + data + filtri + scope."""

    def _list_default_args(self, **overrides: Any) -> dict[str, Any]:
        defaults: dict[str, Any] = {
            "attivo": True,
            "tipo_documento_output_id": None,
            "sorgente_tipo_id": None,
            "emittente_fiscale_id": None,
            "search": None,
            "emittente_ids_scope": None,
            "order_by": "codice",
            "order_dir": "asc",
            "limit": 50,
            "offset": 0,
        }
        defaults.update(overrides)
        return defaults

    # 0. baseline: solo `attivo=True` come WHERE; SQL count+data eseguiti.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_list_templates_basic_no_filters(self, mocked_factory) -> None:
        cursor = _mk_cursor(
            fetchone_results=[(2,), None],
            descriptions=[[], _columns("id", "codice")],
            fetchall_results=[[], [(1, "A"), (2, "B")]],
        )
        mocked_factory.return_value = cursor

        rows, total = DocumentiRepository().list_templates(**self._list_default_args())

        self.assertEqual(total, 2)
        self.assertEqual(rows, [{"id": 1, "codice": "A"}, {"id": 2, "codice": "B"}])
        self.assertEqual(cursor.execute.call_count, 2)
        # Tiebreaker su `t.id ASC` nel data SQL (seconda execute).
        data_sql = cursor.execute.call_args_list[1].args[0]
        self.assertIn("ORDER BY t.codice ASC, t.id ASC", data_sql)
        self.assertIn("s_ef.ragione_sociale_completa", data_sql)
        self.assertIn("AS emittente_fiscale_descrizione", data_sql)
        self.assertIn("LEFT JOIN anagrafiche.soggetti_ruoli sr_ef", data_sql)

    # 1. filtri valorizzati e search ILIKE entrano nei params.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_list_templates_applies_filters_and_search(self, mocked_factory) -> None:
        cursor = _mk_cursor(
            fetchone_results=[(0,), None],
            descriptions=[[], _columns("id")],
            fetchall_results=[[], []],
        )
        mocked_factory.return_value = cursor

        DocumentiRepository().list_templates(
            **self._list_default_args(
                attivo=False,
                tipo_documento_output_id=10,
                sorgente_tipo_id=20,
                emittente_fiscale_id=11,
                search="prevent",
            )
        )

        count_call = cursor.execute.call_args_list[0]
        sql, params = count_call.args
        self.assertIn("t.attivo = %s", sql)
        self.assertIn("t.tipo_documento_output_id = %s", sql)
        self.assertIn("t.sorgente_tipo_id = %s", sql)
        self.assertIn("t.emittente_fiscale_id = %s", sql)
        self.assertIn("ILIKE %s", sql)
        self.assertEqual(
            params,
            [False, 10, 20, 11, "%prevent%", "%prevent%", "%prevent%"],
        )

    # 2. scope emittente passa lista ANY(%s) con i soli id whitelisted.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_list_templates_applies_emittente_scope_anyarray(self, mocked_factory) -> None:
        cursor = _mk_cursor(
            fetchone_results=[(0,), None],
            descriptions=[[], _columns("id")],
            fetchall_results=[[], []],
        )
        mocked_factory.return_value = cursor

        DocumentiRepository().list_templates(
            **self._list_default_args(emittente_ids_scope=[11, 22])
        )

        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("t.emittente_fiscale_id = ANY(%s)", sql)
        self.assertEqual(params, [True, [11, 22]])

    # 3. paginazione: LIMIT cappato a 200 + offset preservato + tiebreaker id.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_list_templates_paginazione_deterministica_id_tiebreaker(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor(
            fetchone_results=[(0,), None],
            descriptions=[[], _columns("id")],
            fetchall_results=[[], []],
        )
        mocked_factory.return_value = cursor

        DocumentiRepository().list_templates(
            **self._list_default_args(limit=999, offset=10)
        )

        data_sql, data_params = cursor.execute.call_args_list[1].args
        self.assertEqual(data_params[-2:], [200, 10])
        self.assertIn("ORDER BY t.codice ASC, t.id ASC", data_sql)

    # 8. order_by fuori whitelist -> E_DOCUMENTI_VALIDATION (no DB call).
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_list_templates_invalid_order_by_raises_validation_no_db(
        self, mocked_factory
    ) -> None:
        with self.assertRaises(ServiceError) as ctx:
            DocumentiRepository().list_templates(
                **self._list_default_args(order_by="totalmente_inventato")
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        # Defense-in-depth: nessuna query eseguita.
        mocked_factory.assert_not_called()


class DocumentiRepositoryGetTemplateTests(TestCase):
    # 4. row esistente -> dict; row assente -> None.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_get_template_returns_row(self, mocked_factory) -> None:
        cursor = _mk_cursor(
            fetchone_results=[None],
            descriptions=[_columns("id", "codice")],
            fetchall_results=[[(7, "T7")]],
        )
        mocked_factory.return_value = cursor

        result = DocumentiRepository().get_template(7, emittente_ids_scope=None)
        self.assertEqual(result, {"id": 7, "codice": "T7"})

    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_get_template_returns_none(self, mocked_factory) -> None:
        cursor = _mk_cursor(
            fetchone_results=[None],
            descriptions=[_columns("id")],
            fetchall_results=[[]],
        )
        mocked_factory.return_value = cursor

        self.assertIsNone(
            DocumentiRepository().get_template(7, emittente_ids_scope=[1])
        )

    # 5. scope emittente: WHERE include `t.emittente_fiscale_id = ANY(%s)`.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_get_template_with_scope_passes_anyarray(self, mocked_factory) -> None:
        cursor = _mk_cursor(
            fetchone_results=[None],
            descriptions=[_columns("id")],
            fetchall_results=[[]],
        )
        mocked_factory.return_value = cursor

        DocumentiRepository().get_template(7, emittente_ids_scope=[33])

        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("t.id = %s", sql)
        self.assertIn("t.emittente_fiscale_id = ANY(%s)", sql)
        self.assertEqual(params, [7, [33]])


class DocumentiRepositoryVersioniTests(TestCase):
    # 6. list_versioni filtra per template_id, attivo, stato.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_list_versioni_filters_by_template_and_state(self, mocked_factory) -> None:
        cursor = _mk_cursor(
            fetchone_results=[None],
            descriptions=[_columns("id", "versione", "stato")],
            fetchall_results=[[(1, 1, "PUBBLICATA")]],
        )
        mocked_factory.return_value = cursor

        rows = DocumentiRepository().list_versioni(42, attivo=True, stato="PUBBLICATA")

        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("v.template_documento_id = %s", sql)
        self.assertIn("v.attivo = %s", sql)
        self.assertIn("v.stato = %s", sql)
        self.assertIn("ORDER BY v.versione DESC, v.id DESC", sql)
        self.assertEqual(params, [42, True, "PUBBLICATA"])
        self.assertEqual(rows, [{"id": 1, "versione": 1, "stato": "PUBBLICATA"}])

    # 7. get_versione richiede sia versione_id sia template_documento_id.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_get_versione_binds_template_id(self, mocked_factory) -> None:
        cursor = _mk_cursor(
            fetchone_results=[None],
            descriptions=[_columns("id", "template_documento_id")],
            fetchall_results=[[(99, 42)]],
        )
        mocked_factory.return_value = cursor

        row = DocumentiRepository().get_versione(42, 99)

        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("v.id = %s", sql)
        self.assertIn("v.template_documento_id = %s", sql)
        self.assertEqual(params, [99, 42])
        self.assertEqual(row, {"id": 99, "template_documento_id": 42})


class DocumentiRepositoryCreateTemplateTests(TestCase):
    # 9. create_template usa solo colonne whitelisted; ritorna id RETURNING.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_create_template_inserts_only_whitelisted_columns_returns_id(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor(fetchone_results=[(99,)])
        mocked_factory.return_value = cursor

        data = {
            "tipo_documento_output_id": 1,
            "sorgente_tipo_id": 10,
            "emittente_fiscale_id": 11,
            "codice": "TPL-A",
            "codice_interno": "TPL_A",
            "descrizione": "Demo",
            "context_builder_code": "PREVENTIVO",
            "is_default": True,
            "attivo": True,
            "meta": {"k": "v"},
            "chiave_extra": "ignorata",  # difensivo: non inserita
        }
        new_id = DocumentiRepository().create_template(data)

        self.assertEqual(new_id, 99)
        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("INSERT INTO documenti.template_documenti", sql)
        self.assertIn("RETURNING id", sql)
        self.assertNotIn("chiave_extra", sql)
        # 10 colonne presenti nel data, tutte whitelisted (file_name_pattern
        # assente nel data quindi 10 - 1 = 10 colonne effettive).
        self.assertEqual(len(params), 10)


class DocumentiRepositoryUpdateTemplateTests(TestCase):
    # 10. update_template ritorna True se rowcount > 0.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_update_template_returns_true_on_success(self, mocked_factory) -> None:
        cursor = _mk_cursor()
        cursor.rowcount = 1
        mocked_factory.return_value = cursor

        result = DocumentiRepository().update_template(42, {"descrizione": "Nuova"})

        self.assertTrue(result)
        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("UPDATE documenti.template_documenti", sql)
        self.assertIn("descrizione = %s", sql)
        self.assertIn("WHERE id = %s", sql)
        self.assertEqual(params, ["Nuova", 42])

    # 11. update_template con data vuoto: nessuna SQL eseguita, ritorna False.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_update_template_returns_false_on_empty_data_no_sql(
        self, mocked_factory
    ) -> None:
        result = DocumentiRepository().update_template(42, {})
        self.assertFalse(result)
        mocked_factory.assert_not_called()

    # 12. update_template ignora chiavi non whitelisted (defense-in-depth).
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_update_template_filters_by_id_in_where(self, mocked_factory) -> None:
        cursor = _mk_cursor()
        cursor.rowcount = 1
        mocked_factory.return_value = cursor

        # `tipo_documento_output_id` (immutabile) non e' nella whitelist UPDATE
        # del repository: deve essere silently ignorato.
        DocumentiRepository().update_template(
            7, {"descrizione": "X", "tipo_documento_output_id": 999}
        )

        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("descrizione = %s", sql)
        self.assertNotIn("tipo_documento_output_id", sql)
        self.assertEqual(params, ["X", 7])


class DocumentiRepositoryVersioneMutationsTests(TestCase):
    # 13. next_versione_num: SELECT COALESCE(MAX(versione), 0) + 1.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_next_versione_num_uses_coalesce_max(self, mocked_factory) -> None:
        cursor = _mk_cursor(fetchone_results=[(5,)])
        mocked_factory.return_value = cursor

        result = DocumentiRepository().next_versione_num(42)
        self.assertEqual(result, 5)
        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("COALESCE(MAX(versione), 0) + 1", sql)
        self.assertIn("template_documento_id = %s", sql)
        self.assertEqual(params, [42])

    # 14. create_versione filtra colonne whitelisted + RETURNING id.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_create_versione_inserts_only_whitelisted_columns(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor(fetchone_results=[(50,)])
        mocked_factory.return_value = cursor

        data = {
            "template_documento_id": 1,
            "versione": 5,
            "stato": "BOZZA",
            "titolo": "v5",
            "html_template": "<p/>",
            "render_engine_id": 1,
            "page_format": "A4",
            "chiave_extra": "ignorata",  # non whitelisted
        }
        new_id = DocumentiRepository().create_versione(data)
        self.assertEqual(new_id, 50)
        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("INSERT INTO documenti.template_documenti_versioni", sql)
        self.assertIn("RETURNING id", sql)
        self.assertNotIn("chiave_extra", sql)
        self.assertEqual(len(params), 7)  # 7 chiavi whitelisted

    # 15. update_versione: rowcount > 0 -> True.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_update_versione_returns_true_on_success(self, mocked_factory) -> None:
        cursor = _mk_cursor()
        cursor.rowcount = 1
        mocked_factory.return_value = cursor

        result = DocumentiRepository().update_versione(11, {"titolo": "Nuovo"})
        self.assertTrue(result)
        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("UPDATE documenti.template_documenti_versioni", sql)
        self.assertIn("titolo = %s", sql)
        self.assertEqual(params, ["Nuovo", 11])

    # 16. delete_versione: rowcount > 0 -> True.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_delete_versione_returns_true_on_success(self, mocked_factory) -> None:
        cursor = _mk_cursor()
        cursor.rowcount = 1
        mocked_factory.return_value = cursor

        result = DocumentiRepository().delete_versione(11)
        self.assertTrue(result)
        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("DELETE FROM documenti.template_documenti_versioni", sql)
        self.assertIn("WHERE id = %s", sql)
        self.assertEqual(params, [11])

    # 17. pubblica_versione: WHERE stato='BOZZA' (idempotenza per design).
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_pubblica_versione_filters_by_stato_bozza(self, mocked_factory) -> None:
        from datetime import date as _date

        cursor = _mk_cursor()
        cursor.rowcount = 1
        mocked_factory.return_value = cursor

        result = DocumentiRepository().pubblica_versione(
            11, valido_dal=_date(2026, 6, 1), valido_al=None
        )
        self.assertTrue(result)
        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("UPDATE documenti.template_documenti_versioni", sql)
        self.assertIn("stato       = 'PUBBLICATA'", sql)
        self.assertIn("AND stato = 'BOZZA'", sql)
        self.assertEqual(params, [_date(2026, 6, 1), None, 11])
