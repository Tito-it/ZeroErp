# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il building block `transazione_sola_lettura` sul DB VERO: una
#        scrittura dentro il blocco la ferma PostgreSQL con `25006`, e la
#        connessione non si porta dietro la sola lettura dopo il blocco
#        (brief-db-area-funzionale-assistente-ai §5.4 punto 4,
#        brief-be-letture-in-transazione-sola-lettura §4 punti 1 e 3).
#
# ⭐ PERCHE' SUL DB VERO: la garanzia e' di PostgreSQL, non del codice. Un test
#    col cursore finto proverebbe che si scrive `SET TRANSACTION READ ONLY`,
#    non che una scrittura venga fermata.
# ⭐ «NESSUNA RIGA» PER COSTRUZIONE: la riga tentata non puo' entrare in nessun
#    caso (`destinatario` NULL su una colonna NOT NULL) — ma fallisce per
#    motivi diversi, e il test li distingue dal codice: `25006` se la sola
#    lettura c'e'; se manca, un altro (il 2026-09-25, senza sessione, era il
#    `P0001` della guardia di scrittura di `config.email_log`, che scatta
#    prima del NOT NULL). PostgreSQL controlla la sola lettura all'avvio
#    dell'esecutore, prima di qualunque riga, trigger o vincolo. Cosi' un
#    building block rotto fa un test ROSSO, e non una riga vera sul database.
#
# ⚠️ RICHIEDE IL DB VERO, opt-in `ZEROERP_TEST_DB_E2E=1` (accesa in CI).
# ------------------------------------------------------------

"""Indice test (opt-in `ZEROERP_TEST_DB_E2E=1`).

1. test_una_scrittura_nel_blocco_la_ferma_il_db
     e arriva come `E_SCRITTURA_IN_LETTURA`, col `25006` come causa
2. test_nel_blocco_si_legge
3. test_dopo_il_blocco_la_connessione_scrive_di_nuovo
4. test_dopo_un_errore_nel_blocco_la_connessione_scrive_di_nuovo
5. test_dentro_una_transazione_aperta_rifiuta_di_partire
"""

from __future__ import annotations

from unittest import TestCase

from django.db import DatabaseError, connection, transaction

from apps.core.db.sola_lettura import E_SCRITTURA_IN_LETTURA, transazione_sola_lettura
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import richiedi_db_provvisto

_SQLSTATE_SOLA_LETTURA = "25006"  # read_only_sql_transaction

# Una scrittura che non puo' riuscire in nessun caso (`destinatario` e'
# NOT NULL): vedi l'header.
_INSERT_IMPOSSIBILE = "INSERT INTO config.email_log (destinatario) VALUES (NULL)"


# Scopo: lo SQLSTATE dietro l'eccezione che Django rilancia.
def _sqlstate(exc: BaseException) -> str | None:
    return getattr(exc.__cause__, "sqlstate", None)


# Scopo: `on`/`off` — la sola lettura della transazione in cui gira la query.
def _transaction_read_only() -> str:
    with connection.cursor() as cur:
        cur.execute("SHOW transaction_read_only")
        row = cur.fetchone()
    assert row is not None
    return row[0]


class TransazioneSolaLetturaDbTests(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # ⭐ Il BB traduce il `25006` alla sorgente: un `ServiceError`, che nessun
    #    traduttore di errori DB puo' riscrivere col suo ripiego. La causa resta
    #    il `DatabaseError` di PostgreSQL, ed e' quello che prova la garanzia.
    def test_una_scrittura_nel_blocco_la_ferma_il_db(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            with transazione_sola_lettura(chi="test"), connection.cursor() as cur:
                cur.execute(_INSERT_IMPOSSIBILE)
        self.assertEqual(ctx.exception.code, E_SCRITTURA_IN_LETTURA)
        self.assertEqual(ctx.exception.context, {"chi": "test"})
        self.assertIsInstance(ctx.exception.__cause__, DatabaseError)
        self.assertEqual(_sqlstate(ctx.exception.__cause__), _SQLSTATE_SOLA_LETTURA)

    def test_nel_blocco_si_legge(self) -> None:
        with transazione_sola_lettura():
            self.assertEqual(_transaction_read_only(), "on")
            with connection.cursor() as cur:
                cur.execute("SELECT 1")
                self.assertEqual(cur.fetchone(), (1,))

    # ⛔ Il rischio del «per sessione»: con `CONN_MAX_AGE` la connessione passa
    #    alla richiesta dopo, magari una POST.
    def test_dopo_il_blocco_la_connessione_scrive_di_nuovo(self) -> None:
        with transazione_sola_lettura():
            pass
        self.assertEqual(_transaction_read_only(), "off")

    def test_dopo_un_errore_nel_blocco_la_connessione_scrive_di_nuovo(self) -> None:
        with self.assertRaises(ServiceError):
            with transazione_sola_lettura(), connection.cursor() as cur:
                cur.execute(_INSERT_IMPOSSIBILE)
        self.assertEqual(_transaction_read_only(), "off")

    # Dentro una transazione gia' aperta la sola lettura non si puo' piu'
    # impostare: il blocco lo dice, invece di non darla in silenzio.
    def test_dentro_una_transazione_aperta_rifiuta_di_partire(self) -> None:
        with transaction.atomic():
            with self.assertRaises(RuntimeError):
                with transazione_sola_lettura():
                    pass  # pragma: no cover
