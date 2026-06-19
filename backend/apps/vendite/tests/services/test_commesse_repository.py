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
3) CommesseRepositoryUnitTests.test_upsert_attivita_returns_result
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
13b) CommesseRepositoryUnitTests.test_fetch_pushable_rows_righe_ids_preventivo
13c) CommesseRepositoryUnitTests.test_fetch_pushable_rows_righe_ids_sorgente_non_supportata
14) CommesseRepositoryUnitTests.test_fetch_pushable_rows_maps_shared_columns
15) CommesseRepositoryUnitTests.test_get_or_create_commessa_uses_defaults
16) CommesseRepositoryUnitTests.test_validate_sorgente_map_ok
17) CommesseRepositoryUnitTests.test_validate_sorgente_map_missing_in_map
18) CommesseRepositoryUnitTests.test_list_commesse_emittibili_returns_ids
19) CommesseRepositoryUnitTests.test_list_commesse_emittibili_empty
20) CommesseRepositoryUnitTests.test_list_commessa_attivita_maps_rows
21) CommesseRepositoryUnitTests.test_list_commessa_attivita_empty
22) CommesseRepositoryUnitTests.test_list_active_push_sources
23) CommesseRepositoryUnitTests.test_batch_upsert_attivita_maps_result
24) CommesseRepositoryUnitTests.test_batch_upsert_attivita_empty_list
25) CommesseRepositoryUnitTests.test_upsert_attivita_passes_snapshot_v5_params
26) CommesseRepositoryUnitTests.test_inp_to_jsonb_row_includes_snapshot_v5_keys
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.vendite.db.commesse_repository import (
    BatchUpsertResult,
    CommessaAttivitaInput,
    CommesseRepository,
    PushableRow,
    UpsertAttivitaResult,
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

    # Scopo: Verifica che upsert_attivita chiami la fn DB e restituisca UpsertAttivitaResult.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_upsert_attivita_returns_result(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(77, True))
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
        self.assertIsInstance(result, UpsertAttivitaResult)
        self.assertEqual(result.attivita_id, 77)
        self.assertTrue(result.is_new)
        sql = mock_cursor_factory.return_value.execute.call_args[0][0]
        self.assertIn("fn_upsert_commessa_attivita", sql)

    # Scopo: Verifica default di CommessaAttivitaInput (#3, #4, #5, #10).
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_upsert_attivita_uses_defaults(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(1, False))
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
        # Firma a 3 parametri (commessa_id, only_approved, dry_run): dry_run = params[2].
        self.assertTrue(params[2])
        sql = mock_cursor_factory.return_value.execute.call_args[0][0]
        self.assertNotIn("p_lotto_attivita_id", sql)

    # Scopo: Verifica mapping CommessaStatoResult da fn_get_commessa_stato
    #        (stato + flag governance + tutti i contatori). Colonne nell'ordine
    #        del RETURNS TABLE (senza commessa_id, non selezionato).
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_get_commessa_stato_maps_contatori(self, mock_cursor_factory):
        # stato_commessa_id, stato_commessa, chiude, emittibile, modificabile,
        # policy, fatt_immediata, priorita, ba_id, utility_id, emittente_id,
        # total_attivita, total_approvate, total_non_approvate, total_emesse,
        # total_non_emesse, total_prezzo_da_riallineare, last_update
        mock_cursor_factory.return_value = _mock_cursor(
            fetchone=(
                4, "PRONTA_FATTURAZIONE", False, True, True,
                "DA_DOCUMENTO", False, None, 1001, 2, 555,
                10, 8, 2, 6, 4, 1, None,
            )
        )
        repo = CommesseRepository()
        result = repo.get_commessa_stato(commessa_id=10)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["stato_commessa"], "PRONTA_FATTURAZIONE")
        self.assertTrue(result["emittibile"])
        self.assertTrue(result["modificabile"])
        self.assertFalse(result["chiude_commessa"])
        self.assertEqual(result["total_attivita"], 10)
        self.assertEqual(result["total_approvate"], 8)
        self.assertEqual(result["total_non_approvate"], 2)
        self.assertEqual(result["total_emesse"], 6)
        self.assertEqual(result["total_non_emesse"], 4)
        self.assertEqual(result["total_prezzo_da_riallineare"], 1)
        self.assertIsNone(result["last_update"])

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
            source_types=["PREVENTIVO"],
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
                ["PREVENTIVO", "ORDINE_VENDITA"],
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
        self.assertEqual(result["source_types"], ["PREVENTIVO", "ORDINE_VENDITA"])
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

    # Scopo: righe_ids valorizzato su sorgente PREVENTIVO → chiamata fn a 5
    # parametri con p_righe_ids in coda (smistamento selettivo, brief
    # smistamento C). righe_ids=None → resta la chiamata a 4 parametri.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_fetch_pushable_rows_righe_ids_preventivo(self, mock_cursor_factory):
        cur = _mock_cursor(fetchall=[], description=_ORDINI_COLS)
        mock_cursor_factory.return_value = cur
        repo = CommesseRepository()
        repo.fetch_pushable_rows("PREVENTIVO", sorgente_uid=42, righe_ids=[7, 9])
        sql, params = cur.execute.call_args[0]
        self.assertIn("%s, %s, %s, %s, %s::bigint[]", sql)
        self.assertEqual(params, [None, None, None, 42, [7, 9]])

    # Scopo: righe_ids su sorgente che non lo supporta (fn a 4 parametri) →
    # errore esplicito, niente chiamata SQL malformata.
    def test_fetch_pushable_rows_righe_ids_sorgente_non_supportata(self):
        repo = CommesseRepository()
        with self.assertRaises(Exception):
            repo.fetch_pushable_rows(
                "ORDINE_VENDITA", sorgente_uid=42, righe_ids=[7],
            )

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

    # Scopo: Verifica che list_active_push_sources restituisca codici attivi ordinati per id.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_list_active_push_sources(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(
            fetchall=[("PREVENTIVO",), ("ORDINE_VENDITA",), ("CONTRATTO",)]
        )
        result = CommesseRepository.list_active_push_sources()
        self.assertEqual(result, ["PREVENTIVO", "ORDINE_VENDITA", "CONTRATTO"])
        sql = mock_cursor_factory.return_value.execute.call_args[0][0]
        self.assertIn("PUSH_COMMESSA", sql)
        self.assertIn("attivo", sql)
        self.assertIn("ORDER BY id", sql)

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
        self.assertIsNone(params[4])  # fatturazione_immediata (default: nessun filtro)
        self.assertEqual(params[5], 1000)  # default limit
        self.assertIn("p_fatturazione_immediata", sql)

    # Scopo: Verifica che list_commesse_emittibili restituisca lista vuota se nessun risultato.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_list_commesse_emittibili_empty(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchall=[])
        repo = CommesseRepository()
        result = repo.list_commesse_emittibili()
        self.assertEqual(result, [])

    # Scopo: Verifica che list_emittibili_lane mappi le terne (emittente, tipo_doc, utility,
    # competenza, conteggio), incluso il gruppo emittente NULL, passando il filtro corsia.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_list_emittibili_lane(self, mock_cursor_factory):
        # Colonne nell'ordine della RETURNS TABLE: (emittente, tipo_doc, utility, competenza, total)
        mock_cursor_factory.return_value = _mock_cursor(fetchall=[
            (5, 3, 9, date(2026, 6, 1), 4),
            (5, 7, 9, date(2026, 5, 1), 1),
            (None, 3, 9, date(2026, 6, 1), 2),
        ])
        repo = CommesseRepository()
        result = repo.list_emittibili_lane(
            competenza_mese=date(2026, 6, 1),
            utility_id=9,
            fatturazione_immediata=True,
        )
        self.assertEqual(result, [
            {"emittente_soggetto_ruolo_id": 5, "tipo_doc_fiscale_id": 3, "utility_id": 9,
             "competenza_mese": date(2026, 6, 1), "total_candidate": 4},
            {"emittente_soggetto_ruolo_id": 5, "tipo_doc_fiscale_id": 7, "utility_id": 9,
             "competenza_mese": date(2026, 5, 1), "total_candidate": 1},
            {"emittente_soggetto_ruolo_id": None, "tipo_doc_fiscale_id": 3, "utility_id": 9,
             "competenza_mese": date(2026, 6, 1), "total_candidate": 2},
        ])
        sql = mock_cursor_factory.return_value.execute.call_args[0][0]
        self.assertIn("fn_list_emittibili_lane", sql)
        self.assertIn("utility_id", sql)
        self.assertIn("p_fatturazione_immediata", sql)
        params = mock_cursor_factory.return_value.execute.call_args[0][1]
        self.assertIs(params[4], True)  # fatturazione_immediata

    # Scopo: Verifica che list_commessa_attivita chiami count + fn DB e mappa le righe in dict.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_list_commessa_attivita_maps_rows(self, mock_cursor_factory):
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
        # Due execute: 1) COUNT → fetchone, 2) data → fetchall.
        mock_cursor_factory.return_value = _mock_cursor(
            fetchone=(5,), fetchall=[_row],
        )
        repo = CommesseRepository()
        result = repo.list_commessa_attivita(
            1, stato_emissione="NON_EMESSA", limit=50, offset=0,
        )
        self.assertEqual(result["count"], 5)  # total count, non len(rows)
        row = result["rows"][0]
        self.assertEqual(row["id"], 100)
        self.assertEqual(row["segment_key"], "SEG:001")
        self.assertEqual(row["articolo_id"], str(_art_id))
        self.assertEqual(row["stato_emissione"], "NON_EMESSA")
        self.assertEqual(row["meta"], {"note": "test"})
        # Seconda execute (data query) contiene fn_list_commessa_attivita.
        sql = mock_cursor_factory.return_value.execute.call_args[0][0]
        self.assertIn("fn_list_commessa_attivita", sql)
        params = mock_cursor_factory.return_value.execute.call_args[0][1]
        self.assertEqual(params[0], 1)  # commessa_id
        self.assertEqual(params[1], "NON_EMESSA")  # stato_emissione
        # Prima execute (count query) verifica.
        count_sql = mock_cursor_factory.return_value.execute.call_args_list[0][0][0]
        self.assertIn("COUNT(*)", count_sql)

    # Scopo: Verifica che list_commessa_attivita restituisca count=0 se nessun risultato.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_list_commessa_attivita_empty(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(
            fetchone=(0,), fetchall=[],
        )
        repo = CommesseRepository()
        result = repo.list_commessa_attivita(1)
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["rows"], [])

    # Scopo: Verifica mapping BatchUpsertResult da fn_batch_upsert_commessa_attivita.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_batch_upsert_attivita_maps_result(self, mock_cursor_factory):
        errors_json = '[{"index": 0, "segment_key": "SEG:001", "error": "duplicate"}]'
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(3, 2, 1, errors_json))
        repo = CommesseRepository()
        inp = CommessaAttivitaInput(
            commessa_id=10, segment_key="SEG:001",
            quantita=Decimal("1"), competenza_mese=date(2026, 6, 1),
            articolo_id=None, prezzo_snapshot=None,
        )
        result = repo.batch_upsert_attivita([inp])
        self.assertIsInstance(result, BatchUpsertResult)
        self.assertEqual(result.total_rows, 3)
        self.assertEqual(result.inserted, 2)
        self.assertEqual(result.updated, 1)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0]["segment_key"], "SEG:001")
        sql = mock_cursor_factory.return_value.execute.call_args[0][0]
        self.assertIn("fn_batch_upsert_commessa_attivita", sql)

    # Scopo: Verifica che batch_upsert con lista vuota non chiami il DB.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_batch_upsert_attivita_empty_list(self, mock_cursor_factory):
        repo = CommesseRepository()
        result = repo.batch_upsert_attivita([])
        self.assertEqual(result.total_rows, 0)
        self.assertEqual(result.inserted, 0)
        self.assertEqual(result.updated, 0)
        self.assertEqual(result.errors, [])
        mock_cursor_factory.return_value.execute.assert_not_called()

    # Scopo: F2-BE-11 — upsert_attivita passa i 7 parametri snapshot pricing v5
    #        alla fn DB (posizionali nell'ordine della firma).
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_upsert_attivita_passes_snapshot_v5_params(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(55, True))
        repo = CommesseRepository()
        inp = CommessaAttivitaInput(
            commessa_id=1,
            segment_key="seg",
            quantita=Decimal("1"),
            competenza_mese=date(2026, 6, 1),
            articolo_id=None,
            prezzo_snapshot=Decimal("30"),
            prezzo_base_snapshot=Decimal("25"),
            origine_prezzo="CONTRATTO_LISTINO",
            tipo_variazione_applicata="PERCENTUALE",
            valore_variazione_applicata=Decimal("20"),
            promo_id=None,
            contratto_id=99,
            categoria_cliente_id_snapshot=3,
            classe_utenza_id_snapshot=None,
        )
        repo.upsert_attivita(inp)
        sql, params = mock_cursor_factory.return_value.execute.call_args[0]
        self.assertIn("p_prezzo_base_snapshot", sql)
        self.assertIn("p_origine_prezzo", sql)
        self.assertIn("p_tipo_variazione_applicata", sql)
        self.assertIn("p_valore_variazione_applicata", sql)
        self.assertIn("p_promo_id", sql)
        self.assertIn("p_contratto_id", sql)
        self.assertIn("p_categoria_cliente_id_snapshot", sql)
        self.assertIn("p_classe_utenza_id_snapshot", sql)
        self.assertIn(Decimal("25"), params)
        self.assertIn("CONTRATTO_LISTINO", params)
        self.assertIn(99, params)
        self.assertIn(3, params)

    # Scopo: F2-BE-11 — _inp_to_jsonb_row serializza le 8 chiavi snapshot
    #        pricing v5 (dipendenza: wrapper batch DB deve estrarle).
    def test_inp_to_jsonb_row_includes_snapshot_v5_keys(self):
        inp = CommessaAttivitaInput(
            commessa_id=1,
            segment_key="seg",
            quantita=Decimal("1"),
            competenza_mese=date(2026, 6, 1),
            articolo_id=None,
            prezzo_snapshot=Decimal("30"),
            prezzo_base_snapshot=Decimal("25.0000"),
            origine_prezzo="PROMO",
            tipo_variazione_applicata="VALORE_FISSO",
            valore_variazione_applicata=Decimal("5"),
            promo_id=7,
            contratto_id=None,
            categoria_cliente_id_snapshot=None,
            classe_utenza_id_snapshot=4,
        )
        row = CommesseRepository._inp_to_jsonb_row(inp)
        self.assertEqual(row["prezzo_base_snapshot"], "25.0000")
        self.assertEqual(row["origine_prezzo"], "PROMO")
        self.assertEqual(row["tipo_variazione_applicata"], "VALORE_FISSO")
        self.assertEqual(row["valore_variazione_applicata"], "5")
        self.assertEqual(row["promo_id"], 7)
        self.assertIsNone(row["contratto_id"])
        self.assertIsNone(row["categoria_cliente_id_snapshot"])
        self.assertEqual(row["classe_utenza_id_snapshot"], 4)
