# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le tre istruzioni con cui il BE SCRIVE e rilegge `vendite.fatture_righe`
#        nella fatturazione (`VenditePipelineRepository.batch_insert_righe_and_mark`,
#        `list_righe_per_plafond`, `insert_parte_plafond`), eseguite sul
#        DATABASE PROVVISTO. Provano la giuntura che i test del service (mock)
#        non vedono: che ogni colonna nominata esista nella tabella di oggi.
# Note: ⭐ PERCHE' SUL DB. Il 2026-11-08 il giro finale bis di
#       brief-db-sorgente-documento-e-riga (G-4) ha ritirato le quattro
#       colonne `sorgente_*` della riga di fattura: le tre istruzioni le
#       nominavano ancora, e la creazione delle fatture si e' rotta senza
#       che un solo test lo vedesse (BE-G4-a). Questo e' il presidio.
#       ⚠️ Prova la SCRITTURA, non la marcatura: l'attivita' da marcare e'
#       un id che non c'e', quindi l'`UPDATE` finale non tocca niente e il
#       metodo torna 0. Il collegamento riga ↔ attivita' lo prova lo smoke
#       `scripts/tests/smoke-fatturazione-aggregazione-righe` (check 3).
#       Il mondo lo costruiscono le fixture `dbops.fn_pgtap_*`; transazione
#       SEMPRE annullata. Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) FattureRigheScritturaDbTests.test_batch_insert_scrive_la_riga
2) FattureRigheScritturaDbTests.test_plafond_rilegge_e_spezza_la_riga
"""
from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal

from django.db import connection

from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.vendite.db.pipeline_repository import VenditePipelineRepository

# Un id che nessuna sequenza raggiunge: l'attivita' che non c'e'.
_ID_INESISTENTE = 9_000_000_000_000


class FattureRigheScritturaDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto("dbops.fn_pgtap_crea_fattura(text, character varying, bigint,"
                              " boolean, boolean, boolean, numeric, bigint, boolean)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        self.repo = VenditePipelineRepository()
        with connection.cursor() as cur:
            cur.execute(
                "SELECT fattura_id, billing_account_id"
                "  FROM dbops.fn_pgtap_crea_fattura('BE-G4 righe')"
            )
            self.fattura_id, self.ba_id = cur.fetchone()
            cur.execute("SELECT dbops.fn_pgtap_crea_articolo('BE-G4-RIGHE')")
            self.articolo_id = str(cur.fetchone()[0])
            cur.execute("SELECT uom_id FROM catalogo.articoli WHERE id = %s",
                        [self.articolo_id])
            self.uom_id = cur.fetchone()[0]
            # Un'aliquota qualunque del seed: la riga ne vuole una, il test
            # non dipende da quale.
            cur.execute("SELECT id FROM config.iva WHERE attivo ORDER BY id LIMIT 1")
            self.iva_id = cur.fetchone()[0]

    # Scopo: la riga come la scrive `batch_insert_righe_and_mark`, cioe' come
    #        la scrive la fatturazione.
    def _scrivi_riga(self, riga_nr: int = 1) -> int:
        self.repo.batch_insert_righe_and_mark(
            righe_fattura_ids=[self.fattura_id],
            righe_nrs=[riga_nr],
            righe_articolo_ids=[self.articolo_id],
            righe_descrizioni=["BE-G4"],
            righe_uom_ids=[self.uom_id],
            righe_qtas=[Decimal("10")],
            righe_prezzi_unitari=[Decimal("10.00")],
            righe_iva_ids=[self.iva_id],
            righe_dest_billing_account_ids=[self.ba_id],
            righe_kit_keys=[None],
            righe_kit_esposizioni=[None],
            righe_kit_articolo_padre_ids=[None],
            righe_kit_qtas=[None],
            righe_kit_uom_ids=[None],
            righe_competenze_dal=[date(2026, 11, 1)],
            righe_competenze_al=[date(2026, 11, 30)],
            righe_sconti=[None],
            righe_rettificate=[None],
            righe_metas=["{}"],
            att_ids=[_ID_INESISTENTE],
            att_fattura_ids=[self.fattura_id],
            att_riga_nrs=[riga_nr],
        )
        with connection.cursor() as cur:
            cur.execute(
                "SELECT id FROM vendite.fatture_righe WHERE fattura_id = %s AND riga_nr = %s",
                [self.fattura_id, riga_nr],
            )
            row = cur.fetchone()
        self.assertIsNotNone(row, "la riga non e' stata scritta")
        return int(row[0])

    # 1. La INSERT della fatturazione scrive la riga; nessuna attivita' da
    #    marcare (l'id non c'e'), quindi il metodo torna 0.
    def test_batch_insert_scrive_la_riga(self):
        riga_id = self._scrivi_riga()
        with connection.cursor() as cur:
            cur.execute(
                "SELECT qta, prezzo_unitario, imponibile_riga FROM vendite.fatture_righe"
                " WHERE id = %s",
                [riga_id],
            )
            qta, prezzo, imponibile = cur.fetchone()
        self.assertEqual((qta, prezzo), (Decimal("10"), Decimal("10.00")))
        # L'importo lo calcola il trigger della riga, non il BE.
        self.assertEqual(imponibile, Decimal("100.00"))

    # 2. Il plafond rilegge la riga e ne scrive la parte, legata alla capofila
    #    e sulla stessa fattura.
    def test_plafond_rilegge_e_spezza_la_riga(self):
        capofila_id = self._scrivi_riga()
        righe = self.repo.list_righe_per_plafond(self.fattura_id)
        self.assertEqual([r["id"] for r in righe], [capofila_id])

        parte_id = self.repo.insert_parte_plafond(
            riga_capofila_id=capofila_id,
            riga_nr=2,
            qta=Decimal("4"),
            iva_id=self.iva_id,
            kit_qta=None,
            meta={},
        )
        with connection.cursor() as cur:
            cur.execute(
                "SELECT fattura_id, riga_capofila_id, qta FROM vendite.fatture_righe"
                " WHERE id = %s",
                [parte_id],
            )
            self.assertEqual(cur.fetchone(), (self.fattura_id, capofila_id, Decimal("4")))
