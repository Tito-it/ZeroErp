# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `VenditePipelineRepository.set_lotto_job_stato` sul DATABASE PROVVISTO:
#        lo stato del job e' un vocabolario in tabella (`config.stati_lotto_job`,
#        FK `fk_fatturazione_lotti_stato_lotto`), e il backend non ne tiene una
#        copia (brief-modello-documento-vendita §15.8 punto 2). Un valore fuori
#        vocabolario lo rifiuta il DB, e il rifiuto arriva con un codice.
# Note: ⭐ Il rifiuto e' del GUARD (BEFORE UPDATE, matrice
#       `config.transizioni_stati_lotto_job`), non della FK: il guard gira prima
#       e un codice fuori vocabolario non e' in nessuna riga della matrice. E'
#       quello che questo test fissa: il backend non deve tradurre un 23503 che
#       non arriva. Transazione annullata.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) test_stato_fuori_vocabolario_ha_il_codice — rifiuta il guard, col codice E_LOTTO_PARAMETRO_NON_COERENTE
2) test_stato_del_vocabolario_si_scrive — il verso buono: uno stato del vocabolario passa
"""
from __future__ import annotations

import unittest

from django.db import DatabaseError, connection, transaction

from apps.core.services.db_error_fields import db_error_code
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.vendite.db.pipeline_repository import VenditePipelineRepository


class LottoJobStatoDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        # Sonda: il verbo dello step del giro 11, nato con il vocabolario del job.
        richiedi_db_provvisto("vendite.fn_lotto_proietta_stato_step(bigint,bigint)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            cur.execute("SELECT script.fn_pgtap_set_contesto_operatore()")
            cur.execute("SELECT lotto_id FROM dbops.fn_pgtap_crea_lotto('job stato be')")
            self.lotto_id = cur.fetchone()[0]
            cur.execute("SELECT stato_lotto FROM vendite.fatturazione_lotti WHERE id = %s", [self.lotto_id])
            self.stato_iniziale = cur.fetchone()[0]

    def test_stato_fuori_vocabolario_ha_il_codice(self) -> None:
        # Savepoint: il rifiuto annulla solo questo blocco, non la transazione
        # del test.
        with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
            VenditePipelineRepository().set_lotto_job_stato(self.lotto_id, "NON_ESISTE", "nota")
        self.assertEqual(db_error_code(ctx.exception), "E_LOTTO_PARAMETRO_NON_COERENTE")

    def test_stato_del_vocabolario_si_scrive(self) -> None:
        # Uno stato del vocabolario diverso da quello attuale e raggiungibile
        # da li' secondo la matrice: lo si legge, non lo si scrive qui.
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT s_a.codice_interno
                  FROM config.transizioni_stati_lotto_job t
                  JOIN config.stati_lotto_job s_da ON s_da.id = t.stato_da_id
                  JOIN config.stati_lotto_job s_a ON s_a.id = t.stato_a_id
                 WHERE s_da.codice_interno = %s
                   AND t.attivo
                 ORDER BY s_a.codice_interno
                 LIMIT 1
                """,
                [self.stato_iniziale],
            )
            riga = cur.fetchone()
        if riga is None:
            self.skipTest(f"nessun passaggio del job da {self.stato_iniziale} nella matrice")
        VenditePipelineRepository().set_lotto_job_stato(self.lotto_id, riga[0], "nota")
        with connection.cursor() as cur:
            cur.execute("SELECT stato_lotto FROM vendite.fatturazione_lotti WHERE id = %s", [self.lotto_id])
            self.assertEqual(cur.fetchone()[0], riga[0])
