# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit `DocumentiRepository` per i metodi della Tranche K
#        (lista documenti generati per sorgente, dettaglio documento, file
#        principale per download). Il lookup della sorgente per codice sta in
#        `apps.config.db.sorgenti_repository` (test in config/tests/db, dal
#        2026-10-11).
#        Mocka `connection.cursor` (regola CI: niente DB reale).
#
# Indice test (0..N):
#   1. list_documenti_per_sorgente_filtra_sorgente_riga_null
#   2. list_documenti_per_sorgente_filtra_sorgente_riga_valorizzata
#   3. list_documenti_per_sorgente_applica_scope_anyarray
#   4. list_documenti_per_sorgente_paginazione_cap_200_e_order
#   4-bis. list_documenti_per_sorgente_ordina_dalla_whitelist
#   4-ter. list_documenti_per_sorgente_passa_la_ricerca_al_bb
#   5. get_documento_generato_returns_row_or_none
#   6. get_documento_generato_with_scope_passes_anyarray
#   7. get_documento_generato_file_principale_filtra_is_principale_e_limit_1
#   8. get_documento_generato_file_principale_returns_none_when_no_match
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.documenti.db.documenti_repository import DocumentiRepository


# Scopo: Cursor mock con context manager + sequenza programmata di execute.
def _mk_cursor(
    *,
    fetchone_results: list[Any] | None = None,
    fetchall_results: list[list[tuple]] | None = None,
    descriptions: list[list[Any]] | None = None,
) -> MagicMock:
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
    cols = []
    for n in names:
        m = MagicMock()
        m.name = n
        cols.append(m)
    return cols


class ListDocumentiPerSorgenteTests(TestCase):
    """list_documenti_per_sorgente: branching + scope + paginazione + ordine.

    ⭐ Dal 2026-09-27 pagina e totale escono da UNA query (`COUNT(*) OVER ()`,
    BB `fetch_paged_with_total`): la prima `execute` e' la pagina, e il
    conteggio separato parte solo sulla pagina oltre l'ultima.
    """

    def _default_args(self, **overrides: Any) -> dict[str, Any]:
        defaults: dict[str, Any] = {
            "sorgente_tipo_id": 10,
            "sorgente_uid": "uid-100",
            "sorgente_riga": None,
            "emittente_ids_scope": None,
            "limit": 50,
            "offset": 0,
        }
        defaults.update(overrides)
        return defaults

    # 1. sorgente_riga=None -> WHERE include `IS NULL`.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_list_documenti_per_sorgente_filtra_sorgente_riga_null(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor()
        mocked_factory.return_value = cursor

        DocumentiRepository().list_documenti_per_sorgente(**self._default_args())

        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("d.sorgente_tipo_id = %s", sql)
        self.assertIn("d.sorgente_uid = %s", sql)
        self.assertIn("d.sorgente_riga IS NULL", sql)
        self.assertIn("COUNT(*) OVER () AS total_count", sql)
        self.assertEqual(params, [10, "uid-100", 50, 0])

    # 2. sorgente_riga valorizzata -> WHERE include `=`.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_list_documenti_per_sorgente_filtra_sorgente_riga_valorizzata(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor()
        mocked_factory.return_value = cursor

        DocumentiRepository().list_documenti_per_sorgente(
            **self._default_args(sorgente_riga=3),
        )
        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("d.sorgente_riga = %s", sql)
        self.assertEqual(params[:3], [10, "uid-100", 3])

    # 3. scope -> WHERE include `ANY(%s)` con lista params.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_list_documenti_per_sorgente_applica_scope_anyarray(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor()
        mocked_factory.return_value = cursor

        DocumentiRepository().list_documenti_per_sorgente(
            **self._default_args(emittente_ids_scope=[11, 22]),
        )
        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("d.emittente_fiscale_id = ANY(%s)", sql)
        self.assertEqual(params[:3], [10, "uid-100", [11, 22]])

    # 4. paginazione: cap 200, offset preservato, ORDER BY di partenza
    #    `generato_at DESC, id DESC` (la timeline: il piu' recente in cima).
    #    Pagina oltre l'ultima (0 righe, offset > 0) -> ripiego COUNT con lo
    #    stesso WHERE.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_list_documenti_per_sorgente_paginazione_cap_200_e_order(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor(fetchone_results=[None, (7,)])
        mocked_factory.return_value = cursor

        _, totale = DocumentiRepository().list_documenti_per_sorgente(
            **self._default_args(limit=999, offset=20),
        )

        data_sql, data_params = cursor.execute.call_args_list[0].args
        self.assertEqual(data_params[-2:], [200, 20])
        self.assertIn("ORDER BY d.generato_at DESC NULLS LAST, d.id DESC", data_sql)
        count_sql, count_params = cursor.execute.call_args_list[1].args
        self.assertIn("SELECT COUNT(*) FROM documenti.documenti_generati d", count_sql)
        self.assertEqual(count_params, [10, "uid-100"])
        self.assertEqual(totale, 7)

    # 4-bis. `order_by` dalla whitelist (chiave = campo_sorgente del catalogo);
    #        una colonna DATA senza verso ripiega DESC; fuori whitelist -> 400
    #        (`ValueError("order_by_invalid")`, decisione Tid 2026-10-20,
    #        brief-be-verifica-documentazione-api §A1: nessuna lista ripiega in
    #        silenzio sul default).
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_list_documenti_per_sorgente_ordina_dalla_whitelist(
        self, mocked_factory
    ) -> None:
        casi = [
            (("titolo", "asc"), "ORDER BY d.titolo ASC NULLS FIRST, d.id ASC"),
            (("progressivo_sorgente", "desc"), "ORDER BY d.progressivo_sorgente DESC NULLS LAST, d.id DESC"),
            (("generato_at", None), "ORDER BY d.generato_at DESC NULLS LAST, d.id DESC"),
        ]
        for (order_by, order_dir), atteso in casi:
            with self.subTest(order_by=order_by, order_dir=order_dir):
                cursor = _mk_cursor()
                mocked_factory.return_value = cursor
                DocumentiRepository().list_documenti_per_sorgente(
                    **self._default_args(order_by=order_by, order_dir=order_dir),
                )
                sql, _ = cursor.execute.call_args_list[0].args
                self.assertIn(atteso, sql)
        # «Originale» non ordina a catalogo: chiederlo e' un 400, non un ripiego.
        mocked_factory.return_value = _mk_cursor()
        with self.assertRaisesRegex(ValueError, "order_by_invalid"):
            DocumentiRepository().list_documenti_per_sorgente(
                **self._default_args(order_by="has_file_principale", order_dir="asc"),
            )

    # 4-ter. ricerca: la condizione del BB (`add_ricerca_full_condition`) sulle
    #        colonne accese dal catalogo, dentro lo stesso WHERE della pagina.
    @patch("apps.documenti.db.documenti_repository.add_ricerca_full_condition")
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_list_documenti_per_sorgente_passa_la_ricerca_al_bb(
        self, mocked_factory, mocked_ricerca
    ) -> None:
        cursor = _mk_cursor()
        mocked_factory.return_value = cursor

        def _aggiungi(conditions, params, termine, ricerca, *, alias):
            conditions.append("(d.titolo)::text ILIKE %s")
            params.append(f"%{termine}%")

        mocked_ricerca.side_effect = _aggiungi
        DocumentiRepository().list_documenti_per_sorgente(
            **self._default_args(search="offerta"),
        )
        _, _, termine, ricerca = mocked_ricerca.call_args.args
        self.assertEqual(termine, "offerta")
        self.assertEqual(ricerca.lista_codice, "documenti.documenti_sorgente")
        self.assertEqual(mocked_ricerca.call_args.kwargs, {"alias": "d"})
        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("(d.titolo)::text ILIKE %s", sql)
        self.assertEqual(params, [10, "uid-100", "%offerta%", 50, 0])


