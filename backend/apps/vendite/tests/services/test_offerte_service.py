# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari OfferteService — perimetro D4 (step DB 1-4 atterrati).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1)  list_offerte_invalid_order_by
2)  list_offerte_search_too_short
3)  get_offerta_not_found
4)  get_offerta_ok_arricchisce_eccezioni_e_utility
5)  crea_offerta_codice_rifiutato_in_payload          [Step 5]
6)  crea_offerta_richiede_validita_dal
7)  crea_offerta_ok_setta_stato_bozza                 [Step 5: no codice]
8)  aggiorna_offerta_su_emessa_fallisce
9)  emetti_da_non_bozza_fallisce
10) registra_accettazione_da_bozza_fallisce
11) registra_rifiuto_senza_motivazione_fallisce
12) registra_rifiuto_da_bozza_fallisce_c3
13) annulla_da_emessa_fallisce_c3
14) annulla_da_bozza_ok_passa_motivazione
15) crea_eccezione_su_emessa_fallisce
16) crea_utility_duplicato_mappato
17) emetti_ok                                         [happy path]
18) registra_accettazione_ok                          [happy path]
19) registra_esito_routing_accettata                  [routing service]
20) registra_esito_routing_rifiutata_richiede_motivazione
21) registra_esito_invalido
22) aggiorna_offerta_payload_vuoto_fallisce           [fix #3]
23) aggiorna_offerta_ok                               [happy path]
24) crea_eccezione_ok                                 [happy path]
25) aggiorna_eccezione_ownership_violata              [security]
26) emetti_trigger_db_codice_propagato                [fix #1]
27) crea_revisione_da_bozza_fallisce                  [Step 7]
28) crea_revisione_da_accettata_fallisce              [Step 7]
29) crea_revisione_ok_passa_user_e_legge_nuova       [Step 7]
30) crea_revisione_trigger_db_codice_propagato        [Step 7]
31) list_revisioni_offerta_inesistente_404            [Step 7]
32) list_revisioni_ok_passa_id_al_repo                [Step 7]
33) push_a_contratto_da_emessa_fallisce               [Step 8]
34) push_a_contratto_da_bozza_fallisce                [Step 8]
35) push_a_contratto_ok_costruisce_result             [Step 8]
36) push_a_contratto_idempotenza_codice_propagato     [Step 8: pattern A]
37) push_a_contratto_con_pratica_passa_pratica_id     [Step 8]
38) push_a_contratto_pratica_id_invalido_fallisce     [Step 8]
39) crea_offerta_con_utility_inline_atomico           [refactor utility atomico]
40) crea_offerta_senza_utility_inline_non_chiama_repo [refactor utility atomico]
41) aggiorna_offerta_con_utility_inline_update_atomico  [simmetria CREATE/UPDATE]
42) aggiorna_offerta_con_utility_inline_create_atomico  [upsert: senza utility esistente]
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.db import IntegrityError

from apps.core.services.service_errors import ServiceError


def _make_offerta_dict(stato_codice: str = "BOZZA") -> dict[str, object]:
    return {
        "id": 1,
        "uid": "00000000-0000-7000-8000-000000000001",
        "codice": "OFC-TEST-0001",
        "emittente_fiscale_id": 10,
        "billing_account_id": 100,
        "istanza_utility_id": 200,
        "utility_id": 3,
        "listino_id": 50,
        "listino_versione_id": None,
        "validita_dal": "2026-06-01",
        "validita_al": None,
        "stato_doc_offerta_id": 1,
        "stato_codice_interno": stato_codice,
        "revisione_numero": 1,
        "meta": {},
    }


