# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: LA STORIA DI UNA MAPPATURA E DI UNA CONVERSIONE, dalle porte del
#        backend fino al DB vero (BE21 di brief-db-revisione-catalogo, D24 e
#        D27, giro 2-bis, 2026-11-11). L'identita' (unita', fattore, inizio)
#        non si cambia sul posto (`E_UOM_STORIA_IMMUTABILE`); una mappatura in
#        vigore non si cancella, si chiude (`E_UOM_STORIA_IN_VIGORE`). Lo
#        giudica `catalogo.trgfn_uom_guard_storia`.
# Note: ⭐ Il caso 1: un client che rimanda TUTTI i campi, fattore e inizio
#       compresi e invariati, chiude lo stesso. Il guard giudica il
#       cambiamento, non la presenza. (I form del FE dal 2026-11-11 i campi
#       fermi non li mandano proprio: BB `senzaCampiFermi`.)
#       ⭐ Il mondo si COSTRUISCE (unita' e articolo dalle porte), in una
#       transazione annullata; le date dal giorno AZIENDALE.
#       Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) UomStoriaDbTests.test_chiusura_col_form_intero_passa
2) UomStoriaDbTests.test_fattore_della_mappatura_non_si_cambia
3) UomStoriaDbTests.test_mappatura_in_vigore_non_si_cancella
4) UomStoriaDbTests.test_mappatura_futura_si_cancella
5) UomStoriaDbTests.test_fattore_della_conversione_non_si_cambia
"""
from __future__ import annotations

import unittest
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any
from uuid import uuid4

from django.db import DatabaseError, connection, transaction

from apps.catalogo.services import catalogo_service
from apps.catalogo.tests.db._unita_di_prova import crea_unita_di_prova
from apps.core.services.error_translator import ErrorTranslator
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto


class UomStoriaDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto("catalogo.trgfn_uom_guard_storia()")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        self.sfx = uuid4().hex[:6].upper()
        with connection.cursor() as cur:
            cur.execute("SELECT script.fn_data_operativa()")
            self.oggi: date = cur.fetchone()[0]
        self.base = crea_unita_di_prova("SB", self.sfx)
        with connection.cursor() as cur:
            cur.execute(
                "SELECT dbops.fn_pgtap_crea_articolo(%s, p_uom_id => %s)::text",
                [f"USTO-{self.sfx}", self.base],
            )
            self.articolo = cur.fetchone()[0]

    def _giorni(self, n: int) -> date:
        return self.oggi + timedelta(days=n)

    def _mappatura(self, valido_dal: date) -> dict[str, Any]:
        return catalogo_service.fn_create_uom_operativa(self.articolo, {
            "uom_id": crea_unita_di_prova("SC", self.sfx), "factor_to_base": "10",
            "valido_dal": valido_dal.isoformat(),
        })

    # Il payload di un client che rimanda tutti i campi, come li ha letti.
    @staticmethod
    def _form(riga: dict[str, Any], **cambi: Any) -> dict[str, Any]:
        payload = {
            "factor_to_base": str(riga["factor_to_base"]),
            "valido_dal": riga["valido_dal"].isoformat(),
            "valido_al": riga["valido_al"].isoformat() if riga["valido_al"] else None,
            "attivo": riga["attivo"],
        }
        payload.update(cambi)
        return payload

    # Il rifiuto come lo riceve il client: dal service, o dal traduttore generale.
    def _rifiuto(self, chiama: Callable[[], Any]) -> Any:
        with self.assertRaises((ServiceError, DatabaseError)) as ctx, transaction.atomic():
            chiama()
        errore = ctx.exception
        return ErrorTranslator.to_api_error(errore) if isinstance(errore, DatabaseError) else errore

    # 1. Chiudere una mappatura in vigore col form intero: passa.
    def test_chiusura_col_form_intero_passa(self) -> None:
        riga = self._mappatura(self._giorni(-10))
        fine = self._giorni(5)
        esito = catalogo_service.fn_update_uom_operativa(
            self.articolo, riga["id"], self._form(riga, valido_al=fine.isoformat()),
        )
        self.assertEqual(esito["valido_al"], fine)

    # 2. Il fattore di una mappatura scritta non si cambia sul posto.
    def test_fattore_della_mappatura_non_si_cambia(self) -> None:
        riga = self._mappatura(self._giorni(-10))
        errore = self._rifiuto(lambda: catalogo_service.fn_update_uom_operativa(
            self.articolo, riga["id"], self._form(riga, factor_to_base="12"),
        ))
        self.assertEqual(errore.code, "E_UOM_STORIA_IMMUTABILE")

    # 3. Una mappatura con giorni passati non si cancella: si chiude.
    def test_mappatura_in_vigore_non_si_cancella(self) -> None:
        riga = self._mappatura(self._giorni(-10))
        errore = self._rifiuto(
            lambda: catalogo_service.fn_delete_uom_operativa(self.articolo, riga["id"]),
        )
        self.assertEqual(errore.code, "E_UOM_STORIA_IN_VIGORE")

    # 4. Una mappatura che comincia domani non ha giorni passati: si cancella.
    def test_mappatura_futura_si_cancella(self) -> None:
        riga = self._mappatura(self._giorni(1))
        catalogo_service.fn_delete_uom_operativa(self.articolo, riga["id"])

    # 5. Il fattore di una conversione generale non si cambia sul posto.
    def test_fattore_della_conversione_non_si_cambia(self) -> None:
        conversione = catalogo_service.fn_create_conversione({
            "uom_from_id": crea_unita_di_prova("SK", self.sfx), "uom_to_id": self.base, "fattore": "1000",
            "valido_dal": self._giorni(-10).isoformat(),
        })
        errore = self._rifiuto(lambda: catalogo_service.fn_update_conversione(
            conversione["id"], {"fattore": "999"},
        ))
        self.assertEqual(errore.code, "E_UOM_STORIA_IMMUTABILE")
