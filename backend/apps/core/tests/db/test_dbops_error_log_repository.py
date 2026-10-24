# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `DbopsRepository.list_error_logs` — la consultazione di
#        `dbops.error_log` (pezzo E). Due meta': la COMPOSIZIONE della query
#        con cursore mockato (whitelist dell'ordinamento, escape del prefisso
#        `LIKE`, i valori nei params) e UNA lettura sul DB provvisto, che
#        prova il JOIN col catalogo e il binding delle colonne per nome — il
#        verso che i mock non vedono.
#
# Indice test:
#   1. `order_by` fuori whitelist -> ripiego `occurred_at DESC, id DESC`, non SQL
#   2. `order_by` in whitelist, senza `order_dir`: la data ripiega DESC
#   3. il prefisso di `function_name` e' un `LIKE` con `_`/`%`/`\` ESCAPATI
#      (l'indice e' `text_pattern_ops`: mai `ILIKE`)
#   4. ogni filtro finisce nei params, mai interpolato; i vuoti sono None
#   5. [DB vero] una lettura reale: JOIN col catalogo, colonne per nome,
#      `context` dict, `tx_id` stringa
# ------------------------------------------------------------
from datetime import date
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.db import transaction
from django.test import SimpleTestCase

from apps.core.db.dbops_repository import (
    ERROR_LOG_SORT_COLUMNS,
    DbopsRepository,
    _prefisso_like,
)
from apps.core.tests.db_e2e import richiedi_db_provvisto
from apps.core.types import ErrorLogRow

# ⚠️ Si sostituisce la `connection` DEL MODULO, non il suo `.cursor`: quello
#    e' l'oggetto condiviso che `SimpleTestCase` avvolge per vietare il DB, e
#    ripristinarlo da un patch lo lascia senza il suo involucro.
_CONN = "apps.core.db._helpers.connection"


def _cursore_vuoto(conn: MagicMock) -> MagicMock:
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.description = []
    cursor.fetchall.return_value = []
    conn.cursor.return_value = cursor
    return cursor


