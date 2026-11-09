# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del building block registered_job (registrazione run-level job headless).
# Indice test:
#   1) start acquired → corpo eseguito, fn_job_run_end chiamato con ok=True + meta
#   2) lock occupato (acquired=False) → corpo vede acquired False, NIENTE fn_job_run_end
#   3) eccezione nel corpo → fn_job_run_end ok=False + error_code/detail, eccezione rilanciata
#   4) ⭐ l'ATTORE arriva a fn_job_run_start — e non si deriva dal job_name
#   5) ⛔ senza attore il BB non si chiama: TypeError, non un run anonimo
#   6) ⭐ l'AMBIENTE vince sugli argomenti: origine e attore di «Esegui ora»
#   7) ambiente assente → valgono gli argomenti (i sei command non cambiano)
#   8) ⛔ origine ignota nell'ambiente → solleva PRIMA di aprire il run
#   9) ⛔ id non numerico, vuoto o <= 0 → solleva, nessun attore di ripiego
#  10) ⭐ errore del database → SQLSTATE al nono argomento di fn_job_run_end
#  11) ⭐ P0001 del database → error_code e' il codice E_, non InternalError
#  12) ⭐ ServiceError tradotto da un errore DB → codice del backend + SQLSTATE
#      dal fondo della catena
#  13) errore non del database (o solo per __context__) → SQLSTATE NULL
#  14) errore del driver senza SQLSTATE (lato client) → nessuno SQLSTATE inventato
#  15) chiudi_se_elementi_non_completati: nessun elemento → niente
#  16) ⭐ elementi falliti → messaggio della corsa, ServiceError col codice D9
#  17) dentro registered_job → corsa rossa con E_JOB_ELEMENTI_NON_COMPLETATI e meta
# ------------------------------------------------------------

from __future__ import annotations

import json
import os
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.db import DatabaseError

from apps.core.services.job_run import (
    E_JOB_ELEMENTI_NON_COMPLETATI,
    ENV_JOB_AUTH_USER_ID,
    JobRunHandle,
    chiudi_se_elementi_non_completati,
    ENV_JOB_ORIGINE,
    ORIGINE_COMMAND,
    ORIGINE_CRON,
    esito_errore,
    registered_job,
)
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
    #    `fn_job_run_start` nelle posizioni giuste: e' cio' che lega una corsa
    #    del giornale al suo processo, che il CHECK
    #    `chk_job_run_log_processo_dichiarato` pretende. (Il presidio
    #    `dbops.vw_run_senza_attore` e' ritirato: D42 di brief-db-revisione-dbops.)
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


# Scopo: i parametri con cui e' stata chiamata `fn_job_run_start`
#        (jobname, origine, stepname, lock_key, agent_host, processo, auth_user).
def _params_start(cursor):
    call = next(c for c in cursor.execute.call_args_list if "fn_job_run_start" in c.args[0])
    return call.args[1]


