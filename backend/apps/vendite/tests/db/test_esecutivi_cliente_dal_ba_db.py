# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il cliente di DDT e ordine sul DATABASE PROVVISTO, dai verbi del
#        service (brief-db-esecutivi-ba-coppia §7, §9.6, §11.5): whitelist del
#        service → repository → trigger. Il backend non deriva piu' niente dal
#        billing account; qui si prova che le copie (destinatario o ruolo,
#        utility) le scriva davvero il DB, e che i rifiuti arrivino col loro
#        codice.
#          · DDT: nasce senza cliente (terzista), riceve il BA in bozza (il
#            destinatario non toccato segue il BA), lo perde (utility via,
#            destinatario resta); un destinatario diverso dal BA e' rifiutato.
#          · Ordine: ruolo e utility dal BA; il BA non cambia dopo la creazione
#            (lock del DB, non piu' una copia Python).
# Note: ⭐ Perche' qui: i test del service mockano il repository, quindi non
#       vedono ne' una colonna mancante nella whitelist RIGIDA del repository
#       (`TESTATA_UPDATE_COLUMNS`) ne' che cosa il trigger faccia della riga.
#       ⚠️ Il mondo si COSTRUISCE (`dbops.fn_pgtap_crea_mondo_cliente`, che apre
#       il contesto operatore; il terzista da `fn_pgtap_crea_soggetto_pg` +
#       `fn_pgtap_crea_soggetto_ruolo`). Transazione SEMPRE annullata; ogni
#       rifiuto atteso sta in un savepoint, perche' un errore DB aborta la
#       transazione intera. Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) EsecutiviClienteDalBaDbTests.test_ddt_senza_cliente_poi_col_ba_poi_senza
2) EsecutiviClienteDalBaDbTests.test_ddt_col_ba_destinatario_dal_db_e_diverso_rifiutato
3) EsecutiviClienteDalBaDbTests.test_ordine_ruolo_e_utility_dal_ba_e_ba_bloccato
"""
from __future__ import annotations

import unittest
from typing import Any

from django.db import connection, transaction

from apps.core.db._helpers import row_to_dict
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.vendite.services import ddt_service, ordini_service


class EsecutiviClienteDalBaDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        # La sonda e' il BB delle copie: senza, il test non ha materia.
        richiedi_db_provvisto(
            "script.fn_cliente_dal_billing_account(bigint,bigint,integer,text,text,uuid)"
        )

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('esecutivi cliente dal ba')")
            mondo = row_to_dict(cur)
            assert mondo is not None
            cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_pg('esecutivi terzista')")
            soggetto = cur.fetchone()
            assert soggetto is not None
            cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_ruolo(%s, 'FO')", [soggetto[0]])
            terzista = cur.fetchone()
            assert terzista is not None
        self.mondo: dict[str, Any] = mondo
        self.terzista: int = terzista[0]

    def _testata(self, tabella: str, colonna_ruolo: str, documento_id: int) -> dict[str, Any]:
        with connection.cursor() as cur:
            cur.execute(
                f"SELECT billing_account_id, utility_id, {colonna_ruolo} AS ruolo "
                f"  FROM vendite.{tabella} WHERE id = %s",
                [documento_id],
            )
            riga = row_to_dict(cur)
        assert riga is not None, f"{tabella} {documento_id} non si rilegge (RLS?)"
        return riga

    def _ddt(self, ddt_id: int) -> dict[str, Any]:
        return self._testata("ddt", "destinatario_soggetto_ruolo_id", ddt_id)

    def test_ddt_senza_cliente_poi_col_ba_poi_senza(self) -> None:
        m = self.mondo
        # D-2: la bolla al terzista nasce senza cliente.
        ddt_id = int(ddt_service.crea_ddt({
            "destinatario_soggetto_ruolo_id": self.terzista,
            "emittente_fiscale_id": m["emittente_fiscale_id"],
        })["id"])
        self.assertEqual(
            self._ddt(ddt_id),
            {"billing_account_id": None, "utility_id": None, "ruolo": self.terzista},
        )
        # In bozza riceve il cliente: il destinatario non toccato segue il BA,
        # la utility la scrive il DB.
        ddt_service.aggiorna_ddt(ddt_id, {"billing_account_id": m["billing_account_id"]})
        self.assertEqual(self._ddt(ddt_id), {
            "billing_account_id": m["billing_account_id"],
            "utility_id": m["utility_id"],
            "ruolo": m["cliente_soggetto_ruolo_id"],
        })
        # Lo perde: la utility se ne va, il destinatario resta.
        ddt_service.aggiorna_ddt(ddt_id, {"billing_account_id": None})
        self.assertEqual(self._ddt(ddt_id), {
            "billing_account_id": None,
            "utility_id": None,
            "ruolo": m["cliente_soggetto_ruolo_id"],
        })

    def test_ddt_col_ba_destinatario_dal_db_e_diverso_rifiutato(self) -> None:
        m = self.mondo
        ddt_id = int(ddt_service.crea_ddt({
            "billing_account_id": m["billing_account_id"],
            "emittente_fiscale_id": m["emittente_fiscale_id"],
        })["id"])
        self.assertEqual(self._ddt(ddt_id), {
            "billing_account_id": m["billing_account_id"],
            "utility_id": m["utility_id"],
            "ruolo": m["cliente_soggetto_ruolo_id"],
        })
        # Col BA, un destinatario diverso dal suo ruolo lo rifiuta il BB.
        with self.assertRaises(ServiceError) as cm, transaction.atomic():
            ddt_service.crea_ddt({
                "billing_account_id": m["billing_account_id"],
                "destinatario_soggetto_ruolo_id": self.terzista,
                "emittente_fiscale_id": m["emittente_fiscale_id"],
            })
        self.assertEqual(cm.exception.code, "E_DOC_CLIENTE_DIVERSO_DA_BA")

    def test_ordine_ruolo_e_utility_dal_ba_e_ba_bloccato(self) -> None:
        m = self.mondo
        ordine_id = int(ordini_service.crea_ordine({
            "billing_account_id": m["billing_account_id"],
            "emittente_fiscale_id": m["emittente_fiscale_id"],
        })["id"])
        self.assertEqual(self._testata("ordini", "soggetto_ruolo_id", ordine_id), {
            "billing_account_id": m["billing_account_id"],
            "utility_id": m["utility_id"],
            "ruolo": m["cliente_soggetto_ruolo_id"],
        })
        # Il form rimanda il BA invariato: passa (il lock confronta i valori).
        ordini_service.aggiorna_ordine(ordine_id, {"billing_account_id": m["billing_account_id"]})
        # Un BA diverso lo rifiuta il lock del DB, col codice dell'ordine.
        # ⛔ Un BA VERO della stessa azienda, non `id + 1`: un id calcolato puo'
        #    non esistere, o essere di un'altra azienda, e allora il rifiuto
        #    dipenderebbe dall'ordine dei trigger e dagli id di oggi. Contesto
        #    aperto: il legame all'azienda lo scrive il trigger z90.
        with connection.cursor() as cur:
            cur.execute(
                "SELECT billing_account_id FROM dbops.fn_pgtap_crea_cliente_ba("
                "  'esecutivi altro cliente', %s)",
                [m["utility_id"]],
            )
            altro = cur.fetchone()
        assert altro is not None
        with self.assertRaises(ServiceError) as cm, transaction.atomic():
            ordini_service.aggiorna_ordine(ordine_id, {"billing_account_id": altro[0]})
        self.assertEqual(cm.exception.code, "E_ORD_CLIENTE_IMMUTABILE")
