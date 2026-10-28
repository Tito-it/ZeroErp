# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: «Attiva» del contratto su un contratto VINCOLANTE sovrapposto, dal
#        service vero al DATABASE VERO (2026-10-19, collaudo di Tid): la
#        capability del dettaglio porta l'azione spenta col motivo che nomina il
#        contratto in conflitto, e `emetti` riceve il rifiuto del guard col suo
#        codice. Il backend non ha piu' la sua copia Python della regola.
# Note: ⚠️ Il mondo si COSTRUISCE (emittente e operatore, un cliente, un listino
#       della sua utility), in transazione ANNULLATA. Periodi nel 2091, su un
#       cliente nuovo: nessun contratto vero li tocca. Opt-in
#       `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) ContrattoAttivaSovrappostoDbTests.test_attiva_spento_col_motivo_e_rifiuto_dal_db
"""
from __future__ import annotations

import unittest
from typing import Any

from django.db import connection, transaction

from apps.core.db._helpers import row_to_dict
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.vendite.services.contratti_service import ContrattiService

_REASON_KEY = "vendite.contratti.azione_reason.contratto_sovrapposto"


class ContrattoAttivaSovrappostoDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto("script.fn_check_contratto_sovrapposto(bigint,bigint,integer,character varying,date,date)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore()")
            mondo = row_to_dict(cur)
            assert mondo is not None
            cur.execute("SELECT script.fn_pgtap_set_contesto_operatore(%s)", [mondo["auth_user_id"]])
            # «Attiva» chiede `emetti_contratto` dalla riga del passaggio, e la
            # capability la nasconde a chi non ce l'ha (§11.6).
            cur.execute(
                "SELECT dbops.fn_pgtap_concedi_azione(%s, 'emetti_contratto')", [mondo["auth_user_id"]],
            )
            cur.execute("SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('attiva sovrapposto')")
            cliente = row_to_dict(cur)
            assert cliente is not None
            cur.execute(
                "SELECT listino_id FROM dbops.fn_pgtap_crea_listino(%s, 'attiva sovrapposto')",
                [cliente["utility_id"]],
            )
            listino_id = cur.fetchone()[0]
        self.cliente: dict[str, Any] = cliente
        self.emittente_fiscale_id = mondo["emittente_fiscale_id"]
        self.listino_id = listino_id

    def _contratto(self, dal: str, al: str) -> int:
        c = self.cliente
        return int(ContrattiService().create_contratto({
            "billing_account_id": c["billing_account_id"],
            "istanza_utility_id": c["istanza_utility_id"],
            "utility_id": c["utility_id"],
            "emittente_fiscale_id": self.emittente_fiscale_id,
            "listino_id": self.listino_id,
            "valido_dal": dal,
            "valido_al": al,
        })["id"])

    @staticmethod
    def _attiva(dettaglio: dict[str, Any]) -> dict[str, Any]:
        azioni = dettaglio["capabilities"]["available_actions"]
        trovate = [a for a in azioni if a.get("target_state") == "ATTIVO"]
        assert trovate, f"nessuna azione verso ATTIVO: {azioni}"
        return trovate[0]

    def test_attiva_spento_col_motivo_e_rifiuto_dal_db(self) -> None:
        servizio = ContrattiService()
        primo = self._contratto("2091-01-01", "2091-12-31")
        attivo = servizio.emetti(primo)
        self.assertEqual("ATTIVO", attivo["stato_codice_interno"])

        sovrapposto = self._contratto("2091-06-01", "2092-05-31")
        azione = self._attiva(servizio.get_contratto(sovrapposto))
        self.assertFalse(azione["enabled"])
        self.assertEqual(_REASON_KEY, azione["reason_key"])

        # In un savepoint: il rifiuto interrompe la transazione del test.
        with self.assertRaises(ServiceError) as ctx, transaction.atomic():
            servizio.emetti(sovrapposto)
        self.assertEqual("E_CONTRATTO_OVERLAP_ESISTENTE", ctx.exception.code)
        self.assertIn(attivo["numero"], ctx.exception.message or "")

        # Un periodo libero non e' sovrapposto: «Attiva» acceso.
        libero = self._contratto("2093-01-01", "2093-12-31")
        self.assertTrue(self._attiva(servizio.get_contratto(libero))["enabled"])
