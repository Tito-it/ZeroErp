# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `DocumentoModelloRepository` sul DATABASE PROVVISTO, con bolla, reso
#        e preventivo costruiti: l'azione che il backend chiede prima della
#        transazione e' quella della riga della matrice
#        (`script.fn_doc_azione_passaggio`, M-3), dallo stato CORRENTE del
#        documento; stato di emissione e d'annullo dai lettori unici
#        (`script.fn_stato_emissione_id`, `script.fn_stato_abortito_id`,
#        `script.fn_doc_stato_codice`). E' la
#        giuntura che i test unitari (repository mockato) non vedono.
# Note: ⚠️ Le azioni e gli stati di emissione attesi sono quelli del seed di
#       oggi (`transizioni_stati_ddt.csv`, `_reso.csv`, `_preventivi.csv`, la
#       colonna `emissione` dei vocabolari): se Tid sposta un'azione su
#       un'altra riga, cambia l'atteso, non il codice. Transazione annullata.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) test_reso_in_bozza — conferma: `conferma_reso`; annullo di una bozza: nessuna (M-4)
2) test_bolla_consegnata — passaggio di processo e passaggio fuori matrice: nessuna
3) test_casi_senza_riga — stato inesistente, documento inesistente: None, nessun errore
4) test_testata_fuori_mappa — errore di cablaggio: E_SCRIPT_CHIAMATA_NON_VALIDA dal DB
5) test_preventivo_in_bozza — emissione: `emetti_preventivo`; annullo di una bozza: nessuna (M-4)
6) test_stato_di_emissione — il vocabolario dice l'emissione; reso e codici ignoti no
7) (ritirato il 2026-10-26 con `DocumentoModelloRepository.stato_id`, §13.8)
8) test_ordine_in_bozza — conferma: `emetti_ordine`; annullo di una bozza: nessuna (M-4)
9) test_stato_di_emissione_composto — id e codice dell'emissione, dal vocabolario; reso: None
10) test_stato_di_annullo — le otto testate: lo stato `is_abortito` del vocabolario, e solo quello
"""
from __future__ import annotations

import unittest

from django.db import DatabaseError, connection

from apps.core.db.documento_modello_repository import DocumentoModelloRepository
from apps.core.services.db_error_fields import structured_db_error_code
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.vendite.db.resi_repository import ResiRepository
from apps.vendite.tests.db._ddt_consegnato import crea_ddt_consegnato


class PermessoPassaggioDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        # La sonda sul lettore del giro 6: un DB indietro fallisce sull'oggetto
        # mancante, non su un'attesa sbagliata.
        richiedi_db_provvisto("script.fn_doc_azione_passaggio(regclass,bigint,text)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        self.repo = DocumentoModelloRepository()
        with connection.cursor() as cur:
            ddt = crea_ddt_consegnato(cur, etichetta="permesso passaggio db")
            # Il caso si e' formato davvero: senza, i passaggi letti sarebbero
            # quelli di un altro stato.
            self.assertEqual(ddt["stato"], "CONSEGNATO")
            self.ddt_id = ddt["id"]
            cur.execute("SELECT id FROM config.sorgenti WHERE codice_interno = 'DDT_VENDITA'")
            sorgente_tipo_id = cur.fetchone()[0]
        self.reso_id = int(ResiRepository().create_reso(
            sorgente_tipo_id=sorgente_tipo_id, sorgente_uid=ddt["uid"], data=None,
            meta={"test_scope": "permesso passaggio db"},
        )["id"])

    def test_reso_in_bozza(self) -> None:
        self.assertEqual(
            self.repo.azione_del_passaggio("vendite.resi", self.reso_id, "CONFERMATO"),
            "conferma_reso",
        )
        self.assertIsNone(
            self.repo.azione_del_passaggio("vendite.resi", self.reso_id, "ANNULLATO"),
        )

    def test_bolla_consegnata(self) -> None:
        # CONSEGNATO -> RESO e' di processo: la riga c'e', senza azione; il
        # rifiuto lo da' il verbo (E_DOC_PASSAGGIO_DI_PROCESSO).
        self.assertIsNone(self.repo.azione_del_passaggio("vendite.ddt", self.ddt_id, "RESO"))
        # CONSEGNATO -> EMESSO non e' nella matrice: lo rifiuta il guard.
        self.assertIsNone(self.repo.azione_del_passaggio("vendite.ddt", self.ddt_id, "EMESSO"))

    def test_casi_senza_riga(self) -> None:
        self.assertIsNone(self.repo.azione_del_passaggio("vendite.ddt", self.ddt_id, "INESISTENTE"))
        self.assertIsNone(self.repo.azione_del_passaggio("vendite.resi", -1, "CONFERMATO"))

    def test_testata_fuori_mappa(self) -> None:
        with self.assertRaises(DatabaseError) as cm:
            self.repo.azione_del_passaggio("vendite.ddt_righe", self.ddt_id, "EMESSO")
        # Il codice dal campo strutturato (BB), non dal testo del messaggio.
        self.assertEqual(structured_db_error_code(cm.exception), "E_SCRIPT_CHIAMATA_NON_VALIDA")

    def test_preventivo_in_bozza(self) -> None:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT preventivo_id FROM dbops.fn_pgtap_crea_preventivo('permesso passaggio db')",
            )
            preventivo_id = cur.fetchone()[0]
        self.assertEqual(
            self.repo.azione_del_passaggio("vendite.preventivi", preventivo_id, "EMESSO"),
            "emetti_preventivo",
        )
        self.assertIsNone(
            self.repo.azione_del_passaggio("vendite.preventivi", preventivo_id, "ANNULLATO"),
        )

    def test_stato_di_emissione(self) -> None:
        for testata, codice in (("vendite.preventivi", "EMESSO"), ("vendite.ddt", "EMESSO"),
                                ("vendite.contratti", "ATTIVO"), ("vendite.ordini", "CONFERMATO"),
                                ("vendite.offerte_commerciali", "EMESSA")):
            with self.subTest(testata=testata):
                self.assertTrue(self.repo.e_stato_di_emissione(testata, codice))
        for testata, codice in (("vendite.preventivi", "ANNULLATO"), ("vendite.ddt", "INESISTENTE"),
                                ("vendite.resi", "CONFERMATO")):
            with self.subTest(testata=testata, codice=codice):
                self.assertFalse(self.repo.e_stato_di_emissione(testata, codice))

    def test_ordine_in_bozza(self) -> None:
        with connection.cursor() as cur:
            cur.execute("SELECT ordine_id FROM dbops.fn_pgtap_crea_ordine('permesso passaggio db')")
            ordine_id = cur.fetchone()[0]
        self.assertEqual(
            self.repo.azione_del_passaggio("vendite.ordini", ordine_id, "CONFERMATO"),
            "emetti_ordine",
        )
        self.assertIsNone(self.repo.azione_del_passaggio("vendite.ordini", ordine_id, "ANNULLATO"))

    # B-1/B-5 (§8.11): lo stato di emissione che «Emetti» scrive e' quello che
    # il vocabolario dichiara (`emissione = true`), letto dalla colonna e non
    # scritto qui; un documento che non si emette (il reso) -> None.
    def test_stato_di_emissione_composto(self) -> None:
        vocabolari = {
            "vendite.ddt": "config.stati_doc_ddt",
            "vendite.preventivi": "config.stati_doc_preventivi",
            "vendite.ordini": "config.stati_doc_ordini",
            "vendite.contratti": "config.stati_doc_contratti",
            "vendite.offerte_commerciali": "config.stati_doc_offerte",
        }
        with connection.cursor() as cur:
            for testata, vocabolario in vocabolari.items():
                with self.subTest(testata=testata):
                    cur.execute(f"SELECT id, codice_interno FROM {vocabolario} WHERE emissione")
                    atteso = cur.fetchall()
                    self.assertEqual(len(atteso), 1)
                    stato = self.repo.stato_di_emissione(testata)
                    assert stato is not None
                    self.assertEqual((stato.id, stato.codice), (int(atteso[0][0]), atteso[0][1]))
        self.assertIsNone(self.repo.stato_di_emissione("vendite.resi"))


    # §9.8: lo stato d'annullo che il backend riconosce e' quello che il
    # vocabolario dichiara (`is_abortito`), letto dalla colonna e non scritto
    # qui; un altro stato attivo non lo e'.
    def test_stato_di_annullo(self) -> None:
        vocabolari = {
            "vendite.ddt": "config.stati_doc_ddt",
            "vendite.preventivi": "config.stati_doc_preventivi",
            "vendite.ordini": "config.stati_doc_ordini",
            "vendite.contratti": "config.stati_doc_contratti",
            "vendite.offerte_commerciali": "config.stati_doc_offerte",
            "vendite.resi": "config.stati_doc_reso",
            "vendite.commesse": "vendite.stati_commessa",
            "vendite.fatture": "config.stati_doc_fiscale",
        }
        with connection.cursor() as cur:
            for testata, vocabolario in vocabolari.items():
                with self.subTest(testata=testata):
                    cur.execute(f"SELECT id, codice_interno FROM {vocabolario} WHERE is_abortito")
                    atteso = cur.fetchall()
                    self.assertEqual(len(atteso), 1)
                    stato = self.repo.stato_di_annullo(testata)
                    assert stato is not None
                    self.assertEqual((stato.id, stato.codice), (int(atteso[0][0]), atteso[0][1]))
                    self.assertTrue(self.repo.e_stato_di_annullo(testata, atteso[0][1]))
                    cur.execute(
                        f"SELECT codice_interno FROM {vocabolario}"
                        " WHERE attivo AND NOT is_abortito ORDER BY id LIMIT 1",
                    )
                    self.assertFalse(self.repo.e_stato_di_annullo(testata, cur.fetchone()[0]))
        self.assertFalse(self.repo.e_stato_di_annullo("vendite.ordini", "INESISTENTE"))
