# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `DocumentoModelloRepository.azione_del_passaggio` sul DATABASE
#        PROVVISTO, con bolla e reso costruiti: l'azione che il backend chiede
#        prima della transazione e' quella della riga della matrice
#        (`script.fn_doc_passaggio`, M-3), dallo stato CORRENTE del documento.
#        E' la giuntura che i test unitari (repository mockato) non vedono:
#        mappa, quote degli identificatori, codice -> id dello stato.
# Note: ⚠️ Le azioni attese sono quelle del seed di oggi
#       (`transizioni_stati_ddt.csv`, `_reso.csv`): se Tid sposta un'azione su
#       un'altra riga, cambia l'atteso, non il codice. Transazione annullata.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) test_reso_in_bozza — conferma: `conferma_reso`; annullo di una bozza: nessuna (M-4)
2) test_bolla_consegnata — passaggio di processo e passaggio fuori matrice: nessuna
3) test_casi_senza_riga — stato inesistente, documento inesistente: None, nessun errore
4) test_testata_fuori_mappa — errore di cablaggio: RuntimeError
"""
from __future__ import annotations

import unittest

from django.db import connection

from apps.core.db.documento_modello_repository import DocumentoModelloRepository
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.vendite.db.resi_repository import ResiRepository
from apps.vendite.tests.db._ddt_consegnato import crea_ddt_consegnato


class PermessoPassaggioDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

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
        with self.assertRaises(RuntimeError):
            self.repo.azione_del_passaggio("vendite.ddt_righe", self.ddt_id, "EMESSO")
