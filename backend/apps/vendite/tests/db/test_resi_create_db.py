# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `ResiRepository.create_reso` sul DATABASE PROVVISTO, dopo il passaggio
#        al BB `execute_dynamic_insert` (2026-09-26): la testata nasce davvero
#        in `vendite.resi`, eredita dal DDT sorgente cio' che il trigger le da'
#        (destinatario, cliente, emittente), e i valori riletti sono quelli
#        scritti. Presidia `skip_none` (`data` None -> DEFAULT fn_data_operativa()),
#        il dict `meta` -> `::jsonb` e la nascita in bozza senza che lo stato si
#        passi (lo mette il DB, P-2 di brief-modello-documento-vendita).
# Note: ⚠️ Il reso nasce SOLO da un DDT CONSEGNATO
#       (`trgfn_resi_guard_ddt_consegnato`): la bolla la costruisce
#       `_ddt_consegnato.crea_ddt_consegnato` (estratto da qui il 2026-10-19,
#       regola del 2). Transazione SEMPRE annullata. Opt-in `ZEROERP_TEST_DB_E2E=1`.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) CreateResoDbTests.test_la_testata_nasce_dal_ddt_consegnato_coi_default
   (anche: il dettaglio porta il magazzino di rientro della bolla d'origine)
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.core.db._helpers import row_to_dict
from apps.core.tests.db_e2e import richiedi_db_provvisto
from apps.vendite.db.resi_repository import ResiRepository
from apps.vendite.tests.db._ddt_consegnato import crea_ddt_consegnato

_META = {"test_scope": "be_create_reso_db", "annidato": {"n": 1, "lista": [1, 2]}}

class CreateResoDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def test_la_testata_nasce_dal_ddt_consegnato_coi_default(self):
        with transaction.atomic():
            try:
                with connection.cursor() as cur:
                    ddt = crea_ddt_consegnato(cur, etichetta="create reso db")
                    cur.execute("SELECT * FROM _mondo")
                    mondo = row_to_dict(cur)
                    assert mondo is not None
                    # Il caso si e' formato davvero: senza, il reso sarebbe
                    # rifiutato dal guard e il test proverebbe il guard.
                    self.assertEqual(ddt["stato"], "CONSEGNATO")
                    cur.execute("SELECT id FROM config.sorgenti WHERE codice_interno = 'DDT_VENDITA'")
                    sorgente_tipo_id = cur.fetchone()[0]
                    cur.execute("SELECT id FROM config.stati_doc_reso WHERE codice_interno = 'DRAFT'")
                    stato_bozza_id = cur.fetchone()[0]
                    cur.execute("SELECT script.fn_data_operativa()")
                    oggi = cur.fetchone()[0]

                    # Il payload di `resi_service.crea_reso`: `sorgente_uid`
                    # e' `str(ddt["uid"])`, `data` None (non indicata).
                    creato = ResiRepository().create_reso(
                        sorgente_tipo_id=sorgente_tipo_id,
                        sorgente_uid=ddt["uid"],
                        data=None,
                        meta=_META,
                    )
                    self.assertEqual(set(creato), {"id", "uid", "numero"})

                    cur.execute(
                        """
                        SELECT sorgente_tipo_id, sorgente_uid::text AS sorgente_uid,
                               stato_doc_reso_id, data, destinatario_soggetto_ruolo_id,
                               billing_account_id, emittente_fiscale_id,
                               meta, jsonb_typeof(meta) AS meta_tipo, uid::text AS uid
                          FROM vendite.resi WHERE id = %s
                        """,
                        [creato["id"]],
                    )
                    riga = row_to_dict(cur)
                    self.assertIsNotNone(riga, "la riga creata non si rilegge (RLS?)")
                    assert riga is not None
                    self.assertEqual(riga["uid"], creato["uid"])
                    self.assertEqual(riga["sorgente_tipo_id"], sorgente_tipo_id)
                    self.assertEqual(riga["sorgente_uid"], ddt["uid"])
                    # Lo stato non si passa: nasce in bozza perche' lo mette
                    # il DB (brief-modello-documento-vendita P-2).
                    self.assertEqual(riga["stato_doc_reso_id"], stato_bozza_id)
                    # skip_none: `data` omessa -> DEFAULT fn_data_operativa().
                    self.assertEqual(riga["data"], oggi)
                    # Ereditati dal DDT sorgente dal trigger.
                    self.assertEqual(riga["destinatario_soggetto_ruolo_id"], mondo["cliente_soggetto_ruolo_id"])
                    self.assertEqual(riga["billing_account_id"], mondo["billing_account_id"])
                    self.assertEqual(riga["emittente_fiscale_id"], mondo["emittente_fiscale_id"])
                    self.assertEqual(riga["meta_tipo"], "object")
                    # Il jsonb arriva decodificato dal lettore comune (`row_to_dict`).
                    self.assertEqual(riga["meta"], _META)

                    # Il dettaglio porta il magazzino di rientro con le sue
                    # etichette (3-bis D-3b-a): senza indicarlo, quello della
                    # bolla d'origine (`trgfn_resi_default_magazzino`).
                    cur.execute(
                        "SELECT d.magazzino_id, m.codice FROM vendite.ddt d"
                        "  LEFT JOIN magazzino.magazzini m ON m.id = d.magazzino_id"
                        " WHERE d.id = (SELECT ddt_id FROM _ddt)"
                    )
                    mag_bolla, codice_bolla = cur.fetchone()
                    dettaglio = ResiRepository().get_reso(creato["id"])
                    assert dettaglio is not None
                    self.assertEqual(dettaglio["magazzino_id"], mag_bolla)
                    self.assertEqual(dettaglio["magazzino_codice"], codice_bolla)
                    self.assertIn("magazzino_descrizione", dettaglio)
            finally:
                transaction.set_rollback(True)
