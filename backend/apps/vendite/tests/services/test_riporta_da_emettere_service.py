# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: il verbo «Riporta da emettere» e l'elenco dei residui su cui agisce.
# Note: mock sul repository — nessun DB (regola CI di AGENTS.md).
# ------------------------------------------------------------
"""Indice test:

 1) test_elenco_vuoto_rifiutato               — [] non passa: darebbe «zero riportate»
 2) test_elenco_assente_rifiutato             — None idem
 3) test_id_non_interi_rifiutati              — stringhe e bool fuori
 4) test_id_non_positivi_rifiutati            — 0 e negativi fuori
 5) test_oltre_il_tetto_rifiutato             — > MAX_ATTIVITA_RIPORTO
 6) test_duplicati_rimossi_ordine_preservato  — la madre li tratterebbe una volta
 7) test_delega_alla_madre_una_sola_chiamata  — atomicita' del DB, non ricomposta
 8) test_check_non_muta                       — la lettura dei motivi non scrive
 9) test_motivi_passano_intatti               — reason_key/bersaglio non riscritti
10) test_lista_residui_filtra_e_pagina        — il perimetro non si allarga
11) test_lista_residui_order_by_fuori_whitelist — colonna non ammessa -> errore
12) test_lista_residui_order_dir_invalida     — direzione non ammessa -> errore
13) test_proiezione_copre_ogni_colonna_del_catalogo — colonna dichiarata e non
    proiettata: uscirebbe VUOTA nella lista e nel file di export
14) test_whitelist_chiavata_sui_campi_fisici  — chiavi = campo_sorgente, non codice
"""

import unittest
from datetime import date
from unittest.mock import patch

from apps.core.services.service_errors import ServiceError
from apps.vendite.services import vendite_service as vs


