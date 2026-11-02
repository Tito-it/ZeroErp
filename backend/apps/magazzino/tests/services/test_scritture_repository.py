# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari delle SCRITTURE dei due repository di magazzino dopo la
#        migrazione sui BB core (2026-09-26): la whitelist RIGIDA (una chiave
#        fuori lista e' `RuntimeError`, non piu' uno scarto silenzioso), la
#        regola `meta` NOT NULL (`None` -> `{}`), il WHERE legato al padre
#        (ubicazione -> magazzino, riga -> testata), il cast uuid del lotto e
#        l'INSERT della testata che lascia al DB il DEFAULT di `data`.
#        Cursore mockato: CI-safe. La giuntura col DB vero e' in `tests/db/`.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) AnagraficheScrittureTests.test_chiave_fuori_whitelist_e_runtime_error
2) AnagraficheScrittureTests.test_meta_none_diventa_oggetto_vuoto
3) AnagraficheScrittureTests.test_ubicazione_aggiornata_dentro_il_suo_magazzino
4) AnagraficheScrittureTests.test_il_lotto_nasce_col_cast_uuid_dell_articolo
5) AnagraficheScrittureTests.test_patch_vuoto_non_esegue_niente
6) DocumentoInternoScrittureTests.test_descrizione_sulla_rettifica_e_runtime_error
7) DocumentoInternoScrittureTests.test_la_testata_lascia_al_db_la_data_assente
8) DocumentoInternoScrittureTests.test_la_riga_aggiornata_dentro_la_sua_testata
9) DocumentoInternoScrittureTests.test_la_fk_della_riga_vince_sul_payload
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.magazzino.db.anagrafiche_magazzino_repository import AnagraficheMagazzinoRepository
from apps.magazzino.db.famiglie import INVENTARI, RETTIFICHE
from apps.magazzino.db.magazzino_repository import MagazzinoRepository

_BB_CONN = "apps.core.db.sql_write_helpers.connection"
_ANA_CONN = "apps.magazzino.db.anagrafiche_magazzino_repository.connection"
_MAG_CONN = "apps.magazzino.db.magazzino_repository.connection"
_UUID = "0190a1b2-0000-7000-8000-000000000001"


# Scopo: un `connection` finto il cui cursore restituisce `RETURNING id` = 42
#        e `rowcount` = 1; ritorna (connection, cursor).
def _connessione() -> tuple[MagicMock, MagicMock]:
    cursor = MagicMock()
    cursor.fetchone.return_value = (42,)
    cursor.description = [SimpleNamespace(name="id")]
    cursor.rowcount = 1
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    return conn, cursor


class AnagraficheScrittureTests(SimpleTestCase):
    def setUp(self) -> None:
        self.repo = AnagraficheMagazzinoRepository()

    # 1. Prima veniva SCARTATA in silenzio: ora e' l'allarme tecnico (500).
    def test_chiave_fuori_whitelist_e_runtime_error(self):
        conn, cursor = _connessione()
        with patch(_BB_CONN, conn), patch(_ANA_CONN, conn):
            for chiamata in (
                lambda: self.repo.create_magazzino({"codice": "A", "emittente_fiscale_id": 1}),
                lambda: self.repo.update_magazzino(3, {"emittente_fiscale_id": 1}),
                lambda: self.repo.update_ubicazione(3, 9, {"magazzino_id": 4}),
                lambda: self.repo.update_lotto(5, {"articolo_id": _UUID}),
            ):
                with self.assertRaises(RuntimeError):
                    chiamata()
        cursor.execute.assert_not_called()

    # 2. `meta` e' `jsonb NOT NULL DEFAULT '{}'`: None scrive `{}`, mai NULL.
    def test_meta_none_diventa_oggetto_vuoto(self):
        conn, cursor = _connessione()
        with patch(_BB_CONN, conn):
            self.repo.update_magazzino(3, {"meta": None})
        sql, params = cursor.execute.call_args.args
        self.assertIn("meta = %s::jsonb", sql)
        self.assertEqual(json.loads(params[0]), {})

    # 3. Il WHERE lega l'ubicazione al SUO magazzino (un id altrui = 0 righe).
    def test_ubicazione_aggiornata_dentro_il_suo_magazzino(self):
        conn, cursor = _connessione()
        with patch(_ANA_CONN, conn):
            self.assertTrue(self.repo.update_ubicazione(3, 9, {"codice": "U2", "parent_id": None}))
        sql, params = cursor.execute.call_args.args
        self.assertIn("WHERE id = %s AND magazzino_id = %s", sql)
        self.assertEqual(params, ["U2", None, 9, 3])

    # 4. L'articolo del lotto viaggia come stringa: cast esplicito a uuid.
    def test_il_lotto_nasce_col_cast_uuid_dell_articolo(self):
        conn, cursor = _connessione()
        with patch(_BB_CONN, conn):
            self.assertEqual(self.repo.create_lotto(_UUID, {"codice": "L1", "meta": {"a": 1}}), 42)
        sql, params = cursor.execute.call_args.args
        self.assertIn("%s::uuid", sql)
        self.assertIn("%s::jsonb", sql)
        self.assertIn(_UUID, params)

    # 5. Niente da aggiornare: nessuna SQL (e nessun UPDATE senza SET).
    def test_patch_vuoto_non_esegue_niente(self):
        conn, cursor = _connessione()
        with patch(_BB_CONN, conn), patch(_ANA_CONN, conn):
            self.assertFalse(self.repo.update_ubicazione(3, 9, {}))
            self.assertFalse(self.repo.update_lotto(5, {}))
        cursor.execute.assert_not_called()


