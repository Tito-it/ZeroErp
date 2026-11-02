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
