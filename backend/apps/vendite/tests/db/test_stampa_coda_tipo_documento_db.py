# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La coda di stampa delle fatture dice che cosa stampare
#        (brief-db-modelli-documento-standard §9): il BINDING delle due
#        chiamate del repository col database vero.
# Note: ⭐ Prova la giuntura che i mock non vedono: la firma a due argomenti di
#       `vendite.fn_accoda_stampe_lotto(bigint, bigint)` (la `(bigint)` e'
#       stata ritirata dalla `20261020-30`) e la colonna
#       `tipo_documento_output_id` nel `RETURNING` del claim. Un nome
#       sbagliato e' un errore del parser anche a zero righe, quindi il test
#       non ha bisogno di una fattura: il lotto non esiste, e la coda resta
#       com'era. Le regole della coda (vincolo dei vivi, CHECK, FK) le prova
#       il pgTAP `vendite/test-stampa-coda-tipo-documento-v1.sql`.
#       ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1`. Tutto in transazione ANNULLATA.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) StampaCodaTipoDocumentoDbTests.test_accoda_col_tipo_lega_la_firma_a_due_argomenti
   `accoda_stampe_lotto(lotto, tipo)` e `accoda_stampe_lotto(lotto)` arrivano
   alla funzione; un lotto senza fatture accoda zero righe.
2) StampaCodaTipoDocumentoDbTests.test_claim_restituisce_il_tipo
   il `RETURNING` del claim nomina una colonna che esiste.
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.core.tests.db_e2e import Annulla, richiedi_db_provvisto
from apps.vendite.db.pipeline_repository import VenditePipelineRepository

# Un lotto che non esiste: la funzione non ha fatture da accodare.
_LOTTO_INESISTENTE = 2_000_000_000


class StampaCodaTipoDocumentoDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto("vendite.fn_accoda_stampe_lotto(bigint, bigint)")

    # 1. La firma a due argomenti, col tipo e senza.
    def test_accoda_col_tipo_lega_la_firma_a_due_argomenti(self) -> None:
        repo = VenditePipelineRepository()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                cur.execute(
                    "SELECT id FROM documenti.tipi_documento_output ORDER BY id LIMIT 1"
                )
                riga = cur.fetchone()
                self.assertIsNotNone(riga, "nessun tipo di documento nel seed")
                self.assertEqual(repo.accoda_stampe_lotto(_LOTTO_INESISTENTE, riga[0]), 0)
                self.assertEqual(repo.accoda_stampe_lotto(_LOTTO_INESISTENTE), 0)
                raise Annulla
        except Annulla:
            pass

    # 2. Il claim nomina la colonna del tipo.
    def test_claim_restituisce_il_tipo(self) -> None:
        repo = VenditePipelineRepository()
        try:
            with transaction.atomic():
                for item in repo.claim_stampe_pending(1):
                    self.assertIn("tipo_documento_output_id", item)
                raise Annulla
        except Annulla:
            pass
