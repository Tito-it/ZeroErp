# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `MaintenanceRepository.corsa_riuscita_dal` sul database vero — la
#        lettura con cui `e_dovuto` sa se il lavoro del periodo e' fatto.
#        Righe COSTRUITE in transazione annullata, con un jobname che nessun
#        processo vero scrive: riuscita, fallita, prima dell'inizio, in corso,
#        e SALTATA — il lock della corsia tenuto da una seconda connessione,
#        cioe' il ramo vero di `fn_job_run_start`, non una riga scritta a mano
#        (brief-db-corsa-saltata-non-e-una-corsa §6, §8.6).
# ------------------------------------------------------------
"""Indice test previsti (su DB provvisto, `ZEROERP_TEST_DB_E2E=1`).

1. test_conta_solo_una_corsa_riuscita_dall_inizio_del_periodo
2. test_una_corsa_saltata_non_chiude_il_periodo
3. test_l_ultima_conclusa_e_la_corsa_vera_non_la_saltata
4. test_una_corsa_saltata_non_si_chiude
5. test_corsa_chiusa_conta_anche_la_fallita_non_la_saltata
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest import TestCase

from django.db import DatabaseError, connection, connections, transaction

from apps.core.db.maintenance_repository import MaintenanceRepository
from apps.core.services.processi import PROCESSO_DIGEST_PRESIDI
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto

_JOB = "test_e_dovuto:corsia"


class CorsaRiuscitaDalDbTests(TestCase):
    """La corsa che chiude il periodo."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)

    # Scopo: scrive una corsa della corsia di test DALLA PORTA dei processi
    #        (`fn_job_run_start`/`_end`: il ruolo applicativo non scrive la
    #        tabella), chiusa con `ok` o lasciata aperta. `started_at` e'
    #        l'istante della chiamata.
    def _corsa(self, ok: bool | None) -> None:
        with connection.cursor() as cur:
            # Il CHECK vuole un processo dichiarato: uno vero, in transazione annullata.
            cur.execute(
                "SELECT id FROM script.fn_job_run_start(%s, 'CRON', NULL, NULL, NULL, %s, NULL)",
                [_JOB, PROCESSO_DIGEST_PRESIDI],
            )
            row = cur.fetchone()
            assert row is not None
            if ok is not None:
                cur.execute(
                    "SELECT script.fn_job_run_end(%s, %s, NULL, NULL, NULL, NULL, NULL::jsonb, NULL)",
                    [row[0], ok],
                )

    # Scopo: la corsa SALTATA, dal ramo vero: una seconda connessione apre una
    #        corsa con la stessa chiave di lock e la tiene aperta (transazione
    #        mai confermata, lock di SESSIONE preso), poi questa connessione ne
    #        apre un'altra, che trova il lock occupato. Ritorna l'id della skip.
    # ⚠️ Il lock e' di sessione: lo stesso processo lo riprende (rientrante),
    #    quindi una connessione sola non sa costruire il caso. La seconda si
    #    annulla e si chiude in cleanup: la sua riga non resta, e il lock cade
    #    con la sessione.
    def _corsa_saltata(self) -> int:
        altra = connections.create_connection("default")
        self.addCleanup(altra.close)
        altra.set_autocommit(False)
        self.addCleanup(altra.rollback)
        with altra.cursor() as cur:
            cur.execute(
                "SELECT acquired FROM script.fn_job_run_start(%s, 'CRON', NULL, %s, NULL, %s, NULL)",
                [_JOB, _JOB, PROCESSO_DIGEST_PRESIDI],
            )
            row = cur.fetchone()
            assert row is not None
            self.assertTrue(row[0], "la seconda connessione deve prendere il lock")
        with connection.cursor() as cur:
            cur.execute(
                "SELECT id, acquired FROM script.fn_job_run_start(%s, 'CRON', NULL, %s, NULL, %s, NULL)",
                [_JOB, _JOB, PROCESSO_DIGEST_PRESIDI],
            )
            row = cur.fetchone()
            assert row is not None
            self.assertFalse(row[1], "il lock e' occupato: la corsa deve essere saltata")
            cur.execute(
                "SELECT saltata, ok, ended_at IS NOT NULL FROM maintenance.job_run_log WHERE id = %s",
                [row[0]],
            )
            forma = cur.fetchone()
        self.assertEqual(forma, (True, None, True), "la skip nasce saltata, senza esito, chiusa")
        return int(row[0])

    # 1. Fallita e in corso non chiudono il periodo; una riuscita da `dal` in
    #    poi si', e una riuscita PRIMA di `dal` no.
    def test_conta_solo_una_corsa_riuscita_dall_inizio_del_periodo(self) -> None:
        repo = MaintenanceRepository()
        prima = datetime.now(UTC) - timedelta(hours=1)
        dopo = datetime.now(UTC) + timedelta(hours=1)
        self.assertFalse(repo.corsa_riuscita_dal(_JOB, prima))
        self._corsa(ok=False)
        self._corsa(ok=None)
        self.assertFalse(repo.corsa_riuscita_dal(_JOB, prima), "fallita o in corso non chiude il periodo")
        self._corsa(ok=True)
        self.assertTrue(repo.corsa_riuscita_dal(_JOB, prima))
        self.assertFalse(repo.corsa_riuscita_dal(_JOB, dopo), "una corsa prima dell'inizio e' del periodo precedente")

    # 2. Lo scenario del brief (§2.1): una corsa fallita, poi una sveglia che
    #    trova il lock occupato. Fino al 2026-10-10 la skip aveva `ok = true` e
    #    il periodo risultava fatto: la sveglia dopo non riprovava piu'.
    def test_una_corsa_saltata_non_chiude_il_periodo(self) -> None:
        repo = MaintenanceRepository()
        prima = datetime.now(UTC) - timedelta(hours=1)
        self._corsa(ok=False)
        self._corsa_saltata()
        self.assertFalse(repo.corsa_riuscita_dal(_JOB, prima), "una skip non e' il lavoro fatto")

    # 3. Per la liveness la skip e' segno di vita (la riga piu' recente, chiusa:
    #    non «in corso»), ma l'ultima conclusa resta la corsa VERA, col suo
    #    esito; nel riepilogo la skip non e' un'esecuzione.
    def test_l_ultima_conclusa_e_la_corsa_vera_non_la_saltata(self) -> None:
        repo = MaintenanceRepository()
        self._corsa(ok=False)
        self._corsa_saltata()
        corsa = repo.job_liveness([_JOB], soglia_minuti=60)[_JOB]
        self.assertTrue(corsa["attivo"], "la sveglia e' scattata: segno di vita")
        self.assertFalse(corsa["in_corso"], "la skip e' chiusa")
        self.assertIsNotNone(corsa["ultima_conclusa"])
        self.assertIs(corsa["ultima_conclusa"]["ok"], False, "l'esito e' della corsa fallita, non della skip")
        riepilogo, _ = repo.list_job_summary(jobname_prefix=_JOB)
        self.assertEqual(len(riepilogo), 1)
        self.assertEqual(
            (riepilogo[0]["total_runs"], riepilogo[0]["fail_count"], riepilogo[0]["saltate_count"]),
            (1, 1, 1),
        )
        righe, _ = repo.list_job_runs(jobname=_JOB)
        self.assertEqual([r["saltata"] for r in righe], [True, False])

    # 4. Chiudere una skip e' un chiamante rotto: il DB la rifiuta (dal -23),
    #    col codice TECNICO che il backend conosce.
    def test_una_corsa_saltata_non_si_chiude(self) -> None:
        run_id = self._corsa_saltata()
        with self.assertRaises(DatabaseError) as ctx, transaction.atomic(), connection.cursor() as cur:
            cur.execute(
                "SELECT script.fn_job_run_end(%s, true, NULL, NULL, NULL, NULL, NULL::jsonb, NULL)",
                [run_id],
            )
        self.assertIn("E_JOB_RUN_SALTATA_NON_CHIUDIBILE", str(ctx.exception))

    # 5. `corsa_chiusa_dal` (il `dovuto` con `basta_una_corsa`): una corsa
    #    FALLITA chiude il periodo, una saltata o ancora in corso no.
    def test_corsa_chiusa_conta_anche_la_fallita_non_la_saltata(self) -> None:
        repo = MaintenanceRepository()
        prima = datetime.now(UTC) - timedelta(hours=1)
        self._corsa(ok=None)
        self._corsa_saltata()
        self.assertFalse(repo.corsa_chiusa_dal(_JOB, prima), "in corso o saltata non e' una corsa chiusa")
        self._corsa(ok=False)
        self.assertTrue(repo.corsa_chiusa_dal(_JOB, prima), "una fallita e' una corsa chiusa")
        self.assertFalse(repo.corsa_riuscita_dal(_JOB, prima), "ma non riuscita")

