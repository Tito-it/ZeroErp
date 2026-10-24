# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `PraticheRepository.ha_ba_attivo` misura «attivo» sul PERIODO del
#        cliente (C-8 di brief-db-cliente-manuale-uno-per-soggetto-e-utility),
#        sul DATABASE VERO. I casi sono quelli in cui il criterio di prima
#        («attivazione valorizzata e chiusura vuota») e il periodo rispondono
#        in due modi: una chiusura con data futura (ancora attivo) e
#        un'attivazione con data futura (non ancora attivo). Piu' l'annullato,
#        che non ha periodo.
# Note: ⚠️ Il mondo si COSTRUISCE (`dbops.fn_pgtap_crea_mondo_cliente` per il
#       contesto, `dbops.fn_pgtap_crea_cliente` per un cliente AT legato
#       all'azienda di chi agisce), in transazione ANNULLATA.
#       Le date si scrivono con un UPDATE: il periodo lo deriva il trigger
#       `trgfn_clienti_set_periodo`, e il grafo degli stati lo controlla
#       `trgfn_clienti_guard_stato_date` (AT -> CH, AT -> AN ammessi).
#       Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti:
Opt-in `ZEROERP_TEST_DB_E2E=1`:
1) HaBaAttivoDbTests.test_attivo_oggi
2) HaBaAttivoDbTests.test_attivazione_futura_non_e_attivo
3) HaBaAttivoDbTests.test_chiusura_futura_e_ancora_attivo
4) HaBaAttivoDbTests.test_chiuso_ieri_non_e_attivo
5) HaBaAttivoDbTests.test_annullato_non_e_attivo
"""
from __future__ import annotations

import unittest

from django.db import connection

from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.pratiche.db.pratiche_repository import PraticheRepository


class HaBaAttivoDbTests(unittest.TestCase):
    def setUp(self):
        richiedi_db_provvisto("dbops.fn_pgtap_crea_mondo_cliente(text,character varying)")
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            # Il mondo apre il contesto (azienda + operatore); il cliente lo
            # scrive il builder completo DOPO, su una utility senza PDP: AT da
            # oggi, legato dal trigger all'azienda di chi agisce.
            # ⚠️ In tabelle e non in una sola istruzione: la lettura non vede
            #    cio' che il builder scrive nella stessa istruzione.
            cur.execute(
                "CREATE TEMP TABLE _mondo AS"
                " SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('HABAATTIVO')"
            )
            cur.execute(
                "CREATE TEMP TABLE _cli AS"
                " SELECT * FROM dbops.fn_pgtap_crea_cliente('HABAATTIVO')"
            )
            cur.execute(
                "SELECT c.soggetto_id, m.emittente_fiscale_id, c.cliente_id"
                "  FROM _cli c CROSS JOIN _mondo m"
            )
            soggetto_id, emittente_id, cliente_id = cur.fetchone()
        self.soggetto_id = str(soggetto_id)
        self.emittente_id = emittente_id
        self.cliente_id = cliente_id

    # Scopo: porta il cliente del mondo nello stato e nelle date del caso.
    def _scrivi(self, stato: str, *, attivazione: str = "oggi", chiusura: str | None = None) -> None:
        espr = {"oggi": "script.fn_data_operativa()",
                "ieri": "script.fn_data_operativa() - 1",
                "futuro": "script.fn_data_operativa() + 10",
                "passato": "script.fn_data_operativa() - 10"}
        with connection.cursor() as cur:
            cur.execute(
                f"""
                UPDATE anagrafiche.clienti
                   SET stato_cliente_id = (SELECT id FROM config.stati_cliente
                                            WHERE codice_interno = %s),
                       data_attivazione = {espr[attivazione]},
                       data_chiusura = {espr[chiusura] if chiusura else 'NULL'}
                 WHERE id = %s
                """,
                [stato, self.cliente_id],
            )

    def _attivo(self) -> bool:
        return PraticheRepository().ha_ba_attivo(self.soggetto_id, self.emittente_id)

    # 1. Il cliente del mondo: AT da oggi.
    def test_attivo_oggi(self):
        self.assertTrue(self._attivo())

    # 2. Attivazione futura: prima valeva «attivo» (attivazione valorizzata).
    def test_attivazione_futura_non_e_attivo(self):
        self._scrivi("AT", attivazione="futuro")
        self.assertFalse(self._attivo())

    # 3. Chiusura futura: prima valeva «non attivo» (chiusura valorizzata).
    def test_chiusura_futura_e_ancora_attivo(self):
        self._scrivi("CH", attivazione="passato", chiusura="futuro")
        self.assertTrue(self._attivo())

    # 4. Chiuso ieri: il periodo [attivazione, chiusura) non contiene oggi.
    def test_chiuso_ieri_non_e_attivo(self):
        self._scrivi("CH", attivazione="passato", chiusura="ieri")
        self.assertFalse(self._attivo())

    # 5. Annullato: il trigger azzera date e periodo.
    def test_annullato_non_e_attivo(self):
        self._scrivi("AN")
        self.assertFalse(self._attivo())