class DocumentoInternoScrittureTests(SimpleTestCase):
    def setUp(self) -> None:
        self.repo = MagazzinoRepository()

    # 6. La rettifica non ha `descrizione`: prima la chiave era scartata.
    def test_descrizione_sulla_rettifica_e_runtime_error(self):
        conn, cursor = _connessione()
        with patch(_BB_CONN, conn):
            with self.assertRaises(RuntimeError):
                self.repo.update_documento(RETTIFICHE, 1, {"descrizione": "x"})
            self.assertTrue(self.repo.update_documento(INVENTARI, 1, {"descrizione": "x"}))
        self.assertEqual(cursor.execute.call_count, 1)

    # 7. `data` e `descrizione` assenti non viaggiano (DEFAULT del DB);
    #    `meta` viaggia sempre, `{}` se None.
    def test_la_testata_lascia_al_db_la_data_assente(self):
        conn, cursor = _connessione()
        with patch(_BB_CONN, conn):
            doc_id = self.repo.create_documento(
                INVENTARI, magazzino_id=7, data=None, descrizione=None, meta=None,
            )
        self.assertEqual(doc_id, 42)
        sql, params = cursor.execute.call_args.args
        self.assertIn("INSERT INTO magazzino.inventari (magazzino_id, meta)", sql)
        self.assertEqual(params[0], 7)
        self.assertEqual(json.loads(params[1]), {})

    # 8. Il WHERE lega la riga alla SUA testata, con la FK della famiglia.
    def test_la_riga_aggiornata_dentro_la_sua_testata(self):
        conn, cursor = _connessione()
        with patch(_MAG_CONN, conn):
            self.repo.update_riga(RETTIFICHE, 1, 2, {"qta_delta": 3, "motivo": " ROTTURA "})
        sql, params = cursor.execute.call_args.args
        self.assertIn("magazzino.rettifiche_righe", sql)
        self.assertIn("WHERE id = %s AND rettifica_id = %s", sql)
        self.assertEqual(params, [3, "ROTTURA", 2, 1])
        with patch(_MAG_CONN, conn), self.assertRaises(RuntimeError):
            self.repo.update_riga(INVENTARI, 1, 2, {"motivo": "x"})

    # 9. La testata viene dall'argomento, non dal payload.
    def test_la_fk_della_riga_vince_sul_payload(self):
        conn, cursor = _connessione()
        with patch(_BB_CONN, conn):
            self.repo.create_riga(INVENTARI, 1, {"articolo_id": _UUID, "qta_contata": 4, "inventario_id": 99})
        sql, params = cursor.execute.call_args.args
        self.assertIn("inventario_id", sql)
        self.assertIn(1, params)
        self.assertNotIn(99, params)
