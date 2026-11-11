# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: UNA RIGA DI COMMESSA SENZA FATTORE, dal push del backend fino al DB
#        vero (BE23 di brief-db-revisione-catalogo, D26, 2026-11-11). Il
#        backend passa il fattore COM'E' (`_map_pushable_row` non scrive piu'
#        1 al posto di un NULL), e decide il DB
#        (`vendite.trgfn_attivita_fattore_alla_data`): nell'unita' base il
#        fattore e' 1, in un'unita' senza conversione la riga si rifiuta con
#        `E_UOM_MISSING` (il batch ne riporta la frase).
# Note: ⭐ Il mondo si COSTRUISCE (regola zero): commessa, articolo e riga dai
#       builder dei pgTAP, e un'unita' NUOVA, nata nella transazione, che per
#       costruzione non ha conversioni. Transazione annullata.
#       ⚠️ Prima di D26 il caso 2 passava: 3 cartoni diventavano 3 pezzi.
#       Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) CommessaFattoreSenzaDbTests.test_il_push_non_scrive_uno_al_posto_del_null
2) CommessaFattoreSenzaDbTests.test_senza_fattore_nella_base_vale_uno
3) CommessaFattoreSenzaDbTests.test_senza_fattore_fuori_dalla_base_si_rifiuta
"""
from __future__ import annotations

import unittest
from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

from django.db import connection

from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.vendite.db.commesse_repository import (
    CommessaAttivitaInput,
    CommesseRepository,
    _map_pushable_row,
)


class CommessaFattoreSenzaDbTests(unittest.TestCase):
    def setUp(self) -> None:
        richiedi_db_provvisto("vendite.trgfn_attivita_fattore_alla_data()")
        apri_transazione_annullata(self)
        sfx = uuid4().hex[:8].upper()
        self.codice_uom_senza = self._codice_uom(sfx)
        with connection.cursor() as cur:
            cur.execute("SELECT commessa_id FROM dbops.fn_pgtap_crea_commessa('BE23 fattore senza')")
            self.commessa = cur.fetchone()[0]
            cur.execute("SELECT dbops.fn_pgtap_crea_articolo(%s::varchar, false)", [f"PGT-BE23-{sfx}"])
            articolo = cur.fetchone()[0]
            cur.execute(
                "SELECT attivita_id FROM dbops.fn_pgtap_crea_commessa_attivita(%s, p_articolo_id => %s)",
                [self.commessa, articolo],
            )
            attivita = cur.fetchone()[0]
            # Un'unita' nuova della stessa tipologia della base: nessuna
            # mappatura dell'articolo e nessuna conversione generale la toccano.
            cur.execute(
                "INSERT INTO catalogo.unita_misura (codice, descrizione, tipo_uom_id)"
                " SELECT %s, 'BE23 senza conversione', um.tipo_uom_id"
                "   FROM catalogo.articoli a JOIN catalogo.unita_misura um ON um.id = a.uom_id"
                "  WHERE a.id = %s RETURNING id",
                [self._codice_uom(sfx), articolo],
            )
            self.uom_senza = cur.fetchone()[0]
            cur.execute(
                "SELECT segment_key, quantita, competenza_mese, articolo_id, prezzo_snapshot,"
                " uom_id, istanza_utility_id, data_attivita, competenza_dal, competenza_al,"
                " tipo_doc_fiscale_id, valuta_id, sorgente_tipo_id,"
                " COALESCE(sorgente_id::text, sorgente_uid::text), sorgente_riga"
                " FROM vendite.commesse_attivita WHERE id = %s",
                [attivita],
            )
            (
                segment_key, quantita, competenza_mese, articolo_id, prezzo, uom_id,
                istanza_utility_id, data_attivita, competenza_dal, competenza_al,
                tipo_doc_fiscale_id, valuta_id, sorgente_tipo_id, sorgente_chiave,
                sorgente_riga,
            ) = cur.fetchone()
        self.uom_base = uom_id
        # La riga del builder, ripushata (ramo ON CONFLICT sullo stesso
        # segmento) con la sua sorgente, come il push vero.
        self.riga = CommessaAttivitaInput(
            commessa_id=self.commessa,
            segment_key=segment_key,
            quantita=quantita,
            competenza_mese=competenza_mese,
            articolo_id=articolo_id,
            prezzo_snapshot=prezzo,
            uom_id=uom_id,
            istanza_utility_id=istanza_utility_id,
            data_attivita=data_attivita,
            competenza_dal=competenza_dal,
            competenza_al=competenza_al,
            tipo_doc_fiscale_id=tipo_doc_fiscale_id,
            valuta_id=valuta_id,
            sorgente_tipo_id=sorgente_tipo_id,
            sorgente_chiave=sorgente_chiave,
            sorgente_riga=sorgente_riga,
        )

    @staticmethod
    def _codice_uom(sfx: str) -> str:
        return f"B23{sfx}"[:20]

    def _fattore(self) -> tuple:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT uom_operativa_id, factor_to_base FROM vendite.commesse_attivita"
                " WHERE commessa_id = %s AND segment_key = %s",
                [self.commessa, self.riga.segment_key],
            )
            return cur.fetchone()

    # 1. Il binding del push: un NULL dal lister resta NULL (prima era 1).
    #    Senza DB: la mappa colonne e' quella che il repository costruisce.
    def test_il_push_non_scrive_uno_al_posto_del_null(self) -> None:
        from apps.vendite.db.commesse_repository import _PUSHABLE_SHARED_COLS

        colonne = list(_PUSHABLE_SHARED_COLS)
        valori: dict[str, object] = dict.fromkeys(colonne)
        valori.update({
            "sorgente_chiave": "1", "segment_key": "s", "fatturazione_immediata": False,
            "prezzo_bloccato": False, "pricing_mode": "LISTINO", "tipo_movimento": "NORMALE",
            "meta": "{}", "factor_to_base": None,
        })
        riga = _map_pushable_row({c: i for i, c in enumerate(colonne)}, tuple(valori[c] for c in colonne))
        self.assertIsNone(riga.factor_to_base)

    # 2. Senza fattore, nell'unita' base: il DB scrive 1.
    def test_senza_fattore_nella_base_vale_uno(self) -> None:
        esito = CommesseRepository().batch_upsert_attivita([replace(
            self.riga, uom_operativa_id=self.uom_base, qta_operativa=self.riga.quantita,
            factor_to_base=None,
        )])
        self.assertEqual(esito.errors, [])
        self.assertEqual(self._fattore(), (self.uom_base, Decimal("1")))

    # 3. Senza fattore, in un'unita' che per l'articolo non si converte: il
    #    rifiuto del DB, e la riga resta com'era.
    def test_senza_fattore_fuori_dalla_base_si_rifiuta(self) -> None:
        prima = self._fattore()
        esito = CommesseRepository().batch_upsert_attivita([replace(
            self.riga, uom_operativa_id=self.uom_senza, qta_operativa=Decimal("3"),
            factor_to_base=None,
        )])
        self.assertEqual(len(esito.errors), 1, esito.errors)
        # ⚠️ Il batch del DB riporta la FRASE del rifiuto, non il codice: si
        #    riconosce dall'unita' che nomina, costruita qui.
        self.assertIn(self.codice_uom_senza, esito.errors[0]["error"])
        self.assertEqual(self._fattore(), prima)
