# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit `DocumentiRepository` per i metodi della Tranche I
#        (resolve template + versione, INSERT documento_generati,
#        documento_generati_file, evento, lookup tipo file). Mocka
#        `connection.cursor` per non richiedere DB reale (regola CI).
#        Verifica:
#         - find_template_applicabile: WHERE include `is_default=true`,
#           filtra `tipo_documento_output_id` quando passato, applica
#           scope `ANY(%s)`, LIMIT 1, ritorna None se nessuna riga;
#         - get_versione_pubblicata_attiva: filtra `stato='PUBBLICATA'`,
#           `attivo=true`, `validita @> %s::date`, ORDER BY versione DESC;
#         - next_progressivo_sorgente: COALESCE MAX+1 con branching
#           IS NULL vs `=` su `sorgente_riga`;
#         - create_documento_generato: INSERT solo colonne whitelisted in
#           DOCUMENTO_GENERATO_CREATE_COLUMNS, RETURNING id+uid;
#         - create_documento_generato_file: INSERT solo whitelisted,
#           RETURNING id;
#         - emit_evento_documento: INSERT solo whitelisted, NIENTE
#           `tx_id` esplicito (Decisione 76), RETURNING id;
#         - get_tipo_file_documento_by_codice: dict normalizzato o None.
#
# Indice test (0..N):
#   0. find_template_applicabile_filtra_is_default_e_active
#   1. find_template_applicabile_con_tipo_output_aggiuntivo
#   2. find_template_applicabile_con_scope_anyarray
#   3. find_template_applicabile_returns_none_when_no_match
#   4. get_versione_pubblicata_attiva_filtra_stato_attivo_validita
#   5. get_versione_pubblicata_attiva_returns_none_when_no_match
#   6. next_progressivo_sorgente_riga_null_branch
#   7. next_progressivo_sorgente_riga_valorizzata_branch
#   8. create_documento_generato_inserts_whitelisted_returns_id_and_uid
#   9. create_documento_generato_file_inserts_whitelisted_returns_id
#  10. emit_evento_documento_inserts_whitelisted_no_tx_id
#  11. get_tipo_file_documento_by_codice_returns_dict_or_none
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from typing import Any
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.documenti.db.documenti_repository import (
    DOCUMENTO_GENERATO_CREATE_COLUMNS,
    DOCUMENTO_GENERATO_FILE_CREATE_COLUMNS,
    EVENTO_DOCUMENTO_CREATE_COLUMNS,
    DocumentiRepository,
)


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


class FindTemplateApplicabileTests(TestCase):
    """Test find_template_applicabile: filtro is_default + scope."""

    # 0. baseline: WHERE include attivo + is_default; LIMIT 1.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_find_template_applicabile_filtra_is_default_e_active(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor(
            fetchone_results=[None],
            descriptions=[_columns("id", "codice")],
            fetchall_results=[[(7, "TPL-PREV")]],
        )
        mocked_factory.return_value = cursor

        row = DocumentiRepository().find_template_applicabile(
            sorgente_tipo_id=10,
            emittente_fiscale_id=11,
            tipo_documento_output_id=None,
            emittente_ids_scope=None,
        )

        self.assertEqual(row, {"id": 7, "codice": "TPL-PREV"})
        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("t.sorgente_tipo_id = %s", sql)
        self.assertIn("t.emittente_fiscale_id = %s", sql)
        self.assertIn("t.attivo = true", sql)
        self.assertIn("t.is_default = true", sql)
        self.assertIn("LIMIT 1", sql)
        self.assertEqual(params, [10, 11])

    # 1. tipo_documento_output_id passato -> WHERE include filtro + param.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_find_template_applicabile_con_tipo_output_aggiuntivo(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor(
            fetchone_results=[None],
            descriptions=[_columns("id")],
            fetchall_results=[[]],
        )
        mocked_factory.return_value = cursor

        DocumentiRepository().find_template_applicabile(
            sorgente_tipo_id=10,
            emittente_fiscale_id=11,
            tipo_documento_output_id=5,
            emittente_ids_scope=None,
        )
        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("t.tipo_documento_output_id = %s", sql)
        self.assertEqual(params, [10, 11, 5])

    # 2. scope -> ANY(%s) appiccicato + lista params.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_find_template_applicabile_con_scope_anyarray(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor(
            fetchone_results=[None],
            descriptions=[_columns("id")],
            fetchall_results=[[]],
        )
        mocked_factory.return_value = cursor

        DocumentiRepository().find_template_applicabile(
            sorgente_tipo_id=10,
            emittente_fiscale_id=11,
            tipo_documento_output_id=None,
            emittente_ids_scope=[11, 22],
        )
        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("t.emittente_fiscale_id = ANY(%s)", sql)
        self.assertEqual(params, [10, 11, [11, 22]])

    # 3. nessun match -> None.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_find_template_applicabile_returns_none_when_no_match(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor(
            fetchone_results=[None],
            descriptions=[_columns("id")],
            fetchall_results=[[]],
        )
        mocked_factory.return_value = cursor

        row = DocumentiRepository().find_template_applicabile(
            sorgente_tipo_id=10,
            emittente_fiscale_id=11,
            tipo_documento_output_id=None,
            emittente_ids_scope=None,
        )
        self.assertIsNone(row)


