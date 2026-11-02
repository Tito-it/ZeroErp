# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La PROVENIENZA di un ordine da offerta sul DATABASE PROVVISTO, dopo il
#        lotto 2b della grammatica unica (brief-db-grammatica-unica-documenti
#        §12, 2026-10-19): `vendite.ordini.documento_origine_tipo` ha la FK
#        verso `config.sorgenti`. Dal 2026-10-21 la provenienza la scrive il
#        verbo DB `vendite.fn_genera_ordine_da_offerta` (provato dalla
#        giuntura `test_genera_ordine_da_offerta_db.py`): qui si scrive a mano,
#        per provare chi la LEGGE.
#        Lo stesso caso, letto dal BB dei legami: l'`origine` e' il codice
#        della sorgente, e per l'offerta e' anche il tipo del documento da
#        aprire.
# Note: ⚠️ La giuntura che i test mockati non vedono: un codice corto
#       (`OFFERTA`) e' un rifiuto della FK solo sul DB vero, e fino al giro
#       BE del 2b era proprio cio' che `crea_ordine_da_offerta` scriveva.
#       L'ordine lo costruisce lo stampo `dbops.fn_pgtap_crea_ordine`; l'id
#       dell'offerta e' polimorfo (nessuna FK), quindi non serve un'offerta
#       vera per provare il vocabolario. Transazione SEMPRE annullata.
#       Opt-in `ZEROERP_TEST_DB_E2E=1`.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) OrigineOrdineSorgenteDbTests.test_provenienza_col_codice_della_sorgente
   (anche: i legami dell'ordine la riportano, col tipo da aprire)
2) OrigineOrdineSorgenteDbTests.test_il_codice_corto_e_rifiutato
3) OrigineOrdineSorgenteDbTests.test_etichetta_dell_origine_per_la_stampa
   (§12.10.4: `get_ordine` porta il nome del tipo d'origine da
   `config.sorgenti.etichetta`, NULL senza origine; il builder lo passa)
"""
from __future__ import annotations

import unittest

import psycopg
from django.db import IntegrityError, connection, transaction

from apps.config.sorgenti import SORGENTE_OFFERTA_COMMERCIALE, SORGENTE_ORDINE_VENDITA
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.vendite.db.ordini_repository import OrdiniRepository
from apps.vendite.services.ordine_document_context_builder import (
    OrdineDocumentContextBuilder,
)
from apps.vendite.services._annullo_con_legami import legami_del_documento

# Un id d'offerta qualunque: `documento_origine_id` e' polimorfo.
_OFFERTA_ID = 987654321


# Scopo: la provenienza scritta a mano sull'ordine del test (le colonne che il
#        verbo DB valorizza nella sua INSERT).
def _scrivi_origine(ordine_id: int, tipo: str, origine_id: int) -> None:
    with connection.cursor() as cur:
        cur.execute(
            "UPDATE vendite.ordini SET documento_origine_tipo = %s, documento_origine_id = %s"
            " WHERE id = %s",
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
            cur.execute("SELECT ordine_id FROM dbops.fn_pgtap_crea_ordine('origine 2b')")
            self.ordine_id = int(cur.fetchone()[0])

    def test_provenienza_col_codice_della_sorgente(self) -> None:
        _scrivi_origine(self.ordine_id, SORGENTE_OFFERTA_COMMERCIALE, _OFFERTA_ID)
        out = legami_del_documento(SORGENTE_ORDINE_VENDITA, self.ordine_id)
        provenienze = [r for r in out["righe"] if r["natura"] == "PROVENIENZA"]
        self.assertEqual(len(provenienze), 1, out["righe"])
        riga = provenienze[0]
        self.assertEqual(riga["origine"], SORGENTE_OFFERTA_COMMERCIALE)
        self.assertEqual(riga["origine_id"], _OFFERTA_ID)
        # Il tipo da aprire e' l'origine stessa: nessuna traduzione.
        self.assertEqual(riga["origine_tipo_codice_interno"], SORGENTE_OFFERTA_COMMERCIALE)

    def test_il_codice_corto_e_rifiutato(self) -> None:
        with self.assertRaises(IntegrityError) as cm:
            with transaction.atomic():
                _scrivi_origine(self.ordine_id, "OFFERTA", _OFFERTA_ID)
        # Il vincolo dal canale strutturato di libpq, non dal testo.
        causa = cm.exception.__cause__
        self.assertIsInstance(causa, psycopg.Error)
        assert isinstance(causa, psycopg.Error)
        self.assertEqual(
            causa.diag.constraint_name,
            "fk_ordini_documento_origine_tipo_sorgenti",
        )

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

        _scrivi_origine(self.ordine_id, SORGENTE_OFFERTA_COMMERCIALE, _OFFERTA_ID)
        with connection.cursor() as cur:
            cur.execute(
                "SELECT etichetta FROM config.sorgenti WHERE codice_interno = %s",
                [SORGENTE_OFFERTA_COMMERCIALE],
            )
            attesa = cur.fetchone()[0]
        con = repo.get_ordine(self.ordine_id)
        assert con is not None
        self.assertEqual(con["documento_origine_etichetta"], attesa)

        origine = OrdineDocumentContextBuilder(repo=repo).build_context(
            self.ordine_id,
        )["ordine"]["origine"]
        self.assertEqual(origine["tipo"], SORGENTE_OFFERTA_COMMERCIALE)
        self.assertEqual(origine["etichetta"], attesa)
