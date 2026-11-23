# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari delle SCRITTURE dei due repository di magazzino. Le
#        anagrafiche scrivono dai VERBI del DB (2026-11-22, R-1 di
#        brief-db-magazzino-tutte-le-scritture-dal-verbo): la chiamata giusta
#        con gli argomenti al loro posto, i campi in jsonb con la regola `meta`
#        NOT NULL (`None` -> `{}`), le colonne ammesse lette dalla funzione
#        del DB. Il documento interno dal 2026-11-23 (R-2): la nascita dal
#        verbo della famiglia, il resto dai verbi comuni col codice della
#        famiglia del DB come primo argomento.
#        Cursore mockato: CI-safe. La giuntura col DB vero e' in `tests/db/`.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) AnagraficheScrittureTests.test_colonne_ammesse_dalla_funzione_del_db
2) AnagraficheScrittureTests.test_meta_none_diventa_oggetto_vuoto
3) AnagraficheScrittureTests.test_ubicazione_modificata_dal_verbo_col_suo_magazzino
4) AnagraficheScrittureTests.test_il_lotto_nasce_dal_verbo_coi_cast
5) AnagraficheScrittureTests.test_il_magazzino_nasce_dal_verbo_senza_emittente
6) DocumentoInternoScrittureTests.test_colonne_ammesse_per_famiglia_parte_e_gesto
7) DocumentoInternoScrittureTests.test_la_testata_nasce_dal_verbo_della_famiglia
8) DocumentoInternoScrittureTests.test_la_riga_modificata_dal_verbo_comune_dentro_la_sua_testata
9) DocumentoInternoScrittureTests.test_la_riga_nasce_con_articolo_e_quantita_come_argomenti
10) DocumentoInternoScrittureTests.test_stato_elimina_e_togli_dai_verbi_comuni
"""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.magazzino.db.anagrafiche_magazzino_repository import AnagraficheMagazzinoRepository
from apps.magazzino.db.famiglie import INVENTARI, RETTIFICHE
from apps.magazzino.db.magazzino_repository import MagazzinoRepository

# I verbi passano tutti da `esegui_verbo` (BB core `sql_write_helpers`): il cursore si
# finge li'.
_VERBO_CONN = "apps.core.db.sql_write_helpers.connection"
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

    # 1. La lista la dice il DB; tabella o gesto fuori elenco e' un errore
    #    del chiamante, prima di qualunque SQL.
    def test_colonne_ammesse_dalla_funzione_del_db(self):
        conn, cursor = _connessione()
        cursor.fetchone.return_value = (["codice", "meta"],)
        with patch(_VERBO_CONN, conn):
            self.assertEqual(self.repo.colonne_ammesse("lotti", "crea"), frozenset({"codice", "meta"}))
            sql, params = cursor.execute.call_args.args
            self.assertIn("magazzino.fn_lotti_colonne_ammesse(%s)", sql)
            self.assertEqual(params, ["crea"])
            cursor.execute.reset_mock()
            for tabella, gesto in (("assets", "crea"), ("lotti", "cancella")):
                with self.assertRaises(RuntimeError):
                    self.repo.colonne_ammesse(tabella, gesto)
        cursor.execute.assert_not_called()

    # 2. `meta` e' `jsonb NOT NULL DEFAULT '{}'`: None scrive `{}`, mai NULL
    #    (nel delta del verbo una chiave a null SVUOTA la colonna).
    def test_meta_none_diventa_oggetto_vuoto(self):
        conn, cursor = _connessione()
        cursor.fetchone.return_value = ({"id": 3},)
        with patch(_VERBO_CONN, conn):
            self.repo.update_magazzino(3, {"meta": None})
        sql, params = cursor.execute.call_args.args
        self.assertIn("magazzino.fn_modifica_magazzino(%s, %s::jsonb)", sql)
        self.assertEqual(params[0], 3)
        self.assertEqual(json.loads(params[1]), {"meta": {}})

    # 3. La coppia (magazzino, ubicazione) e' la risorsa: tutte e due al verbo.
    def test_ubicazione_modificata_dal_verbo_col_suo_magazzino(self):
        conn, cursor = _connessione()
        cursor.fetchone.return_value = ({"id": 9},)
        with patch(_VERBO_CONN, conn):
            self.assertEqual(self.repo.update_ubicazione(3, 9, {"codice": "U2", "parent_id": None}), {"id": 9})
        sql, params = cursor.execute.call_args.args
        self.assertIn("magazzino.fn_modifica_ubicazione(%s, %s, %s::jsonb)", sql)
        self.assertEqual(params[:2], [3, 9])
        self.assertEqual(json.loads(params[2]), {"codice": "U2", "parent_id": None})

    # 4. L'articolo viaggia come stringa, la data come data: cast espliciti.
    def test_il_lotto_nasce_dal_verbo_coi_cast(self):
        conn, cursor = _connessione()
        with patch(_VERBO_CONN, conn):
            self.assertEqual(self.repo.create_lotto(
                _UUID, codice="L1", data_arrivo=date(2026, 9, 1), campi={"data_scadenza": date(2027, 1, 1)},
            ), 42)
        sql, params = cursor.execute.call_args.args
        self.assertIn("magazzino.fn_aggiungi_lotto(%s::uuid, %s, %s::date, %s::jsonb)", sql)
        self.assertEqual(params[:3], [_UUID, "L1", date(2026, 9, 1)])
        self.assertEqual(json.loads(params[3]), {"data_scadenza": "2027-01-01"})

    # 5. L'emittente non viaggia: lo mette il DB dalla sessione.
    def test_il_magazzino_nasce_dal_verbo_senza_emittente(self):
        conn, cursor = _connessione()
        with patch(_VERBO_CONN, conn):
            self.repo.create_magazzino(
                codice="A", descrizione="d", indirizzo_dettaglio_id=4, campi={"predefinito": True},
            )
        sql, params = cursor.execute.call_args.args
        self.assertIn("magazzino.fn_aggiungi_magazzino(%s, %s, %s::bigint, %s::jsonb)", sql)
        self.assertEqual(params[:3], ["A", "d", 4])
        self.assertEqual(json.loads(params[3]), {"predefinito": True})
        self.assertNotIn("emittente", sql)


class DocumentoInternoScrittureTests(SimpleTestCase):
    def setUp(self) -> None:
        self.repo = MagazzinoRepository()

    # 6. La lista la dice il DB per (famiglia, parte, gesto); una parte o un
    #    gesto fuori elenco e' un errore del chiamante, prima di ogni SQL (il
    #    DB risponderebbe con una lista vuota: «niente e' ammesso»).
    def test_colonne_ammesse_per_famiglia_parte_e_gesto(self):
        conn, cursor = _connessione()
        cursor.fetchone.return_value = (["data", "descrizione"],)
        with patch(_VERBO_CONN, conn):
            self.assertEqual(
                self.repo.colonne_ammesse(INVENTARI, "testata", "modifica"), frozenset({"data", "descrizione"}),
            )
            sql, params = cursor.execute.call_args.args
            self.assertIn("magazzino.fn_documento_interno_colonne_ammesse(%s, %s, %s)", sql)
            self.assertEqual(params, ["INVENTARIO", "testata", "modifica"])
            cursor.execute.reset_mock()
            for parte, gesto in (("righe", "crea"), ("riga", "cancella")):
                with self.assertRaises(RuntimeError):
                    self.repo.colonne_ammesse(INVENTARI, parte, gesto)
        cursor.execute.assert_not_called()

    # 7. La nascita e' per famiglia: il magazzino e' l'argomento, il resto in
    #    jsonb (la data come ISO). Un campo assente non viaggia: DEFAULT del DB.
    def test_la_testata_nasce_dal_verbo_della_famiglia(self):
        conn, cursor = _connessione()
        with patch(_VERBO_CONN, conn):
            self.assertEqual(self.repo.create_documento(RETTIFICHE, magazzino_id=7, campi={}), 42)
            sql, params = cursor.execute.call_args.args
            self.assertIn("magazzino.fn_aggiungi_rettifica(%s::bigint, %s::jsonb)", sql)
            self.assertEqual((params[0], json.loads(params[1])), (7, {}))
            self.repo.create_documento(INVENTARI, magazzino_id=7, campi={"data": date(2026, 9, 1)})
        sql, params = cursor.execute.call_args.args
        self.assertIn("magazzino.fn_aggiungi_inventario(%s::bigint, %s::jsonb)", sql)
        self.assertEqual(json.loads(params[1]), {"data": "2026-09-01"})

    # 8. La coppia (documento, riga) e' la chiave del verbo comune, con la
    #    famiglia del DB davanti; una chiave a null svuota.
    def test_la_riga_modificata_dal_verbo_comune_dentro_la_sua_testata(self):
        conn, cursor = _connessione()
        cursor.fetchone.return_value = ({"id": 2},)
        with patch(_VERBO_CONN, conn):
            self.assertEqual(
                self.repo.update_riga(RETTIFICHE, 1, 2, {"qta_delta": Decimal("3"), "lotto_id": None}), {"id": 2},
            )
        sql, params = cursor.execute.call_args.args
        self.assertIn("magazzino.fn_modifica_riga_documento_interno(%s, %s, %s, %s::jsonb)", sql)
        self.assertEqual(params[:3], ["RETTIFICA", 1, 2])
        self.assertEqual(json.loads(params[3]), {"qta_delta": "3", "lotto_id": None})

    # 9. Articolo e quantita' sono argomenti tipizzati del verbo di nascita.
    def test_la_riga_nasce_con_articolo_e_quantita_come_argomenti(self):
        conn, cursor = _connessione()
        with patch(_VERBO_CONN, conn):
            self.repo.create_riga(INVENTARI, 1, articolo_id=_UUID, qta=Decimal("4"), campi={"ubicazione_id": 5})
        sql, params = cursor.execute.call_args.args
        self.assertIn("magazzino.fn_aggiungi_riga_inventario(%s::bigint, %s::uuid, %s::numeric, %s::jsonb)", sql)
        self.assertEqual(params[:3], [1, _UUID, Decimal("4")])
        self.assertEqual(json.loads(params[3]), {"ubicazione_id": 5})

    # 10. Stato, eliminazione e riga tolta: i verbi comuni, la famiglia del DB.
    def test_stato_elimina_e_togli_dai_verbi_comuni(self):
        conn, cursor = _connessione()
        cursor.fetchone.return_value = ("CONFIRM",)
        with patch(_VERBO_CONN, conn):
            self.assertEqual(self.repo.set_stato_documento(INVENTARI, 7, "CONFIRM"), "CONFIRM")
            sql, params = cursor.execute.call_args.args
            self.assertIn("magazzino.fn_cambia_stato_documento_interno(%s, %s, %s)", sql)
            self.assertEqual(params, ["INVENTARIO", 7, "CONFIRM"])
            self.repo.delete_documento(RETTIFICHE, 7)
            sql, params = cursor.execute.call_args.args
            self.assertIn("magazzino.fn_elimina_documento_interno(%s, %s)", sql)
            self.assertEqual(params, ["RETTIFICA", 7])
            self.repo.delete_riga(INVENTARI, 7, 11)
        sql, params = cursor.execute.call_args.args
        self.assertIn("magazzino.fn_togli_riga_documento_interno(%s, %s, %s)", sql)
        self.assertEqual(params, ["INVENTARIO", 7, 11])