class GetVersionePubblicataAttivaTests(TestCase):
    """Test get_versione_pubblicata_attiva: stato + validita."""

    # 4. WHERE filtra stato='PUBBLICATA', attivo=true, validita @> today::date.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_get_versione_pubblicata_attiva_filtra_stato_attivo_validita(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor(
            fetchone_results=[None],
            descriptions=[_columns("id", "versione", "stato")],
            fetchall_results=[[(99, 3, "PUBBLICATA")]],
        )
        mocked_factory.return_value = cursor

        today = date(2026, 5, 4)
        row = DocumentiRepository().get_versione_pubblicata_attiva(
            42, today=today,
        )

        self.assertEqual(
            row, {"id": 99, "versione": 3, "stato": "PUBBLICATA"},
        )
        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("v.template_documento_id = %s", sql)
        self.assertIn("v.stato = 'PUBBLICATA'", sql)
        self.assertIn("v.attivo = true", sql)
        self.assertIn("v.validita @> %s::date", sql)
        self.assertIn("ORDER BY v.versione DESC", sql)
        self.assertIn("LIMIT 1", sql)
        self.assertEqual(params, [42, today])

    # 5. nessun match -> None.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_get_versione_pubblicata_attiva_returns_none_when_no_match(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor(
            fetchone_results=[None],
            descriptions=[_columns("id")],
            fetchall_results=[[]],
        )
        mocked_factory.return_value = cursor

        self.assertIsNone(
            DocumentiRepository().get_versione_pubblicata_attiva(
                42, today=date(2026, 5, 4),
            )
        )


class NextProgressivoSorgenteTests(TestCase):
    """Test next_progressivo_sorgente: branching IS NULL vs =."""

    # 6. sorgente_riga=None -> WHERE include `IS NULL`.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_next_progressivo_sorgente_riga_null_branch(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor(fetchone_results=[(7,)])
        mocked_factory.return_value = cursor

        result = DocumentiRepository().next_progressivo_sorgente(
            sorgente_tipo_id=10,
            sorgente_uid="abc-123",
            sorgente_riga=None,
        )
        self.assertEqual(result, 7)
        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("COALESCE(MAX(progressivo_sorgente), 0) + 1", sql)
        self.assertIn("sorgente_riga IS NULL", sql)
        self.assertEqual(params, [10, "abc-123"])

    # 7. sorgente_riga valorizzata -> WHERE include `=`.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_next_progressivo_sorgente_riga_valorizzata_branch(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor(fetchone_results=[(2,)])
        mocked_factory.return_value = cursor

        result = DocumentiRepository().next_progressivo_sorgente(
            sorgente_tipo_id=10,
            sorgente_uid="abc-123",
            sorgente_riga=5,
        )
        self.assertEqual(result, 2)
        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("sorgente_riga    = %s", sql)
        self.assertEqual(params, [10, "abc-123", 5])


