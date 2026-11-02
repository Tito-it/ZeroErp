# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
  6. test_una_corsa_aperta_non_e_un_esito_e_la_conclusa_porta_la_sua_data   ⭐ 14-09
"""

from __future__ import annotations

import uuid
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.db import connection, transaction
from django.test import SimpleTestCase

from apps.core.db import maintenance_repository as modulo
from apps.core.db.maintenance_repository import MaintenanceRepository
from apps.core.services.job_run import ORIGINE_COMMAND
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
        # ⚠️ Il valore del filtro va una volta per CTE (`recente`, `conclusa`),
        #    poi la soglia: e' l'ordine dei `%s` nel testo, e un parametro
        #    fuori posto qui non fallisce — filtra sulla cosa sbagliata.
        self.assertEqual(params, ["un_processo", "un_processo", 90])

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
                self.assertIn("in_corso", corsa)
                self.assertIn("ultima_conclusa", corsa)
                # ⭐ Il jobname porta la corsia: e' la forma che il battito
                #    ritrova, ed e' il motivo per cui la chiave e' il processo.
                self.assertTrue(jobname.startswith(PROCESSO_DIGEST_PRESIDI))

    # 6. ⛔ `ok` ha TRE facce — true, false, NULL = corsa ancora aperta — e
    #    una corsa aperta NON e' un esito. Fino al 2026-09-14 (mattina) la riga
    #    piu' recente dava l'esito: il digest, componendo la mail dentro la
    #    propria corsa, si chiamava «FALLITA». La correzione della mattina
    #    prese l'esito dall'ultima CONCLUSA — ma lascio' la DATA sulla riga piu'
    #    recente: «09:47:32 (ok)», l'ora della corsa in esecuzione con l'ok di
    #    quella delle 07:30 (nota del team DB, sera). Qui il caso si
    #    COSTRUISCE, con le stesse funzioni con cui il giornale si scrive
    #    davvero (`script.fn_job_run_start/_end`, SECURITY DEFINER), e si
    #    ritira: una corsa chiusa ok = true, poi una corsa APERTA sullo stesso
    #    jobname. Entrambe le sedi — `job_liveness` e `list_job_summary` —
    #    devono dire `in_corso`, la liveness deve vedere la corsa aperta come
    #    segno di vita, e `ultima_conclusa` deve portare l'esito CON LA DATA
    #    DELLA PRIMA corsa — non quella dell'aperta.
    def test_una_corsa_aperta_non_e_un_esito_e_la_conclusa_porta_la_sua_data(self) -> None:
        jobname = "test-liveness-corsa-aperta:" + uuid.uuid4().hex[:8]

        def apri(cur) -> int:
            cur.execute(
                "SELECT id FROM script.fn_job_run_start(%s, %s, %s, %s, %s, %s, %s)",
                [jobname, ORIGINE_COMMAND, "test", None, "test", PROCESSO_DIGEST_PRESIDI, None],
            )
            riga = cur.fetchone()
            assert riga is not None
            return int(riga[0])

        with transaction.atomic():
            with connection.cursor() as cur:
                prima = apri(cur)
                cur.execute(
                    "SELECT script.fn_job_run_end(%s, %s, %s, %s, %s, %s, %s::jsonb, %s)",
                    [prima, True, "conclusa", 0, None, None, None, None],
                )
                seconda = apri(cur)  # resta APERTA: ok NULL, ended_at NULL
                # ⚠️ La premessa si ASSERISCE, non si presume: due righe, una
                #    aperta, e l'aperta e' la PIU' RECENTE (`started_at` e'
                #    `clock_timestamp()`, quindi cresce anche dentro una
                #    transazione) — e' esattamente la riga che il difetto leggeva.
                cur.execute(
                    "SELECT count(*), count(*) FILTER (WHERE ended_at IS NULL), "
                    "       (ARRAY_AGG(ended_at IS NULL ORDER BY started_at DESC))[1] "
                    "  FROM maintenance.job_run_log WHERE jobname = %s",
                    [jobname],
                )
                totale, aperte, recente_aperta = cur.fetchone()
                # Le due date, per confrontarle con cio' che le sedi rispondono.
                cur.execute(
                    "SELECT started_at FROM maintenance.job_run_log WHERE id = %s", [prima],
                )
                avvio_prima = cur.fetchone()[0].isoformat()
                cur.execute(
                    "SELECT started_at FROM maintenance.job_run_log WHERE id = %s", [seconda],
                )
                avvio_seconda = cur.fetchone()[0].isoformat()
            self.assertEqual((totale, aperte), (2, 1), "il caso non e' stato costruito")
            self.assertTrue(recente_aperta, "la riga piu' recente doveva essere quella aperta")
            self.assertNotEqual(avvio_prima, avvio_seconda)

            liveness = MaintenanceRepository().job_liveness(
                jobnames=[jobname], soglia_minuti=60,
            )
            corsa = liveness[jobname]
            self.assertTrue(corsa["attivo"], "una corsa aperta e' un segno di vita")
            self.assertTrue(corsa["in_corso"], "la riga piu' recente e' aperta, e va detto")
            self.assertEqual(corsa["last_run_at"], avvio_seconda)
            conclusa = corsa["ultima_conclusa"]
            self.assertIsNotNone(conclusa)
            self.assertIs(conclusa["ok"], True, "la corsa aperta e' stata letta come esito")
            # ⛔ La cucitura: l'esito della prima con la data della seconda.
            self.assertEqual(
                conclusa["started_at"], avvio_prima,
                "l'esito viaggia con la data di un'altra corsa",
            )
            self.assertIsNotNone(conclusa["ended_at"])

            righe, _totale = MaintenanceRepository().list_job_summary(
                jobname_prefix=jobname, limit=10, offset=0,
            )
            self.assertEqual(len(righe), 1)
            self.assertTrue(righe[0]["in_corso"], "la seconda sede non vede la corsa aperta")
            self.assertIs(righe[0]["ultima_conclusa"]["ok"], True)
            self.assertEqual(
                righe[0]["ultima_conclusa"]["started_at"], avvio_prima,
                "la seconda sede ha ancora la cucitura",
            )
            transaction.set_rollback(True)
