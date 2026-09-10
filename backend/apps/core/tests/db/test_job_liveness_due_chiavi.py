# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le DUE CHIAVI di `MaintenanceRepository.job_liveness` — per jobname
#        (i due drainer) e per `processo_codice` (i processi a piu' corsie).
# Note: ⭐ Perche' esiste. Il badge delle code chiede la liveness per NOME, e il
#        suo commento dichiara aperto il caso opposto: «dove jobname e processo
#        non coincidono — le corsie di `run_fatturazione_batch`, che attaccano
#        la corsia al jobname — la liveness non si fa da qui». Il battito del
#        digest dei presidi e' il primo che ne ha bisogno, e la chiave onesta e'
#        `processo_codice`: ha una FK dura verso `dbops.processi`.
#        ⛔ Il guard sulle due chiavi si prova SENZA database: e' quello che
#        impedisce a una chiamata senza filtro di rispondere la liveness
#        dell'INTERO giornale — un errore che non fallisce, restituisce solo la
#        cosa sbagliata.
# ------------------------------------------------------------

"""Indice test previsti.

Senza database:
  1. test_senza_nessuna_chiave_si_ferma
  2. test_con_tutte_e_due_le_chiavi_si_ferma
  3. test_la_chiave_processo_filtra_sul_processo
  4. test_una_lista_di_jobname_vuota_non_interroga_il_giornale

Su DB provvisto (`ZEROERP_TEST_DB_E2E=1`):
  5. test_la_liveness_per_processo_gira_sul_database_vero
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.db import maintenance_repository as modulo
from apps.core.db.maintenance_repository import MaintenanceRepository
from apps.core.services.processi import PROCESSO_DIGEST_PRESIDI
from apps.core.tests.db_e2e import richiedi_db_provvisto


class JobLivenessGuardTests(SimpleTestCase):
    """Il guard delle due chiavi, senza database."""

    def setUp(self) -> None:
        self.repo = MaintenanceRepository()

    # 1-2. ⛔ Esattamente UNA chiave. Senza filtro la query leggerebbe il
    #      giornale intero e risponderebbe la liveness di tutto; con tutte e due
    #      il chiamante crede di aver ristretto due volte e ne vale una sola.
    def test_senza_nessuna_chiave_si_ferma(self) -> None:
        finta = MagicMock()
        with patch.object(modulo, "connection", finta):
            with self.assertRaises(ValueError):
                self.repo.job_liveness(soglia_minuti=10)
        finta.cursor.assert_not_called()

    def test_con_tutte_e_due_le_chiavi_si_ferma(self) -> None:
        finta = MagicMock()
        with patch.object(modulo, "connection", finta):
            with self.assertRaises(ValueError):
                self.repo.job_liveness(
                    ["un_job"], soglia_minuti=10, processo_codice="un_processo",
                )
        finta.cursor.assert_not_called()

    # 3. La chiave nuova filtra sul PROCESSO, e il valore viaggia come parametro.
    def test_la_chiave_processo_filtra_sul_processo(self) -> None:
        cursore = MagicMock()
        cursore.fetchall.return_value = []
        cursore.__enter__ = MagicMock(return_value=cursore)
        cursore.__exit__ = MagicMock(return_value=False)
        finta = MagicMock()
        finta.cursor.return_value = cursore
        with patch.object(modulo, "connection", finta):
            self.repo.job_liveness(
                soglia_minuti=90, processo_codice="un_processo",
            )
        sql, params = cursore.execute.call_args[0]
        self.assertIn("processo_codice = %s", sql)
        self.assertNotIn("jobname = ANY", sql)
        self.assertEqual(params, [90, "un_processo"])

    # 4. Una lista vuota non e' «nessun filtro»: e' «nessun job», e la risposta
    #    e' vuota senza interrogare niente.
    def test_una_lista_di_jobname_vuota_non_interroga_il_giornale(self) -> None:
        finta = MagicMock()
        with patch.object(modulo, "connection", finta):
            self.assertEqual(self.repo.job_liveness([], soglia_minuti=10), {})
        finta.cursor.assert_not_called()


class JobLivenessSulDatabaseTests(TestCase):
    """La query per processo, contro il database vero (sola lettura)."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # 5. ⚠️ Non si asserisce su QUANTE corse ci siano — sarebbe una misura sulla
    #    popolazione di oggi, che in CI e' un'altra. Si prova che la query LEGA:
    #    la colonna esiste, il filtro compila, e la forma della risposta e'
    #    quella che il chiamante si aspetta.
    def test_la_liveness_per_processo_gira_sul_database_vero(self) -> None:
        esito = MaintenanceRepository().job_liveness(
            processo_codice=PROCESSO_DIGEST_PRESIDI, soglia_minuti=1440,
        )
        self.assertIsInstance(esito, dict)
        for jobname, corsa in esito.items():
            with self.subTest(jobname=jobname):
                self.assertIn("last_run_at", corsa)
                self.assertIn("attivo", corsa)
                self.assertIn("last_ok", corsa)
                # ⭐ Il jobname porta la corsia: e' la forma che il battito
                #    ritrova, ed e' il motivo per cui la chiave e' il processo.
                self.assertTrue(jobname.startswith(PROCESSO_DIGEST_PRESIDI))
