# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari OfferteService — perimetro D4 (step DB 1-4 atterrati).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1)  list_offerte_invalid_order_by
2)  list_offerte_search_corta_non_e_un_errore
3)  get_offerta_not_found
4)  get_offerta_ok_arricchisce_eccezioni_e_utility
5)  crea_offerta_codice_rifiutato_in_payload          [Step 5]
6)  crea_offerta_richiede_validita_dal
7)  crea_offerta_ok_setta_stato_bozza                 [Step 5: no codice]
8)  aggiorna_offerta_su_emessa_decide_il_db + aggiorna_offerta_utility_su_emessa_decide_il_db
9)  emetti_secondo_emetti_lo_rifiuta_il_verbo       [§13.6: lo stato lo giudica il verbo]
    (+ emetti_offerta_inesistente_e_404)
10) registra_accettazione_da_bozza_la_rifiuta_il_db
11) registra_rifiuto_senza_motivazione_la_rifiuta_il_db (+ motivazione_non_stringa_e_400)
12) registra_rifiuto_da_bozza_lo_rifiuta_il_db_c3
13) annulla_da_emessa_lo_rifiuta_il_db (+ annulla_da_accettata_arriva_al_db,
    annulla_offerta_inesistente_e_404)
14) annulla_da_bozza_ok_passa_motivazione (+ annulla_revisione_chiede_e_poi_riceve_la_conferma,
    annulla_corpo_malformato_e_400, get_legami_legge_prima_la_testata)
15) crea_eccezione_su_emessa_fallisce
16) crea_utility_duplicato_mappato
17) emetti_ok                                         [happy path]
18) registra_accettazione_ok                          [happy path]
19) registra_esito_routing_accettata                  [routing service]
    (+ registra_esito_accettata_con_motivazione_e_400)
20) registra_esito_routing_rifiutata_motivazione_al_verbo
21) registra_esito_invalido
22) aggiorna_offerta_payload_vuoto_fallisce           [fix #3]
23) aggiorna_offerta_ok                               [happy path]
24) crea_eccezione_ok                                 [happy path]
25) aggiorna_eccezione_ownership_violata              [security]
26) emetti_trigger_db_codice_propagato                [fix #1]
27) crea_revisione_stato_lo_dice_il_db                [Step 7, §13.6]
28) crea_revisione_offerta_inesistente_404            [Step 7, §13.6]
29) crea_revisione_ok_passa_user_e_legge_nuova       [Step 7]
30) crea_revisione_trigger_db_codice_propagato        [Step 7]
31) list_revisioni_offerta_inesistente_404            [Step 7]
32) list_revisioni_ok_passa_id_al_repo                [Step 7]
33) push_a_contratto_stato_lo_dice_il_db              [Step 8, §13.6]
34) push_a_contratto_offerta_inesistente_404          [Step 8, §13.6]
35) push_a_contratto_ok_costruisce_result             [Step 8]
36) push_a_contratto_idempotenza_codice_propagato     [Step 8: pattern A]
37) push_a_contratto_con_pratica_passa_pratica_id     [Step 8]
38) push_a_contratto_pratica_id_invalido_fallisce     [Step 8]
39) crea_offerta_con_utility_inline_atomico           [refactor utility atomico]
40) crea_offerta_senza_utility_inline_non_chiama_repo [refactor utility atomico]
41) aggiorna_offerta_con_utility_inline_update_atomico  [simmetria CREATE/UPDATE]
42) aggiorna_offerta_con_utility_inline_create_atomico  [upsert: senza utility esistente]
43) get_offerta_capability_db_error_graceful_fallback  [hardening fn DB rotta]
44) crea_eccezione_articolo_composito_invoca_init       [BoM simmetria contratti]
45) crea_eccezione_articolo_atomico_non_invoca_init     [BoM no-op]
46) crea_eccezione_composito_senza_emittente_fallisce   [BoM guard]
47) preview_componenti_eccezione_ok                     [BoM preview]
48) preview_componenti_eccezione_offerta_not_found      [BoM preview 404]
49) list_componenti_eccezione_ownership_violata         [BoM security]
50) update_componente_eccezione_payload_vuoto_fallisce  [BoM whitelist]
50b) update_componente_eccezione_campi_del_workflow_rifiutati [BoM auto-approvazione L3]
51) update_componente_eccezione_ownership_violata       [BoM security]
52) delete_componente_eccezione_ok                      [BoM happy path]

Gate prezzo L1/L2/L3 (refactor-prezzi 2026-06-01):
53) crea_eccezione_invoca_validate_l1_componenti        [L1 wiring]
54) crea_eccezione_override_invoca_gate                 [L2/L3 wiring]
55) crea_eccezione_esclusione_non_invoca_gate           [no gate su ESCLUSIONE]
56) apply_gate_eccezione_l3_pending_setta_stato         [L3 PENDING + pratica]
57) resolve_override_prezzo_offerta_skip_senza_listino  [guard listino None]
58) apply_gate_eccezione_preserva_meta_esistente        [fallback_meta no-clobber]

