# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I due lookup con cui la pratica sceglie il cliente a grana fine (D-9
#        di brief-db-istanza-nasce-col-ba), provati sul DATABASE VERO: il
#        lookup istanze da' una riga per billing account, e il lookup
#        soggetto+ruolo conta i BA del ruolo.
# Note: ⛔ Il caso che presidia non si vede con un mondo da un BA solo: serve
#       un'istanza con DUE utility, cioe' due BA. Fino al 2026-10-08 la riga
#       era l'istanza con un BA «campione» (`LIMIT 1`) e il ruolo contava le
#       istanze via `clienti`: col secondo BA senza riga cliente il lookup lo
#       ignorava, e nessun test se ne poteva accorgere.
#       ⚠️ Il mondo si COSTRUISCE (builder `dbops.fn_pgtap_crea_*` tramite
#       `_mondo_cliente`), in transazione ANNULLATA.
#       ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) LookupFornitureDbTests.test_un_istanza_due_utility_da_due_righe
2) LookupFornitureDbTests.test_il_filtro_utility_tiene_la_sola_coppia
3) LookupFornitureDbTests.test_il_ruolo_conta_i_suoi_ba
4) LookupFornitureDbTests.test_il_restore_dell_istanza_non_sceglie_fra_due_ba
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.anagrafiche.tests.db.test_ricerca_liste_db import _mondo_cliente
from apps.core.tests.db_e2e import Annulla, richiedi_db_provvisto


# Scopo: il mondo del cliente (un BA, con la riga cliente) piu' un SECONDO BA
#        sulla stessa istanza, per un'altra utility e SENZA riga cliente: la
#        fase del preventivo, in cui il ruolo ha il BA e non ancora il cliente.
#        Ritorna (cliente del builder, id del secondo BA, utility del secondo).
def _mondo_due_ba(cur) -> tuple[dict, int, int]:
    mondo, _cliente_id = _mondo_cliente(cur)
    cli = mondo["cliente"]
    # Il BA nasce sotto l'operatore del MONDO, che ha la sua azienda: il trigger
    # z90 lo lega a quella di chi agisce, la stessa del primo BA (R-7, un'istanza
    # un emittente). `_mondo_cliente` chiude col superuser, che e' admin
    # globale e non puo' creare un BA (E_BA_ADMIN_GLOBALE_VIETATO).
    cur.execute("SELECT script.fn_pgtap_set_contesto_operatore(%s)", [mondo["auth_user_id"]])
    cur.execute(
        "SELECT u.id FROM config.utilities u WHERE u.id <> %s ORDER BY u.id LIMIT 1",
        [cli["utility_id"]],
    )
    utility_2 = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO anagrafiche.billing_account "
        "       (istanza_utility_id, soggetto_ruolo_id, utility_id, categoria_cliente_id) "
        "SELECT ba.istanza_utility_id, ba.soggetto_ruolo_id, %s, ba.categoria_cliente_id "
        "  FROM anagrafiche.billing_account ba WHERE ba.id = %s "
        "RETURNING id",
        [utility_2, cli["billing_account_id"]],
    )
    return cli, cur.fetchone()[0], utility_2


