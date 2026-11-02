# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il restore per id dei due lookup cross-dominio — istanze utility e
#        contesto soggetto/ruolo — risponde SOLO nello scope emittente del
#        chiamante, lo stesso della ricerca per testo. Provato sul DATABASE
#        VERO, col mondo costruito.
# Note: ⛔ Il difetto che presidia non da' errore (D10-bis di
#       migliorie-generali-BE-FE-da-test-valutazione, 2026-10-08): le due view
#       hanno `skip_area_check`, e il repository dichiarava «lo scope lo gestisce
#       l'endpoint chiamante» — che non lo gestiva. Con un id si leggevano nome,
#       CF, indirizzo e PDP di soggetti di QUALUNQUE emittente, con un 200.
#       ⚠️ «Altro emittente» e' un array con un id che non e' un emittente
#       (`-1`): e' l'operatore scoped altrove, senza fabbricare una seconda
#       azienda. Il caso costruito e' quello del modello, non dei dati.
#       ⚠️ Il mondo si COSTRUISCE (builder `dbops.fn_pgtap_crea_*`), in
#       transazione ANNULLATA. Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) LookupRestoreScopeDbTests.test_istanza_solo_nel_proprio_scope
2) LookupRestoreScopeDbTests.test_ruolo_cliente_solo_nel_proprio_scope
3) LookupRestoreScopeDbTests.test_soggetto_cliente_solo_nel_proprio_scope
4) LookupRestoreScopeDbTests.test_soggetto_senza_ruolo_cliente_resta_visibile
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.anagrafiche.tests.db.test_ricerca_liste_db import _mondo_cliente
from apps.core.tests.db_e2e import Annulla, richiedi_db_provvisto

# Un operatore scoped su un emittente che non e' quello del mondo costruito.
_ALTRO_EMITTENTE = [-1]


class LookupRestoreScopeDbTests(unittest.TestCase):

    def setUp(self):
        richiedi_db_provvisto()

    # Scopo: esegue `prova(cur, mondo)` dentro un mondo cliente costruito, in
    #        una transazione che si annulla sempre.
    def _nel_mondo(self, prova) -> None:
        try:
            with transaction.atomic(), connection.cursor() as cur:
                mondo, _cliente_id = _mondo_cliente(cur)
                prova(cur, mondo)
                raise Annulla
        except Annulla:
            pass

    # 1. L'istanza del cliente: la vede il suo emittente e il bypass, non un altro.
    def test_istanza_solo_nel_proprio_scope(self):
        from apps.anagrafiche.db.istanze_utility_repository import IstanzeUtilityRepository

        def prova(_cur, mondo):
            repo = IstanzeUtilityRepository()
            istanza_id = mondo["cliente"]["istanza_utility_id"]
            proprio = [mondo["emittente_soggetto_ruolo_id"]]
            self.assertIsNotNone(repo.get_lookup_by_id(istanza_id, emittente_ids=proprio))
            self.assertIsNotNone(repo.get_lookup_by_id(istanza_id, emittente_ids=None))
            self.assertIsNone(repo.get_lookup_by_id(istanza_id, emittente_ids=_ALTRO_EMITTENTE))

        self._nel_mondo(prova)

    # 2. La riga ruolo CL: stessa regola della ricerca (`_RUOLO_CL_SCOPE_SQL`).
    def test_ruolo_cliente_solo_nel_proprio_scope(self):
        from apps.anagrafiche.db.soggetti_repository import SoggettiRepository

        def prova(_cur, mondo):
            repo = SoggettiRepository()
            sr_id = mondo["cliente"]["soggetto_ruolo_id"]
            proprio = [mondo["emittente_soggetto_ruolo_id"]]
            self.assertIsNotNone(repo.get_ruolo_lookup_by_id(soggetto_ruolo_id=sr_id, emittente_ids=proprio))
            self.assertIsNotNone(repo.get_ruolo_lookup_by_id(soggetto_ruolo_id=sr_id, emittente_ids=None))
            self.assertIsNone(repo.get_ruolo_lookup_by_id(soggetto_ruolo_id=sr_id, emittente_ids=_ALTRO_EMITTENTE))

        self._nel_mondo(prova)

    # 3. La riga «senza ruolo» di un soggetto che E' cliente: chi non vede il
    #    cliente non ricostruisce nemmeno il soggetto (la chiave alternativa non
    #    e' una porta laterale).
    def test_soggetto_cliente_solo_nel_proprio_scope(self):
        from apps.anagrafiche.db.soggetti_repository import SoggettiRepository

        def prova(cur, mondo):
            cur.execute(
                "SELECT soggetto_id::text FROM anagrafiche.soggetti_ruoli WHERE id = %s",
                [mondo["cliente"]["soggetto_ruolo_id"]],
            )
            soggetto_id = cur.fetchone()[0]
            repo = SoggettiRepository()
            proprio = [mondo["emittente_soggetto_ruolo_id"]]
            self.assertIsNotNone(repo.get_ruolo_lookup_by_id(soggetto_id=soggetto_id, emittente_ids=proprio))
            self.assertIsNone(repo.get_ruolo_lookup_by_id(soggetto_id=soggetto_id, emittente_ids=_ALTRO_EMITTENTE))

        self._nel_mondo(prova)

    # 4. Il soggetto dell'emittente ha ruoli, ma nessuno CL: lo scope riguarda
    #    il solo ruolo cliente, come nella ricerca — resta visibile a chiunque.
    #    ⚠️ Senza questo test la clausola «nessun ruolo fuori scope» potrebbe
    #    degenerare in «nessun ruolo» e il test 3 resterebbe verde.
    def test_soggetto_senza_ruolo_cliente_resta_visibile(self):
        from apps.anagrafiche.db.soggetti_repository import SoggettiRepository

        def prova(cur, mondo):
            cur.execute(
                "SELECT soggetto_id::text FROM anagrafiche.soggetti_ruoli WHERE id = %s",
                [mondo["emittente_soggetto_ruolo_id"]],
            )
            soggetto_id = cur.fetchone()[0]
            cur.execute(
                "SELECT count(*) FROM anagrafiche.soggetti_ruoli sr "
                "  JOIN config.tipi_ruoli tr ON tr.id = sr.tipo_ruolo_id "
                " WHERE sr.soggetto_id = %s::uuid AND COALESCE(tr.codice_interno, tr.codice) = 'CL'",
                [soggetto_id],
            )
            self.assertEqual(cur.fetchone()[0], 0, "premessa: il soggetto emittente non e' cliente")
            repo = SoggettiRepository()
            self.assertIsNotNone(
                repo.get_ruolo_lookup_by_id(soggetto_id=soggetto_id, emittente_ids=_ALTRO_EMITTENTE),
            )

        self._nel_mondo(prova)
