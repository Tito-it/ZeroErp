# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit `DocumentiRepository` per i metodi della Tranche I
#        (resolve template + versione, INSERT documento_generati,
#        documento_generati_file, evento, lookup tipo file). Mocka
#        `connection.cursor` per non richiedere DB reale (regola CI).
#        Verifica:
#         - risolvi_template_applicabile: chiama
#           `documenti.fn_risolvi_template_applicabile` coi tre argomenti (il
#           tipo assente arriva NULL), zero righe = invariante rotta;
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
#   0. risolvi_template_applicabile_chiama_la_funzione_db
#   1. risolvi_template_applicabile_con_tipo_output
#   2. risolvi_template_applicabile_zero_righe_invariante
#   4. get_versione_pubblicata_attiva_filtra_stato_attivo_validita
#   5. get_versione_pubblicata_attiva_returns_none_when_no_match
#   6. next_progressivo_sorgente_riga_null_branch
#   7. next_progressivo_sorgente_riga_valorizzata_branch
#   8. create_documento_generato_inserts_whitelisted_returns_id_and_uid
#   9. create_documento_generato_file_inserts_whitelisted_returns_id
#  10. emit_evento_documento_inserts_whitelisted_no_tx_id
#  10-bis. emit_evento_documento_tx_id_esplicito_rifiutato
#  10-ter. emit_evento_documento_stringa_jsonb_e_testo_json
#  11. get_tipo_file_documento_by_codice_returns_dict_or_none
# ------------------------------------------------------------

from __future__ import annotations

import json
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


class RisolviTemplateApplicabileTests(TestCase):
    """Test risolvi_template_applicabile: la regola e' della funzione DB."""

    # 0. chiama la funzione DB coi tre argomenti, ritorna id, livello e la
    #    versione che stampa (P-2).
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_risolvi_template_applicabile_chiama_la_funzione_db(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor(
            fetchone_results=[None],
            descriptions=[_columns("template_documento_id", "livello", "template_versione_id")],
            fetchall_results=[[(7, "STANDARD", 12)]],
        )
        mocked_factory.return_value = cursor

        row = DocumentiRepository().risolvi_template_applicabile(
            sorgente_tipo_id=10,
            emittente_fiscale_id=11,
            tipo_documento_output_id=None,
        )

        self.assertEqual(
            row,
            {"template_documento_id": 7, "livello": "STANDARD", "template_versione_id": 12},
        )
        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("template_versione_id", sql)
        self.assertIn("documenti.fn_risolvi_template_applicabile(%s, %s, %s)", sql)
        # Il tipo assente arriva NULL: lo deduce il DB, non un ORDER BY qui.
        self.assertEqual(params, [10, 11, None])
        self.assertNotIn("LIMIT", sql)

    # 1. tipo_documento_output_id passato -> terzo argomento.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_risolvi_template_applicabile_con_tipo_output(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor(
            fetchone_results=[None],
            descriptions=[_columns("template_documento_id", "livello")],
            fetchall_results=[[(7, "EMITTENTE")]],
        )
        mocked_factory.return_value = cursor

        DocumentiRepository().risolvi_template_applicabile(
            sorgente_tipo_id=10,
            emittente_fiscale_id=11,
            tipo_documento_output_id=5,
        )
        _sql, params = cursor.execute.call_args_list[0].args
        self.assertEqual(params, [10, 11, 5])

    # 2. zero righe senza errore: la funzione non lo fa mai, e' un'invariante
    #    rotta -> RuntimeError, non un None che il service leggerebbe come 404.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_risolvi_template_applicabile_zero_righe_invariante(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor(
            fetchone_results=[None],
            descriptions=[_columns("template_documento_id", "livello")],
            fetchall_results=[[]],
        )
        mocked_factory.return_value = cursor

        with self.assertRaises(RuntimeError):
            DocumentiRepository().risolvi_template_applicabile(
                sorgente_tipo_id=10,
                emittente_fiscale_id=11,
                tipo_documento_output_id=None,
            )


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
            descriptions=[_columns("id", "uid")],
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
        }
        new_id, uid = DocumentiRepository().create_documento_generato(data)
        self.assertEqual(new_id, 99)
        self.assertTrue(uid.startswith("0190a000"))

        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("INSERT INTO documenti.documenti_generati", sql)
        self.assertIn("RETURNING id, uid", sql)
        # 17 chiavi whitelisted nel data, tutte presenti.
        self.assertEqual(len(params), len(DOCUMENTO_GENERATO_CREATE_COLUMNS))
        self.assertIn("%s::jsonb", sql)
        self.assertIn(json.dumps({"k": "v"}), params)
        self.assertIn(json.dumps({}), params)
        # tx_id NON deve essere in INSERT (Decisione 76).
        self.assertNotIn("tx_id", sql)