class GetDocumentoGeneratoTests(TestCase):
    """Detail documento generato + scope opzionale."""

    # 5. row presente -> dict; row assente -> None.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_get_documento_generato_returns_row_or_none(
        self, mocked_factory
    ) -> None:
        cursor_ok = _mk_cursor(
            fetchone_results=[None],
            descriptions=[_columns("id", "uid")],
            fetchall_results=[[(99, "uid-x")]],
        )
        mocked_factory.return_value = cursor_ok
        row = DocumentiRepository().get_documento_generato(
            99, emittente_ids_scope=None,
        )
        self.assertEqual(row, {"id": 99, "uid": "uid-x"})

        cursor_none = _mk_cursor(
            fetchone_results=[None],
            descriptions=[_columns("id")],
            fetchall_results=[[]],
        )
        mocked_factory.return_value = cursor_none
        self.assertIsNone(
            DocumentiRepository().get_documento_generato(
                999, emittente_ids_scope=[1, 2],
            ),
        )

    # 6. scope -> WHERE include ANY(%s).
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_get_documento_generato_with_scope_passes_anyarray(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor(
            fetchone_results=[None],
            descriptions=[_columns("id")],
            fetchall_results=[[]],
        )
        mocked_factory.return_value = cursor

        DocumentiRepository().get_documento_generato(
            99, emittente_ids_scope=[11],
        )
        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("d.id = %s", sql)
        self.assertIn("d.emittente_fiscale_id = ANY(%s)", sql)
        self.assertEqual(params, [99, [11]])


class GetDocumentoGeneratoFilePrincipaleTests(TestCase):
    """File principale del documento (`is_principale=true`, LIMIT 1)."""

    # 7. WHERE include `is_principale = true` e LIMIT 1.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_get_documento_generato_file_principale_filtra_is_principale_e_limit_1(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor(
            fetchone_results=[None],
            descriptions=[_columns("id", "storage_key", "mime_type", "file_name", "file_size_bytes")],
            fetchall_results=[[(123, "documenti/11/abc.pdf", "application/pdf", "x.pdf", 4096)]],
        )
        mocked_factory.return_value = cursor

        row = DocumentiRepository().get_documento_generato_file_principale(99)
        self.assertEqual(row["storage_key"], "documenti/11/abc.pdf")
        self.assertEqual(row["mime_type"], "application/pdf")
        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("f.documento_generato_id = %s", sql)
        self.assertIn("f.is_principale = true", sql)
        self.assertIn("LIMIT 1", sql)
        self.assertEqual(params, [99])

    # 8. nessun file principale -> None (es. cleanup STORAGE_ORPHAN).
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_get_documento_generato_file_principale_returns_none_when_no_match(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor(
            fetchone_results=[None],
            descriptions=[_columns("id")],
            fetchall_results=[[]],
        )
        mocked_factory.return_value = cursor
        self.assertIsNone(
            DocumentiRepository().get_documento_generato_file_principale(99),
        )
