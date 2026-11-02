# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il secondo cliente manuale con la stessa chiave (soggetto + utility +
#        azienda emittente, C-1 di brief-db-cliente-manuale-uno-per-soggetto-
#        e-utility) arriva all'operatore come 409 `E_CLIENTE_STESSA_CHIAVE`,
#        col codice del billing account del cliente esistente nel messaggio
#        (C-3). Sul DATABASE VERO: il rifiuto nasce da un constraint trigger
#        DIFFERITO, cioe' al COMMIT e non all'INSERT del cliente — e' il punto
#        che un test col repository mockato non puo' vedere.
# Note: ⚠️ Il mondo si COSTRUISCE (`dbops.fn_pgtap_crea_mondo_cliente` per azienda,
#       operatore e contesto; `dbops.fn_pgtap_crea_cliente` per il cliente AT
#       che occupa la chiave), in transazione ANNULLATA. Il COMMIT non c'e' (il test vive in una
#       transazione): lo si simula con `SET CONSTRAINTS ALL IMMEDIATE`, che fa
#       scattare i trigger differiti come farebbe il COMMIT.
#       ⛔ Nessun pre-check nel BE: la regola ha una sede sola, il guard DB.
#       Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti:
Opt-in `ZEROERP_TEST_DB_E2E=1`:
1) ClienteStessaChiaveDbTests.test_secondo_cliente_stessa_chiave_e_409
   `ClientiService.crea_cliente` sullo stesso soggetto e utility di un
   cliente AT esistente: la creazione passa, il COMMIT rifiuta; la traduzione da'
   `E_CLIENTE_STESSA_CHIAVE`, 409, e il messaggio porta il codice del BA
   esistente.
"""
from __future__ import annotations

import unittest

from django.db import DatabaseError, connection, transaction

from apps.anagrafiche.services.clienti_service import ClientiService
from apps.core.services.error_translator import ErrorTranslator
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto


class ClienteStessaChiaveDbTests(unittest.TestCase):
    def setUp(self):
        richiedi_db_provvisto("anagrafiche.fn_clienti_stessa_chiave(bigint,integer,bigint)")
        apri_transazione_annullata(self)

    # 1. Il doppione: stessa chiave, periodi sovrapposti (entrambi aperti da oggi).
    def test_secondo_cliente_stessa_chiave_e_409(self):
        with connection.cursor() as cur:
            # Il mondo apre il contesto (azienda + operatore); il cliente
            # esistente lo scrive il builder completo DOPO, su una utility
            # senza PDP (quella di un cliente manuale): AT da oggi, il legame
            # all'azienda di chi agisce lo scrive il trigger. Occupa la chiave.
            cur.execute("SELECT 1 FROM dbops.fn_pgtap_crea_mondo_cliente('STESSACHIAVE')")
            # ⚠️ Prima in una tabella e poi il JOIN: nella stessa istruzione la
            #    lettura di billing_account non vedrebbe il BA appena scritto
            #    dal builder (la fotografia e' di inizio istruzione).
            cur.execute(
                "CREATE TEMP TABLE _cli AS"
                " SELECT * FROM dbops.fn_pgtap_crea_cliente('STESSACHIAVE')"
            )
            cur.execute(
                "SELECT c.soggetto_id, c.utility_id, ba.categoria_cliente_id, ba.codice"
                "  FROM _cli c"
                "  JOIN anagrafiche.billing_account ba ON ba.id = c.billing_account_id"
            )
            soggetto_id, utility_id, categoria_id, ba_codice = cur.fetchone()
            # La finestra della creazione: l'istanza vuole il suo BA al COMMIT.
            cur.execute("SET CONSTRAINTS ALL DEFERRED")

        # Il secondo, manuale: istanza fittizia e BA nuovi, stessa azienda (il
        # legame lo scrive il trigger verso chi agisce). L'INSERT passa: il
        # guard della chiave e' differito.
        ClientiService().crea_cliente({
            "soggetto_id": str(soggetto_id),
            "utility_id": utility_id,
            "ba_categoria_cliente_id": categoria_id,
        })

        with self.assertRaises(DatabaseError) as ctx:
            with transaction.atomic(), connection.cursor() as cur:
                cur.execute("SET CONSTRAINTS ALL IMMEDIATE")

        api_error = ErrorTranslator.to_api_error(ctx.exception)
        self.assertEqual(api_error.code, "E_CLIENTE_STESSA_CHIAVE")
        self.assertEqual(ErrorTranslator.get_http_status(api_error), 409)
        self.assertIn(ba_codice, api_error.message)
