# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: LA TENDINA DEI LISTINI di contratto e offerta sul DATABASE PROVVISTO
#        (brief-db-offerta-emissione-ed-erogazione F-2.3): il repository legge
#        `vendite.fn_listini_selezionabili(utility, emittente_fiscale_id)` e la
#        tendina propone solo i listini che il guard del documento ammette.
#
# 🔴 PERCHE' SUL DB VERO. La regola e' del DB (`script.fn_check_listino_documento`)
#    e la provano i pgTAP (`test-doc-listino-documento-v1`). Qui si prova la
#    GIUNTURA: che la chiamata parta coi tipi giusti (integer, bigint) e che
#    l'utility e l'emittente (PK) arrivino nell'ordine giusto. E il TRASPORTO
#    del rifiuto: un listino di un'altra utility sulla testata di contratto e
#    offerta arriva al `ServiceError` col codice del guard e col campo
#    `listino_id` (api.md: «un BB unifica la lettura, non il trasporto»). Un
#    repository mockato non vede ne' l'una ne' l'altro.
#
# ⭐ Il mondo si COSTRUISCE (regola zero), come nel pgTAP: un'azienda e il suo
#    operatore (`fn_pgtap_crea_emittente_operatore`), il contesto, due utility
#    che ammettono una tipologia, un listino per ciascuna. Tutto in transazione
#    ANNULLATA.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) test_propone_il_listino_della_utility_e_dell_emittente — non quello di un'altra utility
2) test_senza_utility_o_emittente_nessun_listino
3) test_contratto_patch_listino_di_altra_utility — E_DOC_LISTINO_UTILITY_DIVERSA, campo listino_id
4) test_offerta_patch_listino_di_altra_utility — lo stesso codice e lo stesso campo
"""
from __future__ import annotations

import unittest


from django.db import connection, transaction

from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import richiedi_db_provvisto
from apps.vendite.db.listini_repository import ListiniRepository
from apps.vendite.db.offerte_repository import OfferteRepository
from apps.vendite.services.contratti_service import ContrattiService
from apps.vendite.services.offerte_service import OfferteService

_CODICE_UTILITY = "E_DOC_LISTINO_UTILITY_DIVERSA"

_FIXTURE: tuple[str, ...] = (
    "CREATE TEMP TABLE _mondo AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore()",
    "SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo))",
    # Due utility che ammettono una tipologia di listino (il builder la pretende).
    """
    CREATE TEMP TABLE _u AS
    SELECT (array_agg(u.id ORDER BY u.id))[1] AS u1,
           (array_agg(u.id ORDER BY u.id))[2] AS u2
      FROM config.utilities u
     WHERE EXISTS (SELECT 1 FROM config.listini_tipologie_utilities ltu
                    WHERE ltu.utility_id = u.id AND ltu.attivo)
    """,
    "CREATE TEMP TABLE _l1 AS SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT u1 FROM _u), 'BE selezionabili U1')",
    "CREATE TEMP TABLE _l2 AS SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT u2 FROM _u), 'BE selezionabili U2')",
    # Il cliente sulla utility U1, a contesto aperto (il z90 lo lega a chi agisce).
    "CREATE TEMP TABLE _c AS SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('BE selezionabili', (SELECT u1 FROM _u))",
)

# Un contratto in DRAFT sulla utility U1 col listino coerente L1.
_CONTRATTO = (
    "INSERT INTO vendite.contratti (numero, billing_account_id, istanza_utility_id, utility_id,"
    " emittente_fiscale_id, stato_doc_contratto_id, listino_id, valido_dal, valido_al)"
    " SELECT 'BESEL-' || substr(gen_random_uuid()::text, 1, 8),"
    " c.billing_account_id, c.istanza_utility_id, c.utility_id, m.emittente_fiscale_id,"
    " (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT'),"
    " (SELECT listino_id FROM _l1), script.fn_data_operativa(), script.fn_data_operativa() + 365"
    " FROM _c c, _mondo m RETURNING id"
)


class ListiniSelezionabiliDbTests(unittest.TestCase):
    """La lettura della tendina, sul mondo costruito."""

    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto("vendite.fn_listini_selezionabili(integer,bigint)")

    # Scopo: esegue `azione(cur, ids)` sul mondo, in una transazione SEMPRE
    #        annullata. `ids`: u1, u2, ef (PK dell'emittente), l1, l2.
    def _nel_mondo(self, azione):
        with transaction.atomic():
            try:
                with connection.cursor() as cur:
                    for passo in _FIXTURE:
                        cur.execute(passo)
                    cur.execute(
                        "SELECT u.u1, u.u2, m.emittente_fiscale_id, l1.listino_id, l2.listino_id"
                        " FROM _u u, _mondo m, _l1 l1, _l2 l2"
                    )
                    riga = cur.fetchone()
                    assert riga is not None
                    if riga[1] is None:
                        self.skipTest("serve una seconda utility con una tipologia di listino")
                    return azione(cur, riga)
            finally:
                transaction.set_rollback(True)

    # 1.
    def test_propone_il_listino_della_utility_e_dell_emittente(self):
        def _prova(_cur, ids):
            u1, u2, ef, l1, l2 = ids
            per_u1 = ListiniRepository().list_lookup_selezionabili(u1, ef)
            id_u1 = {r["id"] for r in per_u1}
            self.assertIn(l1, id_u1)
            self.assertNotIn(l2, id_u1, "un listino di un'altra utility non si propone")
            self.assertEqual(set(per_u1[0].keys()), {"id", "codice", "descrizione"})
            id_u2 = {r["id"] for r in ListiniRepository().list_lookup_selezionabili(u2, ef)}
            self.assertIn(l2, id_u2)
            self.assertNotIn(l1, id_u2)

        self._nel_mondo(_prova)

    # 2.
    def test_senza_utility_o_emittente_nessun_listino(self):
        def _prova(_cur, ids):
            u1, _u2, ef, _l1, _l2 = ids
            repo = ListiniRepository()
            self.assertEqual(repo.list_lookup_selezionabili(None, ef), [])
            self.assertEqual(repo.list_lookup_selezionabili(u1, None), [])

        self._nel_mondo(_prova)

    # Scopo: il rifiuto del guard, col codice e col campo nei canali strutturati.
    def _assert_listino_rifiutato(self, azione) -> None:
        def _prova(cur, ids):
            with self.assertRaises(ServiceError) as ctx, transaction.atomic():
                azione(cur, ids)
            self.assertEqual(ctx.exception.code, _CODICE_UTILITY)
            self.assertIn("listino_id", ctx.exception.fields or ())

        self._nel_mondo(_prova)

    # 3.
    def test_contratto_patch_listino_di_altra_utility(self):
        def azione(cur, ids):
            cur.execute(_CONTRATTO)
            contratto_id = cur.fetchone()[0]
            ContrattiService().update_contratto(contratto_id, {"listino_id": ids[4]})

        self._assert_listino_rifiutato(azione)

    # 4.
    def test_offerta_patch_listino_di_altra_utility(self):
        def azione(cur, ids):
            repo = OfferteRepository()
            cur.execute("SELECT billing_account_id, istanza_utility_id, utility_id FROM _c")
            ba, istanza, utility = cur.fetchone()
            offerta_id = repo.create_offerta({
                "emittente_fiscale_id": ids[2],
                "billing_account_id": ba,
                "istanza_utility_id": istanza,
                "utility_id": utility,
                "listino_id": ids[3],
                "validita_dal": oggi_aziendale(),
            })
            OfferteService().aggiorna_offerta(offerta_id, {"listino_id": ids[4]})

        self._assert_listino_rifiutato(azione)