class ErrorLogRepositoryComposizioneTests(SimpleTestCase):
    # 1. Fuori whitelist -> 400 (`order_by_invalid`), e nessuna query: dal
    #    2026-10-20 nessuna lista ripiega in silenzio sul default (brief-be-verifica-documentazione-api §A1).
    @patch(_CONN)
    def test_order_by_fuori_whitelist_e_rifiutato(self, conn) -> None:
        cursor = _cursore_vuoto(conn)
        for verso in (None, "asc"):
            with self.subTest(verso=verso), self.assertRaisesRegex(ValueError, "order_by_invalid"):
                DbopsRepository().list_error_logs(order_by="1; DROP TABLE x", order_dir=verso)
        cursor.execute.assert_not_called()

    # 2. In whitelist e senza verso: la data ripiega DESC (regola di Tid).
    @patch(_CONN)
    def test_data_senza_verso_ripiega_desc(self, conn) -> None:
        cursor = _cursore_vuoto(conn)
        DbopsRepository().list_error_logs(order_by="occurred_at", order_dir=None)
        self.assertIn("ORDER BY e.occurred_at DESC NULLS LAST, e.id DESC",
                      cursor.execute.call_args.args[0])
        DbopsRepository().list_error_logs(order_by="codice", order_dir=None)
        self.assertIn("ORDER BY m.codice ASC NULLS FIRST, e.id ASC",
                      cursor.execute.call_args.args[0])

    # 3. Il prefisso: `LIKE`, con i jolly resi letterali.
    def test_prefisso_like_escapa_i_jolly(self) -> None:
        self.assertEqual(_prefisso_like("fn_get_lotto"), "fn\\_get\\_lotto%")
        self.assertEqual(_prefisso_like("a%b"), "a\\%b%")
        self.assertEqual(_prefisso_like("a\\b"), "a\\\\b%")

    @patch(_CONN)
    def test_function_name_e_un_like_a_prefisso(self, conn) -> None:
        cursor = _cursore_vuoto(conn)
        DbopsRepository().list_error_logs(function_name=" fn_get_lotto ")
        sql, params = cursor.execute.call_args.args
        self.assertIn("e.function_name LIKE %s", sql)
        self.assertNotIn("ILIKE", sql)
        self.assertIn("fn\\_get\\_lotto%", params)

    # 4. I valori viaggiano nei params; i filtri assenti sono None.
    @patch(_CONN)
    def test_i_filtri_stanno_nei_params(self, conn) -> None:
        cursor = _cursore_vuoto(conn)
        DbopsRepository().list_error_logs(
            area="vendite", codice="E_X", tx_id="123e4567-e89b-12d3-a456-426614174000",
            data_da="2026-09-01", data_a="2026-09-19", limit=25, offset=50,
        )
        filtri = [
            "vendite", "vendite", None, None, "E_X", "E_X",
            "123e4567-e89b-12d3-a456-426614174000", "123e4567-e89b-12d3-a456-426614174000",
            # Le date arrivano ISO e vanno al BB del giorno aziendale come `date`.
            date(2026, 9, 1), date(2026, 9, 1), date(2026, 9, 19), date(2026, 9, 19),
        ]
        # La PAGINA e' la prima execute.
        sql, params = cursor.execute.call_args_list[0].args
        self.assertNotIn("vendite", sql)
        self.assertNotIn("E_X", sql)
        self.assertEqual(params, [*filtri, 25, 50])
        # ⭐ Offset 50 e pagina vuota: il totale lo dice il conteggio di ripiego
        #    (2026-09-28), con lo stesso WHERE e senza LIMIT/OFFSET. Senza, oltre
        #    l'ultima pagina il totale usciva 0 e la lista non sapeva tornare.
        sql_conto, params_conto = cursor.execute.call_args_list[1].args
        self.assertIn("SELECT COUNT(*) FROM dbops.error_log e", sql_conto)
        self.assertNotIn("LIMIT", sql_conto)
        self.assertEqual(params_conto, filtri)
        # La whitelist e' chiavata sui campi FISICI del catalogo.
        self.assertEqual(
            set(ERROR_LOG_SORT_COLUMNS),
            {"occurred_at", "area", "function_name", "codice", "classe", "tx_id"},
        )


class ErrorLogRepositoryDbTests(TestCase):
    """Una lettura vera: il JOIN col catalogo e le colonne per nome."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # 5. La query lega sulle tabelle vere, e la riga ha TUTTE le chiavi del
    #    contratto. ⚠️ Non pretende righe: su un DB nuovo il registro puo'
    #    essere vuoto, e qui si prova la GIUNTURA (la SQL non fallisce, il
    #    totale e' un numero), non il contenuto. Se c'e' almeno una riga si
    #    controlla anche la forma dei valori.
    def test_lettura_reale_col_catalogo(self) -> None:
        with transaction.atomic():
            righe, totale = DbopsRepository().list_error_logs(
                limit=3, offset=0, order_by="occurred_at", order_dir="desc",
            )
            # E ogni filtro della whitelist si ATTRAVERSA (contratto dichiarato
            # = contratto provato): nessuno deve rispondere con un errore SQL.
            for filtro in (
                {"area": "vendite"}, {"function_name": "fn_"},
                {"codice": "E_PARAMETRO_INVALIDO"},
                {"tx_id": "123e4567-e89b-12d3-a456-426614174000"},
                {"data_da": "2026-01-01", "data_a": "2026-12-31"},
            ):
                DbopsRepository().list_error_logs(limit=1, **filtro)
            transaction.set_rollback(True)
        self.assertIsInstance(totale, int)
        self.assertLessEqual(len(righe), 3)
        for riga in righe:
            self.assertEqual(set(riga), set(ErrorLogRow.__annotations__))
            self.assertIsInstance(riga["occurred_at"], str)
            self.assertTrue(riga["context"] is None or isinstance(riga["context"], dict))
            self.assertTrue(riga["tx_id"] is None or isinstance(riga["tx_id"], str))
            self.assertTrue(riga["codice"].startswith("E_"))