class OfferteServiceTests(TestCase):
    # --- lista --------------------------------------------------------

    # Scopo: order_by fuori whitelist -> ServiceError E_VENDITE_VALIDATION.
    def test_list_offerte_invalid_order_by(self):
        from apps.vendite.services.offerte_service import OfferteService

        with self.assertRaises(ServiceError) as cm:
            OfferteService().list_offerte(order_by="prezzo_segreto")
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: search con meno di 3 char rifiutato.
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_list_offerte_search_too_short(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo_cls.return_value.list_offerte.return_value = []
        with self.assertRaises(ServiceError) as cm:
            OfferteService().list_offerte(search="ab")
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")

    # --- dettaglio ----------------------------------------------------

    # Scopo: get_offerta su id inesistente -> 404 (E_VENDITE_NOT_FOUND).
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_get_offerta_not_found(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo = repo_cls.return_value
        repo.get_offerta.return_value = None
        with self.assertRaises(ServiceError) as cm:
            OfferteService().get_offerta(999)
        self.assertEqual(cm.exception.code, "E_VENDITE_NOT_FOUND")

    # Scopo: get_offerta arricchisce con eccezioni + utility + capability blob
    #        (data-driven 2026-05-26: il blob arriva da script.fn_available_actions_offerta,
    #        merged nel dict di ritorno).
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_get_offerta_ok_arricchisce_eccezioni_e_utility(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo = repo_cls.return_value
        repo.get_offerta.return_value = _make_offerta_dict()
        repo.list_eccezioni.return_value = [{"id": 7, "articolo_id": "abc"}]
        repo.get_utility.return_value = {"id": 99, "tipo_utenza_id": 5}
        repo.get_available_actions.return_value = {
            "available_actions": [
                {"key": "emetti", "target_state": "EMESSA"},
                {"key": "annulla", "target_state": "ANNULLATA"},
            ],
            "can_edit_testata": True,
            "can_edit_eccezioni": True,
            "can_push_contratto": False,
            "non_editable_fields": [],
            "stato_codice": "BOZZA",
        }

        result = OfferteService().get_offerta(1)

        self.assertEqual(result["eccezioni"], [{"id": 7, "articolo_id": "abc"}])
        self.assertEqual(result["utility"], {"id": 99, "tipo_utenza_id": 5})
        # Blob capability merged: il FE consuma da qui
        self.assertEqual(len(result["available_actions"]), 2)
        self.assertEqual(result["available_actions"][0]["key"], "emetti")
        self.assertTrue(result["can_edit_testata"])
        self.assertFalse(result["can_push_contratto"])
        self.assertEqual(result["non_editable_fields"], [])
        self.assertEqual(result["stato_codice"], "BOZZA")
        # I display fields del SELECT non vengono sovrascritti dal merge
        # (la fn ritorna `stato_codice` distinto da `stato_codice_interno`).
        self.assertEqual(result["stato_codice_interno"], "BOZZA")

    # --- create -------------------------------------------------------

    # Scopo (Step 5 atterrato 2026-05-25): `codice` in payload rifiutato come
    #        unknown_key (la whitelist lo esclude — il trigger DB lo genera).
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_crea_offerta_codice_rifiutato_in_payload(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo_cls.return_value.get_stato_id_by_codice.return_value = 1
        with self.assertRaises(ServiceError) as cm:
            OfferteService().crea_offerta({
                "codice": "OFC-MANUALE-001",  # rifiutato: lo genera il trigger DB
                "emittente_fiscale_id": 10,
                "billing_account_id": 100,
                "istanza_utility_id": 200,
                "utility_id": 3,
                "listino_id": 50,
                "validita_dal": "2026-06-01",
            })
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: payload senza `validita_dal` -> ServiceError.
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_crea_offerta_richiede_validita_dal(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo_cls.return_value.get_stato_id_by_codice.return_value = 1
        with self.assertRaises(ServiceError) as cm:
            OfferteService().crea_offerta({
                "emittente_fiscale_id": 10,
                "billing_account_id": 100,
                "istanza_utility_id": 200,
                "utility_id": 3,
                "listino_id": 50,
            })
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: create OK risolve stato BOZZA via lookup e passa al repository.
    # Step 5: `codice` NON nel payload (lo genera il trigger DB).
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_crea_offerta_ok_setta_stato_bozza(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_id_by_codice.return_value = 11
        repo.create_offerta.return_value = 1
        repo.get_offerta.return_value = _make_offerta_dict()
        repo.list_eccezioni.return_value = []
        repo.get_utility.return_value = None

        OfferteService().crea_offerta({
            "emittente_fiscale_id": 10,
            "billing_account_id": 100,
            "istanza_utility_id": 200,
            "utility_id": 3,
            "listino_id": 50,
            "validita_dal": "2026-06-01",
        })

        call = repo.create_offerta.call_args.args[0]
        self.assertEqual(call["stato_doc_offerta_id"], 11)
        # `revisione_numero` non viene passato (default DB = 1).
        self.assertNotIn("revisione_numero", call)
        # `codice` NON deve mai arrivare al repo (Step 5: trigger DB).
        self.assertNotIn("codice", call)

    # --- update / delete con guard stato ------------------------------

    # Scopo: PATCH testata su offerta EMESSA -> 422 (guard stato BOZZA).
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_aggiorna_offerta_su_emessa_fallisce(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "EMESSA"
        with self.assertRaises(ServiceError) as cm:
            OfferteService().aggiorna_offerta(1, {"validita_al": "2026-12-31"})
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")

    # --- transizioni di stato -----------------------------------------

    # Scopo: emetti da stato != BOZZA -> 422.
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_emetti_da_non_bozza_fallisce(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo_cls.return_value.get_stato_codice.return_value = "EMESSA"
        with self.assertRaises(ServiceError) as cm:
            OfferteService().emetti(1)
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: registra_accettazione da BOZZA -> 422 (richiede EMESSA).
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_registra_accettazione_da_bozza_fallisce(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo_cls.return_value.get_stato_codice.return_value = "BOZZA"
        with self.assertRaises(ServiceError) as cm:
            OfferteService().registra_accettazione(1)
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: registra_rifiuto senza motivazione -> guard non_empty_string.
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_registra_rifiuto_senza_motivazione_fallisce(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo_cls.return_value.get_stato_codice.return_value = "EMESSA"
        with self.assertRaises(ServiceError) as cm:
            OfferteService().registra_rifiuto(1, motivazione="")
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")

    # Scopo (C3): registra_rifiuto da BOZZA -> 422 (rifiuto solo da EMESSA).
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_registra_rifiuto_da_bozza_fallisce_c3(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo_cls.return_value.get_stato_codice.return_value = "BOZZA"
        with self.assertRaises(ServiceError) as cm:
            OfferteService().registra_rifiuto(1, motivazione="non valida")
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")

    # Scopo (C3): annulla da EMESSA -> 422 (annullamento solo da BOZZA).
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_annulla_da_emessa_fallisce_c3(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo_cls.return_value.get_stato_codice.return_value = "EMESSA"
        with self.assertRaises(ServiceError) as cm:
            OfferteService().annulla(1, motivazione="ripensamento interno")
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: annulla da BOZZA OK passa motivazione al repository.
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_annulla_da_bozza_ok_passa_motivazione(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "BOZZA"
        repo.get_stato_id_by_codice.return_value = 6
        repo.get_offerta.return_value = _make_offerta_dict(stato_codice="ANNULLATA")
        repo.list_eccezioni.return_value = []
        repo.get_utility.return_value = None

        OfferteService().annulla(1, motivazione="  errore impostazione  ")

        repo.update_stato.assert_called_once_with(
            1, 6, motivazione_rifiuto="errore impostazione"
        )

    # --- eccezioni ----------------------------------------------------

    # Scopo: crea eccezione su offerta EMESSA -> 422.
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_crea_eccezione_su_emessa_fallisce(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo_cls.return_value.get_stato_codice.return_value = "EMESSA"
        with self.assertRaises(ServiceError) as cm:
            OfferteService().crea_eccezione(1, {
                "articolo_id": "00000000-0000-7000-8000-000000000abc",
                "tipo_eccezione": "OVERRIDE",
                "fonte_quantita_attesa": "MANUALE",
                "prezzo_unitario": "12.50",
            })
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")

    # --- utility 1:1 --------------------------------------------------

    # Scopo: create_utility doppio (UNIQUE offerta_id) -> E_VENDITE_DUPLICATO.
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_crea_utility_duplicato_mappato(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "BOZZA"
        repo.create_utility.side_effect = IntegrityError(
            "duplicate key value violates unique constraint "
            '"uq_offerte_commerciali_utilities_offerta_id"'
        )
        with self.assertRaises(ServiceError) as cm:
            OfferteService().crea_utility(1, {
                "istanza_utility_id": 200,
                "utility_id": 3,
            })
        self.assertEqual(cm.exception.code, "E_VENDITE_DUPLICATO")

    # --- happy path -----------------------------------------------------

    # Scopo: emetti BOZZA -> EMESSA: chiama update_stato con id risolto.
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_emetti_ok(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "BOZZA"
        repo.get_stato_id_by_codice.return_value = 2
        repo.get_offerta.return_value = _make_offerta_dict("EMESSA")
        repo.list_eccezioni.return_value = []
        repo.get_utility.return_value = None

        OfferteService().emetti(1)

        repo.update_stato.assert_called_once_with(1, 2, motivazione_rifiuto=None)

    # Scopo: registra_accettazione EMESSA -> ACCETTATA, no motivazione.
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_registra_accettazione_ok(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "EMESSA"
        repo.get_stato_id_by_codice.return_value = 3
        repo.get_offerta.return_value = _make_offerta_dict("ACCETTATA")
        repo.list_eccezioni.return_value = []
        repo.get_utility.return_value = None

        OfferteService().registra_accettazione(1)

        repo.update_stato.assert_called_once_with(1, 3, motivazione_rifiuto=None)

    # Scopo: registra_esito routing: ACCETTATA delega a registra_accettazione.
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_registra_esito_routing_accettata(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "EMESSA"
        repo.get_stato_id_by_codice.return_value = 3
        repo.get_offerta.return_value = _make_offerta_dict("ACCETTATA")
        repo.list_eccezioni.return_value = []
        repo.get_utility.return_value = None

        OfferteService().registra_esito(1, esito="ACCETTATA")

        # ACCETTATA -> id stato risolto (3), no motivazione
        repo.update_stato.assert_called_once_with(1, 3, motivazione_rifiuto=None)

    # Scopo: registra_esito routing: RIFIUTATA con motivazione obbligatoria.
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_registra_esito_routing_rifiutata_richiede_motivazione(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo_cls.return_value.get_stato_codice.return_value = "EMESSA"
        with self.assertRaises(ServiceError) as cm:
            OfferteService().registra_esito(1, esito="RIFIUTATA", motivazione="")
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: registra_esito esito non valido -> 422.
    def test_registra_esito_invalido(self):
        from apps.vendite.services.offerte_service import OfferteService

        with self.assertRaises(ServiceError) as cm:
            OfferteService().registra_esito(1, esito="FORSE")
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: aggiorna_offerta payload vuoto -> 400 (no-op evitato, fix #3).
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_aggiorna_offerta_payload_vuoto_fallisce(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo_cls.return_value.get_stato_codice.return_value = "BOZZA"
        with self.assertRaises(ServiceError) as cm:
            OfferteService().aggiorna_offerta(1, {})
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: aggiorna_offerta OK su BOZZA con campi mutabili.
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_aggiorna_offerta_ok(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "BOZZA"
        repo.get_offerta.return_value = _make_offerta_dict("BOZZA")
        repo.list_eccezioni.return_value = []
        repo.get_utility.return_value = None

        OfferteService().aggiorna_offerta(1, {"validita_al": "2026-12-31"})

        repo.update_offerta.assert_called_once_with(
            1, {"validita_al": "2026-12-31"}
        )

    # Scopo: crea_eccezione OK su BOZZA passa il payload al repository.
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_crea_eccezione_ok(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "BOZZA"
        repo.create_eccezione.return_value = 77
        repo.get_eccezione.return_value = {"id": 77, "offerta_id": 1}

        payload = {
            "articolo_id": "00000000-0000-7000-8000-000000000abc",
            "tipo_eccezione": "OVERRIDE",
            "fonte_quantita_attesa": "MANUALE",
            "prezzo_unitario": "12.50",
        }
        OfferteService().crea_eccezione(1, payload)
        repo.create_eccezione.assert_called_once_with(1, payload)

    # Scopo: aggiorna_eccezione ownership cross-offerta -> 404.
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_aggiorna_eccezione_ownership_violata(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "BOZZA"
        repo.get_eccezione.return_value = {"id": 7, "offerta_id": 999}  # altra offerta!
        with self.assertRaises(ServiceError) as cm:
            OfferteService().aggiorna_eccezione(1, 7, {"attivo": False})
        self.assertEqual(cm.exception.code, "E_VENDITE_NOT_FOUND")

    # Scopo: trigger DB E_OFFERTA_* viene propagato come ServiceError con il
    #        codice originale (fix #1): non piu' rimpiazzato da E_VENDITE_VALIDATION.
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_emetti_trigger_db_codice_propagato(self, repo_cls, _atomic):
        from django.db import DatabaseError
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "BOZZA"
        repo.get_stato_id_by_codice.return_value = 2
        # Simula il P0001 sollevato dal trigger guard transizione.
        repo.update_stato.side_effect = DatabaseError(
            "E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO: "
            "listino_versione_id IS NULL su passaggio BOZZA->EMESSA"
        )
        with self.assertRaises(ServiceError) as cm:
            OfferteService().emetti(1)
        self.assertEqual(
            cm.exception.code, "E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO"
        )

    # --- revisioni (Step 6-7) ----------------------------------------

    # Scopo: crea_revisione da BOZZA -> 422 (guard applicativo EMESSA).
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_crea_revisione_da_bozza_fallisce(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo_cls.return_value.get_stato_codice.return_value = "BOZZA"
        with self.assertRaises(ServiceError) as cm:
            OfferteService().crea_revisione(1)
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: crea_revisione da ACCETTATA -> 422 (stato terminale).
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_crea_revisione_da_accettata_fallisce(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo_cls.return_value.get_stato_codice.return_value = "ACCETTATA"
        with self.assertRaises(ServiceError) as cm:
            OfferteService().crea_revisione(1)
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: crea_revisione OK da EMESSA: chiama fn DB, legge la rev.N+1
    #        via get_offerta(new_id).
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_crea_revisione_ok_passa_user_e_legge_nuova(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "EMESSA"
        repo.crea_revisione.return_value = 42  # id rev.N+1
        # get_offerta riceve l'id della NUOVA revisione.
        repo.get_offerta.return_value = _make_offerta_dict("BOZZA")
        repo.list_eccezioni.return_value = []
        repo.get_utility.return_value = None

        result = OfferteService().crea_revisione(1, user="mctit")

        repo.crea_revisione.assert_called_once_with(1, "mctit")
        repo.get_offerta.assert_called_once_with(42)
        self.assertEqual(result["stato_codice_interno"], "BOZZA")

    # Scopo: errore P0001 della fn DB (es. revisione di non-EMESSA via bypass
    #        guard applicativo) viene propagato col codice originale.
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_crea_revisione_trigger_db_codice_propagato(self, repo_cls, _atomic):
        from django.db import DatabaseError
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "EMESSA"
        repo.crea_revisione.side_effect = DatabaseError(
            "E_OFFERTA_REVISIONE_STATO_NON_AMMESSO: stato BOZZA non ammesso"
        )
        with self.assertRaises(ServiceError) as cm:
            OfferteService().crea_revisione(1)
        self.assertEqual(
            cm.exception.code, "E_OFFERTA_REVISIONE_STATO_NON_AMMESSO"
        )

    # Scopo: list_revisioni su offerta inesistente -> 404.
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_list_revisioni_offerta_inesistente_404(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo_cls.return_value.get_stato_codice.return_value = None
        with self.assertRaises(ServiceError) as cm:
            OfferteService().list_revisioni(1)
        self.assertEqual(cm.exception.code, "E_VENDITE_NOT_FOUND")

    # Scopo: list_revisioni delega al repository e ritorna la catena.
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_list_revisioni_ok_passa_id_al_repo(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "EMESSA"
        repo.list_revisioni.return_value = [
            {"id": 1, "revisione_numero": 1, "stato_codice_interno": "SUPERATA"},
            {"id": 42, "revisione_numero": 2, "stato_codice_interno": "BOZZA"},
        ]
        result = OfferteService().list_revisioni(1)
        repo.list_revisioni.assert_called_once_with(1)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[1]["revisione_numero"], 2)

    # --- push a contratto (Step 8) -----------------------------------

    # Scopo: push da EMESSA -> 422 (richiesto ACCETTATA).
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_push_a_contratto_da_emessa_fallisce(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo_cls.return_value.get_stato_codice.return_value = "EMESSA"
        with self.assertRaises(ServiceError) as cm:
            OfferteService().push_a_contratto(1)
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: push da BOZZA -> 422.
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_push_a_contratto_da_bozza_fallisce(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo_cls.return_value.get_stato_codice.return_value = "BOZZA"
        with self.assertRaises(ServiceError) as cm:
            OfferteService().push_a_contratto(1)
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: push ok costruisce OffertaPushResult con id+numero+uid del nuovo
    #        contratto letto da get_contratto_minimal.
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_push_a_contratto_ok_costruisce_result(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "ACCETTATA"
        repo.push_a_contratto.return_value = 101
        repo.get_contratto_minimal.return_value = {
            "id": 101,
            "numero": "CNT0000045",
            "uid": "11111111-2222-3333-4444-555555555555",
            "stato_codice": "DRAFT",
        }

        result = OfferteService().push_a_contratto(1)

        repo.push_a_contratto.assert_called_once_with(1, None)
        repo.get_contratto_minimal.assert_called_once_with(101)
        self.assertEqual(result, {
            "contratto_id": 101,
            "contratto_codice": "CNT0000045",
            "sorgente_uid": "11111111-2222-3333-4444-555555555555",
        })

    # Scopo (pattern A idempotenza): doppia invocazione → la fn DB solleva
    #        E_OFFERTA_CONTRATTO_GIA_GENERATO e il service lo propaga col
    #        codice originale (non rimpiazzato da E_VENDITE_VALIDATION).
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_push_a_contratto_idempotenza_codice_propagato(self, repo_cls, _atomic):
        from django.db import DatabaseError
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "ACCETTATA"
        repo.push_a_contratto.side_effect = DatabaseError(
            "E_OFFERTA_CONTRATTO_GIA_GENERATO: offerta 1 ha gia' generato il contratto"
        )
        with self.assertRaises(ServiceError) as cm:
            OfferteService().push_a_contratto(1)
        self.assertEqual(
            cm.exception.code, "E_OFFERTA_CONTRATTO_GIA_GENERATO"
        )

    # Scopo: pratica_id viene passato al repository quando valorizzato.
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_push_a_contratto_con_pratica_passa_pratica_id(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "ACCETTATA"
        repo.push_a_contratto.return_value = 101
        repo.get_contratto_minimal.return_value = {
            "id": 101, "numero": "CNT0000045",
            "uid": "uid-x", "stato_codice": "DRAFT",
        }

        OfferteService().push_a_contratto(1, pratica_id=77)

        repo.push_a_contratto.assert_called_once_with(1, 77)

    # Scopo: pratica_id <=0 o non-int viene rifiutato dal guard applicativo.
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_push_a_contratto_pratica_id_invalido_fallisce(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo_cls.return_value.get_stato_codice.return_value = "ACCETTATA"
        with self.assertRaises(ServiceError) as cm:
            OfferteService().push_a_contratto(1, pratica_id=0)
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")

    # --- refactor 2026-05-26: crea_offerta atomico con utility inline ----

    # Scopo: se il payload include `utility: {...}` come sub-oggetto, il
    #        service crea il record utility 1:1 dentro la stessa
    #        `transaction.atomic()` della testata, ereditando
    #        `istanza_utility_id`/`utility_id` dalla testata. Nessuna
    #        coppia "POST testata + PATCH utility" che potrebbe lasciare
    #        l'offerta orfana di utility in caso di fallimento intermedio.
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_crea_offerta_con_utility_inline_atomico(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_id_by_codice.return_value = 11
        repo.create_offerta.return_value = 1
        repo.get_offerta.return_value = _make_offerta_dict()
        repo.list_eccezioni.return_value = []
        repo.get_utility.return_value = {"id": 99}

        OfferteService().crea_offerta({
            "emittente_fiscale_id": 10,
            "billing_account_id": 100,
            "istanza_utility_id": 200,
            "utility_id": 3,
            "listino_id": 50,
            "validita_dal": "2026-06-01",
            "utility": {
                "tipo_utenza_id": 7,
                "classe_utenza_id": 4,
                "param_1_num": "12.5",
            },
        })

        # 1) `utility` NON deve finire nel payload testata.
        testata_call = repo.create_offerta.call_args.args[0]
        self.assertNotIn("utility", testata_call)
        # 2) `create_utility` chiamato con merge di istanza_utility_id/utility_id
        #    della testata + campi business dal sub-oggetto.
        repo.create_utility.assert_called_once()
        offerta_id_arg, utility_payload = repo.create_utility.call_args.args
        self.assertEqual(offerta_id_arg, 1)
        self.assertEqual(utility_payload["istanza_utility_id"], 200)
        self.assertEqual(utility_payload["utility_id"], 3)
        self.assertEqual(utility_payload["tipo_utenza_id"], 7)
        self.assertEqual(utility_payload["classe_utenza_id"], 4)
        self.assertEqual(utility_payload["param_1_num"], "12.5")

    # Scopo: senza sub-oggetto utility, il service NON chiama `create_utility`
    #        (zero side-effect su record satellite). Vale per i flussi
    #        anagrafici "offerta minimale" dove la utility non viene
    #        compilata in testata e si arricchisce in edit successivo.
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_crea_offerta_senza_utility_inline_non_chiama_repo(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_id_by_codice.return_value = 11
        repo.create_offerta.return_value = 1
        repo.get_offerta.return_value = _make_offerta_dict()
        repo.list_eccezioni.return_value = []
        repo.get_utility.return_value = None

        OfferteService().crea_offerta({
            "emittente_fiscale_id": 10,
            "billing_account_id": 100,
            "istanza_utility_id": 200,
            "utility_id": 3,
            "listino_id": 50,
            "validita_dal": "2026-06-01",
        })

        repo.create_utility.assert_not_called()

    # Scopo: PATCH testata con `utility: {...}` inline su offerta che HA
    #        gia' un record utility -> il service chiama `update_utility`
    #        (UPDATE atomico, niente create duplicato) filtrando il payload
    #        sui campi modificabili (istanza_utility_id/utility_id immutabili).
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_aggiorna_offerta_con_utility_inline_update_atomico(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "BOZZA"
        repo.get_offerta.return_value = _make_offerta_dict()
        repo.list_eccezioni.return_value = []
        # Utility gia' presente -> ramo update
        repo.get_utility.return_value = {"id": 99, "tipo_utenza_id": 5}

        OfferteService().aggiorna_offerta(1, {
            "valore_variazione_globale": "10.5",
            "tipo_variazione_globale": "PERCENTUALE",
            "utility": {
                "tipo_utenza_id": 7,
                "param_1_num": "42",
            },
        })

        # 1) Testata aggiornata SENZA `utility` (filtrato prima del repo).
        repo.update_offerta.assert_called_once()
        testata_call = repo.update_offerta.call_args.args[1]
        self.assertNotIn("utility", testata_call)
        self.assertEqual(testata_call["valore_variazione_globale"], "10.5")
        # 2) update_utility chiamato con id utility esistente + payload filtrato.
        repo.update_utility.assert_called_once()
        utility_id_arg, utility_payload = repo.update_utility.call_args.args
        self.assertEqual(utility_id_arg, 99)
        self.assertEqual(utility_payload, {"tipo_utenza_id": 7, "param_1_num": "42"})
        # 3) Nessun create utility (esisteva gia').
        repo.create_utility.assert_not_called()

    # Scopo: PATCH testata con `utility: {...}` inline su offerta SENZA
    #        record utility (es. creata senza utility, ora arricchita) ->
    #        il service chiama `create_utility` con merge id testata.
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_aggiorna_offerta_con_utility_inline_create_atomico(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "BOZZA"
        repo.get_offerta.return_value = _make_offerta_dict()
        repo.list_eccezioni.return_value = []
        # Utility NON presente -> ramo create
        repo.get_utility.return_value = None

        OfferteService().aggiorna_offerta(1, {
            "validita_al": "2026-12-31",
            "utility": {"tipo_utenza_id": 7},
        })

        # Testata aggiornata.
        repo.update_offerta.assert_called_once()
        # Utility creata col merge degli id derivati dalla testata.
        repo.create_utility.assert_called_once()
        offerta_id_arg, utility_payload = repo.create_utility.call_args.args
        self.assertEqual(offerta_id_arg, 1)
        self.assertEqual(utility_payload["istanza_utility_id"], 200)
        self.assertEqual(utility_payload["utility_id"], 3)
        self.assertEqual(utility_payload["tipo_utenza_id"], 7)
        repo.update_utility.assert_not_called()
