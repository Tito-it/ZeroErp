# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `CodaLavoriRepository.summary_per_job_type` sul database vero — la
#        terza sede che riassume le corse di un job, nella stessa forma delle
#        due di `MaintenanceRepository`: `in_corso` e `ultima_conclusa` con
#        data ed esito INSIEME.
# Note: ⛔ Perche' esiste (2026-09-14). Fino a quel giorno `last_ok` era
#        `stato = 'FATTO'` sulla riga piu' recente: un lavoro IN_CORSO usciva
#        «Errore» nel pannello degli esiti, e un ANNULLATO pure. E' la stessa
#        famiglia della cucitura sul giornale dei run (test 6 di
#        `test_job_liveness_due_chiavi`): un esito letto da una riga che un
#        esito non ce l'ha. Il caso si COSTRUISCE e si ritira: nessun test che
#        confronti la popolazione di oggi.
#        ⚠️ Le righe si scrivono direttamente sulla tabella con `run_as =
#        SISTEMA` (scope NULL, per il CHECK) e una competenza IMPOSSIBILE
#        (2099), cosi' il filtro isola le righe del test da quelle vere anche
#        se il rollback non arrivasse.
# ------------------------------------------------------------

"""Indice test previsti (su DB provvisto, `ZEROERP_TEST_DB_E2E=1`).

1. test_un_lavoro_in_corso_non_e_un_esito_e_la_conclusa_porta_la_sua_data
2. test_un_lavoro_annullato_non_e_ne_in_corso_ne_concluso
"""

from __future__ import annotations

from datetime import date
from unittest import TestCase

from django.db import connection, transaction

from apps.core.services.coda_lavori.repository import CodaLavoriRepository
from apps.core.tests.db_e2e import apri_contesto_operatore, richiedi_db_provvisto

# Un tipo a catalogo (FK dura): quello del giro di fatturazione dall'app.
_JOB_TYPE = "FATTURAZIONE_GIRO"
# Una competenza che nessun lavoro vero puo' avere.
_COMPETENZA = date(2099, 1, 1)


class SummaryPerJobTypeSulDatabaseTests(TestCase):
    """La forma delle corse, contro il database vero (in transazione ritirata)."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # Scopo: scrive una riga della coda nello stato dato, con la competenza del
    #        test; torna id e `started_at` (ISO), che e' la data che le sedi
    #        devono restituire per una conclusa.
    def _scrivi(self, cur, stato: str, *, started: str, ended: str | None) -> tuple[int, str]:
        # ⛔ Come SUPER ADMIN (dal blocco 5b la coda e' sotto RLS: una riga
        #    SISTEMA la scrive e la legge solo lui o il drenatore). `SET LOCAL`:
        #    vale per la transazione del test, e ripeterlo e' innocuo.
        apri_contesto_operatore(cur, super_admin=True)
        cur.execute(
            """
            INSERT INTO dbops.coda_lavori
                   (job_type, payload, run_as, scope, origine, stato, started_at, ended_at)
            VALUES (%s, jsonb_build_object('competenza_mese', %s), 'SISTEMA', NULL,
                    'COMMAND', %s, %s::timestamptz, %s::timestamptz)
            RETURNING id, started_at
            """,
            [_JOB_TYPE, _COMPETENZA.isoformat(), stato, started, ended],
        )
        riga = cur.fetchone()
        assert riga is not None
        return int(riga[0]), riga[1].isoformat()

    def _riassunto(self) -> dict:
        righe = CodaLavoriRepository().summary_per_job_type(
            job_types=[_JOB_TYPE], competenza_mese=_COMPETENZA,
        )
        self.assertEqual(len(righe), 1, "la competenza del test non isola le righe")
        return righe[0]

    # 1. ⛔ Un FATTO vecchio, poi un IN_CORSO piu' recente: la riga dice
    #    «in corso» e l'ultima conclusa e' il FATTO — con la SUA data.
    def test_un_lavoro_in_corso_non_e_un_esito_e_la_conclusa_porta_la_sua_data(self) -> None:
        with transaction.atomic():
            with connection.cursor() as cur:
                _id_fatto, avvio_fatto = self._scrivi(
                    cur, "FATTO",
                    started="2099-01-10 07:30:00+00", ended="2099-01-10 07:31:00+00",
                )
                _id_vivo, avvio_vivo = self._scrivi(
                    cur, "IN_CORSO", started="2099-01-10 09:47:00+00", ended=None,
                )
            r = self._riassunto()
            self.assertEqual(r["total_runs"], 2)
            self.assertEqual((r["ok_count"], r["fail_count"]), (1, 0))
            self.assertTrue(r["in_corso"], "il lavoro vivo non e' stato visto")
            conclusa = r["ultima_conclusa"]
            self.assertIsNotNone(conclusa)
            self.assertIs(conclusa["ok"], True)
            # ⛔ La cucitura: l'esito del FATTO con la data dell'IN_CORSO.
            self.assertEqual(conclusa["started_at"], avvio_fatto)
            self.assertNotEqual(conclusa["started_at"], avvio_vivo)
            transaction.set_rollback(True)

    # 2. ⚠️ ANNULLATO e' un lavoro che non ha girato: ne' in corso ne'
    #    concluso. Con un ERRORE prima, l'ultima conclusa e' l'ERRORE (ok =
    #    false, con la sua data) e la riga non e' «in corso».
    def test_un_lavoro_annullato_non_e_ne_in_corso_ne_concluso(self) -> None:
        with transaction.atomic():
            with connection.cursor() as cur:
                _id_err, avvio_err = self._scrivi(
                    cur, "ERRORE",
                    started="2099-01-11 07:30:00+00", ended="2099-01-11 07:31:00+00",
                )
                self._scrivi(cur, "ANNULLATO", started="2099-01-11 09:00:00+00", ended=None)
            r = self._riassunto()
            self.assertEqual(r["total_runs"], 2)
            self.assertFalse(r["in_corso"])
            conclusa = r["ultima_conclusa"]
            self.assertIsNotNone(conclusa)
            self.assertIs(conclusa["ok"], False)
            self.assertEqual(conclusa["started_at"], avvio_err)
            transaction.set_rollback(True)
