# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: «L'ARTICOLO E' UN ONERE» arriva al frontend, provato contro il
#        database vero (20261103-53, brief-db-addebito-trasporto-ordine §9.9):
#        il picker delle righe di documento e il dettaglio dell'articolo
#        portano `e_onere` e `causale_onere_id` della vista.
#
# 🔴 PERCHE' SUL DB VERO. Il repository proietta la vista PER NOME: una colonna
#    che la vista espone e il repository non nomina non arriva, senza errore —
#    il form della riga mostrerebbe le date su un onere e il drawer lascerebbe
#    accendere il magazzino, e ci penserebbe il guard a rifiutare. Un mock del
#    repository non vede la proiezione.
#
# ⭐ IL CASO SI COSTRUISCE dal seed (`ONERE_TRASPORTO`, causale TRASPORTO) e da
#    una merce qualunque; senza, il test si dichiara saltato col motivo.
#
# Indice test:
#   1) il picker delle righe d'ordine: l'onere porta `e_onere` e la causale,
#      la merce `e_onere` falso e nessuna causale
#   2) il picker degli oneri (`solo_oneri`): solo oneri, con `e_onere` e la
#      causale decodificata, nessuna colonna doppia
#   3) il dettaglio dell'articolo (drawer): `e_onere` e la causale
# ------------------------------------------------------------

from __future__ import annotations

import unittest

from django.db import connection

from apps.catalogo.services import catalogo_service
from apps.core.tests.db_e2e import richiedi_db_provvisto


class ArticoloEOnereDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id::text, codice, causale_onere_id FROM catalogo.vw_articoli_dettaglio"
                " WHERE codice = 'ONERE_TRASPORTO' AND attivo"
            )
            cls.onere = cursor.fetchone()
            cursor.execute(
                "SELECT id::text, codice FROM catalogo.vw_articoli_dettaglio"
                " WHERE attivo AND NOT e_onere ORDER BY codice LIMIT 1"
            )
            cls.merce = cursor.fetchone()

    def setUp(self) -> None:
        if not self.onere or not self.merce:
            self.skipTest("servono il seed ONERE_TRASPORTO e una merce attiva: caso non costruibile")

    # 1. Il picker delle righe d'ordine: quello che legge il form di riga.
    def test_il_picker_di_riga_dice_se_e_un_onere(self):
        for codice, atteso_onere, attesa_causale in (
            (self.onere[1], True, self.onere[2]),
            (self.merce[1], False, None),
        ):
            # ⚠️ Un ordine che non esiste (-1): la funzione lo giudica senza
            #    testata, e qui conta la PROIEZIONE, non il giudizio.
            esito = catalogo_service.fn_lookup_articoli_ammessi(
                documento="ORDINE_VENDITA", documento_id=-1, search=codice, limit=50,
            )
            riga = next((r for r in esito["results"] if r["codice"] == codice), None)
            self.assertIsNotNone(riga, f"{codice} non trovato dal picker")
            self.assertIs(riga["e_onere"], atteso_onere, codice)
            self.assertEqual(riga["causale_onere_id"], attesa_causale, codice)

    # 2. Il picker degli oneri: la causale viene dalla vista, il vocabolario
    #    aggiunge solo la decodifica.
    def test_il_picker_degli_oneri(self):
        esito = catalogo_service.fn_lookup_articoli(solo_oneri=True, limit=50)
        self.assertTrue(esito["results"], "nessun onere attivo: il seed c'e', il filtro no")
        for r in esito["results"]:
            self.assertIs(r["e_onere"], True, r["codice"])
            self.assertIsNotNone(r["causale_onere_id"], r["codice"])
            self.assertTrue(r["causale_onere_codice"], r["codice"])

    # 3. Il dettaglio: quello che legge il drawer articolo.
    def test_il_dettaglio_dice_se_e_un_onere(self):
        onere = catalogo_service.fn_get_articolo(self.onere[0])
        self.assertIs(onere["e_onere"], True)
        self.assertEqual(onere["causale_onere_id"], self.onere[2])
        merce = catalogo_service.fn_get_articolo(self.merce[0])
        self.assertIs(merce["e_onere"], False)
        self.assertIsNone(merce["causale_onere_id"])
