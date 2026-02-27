# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari CommesseRepository.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) CommesseRepositoryUnitTests.test_get_or_create_commessa_returns_int
2) CommesseRepositoryUnitTests.test_link_sorgente_returns_int
3) CommesseRepositoryUnitTests.test_upsert_attivita_returns_int
4) CommesseRepositoryUnitTests.test_upsert_attivita_uses_defaults
5) CommesseRepositoryUnitTests.test_emit_attivita_fatturabili_maps_result
6) CommesseRepositoryUnitTests.test_emit_attivita_fatturabili_dry_run_zero_writes
7) CommesseRepositoryUnitTests.test_get_commessa_stato_maps_contatori
8) CommesseRepositoryUnitTests.test_get_commessa_stato_returns_none_when_not_found
9) CommesseRepositoryUnitTests.test_log_push_run_returns_int
10) CommesseRepositoryUnitTests.test_get_push_log_maps_row
11) CommesseRepositoryUnitTests.test_get_push_log_returns_none_when_not_found
12) CommesseRepositoryUnitTests.test_fetch_pushable_rows_calls_correct_fn
13) CommesseRepositoryUnitTests.test_fetch_pushable_rows_unknown_sorgente_raises
14) CommesseRepositoryUnitTests.test_fetch_pushable_rows_maps_shared_columns
15) CommesseRepositoryUnitTests.test_get_or_create_commessa_uses_defaults
16) CommesseRepositoryUnitTests.test_validate_sorgente_map_ok
17) CommesseRepositoryUnitTests.test_validate_sorgente_map_missing_in_map
18) CommesseRepositoryUnitTests.test_list_commesse_emittibili_returns_ids
19) CommesseRepositoryUnitTests.test_list_commesse_emittibili_empty
20) CommesseRepositoryUnitTests.test_list_commessa_attivita_maps_rows
21) CommesseRepositoryUnitTests.test_list_commessa_attivita_empty
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.vendite.db.commesse_repository import (
    CommessaAttivitaInput,
    CommesseRepository,
    PushableRow,
    _SORGENTE_FN_MAP,
)


def _mock_cursor(fetchone=None, fetchall=None, description=None):
    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = fetchone
    cursor.fetchall.return_value = fetchall or []
    cursor.description = description
    return cursor


# Colonne restituite da fn_list_ordini_da_pushare (29 totali: 3 source + 26 shared).
_ORDINI_COLS = [
    ("ordine_id",), ("ordine_uid",), ("riga_id",),
    ("billing_account_id",), ("utility_id",), ("emittente_soggetto_ruolo_id",),
    ("competenza_dal",), ("competenza_al",), ("fatturazione_immediata",),
    ("sorgente_tipo_id",), ("sorgente_uid",), ("segment_key",),
    ("articolo_id",), ("istanza_utility_id",), ("data_attivita",),
    ("uom_id",), ("quantita",), ("qta_operativa",),
    ("uom_operativa_id",), ("factor_to_base",), ("competenza_mese",),
    ("prezzo_snapshot",), ("prezzo_bloccato",), ("pricing_mode",),
    ("tipo_movimento",), ("tipo_consumo",), ("valuta_id",),
    ("meta",), ("tipo_doc_fiscale_id",),
]

# Tupla di test che simula una riga ordine.
_ORDINI_ROW = (
    # 3 source-specific
    100, "uid-ordine-001", 200,
    # 26 shared
    1, 2, 3,
    date(2026, 6, 1), date(2026, 6, 30), False,
    6, "uid-ordine-001", "ORD:uid-ordine-001:R:200",
    "art-uuid-001", 4, date(2026, 6, 1),
    None, Decimal("10.0"), Decimal("10.0"),
    None, Decimal("1"), date(2026, 6, 1),
    Decimal("22.50"), True, "FIXED",
    "NORMALE", "CONGUAGLIO", 1,
    {"tipo_commessa": "AUTO", "policy_fatturazione": "DA_DOCUMENTO"},
    7,  # tipo_doc_fiscale_id
)


