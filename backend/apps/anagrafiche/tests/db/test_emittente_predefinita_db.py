# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: «Rendi predefinita questa azienda» dal repository VERO sul DB vero
#        (brief-db-revisione-anagrafiche §26.2, 2026-11-27): la riga della
#        predefinita (`billing_account_id` NULL) si SPOSTA sull'emittente, e
#        non si cancella e ricrea, perche' il DB rifiuta la cancellazione di
#        ogni collegamento (`E_BA_COLLEGAMENTO_NON_SI_TOGLIE`, giro 6). Un mock
#        non vede se i trigger del collegamento lasciano passare l'UPDATE.
# Note: Il mondo si COSTRUISCE: un secondo emittente da
#       `dbops.fn_pgtap_crea_emittente_operatore`, poi il SUPER_ADMIN col
#       contesto aperto per ultimo. Transazione SEMPRE annullata.
#       Opt-in `ZEROERP_TEST_DB_E2E=1`.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) EmittentePredefinitaDbTests.test_la_predefinita_si_sposta — la stessa riga, sull'emittente
   nuovo; una seconda volta non cambia niente
2) EmittentePredefinitaDbTests.test_il_collegamento_non_si_toglie — la cancellazione della
   riga e' `E_BA_COLLEGAMENTO_NON_SI_TOGLIE` (per questo il DELETE e' ritirato)
"""
from __future__ import annotations

import unittest

from django.db import DatabaseError, connection, transaction

from apps.anagrafiche.db.emittenti_fiscali_repository import (
    EmittentiFiscaliBillingAccountRepository,
)
from apps.core.services.db_error_fields import structured_db_error_code
from apps.core.tests.db_e2e import (
    apri_super_admin_costruito,
    apri_transazione_annullata,
    richiedi_db_provvisto,
)


class EmittentePredefinitaDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            cur.execute(
                "SELECT soggetto_ruolo_id FROM dbops.fn_pgtap_crea_emittente_operatore()"
            )
            self.emittente = int(cur.fetchone()[0])
            apri_super_admin_costruito(cur, etichetta="predefinita admin")

    @staticmethod
    def _predefinita() -> tuple[int, int] | None:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT id, emittente_soggetto_ruolo_id"
                "  FROM anagrafiche.emittenti_fiscali_billing_account WHERE is_default"
            )
            riga = cur.fetchone()
        return None if riga is None else (int(riga[0]), int(riga[1]))

    def test_la_predefinita_si_sposta(self) -> None:
        prima = self._predefinita()
        repo = EmittentiFiscaliBillingAccountRepository()
        riga_id = repo.imposta_predefinita(self.emittente)
        self.assertEqual((riga_id, self.emittente), self._predefinita())
        if prima is not None:
            self.assertEqual(prima[0], riga_id, "la riga si sposta, non nasce un'altra")
        self.assertEqual(riga_id, repo.imposta_predefinita(self.emittente))
        self.assertEqual((riga_id, self.emittente), self._predefinita())

    def test_il_collegamento_non_si_toglie(self) -> None:
        riga_id = EmittentiFiscaliBillingAccountRepository().imposta_predefinita(self.emittente)
        with self.assertRaises(DatabaseError) as ctx, transaction.atomic(), connection.cursor() as cur:
            cur.execute(
                "DELETE FROM anagrafiche.emittenti_fiscali_billing_account WHERE id = %s",
                [riga_id],
            )
        self.assertEqual("E_BA_COLLEGAMENTO_NON_SI_TOGLIE", structured_db_error_code(ctx.exception))
