# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `ResiRepository.create_reso` sul DATABASE PROVVISTO, dopo il passaggio
#        al BB `execute_dynamic_insert` (2026-09-26): la testata nasce davvero
#        in `vendite.resi`, eredita dal DDT sorgente cio' che il trigger le da'
#        (destinatario, cliente, emittente), e i valori riletti sono quelli
#        scritti. Presidia `skip_none` (`data` None -> DEFAULT CURRENT_DATE) e
#        il dict `meta` -> `::jsonb`.
# Note: ⚠️ Il reso nasce SOLO da un DDT CONSEGNATO
#       (`trgfn_resi_guard_ddt_consegnato`), e non c'e' un BB `fn_pgtap_*` che
#       lo costruisca: la catena ordine CONFERMATO -> riga -> DDT generato ->
#       EMESSO -> SPEDITO -> CONSEGNATO e' la stessa di
#       `db/pgtap/vendite/test-annulla-reso-gate-accredito-v1.sql`
#       (`agr_mk_partita`), sul mondo costruito da
#       `dbops.fn_pgtap_crea_mondo_cliente` + `fn_pgtap_crea_articolo`.
#       Transazione SEMPRE annullata. Opt-in `ZEROERP_TEST_DB_E2E=1`.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) CreateResoDbTests.test_la_testata_nasce_dal_ddt_consegnato_coi_default
"""
from __future__ import annotations

import json
import unittest
from uuid import uuid4

from django.db import connection, transaction

from apps.core.db._helpers import row_to_dict
from apps.core.tests.db_e2e import richiedi_db_provvisto
from apps.vendite.db.resi_repository import ResiRepository

_META = {"test_scope": "be_create_reso_db", "annidato": {"n": 1, "lista": [1, 2]}}

# ⚠️ Padre e figlio in istruzioni SEPARATE (mai nella stessa CTE): una policy
#    che risolve il perimetro dal padre non vede le righe scritte dallo stesso
#    comando e nega fail-closed.
_FIXTURE: tuple[str, ...] = (
    "CREATE TEMP TABLE _mondo AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('create reso db')",
    "CREATE TEMP TABLE _art AS SELECT dbops.fn_pgtap_crea_articolo('RSART-' || %(sfx)s, false) AS articolo_id",
    """
    CREATE TEMP TABLE _refs AS
    SELECT (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
           (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
           (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno = 'CONFERMATO' AND s.attivo) AS ord_conf,
           (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno = 'EMESSO' AND s.attivo) AS ddt_emesso,
           (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno = 'SPEDITO' AND s.attivo) AS ddt_spedito,
           (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno = 'CONSEGNATO' AND s.attivo) AS ddt_consegnato,
           (SELECT c.id FROM config.causali_trasporto c WHERE c.codice = 'VENDITA' ORDER BY c.id LIMIT 1) AS causale_vendita,
           (SELECT t.id FROM config.tipi_indirizzi t WHERE t.codice_interno = 'CON') AS tipo_ind_con
    """,
    """
    CREATE TEMP TABLE _ord AS
    WITH ins AS (
        INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
            valuta_id, fatturazione_trigger, emittente_fiscale_id, storicizza, meta)
        SELECT m.cliente_soggetto_ruolo_id, m.billing_account_id, r.ord_conf, r.valuta_id,
               'CONSEGNATO', m.emittente_fiscale_id, false, '{"test_scope": "be_create_reso_db"}'::jsonb
          FROM _mondo m, _refs r
        RETURNING id
    )
    SELECT id AS ordine_id FROM ins
    """,
    """
    INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
        qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
    SELECT o.ordine_id, 1, a.articolo_id, 'Riga reso BE', 2, 2, 10.00, r.iva_id, true, false,
           '{"test_scope": "be_create_reso_db"}'::jsonb
      FROM _ord o, _art a, _refs r
    """,
    "CREATE TEMP TABLE _ddt AS SELECT vendite.fn_genera_ddt_da_ordine((SELECT ordine_id FROM _ord)) AS ddt_id",
    """
    INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
    SELECT d.ddt_id, r.tipo_ind_con, '{"display": "CON"}'::jsonb FROM _ddt d, _refs r
    ON CONFLICT DO NOTHING
    """,
    "UPDATE vendite.ddt SET causale_trasporto_id = (SELECT causale_vendita FROM _refs) WHERE id = (SELECT ddt_id FROM _ddt)",
    "UPDATE vendite.ddt SET stato_doc_ddt_id = (SELECT ddt_emesso FROM _refs) WHERE id = (SELECT ddt_id FROM _ddt)",
    "UPDATE vendite.ddt SET stato_doc_ddt_id = (SELECT ddt_spedito FROM _refs) WHERE id = (SELECT ddt_id FROM _ddt)",
    "UPDATE vendite.ddt SET stato_doc_ddt_id = (SELECT ddt_consegnato FROM _refs) WHERE id = (SELECT ddt_id FROM _ddt)",
)


class CreateResoDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def test_la_testata_nasce_dal_ddt_consegnato_coi_default(self):
        sfx = uuid4().hex[:8].upper()
        with transaction.atomic():
            try:
                with connection.cursor() as cur:
                    for passo in _FIXTURE:
                        cur.execute(passo, {"sfx": sfx})
                    cur.execute("SELECT * FROM _mondo")
                    mondo = row_to_dict(cur)
                    assert mondo is not None
                    cur.execute(
                        "SELECT d.id, d.uid::text AS uid, s.codice_interno AS stato"
                        "  FROM vendite.ddt d JOIN config.stati_doc_ddt s ON s.id = d.stato_doc_ddt_id"
                        " WHERE d.id = (SELECT ddt_id FROM _ddt)"
                    )
                    ddt = row_to_dict(cur)
                    assert ddt is not None
                    # Il caso si e' formato davvero: senza, il reso sarebbe
                    # rifiutato dal guard e il test proverebbe il guard.
                    self.assertEqual(ddt["stato"], "CONSEGNATO")
                    cur.execute("SELECT id FROM config.sorgenti WHERE codice_interno = 'DDT_VENDITA'")
                    sorgente_tipo_id = cur.fetchone()[0]
                    cur.execute("SELECT id FROM config.stati_doc_reso WHERE codice_interno = 'DRAFT'")
                    stato_bozza_id = cur.fetchone()[0]
                    cur.execute("SELECT current_date")
                    oggi = cur.fetchone()[0]

                    # Il payload di `resi_service.crea_reso`: `sorgente_uid`
                    # e' `str(ddt["uid"])`, `data` None (non indicata).
                    creato = ResiRepository().create_reso(
                        sorgente_tipo_id=sorgente_tipo_id,
                        sorgente_uid=ddt["uid"],
                        stato_doc_reso_id=stato_bozza_id,
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
                    self.assertEqual(riga["stato_doc_reso_id"], stato_bozza_id)
                    # skip_none: `data` omessa -> DEFAULT CURRENT_DATE.
                    self.assertEqual(riga["data"], oggi)
                    # Ereditati dal DDT sorgente dal trigger.
                    self.assertEqual(riga["destinatario_soggetto_ruolo_id"], mondo["cliente_soggetto_ruolo_id"])
                    self.assertEqual(riga["billing_account_id"], mondo["billing_account_id"])
                    self.assertEqual(riga["emittente_fiscale_id"], mondo["emittente_fiscale_id"])
                    self.assertEqual(riga["meta_tipo"], "object")
                    # ⚠️ Il cursore Django rende il jsonb come TESTO.
                    self.assertEqual(json.loads(riga["meta"]), _META)
            finally:
                transaction.set_rollback(True)