class CommesseRepositoryUnitTests(TestCase):

    # Scopo: Verifica che get_or_create_commessa chiami la funzione DB e restituisca int.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_get_or_create_commessa_returns_int(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(42,))
        repo = CommesseRepository()
        result = repo.get_or_create_commessa(
            billing_account_id=1,
            utility_id=2,
            tipo_commessa="AUTO",
            policy_fatturazione="DA_DOCUMENTO",
            fatturazione_immediata=False,
            priorita_operativa="NORMALE",
            emittente_soggetto_ruolo_id=3,
            competenza_dal=date(2026, 6, 1),
            competenza_al=date(2026, 6, 30),
        )
        self.assertEqual(result, 42)
        sql = mock_cursor_factory.return_value.execute.call_args[0][0]
        self.assertIn("fn_get_or_create_commessa", sql)

    # Scopo: Verifica che get_or_create_commessa accetti i default (#7).
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_get_or_create_commessa_uses_defaults(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(1,))
        repo = CommesseRepository()
        result = repo.get_or_create_commessa(billing_account_id=1)
        self.assertEqual(result, 1)
        params = mock_cursor_factory.return_value.execute.call_args[0][1]
        # Verifica default: tipo_commessa="AUTO", priorita_operativa="NORMALE"
        self.assertEqual(params[2], "AUTO")
        self.assertEqual(params[5], "NORMALE")

    # Scopo: Verifica che link_sorgente chiami la funzione DB e restituisca int.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_link_sorgente_returns_int(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(99,))
        repo = CommesseRepository()
        result = repo.link_sorgente(
            commessa_id=10,
            sorgente_tipo_id=5,
            sorgente_uid="PREV-001",
        )
        self.assertEqual(result, 99)
        sql = mock_cursor_factory.return_value.execute.call_args[0][0]
        self.assertIn("fn_link_commessa_sorgente", sql)

    # Scopo: Verifica che upsert_attivita chiami la funzione DB e restituisca int.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_upsert_attivita_returns_int(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(77,))
        repo = CommesseRepository()
        inp = CommessaAttivitaInput(
            commessa_id=10,
            segment_key="10_2026-06_BASE",
            quantita=Decimal("2.0"),
            competenza_mese=date(2026, 6, 1),
            articolo_id=1,
            prezzo_snapshot=Decimal("22.10"),
            uom_id=1,
            tipo_doc_fiscale_id=1,
            valuta_id=1,
            prezzo_bloccato=True,
            stato_approvazione="APPROVATA",
            tipo_consumo="ACCONTO",
        )
        result = repo.upsert_attivita(inp)
        self.assertEqual(result, 77)
        sql = mock_cursor_factory.return_value.execute.call_args[0][0]
        self.assertIn("fn_upsert_commessa_attivita", sql)

    # Scopo: Verifica default di CommessaAttivitaInput (#3, #4, #5, #10).
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_upsert_attivita_uses_defaults(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(1,))
        repo = CommesseRepository()
        inp = CommessaAttivitaInput(
            commessa_id=10,
            segment_key="seg",
            quantita=Decimal("1"),
            competenza_mese=date(2026, 6, 1),
            articolo_id=None,
            prezzo_snapshot=None,
        )
        # Verifica default dei campi ristrutturati.
        self.assertIsNone(inp.uom_id)
        self.assertIsNone(inp.tipo_doc_fiscale_id)
        self.assertFalse(inp.prezzo_da_riallineare)
        self.assertEqual(inp.stato_approvazione, "BOZZA")
        self.assertEqual(inp.stato_emissione, "NON_EMESSA")
        self.assertEqual(inp.tipo_movimento, "NORMALE")
        self.assertEqual(inp.tipo_consumo, "CONGUAGLIO")
        repo.upsert_attivita(inp)

    # Scopo: Verifica mapping CommessaEmitResult da fn_emit_attivita_fatturabili_da_commessa.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_emit_attivita_fatturabili_maps_result(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(5, 3, 2))
        repo = CommesseRepository()
        result = repo.emit_attivita_fatturabili(commessa_id=10)
        self.assertEqual(result["total_candidate"], 5)
        self.assertEqual(result["inserted_rows"], 3)
        self.assertEqual(result["updated_rows"], 2)
        sql = mock_cursor_factory.return_value.execute.call_args[0][0]
        self.assertIn("fn_emit_attivita_fatturabili_da_commessa", sql)

    # Scopo: Verifica che dry_run=True venga passato e non produca righe scritte.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_emit_attivita_fatturabili_dry_run_zero_writes(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(3, 3, 0))
        repo = CommesseRepository()
        result = repo.emit_attivita_fatturabili(commessa_id=10, dry_run=True)
        self.assertEqual(result["total_candidate"], 3)
        params = mock_cursor_factory.return_value.execute.call_args[0][1]
        self.assertTrue(params[3])

    # Scopo: Verifica mapping CommessaStatoResult da fn_get_commessa_stato.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_get_commessa_stato_maps_contatori(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(10, 8, 6))
        repo = CommesseRepository()
        result = repo.get_commessa_stato(commessa_id=10)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["total_attivita"], 10)
        self.assertEqual(result["total_approvate"], 8)
        self.assertEqual(result["total_emesse"], 6)

    # Scopo: Verifica che get_commessa_stato restituisca None quando la commessa non esiste.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_get_commessa_stato_returns_none_when_not_found(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=None)
        repo = CommesseRepository()
        result = repo.get_commessa_stato(commessa_id=999)
        self.assertIsNone(result)

    # Scopo: Verifica che log_push_run chiami fn_log_commessa_push_run e restituisca int.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_log_push_run_returns_int(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(55,))
        repo = CommesseRepository()
        result = repo.log_push_run(
            stato="COMPLETATO",
            dry_run=False,
            source_types=["HandlerPreventivi"],
            risultato={"HandlerPreventivi": {"created": 3, "errors": []}},
            durata_ms=1200,
        )
        self.assertEqual(result, 55)
        sql = mock_cursor_factory.return_value.execute.call_args[0][0]
        self.assertIn("fn_log_commessa_push_run", sql)

    # Scopo: Verifica mapping CommessaPushLogRow da SELECT commesse_push_log.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_get_push_log_maps_row(self, mock_cursor_factory):
        ts = datetime(2026, 2, 24, 10, 0, 0, tzinfo=timezone.utc)
        mock_cursor_factory.return_value = _mock_cursor(
            fetchone=(
                55, ts, False,
                ["HandlerPreventivi", "HandlerOrdini"],
                '{"HandlerPreventivi": {"created": 3}}',
                "COMPLETATO", 1200,
            )
        )
        repo = CommesseRepository()
        result = repo.get_push_log(55)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["id"], 55)
        self.assertEqual(result["stato"], "COMPLETATO")
        self.assertEqual(result["durata_ms"], 1200)
        self.assertFalse(result["dry_run"])
        self.assertEqual(result["source_types"], ["HandlerPreventivi", "HandlerOrdini"])
        self.assertIn("HandlerPreventivi", result["risultato"] or {})

    # Scopo: Verifica che get_push_log restituisca None quando il log non esiste.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_get_push_log_returns_none_when_not_found(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=None)
        repo = CommesseRepository()
        result = repo.get_push_log(999)
        self.assertIsNone(result)

    # Scopo: Verifica che fetch_pushable_rows chiami la fn SQL corretta per ogni sorgente.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_fetch_pushable_rows_calls_correct_fn(self, mock_cursor_factory):
        for codice, fn_expected in _SORGENTE_FN_MAP.items():
            cur = _mock_cursor(fetchall=[], description=_ORDINI_COLS)
            mock_cursor_factory.return_value = cur
            repo = CommesseRepository()
            repo.fetch_pushable_rows(codice)
            sql = cur.execute.call_args[0][0]
            self.assertIn(fn_expected, sql, f"fn per {codice} non trovata nel SQL")

    # Scopo: Verifica che sorgente_codice sconosciuto lanci errore.
    def test_fetch_pushable_rows_unknown_sorgente_raises(self):
        repo = CommesseRepository()
        with self.assertRaises(Exception):
            repo.fetch_pushable_rows("SCONOSCIUTO")

    # Scopo: Verifica mapping colonne condivise in PushableRow.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_fetch_pushable_rows_maps_shared_columns(self, mock_cursor_factory):
        cur = _mock_cursor(
            fetchall=[_ORDINI_ROW],
            description=_ORDINI_COLS,
        )
        mock_cursor_factory.return_value = cur
        repo = CommesseRepository()
        rows = repo.fetch_pushable_rows("ORDINE_VENDITA")
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertIsInstance(row, PushableRow)
        self.assertEqual(row.billing_account_id, 1)
        self.assertEqual(row.utility_id, 2)
        self.assertEqual(row.segment_key, "ORD:uid-ordine-001:R:200")
        self.assertIsNone(row.uom_id)
        self.assertEqual(row.quantita, Decimal("10.0"))
        self.assertEqual(row.prezzo_snapshot, Decimal("22.50"))
        self.assertTrue(row.prezzo_bloccato)
        self.assertEqual(row.tipo_doc_fiscale_id, 7)
        self.assertEqual(row.meta["tipo_commessa"], "AUTO")

    # Scopo: Verifica validate_sorgente_map senza warning quando DB e map allineati.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_validate_sorgente_map_ok(self, mock_cursor_factory):
        cur = _mock_cursor(fetchall=[
            ("PREVENTIVO",), ("ORDINE_VENDITA",), ("ATTIVITA_CONSUMI",),
            ("CONTRATTO",), ("DDT_VENDITA",),
        ])
        mock_cursor_factory.return_value = cur
        warnings = CommesseRepository.validate_sorgente_map()
        self.assertEqual(warnings, [])

    # Scopo: Verifica warning quando DB ha sorgente non presente nella map.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_validate_sorgente_map_missing_in_map(self, mock_cursor_factory):
        cur = _mock_cursor(fetchall=[
            ("PREVENTIVO",), ("ORDINE_VENDITA",), ("ATTIVITA_CONSUMI",),
            ("CONTRATTO",), ("DDT_VENDITA",), ("NUOVA_SORGENTE",),
        ])
        mock_cursor_factory.return_value = cur
        warnings = CommesseRepository.validate_sorgente_map()
        self.assertEqual(len(warnings), 1)
        self.assertIn("NUOVA_SORGENTE", warnings[0])

    # Scopo: Verifica che list_commesse_emittibili chiami la fn DB e restituisca list[int].
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_list_commesse_emittibili_returns_ids(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchall=[(10,), (20,), (30,)])
        repo = CommesseRepository()
        result = repo.list_commesse_emittibili(
            competenza_mese=date(2026, 6, 1),
            billing_account_id=1,
            utility_id=2,
            emittente_soggetto_ruolo_id=3,
        )
        self.assertEqual(result, [10, 20, 30])
        sql = mock_cursor_factory.return_value.execute.call_args[0][0]
        self.assertIn("fn_list_commesse_emittibili", sql)
        params = mock_cursor_factory.return_value.execute.call_args[0][1]
        self.assertEqual(params[0], date(2026, 6, 1))
        self.assertEqual(params[1], 1)
        self.assertEqual(params[2], 2)
        self.assertEqual(params[3], 3)
        self.assertEqual(params[4], 1000)  # default limit

    # Scopo: Verifica che list_commesse_emittibili restituisca lista vuota se nessun risultato.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_list_commesse_emittibili_empty(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchall=[])
        repo = CommesseRepository()
        result = repo.list_commesse_emittibili()
        self.assertEqual(result, [])

    # Scopo: Verifica che list_commessa_attivita chiami la fn DB e mappa le righe in dict.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_list_commessa_attivita_maps_rows(self, mock_cursor_factory):
        _attivita_desc = [
            ("id",), ("commessa_id",), ("segment_key",), ("articolo_id",),
            ("istanza_utility_id",), ("data_attivita",), ("uom_id",), ("quantita",),
            ("competenza_mese",), ("competenza_dal",), ("competenza_al",),
            ("prezzo_snapshot",), ("prezzo_bloccato",), ("prezzo_da_riallineare",),
            ("stato_approvazione",), ("stato_emissione",), ("sorgente_tipo_id",),
            ("sorgente_codice",), ("meta",), ("data_update",),
        ]
        import uuid
        from datetime import datetime
        _art_id = uuid.uuid4()
        _row = (
            100, 1, "SEG:001", _art_id,
            None, date(2026, 2, 1), 5, Decimal("10.00"),
            date(2026, 2, 1), date(2026, 2, 1), date(2026, 2, 28),
            Decimal("22.50"), True, False,
            "APPROVATA", "NON_EMESSA", 3,
            "PREVENTIVO", {"note": "test"}, datetime(2026, 2, 26, 10, 0, 0),
        )
        mock_cursor_factory.return_value = _mock_cursor(
            fetchall=[_row], description=_attivita_desc,
        )
        repo = CommesseRepository()
        result = repo.list_commessa_attivita(
            1, stato_emissione="NON_EMESSA", limit=50, offset=0,
        )
        self.assertEqual(result["count"], 1)
        row = result["rows"][0]
        self.assertEqual(row["id"], 100)
        self.assertEqual(row["segment_key"], "SEG:001")
        self.assertEqual(row["articolo_id"], str(_art_id))
        self.assertEqual(row["stato_emissione"], "NON_EMESSA")
        self.assertEqual(row["meta"], {"note": "test"})
        sql = mock_cursor_factory.return_value.execute.call_args[0][0]
        self.assertIn("fn_list_commessa_attivita", sql)
        params = mock_cursor_factory.return_value.execute.call_args[0][1]
        self.assertEqual(params[0], 1)  # commessa_id
        self.assertEqual(params[1], "NON_EMESSA")  # stato_emissione

    # Scopo: Verifica che list_commessa_attivita restituisca count=0 se nessun risultato.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_list_commessa_attivita_empty(self, mock_cursor_factory):
        _attivita_desc = [("id",), ("commessa_id",)]
        mock_cursor_factory.return_value = _mock_cursor(
            fetchall=[], description=_attivita_desc,
        )
        repo = CommesseRepository()
        result = repo.list_commessa_attivita(1)
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["rows"], [])