Scritture sul BB core (2026-09-26):
59) aggiorna_offerta_meta_stringa_json_diventa_dict      [meta normalizzato nel service]
60) aggiorna_offerta_meta_null_diventa_oggetto_vuoto     [NOT NULL DEFAULT '{}']
61) crea_eccezione_meta_non_oggetto_e_400                [400, repo non chiamato]
62) aggiorna_utility_meta_non_oggetto_e_400              [400, repo non chiamato]
63) aggiorna_offerta_utility_inline_chiave_estranea_e_400 [niente scarto silenzioso]
64) aggiorna_offerta_cambio_cliente_non_riscrive_la_scheda [R-BE-6: la rifa' il DB]
65) aggiorna_offerta_stesso_cliente_applica_la_scheda    [id come testo: non e' un cambio]
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.db import DatabaseError, IntegrityError

from apps.core.services.service_errors import ServiceError
from apps.core.tests._helpers.modello_documento_mockato import ModelloDocumentoMockatoMixin


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


# Il dettaglio porta i `contatori` dei badge (BB `contatori_documento`), che
# contano le note sul DB: qui si sostituisce, o ogni test che passa dal
# dettaglio farebbe una query vera senza dirlo.
_SENZA_CONTATORI_DB = patch(
    "apps.vendite.services.offerte_service.contatori_documento",
    new=lambda *_a, **_k: {"note": 0},
)


@_SENZA_CONTATORI_DB
class OfferteServiceTests(ModelloDocumentoMockatoMixin, TestCase):
    # --- lista --------------------------------------------------------

    # Scopo: order_by fuori whitelist -> ServiceError E_VENDITE_VALIDATION.
    def test_list_offerte_invalid_order_by(self):
        from apps.vendite.services.offerte_service import OfferteService

        with self.assertRaises(ServiceError) as cm:
            OfferteService().list_offerte(order_by="prezzo_segreto")
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: search sotto soglia NON e' un errore (fino al 2026-09-23 era un
    #        400): il termine arriva al repository, dove la soglia la applica
    #        il BB `add_ricerca_full_condition` come per tutte le liste.
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_list_offerte_search_corta_non_e_un_errore(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo = repo_cls.return_value
        repo.list_offerte.return_value = []
        repo.count_offerte.return_value = 0
        self.assertEqual(OfferteService().list_offerte(search="ab"), ([], 0))
        self.assertEqual(repo.list_offerte.call_args.kwargs["search"], "ab")

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
    #        e dal 2026-09-23 viaggia SOTTO `capabilities`, non fuso nel dettaglio).
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
        # Blob capability intatto sotto la sua chiave: il FE consuma da qui
        caps = result["capabilities"]
        self.assertEqual(caps, repo.get_available_actions.return_value)
        self.assertEqual(len(caps["available_actions"]), 2)
        self.assertEqual(caps["available_actions"][0]["key"], "emetti")
        self.assertTrue(caps["can_edit_testata"])
        self.assertFalse(caps["can_push_contratto"])
        # Nessuna chiave del blob sale nella testata: i display fields del
        # SELECT restano i loro.
        for chiave in caps:
            self.assertNotIn(chiave, result)
        self.assertEqual(result["stato_codice_interno"], "BOZZA")

    # --- create -------------------------------------------------------

    # Scopo (Step 5 atterrato 2026-05-25): `codice` in payload rifiutato come
    #        unknown_key (la whitelist lo esclude — il trigger DB lo genera).
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_crea_offerta_codice_rifiutato_in_payload(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

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
    def test_crea_offerta_ok_non_passa_lo_stato(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
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
        # Lo stato non si passa: lo mette il DB, lo stato iniziale del
        # vocabolario (brief-modello-documento-vendita P-2).
        self.assertNotIn("stato_doc_offerta_id", call)
        # `revisione_numero` non viene passato (default DB = 1).
        self.assertNotIn("revisione_numero", call)
        # `codice` NON deve mai arrivare al repo (Step 5: trigger DB).
        self.assertNotIn("codice", call)
        # Lo slot di default lo riempie il DB, nella transazione della
        # creazione (R-BE-1).
        repo.riempi_indirizzo_default.assert_called_once_with(1)

    # --- update / delete con guard stato ------------------------------

    # Scopo: PATCH testata su offerta EMESSA: quali colonne si cambiano lo
    #        dice il lock di testata del DB (brief-db-testata-dopo-emissione,
    #        D-0). Il service non ha piu' un «solo in BOZZA» e passa la scrittura.
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_aggiorna_offerta_su_emessa_decide_il_db(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "EMESSA"
        OfferteService().aggiorna_offerta(1, {"meta": {"nota": "x"}})
        repo.update_offerta.assert_called_once()
        repo.get_available_actions.assert_called()  # il dettaglio di ritorno

    # Scopo: la fornitura su un'offerta emessa: lo stato lo giudica il lock
    #        «solo in bozza» dei satelliti a DB (`E_DOC_DATI_COLLEGATI_NON_BOZZA`,
    #        brief-db-testata-dopo-emissione §11, R-BE-6). Il service non legge
    #        piu' `can_edit_utility` e passa la scrittura.
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_aggiorna_offerta_utility_su_emessa_decide_il_db(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "EMESSA"
        repo.get_utility.return_value = {"id": 7}
        OfferteService().aggiorna_offerta(
            1, {"meta": {"nota": "x"}, "utility": {"param_2_txt": "y"}},
        )
        repo.update_offerta.assert_called_once()
        repo.update_utility.assert_called_once()

    # --- transizioni di stato -----------------------------------------

    # Scopo: «Emetti» su un'offerta gia' emessa: lo stato di partenza lo
    #        giudica il verbo (E_DOC_GIA_NELLO_STATO), non il service. ⛔ Fino
    #        al 2026-10-26 lo anticipava un «solo da BOZZA» Python
    #        (brief-modello-documento-vendita §13.6 punto 4).
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_emetti_secondo_emetti_lo_rifiuta_il_verbo(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        self.emissione_del_documento("EMESSA")
        repo.cambia_stato.side_effect = DatabaseError(
            "E_DOC_GIA_NELLO_STATO: Il documento e' gia' nello stato EMESSA",
        )
        with self.assertRaises(ServiceError) as cm:
            OfferteService().emetti(1)
        self.assertEqual(cm.exception.code, "E_DOC_GIA_NELLO_STATO")
        # Un rifiuto che non e' della motivazione non accende il suo campo.
        self.assertIsNone(cm.exception.fields)
        # Regola del 1: nessun lettore davanti al verbo.
        repo.get_stato_codice.assert_not_called()

    # Scopo: «Emetti» su un'offerta che non c'e' (o fuori perimetro): il 404 e'
    #        del verbo, col suo codice (regola del 1, 2026-10-27).
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_emetti_offerta_inesistente_e_404(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        self.emissione_del_documento("EMESSA")
        repo_cls.return_value.cambia_stato.side_effect = DatabaseError(
            "E_OFFERTA_NON_TROVATA: offerta 1",
        )
        with self.assertRaises(ServiceError) as cm:
            OfferteService().emetti(1)
        self.assertEqual(cm.exception.code, "E_OFFERTA_NON_TROVATA")
        repo_cls.return_value.get_stato_codice.assert_not_called()

    # Scopo: registra_accettazione da BOZZA: la matrice la rifiuta al verbo
    #        (E_OFFERTA_TRANSIZIONE_NON_AMMESSA), col suo codice.
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_registra_accettazione_da_bozza_la_rifiuta_il_db(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.cambia_stato.side_effect = DatabaseError(
            "E_OFFERTA_TRANSIZIONE_NON_AMMESSA: BOZZA -> ACCETTATA",
        )
        with self.assertRaises(ServiceError) as cm:
            OfferteService().registra_accettazione(1)
        self.assertEqual(cm.exception.code, "E_OFFERTA_TRANSIZIONE_NON_AMMESSA")
        repo.cambia_stato.assert_called_once_with(1, "ACCETTATA", None)

    # Scopo: registra_rifiuto senza motivazione: la motivazione vuota arriva al
    #        verbo come assente, e l'obbligo lo dice la riga del passaggio
    #        (E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA, O-3). ⛔ Fino al 2026-10-26 era
    #        `guard_non_empty_string` qui.
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_registra_rifiuto_senza_motivazione_la_rifiuta_il_db(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.cambia_stato.side_effect = DatabaseError(
            "E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA: serve una motivazione",
        )
        with self.assertRaises(ServiceError) as cm:
            OfferteService().registra_rifiuto(1, motivazione="   ")
        self.assertEqual(cm.exception.code, "E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA")
        # Il verbo nomina la colonna (`motivazione_rifiuto`): al client va il
        # campo della richiesta.
        self.assertEqual(cm.exception.fields, ("motivazione",))
        repo.cambia_stato.assert_called_once_with(1, "RIFIUTATA", None)

    # Scopo: una motivazione che non e' una stringa e' un 400 col campo, prima
    #        del verbo (non un 500 dal cast del DB).
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_registra_rifiuto_motivazione_non_stringa_e_400(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        with self.assertRaises(ServiceError) as cm:
            OfferteService().registra_rifiuto(1, motivazione=42)
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")
        repo_cls.return_value.cambia_stato.assert_not_called()

    # Scopo (C3): registra_rifiuto da BOZZA: la matrice lo rifiuta al verbo.
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_registra_rifiuto_da_bozza_lo_rifiuta_il_db_c3(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.cambia_stato.side_effect = DatabaseError(
            "E_OFFERTA_TRANSIZIONE_NON_AMMESSA: BOZZA -> RIFIUTATA",
        )
        with self.assertRaises(ServiceError) as cm:
            OfferteService().registra_rifiuto(1, motivazione="  non valida ")
        self.assertEqual(cm.exception.code, "E_OFFERTA_TRANSIZIONE_NON_AMMESSA")
        repo.cambia_stato.assert_called_once_with(1, "RIFIUTATA", "non valida")

    # Scopo: annulla da EMESSA -> il rifiuto e' del DB (transizione non
    #        ammessa) e arriva col SUO codice. ⛔ Fino al 2026-10-21 il service
    #        lo anticipava con un «solo da BOZZA» suo, che avrebbe rifiutato
    #        anche l'annullo da ACCETTATA ammesso dal DB
    #        (brief-db-offerta-emissione-ed-erogazione H-R3).
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_annulla_da_emessa_lo_rifiuta_il_db(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "EMESSA"
        repo.annulla.side_effect = DatabaseError(
            "E_OFFERTA_TRANSIZIONE_NON_AMMESSA: EMESSA -> ANNULLATA",
        )
        with self.assertRaises(ServiceError) as cm:
            OfferteService().annulla(1, motivazione="ripensamento interno")
        self.assertEqual(cm.exception.code, "E_OFFERTA_TRANSIZIONE_NON_AMMESSA")
        repo.annulla.assert_called_once()

    # Scopo: annulla da ACCETTATA: il service arriva al verbo d'annullo
    #        (nessuno stato di partenza ne' stato d'annullo scritto qui), senza
    #        dichiarazione al primo tentativo.
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_annulla_da_accettata_arriva_al_db(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "ACCETTATA"
        repo.get_offerta.return_value = _make_offerta_dict('ANNULLATA')
        repo.list_eccezioni.return_value = []
        repo.get_utility.return_value = None

        OfferteService().annulla(1, motivazione="il cliente ci ripensa")

        repo.annulla.assert_called_once_with(1, "il cliente ci ripensa", None)

    # Scopo: annulla di un'offerta che non c'e' (o fuori perimetro): il 404 e'
    #        del verbo, col suo codice (regola del 1, 2026-10-27).
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_annulla_offerta_inesistente_e_404(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo_cls.return_value.annulla.side_effect = DatabaseError(
            "E_OFFERTA_NON_TROVATA: offerta 1",
        )
        with self.assertRaises(ServiceError) as cm:
            OfferteService().annulla(1, motivazione="x")
        self.assertEqual(cm.exception.code, "E_OFFERTA_NON_TROVATA")
        repo_cls.return_value.get_stato_codice.assert_not_called()

    # Scopo: annulla da BOZZA OK passa la motivazione (normalizzata) al verbo.
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_annulla_da_bozza_ok_passa_motivazione(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "BOZZA"
        repo.get_offerta.return_value = _make_offerta_dict('ANNULLATA')
        repo.list_eccezioni.return_value = []
        repo.get_utility.return_value = None

        OfferteService().annulla(1, motivazione="  errore impostazione  ")

        repo.annulla.assert_called_once_with(1, "errore impostazione", None)

    # Scopo (O-4): l'annullo di una revisione senza conferma lo rifiuta il DB
    #        con E_DOC_ANNULLO_CON_LEGAMI (`confirm_and_retry`), e il codice
    #        arriva com'e'; la conferma dichiara i legami visti, e il verbo li
    #        riceve.
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_annulla_revisione_chiede_e_poi_riceve_la_conferma(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "BOZZA"
        repo.get_offerta.return_value = _make_offerta_dict('ANNULLATA')
        repo.list_eccezioni.return_value = []
        repo.get_utility.return_value = None
        repo.annulla.side_effect = [
            DatabaseError("E_DOC_ANNULLO_CON_LEGAMI: Annullando OFC-2 si riaprono 1 legami"),
            1,
        ]
        with self.assertRaises(ServiceError) as cm:
            OfferteService().annulla(1, motivazione="errore")
        self.assertEqual(cm.exception.code, "E_DOC_ANNULLO_CON_LEGAMI")

        OfferteService().annulla(1, motivazione="errore", legami_confermati=1)
        self.assertEqual(repo.annulla.call_args.args, (1, "errore", 1))

    # Scopo: la dichiarazione non intera e la motivazione non stringa sono un
    #        400 col campo, prima del verbo.
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_annulla_corpo_malformato_e_400(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        for kwargs in (
            {"motivazione": "x", "legami_confermati": "tanti"},
            {"motivazione": ["x"]},
        ):
            with self.subTest(**{k: repr(v) for k, v in kwargs.items()}):
                with self.assertRaises(ServiceError) as cm:
                    OfferteService().annulla(1, **kwargs)
                self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")
        repo_cls.return_value.annulla.assert_not_called()

    # Scopo: i legami per la finestra: prima la testata (404 del dominio),
    #        poi il BB col codice della sorgente.
    @patch("apps.vendite.services.offerte_service.legami_del_documento")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_get_legami_legge_prima_la_testata(self, repo_cls, legami):
        from apps.vendite.services.offerte_service import OfferteService

        repo_cls.return_value.get_stato_codice.return_value = None
        with self.assertRaises(ServiceError) as cm:
            OfferteService().get_legami(1)
        self.assertEqual(cm.exception.code, "E_VENDITE_NOT_FOUND")
        legami.assert_not_called()

        repo_cls.return_value.get_stato_codice.return_value = "BOZZA"
        legami.return_value = {"legami": 1}
        self.assertEqual(OfferteService().get_legami(1), {"legami": 1})
        legami.assert_called_once_with("OFFERTA_COMMERCIALE", 1)

    # --- eccezioni ----------------------------------------------------

    # Scopo: crea eccezione su offerta EMESSA -> il rifiuto e' del DB
    #        (`trgfn_doc_righe_lock_fuori_bozza`) e arriva col SUO codice,
    #        `E_RIGA_DOC_NON_BOZZA` (409), come per le righe degli altri
    #        documenti. Fino al 2026-10-13 il service lo anticipava con
    #        `E_VENDITE_VALIDATION` (422) e una frase generica.
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_crea_eccezione_su_emessa_fallisce(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "EMESSA"
        repo.create_eccezione.side_effect = DatabaseError(
            "E_RIGA_DOC_NON_BOZZA: Offerta OFF-1 non e' piu' in bozza (stato EMESSA)",
        )
        with self.assertRaises(ServiceError) as cm:
            OfferteService().crea_eccezione(1, {
                "articolo_id": "00000000-0000-7000-8000-000000000abc",
                "tipo_eccezione": "OVERRIDE",
                "fonte_quantita_attesa": "MANUALE",
                "prezzo_unitario": "12.50",
            })
        self.assertEqual(cm.exception.code, "E_RIGA_DOC_NON_BOZZA")

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

    # Scopo: emetti BOZZA -> EMESSA: un solo cambio stato, dal verbo. ⛔ Nessuna
    #        scrittura di `listino_versione_id` dal service: la congela il guard
    #        DB nella stessa scrittura (brief-db-offerta-emissione-ed-erogazione
    #        A-R1). Fino al 2026-10-07 il service la fissava prima, in Python.
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_emetti_ok(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        # Lo stato di emissione dal vocabolario (§8.11 B-4), non `StatoOfferta.EMESSA`.
        self.emissione_del_documento("EMESSA")
        repo.get_offerta.return_value = _make_offerta_dict('EMESSA')
        repo.list_eccezioni.return_value = []
        repo.get_utility.return_value = None

        OfferteService().emetti(1)

        repo.update_offerta.assert_not_called()
        repo.cambia_stato.assert_called_once_with(1, "EMESSA", None)
        self.modello_documento.stato_di_emissione.assert_called_once_with("vendite.offerte_commerciali")

    # Scopo: registra_accettazione EMESSA -> ACCETTATA, no motivazione.
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_registra_accettazione_ok(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_offerta.return_value = _make_offerta_dict('ACCETTATA')
        repo.list_eccezioni.return_value = []
        repo.get_utility.return_value = None

        OfferteService().registra_accettazione(1)

        repo.cambia_stato.assert_called_once_with(1, "ACCETTATA", None)

    # Scopo: registra_esito routing: ACCETTATA delega a registra_accettazione.
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_registra_esito_routing_accettata(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_offerta.return_value = _make_offerta_dict('ACCETTATA')
        repo.list_eccezioni.return_value = []
        repo.get_utility.return_value = None

        # Vuota vale assente: e' cio' che manda il dialog senza il campo.
        OfferteService().registra_esito(1, esito="ACCETTATA", motivazione="  ")

        # ACCETTATA -> il codice al verbo, nessuna motivazione.
        repo.cambia_stato.assert_called_once_with(1, "ACCETTATA", None)

    # Scopo: una motivazione con ACCETTATA e' un 400 col campo, non si perde in
    #        silenzio: l'accettazione non ha una colonna che la tenga.
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_registra_esito_accettata_con_motivazione_e_400(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService
        from apps.core.services.error_translator import ErrorTranslator

        with self.assertRaises(ServiceError) as cm:
            OfferteService().registra_esito(1, esito="ACCETTATA", motivazione="ottimo prezzo")
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")
        self.assertEqual(ErrorTranslator.to_api_error(cm.exception).fields, ("motivazione",))
        repo_cls.return_value.cambia_stato.assert_not_called()

    # Scopo: registra_esito routing: RIFIUTATA porta la motivazione al verbo
    #        (assente = None); l'obbligo lo dice il DB.
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_registra_esito_routing_rifiutata_motivazione_al_verbo(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_offerta.return_value = _make_offerta_dict('RIFIUTATA')
        repo.list_eccezioni.return_value = []
        repo.get_utility.return_value = None

        OfferteService().registra_esito(1, esito="RIFIUTATA", motivazione=" prezzo alto ")
        repo.cambia_stato.assert_called_once_with(1, "RIFIUTATA", "prezzo alto")

        repo.cambia_stato.reset_mock()
        repo.cambia_stato.side_effect = DatabaseError(
            "E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA: serve una motivazione",
        )
        with self.assertRaises(ServiceError) as cm:
            OfferteService().registra_esito(1, esito="RIFIUTATA")
        self.assertEqual(cm.exception.code, "E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA")
        repo.cambia_stato.assert_called_once_with(1, "RIFIUTATA", None)

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
        # Lo stato di emissione dal vocabolario (§8.11 B-4), non `StatoOfferta.EMESSA`.
        self.emissione_del_documento("EMESSA")
        # Simula il P0001 sollevato dal trigger guard transizione.
        repo.cambia_stato.side_effect = DatabaseError(
            "E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO: "
            "listino_versione_id IS NULL su passaggio BOZZA->EMESSA"
        )
        with self.assertRaises(ServiceError) as cm:
            OfferteService().emetti(1)
        self.assertEqual(
            cm.exception.code, "E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO"
        )

    # --- revisioni (Step 6-7) ----------------------------------------

    # Scopo: crea_revisione da uno stato che non la ammette: la rifiuta la fn
    #        DB (E_OFFERTA_REVISIONE_STATO_NON_AMMESSO), col suo codice. ⛔ Fino
    #        al 2026-10-26 la anticipava `_assert_stato_corrente` (§13.6 punto 4).
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_crea_revisione_stato_lo_dice_il_db(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "BOZZA"
        repo.crea_revisione.side_effect = DatabaseError(
            "E_OFFERTA_REVISIONE_STATO_NON_AMMESSO: stato BOZZA non ammesso"
        )
        with self.assertRaises(ServiceError) as cm:
            OfferteService().crea_revisione(1)
        self.assertEqual(cm.exception.code, "E_OFFERTA_REVISIONE_STATO_NON_AMMESSO")
        repo.crea_revisione.assert_called_once()

    # Scopo: crea_revisione di un'offerta che non c'e' (o fuori perimetro): 404.
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_crea_revisione_offerta_inesistente_404(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo_cls.return_value.get_stato_codice.return_value = None
        with self.assertRaises(ServiceError) as cm:
            OfferteService().crea_revisione(1)
        self.assertEqual(cm.exception.code, "E_VENDITE_NOT_FOUND")
        repo_cls.return_value.crea_revisione.assert_not_called()

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

    # Scopo: list_revisioni delega al repository la PAGINA (id, limit/offset,
    #        ordinamento) e ritorna (righe, totale).
    #        ⚠️ Dal 2026-09-27 e' paginata: prima tornava la catena intera.
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_list_revisioni_ok_passa_id_al_repo(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "EMESSA"
        repo.list_revisioni.return_value = ([
            {"id": 1, "revisione_numero": 1, "stato_codice_interno": "SUPERATA"},
            {"id": 42, "revisione_numero": 2, "stato_codice_interno": "BOZZA"},
        ], 2)
        righe, totale = OfferteService().list_revisioni(
            1, limit=25, offset=0,
            order_by="data_emissione", order_dir="desc",
        )
        repo.list_revisioni.assert_called_once_with(
            1, limit=25, offset=0,
            order_by="data_emissione", order_dir="desc",
        )
        self.assertEqual(totale, 2)
        self.assertEqual(righe[1]["revisione_numero"], 2)

    # --- push a contratto (Step 8) -----------------------------------

    # Scopo: push da uno stato diverso da ACCETTATA: lo rifiuta il verbo
    #        (E_OFFERTA_PUSH_STATO_NON_AMMESSO), col suo codice. ⛔ Fino al
    #        2026-10-26 lo anticipava `_assert_stato_corrente` (§13.6 punto 4).
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_push_a_contratto_stato_lo_dice_il_db(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "EMESSA"
        repo.push_a_contratto.side_effect = DatabaseError(
            "E_OFFERTA_PUSH_STATO_NON_AMMESSO: stato EMESSA non ammesso"
        )
        with self.assertRaises(ServiceError) as cm:
            OfferteService().push_a_contratto(1)
        self.assertEqual(cm.exception.code, "E_OFFERTA_PUSH_STATO_NON_AMMESSO")

    # Scopo: push di un'offerta che non c'e' (o fuori perimetro): il 404 e'
    #        della fn, col suo codice (regola del 1, 2026-10-27).
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_push_a_contratto_offerta_inesistente_404(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo_cls.return_value.push_a_contratto.side_effect = DatabaseError(
            "E_OFFERTA_NON_TROVATA: offerta 1",
        )
        with self.assertRaises(ServiceError) as cm:
            OfferteService().push_a_contratto(1)
        self.assertEqual(cm.exception.code, "E_OFFERTA_NON_TROVATA")
        repo_cls.return_value.get_stato_codice.assert_not_called()

    # Scopo: push ok costruisce OffertaPushResult con id+numero+uid del nuovo
    #        contratto letto da get_contratto_minimal.
    @patch("apps.vendite.services.offerte_service.ContrattiRepository")
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_push_a_contratto_ok_costruisce_result(self, repo_cls, _atomic, contratti_cls):
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

        repo.push_a_contratto.assert_called_once_with(1, None, False)
        # Dopo la cascata dall'offerta, lo slot di default sul contratto nato:
        # il verbo non passa da `fn_create_contratto`, quindi lo chiede il
        # service (brief-db-indirizzi-documento-seguono-il-cliente, R-BE-1).
        contratti_cls.return_value.riempi_indirizzo_default.assert_called_once_with(101)
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
    @patch("apps.vendite.services.offerte_service.ContrattiRepository")
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_push_a_contratto_con_pratica_passa_pratica_id(self, repo_cls, _atomic, _contratti_cls):
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

        repo.push_a_contratto.assert_called_once_with(1, 77, False)

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

    # Scopo: R-BE-6 (brief-db-indirizzi-documento-seguono-il-cliente): con un
    #        CAMBIO DI CLIENTE la scheda del payload non si applica — il DB l'ha
    #        appena rifatta dal contatore nuovo, e l'upsert ci scriverebbe sopra
    #        quella del contatore di prima.
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    @patch(
        "apps.vendite.services.offerte_service.risolvi_cliente_coppia",
        return_value=(11, 4),
    )
    def test_aggiorna_offerta_cambio_cliente_non_riscrive_la_scheda(self, _cliente, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "BOZZA"
        repo.get_offerta.return_value = _make_offerta_dict()
        repo.list_eccezioni.return_value = []
        repo.get_coppia.return_value = {"billing_account_id": 10, "istanza_utility_id": 3, "utility_id": 1}
        repo.get_utility.return_value = {"id": 99}

        OfferteService().aggiorna_offerta(1, {
            "billing_account_id": 11,
            "utility": {"tipo_utenza_id": 7},
        })

        repo.update_offerta.assert_called_once()
        repo.update_utility.assert_not_called()
        repo.create_utility.assert_not_called()
        # Il cliente lo risolve il BB, sulla utility della testata: BA e
        # istanza arrivano al repository in coppia.
        self.assertEqual(_cliente.call_args.kwargs["utility_id"], 1)
        self.assertEqual(_cliente.call_args.kwargs["billing_account_id"], 11)
        dati = repo.update_offerta.call_args.args[1]
        self.assertEqual((dati["billing_account_id"], dati["istanza_utility_id"]), (11, 4))

    # Scopo: stesso cliente (anche se arriva come testo dal JSON): non e' un
    #        cambio di coppia, la scheda del payload si applica.
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    @patch(
        "apps.vendite.services.offerte_service.risolvi_cliente_coppia",
        return_value=(10, 3),
    )
    def test_aggiorna_offerta_stesso_cliente_applica_la_scheda(self, _cliente, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "BOZZA"
        repo.get_offerta.return_value = _make_offerta_dict()
        repo.list_eccezioni.return_value = []
        repo.get_coppia.return_value = {"billing_account_id": 10, "istanza_utility_id": 3, "utility_id": 1}
        repo.get_utility.return_value = {"id": 99}

        OfferteService().aggiorna_offerta(1, {
            "billing_account_id": "10",
            "utility": {"tipo_utenza_id": 7},
        })

        repo.update_utility.assert_called_once()

    # Scopo: ⛔ `{"utility": {}}` da solo non e' una modifica: 400 e niente
    #        scritto. Fino al 2026-10-14 passava il guard (il payload aveva una
    #        chiave) e la risposta era «salvata» a vuoto.
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_aggiorna_offerta_scheda_vuota_da_sola_e_400(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "BOZZA"
        with self.assertRaises(ServiceError) as ctx:
            OfferteService().aggiorna_offerta(1, {"utility": {}})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        repo.update_offerta.assert_not_called()
        repo.update_utility.assert_not_called()
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

    # Scopo (hardening 2026-05-26): se `script.fn_available_actions_offerta`
    #        solleva DatabaseError (es. SQL invalido nella fn — bug `??`
    #        JSONB osservato in dev), il service NON deve propagare
    #        E_DATABASE al client: logga warning e ritorna il detail senza
    #        blob capability. Il FE cade in readonly conservativo ma l'utente
    #        vede comunque l'offerta. Pattern: "capability layer rotto non
    #        deve impedire la read della testata".
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_get_offerta_capability_db_error_graceful_fallback(self, repo_cls):
        from django.db import DatabaseError

        from apps.vendite.services.offerte_service import OfferteService

        repo = repo_cls.return_value
        repo.get_offerta.return_value = _make_offerta_dict()
        repo.list_eccezioni.return_value = []
        repo.get_utility.return_value = None
        repo.get_available_actions.side_effect = DatabaseError(
            "l'operatore non esiste: jsonb ?? unknown"
        )

        # NON deve sollevare nonostante l'errore DB sulla fn capability.
        result = OfferteService().get_offerta(1)

        # Detail testata + eccezioni + utility OK
        self.assertEqual(result["id"], 1)
        self.assertEqual(result["stato_codice_interno"], "BOZZA")
        self.assertEqual(result["eccezioni"], [])
        self.assertIsNone(result["utility"])
        # Blob capability VUOTO, ma la chiave c'e': la forma non dipende
        # dall'esito. Il FE cade in readonly conservativo via
        # `useEntityCapabilities`.
        self.assertEqual(result["capabilities"], {})

    # --- BoM componenti su eccezione (simmetria contratti 2026-05-26) ---

    # Scopo: crea_eccezione su articolo composito invoca
    #        init_componenti_eccezione con emittente_sr_id risolto dalla
    #        testata via repo.get_emittente_sr_id_by_fiscale_id e data
    #        riferimento = validita_dal della testata.
    @patch(
        "apps.vendite.services.offerte_service."
        "validate_componenti_overrides_authorization",
        return_value=None,
    )
    @patch("apps.vendite.services.offerte_service.resolve_emittente_sr_id_for_testata")
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_crea_eccezione_articolo_composito_invoca_init(
        self, repo_cls, _atomic, _resolve, _l1,
    ):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "BOZZA"
        repo.create_eccezione.return_value = 42
        repo.is_articolo_composito.return_value = True
        repo.get_offerta.return_value = _make_offerta_dict()
        repo.init_componenti_eccezione.return_value = 3
        repo.get_eccezione.return_value = {"id": 42, "offerta_id": 1}
        _resolve.return_value = 555

        OfferteService().crea_eccezione(
            1,
            {
                "articolo_id": "00000000-0000-7000-8000-000000000abc",
                "tipo_eccezione": "OVERRIDE",
                "fonte_quantita_attesa": "MANUALE",
                "prezzo_unitario": "12.50",
                "componenti_overrides": {"00000000-0000-7000-8000-deadbeef0001": "9.50"},
            },
            auth_user_id=99,
        )

        repo.init_componenti_eccezione.assert_called_once()
        kwargs = repo.init_componenti_eccezione.call_args.kwargs
        self.assertEqual(kwargs["eccezione_id"], 42)
        self.assertEqual(kwargs["emittente_soggetto_ruolo_id"], 555)
        self.assertEqual(kwargs["data_riferimento"], "2026-06-01")
        self.assertEqual(
            kwargs["componenti_overrides"],
            {"00000000-0000-7000-8000-deadbeef0001": "9.50"},
        )

    # Scopo: crea_eccezione su articolo NON composito non chiama init
    #        (BoM no-op simmetrico al pattern contratti).
    @patch(
        "apps.vendite.services.offerte_service.OfferteService."
        "_apply_pricing_gate_eccezione",
        return_value=(None, None),
    )
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_crea_eccezione_articolo_atomico_non_invoca_init(
        self, repo_cls, _atomic, _gate,
    ):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "BOZZA"
        repo.create_eccezione.return_value = 42
        repo.is_articolo_composito.return_value = False
        repo.get_eccezione.return_value = {"id": 42, "offerta_id": 1}

        OfferteService().crea_eccezione(
            1,
            {
                "articolo_id": "00000000-0000-7000-8000-000000000abc",
                "tipo_eccezione": "OVERRIDE",
                "fonte_quantita_attesa": "MANUALE",
                "prezzo_unitario": "12.50",
            },
            auth_user_id=99,
        )

        repo.init_componenti_eccezione.assert_not_called()
        repo.get_offerta.assert_not_called()

    # Scopo: composito senza emittente risolvibile (admin globale + testata
    #        senza emittente_fiscale_id) -> 400 parlante, no INSERT cascade.
    @patch("apps.vendite.services.offerte_service.resolve_emittente_sr_id_for_testata")
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_crea_eccezione_composito_senza_emittente_fallisce(
        self, repo_cls, _atomic, _resolve,
    ):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "BOZZA"
        repo.create_eccezione.return_value = 42
        repo.is_articolo_composito.return_value = True
        repo.get_offerta.return_value = _make_offerta_dict()
        _resolve.return_value = None  # admin globale, no emittente

        with self.assertRaises(ServiceError) as cm:
            OfferteService().crea_eccezione(
                1,
                {
                    "articolo_id": "00000000-0000-7000-8000-000000000abc",
                    "tipo_eccezione": "OVERRIDE",
                    "fonte_quantita_attesa": "MANUALE",
                    "prezzo_unitario": "12.50",
                },
                auth_user_id=None,
            )
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")
        repo.init_componenti_eccezione.assert_not_called()

    # Scopo: preview_componenti_eccezione delega al repo con tutti i campi
    #        derivati dalla testata + emittente risolto.
    @patch("apps.vendite.services.offerte_service.resolve_emittente_sr_id_for_testata")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_preview_componenti_eccezione_ok(self, repo_cls, _resolve):
        from apps.vendite.services.offerte_service import OfferteService

        repo = repo_cls.return_value
        repo.get_offerta.return_value = _make_offerta_dict()
        repo.preview_componenti_eccezione.return_value = [{"componente_id": "x"}]
        _resolve.return_value = 555

        result = OfferteService().preview_componenti_eccezione(
            1, articolo_id="00000000-0000-7000-8000-000000000abc",
            uom_operativa_id=2, quantita="3",
            auth_user_id=99,
        )

        self.assertEqual(len(result), 1)
        repo.preview_componenti_eccezione.assert_called_once()
        kwargs = repo.preview_componenti_eccezione.call_args.kwargs
        self.assertEqual(kwargs["data_riferimento"], "2026-06-01")
        self.assertEqual(kwargs["ba_id"], 100)
        self.assertEqual(kwargs["utility_id"], 3)
        self.assertEqual(kwargs["emittente_soggetto_ruolo_id"], 555)

    # Scopo: preview su offerta inesistente -> 404 prima del lookup repo.
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_preview_componenti_eccezione_offerta_not_found(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo_cls.return_value.get_offerta.return_value = None
        with self.assertRaises(ServiceError) as cm:
            OfferteService().preview_componenti_eccezione(
                999, articolo_id="x", uom_operativa_id=1, quantita="1",
            )
        self.assertEqual(cm.exception.code, "E_VENDITE_NOT_FOUND")

    # Scopo: list_componenti_eccezione tenta tampering offerta/eccezione
    #        -> 404 (eccezione_id non appartiene a offerta_id richiesto).
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_list_componenti_eccezione_ownership_violata(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo_cls.return_value.get_eccezione.return_value = {
            "id": 42, "offerta_id": 999,
        }
        with self.assertRaises(ServiceError) as cm:
            OfferteService().list_componenti_eccezione(1, 42)
        self.assertEqual(cm.exception.code, "E_VENDITE_NOT_FOUND")

    # Scopo: update_componente_eccezione con payload fuori whitelist
    #        (campi struttura immutabili) -> 400 che NOMINA la chiave, e il
    #        repository non viene chiamato. ⛔ Fino al 2026-09-26 la chiave
    #        arrivava al mixin, che la scartava in silenzio.
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_update_componente_eccezione_payload_vuoto_fallisce(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "BOZZA"
        repo.get_eccezione.return_value = {"id": 42, "offerta_id": 1}
        repo.get_componente.return_value = {
            "id": 7, "eccezione_offerta_id": 42,
        }

        with self.assertRaises(ServiceError) as cm:
            OfferteService().update_componente_eccezione(
                1, 42, 7, {"componente_id": "x"},  # struttura immutabile
            )
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")
        self.assertEqual(cm.exception.context["unknown_keys"], ["componente_id"])
        repo.update_componente.assert_not_called()

    # Scopo: ⛔ l'operatore NON puo' approvarsi un prezzo L3 (stesso rifiuto
    #        di preventivi e contratti). Fino al 2026-09-26 la PATCH validava
    #        contro la whitelist del REPOSITORY, che contiene
    #        `stato_approvazione_prezzo`. ⚠️ Sono chiavi che il repository
    #        AMMETTE: e' il caso che distingue il codice vecchio dal nuovo.
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_update_componente_eccezione_campi_del_workflow_rifiutati(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "BOZZA"
        repo.get_eccezione.return_value = {"id": 42, "offerta_id": 1}
        repo.get_componente.return_value = {
            "id": 7, "eccezione_offerta_id": 42,
        }
        for payload in (
            {"stato_approvazione_prezzo": "APPROVED"},
            {"pratica_approvazione_prezzo_id": 7},
            {"prezzo_unitario": "1.00", "origine_prezzo": "CONTRATTO_LISTINO"},
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(ServiceError) as cm:
                    OfferteService().update_componente_eccezione(1, 42, 7, payload)
                self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")
        repo.update_componente.assert_not_called()

    # Scopo: update_componente tenta tampering (componente non appartiene
    #        all'eccezione) -> 404.
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_update_componente_eccezione_ownership_violata(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "BOZZA"
        repo.get_eccezione.return_value = {"id": 42, "offerta_id": 1}
        repo.get_componente.return_value = {
            "id": 7, "eccezione_offerta_id": 999,
        }

        with self.assertRaises(ServiceError) as cm:
            OfferteService().update_componente_eccezione(
                1, 42, 7, {"prezzo_unitario": "9.50"},
            )
        self.assertEqual(cm.exception.code, "E_VENDITE_NOT_FOUND")

    # Scopo: delete_componente happy path -> attivo=False, ritorna deleted=true.
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_delete_componente_eccezione_ok(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "BOZZA"
        repo.get_eccezione.return_value = {"id": 42, "offerta_id": 1}
        repo.get_componente.return_value = {
            "id": 7, "eccezione_offerta_id": 42,
        }
        repo.delete_componente.return_value = True

        result = OfferteService().delete_componente_eccezione(1, 42, 7)
        self.assertEqual(result["componente_id"], 7)
        self.assertTrue(result["deleted"])


class OfferteGatePrezzoTests(TestCase):
    """Gate prezzo L1/L2/L3 sulle eccezioni offerta (refactor 2026-06-01).

    Simmetria col contratto: il wiring (gate invocato per OVERRIDE/AGGIUNTA,
    L1 componenti, L3 PENDING) e' testato qui; la logica dei singoli gate vive
    nel BB `_pricing_gate_helpers` (gia' coperto dai test preventivi/contratti).
    """

    # 53) crea_eccezione invoca il gate L1 sugli override componenti col payload.
    @patch("apps.vendite.services.offerte_service.OfferteService._apply_pricing_gate_eccezione",
           return_value=(None, None))
    @patch("apps.vendite.services.offerte_service.validate_componenti_overrides_authorization")
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_crea_eccezione_invoca_validate_l1_componenti(
        self, repo_cls, _atomic, mock_validate, _gate,
    ):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "BOZZA"
        repo.create_eccezione.return_value = 42
        repo.is_articolo_composito.return_value = False
        repo.get_eccezione.return_value = {"id": 42, "offerta_id": 1}

        OfferteService().crea_eccezione(
            1,
            {
                "articolo_id": "00000000-0000-7000-8000-000000000abc",
                "tipo_eccezione": "AGGIUNTA",
                "fonte_quantita_attesa": "MANUALE",
                "prezzo_unitario": "12.50",
                "componenti_overrides": {"00000000-0000-7000-8000-deadbeef0001": "9.50"},
            },
            auth_user_id=99,
        )

        # Validator invocato col contesto utente (il payload e' poi mutato dal
        # pop overrides → non si asserisce sul dict, che il mock referenzia).
        mock_validate.assert_called_once()
        self.assertEqual(mock_validate.call_args.args[1], 99)

    # 54) OVERRIDE non composito → _apply_pricing_gate_eccezione invocato.
    @patch("apps.vendite.services.offerte_service.validate_componenti_overrides_authorization",
           return_value=None)
    @patch("apps.vendite.services.offerte_service.OfferteService._apply_pricing_gate_eccezione",
           return_value=(None, None))
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_crea_eccezione_override_invoca_gate(
        self, repo_cls, _atomic, mock_gate, _l1,
    ):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "BOZZA"
        repo.create_eccezione.return_value = 42
        repo.is_articolo_composito.return_value = False
        repo.get_eccezione.return_value = {"id": 42, "offerta_id": 1}

        OfferteService().crea_eccezione(
            1,
            {
                "articolo_id": "00000000-0000-7000-8000-000000000abc",
                "tipo_eccezione": "OVERRIDE",
                "fonte_quantita_attesa": "MANUALE",
                "prezzo_unitario": "12.50",
            },
            auth_user_id=99,
        )

        mock_gate.assert_called_once()
        kwargs = mock_gate.call_args.kwargs
        self.assertEqual(kwargs["offerta_id"], 1)
        self.assertEqual(kwargs["riga_id_for_link"], None)

    # 55) ESCLUSIONE (prezzo NULL) → nessun gate prezzo.
    @patch("apps.vendite.services.offerte_service.validate_componenti_overrides_authorization",
           return_value=None)
    @patch("apps.vendite.services.offerte_service.OfferteService._apply_pricing_gate_eccezione")
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_crea_eccezione_esclusione_non_invoca_gate(
        self, repo_cls, _atomic, mock_gate, _l1,
    ):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "BOZZA"
        repo.create_eccezione.return_value = 42
        repo.is_articolo_composito.return_value = False
        repo.get_eccezione.return_value = {"id": 42, "offerta_id": 1}

        OfferteService().crea_eccezione(
            1,
            {
                "articolo_id": "00000000-0000-7000-8000-000000000abc",
                # L'esclusione come la crea «Escludi»: articolo e tipo, niente
                # dati di fatturazione (2026-10-04). Prima ci voleva la fonte.
                "tipo_eccezione": "ESCLUSIONE",
            },
            auth_user_id=99,
        )

        mock_gate.assert_not_called()

    # 56) _apply_pricing_gate_eccezione: violazione L2 + richiesta_approvazione
    #     → payload riceve stato PENDING + pratica_id (workflow L3).
    @patch("apps.vendite.services.offerte_service._orchestrate_l3_request_offerta",
           return_value=777)
    @patch("apps.vendite.services.offerte_service.resolve_or_check_override_prezzo_riga_offerta")
    def test_apply_gate_eccezione_l3_pending_setta_stato(
        self, mock_resolve, mock_orch,
    ):
        from decimal import Decimal

        from apps.vendite.services.offerte_service import (
            OfferteService,
            STATO_APPROVAZIONE_PENDING,
        )

        mock_resolve.return_value = (
            Decimal("12.50"),
            {
                "richiesta_approvazione_pending": True,
                "violazione_l2": {"tipo_violazione": "SCONTO"},
                "prezzo_base_resolver": "10.00",
            },
        )
        svc = OfferteService()
        svc._repo = MagicMock()
        svc._repo.get_offerta.return_value = _make_offerta_dict()

        payload = {"prezzo_unitario": "12.50"}
        pratica_id, _testata = svc._apply_pricing_gate_eccezione(
            offerta_id=1,
            articolo_id="00000000-0000-7000-8000-000000000abc",
            uom_id=5,
            payload=payload,
            auth_user_id=99,
            richiesta_approvazione=True,
            riga_id_for_link=42,
        )

        self.assertEqual(pratica_id, 777)
        self.assertEqual(payload["stato_approvazione_prezzo"], STATO_APPROVAZIONE_PENDING)
        self.assertEqual(payload["pratica_approvazione_prezzo_id"], 777)
        mock_orch.assert_called_once()

    # 57) resolve_or_check_override_prezzo_riga_offerta: offerta senza listino
    #     → ritorna il prezzo as-is, gate BB non invocato.
    @patch("apps.vendite.services.offerte_service.resolve_or_check_override_prezzo")
    def test_resolve_override_prezzo_offerta_skip_senza_listino(self, mock_bb):
        from apps.vendite.services.offerte_service import (
            resolve_or_check_override_prezzo_riga_offerta,
        )

        prezzo, meta = resolve_or_check_override_prezzo_riga_offerta(
            testata={"listino_id": None, "validita_dal": "2026-06-01"},
            articolo_id="x",
            uom_id=5,
            payload_prezzo="12.50",
            auth_user_id=99,
            function_name="test",
        )
        self.assertEqual(prezzo, "12.50")
        self.assertIsNone(meta)
        mock_bb.assert_not_called()

    # 58) _apply_pricing_gate_eccezione: su override entro-soglia preserva il
    #     meta persistito (fallback_meta) mergiando l'audit — niente clobber.
    @patch("apps.vendite.services.offerte_service.resolve_or_check_override_prezzo_riga_offerta")
    def test_apply_gate_eccezione_preserva_meta_esistente(self, mock_resolve):
        from decimal import Decimal

        from apps.vendite.services.offerte_service import OfferteService

        # Override accettato (no L3): meta audit senza richiesta_approvazione.
        mock_resolve.return_value = (
            Decimal("11.00"),
            {"origine_prezzo": "MANUALE", "prezzo_base_resolver": "10.00"},
        )
        svc = OfferteService()
        svc._repo = MagicMock()
        svc._repo.get_offerta.return_value = _make_offerta_dict()

        payload = {"prezzo_unitario": "11.00"}  # update: niente meta nel payload
        svc._apply_pricing_gate_eccezione(
            offerta_id=1,
            articolo_id="00000000-0000-7000-8000-000000000abc",
            uom_id=5,
            payload=payload,
            auth_user_id=99,
            richiesta_approvazione=False,
            riga_id_for_link=42,
            fallback_meta={"nota_interna": "preesistente"},
        )

        # Il meta esistente (`nota_interna`) sopravvive + audit pricing mergiato.
        self.assertEqual(payload["meta"]["nota_interna"], "preesistente")
        self.assertEqual(payload["meta"]["origine_prezzo"], "MANUALE")
        # Nessun workflow L3 → niente stato/pratica nel payload.
        self.assertNotIn("stato_approvazione_prezzo", payload)


@_SENZA_CONTATORI_DB
class OfferteScrittureBbTests(TestCase):
    """Scritture sul BB core (2026-09-26): il service consegna al repository
    un `meta` OGGETTO e rifiuta (400) cio' che prima si scartava o si
    serializzava in silenzio."""

    def _svc(self, repo_cls, _atomic):
        from apps.vendite.services.offerte_service import OfferteService

        _atomic.return_value.__enter__ = MagicMock()
        _atomic.return_value.__exit__ = MagicMock(return_value=False)
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "BOZZA"
        repo.get_offerta.return_value = _make_offerta_dict()
        repo.list_eccezioni.return_value = []
        repo.get_utility.return_value = {"id": 99, "tipo_utenza_id": 5}
        return OfferteService(), repo

    # 59. ⭐ Una stringa che contiene un oggetto JSON arriva al repository come
    #     dict (prima: `json.dumps` di nuovo -> scalare stringa jsonb).
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_aggiorna_offerta_meta_stringa_json_diventa_dict(self, repo_cls, _atomic):
        svc, repo = self._svc(repo_cls, _atomic)
        svc.aggiorna_offerta(1, {"meta": '{"nota": "x"}'})
        repo.update_offerta.assert_called_once_with(1, {"meta": {"nota": "x"}})

    # 60. `null` = reset a `{}`: la colonna e' NOT NULL DEFAULT '{}' (prima:
    #     NULL al database, violazione NOT NULL con errore generico).
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_aggiorna_offerta_meta_null_diventa_oggetto_vuoto(self, repo_cls, _atomic):
        svc, repo = self._svc(repo_cls, _atomic)
        svc.aggiorna_offerta(1, {"meta": None})
        repo.update_offerta.assert_called_once_with(1, {"meta": {}})

    # 61. ⛔ Un `meta` che non e' un oggetto e' un 400 educato, non un errore
    #     di cast al database (o, prima, uno scalare scritto in silenzio).
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_crea_eccezione_meta_non_oggetto_e_400(self, repo_cls, _atomic):
        svc, repo = self._svc(repo_cls, _atomic)
        with self.assertRaises(ServiceError) as cm:
            svc.crea_eccezione(1, {
                "articolo_id": "00000000-0000-7000-8000-000000000abc",
                "tipo_eccezione": "ESCLUSIONE",
                "meta": 42,
            })
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")
        self.assertEqual(cm.exception.context.get("field"), "meta")
        repo.create_eccezione.assert_not_called()

    # 62. Stessa regola sull'utility 1:1 (stringa che non e' un oggetto).
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_aggiorna_utility_meta_non_oggetto_e_400(self, repo_cls, _atomic):
        svc, repo = self._svc(repo_cls, _atomic)
        with self.assertRaises(ServiceError) as cm:
            svc.aggiorna_utility(1, 99, {"meta": '"solo una stringa"'})
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")
        self.assertEqual(cm.exception.context.get("field"), "meta")
        repo.update_utility.assert_not_called()

    # 63. ⛔ Il sotto-oggetto `utility` nel PATCH di testata: una chiave
    #     SCONOSCIUTA e' un 400 (prima l'intersezione con la whitelist la
    #     scartava). Gli id immutabili, che il form riporta, si tolgono ancora.
    @patch("apps.vendite.services.offerte_service.transaction.atomic")
    @patch("apps.vendite.services.offerte_service.OfferteRepository")
    def test_aggiorna_offerta_utility_inline_chiave_estranea_e_400(self, repo_cls, _atomic):
        svc, repo = self._svc(repo_cls, _atomic)
        with self.assertRaises(ServiceError) as cm:
            svc.aggiorna_offerta(1, {"utility": {"tipo_utenza_id": 7, "colore": "blu"}})
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")
        repo.update_utility.assert_not_called()

        svc.aggiorna_offerta(1, {"utility": {"tipo_utenza_id": 7, "utility_id": 3}})
        repo.update_utility.assert_called_once_with(99, {"tipo_utenza_id": 7})