class RegisteredJobAmbienteTests(TestCase):
    """L'origine e l'attore letti dall'ambiente — il canale di «Esegui ora»."""

    # 6. ⭐ Le due variabili VINCONO: il command dice CRON per abitudine,
    #    l'ambiente dice che questa corsa l'ha chiesta una persona.
    def test_l_ambiente_vince_sugli_argomenti(self):
        conn, cursor = _mock_connection(start_row=(1, "uuid-1", True))
        ambiente = {ENV_JOB_ORIGINE: ORIGINE_COMMAND, ENV_JOB_AUTH_USER_ID: "42"}
        with patch(_CONN, conn), patch.dict("os.environ", ambiente):
            with registered_job(
                "digest_presidi:settimanale", processo_codice="digest_presidi",
                origine=ORIGINE_CRON, auth_user_id=None,
            ):
                pass
        params = _params_start(cursor)
        self.assertEqual(params[1], ORIGINE_COMMAND)
        self.assertEqual(params[6], 42)

    # 7. Senza le variabili non cambia niente: e' il percorso dei sei command
    #    sotto timer, e deve restare quello di prima.
    def test_senza_ambiente_valgono_gli_argomenti(self):
        conn, cursor = _mock_connection(start_row=(1, "uuid-1", True))
        pulito = {k: v for k, v in os.environ.items()
                  if k not in (ENV_JOB_ORIGINE, ENV_JOB_AUTH_USER_ID)}
        with patch(_CONN, conn), patch.dict("os.environ", pulito, clear=True):
            with registered_job(
                "job:x", processo_codice=_PROCESSO,
                origine=ORIGINE_CRON, auth_user_id=7,
            ):
                pass
        params = _params_start(cursor)
        self.assertEqual(params[1], ORIGINE_CRON)
        self.assertEqual(params[6], 7)

    # 8. ⛔ Un'origine fuori dal CHECK non ripiega su CRON: solleva, e lo fa
    #    PRIMA di toccare il database — nessuna riga aperta con l'attore
    #    sbagliato. La stringa vuota e' un segnaposto mai riempito, non un'assenza.
    def test_origine_ignota_solleva_prima_del_run(self):
        for valore in ("MANUALE", "", "cron"):
            with self.subTest(valore=valore):
                conn, cursor = _mock_connection(start_row=(1, "uuid-1", True))
                with patch(_CONN, conn), patch.dict("os.environ", {ENV_JOB_ORIGINE: valore}):
                    with self.assertRaises(ValueError):
                        with registered_job("job:x", processo_codice=_PROCESSO):
                            self.fail("il corpo non deve partire")
                cursor.execute.assert_not_called()

    # 9. ⛔ Idem per l'attore: non numerico, vuoto o non positivo.
    def test_attore_invalido_solleva(self):
        for valore in ("abc", "", "0", "-3", "4.5"):
            with self.subTest(valore=valore):
                conn, cursor = _mock_connection(start_row=(1, "uuid-1", True))
                ambiente = {ENV_JOB_ORIGINE: ORIGINE_COMMAND, ENV_JOB_AUTH_USER_ID: valore}
                with patch(_CONN, conn), patch.dict("os.environ", ambiente):
                    with self.assertRaises(ValueError):
                        with registered_job("job:x", processo_codice=_PROCESSO):
                            self.fail("il corpo non deve partire")
                cursor.execute.assert_not_called()


# Scopo: un errore del DRIVER finto, con la forma che psycopg 3 espone:
#        `sqlstate` e `diag.constraint_name`.
class _ErroreDriver(Exception):
    def __init__(self, sqlstate: str | None, constraint_name: str | None = None) -> None:
        super().__init__(f"driver {sqlstate}")
        self.sqlstate = sqlstate
        self.diag = SimpleNamespace(constraint_name=constraint_name)


# Scopo: un errore Django che avvolge quello del driver, come fa
#        `DatabaseErrorWrapper` (`raise dj_exc from driver_exc`).
def _errore_django(driver: BaseException) -> DatabaseError:
    try:
        raise DatabaseError(str(driver)) from driver
    except DatabaseError as exc:
        return exc


# Scopo: i parametri con cui e' stata chiamata `fn_job_run_end`.
def _params_end(cursor):
    call = next(c for c in cursor.execute.call_args_list if "fn_job_run_end" in c.args[0])
    return call.args[1]


