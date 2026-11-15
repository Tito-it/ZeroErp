# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il BB `seed_csv` (helper `_seed_csv`): ogni cella arriva come la
#        scrive il caricatore Liquibase — `null` in ogni grafia e' NULL, la
#        cella vuota e' `''` sulla colonna STRING, il default dove c'e', NULL
#        altrove — e dove i caricatori non danno una risposta sola il BB
#        rifiuta invece di indovinare (brief-db-token-null-dei-seed §1, §6).
# Note: ⚠️ Senza DB. I casi della regola si COSTRUISCONO (un CSV e la sua mappa
#        di celle vuote, o le dichiarazioni dei caricatori date a mano): un
#        test che li cercasse nei seed di oggi diventerebbe verde il giorno in
#        cui il seed smette di averli.
# ------------------------------------------------------------
"""Indice test:

1. test_null_in_ogni_grafia_e_none
   `null`, `NULL`, `Null` e la cella fra virgolette: NULL su ogni colonna,
   anche sulla STRING.
2. test_la_cella_vuota_segue_la_dichiarazione
   Vuota su STRING = `''`; su STRING con default = il default; su NUMERIC e
   su una colonna non dichiarata = `None`.
3. test_le_dichiarazioni_vengono_dal_caricatore
   Un file vero: le colonne STRING del suo caricatore danno `''`, le altre
   `None`. Con `header` la chiave e' l'intestazione del CSV.
4. test_un_file_senza_caricatore_e_rifiutato
5. test_caricatori_in_disaccordo_sono_rifiutati
   Uno dichiara la colonna STRING e l'altro no: la vuota sarebbe `''` o NULL
   secondo chi passa per ultimo.
6. test_caricatori_concordi_sono_accettati
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from apps.core.tests import _seed_csv
from apps.core.tests._seed_csv import SEED_DIR, SEED_UI_DIR, celle_vuote, seed_csv


class SeedCsvTests(TestCase):
    # Scopo: legge un CSV costruito con la mappa di celle vuote data.
    def _leggi(self, testo: str, vuote: dict[str, str | None]) -> list[dict[str, str | None]]:
        with tempfile.TemporaryDirectory() as cartella:
            copia = Path(cartella) / "costruito.csv"
            copia.write_text(testo, encoding="utf-8")
            with patch.object(_seed_csv, "celle_vuote", return_value=vuote):
                return seed_csv(copia)

    def test_null_in_ogni_grafia_e_none(self) -> None:
        righe = self._leggi(
            'testo,numero\nnull,NULL\nNull,"NULL"\n',
            {"testo": "", "numero": None},
        )
        for riga in righe:
            with self.subTest(riga=riga):
                self.assertIsNone(riga["testo"])
                self.assertIsNone(riga["numero"])

    def test_la_cella_vuota_segue_la_dichiarazione(self) -> None:
        (riga,) = self._leggi(
            "testo,con_default,numero,non_dichiarata\n,,,\n",
            {"testo": "", "con_default": "{}", "numero": None},
        )
        self.assertEqual(riga["testo"], "")
        self.assertEqual(riga["con_default"], "{}")
        self.assertIsNone(riga["numero"])
        self.assertIsNone(riga["non_dichiarata"])

    def test_le_dichiarazioni_vengono_dal_caricatore(self) -> None:
        # `lista_preset.csv`: un caricatore solo, colonne dichiarate a mano.
        vuote = celle_vuote(SEED_UI_DIR / "lista_preset.csv")
        self.assertEqual(vuote["descrizione"], "")
        self.assertIsNone(vuote["profilo_accesso_id"])
        self.assertIsNone(vuote["is_default"])
        dichiarazioni = (
            (("geoloc", None), ("nome_strada", "")),
        )
        with patch.object(_seed_csv.caricatori_seed(), "caricatori", return_value=dichiarazioni):
            vuote = celle_vuote(SEED_DIR / "qualunque.csv")
        self.assertEqual(vuote, {"geoloc": None, "nome_strada": ""})
        self.assertEqual(
            _seed_csv.caricatori_seed().vuota_della_colonna({"name": "geo", "header": "geoloc", "type": "STRING"}),
            ("geoloc", ""),
        )
        self.assertEqual(
            _seed_csv.caricatori_seed().vuota_della_colonna({"name": "meta", "type": "JSON", "defaultValue": "{}"}),
            ("meta", "{}"),
        )

    def test_un_file_senza_caricatore_e_rifiutato(self) -> None:
        with self.assertRaisesRegex(AssertionError, "nessun caricatore"):
            celle_vuote(SEED_UI_DIR / "nessun_caricatore_lo_legge.csv")

    def test_caricatori_in_disaccordo_sono_rifiutati(self) -> None:
        dichiarazioni = (
            (("descrizione", ""), ("id", None)),
            (("id", None),),
        )
        with patch.object(_seed_csv.caricatori_seed(), "caricatori", return_value=dichiarazioni):
            with self.assertRaisesRegex(AssertionError, r"non dicono la stessa cosa.*descrizione"):
                celle_vuote(SEED_DIR / "qualunque.csv")

    def test_caricatori_concordi_sono_accettati(self) -> None:
        dichiarazioni = (
            (("descrizione", ""), ("id", None)),
            (("descrizione", ""),),
        )
        with patch.object(_seed_csv.caricatori_seed(), "caricatori", return_value=dichiarazioni):
            self.assertEqual(
                celle_vuote(SEED_DIR / "qualunque.csv"),
                {"descrizione": "", "id": None},
            )
