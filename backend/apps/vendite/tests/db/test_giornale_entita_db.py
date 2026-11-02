# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La STORIA di un'entita' (lista `vendite.giornale` per lotto/fattura,
#        brief-db-liste-datatable-grezze §3.1) sul DB VERO: le tre letture nate
#        il 2026-09-27 che i test col repository mockato non vedono.
#
# ⭐ CASI COSTRUITI: un'azienda dai builder pgTAP (lo stesso `_Mondo` del
#    presidio del giornale trasversale), il suo lotto e le righe di diario che
#    servono — INFO e WARN ritirate comprese. Tutto in transazione annullata.
# ⚠️ RICHIEDE IL DB VERO, opt-in `ZEROERP_TEST_DB_E2E=1` (accesa in CI), con
#    la connessione dell'applicazione (soggetta alla RLS).
#
# Indice test:
#   1. test_con_le_ritirate_il_totale_e_le_righe_mostrate: `ritirate=true` e
#      «solo problemi» — il totale conta le righe a video, non una INFO
#      ritirata in piu' (pagine finali vuote)
#   2. test_la_storia_dice_di_chi_e_ogni_riga: `entita_display` valorizzato
#   3. test_l_errore_vivo_salta_quello_ritirato: il banner prende l'ERROR
#      VIVO, anche se uno ritirato e' piu' recente
# ------------------------------------------------------------
from __future__ import annotations

from unittest import TestCase

from django.db import connection, transaction

from apps.core.tests.db_e2e import richiedi_db_provvisto, richiedi_ruolo_soggetto_a_rls
from apps.vendite.db.vendite_repository import VenditeRepository
from apps.vendite.services.vendite_service import get_lotto_giornale
from apps.vendite.tests.db.test_giornale_trasversale_perimetro import _Mondo


class GiornaleEntitaDbTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()
        richiedi_ruolo_soggetto_a_rls("vendite.event_log")

    # Scopo: esegue `corpo(mondo)` in una transazione annullata, col lotto del
    #        mondo e, oltre all'ERROR vivo del diario (`_Mondo.scrivi`), tre
    #        righe del log del lotto: INFO viva, INFO ritirata, ERROR ritirato
    #        (il piu' recente di tutti).
    def _con_storia(self, corpo) -> None:
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute("SET CONSTRAINTS ALL DEFERRED")
                mondo = _Mondo(cur, "GE")
                cur.execute("SET CONSTRAINTS ALL IMMEDIATE")
                mondo.scrivi(cur)
                for status, ritirata, secondi_dopo in (("I", False, 1), ("I", True, 2), ("C", True, 3)):
                    cur.execute(
                        "INSERT INTO vendite.fatturazione_lotti_log "
                        "       (lotto_id, messaggio, status, disabilitato, data_ora) "
                        "VALUES (%s, 'e2e storia', %s, %s, "
                        "        clock_timestamp() + make_interval(secs => %s))",
                        [mondo.lotto_id, status, ritirata, secondi_dopo],
                    )
            try:
                corpo(mondo)
            finally:
                transaction.set_rollback(True)

    # 1. Con le ritirate a video e «solo problemi»: righe = ERROR vivo + ERROR
    #    ritirato. Il totale e' quello, e le INFO nascoste sono le due (viva e
    #    ritirata) che il filtro toglie davvero.
    def test_con_le_ritirate_il_totale_e_le_righe_mostrate(self) -> None:
        def corpo(mondo):
            data = get_lotto_giornale(
                lotto_id=mondo.lotto_id, includi_ritirate=True, includi_info=False, limit=200,
            )
            self.assertEqual(len(data["results"]), 2)
            self.assertEqual(data["count"], 2)
            self.assertEqual(data["info_count"], 2)
        self._con_storia(corpo)

    # 2. Ogni riga della Storia porta l'etichetta della sua entita'.
    def test_la_storia_dice_di_chi_e_ogni_riga(self) -> None:
        def corpo(mondo):
            data = get_lotto_giornale(lotto_id=mondo.lotto_id, includi_info=True, limit=200)
            self.assertTrue(data["results"])
            for riga in data["results"]:
                self.assertEqual(riga["entita_display"], f"E2E-GIORNALE-{mondo.sr_id}", riga)
        self._con_storia(corpo)

    # 3. L'ERROR ritirato e' il piu' recente, ma il banner dice quello vivo.
    def test_l_errore_vivo_salta_quello_ritirato(self) -> None:
        def corpo(mondo):
            riga = VenditeRepository().get_giornale_errore_vivo(
                entity_type="LOTTO", entity_id=mondo.lotto_id,
            )
            self.assertIsNotNone(riga)
            self.assertEqual(riga["registro"], "EVENT_LOG")
            self.assertFalse(riga["ritirata"])
        self._con_storia(corpo)
