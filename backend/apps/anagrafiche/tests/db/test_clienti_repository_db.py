# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le letture di `ClientiRepository` che la creazione del cliente usa
#        sulle entita' pre-esistenti, provate sul DATABASE VERO.
# Note: ⛔ Il caso che presidia: fino al 2026-10-08 `get_istanza` chiedeva al DB
#       `istanze_utilities.utility_id`, che non esiste — creare un cliente su
#       un'istanza esistente era un 500. I test di servizio mockano il
#       repository, e il mock portava la colonna: verdi per costruzione.
#       ⚠️ Il mondo si COSTRUISCE (`_mondo_cliente`), in transazione ANNULLATA.
#       ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) ClientiRepositoryDbTests.test_get_istanza_legge_l_istanza_del_cliente
2) ClientiRepositoryDbTests.test_get_billing_account_porta_la_coppia
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.anagrafiche.tests.db.test_ricerca_liste_db import _mondo_cliente
from apps.core.tests.db_e2e import Annulla, richiedi_db_provvisto


class ClientiRepositoryDbTests(unittest.TestCase):

    def setUp(self):
        richiedi_db_provvisto()

    # 1. L'istanza si legge: soggetto e id, le colonne che il service confronta.
    def test_get_istanza_legge_l_istanza_del_cliente(self):
        from apps.anagrafiche.db.clienti_repository import ClientiRepository

        try:
            with transaction.atomic(), connection.cursor() as cur:
                mondo, _cliente_id = _mondo_cliente(cur)
                cli = mondo["cliente"]
                istanza = ClientiRepository().get_istanza(cli["istanza_utility_id"])
                assert istanza is not None
                self.assertEqual(str(istanza["soggetto_id"]), str(cli["soggetto_id"]))
                raise Annulla
        except Annulla:
            pass

    # 2. Il BA porta la sua coppia (istanza, utility): e' su quella che il
    #    service verifica il BA indicato dal chiamante.
    def test_get_billing_account_porta_la_coppia(self):
        from apps.anagrafiche.db.clienti_repository import ClientiRepository

        try:
            with transaction.atomic(), connection.cursor() as cur:
                mondo, _cliente_id = _mondo_cliente(cur)
                cli = mondo["cliente"]
                ba = ClientiRepository().get_billing_account(cli["billing_account_id"])
                assert ba is not None
                self.assertEqual(
                    (ba["istanza_utility_id"], ba["utility_id"]),
                    (cli["istanza_utility_id"], cli["utility_id"]),
                )
                raise Annulla
        except Annulla:
            pass
