# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per `compute_non_editable_fields` (Fase 4).
#        Mock di `LockColumnsRepository.list_non_editable`, no DB.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_compute_db_only — solo registro DB, no gap
 2) test_compute_gaps_only — DB vuoto, solo gap (es. tabella non registrata)
 3) test_compute_db_plus_gaps_dedup — unione deduplicata DB + gap
 4) test_compute_returns_sorted — output sempre ordinato alfabeticamente
 5) test_compute_accepts_iterable_gaps — tupla/lista/set/frozenset accettati
 5-bis) test_compute_con_record_legge_i_condizionali — con `record_id` il
    BB legge il ramo per record (ex copia privata di catalogo, 2026-11-09)
 6) test_errore_db_non_resta_in_cache — il fallback vuoto non entra in cache:
    la lettura dopo il guasto torna al DB (regressione 2026-11-09)
"""

from unittest import TestCase
from unittest.mock import patch


HELPER = "apps.core.services.non_editable_fields_helper"
LOCK_REPO = f"{HELPER}.LockColumnsRepository"


class TestComputeNonEditableFields(TestCase):
    """Test compute_non_editable_fields(schema, table, *, gaps=())."""

    @patch(f"{LOCK_REPO}.list_non_editable")
    def test_compute_db_only(self, mock_list):
        # Solo registro DB: la lista contiene esattamente le colonne ritornate.
        from apps.core.services.non_editable_fields_helper import compute_non_editable_fields

        mock_list.return_value = ("codice", "data_insert")

        result = compute_non_editable_fields("anagrafiche", "emittenti_fiscali")

        self.assertEqual(result, ["codice", "data_insert"])
        mock_list.assert_called_once_with("anagrafiche", "emittenti_fiscali")

    @patch(f"{LOCK_REPO}.list_non_editable")
    def test_compute_gaps_only(self, mock_list):
        # DB vuoto (tabella non registrata): solo i gap dominio.
        from apps.core.services.non_editable_fields_helper import compute_non_editable_fields

        mock_list.return_value = ()

        result = compute_non_editable_fields(
            "anagrafiche", "categorie_clienti_listini",
            gaps=("categoria_cliente_id", "utility_id"),
        )

        self.assertEqual(result, ["categoria_cliente_id", "utility_id"])

    @patch(f"{LOCK_REPO}.list_non_editable")
    def test_compute_db_plus_gaps_dedup(self, mock_list):
        # Unione deduplicata: se DB e gap sovrappongono, niente duplicati.
        from apps.core.services.non_editable_fields_helper import compute_non_editable_fields

        mock_list.return_value = ("codice", "soggetto_id")

        result = compute_non_editable_fields(
            "anagrafiche", "emittenti_fiscali",
            gaps=("codice", "regime_fiscale_rf"),  # 'codice' duplicato
        )

        self.assertEqual(result, ["codice", "regime_fiscale_rf", "soggetto_id"])

    @patch(f"{LOCK_REPO}.list_non_editable")
    def test_compute_returns_sorted(self, mock_list):
        # Ordinamento alfabetico stabile a prescindere dall'ordine input.
        from apps.core.services.non_editable_fields_helper import compute_non_editable_fields

        mock_list.return_value = ("zeta", "alpha")

        result = compute_non_editable_fields("x", "y", gaps=("delta", "beta"))

        self.assertEqual(result, ["alpha", "beta", "delta", "zeta"])

    @patch(f"{LOCK_REPO}.list_non_editable")
    def test_compute_accepts_iterable_gaps(self, mock_list):
        # gaps Iterable[str]: tupla, lista, set, frozenset accettati.
        from apps.core.services.non_editable_fields_helper import compute_non_editable_fields

        mock_list.return_value = ()

        # Set / frozenset / list / tuple devono produrre lo stesso output.
        for gaps in (
            ("a", "b"),
            ["a", "b"],
            {"a", "b"},
            frozenset({"a", "b"}),
        ):
            result = compute_non_editable_fields("x", "y", gaps=gaps)
            self.assertEqual(result, ["a", "b"])


class TestComputeConRecord(TestCase):
    """Con `record_id` il BB legge statici + condizionali sul record."""

    @patch(f"{LOCK_REPO}.list_non_editable")
    @patch(f"{LOCK_REPO}.list_non_editable_for_record")
    def test_compute_con_record_legge_i_condizionali(self, mock_rec, mock_stat):
        from apps.core.services.non_editable_fields_helper import (
            compute_non_editable_fields,
        )

        mock_rec.return_value = ("requires_serial", "codice")
        result = compute_non_editable_fields(
            "catalogo", "articoli", gaps=("uom_id",), record_id="u-1",
        )
        self.assertEqual(result, ["codice", "requires_serial", "uom_id"])
        mock_rec.assert_called_once_with("catalogo", "articoli", "u-1")
        # ⛔ Il ramo per record porta GIA' gli statici: rileggerli e' una
        #    query in piu', non un'informazione in piu'.
        mock_stat.assert_not_called()

class TestLockColumnsCache(TestCase):
    """La cache dei lock statici tiene solo le letture riuscite."""

    def setUp(self):
        from apps.core.db.lock_columns_repository import LockColumnsRepository

        LockColumnsRepository.cache_clear()
        self.addCleanup(LockColumnsRepository.cache_clear)

    # ⛔ Prima del 2026-11-09 l'`lru_cache` avvolgeva il fallback: un guasto
    #    transitorio alla prima lettura lasciava `()` in cache per la vita del
    #    worker, e il form lasciava modificare colonne bloccate dal DB.
    @patch("apps.core.db.lock_columns_repository.connection")
    def test_errore_db_non_resta_in_cache(self, mock_conn):
        from django.db import DatabaseError

        from apps.core.db.lock_columns_repository import LockColumnsRepository

        cursor = mock_conn.cursor.return_value.__enter__.return_value
        cursor.execute.side_effect = [DatabaseError("giu'"), None]
        cursor.fetchall.return_value = [("codice",)]

        with self.assertLogs("apps.core.db.lock_columns_repository", "WARNING"):
            self.assertEqual(LockColumnsRepository.list_non_editable("s", "t"), ())
        self.assertEqual(LockColumnsRepository.list_non_editable("s", "t"), ("codice",))
        # E la lettura riuscita SI' resta in cache: nessuna terza query.
        self.assertEqual(LockColumnsRepository.list_non_editable("s", "t"), ("codice",))
        self.assertEqual(cursor.execute.call_count, 2)
