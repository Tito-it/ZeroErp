# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio della lista configurabile `vendite.lotti` — ordinamento
#        server-side ed export. Test senza DB (unittest.TestCase): leggono il
#        seed CSV e le costanti del codice, quindi girano anche in CI.
# ------------------------------------------------------------
"""Indice test:

1. test_whitelist_ordinamento_copre_il_seed
   Ogni colonna marcata `ordinabile = t` nel seed ha una voce nella whitelist
   del repository: altrimenti l'intestazione mostra una freccia che, al click,
   risponde 400.

2. test_seed_offre_tutto_cio_che_il_backend_sa_ordinare
   Il verso opposto: nessuna colonna resta ordinabile solo sulla carta.

3. test_whitelist_chiavata_sul_campo_sorgente_non_sul_codice
   `<ListaConfigurabile>` monta le Column con `:field="col.campo_sorgente"`,
   quindi `event.sortField` porta il nome FISICO. Chiavare la whitelist sui
   `codice` logici romperebbe proprio le colonne in cui i due divergono.

4. test_colonna_azioni_non_ordinabile
   `tipo_colonna='azione'` non ha campo sorgente: ordinarla non significa nulla.

5. test_export_non_passa_dal_cap_della_lista
   L'export chiede piu' righe del tetto di pagina della lista: se passasse da
   `fn_list_lotti` (page_size <= 200) non potrebbe nemmeno rilevare il
   superamento del limite.
"""

import csv
import unittest
from pathlib import Path

from apps.vendite.db.vendite_repository import VenditeRepository

_LISTA_CODICE = "vendite.lotti"


# Scopo: root del repo cercata risalendo fino a trovare `db/changelog`, invece
#        di contare i livelli a mano (`parents[N]` si rompe in silenzio al primo
#        spostamento del file di test).
def _repo_root() -> Path:
    for cartella in Path(__file__).resolve().parents:
        if (cartella / "db" / "changelog").is_dir():
            return cartella
    raise AssertionError("root del repo non trovata (nessun db/changelog risalendo)")


_SEED_CSV = _repo_root() / "db/changelog/migrations_v2/80_data/sql/ui/lista_colonna.csv"
_SEED_DEFINIZIONE = _SEED_CSV.parent / "lista_definizione.csv"


# Scopo: id della lista `vendite.lotti` nel seed, risolto dal codice invece che
#        cablato: se il seed cambia numerazione il test segue, non si rompe.
def _lista_id() -> str:
    with _SEED_DEFINIZIONE.open(newline="", encoding="utf-8") as fh:
        for riga in csv.DictReader(fh):
            if riga["codice"] == _LISTA_CODICE:
                return riga["id"]
    raise AssertionError(f"lista {_LISTA_CODICE} assente da lista_definizione.csv")


# Scopo: righe di catalogo della lista lotti dal seed CSV.
def _colonne_seed() -> list[dict[str, str]]:
    lista_id = _lista_id()
    with _SEED_CSV.open(newline="", encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if r["lista_id"] == lista_id]


class LottiOrdinamentoSeedTests(unittest.TestCase):
    """L'invariante fra seed e backend, che nessun altro test copre.

    E' il tipo di disallineamento che non produce un errore in fase di build:
    si manifesta come una colonna che a video sembra ordinabile e in risposta
    da' 400, oppure come una capacita' del backend che l'operatore non puo'
    raggiungere. Entrambi si scoprono solo cliccando.
    """

    def setUp(self) -> None:
        self.colonne = _colonne_seed()
        self.assertTrue(self.colonne, "seed della lista vendite.lotti vuoto")
        self.whitelist = set(VenditeRepository.LOTTI_SORT_COLUMNS)
        # Solo le colonne ATTIVE: una colonna disattivata nel catalogo non
        # arriva a video (fn_resolve_lista_config la esclude), quindi i suoi
        # flag non dicono nulla sul contratto lista<->backend.
        self.ordinabili = {
            r["campo_sorgente"]
            for r in self.colonne
            if r["ordinabile"] == "t" and r["attivo"] == "t"
        }

    def test_whitelist_ordinamento_copre_il_seed(self) -> None:
        mancanti = sorted(self.ordinabili - self.whitelist)
        self.assertEqual(
            mancanti,
            [],
            "colonne ordinabili nel seed ma assenti da LOTTI_SORT_COLUMNS: "
            "la freccia a video risponderebbe 400.",
        )

    def test_seed_offre_tutto_cio_che_il_backend_sa_ordinare(self) -> None:
        inutilizzate = sorted(self.whitelist - self.ordinabili)
        self.assertEqual(
            inutilizzate,
            [],
            "colonne ordinabili lato backend ma non offerte dal seed: "
            "capacita' irraggiungibile dall'operatore.",
        )

    def test_whitelist_chiavata_sul_campo_sorgente_non_sul_codice(self) -> None:
        # Almeno una colonna deve avere codice != campo_sorgente, altrimenti il
        # test non distingue le due convenzioni e passerebbe per caso.
        divergenti = [
            r for r in self.colonne
            if r["campo_sorgente"] and r["codice"] != r["campo_sorgente"]
        ]
        self.assertTrue(
            divergenti,
            "nessuna colonna con codice != campo_sorgente: il test non "
            "discrimina piu' le due convenzioni, va rivisto.",
        )
        for riga in divergenti:
            if riga["ordinabile"] != "t":
                continue
            self.assertIn(
                riga["campo_sorgente"],
                self.whitelist,
                f"la whitelist deve usare il campo fisico "
                f"'{riga['campo_sorgente']}', non il codice '{riga['codice']}'.",
            )
            self.assertNotIn(
                riga["codice"],
                self.whitelist,
                f"'{riga['codice']}' e' il codice logico: il FE non lo invia mai "
                "come sortField.",
            )

    def test_colonna_azioni_non_ordinabile(self) -> None:
        for riga in self.colonne:
            if riga["tipo_colonna"] == "azione":
                self.assertEqual(
                    riga["ordinabile"], "f",
                    "la colonna azioni non ha campo sorgente: ordinarla non "
                    "significa nulla.",
                )


class LottiExportCapTests(unittest.TestCase):
    # Scopo: l'export non puo' passare dalla porta della lista.
    def test_export_non_passa_dal_cap_della_lista(self) -> None:
        from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS

        self.assertGreater(
            EXPORT_MAX_ROWS,
            200,
            "se il tetto export scendesse a 200 l'endpoint dedicato non "
            "servirebbe piu': andrebbe rimosso invece di restare a doppione.",
        )
