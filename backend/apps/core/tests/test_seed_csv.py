# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il BB `seed_csv` (helper `_seed_csv`): il token NULL di un CSV di seed
#        si legge dal suo caricatore, e dove non c'e' una risposta sola il BB
#        rifiuta invece di indovinare.
# Note: ⚠️ Senza DB: legge gli YAML di `db/changelog` e i CSV di `80_data`.
# ------------------------------------------------------------
"""Indice test:

1. test_il_token_e_quello_del_caricatore
   I file noti danno il token dichiarato dal loro caricatore, compreso
   `lista_colonna.csv`, che ne ha due ed e' deciso da `CSV_SEED`.
2. test_il_token_diventa_none_la_cella_vuota_no
   Con `nullValue: "NULL"` il token diventa `None`, la cella vuota resta `''`:
   e' come la scrive il loader.
3. test_un_file_senza_caricatore_e_rifiutato
4. test_un_descrittore_in_disaccordo_coi_caricatori_e_rifiutato
5. test_un_nullvalue_non_stringa_e_rifiutato
   `nullValue:` senza valore e' `None` per YAML: non e' un token da confrontare.
"""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from apps.core.tests import _seed_csv
from apps.core.tests._seed_csv import SEED_DIR, SEED_UI_DIR, seed_csv, token_nullo


class SeedCsvTests(TestCase):
    def test_il_token_e_quello_del_caricatore(self) -> None:
        attesi = {
            "ui/lista_colonna.csv": "NULL",
            "ui/lista_definizione.csv": "NULL",
            "ui/lista_preset.csv": "",
            "ui/lista_preset_colonna.csv": "",
            "dbops/processi.csv": "NULL",
            "config/tipi_entita.csv": "NULL",
        }
        for nome, token in attesi.items():
            with self.subTest(file=nome):
                self.assertEqual(token_nullo(SEED_DIR / nome), token)

    def test_il_token_diventa_none_la_cella_vuota_no(self) -> None:
        sorgente = SEED_DIR / "dbops/processi.csv"
        with sorgente.open(newline="", encoding="utf-8") as fh:
            lettore = csv.DictReader(fh)
            campi = list(lettore.fieldnames or ())
            prima = next(lettore)
        with tempfile.TemporaryDirectory() as cartella:
            copia = Path(cartella) / "processi.csv"
            with copia.open("w", newline="", encoding="utf-8") as fh:
                scrittore = csv.DictWriter(fh, fieldnames=campi)
                scrittore.writeheader()
                scrittore.writerow({**prima, "tolleranza_minuti": "NULL", "segno_di_vita": ""})
            # La copia non ha un caricatore suo: le si presta quello del seed.
            with patch.object(_seed_csv, "token_nullo", return_value="NULL"):
                (riga,) = seed_csv(copia)
        self.assertIsNone(riga["tolleranza_minuti"])
        self.assertEqual(riga["segno_di_vita"], "")

    def test_un_file_senza_caricatore_e_rifiutato(self) -> None:
        with self.assertRaisesRegex(AssertionError, "nessun caricatore"):
            token_nullo(SEED_UI_DIR / "nessun_caricatore_lo_legge.csv")

    def test_un_descrittore_in_disaccordo_coi_caricatori_e_rifiutato(self) -> None:
        generatore = _seed_csv.generatore_seed_lista()
        falso = {**generatore.CSV_SEED, "lista_preset.csv": {"nullo": "NULL"}}
        with patch.object(generatore, "CSV_SEED", falso):
            with self.assertRaisesRegex(AssertionError, "nessun caricatore usa"):
                token_nullo(SEED_UI_DIR / "lista_preset.csv")

    def test_un_nullvalue_non_stringa_e_rifiutato(self) -> None:
        with patch.object(_seed_csv, "_token_dei_caricatori", return_value=frozenset({None})):
            with self.assertRaisesRegex(AssertionError, "non e' una stringa"):
                token_nullo(SEED_DIR / "dbops/processi.csv")
