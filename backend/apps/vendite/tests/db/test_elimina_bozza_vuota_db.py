# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: L'eliminazione della bozza DAL SERVICE sul DATABASE PROVVISTO
#        (brief-db-sorgente-documento-e-riga §8.21 BE-Z.2-a): «si cancella solo
#        la bozza vuota» sta solo nel guard DB
#        (`vendite.trgfn_doc_guard_delete_solo_bozza`), e il service non la
#        ripete. Qui si prova la giuntura che i test del service (mock) non
#        vedono: il rifiuto VERO del guard arriva al client col suo codice e la
#        sua classe (409) attraverso il traduttore del dominio, la bozza vuota
#        si cancella, il DELETE che non tocca niente e' il 404.
# Note: ⚠️ Le REGOLE del guard (stato iniziale dal vocabolario, che cosa conta
#       come contenuto per ogni documento) le prova il pgTAP
#       `vendite/test-delete-testate-solo-bozza-vuota-v1`. Qui due documenti
#       con due traduttori dello stesso BB (`make_db_errors_translator`):
#       il preventivo (guard dal giro Z.2) e l'ordine (dal giro T.4).
#       Il mondo lo costruiscono le fixture pgTAP, che aprono il contesto
#       sull'operatore; transazione SEMPRE annullata, ogni rifiuto atteso in
#       un SAVEPOINT. Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) EliminaBozzaVuotaDbTests.test_preventivo_fuori_bozza — E_DELETE_DOC_NON_BOZZA, 409
2) EliminaBozzaVuotaDbTests.test_preventivo_bozza_con_righe — E_DELETE_DOC_CON_RIGHE, 409
3) EliminaBozzaVuotaDbTests.test_preventivo_bozza_vuota_si_elimina
4) EliminaBozzaVuotaDbTests.test_preventivo_che_non_ce_e_404 — E_PREV_NOT_FOUND
5) EliminaBozzaVuotaDbTests.test_ordine_bozza_con_righe — E_DELETE_DOC_CON_RIGHE, 409
6) EliminaBozzaVuotaDbTests.test_ordine_bozza_vuota_si_elimina
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.core.services.error_policies_generated import CLASSE_PER_CODICE
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.vendite.services import ordini_service, preventivi_service

# Un id che nessuna sequenza raggiunge: il documento che non c'e'.
_ID_INESISTENTE = 9_000_000_000_000


class EliminaBozzaVuotaDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        # La sonda sullo stato iniziale dal vocabolario (giro Z.2): il guard
        # sul preventivo nasce nello stesso giro.
        richiedi_db_provvisto("script.fn_doc_stato_iniziale_id(regclass)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)

    def _uno(self, sql: str) -> int:
        with connection.cursor() as cur:
            cur.execute(sql)
            return int(cur.fetchone()[0])

    def _esiste(self, tabella: str, documento_id: int) -> bool:
        with connection.cursor() as cur:
            cur.execute(f"SELECT EXISTS (SELECT 1 FROM {tabella} WHERE id = %s)", [documento_id])  # tabella letterale dei test, mai input
            return bool(cur.fetchone()[0])

    # Il rifiuto del guard: il codice del DB, la sua classe, il documento resta.
    def _rifiutato(self, elimina, documento_id: int, *, codice: str, tabella: str) -> None:
        with self.assertRaises(ServiceError) as cm, transaction.atomic():
            elimina(documento_id)
        self.assertEqual(cm.exception.code, codice)
        self.assertEqual(CLASSE_PER_CODICE[codice], "CONFLITTO_STATO")
        self.assertTrue(self._esiste(tabella, documento_id))

    def test_preventivo_fuori_bozza(self) -> None:
        preventivo_id = self._uno(
            "SELECT preventivo_id FROM dbops.fn_pgtap_crea_preventivo_con_righe("
            "'BE elimina fuori bozza', 'EMESSO')",
        )
        self._rifiutato(
            preventivi_service.elimina_preventivo, preventivo_id,
            codice="E_DELETE_DOC_NON_BOZZA", tabella="vendite.preventivi",
        )

    def test_preventivo_bozza_con_righe(self) -> None:
        preventivo_id = self._uno(
            "SELECT preventivo_id FROM dbops.fn_pgtap_crea_preventivo_con_righe("
            "'BE elimina con righe', 'DRAFT')",
        )
        self._rifiutato(
            preventivi_service.elimina_preventivo, preventivo_id,
            codice="E_DELETE_DOC_CON_RIGHE", tabella="vendite.preventivi",
        )

    def test_preventivo_bozza_vuota_si_elimina(self) -> None:
        preventivo_id = self._uno(
            "SELECT preventivo_id FROM dbops.fn_pgtap_crea_preventivo('BE elimina vuota')",
        )
        out = preventivi_service.elimina_preventivo(preventivo_id)
        self.assertEqual(out, {"status": "ok", "preventivo_id": preventivo_id})
        self.assertFalse(self._esiste("vendite.preventivi", preventivo_id))

    def test_preventivo_che_non_ce_e_404(self) -> None:
        with self.assertRaises(ServiceError) as cm:
            preventivi_service.elimina_preventivo(_ID_INESISTENTE)
        self.assertEqual(cm.exception.code, "E_PREV_NOT_FOUND")

    def test_ordine_bozza_con_righe(self) -> None:
        ordine_id = self._uno(
            "SELECT ordine_id FROM dbops.fn_pgtap_crea_ordine_con_righe("
            "'BE elimina con righe', 'DRAFT')",
        )
        self._rifiutato(
            ordini_service.elimina_ordine, ordine_id,
            codice="E_DELETE_DOC_CON_RIGHE", tabella="vendite.ordini",
        )

    def test_ordine_bozza_vuota_si_elimina(self) -> None:
        ordine_id = self._uno("SELECT ordine_id FROM dbops.fn_pgtap_crea_ordine('BE elimina vuota')")
        out = ordini_service.elimina_ordine(ordine_id)
        self.assertEqual(out, {"ordine_id": ordine_id, "deleted": True})
        self.assertFalse(self._esiste("vendite.ordini", ordine_id))