class ValidazioneIdsRiportoTests(unittest.TestCase):
    """⛔ Il guard sull'elenco non e' pedanteria: un elenco vuoto che passasse
    produrrebbe «zero attivita' riportate», cioe' un messaggio identico a quello
    di un'operazione riuscita che non aveva niente da fare."""

    # Scopo: Verifica che l'elenco vuoto sia rifiutato prima di toccare il DB.
    def test_elenco_vuoto_rifiutato(self):
        with self.assertRaises(ServiceError) as exc:
            vs.fn_riporta_attivita_da_emettere(attivita_fatturabili_ids=[])
        self.assertEqual(exc.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: Verifica che l'elenco assente sia rifiutato.
    def test_elenco_assente_rifiutato(self):
        with self.assertRaises(ServiceError):
            vs.fn_riporta_attivita_da_emettere(attivita_fatturabili_ids=None)

    # Scopo: Verifica che gli id non interi siano rifiutati.
    # ⚠️ `True` e' un int in Python: se passasse, diventerebbe l'id 1.
    def test_id_non_interi_rifiutati(self):
        for cattivo in (["7"], [1, "2"], [True], [1.5]):
            with self.subTest(cattivo=cattivo), self.assertRaises(ServiceError):
                vs.fn_riporta_attivita_da_emettere(attivita_fatturabili_ids=cattivo)

    # Scopo: Verifica che zero e negativi siano rifiutati.
    def test_id_non_positivi_rifiutati(self):
        for cattivo in ([0], [-1], [5, 0]):
            with self.subTest(cattivo=cattivo), self.assertRaises(ServiceError):
                vs.fn_riporta_attivita_da_emettere(attivita_fatturabili_ids=cattivo)

    # Scopo: Verifica il tetto sul numero di attivita' per chiamata.
    def test_oltre_il_tetto_rifiutato(self):
        troppi = list(range(1, vs.MAX_ATTIVITA_RIPORTO + 2))
        with self.assertRaises(ServiceError) as exc:
            vs.fn_riporta_attivita_da_emettere(attivita_fatturabili_ids=troppi)
        self.assertEqual(exc.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: Verifica che i duplicati siano rimossi preservando l'ordine.
    # ⚠️ Due volte lo stesso id e' la stessa riga e la madre la tratterebbe una
    #    volta sola: senza dedup il conteggio a video direbbe un numero diverso
    #    da quello che si e' spuntato.
    @patch.object(vs.VenditeRepository, "riporta_attivita_da_emettere")
    def test_duplicati_rimossi_ordine_preservato(self, mock_riporta):
        mock_riporta.return_value = {"riportate": 3, "riemesse_attivita": 3}
        vs.fn_riporta_attivita_da_emettere(attivita_fatturabili_ids=[9, 4, 9, 7, 4])
        mock_riporta.assert_called_once_with([9, 4, 7])


class VerboRiportaTests(unittest.TestCase):

    # Scopo: Verifica che il verbo deleghi alla madre DB in UNA sola chiamata.
    # ⛔ L'atomicita' e' del database (due scritture + evento di registro in una
    #    transazione): ricomporla qui sarebbe una seconda implementazione.
    @patch.object(vs.VenditeRepository, "riporta_attivita_da_emettere")
    def test_delega_alla_madre_una_sola_chiamata(self, mock_riporta):
        mock_riporta.return_value = {"riportate": 5, "riemesse_attivita": 5}
        esito = vs.fn_riporta_attivita_da_emettere(attivita_fatturabili_ids=[1, 2, 3, 4, 5])
        self.assertEqual(esito, {"riportate": 5, "riemesse_attivita": 5})
        self.assertEqual(mock_riporta.call_count, 1)

    # Scopo: Verifica che la lettura dei motivi non chiami la mutazione.
    @patch.object(vs.VenditeRepository, "riporta_attivita_da_emettere")
    @patch.object(vs.VenditeRepository, "check_attivita_riportabili_da_emettere")
    def test_check_non_muta(self, mock_check, mock_riporta):
        mock_check.return_value = []
        vs.fn_check_attivita_riportabili(attivita_fatturabili_ids=[1])
        mock_riporta.assert_not_called()

    # Scopo: Verifica che i motivi arrivino INTATTI a chi chiama.
    # ⛔ `reason_key` e gli id del bersaglio non si riscrivono nel backend: il
    #    frontend risolve l'indirizzo i18n che il DATABASE dichiara, e riscriverlo
    #    qui sarebbe una seconda copia del vocabolario.
    @patch.object(vs.VenditeRepository, "check_attivita_riportabili_da_emettere")
    def test_motivi_passano_intatti(self, mock_check):
        motivo = {
            "codice": "E_ATTIVITA_ANCORA_IN_FATTURA",
            "reason": "ATTIVITA_IN_FATTURA",
            "reason_key": "vendite.attivita.azione_reason.ancora_in_fattura",
            "dettaglio": "commessa CMM-1, competenza 07/2026",
            "attivita_fatturabile_id": 11,
            "commessa_id": 22,
            "fattura_id": 33,
        }
        mock_check.return_value = [motivo]
        self.assertEqual(
            vs.fn_check_attivita_riportabili(attivita_fatturabili_ids=[11]),
            {"motivi": [motivo]},
        )


class ListaResiduiTests(unittest.TestCase):

    # Scopo: Verifica che la lista deleghi al repository col mese normalizzato al
    #        primo giorno, e che la paginazione arrivi come limit/offset.
    @patch.object(vs.VenditeRepository, "list_dash_competenza_residui")
    def test_lista_residui_filtra_e_pagina(self, mock_list):
        mock_list.return_value = ([], 0)
        vs.fn_dash_competenza_residui(competenza_mese=date(2026, 7, 18), limit=25, offset=25)
        kwargs = mock_list.call_args.kwargs
        self.assertEqual(kwargs["competenza_mese"], date(2026, 7, 1))
        self.assertEqual(kwargs["limit"], 25)
        self.assertEqual(kwargs["offset"], 25)

    # Scopo: Verifica che una colonna fuori whitelist sia rifiutata.
    # ⚠️ La colonna finisce in una clausola SQL: un valore non ammesso che
    #    passasse sarebbe un 500, non un rifiuto educato.
    def test_lista_residui_order_by_fuori_whitelist(self):
        with self.assertRaises(ServiceError) as exc:
            vs.fn_dash_competenza_residui(
                competenza_mese=date(2026, 7, 1), order_by="drop_table",
            )
        self.assertEqual(exc.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: Verifica che una direzione non ammessa sia rifiutata.
    def test_lista_residui_order_dir_invalida(self):
        with self.assertRaises(ServiceError):
            vs.fn_dash_competenza_residui(
                competenza_mese=date(2026, 7, 1), order_dir="sideways",
            )

    # Scopo: ⭐ Ogni colonna che il CATALOGO dichiara ordinabile deve stare nella
    #        whitelist, e viceversa. Qui si prova il verso che il presidio
    #        generale non copre finche' la lista non e' montata dal frontend:
    #        che le chiavi siano i CAMPI FISICI, non i codici delle colonne.
    def test_proiezione_copre_ogni_colonna_del_catalogo(self):
        """⛔ Ogni `campo_sorgente` a catalogo deve esistere nella riga che il
        repository proietta: una colonna dichiarata e non proiettata non fa
        nessun errore — esce **vuota** nel file di export e nella lista, e chi
        apre il foglio non ha modo di accorgersene.
        ⚠️ Il legame e' verificato sui NOMI, senza DB: il catalogo vive nel CSV
        di `80_data`, che e' la sorgente anche del seed."""
        import csv
        from pathlib import Path

        radice = Path(__file__).resolve().parents[4].parent
        csv_path = (radice / "db/changelog/migrations_v2/80_data/sql/ui/lista_colonna.csv")
        if not csv_path.exists():          # albero senza la parte DB: si dichiara
            self.skipTest(f"catalogo non presente in questo albero: {csv_path}")
        campi = {
            r["campo_sorgente"]
            for r in csv.DictReader(csv_path.open(encoding="utf-8"))
            if r.get("lista_id") == "49"
            and r.get("tipo_colonna") != "azione"
            and r.get("campo_sorgente")
        }
        self.assertTrue(campi, "nessuna colonna trovata per la lista 49")
        # I nomi che il repository scrive nel dict di riga.
        from apps.vendite.types import DashCompetenzaResiduoRow

        proiettati = set(DashCompetenzaResiduoRow.__annotations__)
        self.assertEqual(
            sorted(campi - proiettati), [],
            "colonne dichiarate a catalogo e non proiettate: uscirebbero VUOTE",
        )

    def test_whitelist_chiavata_sui_campi_fisici(self):
        w = vs.VenditeRepository.DASH_COMPETENZA_RESIDUI_SORT_COLUMNS
        # I due casi in cui `codice` e `campo_sorgente` divergono a catalogo.
        self.assertIn("articolo_codice", w)
        self.assertIn("lotto_provenienza_codice", w)
        self.assertNotIn("articolo", w)
        self.assertNotIn("lotto_provenienza", w)
