# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il rollback automatico dello step lo decide il DB
#        (`VenditePipelineRepository.is_rollback_step_automatico` →
#        `vendite.fn_check_rollback_step_automatico`), sul DB vero: il binding
#        per nome degli argomenti, la colonna `auto_step_rollback` della
#        pipeline e il task `distruttivo` del registro non li vede nessun mock.
#        R-DB-I3, passo 3n (brief-db-porte-aperte-dalla-sola-guc §4.8), dopo
#        D-I.4 a (Tid, 2026-11-24): il flag e' della corsia, non della richiesta.
# Note: opt-in `ZEROERP_TEST_DB_E2E=1`; ogni test scrive in una transazione
#       annullata. ⭐ I casi si COSTRUISCONO: due task di prova nel registro
#       (uno innocuo, uno distruttivo) e il rollback dello step scritto dal
#       test. Il seed non ne sa produrre nessuno: nessuna pipeline ha un
#       rollback. La riga di pipeline scelta e' l'input del test, non la regola:
#       la risoluzione la fa la funzione DB, come nel runner.
#
# Indice test:
#   1) test_corsia_accesa_e_task_innocuo_parte
#        colonna accesa, rollback con un task registrato non distruttivo: True
#   2) test_corsia_spenta_non_parte
#        lo stesso rollback con la colonna spenta: False
#   3) test_task_distruttivo_non_parte
#        il caso distruttivo: colonna accesa, un task distruttivo nel rollback
#        (anche accanto a uno innocuo): False
#   4) test_task_sconosciuto_non_parte
#        un task che il registro non conosce: False (fail-closed)
#   5) test_la_chiave_nel_meta_e_rifiutata
#        `meta.auto_step_rollback` non e' piu' una sede: il CHECK la rifiuta
#   6) test_step_senza_pipeline_e_spento
#        uno step che nessuna pipeline della corsia conosce: False, non errore
# ------------------------------------------------------------

from __future__ import annotations

import json
import unittest
import uuid

from django.db import IntegrityError, connection, transaction

from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.vendite.db.pipeline_repository import VenditePipelineRepository


class RollbackStepAutomaticoDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT r.pipeline_id, fp.tipo_lotto, fp.stato_doc_fiscale_id
                FROM vendite.fatturazione_pipeline fp
                CROSS JOIN LATERAL vendite.fn_resolve_fatturazione_pipeline_step(
                    p_tipo_lotto => fp.tipo_lotto,
                    p_stato_doc_fiscale_id => fp.stato_doc_fiscale_id,
                    p_rollback => true
                ) AS r
                WHERE fp.attivo AND fp.utility_id IS NULL
                  AND fp.tipo_doc_fiscale_id IS NULL
                ORDER BY fp.id
                LIMIT 1
                """
            )
            row = cur.fetchone()
            if row is None:
                self.skipTest("nessuna pipeline di fallback attiva sul DB")
            self.pipeline_id, self.tipo_lotto, self.stato_id = row

            # I due task di prova, nel dominio che la funzione legge.
            suffisso = uuid.uuid4().hex[:8]
            self.task_innocuo = f"test_rb_innocuo_{suffisso}"
            self.task_distruttivo = f"test_rb_distruttivo_{suffisso}"
            cur.execute(
                """
                INSERT INTO dbops.pipeline_task_registry
                    (dominio_id, task_code, descrizione, attivo, distruttivo)
                SELECT d.id, t.code, 'task di prova (test BE)', true, t.distruttivo
                FROM dbops.domini_task d
                CROSS JOIN (VALUES (%s, false), (%s, true)) AS t(code, distruttivo)
                WHERE d.codice = 'FATTURAZIONE'
                """,
                [self.task_innocuo, self.task_distruttivo],
            )
            self.assertEqual(cur.rowcount, 2, "dominio FATTURAZIONE assente")
        self.repo = VenditePipelineRepository()

    def _imposta(self, *, accesa: bool, tasks: list[str]) -> None:
        rollback = json.dumps([{"task": t, "params": {}} for t in tasks])
        with connection.cursor() as cur:
            cur.execute(
                "UPDATE vendite.fatturazione_pipeline "
                "SET auto_step_rollback = %s, rollback = %s::jsonb WHERE id = %s",
                [accesa, rollback, self.pipeline_id],
            )

    def _decisione(self, stato_id: int | None = None) -> bool:
        return self.repo.is_rollback_step_automatico(
            self.stato_id if stato_id is None else stato_id,
            tipo_lotto=self.tipo_lotto,
            utility_id=None,
            tipo_doc_fiscale_id=None,
        )

    # 1) La corsia accesa e un task innocuo: il rollback parte da solo.
    def test_corsia_accesa_e_task_innocuo_parte(self) -> None:
        self._imposta(accesa=True, tasks=[self.task_innocuo])
        self.assertIs(self._decisione(), True)

    # 2) Lo stesso rollback, la corsia spenta: no.
    def test_corsia_spenta_non_parte(self) -> None:
        self._imposta(accesa=False, tasks=[self.task_innocuo])
        self.assertIs(self._decisione(), False)

    # 3) Il caso distruttivo: basta un task che cancella dati, anche accanto a
    #    uno innocuo, perche' il rollback non parta da solo.
    def test_task_distruttivo_non_parte(self) -> None:
        for tasks in (
            [self.task_distruttivo],
            [self.task_innocuo, self.task_distruttivo],
        ):
            with self.subTest(tasks=tasks):
                self._imposta(accesa=True, tasks=tasks)
                self.assertIs(self._decisione(), False)

    # 4) Un task che il registro non conosce: fail-closed.
    def test_task_sconosciuto_non_parte(self) -> None:
        self._imposta(accesa=True, tasks=[f"{self.task_innocuo}_ignoto"])
        self.assertIs(self._decisione(), False)

    # 5) La chiave nel `meta` non accende piu' niente perche' non ci puo'
    #    stare: un nome scritto storto non spegne in silenzio, la sede e' una.
    def test_la_chiave_nel_meta_e_rifiutata(self) -> None:
        with self.assertRaises(IntegrityError):
            with transaction.atomic(), connection.cursor() as cur:
                cur.execute(
                    "UPDATE vendite.fatturazione_pipeline "
                    "SET meta = COALESCE(meta, '{}'::jsonb) "
                    "|| '{\"auto_step_rollback\": true}'::jsonb WHERE id = %s",
                    [self.pipeline_id],
                )

    # 6) Uno step che la corsia non conosce: spento, senza errore.
    def test_step_senza_pipeline_e_spento(self) -> None:
        with connection.cursor() as cur:
            cur.execute("SELECT COALESCE(MAX(id), 0) + 1000 FROM config.stati_doc_fiscale")
            row = cur.fetchone()
        assert row is not None
        self.assertIs(self._decisione(int(row[0])), False)
