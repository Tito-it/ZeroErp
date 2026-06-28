# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit `DocumentiRepository` per i metodi della Tranche K
#        (lookup sorgente per codice, lista documenti generati per
#        sorgente, dettaglio documento, file principale per download).
#        Mocka `connection.cursor` (regola CI: niente DB reale).
#
# Indice test (0..N):
#   0. get_sorgente_tipo_id_by_codice_returns_dict_or_none
#   1. list_documenti_per_sorgente_filtra_sorgente_riga_null
#   2. list_documenti_per_sorgente_filtra_sorgente_riga_valorizzata
#   3. list_documenti_per_sorgente_applica_scope_anyarray
#   4. list_documenti_per_sorgente_paginazione_cap_200_e_order
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


class GetSorgenteTipoIdByCodiceTests(TestCase):
    """Lookup config.sorgenti per codice (es. PREVENTIVO)."""

    # 0. row presente -> dict; row assente -> None.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_get_sorgente_tipo_id_by_codice_returns_dict_or_none(
        self, mocked_factory
    ) -> None:
        cursor_ok = _mk_cursor(fetchone_results=[(10, "PREVENTIVO", True)])
        mocked_factory.return_value = cursor_ok
        row = DocumentiRepository().get_sorgente_tipo_id_by_codice("PREVENTIVO")
        self.assertEqual(
            row, {"id": 10, "codice": "PREVENTIVO", "attivo": True},
        )
        sql, params = cursor_ok.execute.call_args_list[0].args
        self.assertIn("FROM config.sorgenti", sql)
        self.assertIn("WHERE codice_interno = %s", sql)
        self.assertEqual(params, ["PREVENTIVO"])

        cursor_none = _mk_cursor(fetchone_results=[None])
        mocked_factory.return_value = cursor_none
        self.assertIsNone(
            DocumentiRepository().get_sorgente_tipo_id_by_codice("INESIST"),
        )


class ListDocumentiPerSorgenteTests(TestCase):
    """list_documenti_per_sorgente: branching + scope + paginazione."""

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
        cursor = _mk_cursor(
            fetchone_results=[(0,), None],
            descriptions=[[], _columns("id")],
            fetchall_results=[[], []],
        )
        mocked_factory.return_value = cursor

        DocumentiRepository().list_documenti_per_sorgente(**self._default_args())

        count_sql, count_params = cursor.execute.call_args_list[0].args
        self.assertIn("d.sorgente_tipo_id = %s", count_sql)
        self.assertIn("d.sorgente_uid = %s", count_sql)
        self.assertIn("d.sorgente_riga IS NULL", count_sql)
        self.assertEqual(count_params, [10, "uid-100"])

    # 2. sorgente_riga valorizzata -> WHERE include `=`.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_list_documenti_per_sorgente_filtra_sorgente_riga_valorizzata(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor(
            fetchone_results=[(0,), None],
            descriptions=[[], _columns("id")],
            fetchall_results=[[], []],
        )
        mocked_factory.return_value = cursor

        DocumentiRepository().list_documenti_per_sorgente(
            **self._default_args(sorgente_riga=3),
        )
        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("d.sorgente_riga = %s", sql)
        self.assertEqual(params, [10, "uid-100", 3])

    # 3. scope -> WHERE include `ANY(%s)` con lista params.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_list_documenti_per_sorgente_applica_scope_anyarray(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor(
            fetchone_results=[(0,), None],
            descriptions=[[], _columns("id")],
            fetchall_results=[[], []],
        )
        mocked_factory.return_value = cursor

        DocumentiRepository().list_documenti_per_sorgente(
            **self._default_args(emittente_ids_scope=[11, 22]),
        )
        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("d.emittente_fiscale_id = ANY(%s)", sql)
        self.assertEqual(params, [10, "uid-100", [11, 22]])

    # 4. paginazione: cap 200, offset preservato, ORDER BY generato_at DESC.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_list_documenti_per_sorgente_paginazione_cap_200_e_order(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor(
            fetchone_results=[(0,), None],
            descriptions=[[], _columns("id")],
            fetchall_results=[[], []],
        )
        mocked_factory.return_value = cursor

        DocumentiRepository().list_documenti_per_sorgente(
            **self._default_args(limit=999, offset=20),
        )

        data_sql, data_params = cursor.execute.call_args_list[1].args
        self.assertEqual(data_params[-2:], [200, 20])
        self.assertIn("ORDER BY d.generato_at DESC, d.id DESC", data_sql)


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
