# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: «L'ARTICOLO E' UN ONERE» arriva al frontend, provato contro il
#        database vero (20261103-53, brief-db-addebito-trasporto-ordine §9.9):
#        il picker delle righe di documento e il dettaglio dell'articolo
#        portano `e_onere` e `causale_onere_id` della vista. Dal 2026-11-12
#        (§9.10) anche la decodifica della causale e la sua SCRITTURA: la
#        causale scelta in inserimento, il doppione rifiutato col suo codice,
#        la tendina delle sole causali libere.
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
#      causale decodificata dalla vista; `causale_onere_codice` non esce piu'
#   3) il dettaglio dell'articolo (drawer): `e_onere`, la causale e la sua
#      decodifica; tutto NULL sulla merce
#   Scrittura (mondo costruito, transazione annullata):
#   4) un articolo nato con una causale libera e' un onere, con la decodifica
#   5) la causale di un altro articolo: `E_ARTICOLO_CAUSALE_ONERE_GIA_USATA`
#      sul campo `causale_onere_id`, dal guard e non dall'indice
#   6) la tendina (`rel=catalogo.vw_causali_onere_assegnabili`) da' la libera
#      e non la legata
# ------------------------------------------------------------

from __future__ import annotations

import unittest

from django.db import DatabaseError, connection, transaction

from apps.catalogo.services import catalogo_service
from apps.core.services.db_error_fields import diagnostica_db
from apps.core.services.lookup_service import fn_list_lookup_codici
from apps.core.tests.db_e2e import (
    apri_contesto_operatore,
    apri_transazione_annullata,
    richiedi_db_provvisto,
)

# La tendina delle causali libere (20261112-41, riga 94 della whitelist).
REL_CAUSALI_ASSEGNABILI = "catalogo.vw_causali_onere_assegnabili"


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

    # 2. Il picker degli oneri: la causale e la sua decodifica vengono dalla
    #    vista (20261112-40). ⛔ `causale_onere_codice` era la copia del JOIN
    #    ritirato (C-1): se torna, la decodifica ha di nuovo due sedi.
    def test_il_picker_degli_oneri(self):
        esito = catalogo_service.fn_lookup_articoli(solo_oneri=True, limit=50)
        self.assertTrue(esito["results"], "nessun onere attivo: il seed c'e', il filtro no")
        for r in esito["results"]:
            self.assertIs(r["e_onere"], True, r["codice"])
            self.assertIsNotNone(r["causale_onere_id"], r["codice"])
            self.assertTrue(r["causale_onere_codice_interno"], r["codice"])
            self.assertTrue(r["causale_onere_descrizione"], r["codice"])
            self.assertNotIn("causale_onere_codice", r, r["codice"])

    # 3. Il dettaglio: quello che legge il drawer articolo.
    def test_il_dettaglio_dice_se_e_un_onere(self):
        onere = catalogo_service.fn_get_articolo(self.onere[0])
        self.assertIs(onere["e_onere"], True)
        self.assertEqual(onere["causale_onere_id"], self.onere[2])
        self.assertEqual(onere["causale_onere_codice_interno"], "TRASPORTO")
        self.assertTrue(onere["causale_onere_descrizione"])
        merce = catalogo_service.fn_get_articolo(self.merce[0])
        self.assertIs(merce["e_onere"], False)
        self.assertIsNone(merce["causale_onere_id"])
        self.assertIsNone(merce["causale_onere_codice_interno"])
        self.assertIsNone(merce["causale_onere_descrizione"])


# Scopo: la causale si SCRIVE dal service (§9.10, D-1): il mondo si costruisce
#        (due causali proprie, una natura da servizio), in una transazione
#        annullata. ⭐ Non dal seed: su dbdev le sei causali sono tutte legate
#        (2026-11-12), e un test che cercasse la libera passerebbe a vuoto.
class CausaleOnereScritturaDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            apri_contesto_operatore(cur)
            cur.execute(
                """
                INSERT INTO config.causali_onere (codice_interno, codice, descrizione, attivo)
                VALUES ('BE_COA_1', 'BE-COA-1', 'Test BE: causale assegnabile 1', true),
                       ('BE_COA_2', 'BE-COA-2', 'Test BE: causale assegnabile 2', true)
                RETURNING id, codice_interno
                """
            )
            ids = {codice: pk for pk, codice in cur.fetchall()}
            self.c1, self.c2 = ids["BE_COA_1"], ids["BE_COA_2"]
            # Una natura che non va in ordine: su un onere quella da merce la
            # rifiuta il guard (`E_ARTICOLO_ONERE_NATURA_MERCE`).
            cur.execute(
                "SELECT id FROM config.nature_vendita"
                " WHERE destinazione_tipo = 'COMMESSA' AND attivo ORDER BY id LIMIT 1"
            )
            natura = cur.fetchone()
            cur.execute("SELECT id FROM catalogo.unita_misura WHERE attivo ORDER BY id LIMIT 1")
            uom = cur.fetchone()
        if natura is None or uom is None:
            self.skipTest("servono una natura COMMESSA e un'unita' di misura attive")
        self.natura, self.uom = natura[0], uom[0]

    # Scopo: il payload del drawer per un articolo-onere.
    def _payload(self, codice: str, causale: int) -> dict:
        return {
            "codice": codice,
            "descrizione": f"Onere di prova {codice}",
            "uom_id": self.uom,
            "natura_vendita_id": self.natura,
            "causale_onere_id": causale,
        }

    # 4. La causale scelta in inserimento fa dell'articolo un onere.
    def test_nasce_onere_con_la_causale(self):
        art = catalogo_service.fn_create_articolo(self._payload("BE-COA-A1", self.c1))
        self.assertIs(art["e_onere"], True)
        self.assertEqual(art["causale_onere_id"], self.c1)
        self.assertEqual(art["causale_onere_codice_interno"], "BE_COA_1")
        self.assertEqual(art["causale_onere_descrizione"], "Test BE: causale assegnabile 1")

    # 5. Il doppione: il codice del guard, sul campo, non il 23505 dell'indice.
    def test_la_causale_di_un_altro_e_rifiutata(self):
        catalogo_service.fn_create_articolo(self._payload("BE-COA-A1", self.c1))
        with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
            catalogo_service.fn_create_articolo(self._payload("BE-COA-A2", self.c1))
        diag = diagnostica_db(ctx.exception)
        self.assertEqual(diag.codice, "E_ARTICOLO_CAUSALE_ONERE_GIA_USATA")
        self.assertEqual(diag.campo, "causale_onere_id")

    # 6. La tendina: la libera si', la legata no.
    def test_la_tendina_da_le_sole_libere(self):
        catalogo_service.fn_create_articolo(self._payload("BE-COA-A1", self.c1))
        esito = fn_list_lookup_codici(rel=REL_CAUSALI_ASSEGNABILI, search="BE_COA", limit=50)
        ids = {r["id"] for r in esito["results"]}
        self.assertIn(self.c2, ids)
        self.assertNotIn(self.c1, ids)