class CreateDocumentoGeneratoTests(TestCase):
    """Test INSERT documenti_generati con whitelist + RETURNING id, uid."""

    # 8. INSERT solo colonne whitelisted; ritorna (id, uid).
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_create_documento_generato_inserts_whitelisted_returns_id_and_uid(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor(
            fetchone_results=[(99, "0190a000-0000-7000-8000-000000000001")],
        )
        mocked_factory.return_value = cursor

        data = {
            "tipo_documento_output_id": 1,
            "template_documento_id": 7,
            "template_versione_id": 12,
            "sorgente_tipo_id": 10,
            "sorgente_uid": "uid-1",
            "sorgente_riga": None,
            "progressivo_sorgente": 1,
            "stato": "GENERATO",
            "titolo": "Preventivo X",
            "nome_file": "preventivo-1.pdf",
            "context_json": {"k": "v"},
            "context_hash": "a" * 64,
            "template_hash": "b" * 64,
            "pdf_hash": "c" * 64,
            "generato_da_user_id": 5,
            "emittente_fiscale_id": 11,
            "meta": {},
            "chiave_extra": "ignorata",  # non whitelisted
        }
        new_id, uid = DocumentiRepository().create_documento_generato(data)
        self.assertEqual(new_id, 99)
        self.assertTrue(uid.startswith("0190a000"))

        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("INSERT INTO documenti.documenti_generati", sql)
        self.assertIn("RETURNING id, uid", sql)
        self.assertNotIn("chiave_extra", sql)
        # 17 chiavi whitelisted nel data, tutte presenti.
        self.assertEqual(len(params), len(DOCUMENTO_GENERATO_CREATE_COLUMNS))
        # tx_id NON deve essere in INSERT (Decisione 76).
        self.assertNotIn("tx_id", sql)


class CreateDocumentoGeneratoFileTests(TestCase):
    """Test INSERT documenti_generati_file con whitelist + RETURNING id."""

    # 9. INSERT solo whitelisted; ritorna id RETURNING.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_create_documento_generato_file_inserts_whitelisted_returns_id(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor(fetchone_results=[(123,)])
        mocked_factory.return_value = cursor

        data = {
            "documento_generato_id": 99,
            "file_tipo_id": 1,
            "mime_type": "application/pdf",
            "file_name": "preventivo-1.pdf",
            "file_size_bytes": 4096,
            "storage_key": "documenti/11/abc.pdf",
            "sha256": "c" * 64,
            "ordinamento": 1,
            "is_principale": True,
            "meta": {},
            "chiave_extra": "ignorata",
        }
        new_id = DocumentiRepository().create_documento_generato_file(data)
        self.assertEqual(new_id, 123)

        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("INSERT INTO documenti.documenti_generati_file", sql)
        self.assertIn("RETURNING id", sql)
        self.assertNotIn("chiave_extra", sql)
        self.assertEqual(
            len(params), len(DOCUMENTO_GENERATO_FILE_CREATE_COLUMNS),
        )


class EmitEventoDocumentoTests(TestCase):
    """Test INSERT documenti_generati_eventi senza tx_id (Decisione 76)."""

    # 10. INSERT solo whitelisted; NIENTE tx_id; ritorna id.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_emit_evento_documento_inserts_whitelisted_no_tx_id(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor(fetchone_results=[(7,)])
        mocked_factory.return_value = cursor

        data = {
            "documento_generato_id": 99,
            "evento_tipo": "GENERATO",
            "user_id": 5,
            "esito": "OK",
            "messaggio": None,
            "detail": {"size_bytes": 4096},
            "meta": {},
            "tx_id": "would-be-bug",  # Decisione 76: must be ignored
        }
        new_id = DocumentiRepository().emit_evento_documento(data)
        self.assertEqual(new_id, 7)

        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("INSERT INTO documenti.documenti_generati_eventi", sql)
        self.assertIn("RETURNING id", sql)
        self.assertNotIn("tx_id", sql)
        self.assertEqual(len(params), len(EVENTO_DOCUMENTO_CREATE_COLUMNS))
        # `tx_id="would-be-bug"` non deve risultare nei params: la
        # whitelist EVENTO_DOCUMENTO_CREATE_COLUMNS lo esclude per design.
        self.assertNotIn("would-be-bug", params)


class GetTipoFileDocumentoByCodiceTests(TestCase):
    """Test lookup tipo file per codice (PDF_FINALE)."""

    # 11. row presente -> dict normalizzato; row assente -> None.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_get_tipo_file_documento_by_codice_returns_dict_or_none(
        self, mocked_factory
    ) -> None:
        cursor_ok = _mk_cursor(fetchone_results=[(2, "PDF_FINALE", True)])
        mocked_factory.return_value = cursor_ok
        row = DocumentiRepository().get_tipo_file_documento_by_codice(
            "PDF_FINALE",
        )
        self.assertEqual(
            row, {"id": 2, "codice": "PDF_FINALE", "attivo": True},
        )
        sql, params = cursor_ok.execute.call_args_list[0].args
        self.assertIn("FROM documenti.tipi_file_documento", sql)
        self.assertIn("WHERE codice = %s", sql)
        self.assertEqual(params, ["PDF_FINALE"])

        cursor_none = _mk_cursor(fetchone_results=[None])
        mocked_factory.return_value = cursor_none
        self.assertIsNone(
            DocumentiRepository().get_tipo_file_documento_by_codice("INESIST"),
        )
