# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `OrdiniRepository.create_ordine` sul DATABASE PROVVISTO, dopo il
#        passaggio al BB `execute_dynamic_insert` (2026-09-26): la riga nasce
#        davvero in `vendite.ordini` e i valori riletti sono quelli scritti.
#        Presidia le convenzioni del BB che un mock non vede:
#          · `skip_none` — un opzionale None si OMETTE e vale il DEFAULT del
#            DB (`data` = fn_data_operativa(), `fatturazione_immediata` = false,
#            `canale_origine` = ADMIN) o il trigger BEFORE INSERT
#            (`fatturazione_trigger` ereditato dal cliente da
#            `trgfn_ordini_normalize`: NOT NULL senza DEFAULT, quindi un NULL
#            esplicito o un'omissione devono dare lo stesso esito);
#          · lo stato NON si passa: l'ordine nasce nello stato iniziale, e
#            lo mette il DB (`script.trgfn_doc_stato_iniziale`, P-2 di
#            brief-modello-documento-vendita);
#          · il dict `meta` esce `::jsonb` e si rilegge come oggetto;
#          · le stringhe arrivano strippate: `fatturazione_trigger` con spazi ai
#            bordi passa il CHECK di vocabolario SOLO se il BB lo stripa (il
#            trigger non fa `btrim` su quella colonna).
# Note: ⚠️ Il mondo si COSTRUISCE (regola zero): azienda, operatore e cliente
#       da `dbops.fn_pgtap_crea_mondo_cliente`, che apre anche il contesto
#       operatore. Transazione SEMPRE annullata. Opt-in `ZEROERP_TEST_DB_E2E=1`.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) CreateOrdineDbTests.test_la_testata_nasce_coi_valori_scritti_e_i_default
"""
from __future__ import annotations

import json
import unittest
from datetime import date

from django.db import connection, transaction

from apps.core.db._helpers import row_to_dict
from apps.core.tests.db_e2e import richiedi_db_provvisto
from apps.vendite.db.ordini_repository import OrdiniRepository

_META = {"test_scope": "be_create_ordine_db", "annidato": {"n": 1, "lista": [1, 2]}}

_RILETTURA = """
    SELECT soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id, utility_id,
           emittente_fiscale_id, valuta_id, fatturazione_trigger, data,
           fatturazione_immediata, canale_origine::text AS canale_origine,
           meta, jsonb_typeof(meta) AS meta_tipo, uid::text AS uid
      FROM vendite.ordini WHERE id = %s
"""


class CreateOrdineDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def test_la_testata_nasce_coi_valori_scritti_e_i_default(self):
        with transaction.atomic():
            try:
                with connection.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('create ordine db')"
                    )
                    mondo = row_to_dict(cur)
                    assert mondo is not None
                    cur.execute("SELECT id FROM config.valute ORDER BY id LIMIT 1")
                    valuta_id = cur.fetchone()[0]
                    cur.execute("SELECT id FROM config.stati_doc_ordini WHERE codice_interno = 'DRAFT'")
                    stato_bozza_id = cur.fetchone()[0]
                    cur.execute("SELECT script.fn_data_operativa()")
                    oggi = cur.fetchone()[0]
                    repo = OrdiniRepository()

                    # (a) Il payload che `ordini_service.crea_ordine` passa al
                    #     repository, coi valori espliciti.
                    # ⭐ Ruolo e utility NON si passano: li scrive il DB dal BA
                    #    (brief-db-esecutivi-ba-coppia §10.2), e la rilettura
                    #    sotto lo prova.
                    creato = repo.create_ordine(
                        billing_account_id=mondo["billing_account_id"],
                        emittente_fiscale_id=mondo["emittente_fiscale_id"],
                        valuta_id=valuta_id,
                        modalita_pagamento_id=None,
                        termine_pagamento_id=None,
                        fatturazione_trigger="  SPEDITO  ",
                        agente_soggetto_ruolo_id=None,
                        data=date(2083, 3, 15),
                        meta=_META,
                        fatturazione_immediata=None,
                    )
                    self.assertEqual(set(creato), {"id", "uid", "numero"})
                    cur.execute(_RILETTURA, [creato["id"]])
                    riga = row_to_dict(cur)
                    self.assertIsNotNone(riga, "la riga creata non si rilegge (RLS?)")
                    assert riga is not None
                    self.assertEqual(riga["uid"], creato["uid"])
                    self.assertEqual(riga["soggetto_ruolo_id"], mondo["cliente_soggetto_ruolo_id"])
                    self.assertEqual(riga["billing_account_id"], mondo["billing_account_id"])
                    # Lo stato non si passa: l'ordine nasce in bozza perche'
                    # lo mette il DB (brief-modello-documento-vendita P-2).
                    self.assertEqual(riga["stato_doc_ordine_id"], stato_bozza_id)
                    self.assertEqual(riga["utility_id"], mondo["utility_id"])
                    self.assertEqual(riga["emittente_fiscale_id"], mondo["emittente_fiscale_id"])
                    self.assertEqual(riga["valuta_id"], valuta_id)
                    self.assertEqual(riga["fatturazione_trigger"], "SPEDITO")
                    self.assertEqual(riga["data"], date(2083, 3, 15))
                    self.assertIs(riga["fatturazione_immediata"], False)
                    self.assertEqual(riga["canale_origine"], "ADMIN")
                    self.assertEqual(riga["meta_tipo"], "object")
                    # ⚠️ Il cursore Django rende il jsonb come TESTO.
                    self.assertEqual(json.loads(riga["meta"]), _META)

                    # (b) Gli opzionali None: `data` al DEFAULT, il trigger
                    #     eredita `fatturazione_trigger`, `meta` None -> {}.
                    minimo = repo.create_ordine(
                        billing_account_id=mondo["billing_account_id"],
                    )
                    cur.execute(_RILETTURA, [minimo["id"]])
                    riga = row_to_dict(cur)
                    assert riga is not None
                    self.assertEqual(riga["data"], oggi)
                    self.assertIn(riga["fatturazione_trigger"], {"CONFERMATO", "SPEDITO", "CONSEGNATO"})
                    self.assertEqual(riga["emittente_fiscale_id"], mondo["emittente_fiscale_id"])
                    self.assertEqual(json.loads(riga["meta"]), {})
            finally:
                transaction.set_rollback(True)