class CreateDocumentoGeneratoFileTests(TestCase):
    """Test INSERT documenti_generati_file con whitelist + RETURNING id."""

    # 9. INSERT solo whitelisted; ritorna id RETURNING.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_create_documento_generato_file_inserts_whitelisted_returns_id(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor(
            fetchone_results=[(123,)], descriptions=[_columns("id")],
        )
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
        }
        new_id = DocumentiRepository().create_documento_generato_file(data)
        self.assertEqual(new_id, 123)

        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("INSERT INTO documenti.documenti_generati_file", sql)
        self.assertIn("RETURNING id", sql)
        self.assertEqual(
            len(params), len(DOCUMENTO_GENERATO_FILE_CREATE_COLUMNS),
        )
        self.assertIn("%s::jsonb", sql)
        self.assertIn(json.dumps({}), params)


class EmitEventoDocumentoTests(TestCase):
    """Test INSERT documenti_generati_eventi senza tx_id (Decisione 76)."""

    # 10. INSERT solo whitelisted; NIENTE tx_id; ritorna id.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_emit_evento_documento_inserts_whitelisted_no_tx_id(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor(
            fetchone_results=[(7,)], descriptions=[_columns("id")],
        )
        mocked_factory.return_value = cursor

        data = {
            "documento_generato_id": 99,
            "evento_tipo": "GENERATO",
            "user_id": 5,
            "esito": "OK",
            "messaggio": None,
            "detail": {"size_bytes": 4096},
            "meta": {},
        }
        new_id = DocumentiRepository().emit_evento_documento(data)
        self.assertEqual(new_id, 7)

        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("INSERT INTO documenti.documenti_generati_eventi", sql)
        self.assertIn("RETURNING id", sql)
        self.assertNotIn("tx_id", sql)
        self.assertEqual(len(params), len(EVENTO_DOCUMENTO_CREATE_COLUMNS))
        self.assertIn("%s::jsonb", sql)
        self.assertIn(json.dumps({"size_bytes": 4096}), params)
        self.assertIn(json.dumps({}), params)

    # 10-bis. ⛔ `tx_id` esplicito (Decisione 76) e' fuori whitelist: dal
    #         2026-09-26 e' RuntimeError, non piu' scartato in silenzio.
    #         Nessuna SQL parte.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_emit_evento_documento_tx_id_esplicito_rifiutato(
        self, mocked_factory
    ) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            DocumentiRepository().emit_evento_documento({
                "documento_generato_id": 99,
                "evento_tipo": "GENERATO",
                "tx_id": "would-be-bug",
            })
        self.assertIn("tx_id", str(ctx.exception))
        mocked_factory.assert_not_called()

    # 10-ter. ⭐ Colonna jsonb dichiarata al BB: una STRINGA e' testo JSON
    #         (regola Tid 2026-09-26), passa cosi' com'e' col cast — non
    #         diventa lo scalare stringa che faceva `to_write_param`.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_emit_evento_documento_stringa_jsonb_e_testo_json(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor(
            fetchone_results=[(8,)], descriptions=[_columns("id")],
        )
        mocked_factory.return_value = cursor

        DocumentiRepository().emit_evento_documento({
            "documento_generato_id": 99,
            "evento_tipo": "GENERATO",
            "detail": '{"size_bytes": 1}',
        })

        sql, params = cursor.execute.call_args_list[0].args
        self.assertEqual(params, [99, "GENERATO", '{"size_bytes": 1}'])
        self.assertIn("%s::jsonb", sql)


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
        self.assertIn("WHERE codice_interno = %s", sql)
        self.assertEqual(params, ["PDF_FINALE"])

        cursor_none = _mk_cursor(fetchone_results=[None])
        mocked_factory.return_value = cursor_none
        self.assertIsNone(
            DocumentiRepository().get_tipo_file_documento_by_codice("INESIST"),
        )
