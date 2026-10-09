# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `MaintenanceRepository.corsa_riuscita_dal` sul database vero — la
#        lettura con cui `e_dovuto` sa se il lavoro del periodo e' fatto.
#        Righe COSTRUITE in transazione annullata, con un jobname che nessun
#        processo vero scrive: riuscita, fallita, prima dell'inizio, in corso.
# ------------------------------------------------------------
"""Indice test previsti (su DB provvisto, `ZEROERP_TEST_DB_E2E=1`).

1. test_conta_solo_una_corsa_riuscita_dall_inizio_del_periodo
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest import TestCase

from django.db import connection

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
