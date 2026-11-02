# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: LA SONDA `+1` DEL LOOKUP ARTICOLI, provata contro il database vero —
#        cioe' nel solo posto in cui si puo' provare.
#
# 🔴 PERCHE' NON BASTA UN TEST UNITARIO (2026-09-10). Il troncamento nasce sotto
#    il service: e' il repository a clampare (`safe_limit = max(1, min(limit, 50))`)
#    e il BB `fetch_con_sonda` a chiedere una riga in piu', tagliarla e dedurre il
#    flag. I test di `tests/services/` mockano il repository, quindi verificano
#    che il service **trasporti** il flag — non che il flag sia **vero**. Con la
#    mutazione «torna sempre False» quei test restano verdi: e' corretto che sia
#    cosi', ed e' la ragione per cui questo file esiste.
#
# ⭐ E NON PUO' ESSERE VERDE PER SOTTRAZIONE. Le attese non sono numeri scritti
#    qui: si derivano dal contenuto del database in quel momento (`count(*)`).
#    Su un'installazione con pochi articoli il test si DICHIARA saltato con il
#    motivo, invece di passare senza aver guardato niente.
#
# ⚠️ SI PROVA IL LOOKUP CHE L'APPLICAZIONE CHIAMA. Il gemello sulle unita' di
#    misura, che questo file presidiava fino al 2026-09-10, e' stato tolto
#    insieme alla funzione: non lo esponeva nessun endpoint (il lookup UoM passa
#    da `/core/lookup/codici/`), quindi quei quattro test presidiavano un ramo
#    che nessuno percorreva mentre quello vivo restava senza rete.
#
# Indice test — `fn_lookup_articoli`:
#   1) chiesto meno del disponibile -> `troncato` VERO
#   2) un insieme sotto il tetto -> `troncato` FALSO (il flag non e' incollato:
#      uno sempre vero e' inutile quanto uno sempre falso)
#   3) ⭐ il ramo con i JOIN non moltiplica le righe (senza questo, la sonda su
#      QUESTA query non significa niente: conterebbe doppioni)
#   4) le righe consegnate sono `limit`, mai `limit + 1` (la sonda non deve
#      trapelare a chi legge)
# ------------------------------------------------------------

from __future__ import annotations

import unittest

from django.db import connection

from apps.catalogo.services import catalogo_service
from apps.core.tests.db_e2e import richiedi_db_provvisto


# Scopo: quanti articoli ATTIVI esistono adesso — il perimetro di default del
#        lookup articoli (la view passa `attivo=True` quando il parametro manca).
def _articoli_attivi() -> int:
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM catalogo.vw_articoli_dettaglio WHERE attivo")
        row = cursor.fetchone()
        return int(row[0]) if row else 0


class LookupArticoliTroncamentoTests(unittest.TestCase):
    """La sonda `+1` sul lookup VIVO — quello che l'applicazione chiama davvero.

    ⚠️ Questa query non e' una `SELECT` su una tabella sola: monta fino a DUE
       JOIN condizionali (tre fino al 2026-10-14, quando e' uscito il filtro
       natura delle righe di documento). La sonda regge finche' quei JOIN sono 1:1 — uno che
       moltiplicasse le righe le farebbe contare due volte e direbbe «troncato»
       su un elenco intero, buttando per giunta righe vere col taglio. E' il
       ramo che i test col repository mockato non possono nemmeno sfiorare.
    """

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()
        cls.disponibili = _articoli_attivi()

    def setUp(self) -> None:
        if self.disponibili < 2:
            self.skipTest(
                f"servono almeno 2 articoli attivi per distinguere troncato/non "
                f"troncato: qui ce ne sono {self.disponibili}",
            )

    # 1. Chiesto meno del disponibile: il taglio c'e' e si dichiara.
    def test_chiedendo_meno_del_disponibile_dichiara_il_troncamento(self):
        esito = catalogo_service.fn_lookup_articoli(limit=1)
        self.assertEqual(len(esito["results"]), 1)
        self.assertTrue(esito["troncato"], "il lookup ha tagliato e non lo dice")

    # 2. Un insieme sotto il tetto: nessun taglio, e il flag lo sa.
    #    ⚠️ Il caso si costruisce RESTRINGENDO (il codice esatto di un articolo
    #    che esiste), non alzando il tetto: il clamp e' 50 e gli articoli
    #    possono essere di piu', quindi quella strada finirebbe in uno skip
    #    proprio sul test che impedisce al flag di essere incollato.
    def test_un_insieme_sotto_il_tetto_non_dichiara_troncamento(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT codice FROM catalogo.vw_articoli_dettaglio "
                "WHERE attivo ORDER BY codice LIMIT 1",
            )
            riga = cursor.fetchone()
        self.assertIsNotNone(riga, "nessun articolo attivo: il caso non esiste")

        esito = catalogo_service.fn_lookup_articoli(search=riga[0], limit=50)

        self.assertGreaterEqual(len(esito["results"]), 1)
        self.assertLess(
            len(esito["results"]), 50,
            "la ricerca doveva restringere sotto il tetto: caso non costruito",
        )
        self.assertFalse(esito["troncato"], "nessun taglio, eppure lo dichiara")

    # 3. ⭐ IL RAMO CON I JOIN, che e' la ragione di questa classe. Con
    #    `solo_oneri` la query monta due JOIN (la base `articoli` e la causale):
    #    se uno di quelli moltiplicasse le righe, la sonda conterebbe doppioni.
    #    Il presidio e' il confronto con la lista SENZA filtro: restringere agli
    #    oneri puo' solo togliere righe, mai aggiungerne. (Fino al 2026-10-14 il
    #    ramo era quello di `escludi_destinazione_tipi`, ritirato col picker
    #    delle righe di documento sulla sede unica.)
    def test_il_ramo_con_join_non_moltiplica_le_righe(self):
        senza = catalogo_service.fn_lookup_articoli(limit=50)
        con = catalogo_service.fn_lookup_articoli(solo_oneri=True, limit=50)

        self.assertLessEqual(
            len(con["results"]), len(senza["results"]),
            "il JOIN degli oneri ha AGGIUNTO righe: sta moltiplicando, e la "
            "sonda +1 su questa query non significa piu' niente",
        )
        ids = [r["id"] for r in con["results"]]
        self.assertEqual(len(ids), len(set(ids)), "righe duplicate dal JOIN")

    # 4. ⛔ La riga in piu' e' una SONDA, non un risultato.
    def test_la_riga_di_sonda_non_arriva_a_chi_legge(self):
        esito = catalogo_service.fn_lookup_articoli(limit=2)
        self.assertEqual(len(esito["results"]), 2)
        self.assertEqual(esito["count"], 2)
