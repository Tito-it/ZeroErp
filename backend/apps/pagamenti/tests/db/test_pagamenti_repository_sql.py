# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidi sull'SQL del repository `pagamenti` — le tre cose che, se si
#        rompono, non danno un errore: danno un dato sbagliato.
# Note: ⚠️ Senza database: si guarda il TESTO dell'SQL e la composizione delle
#       clausole. Non sostituisce una prova sul campo, ma copre esattamente i
#       difetti che una prova sul campo scoprirebbe tardi — un elenco con le
#       righe doppie, un ordinamento invalido, un nome di colonna in chiaro
#       dentro un UPDATE.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) LottiNonDuplicanoTests.test_i_lotti_si_aggregano_non_si_joinano
2) LottiNonDuplicanoTests.test_l_aggregazione_e_una_lateral
3) UpdateWhitelistTests.test_colonna_fuori_whitelist_rifiutata
4) UpdateWhitelistTests.test_colonna_in_whitelist_ammessa
5) UpdateWhitelistTests.test_meta_esce_castata_a_jsonb
6) UpdateWhitelistTests.test_la_riga_non_aggiorna_le_colonne_della_testata
7) CataloghiTests.test_gli_stati_richiedibili_esistono_a_catalogo
8) CataloghiTests.test_gli_stati_iniziali_esistono_a_catalogo
9) CataloghiTests.test_nessuno_stato_richiedibile_e_ritirato
"""

import csv
from pathlib import Path
from unittest import TestCase

from apps.core.services.error_manager import ServiceError
from apps.pagamenti.db import pagamenti_repository as repo_mod
from apps.pagamenti.db.pagamenti_repository import (
    _COLONNE_DISTINTA_AGGIORNABILI,
    _COLONNE_RIGA_AGGIORNABILI,
    PagamentiRepository,
)
from apps.pagamenti.services import pagamenti_service

# I CSV di seed: .../backend/apps/pagamenti/tests/db/<file> -> parents[5] = radice.
_SEED = (
    Path(__file__).resolve().parents[5]
    / "db/changelog/migrations_v2/80_data/sql/pagamenti"
)


# Scopo: Legge un catalogo di stato dal CSV di seed (non dal database: cosi' il
#        presidio vale anche in CI, dove il DB non c'e').
def _catalogo(nome_file: str) -> dict[str, dict[str, str]]:
    with (_SEED / nome_file).open(encoding="utf-8") as f:
        return {r["codice_interno"]: r for r in csv.DictReader(f)}


class LottiNonDuplicanoTests(TestCase):
    """🔴 Il difetto trovato in revisione, e il presidio che lo tiene chiuso."""

    # Scopo: L'unico su `vendite_contabili_lotti` e' `(lotto_id, contabile_id)`
    #        e NON il solo `contabile_id`: una distinta puo' appartenere a piu'
    #        lotti. Un `LEFT JOIN` diretto DUPLICA la riga nell'elenco — e con
    #        essa sbaglia il conteggio totale, che e' il modo silenzioso di
    #        rompersi: la lista sembra piu' lunga e nessuno se ne accorge.
    def test_i_lotti_si_aggregano_non_si_joinano(self):
        self.assertNotIn(
            "LEFT JOIN pagamenti.vendite_contabili_lotti",
            repo_mod._DISTINTA_SELECT,
            "il JOIN diretto sui lotti duplica le distinte: va aggregato",
        )

    # Scopo: E l'aggregazione e' una LATERAL con `array_agg`, cioe' una riga
    #        sola per distinta qualunque sia il numero di lotti.
    def test_l_aggregazione_e_una_lateral(self):
        self.assertIn("array_agg(l.lotto_id", repo_mod._DISTINTA_SELECT)
        self.assertIn("LEFT JOIN LATERAL", repo_mod._DISTINTA_SELECT)


class UpdateWhitelistTests(TestCase):
    """⛔ Nessun nome di colonna entra in SQL senza passare dalla whitelist."""

    # Scopo: E' l'ULTIMO cancello prima che una chiave finisca dentro una
    #        stringa SQL. Il giorno in cui qualcuno chiamasse questi metodi con
    #        chiavi che arrivano da un payload, la differenza fra avere e non
    #        avere questo controllo sarebbe una SQL injection.
    def test_colonna_fuori_whitelist_rifiutata(self):
        with self.assertRaises(ServiceError):
            PagamentiRepository._set_clause(
                {"stato_id = 4, codice": "x"},
                _COLONNE_DISTINTA_AGGIORNABILI,
                "update_distinta",
            )

    def test_colonna_in_whitelist_ammessa(self):
        clause, params = PagamentiRepository._set_clause(
            {"importo_dichiarato": 10}, _COLONNE_DISTINTA_AGGIORNABILI, "x"
        )
        self.assertEqual(clause, "importo_dichiarato = %s")
        self.assertEqual(params, [10])

    # Scopo: `meta` e' jsonb e va castata, o l'UPDATE fallisce sul tipo.
    def test_meta_esce_castata_a_jsonb(self):
        clause, _ = PagamentiRepository._set_clause(
            {"meta": "{}"}, _COLONNE_DISTINTA_AGGIORNABILI, "x"
        )
        self.assertEqual(clause, "meta = %s::jsonb")

    # Scopo: Le due whitelist sono DUE: la testata non ha `importo`, la riga
    #        non ha `importo_dichiarato`. Confonderle scriverebbe su una
    #        colonna che non esiste, ma solo a runtime.
    def test_la_riga_non_aggiorna_le_colonne_della_testata(self):
        self.assertNotIn("importo_dichiarato", _COLONNE_RIGA_AGGIORNABILI)
        self.assertNotIn("importo", _COLONNE_DISTINTA_AGGIORNABILI)


class CataloghiTests(TestCase):
    """⭐ I codici di stato scritti nel service esistono davvero a catalogo."""

    # Scopo: `STATI_DISTINTA_RICHIEDIBILI` e i suoi gemelli sono stringhe
    #        scritte a mano nel backend: dicono che cosa una PERSONA puo'
    #        chiedere, ed e' una policy legittima. ⚠️ Ma se un `codice_interno`
    #        cambiasse a catalogo, quelle stringhe smetterebbero di risolvere e
    #        il gesto fallirebbe a runtime. Questo presidio le lega al CSV.
    def test_gli_stati_richiedibili_esistono_a_catalogo(self):
        distinta = _catalogo("vendite_contabili_stati.csv")
        riga = _catalogo("vendite_contabili_righe_stati.csv")
        for codice in pagamenti_service.STATI_DISTINTA_RICHIEDIBILI:
            self.assertIn(codice, distinta, f"stato distinta {codice} non a catalogo")
        for codice in pagamenti_service.STATI_RIGA_RICHIEDIBILI:
            self.assertIn(codice, riga, f"stato riga {codice} non a catalogo")

    # Scopo: Idem per i due stati in cui gli oggetti NASCONO.
    def test_gli_stati_iniziali_esistono_a_catalogo(self):
        self.assertIn(
            pagamenti_service.STATO_DISTINTA_INIZIALE,
            _catalogo("vendite_contabili_stati.csv"),
        )
        self.assertIn(
            pagamenti_service.STATO_RIGA_INIZIALE,
            _catalogo("vendite_contabili_righe_stati.csv"),
        )

    # Scopo: 🔴 Uno stato RITIRATO non si propone piu' a nessuno. `STORNATA` e'
    #        stata ritirata il 2026-08-21, e rimetterla in un menu riaprirebbe
    #        una porta che il lotto 2 ha chiuso.
    def test_nessuno_stato_richiedibile_e_ritirato(self):
        distinta = _catalogo("vendite_contabili_stati.csv")
        riga = _catalogo("vendite_contabili_righe_stati.csv")
        ritirati = [
            codice
            for catalogo, codici in (
                (distinta, pagamenti_service.STATI_DISTINTA_RICHIEDIBILI),
                (riga, pagamenti_service.STATI_RIGA_RICHIEDIBILI),
            )
            for codice in codici
            if (catalogo[codice].get("obsoleto_dal") or "").strip()
        ]
        self.assertEqual(ritirati, [], "stati ritirati proposti a chi lavora")