class RegisteredJobErroreDbTests(TestCase):
    """brief-db-presidio-job-run-a-chi-tocca §4.2: SQLSTATE e codice E_."""

    def _corsa_che_solleva(self, exc: BaseException):
        conn, cursor = _mock_connection(start_row=(5, "uuid-5", True))
        with patch(_CONN, conn):
            with self.assertRaises(type(exc)):
                with registered_job("job:x", processo_codice=_PROCESSO):
                    raise exc
        return _params_end(cursor)

    # 10. ⭐ Un disco pieno dentro un command: lo SQLSTATE arriva al nono
    #     argomento, ed e' quello che la vista legge per dire AMBIENTE.
    def test_errore_db_passa_lo_sqlstate(self):
        params = self._corsa_che_solleva(_errore_django(_ErroreDriver("53100")))
        self.assertEqual(len(params), 9)
        self.assertEqual(params[8], "53100")
        self.assertEqual(params[4], "DatabaseError")

    # 11. ⭐ Un errore di dominio sollevato dal database: il codice E_ va in
    #     error_code, cosi' config.codici_errore ne vede la causa.
    def test_p0001_scrive_il_codice_di_dominio(self):
        driver = _ErroreDriver("P0001", constraint_name="E_STATISTICHE_MANCANTI")
        params = self._corsa_che_solleva(_errore_django(driver))
        self.assertEqual(params[4], "E_STATISTICHE_MANCANTI")
        self.assertEqual(params[8], "P0001")

    # 12. ⭐ La strada piu' comune: un service traduce l'errore DB in un
    #     ServiceError. Il codice resta quello del backend; lo SQLSTATE si
    #     prende dal fondo della catena, non si perde al primo anello.
    def test_service_error_tradotto_tiene_lo_sqlstate(self):
        try:
            raise ServiceError(code="E_BOOM", message="rotto") from _errore_django(
                _ErroreDriver("08006"),
            )
        except ServiceError as exc:
            tradotto = exc
        params = self._corsa_che_solleva(tradotto)
        self.assertEqual(params[4], "E_BOOM")
        self.assertEqual(params[8], "08006")

    # 13. Niente database nella catena delle cause ESPLICITE → SQLSTATE NULL.
    #     ⚠️ Un errore DB solo come `__context__` (nato mentre si gestiva
    #     l'altro) non e' la causa, e non presta il suo SQLSTATE.
    def test_errore_non_db_non_ha_sqlstate(self):
        self.assertEqual(esito_errore(ValueError("x")), ("ValueError", None))
        try:
            try:
                raise _errore_django(_ErroreDriver("53100"))
            except DatabaseError:
                raise RuntimeError("altro") from None
        except RuntimeError as exc:
            self.assertEqual(esito_errore(exc), ("RuntimeError", None))

    # 14. Un errore del driver lato client (la connessione non si apre) non
    #     porta SQLSTATE: resta NULL, non se ne inventa uno.
    def test_errore_lato_client_senza_sqlstate(self):
        self.assertEqual(
            esito_errore(_errore_django(_ErroreDriver(None))), ("DatabaseError", None),
        )


class ChiudiSeElementiNonCompletatiTests(TestCase):
    """D9 di brief-db-presidio-job-run-a-chi-tocca: la corsa che perde elementi
    senza un registro loro chiude rossa."""

    # 15. Nessun elemento fallito: la corsa resta com'e', niente messaggio.
    def test_senza_elementi_non_fa_niente(self):
        job = JobRunHandle(run_id=1, run_uuid="u", acquired=True)
        chiudi_se_elementi_non_completati(job, [], cosa="aziende non accodate")
        self.assertIsNone(job.message)

    # 16. ⭐ Elementi falliti: il messaggio della corsa dice quanti (e non
    #     cancella quello che c'era), il dettaglio li nomina.
    def test_con_elementi_solleva_col_codice(self):
        job = JobRunHandle(run_id=1, run_uuid="u", acquired=True)
        job.set_message("accodati 3")
        with self.assertRaises(ServiceError) as ctx:
            chiudi_se_elementi_non_completati(
                job, ["ACME", "BETA"], cosa="aziende non accodate",
            )
        self.assertEqual(ctx.exception.code, E_JOB_ELEMENTI_NON_COMPLETATI)
        self.assertEqual(job.message, "accodati 3; aziende non accodate: 2")
        self.assertIn("ACME, BETA", ctx.exception.detail or "")

    # 17. Dentro `registered_job`: corsa chiusa ok=false col codice, e il meta
    #     scritto prima arriva al giornale insieme al rosso.
    def test_dentro_la_corsa_chiude_rossa_col_meta(self):
        conn, cursor = _mock_connection(start_row=(9, "uuid-9", True))
        with patch(_CONN, conn):
            with self.assertRaises(ServiceError):
                with registered_job("job:x", processo_codice=_PROCESSO) as job:
                    job.set_meta({"falliti": [{"emittente_codice": "ACME"}]})
                    chiudi_se_elementi_non_completati(
                        job, ["ACME"], cosa="aziende non accodate",
                    )
        params = _params_end(cursor)
        self.assertIs(params[1], False)
        self.assertEqual(params[2], "aziende non accodate: 1")
        self.assertEqual(params[4], E_JOB_ELEMENTI_NON_COMPLETATI)
        self.assertEqual(json.loads(params[6]), {"falliti": [{"emittente_codice": "ACME"}]})
        self.assertIsNone(params[8])
