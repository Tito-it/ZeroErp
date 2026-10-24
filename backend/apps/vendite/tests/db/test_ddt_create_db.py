# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `DdtRepository.create_ddt` sul DATABASE PROVVISTO, dopo il passaggio
#        al BB `execute_dynamic_insert` (2026-09-26): la riga nasce davvero
#        in `vendite.ddt` e i valori riletti sono quelli scritti.
#        Presidia le tre convenzioni del BB che un mock non vede:
#          · `skip_none` — un opzionale None si OMETTE, e vale il DEFAULT del
#            DB (`data` = fn_data_operativa(), `fatturazione_immediata` = false);
#          · lo stato NON si passa: il DDT nasce nello stato iniziale, e lo
#            mette il DB (`script.trgfn_doc_stato_iniziale`, P-2 di
#            brief-modello-documento-vendita);
#          · il dict `meta` esce `::jsonb` e si rilegge come oggetto;
#          · le stringhe arrivano strippate (`targa`).
# Note: ⚠️ Il mondo si COSTRUISCE, non si cerca (regola zero): azienda,
#       operatore e cliente da `dbops.fn_pgtap_crea_mondo_cliente`, che apre
#       anche il contesto operatore (senza, RLS risponde zero righe e la
#       rilettura «trova niente»). Transazione SEMPRE annullata.
#       Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) CreateDdtDbTests.test_la_testata_nasce_coi_valori_scritti_e_i_default
"""
from __future__ import annotations

import json
import unittest
from decimal import Decimal

from django.db import connection, transaction

from apps.core.db._helpers import row_to_dict
from apps.core.tests.db_e2e import richiedi_db_provvisto
from apps.vendite.db.ddt_repository import DdtRepository

_META = {"test_scope": "be_create_ddt_db", "annidato": {"n": 1, "lista": [1, 2]}}


class CreateDdtDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def test_la_testata_nasce_coi_valori_scritti_e_i_default(self):
        with transaction.atomic():
            try:
                with connection.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('create ddt db')"
                    )
                    mondo = row_to_dict(cur)
                    assert mondo is not None
                    cur.execute("SELECT id FROM config.valute ORDER BY id LIMIT 1")
                    valuta_id = cur.fetchone()[0]
                    cur.execute("SELECT id FROM config.stati_doc_ddt WHERE codice_interno = 'DRAFT'")
                    stato_bozza_id = cur.fetchone()[0]
                    cur.execute("SELECT script.fn_data_operativa()")
                    oggi = cur.fetchone()[0]

                    # Il payload che `ddt_service.crea_ddt` passa al repository.
                    # ⭐ Col BA, destinatario e utility NON si passano: li scrive
                    #    il DB dal BA (brief-db-esecutivi-ba-coppia §10.2), e la
                    #    rilettura sotto lo prova.
                    creato = DdtRepository().create_ddt(
                        destinatario_soggetto_ruolo_id=None,
                        billing_account_id=mondo["billing_account_id"],
                        emittente_fiscale_id=mondo["emittente_fiscale_id"],
                        valuta_id=valuta_id,
                        num_colli=3,
                        peso_lordo="12.500",
                        targa="  AB 123 CD  ",
                        autista=None,
                        data=None,
                        meta=_META,
                        fatturazione_immediata=None,
                    )
                    self.assertEqual(set(creato), {"id", "uid", "numero"})
                    self.assertIsInstance(creato["uid"], str)

                    cur.execute(
                        """
                        SELECT destinatario_soggetto_ruolo_id, stato_doc_ddt_id,
                               billing_account_id, emittente_fiscale_id, utility_id,
                               valuta_id, num_colli, peso_lordo, targa, autista, data,
                               fatturazione_immediata, meta, jsonb_typeof(meta) AS meta_tipo,
                               uid::text AS uid
                          FROM vendite.ddt WHERE id = %s
                        """,
                        [creato["id"]],
                    )
                    riga = row_to_dict(cur)
                    self.assertIsNotNone(riga, "la riga creata non si rilegge (RLS?)")
                    assert riga is not None
                    self.assertEqual(riga["uid"], creato["uid"])
                    self.assertEqual(riga["destinatario_soggetto_ruolo_id"], mondo["cliente_soggetto_ruolo_id"])
                    # Lo stato non si passa: nasce in bozza perche' lo mette
                    # il DB (brief-modello-documento-vendita P-2).
                    self.assertEqual(riga["stato_doc_ddt_id"], stato_bozza_id)
                    self.assertEqual(riga["billing_account_id"], mondo["billing_account_id"])
                    self.assertEqual(riga["emittente_fiscale_id"], mondo["emittente_fiscale_id"])
                    self.assertEqual(riga["utility_id"], mondo["utility_id"])
                    self.assertEqual(riga["valuta_id"], valuta_id)
                    self.assertEqual(riga["num_colli"], 3)
                    self.assertEqual(riga["peso_lordo"], Decimal("12.500"))
                    # Strip del BB.
                    self.assertEqual(riga["targa"], "AB 123 CD")
                    self.assertIsNone(riga["autista"])
                    # skip_none: omessi -> DEFAULT del DB.
                    self.assertEqual(riga["data"], oggi)
                    self.assertIs(riga["fatturazione_immediata"], False)
                    # dict -> ::jsonb, riletto come oggetto.
                    self.assertEqual(riga["meta_tipo"], "object")
                    # ⚠️ Il cursore Django rende il jsonb come TESTO: si decodifica qui.
                    self.assertEqual(json.loads(riga["meta"]), _META)
            finally:
                transaction.set_rollback(True)
