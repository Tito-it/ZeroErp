# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La PROVENIENZA di un ordine sul DATABASE PROVVISTO, letta da chi la
#        LEGGE: il lettore dell'ordine nato dal preventivo
#        (`OrdiniRepository.get_ordine_by_documento_origine`, smistamento e
#        handler della pratica) e l'etichetta per la stampa. La scrivono i
#        verbi DB; qui si scrive a mano, con la coppia che da' il BB che scrive
#        (`script.fn_sorgente_provenienza`), per provare i lettori.
# Note: ⭐ Dal giro T.5 di brief-db-sorgente-documento-e-riga (2026-11-07) la
#       provenienza e' SOLO `sorgente_tipo_id` + `sorgente_id | sorgente_uid`:
#       `documento_origine_tipo/_id` non esistono piu', e con loro il test del
#       «codice corto» rifiutato dalla loro FK (lotto 2b della grammatica
#       unica). Il tipo ora e' un id di `config.sorgenti`, e il guard unico
#       della provenienza vuole un documento che esiste: l'origine e' un
#       preventivo vero (`dbops.fn_pgtap_crea_preventivo`), non un id
#       inventato. Il preventivo ha chiave `uid`: la provenienza e'
#       `sorgente_uid`, e i lettori la incontrano con la regola del modello.
#       ⚠️ I legami dell'ordine (`fn_documento_legami`) riportano in testata
#       la sola provenienza dall'OFFERTA (quella dal preventivo e' per riga):
#       quel caso lo prova `test_genera_ordine_da_offerta_db`, sull'ordine che
#       genera il verbo. Transazione SEMPRE annullata. Opt-in `ZEROERP_TEST_DB_E2E=1`.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) OrigineOrdineSorgenteDbTests.test_l_ordine_nato_dal_preventivo_si_trova
   (BE-T.5-a: dalla provenienza; un preventivo senza ordini da' None)
2) OrigineOrdineSorgenteDbTests.test_etichetta_dell_origine_per_la_stampa
   (`get_ordine` porta il nome del tipo d'origine da
   `config.sorgenti.etichetta`, NULL senza origine; il builder lo passa)
"""
from __future__ import annotations

import unittest

from django.db import connection

from apps.config.sorgenti import SORGENTE_PREVENTIVO
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.vendite.db.ordini_repository import OrdiniRepository
from apps.vendite.services.ordine_document_context_builder import (
    OrdineDocumentContextBuilder,
)

# Scopo: la provenienza scritta a mano sull'ordine del test, con la coppia
#        del BB che la scrive per i verbi (tipo + la sola chiave del tipo).
def _scrivi_origine(ordine_id: int, tipo: str, origine_id: int) -> None:
    with connection.cursor() as cur:
        cur.execute(
            "UPDATE vendite.ordini o"
            "   SET (sorgente_tipo_id, sorgente_id, sorgente_uid) ="
            "       (SELECT p.sorgente_tipo_id, p.sorgente_id, p.sorgente_uid"
            "          FROM script.fn_sorgente_provenienza(%s, %s::text) p)"
            " WHERE o.id = %s",
            [tipo, origine_id, ordine_id],
        )


class OrigineOrdineSorgenteDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto("dbops.fn_pgtap_crea_ordine(text,character varying,bigint,date)")

    # La transazione del test, annullata sempre (anche se il setUp si
    # interrompe): il BB di `db_e2e`, non un `try/except` ricopiato.
    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            cur.execute("SELECT preventivo_id FROM dbops.fn_pgtap_crea_preventivo('origine ordine')")
            self.preventivo_id = int(cur.fetchone()[0])
            cur.execute("SELECT ordine_id FROM dbops.fn_pgtap_crea_ordine('origine ordine')")
            self.ordine_id = int(cur.fetchone()[0])

    # BE-T.5-a: il lettore cercava `documento_origine_tipo/_id`, che dal giro
    # T.5 non esistono. Ora parte dal preventivo (id) e incontra l'ordine sulla
    # sua chiave `uid`: la giuntura che i mock dello smistamento non vedono.
    def test_l_ordine_nato_dal_preventivo_si_trova(self) -> None:
        repo = OrdiniRepository()
        self.assertIsNone(repo.get_ordine_by_documento_origine(SORGENTE_PREVENTIVO, self.preventivo_id))
        _scrivi_origine(self.ordine_id, SORGENTE_PREVENTIVO, self.preventivo_id)
        trovato = repo.get_ordine_by_documento_origine(SORGENTE_PREVENTIVO, self.preventivo_id)
        assert trovato is not None
        self.assertEqual(trovato["id"], self.ordine_id)
        self.assertIn("numero", trovato)

    # La giuntura della forma 3: la JOIN di `get_ordine` su `config.sorgenti`
    # per codice. Un nome di colonna sbagliato o un JOIN interno (l'ordine
    # senza origine sparirebbe: 404 sulla stampa) i mock non li vedono.
    # L'etichetta attesa si legge dal catalogo, non si ricopia: il testo e'
    # del CSV, e cambiarlo li' non deve rompere questo test.
    def test_etichetta_dell_origine_per_la_stampa(self) -> None:
        repo = OrdiniRepository()
        senza = repo.get_ordine(self.ordine_id)
        assert senza is not None
        self.assertIn("documento_origine_etichetta", senza)
        self.assertIsNone(senza["documento_origine_etichetta"])

        _scrivi_origine(self.ordine_id, SORGENTE_PREVENTIVO, self.preventivo_id)
        with connection.cursor() as cur:
            cur.execute(
                "SELECT etichetta FROM config.sorgenti WHERE codice_interno = %s",
                [SORGENTE_PREVENTIVO],
            )
            attesa = cur.fetchone()[0]
        con = repo.get_ordine(self.ordine_id)
        assert con is not None
        self.assertEqual(con["documento_origine_etichetta"], attesa)

        origine = OrdineDocumentContextBuilder(repo=repo).build_context(
            self.ordine_id,
        )["ordine"]["origine"]
        self.assertEqual(origine["tipo"], SORGENTE_PREVENTIVO)
        self.assertEqual(origine["etichetta"], attesa)
