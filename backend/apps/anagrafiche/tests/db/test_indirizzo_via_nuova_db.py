# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La via nuova incompleta, dal service vero al DATABASE VERO (passaggio
#        al BE del giro 4, brief-db-revisione-anagrafiche §21.7): la rifiuta
#        `anagrafiche.fn_create_indirizzo` con `E_INDIRIZZO_VIA_NUOVA_INCOMPLETA`
#        e col campo che manca, uno per volta nell'ordine del DB.
# Note: ⛔ Il backend NON tiene la regola: fino al 2026-11-26 `richiedi_via` ne
#       era una seconda sede, senza il campo. Il service tiene solo il
#       contratto degli id (positivi), che qui non si prova.
#       Transazione ANNULLATA, ogni rifiuto in un SAVEPOINT. I quattro valori
#       si leggono dal catalogo: nessun id cablato.
#       Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) IndirizzoViaNuovaDbTests.test_il_campo_che_manca_si_accende
"""
from __future__ import annotations

import unittest
from typing import Any

from django.db import connection, transaction

from apps.anagrafiche.services.geo_service import GeoService
from apps.core.services.error_translator import ErrorTranslator
from apps.core.tests.db_e2e import apri_contesto_operatore, apri_transazione_annullata, richiedi_db_provvisto


class IndirizzoViaNuovaDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            apri_contesto_operatore(cur)
            cur.execute("SELECT id FROM config.toponomastica ORDER BY id LIMIT 1")
            topo = cur.fetchone()
            cur.execute("SELECT comune_id, id FROM config.codici_postali ORDER BY id LIMIT 1")
            cap = cur.fetchone()
        if topo is None or cap is None:
            self.skipTest("Catalogo senza toponimi o senza CAP.")
        self.completa: dict[str, Any] = {
            "toponomastica_id": topo[0], "descrizione_via": "Via BE incompleta",
            "comune_id": cap[0], "codice_postale_id": cap[1], "civico": 1,
        }

    def test_il_campo_che_manca_si_accende(self) -> None:
        for campo in ("toponomastica_id", "descrizione_via", "comune_id", "codice_postale_id"):
            payload = {k: v for k, v in self.completa.items() if k != campo}
            with self.subTest(campo=campo):
                try:
                    with transaction.atomic():
                        GeoService().create_indirizzo(payload)
                except Exception as exc:  # la strada e' cio' che si prova
                    api = ErrorTranslator.to_api_error(exc)
                    self.assertEqual(api.code, "E_INDIRIZZO_VIA_NUOVA_INCOMPLETA", f"{api.message} — {exc!r}")
                    self.assertEqual(list(api.fields or ()), [campo])
                    self.assertEqual(ErrorTranslator.get_http_status(api), 400)
                    continue
                self.fail(f"via nuova senza {campo} accettata")
