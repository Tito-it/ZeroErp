# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il dettaglio della ricerca universale dice «non c'e'» sul DATABASE
#        VERO (brief-db-codici-non-trovato-email-e-permessi §5, R-4): la
#        chiamata del repository a `script.fn_get_search_detail` risponde
#        `None` quando il soggetto, con quel ruolo, non risulta (casi 1 e 2:
#        la view ne fa il 404 `E_SEARCH_NOT_FOUND`), e la struttura con
#        `righe` — anche vuota — quando il soggetto c'e' e il filtro utility
#        restringe a zero (caso 4).
#        Dal 2026-10-10 (R-5, R-6, Q-2 dello stesso brief) prova anche:
#        - la regola unica di «il soggetto-ruolo si mostra»: un FO senza la
#          riga in `anagrafiche.fornitori` e' un «non c'e'», come un CL senza
#          clienti (colonna `config.tipi_ruoli.entita_esistenza`);
#        - il ruolo non ricercabile lo rifiuta il DB, con il suo codice 404:
#          il backend ha ritirato il proprio controllo;
#        - il binding delle due firme SENZA `p_emittente_ids` (R-5): il
#          repository chiama per nome, e qui la chiamata e' vera.
# Note: ⭐ Perche' qui e non solo in `test_search_view`: quello prova il 404 con
#       un repository FINTO, ed era verde anche quando la funzione non dava
#       mai NULL. Qui si prova la giuntura — binding per nome dei parametri
#       compreso — che il mock non vede.
#       ⚠️ Il mondo si COSTRUISCE (builder `dbops.fn_pgtap_crea_*`, contesto
#       sull'operatore dell'azienda), in transazione ANNULLATA. Il cliente lo
#       scrive `dbops.fn_pgtap_crea_cliente` (R-9): fino al 2026-10-10 la riga
#       di `anagrafiche.clienti` era una INSERT a mano qui, copia divergente di
#       quella di `anagrafiche/tests/db/test_ricerca_liste_db`. Il caso 3
#       (cliente fuori perimetro → NULL per la RLS) lo prova il pgTAP
#       `script/test-search-scope-interno-v1`.
#       ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) SearchDetailNonTrovatoDbTests.test_soggetto_inesistente_e_none — caso 1
2) SearchDetailNonTrovatoDbTests.test_soggetto_senza_quel_ruolo_e_none — caso 2
3) SearchDetailNonTrovatoDbTests.test_filtro_utility_a_zero_e_righe_vuote — caso 4, non None
4) SearchDetailNonTrovatoDbTests.test_cliente_visibile_ha_le_sue_righe — la contro-asserzione di 3
5) SearchDetailNonTrovatoDbTests.test_fornitore_senza_la_sua_riga_e_none — R-6
6) SearchDetailNonTrovatoDbTests.test_fornitore_con_la_sua_riga_ha_le_righe — la contro-asserzione di 5
7) SearchDetailNonTrovatoDbTests.test_ruolo_non_ricercabile_lo_rifiuta_il_db — Q-2, dettaglio e lista
"""
from __future__ import annotations

import unittest
import uuid

from django.db import DatabaseError, connection, transaction

from apps.core.db.search_repository import SearchRepository
from apps.core.services.db_error_fields import structured_db_error_code
from apps.core.services.error_policies import ErrorPolicyRegistry
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto


class SearchDetailNonTrovatoDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        # La sonda e' il BB della regola unica: senza, il test non ha materia.
        richiedi_db_provvisto("script.fn_predicato_soggetto_ruolo_visibile(integer,text)")

    # Scopo: un cliente visibile all'operatore di contesto (azienda con
    #        operatore, cliente fatturabile legato a quell'azienda, contesto
    #        aperto sull'operatore) e due soggetti FO costruiti: uno con la
    #        riga in `fornitori`, uno senza.
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
                "SELECT * FROM dbops.fn_pgtap_crea_cliente("
                "  'ricerca dettaglio',"
                "  (SELECT u.id FROM config.utilities u WHERE NOT u.richiede_pdp ORDER BY u.id LIMIT 1),"
                "  %s)",
                [emittente_sr],
            )
            riga = cur.fetchone()
            assert riga is not None
            mondo = dict(zip([c.name for c in cur.description], riga, strict=True))
            cur.execute(
                "SELECT codice_interno, id FROM config.tipi_ruoli "
                " WHERE codice_interno IN ('CL', 'FO')"
            )
            ruoli = dict(cur.fetchall())
            # Il ruolo NON ricercabile: lo dice il catalogo, non un id cablato.
            cur.execute(
                "SELECT id FROM config.tipi_ruoli WHERE ricerca_visibile = false ORDER BY id LIMIT 1"
            )
            non_ricercabile = cur.fetchone()
            # Un'utility che il cliente NON ha: il filtro che restringe a zero.
            cur.execute(
                "SELECT id FROM config.utilities WHERE id <> %s ORDER BY id LIMIT 1",
                [mondo["utility_id"]],
            )
            altra = cur.fetchone()
            # Due soggetti FO: «nudo» (solo il soggetto-ruolo) e «pieno» (con
            # la riga in `fornitori`, codice dal trigger, stato AT).
            fornitori: dict[str, str] = {}
            for caso in ("nudo", "pieno"):
                cur.execute(
                    "SELECT dbops.fn_pgtap_crea_soggetto_pg(%s)",
                    [f"ricerca fornitore {caso}"],
                )
                soggetto = cur.fetchone()
                assert soggetto is not None
                cur.execute(
                    "SELECT dbops.fn_pgtap_crea_soggetto_ruolo(%s, 'FO')", [soggetto[0]],
                )
                sr = cur.fetchone()
                assert sr is not None
                if caso == "pieno":
                    cur.execute(
                        "INSERT INTO anagrafiche.fornitori (soggetto_ruolo_id, stato_fornitore_id) "
                        "SELECT %s, sf.id FROM config.stati_fornitore sf "
                        " WHERE sf.codice_interno = 'AT'",
                        [sr[0]],
                    )
                    self.assertEqual(cur.rowcount, 1, "stato fornitore AT assente dal catalogo")
                fornitori[caso] = str(soggetto[0])
        self.assertIsNotNone(altra, "serve una seconda utility a catalogo")
        self.assertIsNotNone(non_ricercabile, "serve un tipo ruolo non ricercabile a catalogo")
        assert altra is not None and non_ricercabile is not None
        self.soggetto_id = str(mondo["soggetto_id"])
        self.utility_id = mondo["utility_id"]
        self.altra_utility_id = altra[0]
        self.cl, self.fo = ruoli["CL"], ruoli["FO"]
        self.non_ricercabile = non_ricercabile[0]
        self.fornitore_nudo = fornitori["nudo"]
        self.fornitore_pieno = fornitori["pieno"]

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

    def test_fornitore_senza_la_sua_riga_e_none(self) -> None:
        # R-6: il soggetto-ruolo FO c'e', la riga di `fornitori` no. Prima del
        # 2026-10-10 rispondeva `righe: []`; ora e' un «non c'e'», come il CL
        # senza clienti.
        self.assertIsNone(self._dettaglio(self.fornitore_nudo, self.fo))

    def test_fornitore_con_la_sua_riga_ha_le_righe(self) -> None:
        # La contro-asserzione del 5: il None di prima viene dalla riga che
        # manca, non da un fornitore che il dettaglio non sa leggere.
        dettaglio = self._dettaglio(self.fornitore_pieno, self.fo)
        self.assertIsNotNone(dettaglio)
        assert dettaglio is not None
        self.assertEqual(len(dettaglio["righe"]), 1)

    def test_ruolo_non_ricercabile_lo_rifiuta_il_db(self) -> None:
        # Q-2: il controllo `ricerca_visibile` non e' piu' nel backend. Lo fa
        # il BB del DB, per il dettaglio e per la lista, con un codice 404.
        chiamate = {
            "dettaglio": lambda: self._dettaglio(self.soggetto_id, self.non_ricercabile),
            "lista": lambda: SearchRepository().search_soggetti(
                search_term="ricerca", tipo_ruolo_id=self.non_ricercabile,
            ),
        }
        for nome, chiama in chiamate.items():
            with self.subTest(chiamata=nome):
                with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
                    chiama()
                codice = structured_db_error_code(ctx.exception)
                self.assertEqual(codice, "E_TIPO_RUOLO_NON_RICERCABILE")
                assert codice is not None
                self.assertEqual(ErrorPolicyRegistry.resolve(codice).http_status, 404)
