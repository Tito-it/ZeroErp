# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le liste dei due diari tecnici — `maintenance.job_run_log`
#        (`MaintenanceRepository.list_job_runs`) e `dbops.audit_log`
#        (`DbopsRepository.list_audit_logs`) — si ordinano sull'ISTANTE, non
#        sul testo della data.
# Note: ⭐ Perche' esiste. Le due SELECT proiettano la data come `::text` con lo
#        stesso nome della colonna (`started_at::text`, `executed_at::text`), e
#        un nome nudo nell'ORDER BY si risolve PRIMA sulle colonne di output:
#        fino al 2026-11-22 entrambe ordinavano il testo, sotto la collation
#        del database (`it_IT`), e nessun indice serviva l'ordine. Il difetto
#        non da' errore: la lista esce, e sembra in ordine.
#        ⛔ Si prova sul PIANO del database vero (`EXPLAIN`), con l'SQL che il
#        repository manda davvero (catturato con `execute_wrapper`), non con
#        un'asserzione sul testo della query: e' il planner a dire su cosa si
#        ordina. Se rimetti `ORDER BY started_at` il `Sort Key` diventa
#        `((started_at)::text)` e il test va rosso.
# ------------------------------------------------------------

"""Indice test (DB provvisto, `ZEROERP_TEST_DB_E2E=1`).

  1. test_le_corse_si_ordinano_sull_istante
  2. test_l_audit_log_si_ordina_sull_istante
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from typing import Any
from unittest import TestCase

from django.db import connection

from apps.core.db.dbops_repository import DbopsRepository
from apps.core.db.maintenance_repository import MaintenanceRepository
from apps.core.tests.db_e2e import richiedi_db_provvisto


def _chiavi_di_ordinamento(nodo: dict) -> Iterator[str]:
    for chiave in ("Sort Key", "Presorted Key"):
        yield from nodo.get(chiave, [])
    for figlio in nodo.get("Plans", []):
        yield from _chiavi_di_ordinamento(figlio)


class OrdineSullIstanteTests(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # Esegue la lettura del repository catturandone l'SQL, poi ne chiede il
    # piano: le chiavi di ordinamento che il planner usa davvero.
    def _chiavi_del_piano(self, lettura: Callable[[], Any]) -> list[str]:
        catturate: list[tuple[str, Any]] = []

        def cattura(execute, sql, params, many, context):
            catturate.append((sql, params))
            return execute(sql, params, many, context)

        with connection.execute_wrapper(cattura):
            lettura()
        self.assertEqual(len(catturate), 1, "la lettura doveva essere una query sola")
        sql, params = catturate[0]
        with connection.cursor() as cur:
            cur.execute("EXPLAIN (FORMAT JSON) " + sql, params)
            piano = cur.fetchone()[0]
        if isinstance(piano, str):
            piano = json.loads(piano)
        return list(_chiavi_di_ordinamento(piano[0]["Plan"]))

    def _assert_istante(self, chiavi: list[str], colonna: str) -> None:
        # Con un indice che serve l'ordine il piano non ha Sort: va bene.
        for chiave in chiavi:
            with self.subTest(chiave=chiave):
                self.assertNotIn(
                    "::text", chiave,
                    f"si ordina il testo di `{colonna}`, non l'istante",
                )

    # 1. `list_job_runs`.
    def test_le_corse_si_ordinano_sull_istante(self) -> None:
        chiavi = self._chiavi_del_piano(
            lambda: MaintenanceRepository().list_job_runs(limit=50, offset=0),
        )
        self._assert_istante(chiavi, "started_at")

    # 2. `list_audit_logs`, il gemello.
    def test_l_audit_log_si_ordina_sull_istante(self) -> None:
        chiavi = self._chiavi_del_piano(
            lambda: DbopsRepository().list_audit_logs(limit=50, offset=0),
        )
        self._assert_istante(chiavi, "executed_at")
