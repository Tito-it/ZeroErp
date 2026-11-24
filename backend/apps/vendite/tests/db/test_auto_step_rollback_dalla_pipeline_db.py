# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il flag del rollback automatico si legge dalla PIPELINE dello step
#        (`VenditePipelineRepository.is_auto_step_rollback_attivo`), sul DB
#        vero: il binding per nome con `fn_resolve_fatturazione_pipeline_step`
#        e con `vendite.fatturazione_pipeline.meta` non lo vede nessun mock.
#        D-I.4 a (Tid, 2026-11-24, brief-db-porte-aperte-dalla-sola-guc §4.8).
# Note: opt-in `ZEROERP_TEST_DB_E2E=1`; ogni test scrive in una transazione
#       annullata.
#
# Indice test:
#   1) test_legge_il_meta_della_riga_risolta
#        la risposta coincide con il `meta` della riga che la funzione DB
#        risolve per lo step (qualunque sia oggi)
#   2) test_solo_il_booleano_true_accende
#        `true` accende; `false`, il testo `"true"` e la chiave assente no
#   3) test_step_senza_pipeline_e_spento
#        uno step che nessuna pipeline della corsia conosce: False, non errore
# ------------------------------------------------------------

from __future__ import annotations

import unittest

from django.db import connection

from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.vendite.db.pipeline_repository import VenditePipelineRepository


class AutoStepRollbackDallaPipelineDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        # Una riga di fallback attiva qualsiasi: e' l'input del test, non la
        # regola. La risoluzione la fa la funzione DB, come nel runner.
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
        self.repo = VenditePipelineRepository()

    def _flag(self) -> bool:
        return self.repo.is_auto_step_rollback_attivo(
            self.stato_id, tipo_lotto=self.tipo_lotto,
            utility_id=None, tipo_doc_fiscale_id=None,
        )

    def _imposta_meta(self, frammento: str | None) -> None:
        with connection.cursor() as cur:
            if frammento is None:
                cur.execute(
                    "UPDATE vendite.fatturazione_pipeline "
                    "SET meta = meta - 'auto_step_rollback' WHERE id = %s",
                    [self.pipeline_id],
                )
            else:
                cur.execute(
                    "UPDATE vendite.fatturazione_pipeline "
                    "SET meta = jsonb_set(meta, '{auto_step_rollback}', %s::jsonb) "
                    "WHERE id = %s",
                    [frammento, self.pipeline_id],
                )

    # 1) La risposta e' il `meta` della riga risolta, comunque sia oggi.
    def test_legge_il_meta_della_riga_risolta(self) -> None:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT meta -> 'auto_step_rollback' = 'true'::jsonb "
                "FROM vendite.fatturazione_pipeline WHERE id = %s",
                [self.pipeline_id],
            )
            atteso = bool(cur.fetchone()[0])
        self.assertIs(self._flag(), atteso)

    # 2) Solo il booleano JSON `true` accende.
    def test_solo_il_booleano_true_accende(self) -> None:
        for frammento, atteso in (
            ("true", True), ("false", False), ('"true"', False), (None, False),
        ):
            with self.subTest(meta=frammento):
                self._imposta_meta(frammento)
                self.assertIs(self._flag(), atteso)

    # 3) Uno step che la corsia non conosce: spento, senza errore.
    def test_step_senza_pipeline_e_spento(self) -> None:
        with connection.cursor() as cur:
            cur.execute("SELECT COALESCE(MAX(id), 0) + 1000 FROM config.stati_doc_fiscale")
            sconosciuto = int(cur.fetchone()[0])
        self.assertIs(
            self.repo.is_auto_step_rollback_attivo(
                sconosciuto, tipo_lotto=self.tipo_lotto,
                utility_id=None, tipo_doc_fiscale_id=None,
            ),
            False,
        )
