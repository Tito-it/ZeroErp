# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il filtro `scadenza_mese` della lista contratti sul DATABASE
#        PROVVISTO (brief-db-mese-di-un-giorno, R-BE-2): il mese di
#        `valido_al` si chiede al BB `script.fn_mese_di`. E' la giuntura
#        Python↔SQL che i test del service (mock) non vedono: il binding del
#        parametro, il nome della funzione, i due confini del mese.
# Note: ⚠️ La REGOLA del mese (bisestili, fusi, NULL) la prova il pgTAP
#       `script/test-mese-di-un-giorno-v1`. Qui il mondo si COSTRUISCE: due
#       clienti, un contratto ciascuno, uno che scade l'ULTIMO giorno di un
#       mese e uno il PRIMO del mese dopo, in transazione ANNULLATA. Opt-in
#       `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) ContrattiListaScadenzaMeseDbTests.test_il_contratto_cade_nel_mese_del_suo_valido_al
2) ContrattiListaScadenzaMeseDbTests.test_valido_al_aperto_non_ha_mese
"""
from __future__ import annotations

import unittest
from datetime import date, timedelta
from typing import Any

from django.db import connection

from apps.core.db._helpers import row_to_dict
from apps.core.tests.db_e2e import apri_contesto_su, apri_transazione_annullata, richiedi_db_provvisto
from apps.vendite.services.contratti_service import ContrattiService


def _primo_del_mese_dopo(giorno: date) -> date:
    return (giorno.replace(day=1) + timedelta(days=31)).replace(day=1)


class ContrattiListaScadenzaMeseDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto("script.fn_mese_di(date)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore()")
            mondo = row_to_dict(cur)
            assert mondo is not None
            self.mondo: dict[str, Any] = mondo
            apri_contesto_su(cur, mondo["auth_user_id"])
            cur.execute("SELECT script.fn_data_operativa()")
            self.oggi: date = cur.fetchone()[0]
        self.servizio = ContrattiService()
        # Il mese M sta qualche mese avanti: valido_al resta dopo valido_dal.
        self.primo_m = _primo_del_mese_dopo(_primo_del_mese_dopo(self.oggi))
        self.primo_m1 = _primo_del_mese_dopo(self.primo_m)

    def _contratto(self, etichetta: str, valido_al: date | None) -> tuple[int, int]:
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(%s)", [etichetta])
            cliente = row_to_dict(cur)
            assert cliente is not None
            cur.execute(
                "SELECT listino_id FROM dbops.fn_pgtap_crea_listino(%s, %s)",
                [cliente["utility_id"], etichetta],
            )
            listino_id = cur.fetchone()[0]
        payload: dict[str, Any] = {
            "billing_account_id": cliente["billing_account_id"],
            "istanza_utility_id": cliente["istanza_utility_id"],
            "utility_id": cliente["utility_id"],
            "emittente_fiscale_id": self.mondo["emittente_fiscale_id"],
            "listino_id": listino_id,
            "valido_dal": (self.oggi - timedelta(days=30)).isoformat(),
        }
        if valido_al is not None:
            payload["valido_al"] = valido_al.isoformat()
        contratto_id = int(self.servizio.create_contratto(payload)["id"])
        return contratto_id, int(cliente["billing_account_id"])

    def _ids(self, scadenza_mese: str, billing_account_id: int) -> set[int]:
        righe, _ = self.servizio.list_contratti(
            scadenza_mese=scadenza_mese,
            billing_account_id=billing_account_id,
            auth_user_id=self.mondo["auth_user_id"],
        )
        return {int(r["id"]) for r in righe}

    def test_il_contratto_cade_nel_mese_del_suo_valido_al(self) -> None:
        fine_m = self.primo_m1 - timedelta(days=1)
        a, ba_a = self._contratto("scadenza mese ultimo", fine_m)
        b, ba_b = self._contratto("scadenza mese primo", self.primo_m1)
        mese_m = self.primo_m.strftime("%Y-%m")
        mese_m1 = self.primo_m1.strftime("%Y-%m")

        self.assertEqual(self._ids(mese_m, ba_a), {a})
        self.assertEqual(self._ids(mese_m1, ba_a), set())
        self.assertEqual(self._ids(mese_m, ba_b), set())
        self.assertEqual(self._ids(mese_m1, ba_b), {b})

    def test_valido_al_aperto_non_ha_mese(self) -> None:
        _, ba = self._contratto("scadenza mese aperto", None)
        self.assertEqual(self._ids(self.primo_m.strftime("%Y-%m"), ba), set())