class LookupFornitureDbTests(unittest.TestCase):

    def setUp(self):
        richiedi_db_provvisto()

    # Scopo: la lookup istanze sul perimetro del ruolo, come la chiama il
    #        drawer della pratica. `emittente_ids=None`: qui si prova la forma
    #        delle righe, non lo scope emittente.
    @staticmethod
    def _cerca(soggetto_ruolo_id: int, utility_id: int | None = None) -> list[dict]:
        from apps.anagrafiche.db.istanze_utility_repository import IstanzeUtilityRepository

        righe, _totale = IstanzeUtilityRepository().search_lookup(
            q="", utility_id=utility_id, soggetto_id=None,
            soggetto_ruolo_id=soggetto_ruolo_id, emittente_ids=None, limit=50,
        )
        return righe

    # 1. Un'istanza con due utility e' due forniture: una riga per BA, e il
    #    secondo BA c'e' anche senza la riga cliente.
    def test_un_istanza_due_utility_da_due_righe(self):
        try:
            with transaction.atomic(), connection.cursor() as cur:
                cli, ba_2, _utility_2 = _mondo_due_ba(cur)
                righe = self._cerca(cli["soggetto_ruolo_id"])
                self.assertEqual(
                    {(r["id"], r["billing_account_id"]) for r in righe},
                    {
                        (cli["istanza_utility_id"], cli["billing_account_id"]),
                        (cli["istanza_utility_id"], ba_2),
                    },
                )
                raise Annulla
        except Annulla:
            pass

    # 2. Col filtro utility resta la sola coppia, col BA e la utility giusti
    #    (con la riga «istanza + BA campione» la utility era quella del primo).
    def test_il_filtro_utility_tiene_la_sola_coppia(self):
        try:
            with transaction.atomic(), connection.cursor() as cur:
                cli, ba_2, utility_2 = _mondo_due_ba(cur)
                righe = self._cerca(cli["soggetto_ruolo_id"], utility_id=utility_2)
                self.assertEqual(
                    [(r["billing_account_id"], r["utility_id"]) for r in righe],
                    [(ba_2, utility_2)],
                )
                raise Annulla
        except Annulla:
            pass

    # 3. Il lookup soggetto+ruolo conta i BA del ruolo: con uno solo lo
    #    propone come derivato, con due lascia scegliere.
    def test_il_ruolo_conta_i_suoi_ba(self):
        from apps.anagrafiche.db.soggetti_repository import SoggettiRepository

        repo = SoggettiRepository()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                mondo, _cliente_id = _mondo_cliente(cur)
                cli = mondo["cliente"]
                riga = repo.get_ruolo_lookup_by_id(
                    soggetto_ruolo_id=cli["soggetto_ruolo_id"], emittente_ids=None,
                )
                assert riga is not None
                self.assertEqual(riga["n_billing_account"], 1)
                self.assertEqual(riga["billing_account_unico_id"], cli["billing_account_id"])
                raise Annulla
        except Annulla:
            pass
        try:
            with transaction.atomic(), connection.cursor() as cur:
                cli, _ba_2, _utility_2 = _mondo_due_ba(cur)
                riga = repo.get_ruolo_lookup_by_id(
                    soggetto_ruolo_id=cli["soggetto_ruolo_id"], emittente_ids=None,
                )
                assert riga is not None
                self.assertEqual(riga["n_billing_account"], 2)
                self.assertIsNone(riga["billing_account_unico_id"])
                raise Annulla
        except Annulla:
            pass

    # 4. Il restore per id dell'istanza conosce solo l'istanza: con due BA
    #    non ne sceglie uno (mai un `LIMIT 1`), con uno lo porta.
    def test_il_restore_dell_istanza_non_sceglie_fra_due_ba(self):
        from apps.anagrafiche.db.istanze_utility_repository import IstanzeUtilityRepository

        repo = IstanzeUtilityRepository()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                mondo, _cliente_id = _mondo_cliente(cur)
                cli = mondo["cliente"]
                riga = repo.get_lookup_by_id(cli["istanza_utility_id"], emittente_ids=None)
                assert riga is not None
                self.assertEqual(riga["billing_account_id"], cli["billing_account_id"])
                raise Annulla
        except Annulla:
            pass
        try:
            with transaction.atomic(), connection.cursor() as cur:
                cli, _ba_2, _utility_2 = _mondo_due_ba(cur)
                riga = repo.get_lookup_by_id(cli["istanza_utility_id"], emittente_ids=None)
                assert riga is not None
                self.assertEqual(riga["id"], cli["istanza_utility_id"])
                self.assertIsNone(riga["billing_account_id"])
                raise Annulla
        except Annulla:
            pass
