# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del building block registered_job (registrazione run-level job headless).
# Indice test:
#   1) start acquired → corpo eseguito, fn_job_run_end chiamato con ok=True + meta
#   2) lock occupato (acquired=False) → corpo vede acquired False, NIENTE fn_job_run_end
#   3) eccezione nel corpo → fn_job_run_end ok=False + error_code/detail, eccezione rilanciata
#   4) ⭐ l'ATTORE arriva a fn_job_run_start — e non si deriva dal job_name
#   5) ⛔ senza attore il BB non si chiama: TypeError, non un run anonimo
# ------------------------------------------------------------

from __future__ import annotations

import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.db import DatabaseError

from apps.core.services.job_run import ORIGINE_CRON, registered_job
from apps.core.services.service_errors import ServiceError

_CONN = "apps.core.services.job_run.connection"
# Un codice qualsiasi: qui non si prova il VOCABOLARIO (lo presidia la FK a
# database), si prova che il parametro arrivi alla funzione.
_PROCESSO = "draina_coda_lavori"


def _mock_connection(*, start_row):
    """Scopo: mock connection con cursor che ritorna start_row su fetchone (start)."""
    cursor = MagicMock()
    cursor.fetchone.return_value = start_row
    conn = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn, cursor


def _executed_sql(cursor):
    return [c.args[0] for c in cursor.execute.call_args_list]


class RegisteredJobTests(TestCase):
    # Scopo: happy path — start acquired, corpo eseguito, end con ok=True + meta serializzato.
    def test_acquired_runs_body_and_ends_ok(self):
        conn, cursor = _mock_connection(start_row=(42, "uuid-1", True))
        with patch(_CONN, conn):
            with registered_job(
                "job:x", processo_codice=_PROCESSO,
                origine=ORIGINE_CRON, lock_key="job:x",
            ) as job:
                self.assertTrue(job.acquired)
                self.assertEqual(job.id, 42)
                self.assertEqual(job.run_uuid, "uuid-1")
                job.set_meta({"emittenti": 3})

        sqls = _executed_sql(cursor)
        self.assertTrue(any("fn_job_run_start" in s for s in sqls))
        self.assertTrue(any("fn_job_run_end" in s for s in sqls))
        # Argomenti di fn_job_run_end: id, ok=True, ..., meta json, lock_key.
        end_call = next(c for c in cursor.execute.call_args_list
                        if "fn_job_run_end" in c.args[0])
        params = end_call.args[1]
        self.assertEqual(params[0], 42)        # id
        self.assertIs(params[1], True)         # ok
        self.assertEqual(json.loads(params[6]), {"emittenti": 3})  # meta::jsonb
        self.assertEqual(params[7], "job:x")   # lock_key

    # Scopo: lock occupato → acquired False, corpo lo vede, fn_job_run_end NON chiamato.
    def test_not_acquired_skips_end(self):
        conn, cursor = _mock_connection(start_row=(99, "uuid-skip", False))
        with patch(_CONN, conn):
            with registered_job("job:x", processo_codice=_PROCESSO, lock_key="job:x") as job:
                self.assertFalse(job.acquired)

        sqls = _executed_sql(cursor)
        self.assertTrue(any("fn_job_run_start" in s for s in sqls))
        self.assertFalse(any("fn_job_run_end" in s for s in sqls))

    # Scopo: eccezione nel corpo → end con ok=False + error_code (ServiceError.code), rilancio.
    def test_exception_records_error_and_reraises(self):
        conn, cursor = _mock_connection(start_row=(7, "uuid-2", True))
        with patch(_CONN, conn):
            with self.assertRaises(ServiceError):
                with registered_job("job:x", processo_codice=_PROCESSO, lock_key="job:x"):
                    raise ServiceError(code="E_BOOM", message="rotto", detail="dett")

        end_call = next(c for c in cursor.execute.call_args_list
                        if "fn_job_run_end" in c.args[0])
        params = end_call.args[1]
        self.assertIs(params[1], False)        # ok
        self.assertEqual(params[4], "E_BOOM")  # error_code (ServiceError.code)
        self.assertIn("dett", params[5] or "")  # error_detail (str(ServiceError) = detail)

    # Scopo: un fallimento di fn_job_run_end (finally) NON deve mascherare l'eccezione
    #        primaria del corpo (logging best-effort).
    def test_end_failure_does_not_mask_body_error(self):
        conn, cursor = _mock_connection(start_row=(7, "uuid-3", True))
        # start: execute ok (fetchone usa start_row); end: execute solleva DatabaseError.
        cursor.execute.side_effect = [None, DatabaseError("db giù")]
        with patch(_CONN, conn):
            # Deve propagare la ServiceError del corpo, NON la DatabaseError del finally.
            with self.assertRaises(ServiceError):
                with registered_job("job:x", processo_codice=_PROCESSO, lock_key="job:x"):
                    raise ServiceError(code="E_BOOM", message="rotto", detail="dett")


class RegisteredJobAttoreTests(TestCase):
    # ⭐ Scopo: l'attore (`processo_codice`) e l'utente tecnico arrivano a
    #    `fn_job_run_start` nelle posizioni giuste. E' il pezzo che rende il
    #    presidio `dbops.vw_run_senza_attore` capace di svuotarsi.
    def test_attore_e_utente_arrivano_alla_funzione(self):
        conn, cursor = _mock_connection(start_row=(7, "uuid-7", True))
        with patch(_CONN, conn):
            with registered_job(
                "run_fatturazione_batch:immediata",
                processo_codice="run_fatturazione_batch",
                origine=ORIGINE_CRON,
                auth_user_id=99,
            ):
                pass

        start_call = next(c for c in cursor.execute.call_args_list
                          if "fn_job_run_start" in c.args[0])
        params = start_call.args[1]
        # jobname, origine, stepname, lock_key, agent_host, processo, auth_user
        self.assertEqual(len(params), 7)
        self.assertEqual(params[5], "run_fatturazione_batch")
        self.assertEqual(params[6], 99)
        # ⛔ E l'attore NON e' il jobname: qui differiscono di proposito, perche'
        #    il jobname porta la corsia. Se un giorno il BB "aiutasse" derivando
        #    il codice dal nome, questa riga lo prenderebbe.
        self.assertNotEqual(params[0], params[5])

    # ⛔ Scopo: il vincolo e' nella FIRMA, non in una convenzione. Un job che
    #    dimentica di dire chi e' non gira: non si registra in silenzio.
    def test_senza_attore_non_si_chiama(self):
        with self.assertRaises(TypeError):
            registered_job("job:senza-attore")  # type: ignore[call-arg]
