# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La lookup delle istanze utility con `q` VUOTA e un perimetro (la
#        tendina del drawer pratiche, che elenca le istanze del ruolo al click
#        senza digitare), provata sul DATABASE VERO.
# Note: ⛔ Il difetto che presidia non da' errore. Dal 2026-09-26 il pattern lo
#       costruisce `pattern_contiene`, che per un termine vuoto torna `None`
#       (prima `%%`, cioe' tutte le righe): senza la guardia `%s::text IS NULL`
#       nel WHERE la ricerca diventava `ILIKE NULL`, cioe' ZERO righe con un
#       200. Il test di servizio mocka il repository e non poteva vederlo.
#       ⚠️ Il mondo si COSTRUISCE (builder `dbops.fn_pgtap_crea_*`, lo stesso
#       mondo di `test_ricerca_liste_db`), in transazione ANNULLATA.
#       ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) LookupIstanzeQVuotaDbTests.test_q_vuota_col_ruolo_elenca_le_istanze_del_ruolo
2) LookupIstanzeQVuotaDbTests.test_q_valorizzata_filtra_ancora
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.anagrafiche.tests.db.test_ricerca_liste_db import _mondo_cliente
from apps.core.tests.db_e2e import Annulla, richiedi_db_provvisto


class LookupIstanzeQVuotaDbTests(unittest.TestCase):

    def setUp(self):
        richiedi_db_provvisto()

    # Scopo: esegue la lookup sul perimetro del ruolo del cliente costruito e
    #        ritorna gli id delle istanze trovate. `emittente_ids=None`: qui si
    #        prova la ricerca, non lo scope emittente.
    @staticmethod
    def _cerca(q: str, soggetto_ruolo_id: int) -> set[int]:
        from apps.anagrafiche.db.istanze_utility_repository import IstanzeUtilityRepository

        righe, _totale = IstanzeUtilityRepository().search_lookup(
            q=q, utility_id=None, soggetto_id=None,
            soggetto_ruolo_id=soggetto_ruolo_id, emittente_ids=None, limit=50,
        )
        return {r["id"] for r in righe}

    # 1. Il caso della tendina: nessun termine, il perimetro basta.
    def test_q_vuota_col_ruolo_elenca_le_istanze_del_ruolo(self):
        try:
            with transaction.atomic(), connection.cursor() as cur:
                mondo, _cliente_id = _mondo_cliente(cur)
                cli = mondo["cliente"]
                self.assertIn(
                    cli["istanza_utility_id"],
                    self._cerca("", cli["soggetto_ruolo_id"]),
                )
                raise Annulla
        except Annulla:
            pass

    # 2. La guardia non spegne il filtro: un termine che non c'e' non trova.
    def test_q_valorizzata_filtra_ancora(self):
        try:
            with transaction.atomic(), connection.cursor() as cur:
                mondo, _cliente_id = _mondo_cliente(cur)
                cli = mondo["cliente"]
                self.assertEqual(
                    set(), self._cerca("zzqq-nessuna-istanza-cosi", cli["soggetto_ruolo_id"]),
                )
                raise Annulla
        except Annulla:
            pass
