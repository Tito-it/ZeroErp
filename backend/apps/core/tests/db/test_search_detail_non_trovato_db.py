# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il dettaglio della ricerca universale dice «non c'e'» sul DATABASE
#        VERO (brief-db-codici-non-trovato-email-e-permessi §5, R-4): la
#        chiamata del repository a `script.fn_get_search_detail` risponde
#        `None` quando il soggetto, con quel ruolo, non risulta (casi 1 e 2:
#        la view ne fa il 404 `E_SEARCH_NOT_FOUND`), e la struttura con
#        `righe` — anche vuota — quando il soggetto c'e' e il filtro utility
#        restringe a zero (caso 4).
# Note: ⭐ Perche' qui e non solo in `test_search_view`: quello prova il 404 con
#       un repository FINTO, ed era verde anche quando la funzione non dava
#       mai NULL. Qui si prova la giuntura — binding per nome dei parametri
#       compreso — che il mock non vede.
#       ⚠️ Il mondo si COSTRUISCE (builder `dbops.fn_pgtap_crea_*`, contesto
#       sull'operatore dell'azienda), in transazione ANNULLATA. La riga
#       di `anagrafiche.clienti` la scrive il test: il builder si ferma al
#       billing account. Il caso 3 (cliente fuori perimetro → NULL per la RLS)
#       lo prova il pgTAP `script/test-search-scope-interno-v1` (test 19).
#       ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) SearchDetailNonTrovatoDbTests.test_soggetto_inesistente_e_none — caso 1
2) SearchDetailNonTrovatoDbTests.test_soggetto_senza_quel_ruolo_e_none — caso 2
3) SearchDetailNonTrovatoDbTests.test_filtro_utility_a_zero_e_righe_vuote — caso 4, non None
4) SearchDetailNonTrovatoDbTests.test_cliente_visibile_ha_le_sue_righe — la contro-asserzione di 3
"""
from __future__ import annotations

import unittest
import uuid

from django.db import connection

from apps.core.db.search_repository import SearchRepository
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto


class SearchDetailNonTrovatoDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto("script.fn_check_soggetto_ruolo_visibile(bigint)")

    # Scopo: un cliente visibile all'operatore di contesto: azienda con
    #        operatore, cliente fatturabile legato a quell'azienda, la riga di
    #        `anagrafiche.clienti` (i builder si fermano al billing account) e
    #        il contesto aperto sull'operatore dell'azienda.
    # ⚠️ Prima l'azienda, poi il contesto, poi il cliente (ordine dei
    #    builder da `zeroerp_app`, vedi `fn_pgtap_crea_cliente_ba`). Utility SENZA PDP: un cliente su
    #    un'utility a PDP ne pretenderebbe uno, e il PDP non c'entra qui.
    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            cur.execute(
                "SELECT soggetto_ruolo_id, auth_user_id "
                "  FROM dbops.fn_pgtap_crea_emittente_operatore()"
            )
            riga = cur.fetchone()
            assert riga is not None
            emittente_sr, operatore = riga
            # Il test gira come l'applicazione (`zeroerp_app`, soggetto alla RLS):
            # il billing account lo puo' creare solo un operatore d'azienda in
            # sessione, e il legame all'azienda lo scrive il trigger z90.
            cur.execute("SELECT script.fn_pgtap_set_contesto_operatore(%s)", [operatore])
            cur.execute(
                "SELECT * FROM dbops.fn_pgtap_crea_cliente_ba("
                "  'ricerca dettaglio',"
                "  (SELECT u.id FROM config.utilities u WHERE NOT u.richiede_pdp ORDER BY u.id LIMIT 1),"
                "  %s)",
                [emittente_sr],
            )
            riga = cur.fetchone()
            assert riga is not None
            mondo = dict(zip([c.name for c in cur.description], riga, strict=True))
            # ⛔ Cio' che il builder scrive si legge in un'istruzione SEPARATA.
            cur.execute(
                "INSERT INTO anagrafiche.clienti "
                "       (soggetto_ruolo_id, istanza_utility_id, stato_cliente_id, billing_account_id, utility_id) "
                "SELECT %s, %s, sc.id, %s, %s FROM config.stati_cliente sc WHERE sc.codice_interno = 'PR'",
                [mondo["soggetto_ruolo_id"], mondo["istanza_utility_id"],
                 mondo["billing_account_id"], mondo["utility_id"]],
            )
            cur.execute(
                "SELECT codice_interno, id FROM config.tipi_ruoli WHERE codice_interno IN ('CL', 'FO')"
            )
            ruoli = dict(cur.fetchall())
            # Un'utility che il cliente NON ha: il filtro che restringe a zero.
            cur.execute(
                "SELECT id FROM config.utilities WHERE id <> %s ORDER BY id LIMIT 1",
                [mondo["utility_id"]],
            )
            altra = cur.fetchone()
        self.assertIsNotNone(altra, "serve una seconda utility a catalogo")
        assert altra is not None
        self.soggetto_id = str(mondo["soggetto_id"])
        self.utility_id = mondo["utility_id"]
        self.altra_utility_id = altra[0]
        self.cl, self.fo = ruoli["CL"], ruoli["FO"]

    def _dettaglio(self, soggetto_id: str, tipo_ruolo_id: int, utility_id: int | None = None):
        return SearchRepository().get_search_detail(
            soggetto_id=soggetto_id, tipo_ruolo_id=tipo_ruolo_id, utility_id=utility_id,
        )

    def test_soggetto_inesistente_e_none(self) -> None:
        self.assertIsNone(self._dettaglio(str(uuid.uuid4()), self.cl))

    def test_soggetto_senza_quel_ruolo_e_none(self) -> None:
        # Il soggetto del cliente esiste, ma non e' fornitore.
        self.assertIsNone(self._dettaglio(self.soggetto_id, self.fo))

    def test_filtro_utility_a_zero_e_righe_vuote(self) -> None:
        # Il soggetto c'e': «l'utility non ne trova» e' un risultato vero.
        dettaglio = self._dettaglio(self.soggetto_id, self.cl, self.altra_utility_id)
        self.assertIsNotNone(dettaglio)
        assert dettaglio is not None
        self.assertEqual(dettaglio["righe"], [])

    def test_cliente_visibile_ha_le_sue_righe(self) -> None:
        # ⭐ Senza questa, un errore di fixture (cliente non visibile) darebbe
        #    None al test 3 — rosso per la ragione sbagliata — o righe vuote
        #    per tutti: qui si vede che il mondo c'e'.
        dettaglio = self._dettaglio(self.soggetto_id, self.cl, self.utility_id)
        self.assertIsNotNone(dettaglio)
        assert dettaglio is not None
        self.assertEqual(len(dettaglio["righe"]), 1)
