# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari ContrattiService (F2-BE-05).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) list_contratti_does_not_apply_default_data_da
2) list_contratti_invalid_order
3) list_contratti_invalid_ambito
4) get_contratto_not_found
5) get_contratto_ok
6) create_contratto_modalita_A_ok
7) create_contratto_modalita_C_ok
8) create_contratto_modalita_C_con_variazione_fallisce
9) create_contratto_variazione_coppia_incompleta_fallisce
10) create_contratto_rifiuta_numero_in_payload
11) create_contratto_overlap_temporal_unique_mappato
12) create_contratto_genera_numero_e_stato_draft
13) update_contratto_rifiuta_identificativi_immutabili
13b) update_contratto_rifiuta_categoria_snapshot_non_draft
14) update_contratto_campi_vuoto_fallisce
15) update_contratto_ok_variazione
15b) update_contratto_variazione_none_azzera — `null` sul tipo AZZERA (tre stati del PATCH, BB `extract_optional_enum`)
15c) create_contratto_ambito_fuori_vocabolario_nomina_il_campo — `ambito` via `require_enum`: campo nel context, non-stringa e' un 400
16) cambia_stato_codice_sconosciuto
17) cambia_stato_modalita_C_senza_righe_tradotto
18) cambia_stato_ok
19) create_riga_modalita_C_senza_prezzo_tradotto
20) create_riga_ok
21) update_riga_rifiuta_articolo_id
22) update_riga_ok
23) delete_riga_not_found
24) create_utility_tipo_classe_obbligatori_tradotto
25) create_utility_ok
26) update_utility_immutabili_rifiutati
27) update_contratto_modalita_B_con_listino_esistente_patch_solo_variazione (regressione review)
28) repository_create_contratto_usa_cast_jsonb_per_meta (regressione review)
29) get_contratto_righe_count_usa_preview_per_modalita_ab
30) get_contratto_righe_count_usa_righe_persistite_per_modalita_c
31) create/update/delete_riga_rifiutata_su_contratto_attivo — E_RIGA_DOC_NON_BOZZA (il codice del DB sulle stesse righe, BB richiedi_righe_in_bozza; frase a catalogo, verbo)
32) create/update_utility_su_contratto_attivo_decide_il_db — lo stato lo giudica il lock dei satelliti (E_DOC_DATI_COLLEGATI_NON_BOZZA)
33) update_componente_contratto_attivo — E_RIGA_DOC_NON_BOZZA, etichetta dal `numero` dello scope
33b) update_componente_campi_del_workflow_rifiutati — niente auto-approvazione L3 dal client
34) update_contratto_cambio/rimozione_listino_decide_il_db — il listino sotto le righe lo giudica il DB (E_DOC_LISTINO_*)
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.db import DatabaseError, IntegrityError

from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.core.services.service_errors import ServiceError


def _testata_default() -> dict[str, object]:
    """Factory riga testata per rilettura get_contratto post-mutazione.
    `stato_codice='DRAFT'` per default: i test che esercitano stati
    post-DRAFT lo sovrascrivono esplicitamente. `valido_dal=oggi-1` per
    permettere ai guard data-driven (es. cambia_stato con valido_al)
    di validare contro un valido_dal valorizzato.
    """
    return {
        "id": 1,
        "numero": "CNT0000001",
        "billing_account_id": 10,
        "istanza_utility_id": 20,
        "utility_id": 3,
        "stato_doc_contratto_id": 1,
        "stato_codice_interno": "DRAFT",
        "valido_dal": oggi_aziendale() - timedelta(days=1),
        "listino_id": 100,
        "tipo_variazione_globale": "PERCENTUALE",
        "valore_variazione_globale": Decimal("-10"),
        "ambito": "COMMODITY",
    }


class ContrattiServiceTests(TestCase):
    # --- lista ---------------------------------------------------------

    # Scopo: senza data_da il service non applica default temporali impliciti.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_list_contratti_does_not_apply_default_data_da(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.list_contratti.return_value = ([], 0)

        ContrattiService().list_contratti()

        call = repo.list_contratti.call_args.kwargs
        self.assertIsNone(call["data_da"])

    # Scopo: order_by non whitelisted -> ServiceError.
    def test_list_contratti_invalid_order(self):
        from apps.vendite.services.contratti_service import ContrattiService

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().list_contratti(order_by="haxxor")
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: filtro ambito fuori whitelist -> ServiceError.
    def test_list_contratti_invalid_ambito(self):
        from apps.vendite.services.contratti_service import ContrattiService

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().list_contratti(ambito="FANTASY")
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # --- dettaglio -----------------------------------------------------

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_get_contratto_not_found(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo_cls.return_value.get_contratto.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().get_contratto(42)
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_get_contratto_ok(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = {"id": 5}
        repo.list_righe.return_value = [{"id": 99}]
        repo.list_righe_preview.return_value = [{"articolo_id": "a"}, {"articolo_id": "b"}]
        repo.get_capabilities.return_value = {}

        result = ContrattiService().get_contratto(1)

        self.assertEqual(result["id"], 1)
        self.assertEqual(result["utility"], {"id": 5})
        self.assertEqual(result["righe"], [{"id": 99}])
        self.assertEqual(result["righe_count"], 2)

    # Scopo: Verifica che get_contratto includa nel detail il blob capabilities
    #        ritornato da script.fn_available_actions_contratto (Fase 1.B2),
    #        SOTTO `capabilities` (api.md §«Il blob sta SOTTO `capabilities`»).
    #        ⚠️ Il blob porta `stato_codice_interno`, che la testata ha gia':
    #        fuso, vinceva il blob in silenzio. Qui i due valori DIFFERISCONO
    #        apposta, e la testata deve restare la sua.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_get_contratto_include_capabilities(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        testata = _testata_default()
        testata["stato_codice_interno"] = "DRAFT"
        repo.get_contratto.return_value = testata
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []
        repo.list_righe_preview.return_value = []
        repo.get_capabilities.return_value = {
            "stato_codice_interno": "ATTIVO",
            "available_actions": [{
                "key": "cessa", "target_state": "CESSATO",
                "label_key": "contratti.azione_cessa",
                "requires_confirm": True, "requires_date": True,
                "default_date": "2026-04-30", "min_date": "2026-04-25",
            }],
            "can_change_state": True,
            "can_edit_testata": True,
            "can_edit_righe": False,
            "non_editable_fields": ["billing_account_id", "utility_id"],
        }

        result = ContrattiService().get_contratto(1)

        caps = result["capabilities"]
        self.assertEqual(caps, repo.get_capabilities.return_value)
        self.assertEqual(caps["can_change_state"], True)
        self.assertEqual(caps["can_edit_righe"], False)
        self.assertEqual(len(caps["available_actions"]), 1)
        action = caps["available_actions"][0]
        self.assertEqual(action["key"], "cessa")
        self.assertEqual(action["default_date"], "2026-04-30")
        self.assertIn("billing_account_id", caps["non_editable_fields"])
        self.assertNotIn("can_change_state", result)
        self.assertNotIn("available_actions", result)
        self.assertEqual(result["stato_codice_interno"], "DRAFT")
        repo.get_capabilities.assert_called_once_with(1)

    # Scopo: in modalita' A/B il conteggio righe del detail usa la preview
    #        effettivamente mostrata dal drawer (listino + override).
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_get_contratto_righe_count_usa_preview_per_modalita_ab(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []
        repo.list_righe_preview.return_value = [
            {"articolo_id": "a"},
            {"articolo_id": "b"},
            {"articolo_id": "c"},
        ]
        repo.get_capabilities.return_value = {}

        result = ContrattiService().get_contratto(1)

        self.assertEqual(result["righe_count"], 3)

    # Scopo: in modalita' C il conteggio righe usa le righe persistite,
    #        perche' non esiste preview da listino.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_get_contratto_righe_count_usa_righe_persistite_per_modalita_c(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        testata = _testata_default()
        testata["listino_id"] = None
        repo.get_contratto.return_value = testata
        repo.get_utility.return_value = None
        repo.list_righe.return_value = [{"id": 1}, {"id": 2}]
        repo.get_capabilities.return_value = {}

        result = ContrattiService().get_contratto(1)

        self.assertEqual(result["righe_count"], 2)
        repo.list_righe_preview.assert_not_called()

    # --- create contratto ---------------------------------------------

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_contratto_modalita_A_ok(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.create_contratto_atomico.return_value = 1
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        result = ContrattiService().create_contratto({
            "billing_account_id": 10,
            "istanza_utility_id": 20,
            "utility_id": 3,
            "valido_dal": "2026-01-01",
            "valido_al": "2026-12-31",
            "listino_id": 100,
            "tipo_variazione_globale": "percentuale",
            "valore_variazione_globale": "10",
        })

        self.assertEqual(result["id"], 1)
        testata = repo.create_contratto_atomico.call_args.kwargs["testata"]
        self.assertEqual(testata["tipo_variazione_globale"], "PERCENTUALE")
        # numero e stato DRAFT sono risolti dalla fn madre: il BE non li passa.
        self.assertNotIn("numero", testata)
        self.assertNotIn("stato_doc_contratto_id", testata)
        # Lo slot di default lo riempie `vendite.fn_create_contratto` da se':
        # il service non lo chiede una seconda volta (R-BE-1).
        repo.riempi_indirizzo_default.assert_not_called()

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_contratto_modalita_C_ok(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.create_contratto_atomico.return_value = 2
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().create_contratto({
            "billing_account_id": 10,
            "istanza_utility_id": 20,
            "utility_id": 3,
            "valido_dal": "2026-01-01",
        })

        testata = repo.create_contratto_atomico.call_args.kwargs["testata"]
        self.assertNotIn("listino_id", testata)
        self.assertNotIn("tipo_variazione_globale", testata)

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_contratto_senza_listino_con_variazione_ok(self, repo_cls):
        # Refactor modalita 2026-05-15: nel modello unificato un contratto
        # "senza_listino" (ex-modalita C) puo' anche avere variazione globale.
        # E' una combinazione di campi liberi — la variazione si applichera'
        # solo sulle righe (ex-modalita B) ma non e' bloccata dal modello.
        # Il vecchio test (E_VENDITE_VALIDATION) era il gating modalita
        # rimosso in questo refactor.
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.create_contratto_atomico.return_value = 3
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().create_contratto({
            "billing_account_id": 10,
            "istanza_utility_id": 20,
            "utility_id": 3,
            "valido_dal": "2026-01-01",
            "tipo_variazione_globale": "PERCENTUALE",
            "valore_variazione_globale": "5",
        })

        testata = repo.create_contratto_atomico.call_args.kwargs["testata"]
        self.assertEqual(testata["tipo_variazione_globale"], "PERCENTUALE")
        self.assertNotIn("listino_id", testata)

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_contratto_variazione_coppia_incompleta_fallisce(
        self, repo_cls,
    ):
        # Resta valido il vincolo strutturale: tipo+valore devono essere
        # coppia coerente (entrambi NULL o entrambi NOT NULL).
        from apps.vendite.services.contratti_service import ContrattiService

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().create_contratto({
                "billing_account_id": 10,
                "istanza_utility_id": 20,
                "utility_id": 3,
                "valido_dal": "2026-01-01",
                "listino_id": 100,
                "tipo_variazione_globale": "PERCENTUALE",
                # valore_variazione_globale mancante -> coppia incompleta
            })
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertIn("entrambi presenti o entrambi NULL", ctx.exception.detail or "")

    def test_create_contratto_rifiuta_numero_in_payload(self):
        from apps.vendite.services.contratti_service import ContrattiService

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().create_contratto({
                "numero": "CNT9999999",
                "billing_account_id": 10,
                "istanza_utility_id": 20,
                "utility_id": 3,
                "valido_dal": "2026-01-01",
            })
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_contratto_overlap_temporal_unique_mappato(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        # Scopo: PG18 temporal UNIQUE (WITHOUT OVERLAPS) sulla colonna `validita`
        #        STORED generated → messaggio standard "unique constraint",
        #        nome `uq_contratti_no_overlap` (migration 20260514-10). Ora
        #        l'IntegrityError arriva dalla fn madre create_contratto_atomico.
        repo.create_contratto_atomico.side_effect = IntegrityError(
            "duplicate key value violates unique constraint \"uq_contratti_no_overlap\""
        )

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().create_contratto({
                "billing_account_id": 10,
                "istanza_utility_id": 20,
                "utility_id": 3,
                "valido_dal": "2026-01-01",
            })
        self.assertEqual(ctx.exception.code, "E_CONTRATTO_OVERLAP_ESISTENTE")

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_contratto_overlap_exclusion_partial_mappato(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        # Scopo: post 2026-05-21 (migrations 20260521-01..03) il constraint
        #        diventa EXCLUDE gist parziale `ex_contratti_no_overlap`
        #        (WHERE NOT is_abortito_snapshot). Messaggio PG ha tipo
        #        "exclusion constraint" e nome cambiato. Entrambi i nomi
        #        sono mappati nei `_UNIQUE_CONSTRAINTS` per resilienza.
        repo.create_contratto_atomico.side_effect = IntegrityError(
            "conflicting key value violates exclusion constraint \"ex_contratti_no_overlap\""
        )

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().create_contratto({
                "billing_account_id": 10,
                "istanza_utility_id": 20,
                "utility_id": 3,
                "valido_dal": "2026-01-01",
            })
        self.assertEqual(ctx.exception.code, "E_CONTRATTO_OVERLAP_ESISTENTE")

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_contratto_delega_numero_e_stato_alla_fn_madre(self, repo_cls):
        # Fix analisi-fix-transazioni #2: numero e stato DRAFT sono risolti
        # DENTRO vendite.fn_create_contratto. Il BE non li genera piu' ne' li
        # passa nella testata, e non c'e' utility -> utility=None.
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.create_contratto_atomico.return_value = 7
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().create_contratto({
            "billing_account_id": 10,
            "istanza_utility_id": 20,
            "utility_id": 3,
            "valido_dal": "2026-01-01",
        })

        repo.generate_numero.assert_not_called()
        kwargs = repo.create_contratto_atomico.call_args.kwargs
        self.assertNotIn("numero", kwargs["testata"])
        self.assertNotIn("stato_doc_contratto_id", kwargs["testata"])
        self.assertIsNone(kwargs["utility"])

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_contratto_con_utility_passa_alla_fn_madre(self, repo_cls):
        # Fix #2: testata + riga utility 1:1 fuse in un'unica fn madre atomica.
        # Il BE costruisce entrambi i dict e li passa insieme; nessun INSERT
        # utility separato (repo.create_utility, usato solo dal percorso update).
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.create_contratto_atomico.return_value = 5
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().create_contratto({
            "billing_account_id": 10,
            "istanza_utility_id": 20,
            "utility_id": 3,
            "valido_dal": "2026-01-01",
            "utility": {"tipo_utenza_id": 2, "classe_utenza_id": 7},
        })

        util = repo.create_contratto_atomico.call_args.kwargs["utility"]
        self.assertIsNotNone(util)
        # istanza/utility derivati dalla testata, non dal payload utility.
        self.assertEqual(util["istanza_utility_id"], 20)
        self.assertEqual(util["utility_id"], 3)
        self.assertEqual(util["tipo_utenza_id"], 2)
        repo.create_utility.assert_not_called()

    # --- update contratto ---------------------------------------------

    def test_update_contratto_rifiuta_identificativi_immutabili(self):
        from apps.vendite.services.contratti_service import ContrattiService

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().update_contratto(1, {"numero": "CNT9999999"})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: contratto ATTIVO -> categoria_cliente_id_snapshot: quali colonne
    #        si cambiano in quale stato lo dice il lock di testata del DB
    #        (brief-db-testata-dopo-emissione, D-0; la categoria e' fra le
    #        condizioni, ferma fuori bozza). Il service non ha piu' la tabella
    #        per stato e passa la scrittura: il 409 arriva dal DB.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_contratto_attivo_categoria_snapshot_decide_il_db(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = {
            **_testata_default(),
            "stato_codice_interno": "ATTIVO",
            "categoria_cliente_id_snapshot": 1,
        }
        repo.update_contratto.return_value = True
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().update_contratto(1, {"categoria_cliente_id_snapshot": 5})
        self.assertEqual(
            repo.update_contratto.call_args.args[1]["categoria_cliente_id_snapshot"], 5,
        )

    # Scopo: contratto ATTIVO -> ammessa solo modifica valido_al/meta
    #        (programma cessazione + note). Il PATCH valido_al passa.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_contratto_attivo_ammette_solo_valido_al(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = {
            **_testata_default(),
            "stato_codice_interno": "ATTIVO",
        }
        repo.update_contratto.return_value = True
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().update_contratto(1, {"valido_al": "2026-12-31"})

        args = repo.update_contratto.call_args.args
        self.assertEqual(args[0], 1)
        self.assertEqual(args[1]["valido_al"], date(2026, 12, 31))

    # Scopo: contratto ATTIVO -> i tre riferimenti dell'atto (CIG/CUP/commessa)
    #        passano (I8/D9, decisione Q1 di Tid del 2026-08-29).
    # ⭐ Sono l'ECCEZIONE al lock post-DRAFT, e la ragione e' di merito: non
    #   toccano prezzo, validita' o perimetro, e non producono nessun effetto
    #   finche' la fattura non ne fa lo snapshot (I4). Negli appalti PA il CIG
    #   arriva quando arriva, e puo' arrivare a contratto gia' ATTIVO: negarlo
    #   costringerebbe a creare un contratto nuovo PER UN PEZZO DI CARTA.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_contratto_attivo_ammette_codici_atto(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = {
            **_testata_default(),
            "stato_codice_interno": "ATTIVO",
        }
        repo.update_contratto.return_value = True
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().update_contratto(1, {
            "codice_cig": "1234567890ABCDE",
            "codice_cup": "H51B09000000001",
            "codice_commessa": "CONV-2026/17",
        })

        data = repo.update_contratto.call_args.args[1]
        self.assertEqual(data["codice_cig"], "1234567890ABCDE")
        self.assertEqual(data["codice_cup"], "H51B09000000001")
        self.assertEqual(data["codice_commessa"], "CONV-2026/17")

    # Scopo: stringa vuota su un riferimento dell'atto -> NULL, non ''.
    # ⚠️ `feedback_null_vs_empty`: un '' sarebbe un valore che SEMBRA un codice,
    #   e finirebbe nel blocco XML della FatturaPA come tag vuoto.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_contratto_codice_atto_vuoto_diventa_null(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()
        repo.update_contratto.return_value = True
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().update_contratto(1, {"codice_cig": "   "})

        data = repo.update_contratto.call_args.args[1]
        self.assertIn("codice_cig", data)
        self.assertIsNone(data["codice_cig"])

    # Scopo: un CIG piu' lungo della colonna e' respinto dal service.
    # ⚠️ Senza il guard arriverebbe come DataError del driver, cioe' come 500 con
    #   un messaggio che nomina una colonna invece del campo compilato.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_contratto_codice_atto_troppo_lungo(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().update_contratto(1, {"codice_cig": "X" * 16})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        repo.update_contratto.assert_not_called()

    # Scopo: contratto CESSATO -> nessun rifiuto Python: a contratto chiuso
    #        tutto fermo lo dice il lock di testata (D-8, E_DOC_CHIUSO), anche
    #        per i riferimenti dell'atto. Il service passa la scrittura.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_contratto_cessato_decide_il_db(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = {
            **_testata_default(),
            "stato_codice_interno": "CESSATO",
        }
        repo.update_contratto.return_value = True
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().update_contratto(1, {"codice_cig": "1234567890ABCDE"})
        self.assertEqual(
            repo.update_contratto.call_args.args[1]["codice_cig"], "1234567890ABCDE",
        )

    # Scopo: contratto ATTIVO -> create_riga rifiutato col codice del DB
    #        (E_RIGA_DOC_NON_BOZZA: lo stesso di trgfn_doc_righe_lock_fuori_bozza
    #        su contratti_righe), frase a catalogo con l'etichetta dal numero.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_riga_rifiutata_su_contratto_attivo(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = {
            **_testata_default(),
            "stato_codice_interno": "ATTIVO",
        }

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().create_riga(1, {
                "articolo_id": "uuid",
                "uom_operativa_id": 1,
                "prezzo_unitario": "10",
                "qta_operativa": "1",
            })
        self.assertEqual(ctx.exception.code, "E_RIGA_DOC_NON_BOZZA")
        self.assertEqual(
            ctx.exception.message,
            "Contratto CNT0000001 non e' piu' in bozza (stato ATTIVO): le sue "
            "righe si possono aggiungere solo finche' e' in bozza.",
        )
        self.assertEqual(ctx.exception.context["operazione"], "INSERT")

    # Scopo: contratto ATTIVO -> update_riga rifiutato (risale dal contratto
    #        della riga via get_riga).
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_riga_rifiutata_su_contratto_attivo(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_riga.return_value = {"id": 99, "contratto_id": 1}
        repo.get_contratto.return_value = {
            **_testata_default(),
            "stato_codice_interno": "ATTIVO",
        }

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().update_riga(99, {"prezzo_unitario": "20"})
        self.assertEqual(ctx.exception.code, "E_RIGA_DOC_NON_BOZZA")
        self.assertIn(" modificare ", ctx.exception.message)

    # Scopo: contratto ATTIVO -> delete_riga rifiutato.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_delete_riga_rifiutata_su_contratto_attivo(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_riga.return_value = {"id": 99, "contratto_id": 1}
        repo.get_contratto.return_value = {
            **_testata_default(),
            "stato_codice_interno": "ATTIVO",
        }

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().delete_riga(99)
        self.assertEqual(ctx.exception.code, "E_RIGA_DOC_NON_BOZZA")
        self.assertIn(" togliere ", ctx.exception.message)

    # Scopo: contratto ATTIVO -> la fornitura: lo stato lo giudica il lock
    #        «solo in bozza» dei satelliti a DB (`E_DOC_DATI_COLLEGATI_NON_BOZZA`,
    #        brief-db-testata-dopo-emissione §11, R-BE-6). Il service non ha
    #        piu' `_assert_contratto_draft` e passa la scrittura.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_utility_su_contratto_attivo_decide_il_db(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = {
            **_testata_default(),
            "stato_codice_interno": "ATTIVO",
        }
        repo.get_utility.return_value = {"id": 1}

        ContrattiService().create_utility(
            1, {"tipo_utenza_id": 2, "classe_utenza_id": 7},
        )
        repo.create_utility.assert_called_once()

    # Scopo: idem per update_utility.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_utility_su_contratto_attivo_decide_il_db(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "ATTIVO"
        repo.get_utility.return_value = {
            "id": 1, "istanza_utility_id": 20, "utility_id": 3,
        }

        ContrattiService().update_utility(1, {"tipo_utenza_id": 5})
        repo.update_utility.assert_called_once()

    # Scopo: cessazione immediata (valido_al passata) -> applica entrambi
    #        in transazione: PATCH valido_al + UPDATE stato CESSATO.
    @patch("apps.vendite.services.contratti_service.transaction.atomic")
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_cambia_stato_cessazione_immediata_data_passata(self, repo_cls, _atomic):
        from apps.vendite.services.contratti_service import ContrattiService

        ieri = oggi_aziendale() - timedelta(days=1)
        repo = repo_cls.return_value
        repo.get_stato_id_by_codice.return_value = 5  # CESSATO id
        repo.update_contratto.return_value = True
        repo.update_stato.return_value = True
        repo.get_contratto.return_value = {
            **_testata_default(),
            "stato_codice_interno": "CESSATO",
        }
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        result = ContrattiService().cambia_stato(
            1, codice_interno="CESSATO", valido_al=ieri,
        )

        # update_contratto chiamato per valido_al, poi update_stato.
        repo.update_contratto.assert_called_once_with(1, {"valido_al": ieri})
        repo.update_stato.assert_called_once_with(1, 5)
        self.assertEqual(result["stato_codice_interno"], "CESSATO")

    # Scopo: cessazione PROGRAMMATA (valido_al futura) -> applica solo
    #        PATCH valido_al, lo stato resta invariato. Il job notturno
    #        DB allineera' a CESSATO quando la data scade.
    @patch("apps.vendite.services.contratti_service.transaction.atomic")
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_cambia_stato_cessazione_programmata_data_futura(self, repo_cls, _atomic):
        from apps.vendite.services.contratti_service import ContrattiService

        domani = oggi_aziendale() + timedelta(days=1)
        repo = repo_cls.return_value
        repo.get_stato_id_by_codice.return_value = 5
        repo.update_contratto.return_value = True
        repo.get_contratto.return_value = {
            **_testata_default(),
            "stato_codice_interno": "ATTIVO",  # stato resta ATTIVO post-call
        }
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        result = ContrattiService().cambia_stato(
            1, codice_interno="CESSATO", valido_al=domani,
        )

        # Solo PATCH valido_al; UPDATE stato NON chiamato (programmazione).
        repo.update_contratto.assert_called_once_with(1, {"valido_al": domani})
        repo.update_stato.assert_not_called()
        self.assertEqual(result["stato_codice_interno"], "ATTIVO")

    # Scopo: cessazione data ODIERNA -> cessazione IMMEDIATA. La data == oggi
    #        non e' programmazione futura: il contratto passa subito a CESSATO
    #        (e' la data di fine validita' a confermare). PATCH valido_al +
    #        UPDATE stato entrambi chiamati. Solo data > oggi e' programmata.
    @patch("apps.vendite.services.contratti_service.transaction.atomic")
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_cambia_stato_cessazione_data_oggi_e_immediata(self, repo_cls, _atomic):
        from apps.vendite.services.contratti_service import ContrattiService

        oggi = oggi_aziendale()
        repo = repo_cls.return_value
        repo.get_stato_id_by_codice.return_value = 5
        repo.update_contratto.return_value = True
        repo.update_stato.return_value = True
        repo.get_contratto.return_value = {
            **_testata_default(),
            "stato_codice_interno": "ATTIVO",
        }
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().cambia_stato(
            1, codice_interno="CESSATO", valido_al=oggi,
        )

        # Data odierna = immediata: PATCH valido_al + UPDATE stato a CESSATO.
        repo.update_contratto.assert_called_once_with(1, {"valido_al": oggi})
        repo.update_stato.assert_called_once_with(1, 5)

    # Scopo: cessazione SENZA valido_al rifiutata (data obbligatoria per
    #        CESSATO: forza UI a passare dal dialog dedicato).
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_cambia_stato_cessato_senza_valido_al_rifiutato(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_stato_id_by_codice.return_value = 5

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().cambia_stato(1, codice_interno="CESSATO")
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertIn("Data cessazione obbligatoria", ctx.exception.message)
        repo.update_contratto.assert_not_called()
        repo.update_stato.assert_not_called()

    # Scopo: cambia_stato senza valido_al -> non chiama update_contratto.
    # NB refactor 2026-05-28: ATTIVO non passa piu' da cambia_stato (guard
    # rinvia a /emetti/). Test riportato su ANNULLATO che non richiede valido_al.
    @patch("apps.vendite.services.contratti_service.transaction.atomic")
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_cambia_stato_senza_valido_al_no_patch(self, repo_cls, _atomic):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_stato_id_by_codice.return_value = 9  # SOSPESO id
        repo.get_stato_codice.return_value = "ATTIVO"
        repo.update_stato.return_value = True
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().cambia_stato(1, codice_interno="SOSPESO")

        repo.update_contratto.assert_not_called()
        repo.update_stato.assert_called_once_with(1, 9)

    # brief-db-annullo-documento-con-legami: ANNULLATO passa SEMPRE dal verbo
    # `fn_annulla_contratto`, con la dichiarazione della conferma.
    @patch("apps.vendite.services.contratti_service.transaction.atomic")
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_annullo_passa_dal_verbo(self, repo_cls, _atomic):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_stato_id_by_codice.return_value = 4
        repo.get_stato_codice.return_value = "DRAFT"
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().cambia_stato(1, codice_interno="ANNULLATO", legami_confermati=2)

        repo.annulla.assert_called_once_with(1, 2)
        repo.update_stato.assert_not_called()

    # Scopo: cambia_stato con valido_al < valido_dal NON lo giudica il
    #        service: la data arriva al DB, dove il guard comune delle date
    #        risponde E_DATA_AL_MINORE_DAL col campo `valido_al` (provato sul
    #        DB vero in apps/core/tests/db/test_date_validita_guard_comune_db).
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_cambia_stato_delega_ordine_date_al_db(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_stato_id_by_codice.return_value = 5  # CESSATO id
        repo.get_contratto.return_value = {
            **_testata_default(),
            "valido_dal": date(2026, 6, 1),
        }

        ContrattiService().cambia_stato(
            1, codice_interno="CESSATO", valido_al=date(2026, 1, 1),
        )
        repo.update_contratto.assert_called_once_with(1, {"valido_al": date(2026, 1, 1)})

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_contratto_campi_vuoto_fallisce(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().update_contratto(1, {})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_contratto_ok_variazione(self, repo_cls):
        """Update happy path: variazione globale PERCENTUALE accettata sulla testata.

        Refactor 2026-05-18: VALORE_FISSO non e' piu' ammesso come variazione
        globale (decisione di dominio: resta solo per OVERRIDE su singola
        riga). Vedi `test_update_contratto_variazione_valore_fisso_rifiutata`.
        """
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.update_contratto.return_value = True
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().update_contratto(1, {
            "listino_id": 200,
            "tipo_variazione_globale": "PERCENTUALE",
            "valore_variazione_globale": "-5",
        })

        args = repo.update_contratto.call_args.args
        self.assertEqual(args[0], 1)
        self.assertEqual(args[1]["listino_id"], 200)
        self.assertEqual(args[1]["tipo_variazione_globale"], "PERCENTUALE")
        self.assertEqual(args[1]["valore_variazione_globale"], Decimal("-5"))

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_contratto_variazione_valore_fisso_rifiutata(self, repo_cls):
        """VALORE_FISSO sulla testata → E_VENDITE_VALIDATION (decisione 2026-05-18)."""
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().update_contratto(1, {
                "tipo_variazione_globale": "VALORE_FISSO",
                "valore_variazione_globale": "5",
            })
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        # Verifica messaggio parlante: cita VALORE_FISSO non ammesso + suggerimento OVERRIDE
        self.assertIn("VALORE_FISSO", ctx.exception.detail)
        self.assertIn("OVERRIDE", ctx.exception.detail)
        # ⭐ Dal 2026-09-18 (BB `extract_optional_enum`) il rifiuto NOMINA il
        #    campo: la copia locale scriveva `{"tipo_variazione_globale": tipo}`
        #    e il form non accendeva niente.
        self.assertEqual(ctx.exception.context["field"], "tipo_variazione_globale")

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_contratto_variazione_none_azzera(self, repo_cls):
        """Tre stati del PATCH: `tipo_variazione_globale: null` AZZERA la
        variazione (e' una scrittura, non un campo saltato) — il caso che
        `extract_optional_enum(nullable=True)` deve distinguere da «assente»."""
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.update_contratto.return_value = True
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = None

        ContrattiService().update_contratto(1, {
            "tipo_variazione_globale": None,
            "valore_variazione_globale": None,
        })
        args = repo.update_contratto.call_args.args
        self.assertIn("tipo_variazione_globale", args[1])
        self.assertIsNone(args[1]["tipo_variazione_globale"])

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_contratto_ambito_fuori_vocabolario_nomina_il_campo(
        self, repo_cls,
    ):
        """`ambito` (BB `require_enum`, 2026-09-18): il vocabolario resta del
        dominio, il rifiuto porta il campo — anche quando il valore non e'
        una stringa, che prima sarebbe stato un `AttributeError` su `.strip()`
        (cioe' un 500). Stesso payload del caso felice A, con il solo ambito
        sbagliato."""
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []
        base = {
            "billing_account_id": 10, "istanza_utility_id": 20, "utility_id": 3,
            "valido_dal": "2026-01-01", "valido_al": "2026-12-31", "listino_id": 100,
        }
        for raw in ("RETAIL", "", None, 7):
            with self.subTest(raw=raw):
                with self.assertRaises(ServiceError) as ctx:
                    ContrattiService().create_contratto({**base, "ambito": raw})
                self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
                self.assertEqual(ctx.exception.context["field"], "ambito")
        repo.create_contratto_atomico.assert_not_called()

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_contratto_non_giudica_le_versioni_del_listino(self, repo_cls):
        """D.4.3 di brief-db-offerta-emissione-ed-erogazione (Tid, 2026-10-07).

        Un listino senza versione in vigore si sceglie in DRAFT, come
        sull'offerta: la regola vera è «non si attiva senza una versione in
        vigore», e la dice il DB all'attivazione
        (`E_CONTRATTO_ATTIVAZIONE_SENZA_VERSIONE_LISTINO`). Il service non
        legge più le versioni del listino e passa la scrittura al DB.
        """
        from apps.vendite.services import contratti_service
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.create_contratto_atomico.return_value = 1
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().create_contratto({
            "billing_account_id": 10,
            "istanza_utility_id": 20,
            "utility_id": 3,
            "valido_dal": "2026-01-01",
            "listino_id": 100,
        })
        repo.create_contratto_atomico.assert_called_once()
        self.assertFalse(hasattr(contratti_service, "ListiniRepository"))

    # Scopo: refactor 2026-05-15. update_riga non puo' settare prezzo NULL
    # su riga OVERRIDE esistente (la coerenza tipo/prezzo va salvaguardata).
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_riga_override_prezzo_null_fallisce(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_riga.return_value = {
            "id": 5, "contratto_id": 1, "tipo_eccezione": "OVERRIDE",
            "prezzo_unitario": Decimal("10"),
        }
        repo.get_contratto.return_value = _testata_default()  # DRAFT

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().update_riga(5, {"prezzo_unitario": None})

        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertIn("prezzo_unitario obbligatorio", ctx.exception.detail or "")
        repo.update_riga.assert_not_called()

    # ⚠️ Il PATCH di una riga ESCLUSIONE non ha piu' un test qui: dal
    # 2026-10-04 lo rifiuta il guard DB `_a05_` (E_CONTRATTO_ESCLUSIONE_NON_MODIFICABILE),
    # e un repository mockato non lo vede. Lo prova
    # `tests/db/test_contratto_esclusione_non_modificabile_db`.

    # Scopo: BE 2.6. get_contesto_pricing delega al repository e ritorna
    # l'envelope per il banner FE.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_get_contesto_pricing(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.resolve_contesto_pricing_contratto.return_value = {
            "contratto_id": 1,
            "forma": "con_listino",
            "stato_codice_interno": "ATTIVO",
            "listino_id": 100,
            "listino_codice": "LST-001",
            "listino_versione_id": 5,
            "listino_versione_codice": "V5",
            "listino_versione_fissata": True,
            "tipo_variazione_globale": "PERCENTUALE",
            "valore_variazione_globale": Decimal("-5"),
            "categoria_cliente_id": 7,
            "categoria_cliente_codice": "PREMIUM",
            "categoria_cliente_descrizione": "Cliente premium",
        }

        result = ContrattiService().get_contesto_pricing(1)

        self.assertEqual(result["forma"], "con_listino")
        self.assertEqual(result["listino_versione_id"], 5)
        self.assertTrue(result["listino_versione_fissata"])
        repo.resolve_contesto_pricing_contratto.assert_called_once_with(1)

    # Scopo: refactor §3-bis-E. Gate L2 sulla variazione globale del contratto
    # al PATCH testata. Sconto PERCENTUALE oltre soglia -> E_PRICING_SCONTO_ECCESSIVO.
    @patch("apps.vendite.services._pricing_gate_helpers.BillingAccountRepository")
    @patch("apps.vendite.services._pricing_gate_helpers.ParameterService")
    @patch("apps.vendite.services._pricing_gate_helpers.get_user_model")
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_contratto_gate_l2_variazione_globale_sconto_eccessivo(
        self, repo_cls, mock_get_user_model, mock_param_service, mock_ba_repo,
    ):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()
        # Mock user non-superuser
        user_mock = MagicMock()
        user_mock.is_superuser = False
        mock_get_user_model.return_value.objects.get.return_value = user_mock
        # Soglia max sconto 10%
        mock_param_service.return_value.get_emittente_fiscale_id_for_user.return_value = 5
        mock_param_service.return_value.get_parameter_decimal.return_value = Decimal("10")
        mock_ba_repo.return_value.get_categoria_cliente_id.return_value = 7

        # PATCH variazione globale a -20% (oltre soglia 10%).
        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().update_contratto(
                1,
                {
                    "tipo_variazione_globale": "PERCENTUALE",
                    "valore_variazione_globale": "-20",
                },
                auth_user_id=42,
            )

        self.assertEqual(ctx.exception.code, "E_PRICING_SCONTO_ECCESSIVO")
        self.assertTrue(ctx.exception.retryable)
        repo.update_contratto.assert_not_called()

    # Scopo: il listino sotto le righe lo giudica il DB, per contratto e
    #        offerta (`script.trgfn_doc_guard_listino_con_righe`,
    #        brief-db-testata-dopo-emissione §11, R-DB-4 e R-BE-5). Il service
    #        non conta piu' righe ne' eccezioni: passa la scrittura, e il 422
    #        (`E_DOC_LISTINO_CAMBIO_CON_RIGHE`) arriva dal DB.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_contratto_cambio_listino_decide_il_db(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()  # listino_id=100
        repo.update_contratto.return_value = True
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().update_contratto(1, {"listino_id": 200})

        self.assertEqual(repo.update_contratto.call_args.args[1]["listino_id"], 200)

    # Scopo: idem per la rimozione del listino (`E_DOC_LISTINO_RIMOZIONE_CON_ECCEZIONI`
    #        dal DB): `null` arriva al repository.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_contratto_rimozione_listino_decide_il_db(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()  # listino_id=100
        repo.update_contratto.return_value = True
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().update_contratto(1, {"listino_id": None})

        self.assertIsNone(repo.update_contratto.call_args.args[1]["listino_id"])

    # --- cambio stato --------------------------------------------------

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_cambia_stato_codice_sconosciuto(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo_cls.return_value.get_stato_id_by_codice.return_value = None

        # Uso un codice non riconosciuto qualsiasi (non ATTIVO che ora ha
        # un guard dedicato che fa scattare prima del lookup).
        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().cambia_stato(1, codice_interno="FROBOZ")
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: refactor 2026-05-28 - cambia_stato non gestisce piu' ATTIVO.
    # L'invariante "ATTIVO => almeno una versione PDF" e' garantita dal
    # nuovo flusso `ApiContrattoEmetti` che orchestra atomic state +
    # genera_documento + allegati nella view. cambia_stato fail-fast con
    # E_VENDITE_VALIDATION se invocato direttamente con 'ATTIVO'.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_cambia_stato_rifiuta_attivo(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().cambia_stato(1, codice_interno="ATTIVO")
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        # Nessuna chiamata al repo: il guard scatta prima del lookup stato.
        repo_cls.return_value.update_stato.assert_not_called()

    # Scopo: marker DB "contratto senza listino e nessuna AGGIUNTA" -> codice
    # specifico E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE. Test riportato su
    # emetti() (refactor 2026-05-28): l'attivazione passa da li'.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_emetti_negoziato_puro_senza_righe_tradotto(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_stato_id_by_codice.return_value = 2  # ATTIVO id
        repo.update_stato.side_effect = DatabaseError(
            "contratto senza listino e nessuna riga AGGIUNTA con prezzo: "
            "serve almeno un'AGGIUNTA prima di attivare."
        )

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().emetti(1)
        self.assertEqual(ctx.exception.code, "E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE")

    # Scopo: `emetti()` thin wrapper sul repo che bypassa il guard di
    # cambia_stato (l'orchestrazione atomic state+genera+allegati vive nella
    # view ApiContrattoEmetti).
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_emetti_delega_a_repo(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_stato_id_by_codice.return_value = 2  # ATTIVO id
        repo.update_stato.return_value = True
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().emetti(1)

        repo.update_stato.assert_called_once_with(1, 2)

    # Scopo: la sovrapposizione la rifiuta il guard della transizione del DB
    #        (2026-10-19, `script.fn_check_contratto_sovrapposto`) col codice del
    #        catalogo, che passa com'e' con la sua frase: il backend non ha piu'
    #        una copia Python della regola (che scattava solo alla conferma).
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_emetti_sovrapposto_lo_rifiuta_il_db(self, repo_cls):
        from apps.core.tests.db_error_fakes import make_db_error
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_stato_id_by_codice.return_value = 2  # ATTIVO id
        repo.update_stato.side_effect = make_db_error(
            "Il periodo si sovrappone al contratto CNT0000027, gia' vincolante.",
            codice="E_CONTRATTO_OVERLAP_ESISTENTE",
        )

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().emetti(1)
        self.assertEqual(ctx.exception.code, "E_CONTRATTO_OVERLAP_ESISTENTE")
        self.assertIn("CNT0000027", ctx.exception.message or "")

    # --- righe ---------------------------------------------------------

    # Refactor modalita 2026-05-15: il vecchio test
    # `test_create_riga_modalita_C_senza_prezzo_tradotto` testava il trigger
    # DB di modalita C (droppato in step 2.1). Sostituito da test sulla
    # coerenza tipo_eccezione/prezzo (validazione service pre-DB).
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_riga_override_senza_prezzo_fallisce(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()  # DRAFT
        # Articolo non composito: il bypass del modello unificato BoM
        # (Decimal('0') placeholder per padri compositi) non scatta;
        # OVERRIDE/AGGIUNTA con prezzo None deve fallire.
        repo.is_articolo_composito.return_value = False

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().create_riga(
                1,
                {
                    "articolo_id": "00000000-0000-0000-0000-000000000001",
                    "tipo_eccezione": "OVERRIDE",
                },
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertIn("prezzo_unitario obbligatorio", ctx.exception.detail or "")
        repo.create_riga.assert_not_called()

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_riga_esclusione_con_prezzo_arriva_al_db(self, repo_cls):
        # ⛔ Nessun 400 del service sul prezzo di un'ESCLUSIONE: e' uno dei
        #    dieci dati che il guard DB rifiuta col campo
        #    (E_RIGA_ESCLUSIONE_CON_DATI, R-BE-3). Il rifiuto vero lo prova
        #    `test_contratto_esclusione_non_modificabile_db` sul DB.
        from apps.vendite.services.contratti_service import ContrattiService

        class _ArrivatoAlRepo(Exception):
            pass

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()  # DRAFT
        repo.create_riga.side_effect = _ArrivatoAlRepo

        with self.assertRaises(_ArrivatoAlRepo):
            ContrattiService().create_riga(
                1,
                {
                    "articolo_id": "00000000-0000-0000-0000-000000000001",
                    "tipo_eccezione": "ESCLUSIONE",
                    "prezzo_unitario": "10",
                },
            )

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_riga_tipo_eccezione_obbligatorio(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()  # DRAFT

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().create_riga(
                1,
                {
                    "articolo_id": "00000000-0000-0000-0000-000000000001",
                    "prezzo_unitario": "10",
                    # tipo_eccezione mancante
                },
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertIn("tipo_eccezione obbligatorio", ctx.exception.detail or "")
        repo.create_riga.assert_not_called()

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_riga_ok(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()  # DRAFT
        # Articolo NON composito: evita il branch auto-init componenti BoM
        # (modello unificato 2026-05-13). Il branch composito viene testato
        # nei test ContrattiServiceComponentiTests.
        repo.is_articolo_composito.return_value = False
        repo.create_riga.return_value = 77
        repo.get_riga.return_value = {"id": 77, "prezzo_unitario": Decimal("25.50")}

        result = ContrattiService().create_riga(
            1,
            {
                "articolo_id": "00000000-0000-0000-0000-000000000001",
                "tipo_eccezione": "OVERRIDE",
                "prezzo_unitario": "25.50",
                "ordine": 10,
            },
        )

        self.assertEqual(result["id"], 77)
        args = repo.create_riga.call_args.args
        self.assertEqual(args[0], 1)
        self.assertEqual(args[1]["prezzo_unitario"], Decimal("25.50"))
        self.assertEqual(args[1]["tipo_eccezione"], "OVERRIDE")

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_riga_rifiuta_articolo_id(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_riga.return_value = {"id": 77, "contratto_id": 1}
        repo.get_contratto.return_value = _testata_default()  # DRAFT

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().update_riga(77, {"articolo_id": "...".ljust(36, "0")})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_riga_ok(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_riga.return_value = {"id": 77, "contratto_id": 1, "prezzo_unitario": Decimal("30")}
        repo.get_contratto.return_value = _testata_default()  # DRAFT
        repo.update_riga.return_value = True

        ContrattiService().update_riga(77, {"prezzo_unitario": "30"})

        args = repo.update_riga.call_args.args
        self.assertEqual(args[0], 77)
        self.assertEqual(args[1]["prezzo_unitario"], Decimal("30"))

    # =========================================================================
    # Cablaggio gate L1+L2+L3 in create_riga / update_riga (refactor 2026-05-19
    # BE porting gate riga contratti, debito tecnico §7.6 chiuso).
    # =========================================================================

    @patch(
        "apps.vendite.services.contratti_service."
        "resolve_or_check_override_prezzo_riga_contratto"
    )
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_riga_override_invoca_gate(self, repo_cls, mock_gate):
        # Scopo: OVERRIDE invoca il BB orchestratore L1+L2+L3 (zero gate L2
        # violazione qui — verifichiamo solo che venga chiamato e che il
        # prezzo normalizzato finisca nei data di INSERT).
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()
        repo.create_riga.return_value = 77
        repo.get_riga.return_value = {"id": 77, "prezzo_unitario": Decimal("25.50")}
        repo.is_articolo_composito.return_value = False
        mock_gate.return_value = (
            Decimal("25.50"),
            {"origine_prezzo": "MANUALE", "override_user_id": 42},
        )

        ContrattiService().create_riga(
            1,
            {
                "articolo_id": "00000000-0000-0000-0000-000000000001",
                "tipo_eccezione": "OVERRIDE",
                "prezzo_unitario": "25.50",
            },
            auth_user_id=42,
        )

        mock_gate.assert_called_once()
        kwargs = mock_gate.call_args.kwargs
        self.assertEqual(kwargs["auth_user_id"], 42)
        self.assertFalse(kwargs["richiesta_approvazione"])
        # Meta audit del gate mergiato nei data riga.
        data = repo.create_riga.call_args.args[1]
        self.assertEqual(data["meta"]["origine_prezzo"], "MANUALE")
        self.assertEqual(data["prezzo_unitario"], Decimal("25.50"))

    @patch(
        "apps.vendite.services.contratti_service."
        "resolve_or_check_override_prezzo_riga_contratto"
    )
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_riga_esclusione_skip_gate(self, repo_cls, mock_gate):
        # Scopo: ESCLUSIONE non passa per il gate (prezzo NULL per design,
        # nessun resolver da invocare). Decisione Alternativa B 2026-05-18.
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()
        repo.create_riga.return_value = 77
        repo.get_riga.return_value = {"id": 77, "prezzo_unitario": None}
        repo.is_articolo_composito.return_value = False

        ContrattiService().create_riga(
            1,
            {
                "articolo_id": "00000000-0000-0000-0000-000000000001",
                "tipo_eccezione": "ESCLUSIONE",
                "prezzo_unitario": None,
            },
            auth_user_id=42,
        )

        mock_gate.assert_not_called()

    @patch(
        "apps.vendite.services.contratti_service._orchestrate_l3_request_contratto"
    )
    @patch(
        "apps.vendite.services.contratti_service."
        "resolve_or_check_override_prezzo_riga_contratto"
    )
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_riga_l3_richiesta_approvazione_pending(
        self, repo_cls, mock_gate, mock_orchestrate,
    ):
        # Scopo: gate L2 viola + richiesta_approvazione=True → riga salvata
        # con stato_approvazione_prezzo=PENDING + FK pratica + link riga<->pratica.
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()
        repo.create_riga.return_value = 99
        repo.get_riga.return_value = {"id": 99, "prezzo_unitario": Decimal("15")}
        repo.is_articolo_composito.return_value = False
        # gate ritorna meta `richiesta_approvazione_pending` (workflow L3).
        mock_gate.return_value = (
            Decimal("15"),
            {
                "origine_prezzo": "MANUALE",
                "richiesta_approvazione_pending": True,
                "violazione_l2": {
                    "tipo_violazione": "SCONTO",
                    "variazione_abs_pct": "50.00",
                    "limite_pct": "20",
                },
                "prezzo_base_resolver": "30",
            },
        )
        mock_orchestrate.return_value = 555  # pratica_id

        with patch(
            "apps.vendite.services.approvazioni_prezzo_service.link_riga_a_pratica"
        ) as mock_link:
            ContrattiService().create_riga(
                1,
                {
                    "articolo_id": "00000000-0000-0000-0000-000000000001",
                    "tipo_eccezione": "OVERRIDE",
                    "prezzo_unitario": "15",
                    "richiesta_approvazione": True,
                },
                auth_user_id=42,
            )

        # Orchestrate L3 chiamato con riga_id_for_link=None (pratica creata
        # PRIMA dell'INSERT riga).
        mock_orchestrate.assert_called_once()
        self.assertIsNone(mock_orchestrate.call_args.kwargs["riga_id_for_link"])
        # Data riga PENDING + FK pratica popolata.
        data = repo.create_riga.call_args.args[1]
        self.assertEqual(data["stato_approvazione_prezzo"], "PENDING")
        self.assertEqual(data["pratica_approvazione_prezzo_id"], 555)
        # Link riga -> pratica post-INSERT con sorgente=contratto.
        mock_link.assert_called_once_with(
            pratica_id=555, riga_id=99, sorgente="contratto",
        )

    @patch(
        "apps.vendite.services.contratti_service."
        "resolve_or_check_override_prezzo_riga_contratto"
    )
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_riga_aggiunta_senza_base_resolver_skip_l2(
        self, repo_cls, mock_gate,
    ):
        # Scopo: AGGIUNTA su articolo che il resolver non trova in matrice
        # categoria/promo → meta None, prezzo manuale puro accettato (L1
        # passed implicitamente nel mock, L2/L3 skip). Alternativa B 2026-05-18.
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()
        repo.create_riga.return_value = 88
        repo.get_riga.return_value = {"id": 88, "prezzo_unitario": Decimal("100")}
        repo.is_articolo_composito.return_value = False
        mock_gate.return_value = (Decimal("100"), None)  # nessuna base resolver

        ContrattiService().create_riga(
            1,
            {
                "articolo_id": "00000000-0000-0000-0000-000000000002",
                "tipo_eccezione": "AGGIUNTA",
                "prezzo_unitario": "100",
            },
            auth_user_id=42,
        )

        mock_gate.assert_called_once()
        data = repo.create_riga.call_args.args[1]
        # Nessun meta_patch -> data["meta"] non valorizzato dal gate.
        self.assertNotIn("stato_approvazione_prezzo", data)
        self.assertEqual(data["prezzo_unitario"], Decimal("100"))

    @patch(
        "apps.vendite.services.contratti_service."
        "resolve_or_check_override_prezzo_riga_contratto"
    )
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_riga_override_invoca_gate(self, repo_cls, mock_gate):
        # Scopo: update_riga su OVERRIDE con prezzo_unitario nel PATCH →
        # gate invocato. Verifica passaggio di articolo_id/uom_id da
        # existing_riga.
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()
        repo.get_riga.return_value = {
            "id": 77, "contratto_id": 1,
            "articolo_id": "00000000-0000-0000-0000-000000000001",
            "tipo_eccezione": "OVERRIDE",
            "uom_operativa_id": 5,
            "prezzo_unitario": Decimal("30"),
            "meta": {},
        }
        repo.update_riga.return_value = True
        mock_gate.return_value = (Decimal("28"), {"origine_prezzo": "MANUALE"})

        ContrattiService().update_riga(
            77, {"prezzo_unitario": "28"}, auth_user_id=42,
        )

        mock_gate.assert_called_once()
        kwargs = mock_gate.call_args.kwargs
        self.assertEqual(kwargs["articolo_id"], "00000000-0000-0000-0000-000000000001")
        self.assertEqual(kwargs["uom_id"], 5)
        self.assertEqual(kwargs["payload_prezzo"], Decimal("28"))

    @patch(
        "apps.vendite.services.contratti_service."
        "resolve_or_check_override_prezzo_riga_contratto"
    )
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_riga_skip_gate_se_prezzo_non_in_patch(
        self, repo_cls, mock_gate,
    ):
        # Scopo: PATCH che NON tocca prezzo_unitario non invoca il gate
        # (ottimizzazione: niente lookup testata/get_riga inutile per puro
        # cambio di ordine/qta).
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_riga.return_value = {"id": 77, "contratto_id": 1}
        repo.get_contratto.return_value = _testata_default()
        repo.update_riga.return_value = True

        ContrattiService().update_riga(77, {"ordine": 50}, auth_user_id=42)

        mock_gate.assert_not_called()

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_delete_riga_not_found(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_riga.return_value = {"id": 77, "contratto_id": 1}
        repo.get_contratto.return_value = _testata_default()  # DRAFT
        repo.delete_riga.return_value = False

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().delete_riga(77)
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")

    # --- utility 1:1 ---------------------------------------------------

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_utility_tipo_classe_obbligatori_tradotto(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()
        repo.create_utility.side_effect = DatabaseError(
            "Contratto utility GAS: tipo_utenza_id e classe_utenza_id sono obbligatori."
        )

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().create_utility(1, {})
        self.assertEqual(
            ctx.exception.code, "E_CONTRATTO_UTILITY_TIPO_CLASSE_OBBLIGATORI"
        )

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_utility_ok(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()
        repo.create_utility.return_value = 9
        repo.get_utility.return_value = {
            "id": 9,
            "contratto_id": 1,
            "istanza_utility_id": 20,
            "utility_id": 3,
        }

        ContrattiService().create_utility(
            1,
            {"tipo_utenza_id": 2, "classe_utenza_id": 7},
        )

        args = repo.create_utility.call_args.args
        self.assertEqual(args[0], 1)
        # istanza e utility derivati dalla testata, non dal payload.
        self.assertEqual(args[1]["istanza_utility_id"], 20)
        self.assertEqual(args[1]["utility_id"], 3)
        self.assertEqual(args[1]["tipo_utenza_id"], 2)

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_utility_immutabili_rifiutati(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()  # DRAFT
        repo.get_utility.return_value = {
            "id": 9,
            "istanza_utility_id": 20,
            "utility_id": 3,
        }

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().update_utility(1, {"utility_id": 999})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: REGRESSIONE review — patch solo sulla variazione globale, senza
    #        listino_id nel payload, su contratto modalita' A/B esistente: il
    #        validator modalita' deve leggere listino_id corrente dal DB, NON
    #        trattare l'assenza come "listino_id=NULL -> modalita' C".
    #        Bug trovato in review: `existing=None` passato sempre -> falso
    #        positivo "modalita' C: tipo/valore devono essere NULL".
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_contratto_modalita_B_con_listino_esistente_patch_solo_variazione(
        self, repo_cls
    ):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        # Contratto esistente modalita' B: listino presente, niente variazione.
        existing = {
            **_testata_default(),
            "listino_id": 100,
            "tipo_variazione_globale": None,
            "valore_variazione_globale": None,
        }
        repo.get_contratto.return_value = existing
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []
        repo.update_contratto.return_value = True

        # Patch: aggiungo variazione globale (passaggio da B ad A).
        result = ContrattiService().update_contratto(1, {
            "tipo_variazione_globale": "PERCENTUALE",
            "valore_variazione_globale": "7",
        })

        self.assertEqual(result["id"], 1)
        args = repo.update_contratto.call_args.args
        self.assertEqual(args[0], 1)
        self.assertEqual(args[1]["tipo_variazione_globale"], "PERCENTUALE")
        self.assertEqual(args[1]["valore_variazione_globale"], Decimal("7"))


# Scopo: REGRESSIONE — la creazione contratto passa `meta` (dict) come oggetto
#        JSON annidato dentro il jsonb `p_testata` della fn madre create_contratto_atomico.
class ContrattiRepositoryJsonbTests(TestCase):
    @patch("apps.vendite.db.contratti_repository.connection")
    def test_create_contratto_atomico_serializza_meta_nel_testata_jsonb(self, mock_connection):
        import json

        from apps.vendite.db.contratti_repository import ContrattiRepository

        cursor = MagicMock()
        cursor.fetchone.return_value = (1, "CNT0000001")
        mock_connection.cursor.return_value.__enter__.return_value = cursor

        ContrattiRepository().create_contratto_atomico(
            testata={
                "billing_account_id": 10,
                "istanza_utility_id": 20,
                "utility_id": 3,
                "valido_dal": date(2026, 1, 1),
                "meta": {"note": "test"},
            },
            utility=None,
        )

        sql = cursor.execute.call_args[0][0]
        self.assertIn("fn_create_contratto(%s::jsonb, %s::jsonb)", sql)
        params = cursor.execute.call_args[0][1]
        # p_testata: JSON string con date→ISO e meta come oggetto annidato.
        testata = json.loads(params[0])
        self.assertEqual(testata["meta"], {"note": "test"})
        self.assertEqual(testata["valido_dal"], "2026-01-01")
        # p_utility None → nessuna riga utility.
        self.assertIsNone(params[1])


# ══════════════════════════════════════════════════════════════════════
# Componenti BoM riga contratto (modello unificato 2026-05-13)
# ══════════════════════════════════════════════════════════════════════
# Test specchio del pattern preventivi (test_preventivi_service §componenti):
# preview, list, update, delete con guard scope contratto/riga/componente.


class ContrattiServiceComponentiTests(TestCase):
    """Suite componenti riga contratto (modello unificato BoM 2026-05-13).

    Specchio simmetrico di `PreventiviServiceComponentiTests`. Tutto mockato
    contro `ContrattiRepository` per non dipendere da DB reale.
    """

    def test_normalize_componenti_overrides_dict_invalid(self):
        """Validator solleva su valori non-numero."""
        from apps.vendite.services._componenti_service_helpers import (
            normalize_componenti_overrides,
        )

        with self.assertRaises(ServiceError) as ctx:
            normalize_componenti_overrides(
                {"abc-uuid": "non-numero"},
                function_name="test",
                error_code="E_VENDITE_VALIDATION",
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    def test_normalize_componenti_overrides_empty(self):
        """{} → None (skip path init)."""
        from apps.vendite.services._componenti_service_helpers import (
            normalize_componenti_overrides,
        )

        self.assertIsNone(
            normalize_componenti_overrides(
                {}, function_name="test",
                error_code="E_VENDITE_VALIDATION",
            )
        )

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_preview_componenti_riga_not_found(self, repo_cls):
        """Contratto inesistente → E_VENDITE_NOT_FOUND."""
        from apps.vendite.services.contratti_service import ContrattiService

        repo = MagicMock()
        repo.get_contratto.return_value = None
        repo_cls.return_value = repo

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().preview_componenti_riga(
                999,
                articolo_id="abc",
                uom_operativa_id=1,
                quantita=Decimal("1"),
                auth_user_id=None,
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")

    @patch(
        "apps.vendite.services.contratti_service."
        "resolve_emittente_sr_id_for_testata",
        return_value=99,
    )
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_preview_componenti_riga_ok(self, repo_cls, _mock_resolve):
        """Preview chiama repo.preview_componenti_riga con args derivati dal contratto.

        Post Fix A 2026-05-15: il lookup contesto e' centralizzato in
        `_load_contratto_context_for_pricing` (module-level) che chiama
        l'helper `resolve_emittente_sr_id_for_testata` (anche module-level).
        Il mock va applicato al livello del helper, non al method del service.
        """
        from apps.vendite.services.contratti_service import ContrattiService

        repo = MagicMock()
        repo.get_contratto.return_value = {
            **_testata_default(),
            "valido_dal": date(2026, 5, 1),
            "emittente_fiscale_id": 7,
        }
        repo.preview_componenti_riga.return_value = [
            {"componente_id": "abc", "prezzo_suggerito": "10.00"},
        ]
        repo_cls.return_value = repo

        result = ContrattiService().preview_componenti_riga(
            1,
            articolo_id="comp-uuid",
            uom_operativa_id=2,
            quantita=Decimal("3"),
            auth_user_id=42,
        )

        self.assertEqual(len(result), 1)
        repo.preview_componenti_riga.assert_called_once()
        kwargs = repo.preview_componenti_riga.call_args.kwargs
        self.assertEqual(kwargs["articolo_id"], "comp-uuid")
        self.assertEqual(kwargs["uom_id"], 2)
        self.assertEqual(kwargs["data_riferimento"], date(2026, 5, 1))
        self.assertEqual(kwargs["ba_id"], 10)
        self.assertEqual(kwargs["utility_id"], 3)
        # Emittente risolto internamente dal service (mock → 99)
        self.assertEqual(kwargs["emittente_soggetto_ruolo_id"], 99)

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_list_componenti_riga_riga_fuori_scope(self, repo_cls):
        """Riga appartiene a contratto diverso → E_VENDITE_NOT_FOUND."""
        from apps.vendite.services.contratti_service import ContrattiService

        repo = MagicMock()
        repo.get_riga.return_value = {"id": 5, "contratto_id": 99}
        repo_cls.return_value = repo

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().list_componenti_riga(1, 5)
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_list_componenti_riga_ok(self, repo_cls):
        """List delega al repo passando solo_attivi."""
        from apps.vendite.services.contratti_service import ContrattiService

        repo = MagicMock()
        repo.get_riga.return_value = {"id": 5, "contratto_id": 1}
        repo.list_componenti_riga.return_value = [{"id": 100}]
        repo_cls.return_value = repo

        result = ContrattiService().list_componenti_riga(1, 5, solo_attivi=False)
        self.assertEqual(result, [{"id": 100}])
        repo.list_componenti_riga.assert_called_once_with(5, solo_attivi=False)

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_componente_contratto_attivo(self, repo_cls):
        """Contratto ATTIVO -> E_RIGA_DOC_NON_BOZZA; l'etichetta prende
        `numero` dallo scope del JOIN (senza, «Contratto #1» su un contratto
        attivo, che il numero ce l'ha sempre)."""
        from apps.vendite.services.contratti_service import ContrattiService

        repo = MagicMock()
        repo.load_componente_with_scope.return_value = {
            "componente_id": 100,
            "riga_contratto_id": 5,
            "contratto_id": 1,
            "stato_codice_interno": "ATTIVO",
            "numero": "CNT0000001",
        }
        repo_cls.return_value = repo

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().update_componente_riga(
                1, 5, 100, {"prezzo_unitario": "10"},
            )
        self.assertEqual(ctx.exception.code, "E_RIGA_DOC_NON_BOZZA")
        self.assertTrue(ctx.exception.message.startswith("Contratto CNT0000001 non e' piu' in bozza (stato ATTIVO)"))
        repo.update_componente.assert_not_called()

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_componente_chiave_fuori_whitelist_400(self, repo_cls):
        """Chiave fuori `COMPONENTE_UPDATE_ALLOWED` -> 400 che la nomina,
        repository non chiamato. ⛔ Fino al 2026-09-26 il mixin la scartava
        in silenzio e la PATCH «riusciva»."""
        from apps.vendite.services.contratti_service import ContrattiService

        repo = MagicMock()
        repo.load_componente_with_scope.return_value = {
            "componente_id": 100,
            "riga_contratto_id": 5,
            "contratto_id": 1,
            "stato_codice_interno": "DRAFT",
            "numero": None,
        }
        repo_cls.return_value = repo

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().update_componente_riga(
                1, 5, 100, {"prezzo_unitario": "10", "riga_contratto_id": 9},
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertEqual(ctx.exception.context["unknown_keys"], ["riga_contratto_id"])
        repo.update_componente.assert_not_called()

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_componente_campi_del_workflow_rifiutati(self, repo_cls):
        """⛔ L'operatore NON puo' approvarsi un prezzo L3. Fino al 2026-09-26
        la PATCH validava contro la whitelist del REPOSITORY, che contiene
        `stato_approvazione_prezzo`: `{"stato_approvazione_prezzo": "APPROVED"}`
        su un componente PENDING passava anche il guard DB. Stesso rifiuto per
        la pratica e per un'origine dichiarata dal client. ⚠️ Sono chiavi che
        il repository AMMETTE: e' il caso che distingue il codice vecchio dal
        nuovo, a differenza delle chiavi di struttura."""
        from apps.vendite.services.contratti_service import ContrattiService

        repo = MagicMock()
        repo.load_componente_with_scope.return_value = {
            "componente_id": 100,
            "riga_contratto_id": 5,
            "contratto_id": 1,
            "stato_codice_interno": "DRAFT",
            "numero": None,
        }
        repo_cls.return_value = repo

        for payload in (
            {"stato_approvazione_prezzo": "APPROVED"},
            {"pratica_approvazione_prezzo_id": 7},
            {"prezzo_unitario": "1.00", "origine_prezzo": "CONTRATTO_LISTINO"},
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(ServiceError) as ctx:
                    ContrattiService().update_componente_riga(1, 5, 100, payload)
                self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        repo.update_componente.assert_not_called()

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_componente_anti_tampering_riga(self, repo_cls):
        """riga_id URL non matcha riga reale → E_VENDITE_NOT_FOUND."""
        from apps.vendite.services.contratti_service import ContrattiService

        repo = MagicMock()
        # 1-JOIN: componente esiste ma appartiene a riga 99, non 5
        repo.load_componente_with_scope.return_value = {
            "componente_id": 100,
            "riga_contratto_id": 99,
            "contratto_id": 1,
            "stato_codice_interno": "DRAFT",
        }
        repo_cls.return_value = repo

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().update_componente_riga(
                1, 5, 100, {"prezzo_unitario": "10"},
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")

    @patch(
        "apps.vendite.services.contratti_service."
        "validate_componenti_overrides_authorization",
        return_value=None,
    )
    @patch("apps.vendite.services.contratti_service.transaction.atomic")
    @patch(
        "apps.vendite.services.contratti_service.ContrattiService."
        "_resolve_emittente_sr_id_for_contratto",
        return_value=99,
    )
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_riga_articolo_composito_auto_init(
        self, repo_cls, _mock_resolve, _mock_atomic, _mock_l1,
    ):
        """Articolo composito → auto-init componenti in transazione atomica."""
        from apps.vendite.services.contratti_service import ContrattiService

        repo = MagicMock()
        repo.get_contratto.return_value = _testata_default()
        repo.create_riga.return_value = 500
        repo.is_articolo_composito.return_value = True  # ← composito
        repo.init_componenti_riga.return_value = 3  # 3 componenti inseriti
        repo.get_riga.return_value = {"id": 500, "contratto_id": 1}
        repo_cls.return_value = repo

        result = ContrattiService().create_riga(
            1,
            {
                "articolo_id": "019d544c-7ef6-7993-9dcb-0cd1ad77d4aa",
                "tipo_eccezione": "AGGIUNTA",
                "prezzo_unitario": "0",
                "quantita": "1",
                "componenti_overrides": {"figlio-1": "5.50"},
            },
            auth_user_id=42,
        )

        # Verifica chiamate: create_riga + init_componenti_riga in atomic.
        repo.create_riga.assert_called_once()
        repo.is_articolo_composito.assert_called_once_with("019d544c-7ef6-7993-9dcb-0cd1ad77d4aa")
        repo.init_componenti_riga.assert_called_once()
        init_kwargs = repo.init_componenti_riga.call_args.kwargs
        self.assertEqual(init_kwargs["riga_id"], 500)
        self.assertEqual(init_kwargs["emittente_soggetto_ruolo_id"], 99)
        # componenti_overrides normalizzato (Decimal-safe).
        self.assertEqual(init_kwargs["componenti_overrides"], {"figlio-1": "5.50"})
        self.assertEqual(result["id"], 500)

    # Fix gap L1 componenti (refactor-prezzi 2026-06-01): create_riga ora
    # invoca il gate L1 sugli override componenti (prima assente su contratti,
    # presente su preventivi). Wiring test; la logica vive nel BB condiviso.
    @patch(
        "apps.vendite.services.contratti_service.ContrattiService."
        "_apply_pricing_gate_riga",
        return_value=(None, None),
    )
    @patch(
        "apps.vendite.services.contratti_service."
        "validate_componenti_overrides_authorization",
    )
    @patch("apps.vendite.services.contratti_service.transaction.atomic")
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_riga_invoca_validate_l1_componenti(
        self, repo_cls, _atomic, mock_validate, _gate,
    ):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = MagicMock()
        repo.get_contratto.return_value = _testata_default()
        repo.create_riga.return_value = 500
        repo.is_articolo_composito.return_value = False
        repo.get_riga.return_value = {"id": 500, "contratto_id": 1}
        repo_cls.return_value = repo

        ContrattiService().create_riga(
            1,
            {
                "articolo_id": "019d544c-7ef6-7993-9dcb-0cd1ad77d4aa",
                "tipo_eccezione": "AGGIUNTA",
                "prezzo_unitario": "5.50",
                "quantita": "1",
                "componenti_overrides": {"figlio-1": "5.50"},
            },
            auth_user_id=42,
        )

        mock_validate.assert_called_once()
        self.assertEqual(mock_validate.call_args.args[1], 42)

    @patch("apps.vendite.services.contratti_service.transaction.atomic")
    @patch(
        "apps.vendite.services.contratti_service.ContrattiService."
        "_resolve_emittente_sr_id_for_contratto",
        return_value=None,  # ← admin globale, niente emittente
    )
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_riga_articolo_composito_senza_emittente_solleva(
        self, repo_cls, _mock_resolve, _mock_atomic,
    ):
        """Articolo composito + emittente non risolvibile → errore parlante
        (refactor 2026-05-19: niente piu' skip silente; il padre orfano e'
        peggio di un errore visibile, l'atomic rollbacka il padre).
        """
        from apps.vendite.services.contratti_service import ContrattiService

        repo = MagicMock()
        repo.get_contratto.return_value = _testata_default()
        repo.create_riga.return_value = 500
        repo.is_articolo_composito.return_value = True
        repo.get_riga.return_value = {"id": 500, "contratto_id": 1}
        repo_cls.return_value = repo

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().create_riga(
                1,
                {
                    "articolo_id": "019d544c-7ef6-7993-9dcb-0cd1ad77d4aa",
                    "tipo_eccezione": "AGGIUNTA",
                    "prezzo_unitario": "0",
                    "quantita": "1",
                },
                auth_user_id=None,
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertIn("emittente", (ctx.exception.detail or "").lower())
        # Init NON chiamato: l'errore scatta prima.
        repo.init_componenti_riga.assert_not_called()

    @patch("apps.vendite.services.contratti_service.transaction.atomic")
    @patch(
        "apps.vendite.services.contratti_service.ContrattiService."
        "_resolve_emittente_sr_id_for_contratto",
        return_value=99,  # EF risolto, ma valido_dal mancante in testata
    )
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_riga_articolo_composito_senza_valido_dal_solleva(
        self, repo_cls, _mock_resolve, _mock_atomic,
    ):
        """Articolo composito + valido_dal NULL in testata → errore parlante
        (refactor 2026-05-19: pari al caso emittente, niente skip silente).
        """
        from apps.vendite.services.contratti_service import ContrattiService

        repo = MagicMock()
        # Testata senza valido_dal (DRAFT con campo non ancora valorizzato).
        testata = _testata_default()
        testata["valido_dal"] = None
        repo.get_contratto.return_value = testata
        repo.create_riga.return_value = 500
        repo.is_articolo_composito.return_value = True
        repo.get_riga.return_value = {"id": 500, "contratto_id": 1}
        repo_cls.return_value = repo

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().create_riga(
                1,
                {
                    "articolo_id": "019d544c-7ef6-7993-9dcb-0cd1ad77d4aa",
                    "tipo_eccezione": "AGGIUNTA",
                    "prezzo_unitario": "0",
                    "quantita": "1",
                },
                auth_user_id=42,
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertIn("valido_dal", (ctx.exception.detail or "").lower())
        # Init NON chiamato: la guard scatta prima.
        repo.init_componenti_riga.assert_not_called()

    @patch("apps.vendite.services.contratti_service.transaction.atomic")
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_riga_articolo_non_composito_no_init(
        self, repo_cls, _mock_atomic,
    ):
        """Articolo non composito → NO auto-init (path semplice)."""
        from apps.vendite.services.contratti_service import ContrattiService

        repo = MagicMock()
        repo.get_contratto.return_value = _testata_default()
        repo.create_riga.return_value = 500
        repo.is_articolo_composito.return_value = False  # ← NON composito
        repo.get_riga.return_value = {"id": 500, "contratto_id": 1}
        repo_cls.return_value = repo

        ContrattiService().create_riga(
            1,
            {
                "articolo_id": "019d53f6-58ca-7cb7-b77b-86d201ce9787",
                "tipo_eccezione": "OVERRIDE",
                "prezzo_unitario": "10",
                "quantita": "1",
            },
            auth_user_id=42,
        )

        repo.init_componenti_riga.assert_not_called()

    def test_normalize_componenti_overrides_infinity_rejected(self):
        """Decimal('Infinity') rifiutato dal check is_finite()."""
        from apps.vendite.services._componenti_service_helpers import (
            normalize_componenti_overrides,
        )

        with self.assertRaises(ServiceError) as ctx:
            normalize_componenti_overrides(
                {"abc-uuid": "Infinity"}, function_name="test",
                error_code="E_VENDITE_VALIDATION",
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertIn("non finito", str(ctx.exception.message))

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_delete_componente_ok(self, repo_cls):
        """Soft delete con scope OK → ritorna {deleted: True}."""
        from apps.vendite.services.contratti_service import ContrattiService

        repo = MagicMock()
        # 1-JOIN restituisce scope completo + stato DRAFT in colpo unico
        repo.load_componente_with_scope.return_value = {
            "componente_id": 100,
            "riga_contratto_id": 5,
            "contratto_id": 1,
            "stato_codice_interno": "DRAFT",
        }
        repo.delete_componente.return_value = True
        repo_cls.return_value = repo

        result = ContrattiService().delete_componente_riga(1, 5, 100)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["deleted"])
        repo.delete_componente.assert_called_once_with(100)


# ════════════════════════════════════════════════════════════════════════
# Pricing per riga contratto — gate L1+L2+L3 (BE 2.0)
# ════════════════════════════════════════════════════════════════════════
#
# Indice test:
# 1) test_suggerisci_prezzo_riga_happy_path — lookup + PricingService + normalize
# 2) test_suggerisci_prezzo_riga_articolo_mancante — E_VENDITE_VALIDATION
# 3) test_suggerisci_prezzo_riga_uom_invalido — E_VENDITE_VALIDATION
# 4) test_suggerisci_prezzo_riga_contratto_not_found — E_VENDITE_NOT_FOUND
# 5) test_suggerisci_prezzo_riga_senza_billing_account — E_VENDITE_VALIDATION
# 6) test_suggerisci_prezzo_riga_senza_valido_dal — E_VENDITE_VALIDATION
# 7) test_resolve_or_check_override_missing_context_skips — ritorna payload+None
# 8) test_resolve_or_check_override_auto_fill — payload None → resolver+meta
# 9) test_resolve_or_check_override_payload_uguale_resolver — no override
# 10) test_resolve_or_check_override_payload_diverso_no_permesso_blocca_L1
# 11) test_resolve_or_check_override_richiesta_approvazione_ritorna_violazione_l2
# 12) test_resolve_or_check_override_prezzo_non_numerico_e_un_400_col_campo — 2026-09-18: la coercizione del BB col codice del dominio E il campo `prezzo_unitario`


class ContrattiServiceFonteQuantitaTests(TestCase):
    """La quantita' per fonte la decide il DB: il service la trasporta com'e'.

    ⛔ Dal 2026-10-08 (brief-db-offerta-emissione-ed-erogazione F-1) il service
    non azzera `quantita`/`qta_operativa` sulle fonti a valle e non pretende una
    quantita' sulla FISSA: il DB svuota `quantita` con una fonte a valle
    (`script.trgfn_qta_from_operativa`), rifiuta una `qta_operativa` valorizzata
    col campo (`E_RIGA_QUANTITA_CON_FONTE_A_VALLE`) e la FISSA senza quantita'
    (`E_QTA_MISSING`). La copia Python (`_apply_fonte_quantita_logic`) azzerava
    in silenzio, e solo sul contratto. Dal 2026-10-07 non giudica nemmeno la
    coppia (tipo_erogazione, fonte) ne' sceglie una fonte di default
    (`vendite.fn_articolo_erogazioni`).

    Indice test:
    1) test_fonte_a_valle_la_quantita_arriva_al_db_com_e — niente azzeramento silenzioso
    2) test_fonte_fissa_senza_quantita_non_e_un_rifiuto_python — lo dice il DB
    3) test_nessun_giudizio_sulla_coppia_ne_default — la coppia la decide il DB
    """

    def _service(self):
        # `_build_data_riga` in update non legge il DB. Niente mock.
        from apps.vendite.services.contratti_service import ContrattiService
        return ContrattiService()

    def test_fonte_a_valle_la_quantita_arriva_al_db_com_e(self):
        svc = self._service()
        for fonte in ("MANUALE", "TIMESHEET", "LETTURE"):
            with self.subTest(fonte=fonte):
                data = svc._build_data_riga(
                    {"fonte_quantita_attesa": fonte, "qta_operativa": "3"},
                    for_create=False,
                )
                # Il rifiuto col campo `qta_operativa` e' del DB: qui nessuno
                # svuota in silenzio.
                self.assertEqual(data["qta_operativa"], Decimal("3"))
                # Ne' si inventa una `quantita`: la svuota il DB.
                self.assertNotIn("quantita", data)

    def test_fonte_fissa_senza_quantita_non_e_un_rifiuto_python(self):
        svc = self._service()
        data = svc._build_data_riga(
            {"tipo_erogazione": "canone", "fonte_quantita_attesa": "fissa"},
            for_create=False,
        )
        self.assertEqual(data["fonte_quantita_attesa"], "FISSA")
        self.assertNotIn("qta_operativa", data)

    def test_nessun_giudizio_sulla_coppia_ne_default(self):
        svc = self._service()
        # Una coppia che la vecchia matrice vietava passa: la giudica il guard
        # del perimetro a DB, sull'articolo.
        data = svc._build_data_riga(
            {"tipo_erogazione": "CONSUMO", "fonte_quantita_attesa": "TIMESHEET"},
            for_create=False,
        )
        self.assertEqual(data["fonte_quantita_attesa"], "TIMESHEET")
        # Erogazione senza fonte: nessun default inventato qui, la eredita il DB.
        data = svc._build_data_riga({"tipo_erogazione": "CANONE"}, for_create=False)
        self.assertNotIn("fonte_quantita_attesa", data)


class ContrattiServicePricingGateTests(TestCase):
    """Suite gate prezzo riga contratto (BE 2.0, 2026-05-15).

    Verifica il wiring contratti-specific: `contratti_suggerisci_prezzo_riga`
    (lookup testata + emittente + data + chiamata PricingService) e
    `resolve_or_check_override_prezzo_riga_contratto` (thin wrapper sul BB).
    La logica generica dei 3 gate vive in `_pricing_gate_helpers` e ha
    test esaustivi nella suite preventivi: qui copriamo solo il path
    contratti.
    """

    # === contratti_suggerisci_prezzo_riga ===

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_suggerisci_prezzo_riga_happy_path(self, repo_cls):
        """Contratto valido → PricingService chiamato → dict normalizzato."""
        from apps.vendite.services.contratti_service import (
            contratti_suggerisci_prezzo_riga,
        )

        repo = MagicMock()
        repo.get_contratto.return_value = _testata_default()
        repo.get_emittente_sr_id_by_fiscale_id.return_value = 999
        repo_cls.return_value = repo

        # La versione di listino la dice il DB (`fn_documento_listino_operativo`):
        # si finge la lettura, o il test interrogherebbe il DB col repo mockato.
        with patch(
            "apps.vendite.services.contratti_service."
            "resolve_emittente_sr_id_for_testata",
            return_value=999,
        ), patch(
            "apps.vendite.services.contratti_service.listino_versione_operativa",
            return_value=77,
        ) as versione, patch(
            "apps.vendite.services.pricing_service.PricingService"
        ) as pricing_cls:
            pricing = MagicMock()
            pricing.resolve_prezzo.return_value = {
                "prezzo_finale": Decimal("25.50"),
                "origine": "LISTINO",
                "listino_id": 100,
                "contratto_id": None,
                "promo_id": None,
                "tipo_variazione_applicata": None,
                "valore_variazione_applicata": None,
            }
            pricing_cls.return_value = pricing

            result = contratti_suggerisci_prezzo_riga(
                1,
                articolo_id="00000000-0000-0000-0000-000000000001",
                uom_id=5,
                auth_user_id=42,
            )

            # Decimal e date normalizzati a string per JSON safety.
            self.assertEqual(result["prezzo_finale"], "25.50")
            self.assertEqual(result["origine"], "LISTINO")
            self.assertEqual(result["listino_id"], 100)
            # PricingService chiamato con il contesto del contratto.
            pricing.resolve_prezzo.assert_called_once()
            kwargs = pricing.resolve_prezzo.call_args.kwargs
            self.assertEqual(kwargs["ba_id"], 10)
            self.assertEqual(kwargs["utility_id"], 3)
            self.assertEqual(kwargs["emittente_soggetto_ruolo_id"], 999)
            # Fast path: la versione letta col selettore del contratto arriva
            # al resolver.
            versione.assert_called_once_with("CONTRATTO", 1)
            self.assertEqual(kwargs["listino_versione_id_preferito"], 77)

    def test_suggerisci_prezzo_riga_articolo_mancante(self):
        """articolo_id None/vuoto → E_VENDITE_VALIDATION."""
        from apps.vendite.services.contratti_service import (
            contratti_suggerisci_prezzo_riga,
        )

        with self.assertRaises(ServiceError) as ctx:
            contratti_suggerisci_prezzo_riga(
                1, articolo_id="", uom_id=5, auth_user_id=42,
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    def test_suggerisci_prezzo_riga_uom_invalido(self):
        """uom_id non intero positivo → E_VENDITE_VALIDATION."""
        from apps.vendite.services.contratti_service import (
            contratti_suggerisci_prezzo_riga,
        )

        with self.assertRaises(ServiceError) as ctx:
            contratti_suggerisci_prezzo_riga(
                1, articolo_id="abc", uom_id=0, auth_user_id=42,
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_suggerisci_prezzo_riga_contratto_not_found(self, repo_cls):
        """Contratto inesistente → E_VENDITE_NOT_FOUND."""
        from apps.vendite.services.contratti_service import (
            contratti_suggerisci_prezzo_riga,
        )

        repo = MagicMock()
        repo.get_contratto.return_value = None
        repo_cls.return_value = repo

        with self.assertRaises(ServiceError) as ctx:
            contratti_suggerisci_prezzo_riga(
                999, articolo_id="abc", uom_id=5, auth_user_id=42,
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_suggerisci_prezzo_riga_senza_billing_account(self, repo_cls):
        """Contratto senza billing_account → E_VENDITE_VALIDATION."""
        from apps.vendite.services.contratti_service import (
            contratti_suggerisci_prezzo_riga,
        )

        testata = _testata_default()
        testata["billing_account_id"] = None
        repo = MagicMock()
        repo.get_contratto.return_value = testata
        repo_cls.return_value = repo

        with self.assertRaises(ServiceError) as ctx:
            contratti_suggerisci_prezzo_riga(
                1, articolo_id="abc", uom_id=5, auth_user_id=42,
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_suggerisci_prezzo_riga_senza_valido_dal(self, repo_cls):
        """Contratto senza valido_dal → E_VENDITE_VALIDATION."""
        from apps.vendite.services.contratti_service import (
            contratti_suggerisci_prezzo_riga,
        )

        testata = _testata_default()
        testata["valido_dal"] = None
        repo = MagicMock()
        repo.get_contratto.return_value = testata
        repo_cls.return_value = repo

        with patch(
            "apps.vendite.services.contratti_service."
            "resolve_emittente_sr_id_for_testata",
            return_value=999,
        ):
            with self.assertRaises(ServiceError) as ctx:
                contratti_suggerisci_prezzo_riga(
                    1, articolo_id="abc", uom_id=5, auth_user_id=42,
                )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # === resolve_or_check_override_prezzo_riga_contratto ===

    def test_resolve_or_check_override_missing_context_skips(self):
        """Testata senza BA/utility/data → skip resolver, ritorna payload+None."""
        from apps.vendite.services.contratti_service import (
            resolve_or_check_override_prezzo_riga_contratto,
        )

        testata = {"id": 1, "billing_account_id": None, "utility_id": 3,
                   "listino_id": 100, "data": "2026-05-15"}
        prezzo, meta = resolve_or_check_override_prezzo_riga_contratto(
            testata=testata,
            articolo_id="abc",
            uom_id=5,
            payload_prezzo=Decimal("10.00"),
            auth_user_id=42,
            function_name="test",
        )
        self.assertEqual(prezzo, Decimal("10.00"))
        self.assertIsNone(meta)

    def test_resolve_or_check_override_skip_per_contratto_senza_listino(self):
        """Refactor 2026-05-20: contratti con listino_id IS NULL saltano
        TUTTI i gate (L1+L2+L3). Semantica del modello "senza_listino":
        prezzo negoziato puro, nessun benchmark esterno comparabile.
        Evita falsi L2 vs cascata CATEGORIA/PROMO non pertinente.
        """
        from apps.vendite.services.contratti_service import (
            resolve_or_check_override_prezzo_riga_contratto,
        )

        testata = {"id": 1, "billing_account_id": 10, "utility_id": 3,
                   "listino_id": None, "data": "2026-05-15"}
        prezzo, meta = resolve_or_check_override_prezzo_riga_contratto(
            testata=testata,
            articolo_id="abc",
            uom_id=5,
            payload_prezzo=Decimal("99.99"),
            auth_user_id=None,  # gate L1 normalmente solleverebbe
            function_name="test",
        )
        # Skip totale: payload as-is, meta None, nessun gate invocato.
        self.assertEqual(prezzo, Decimal("99.99"))
        self.assertIsNone(meta)

    @patch(
        "apps.vendite.services.contratti_service."
        "contratti_suggerisci_prezzo_riga"
    )
    def test_resolve_or_check_override_auto_fill(self, resolver_fn):
        """payload_prezzo=None → ritorna resolver con meta origine."""
        from apps.vendite.services.contratti_service import (
            resolve_or_check_override_prezzo_riga_contratto,
        )

        resolver_fn.return_value = {
            "prezzo_finale": "30.00",
            "origine": "CONTRATTO_LISTINO",
            "listino_id": 100,
        }
        testata = {"id": 1, "billing_account_id": 10, "utility_id": 3, "listino_id": 100,
                   "data": "2026-05-15"}

        prezzo, meta = resolve_or_check_override_prezzo_riga_contratto(
            testata=testata,
            articolo_id="abc",
            uom_id=5,
            payload_prezzo=None,
            auth_user_id=42,
            function_name="test",
        )
        self.assertEqual(prezzo, Decimal("30.00"))
        self.assertIsNotNone(meta)
        self.assertEqual(meta["origine_prezzo"], "CONTRATTO_LISTINO")

    @patch(
        "apps.vendite.services.contratti_service."
        "contratti_suggerisci_prezzo_riga"
    )
    def test_resolve_or_check_override_payload_uguale_resolver(self, resolver_fn):
        """payload == resolver → no override, meta = resolver context."""
        from apps.vendite.services.contratti_service import (
            resolve_or_check_override_prezzo_riga_contratto,
        )

        resolver_fn.return_value = {
            "prezzo_finale": "30.00",
            "origine": "CONTRATTO_LISTINO",
        }
        testata = {"id": 1, "billing_account_id": 10, "utility_id": 3, "listino_id": 100,
                   "data": "2026-05-15"}

        prezzo, meta = resolve_or_check_override_prezzo_riga_contratto(
            testata=testata,
            articolo_id="abc",
            uom_id=5,
            payload_prezzo=Decimal("30.00"),
            auth_user_id=42,
            function_name="test",
        )
        # Quantizzato a 4 decimali → uguale → ritorna resolver (no MANUALE).
        # Assert positivi sulle chiavi attese: origine dal resolver (non
        # MANUALE) + prezzo_resolver_context presente. Evita assert NotIn
        # sul superset di chiavi del ramo override (fragile a future
        # estensioni del meta_patch del BB).
        self.assertEqual(prezzo, Decimal("30.00"))
        self.assertEqual(meta["origine_prezzo"], "CONTRATTO_LISTINO")
        self.assertIn("prezzo_resolver_context", meta)
        self.assertNotEqual(meta["origine_prezzo"], "MANUALE")

    @patch(
        "apps.vendite.services.contratti_service.contratti_suggerisci_prezzo_riga"
    )
    @patch(
        "apps.vendite.services._pricing_gate_helpers."
        "check_permesso_override_prezzo"
    )
    def test_resolve_or_check_override_payload_diverso_no_permesso_blocca_L1(
        self, gate_l1, resolver_fn,
    ):
        """payload != resolver, gate L1 solleva → E_PRICING_OVERRIDE_NON_AUTORIZZATO."""
        from apps.vendite.services.contratti_service import (
            resolve_or_check_override_prezzo_riga_contratto,
        )

        resolver_fn.return_value = {"prezzo_finale": "30.00", "origine": "LISTINO"}
        gate_l1.side_effect = ServiceError(
            code="E_PRICING_OVERRIDE_NON_AUTORIZZATO",
            message="L1 blocco.",
        )
        testata = {"id": 1, "billing_account_id": 10, "utility_id": 3, "listino_id": 100,
                   "data": "2026-05-15"}

        with self.assertRaises(ServiceError) as ctx:
            resolve_or_check_override_prezzo_riga_contratto(
                testata=testata,
                articolo_id="abc",
                uom_id=5,
                payload_prezzo=Decimal("25.00"),
                auth_user_id=42,
                function_name="test",
            )
        self.assertEqual(ctx.exception.code, "E_PRICING_OVERRIDE_NON_AUTORIZZATO")
        gate_l1.assert_called_once()

    @patch(
        "apps.vendite.services.contratti_service.contratti_suggerisci_prezzo_riga"
    )
    @patch(
        "apps.vendite.services._pricing_gate_helpers."
        "check_permesso_override_prezzo"
    )
    @patch(
        "apps.vendite.services._pricing_gate_helpers."
        "check_limite_variazione_prezzo"
    )
    def test_resolve_or_check_override_richiesta_approvazione_ritorna_violazione_l2(
        self, gate_l2, gate_l1, resolver_fn,
    ):
        """L3: accept_for_approval=True + violazione L2 → meta con
        richiesta_approvazione_pending=True, niente raise (orchestra il caller).
        """
        from apps.vendite.services.contratti_service import (
            resolve_or_check_override_prezzo_riga_contratto,
        )

        resolver_fn.return_value = {"prezzo_finale": "30.00", "origine": "LISTINO"}
        # L1 passa, L2 ritorna dict violazione (perche' accept_for_approval=True)
        gate_l2.return_value = {
            "tipo_violazione": "SCONTO",
            "variazione_abs_pct": "20.00",
            "limite_pct": "15",
            "kind_label": "Sconto",
        }
        testata = {"id": 1, "billing_account_id": 10, "utility_id": 3, "listino_id": 100,
                   "data": "2026-05-15"}

        prezzo, meta = resolve_or_check_override_prezzo_riga_contratto(
            testata=testata,
            articolo_id="abc",
            uom_id=5,
            payload_prezzo=Decimal("24.00"),  # sconto 20%
            auth_user_id=42,
            function_name="test",
            richiesta_approvazione=True,
        )
        self.assertEqual(prezzo, Decimal("24.00"))
        self.assertEqual(meta["origine_prezzo"], "MANUALE")
        self.assertTrue(meta["richiesta_approvazione_pending"])
        self.assertEqual(meta["violazione_l2"]["tipo_violazione"], "SCONTO")
        # L2 chiamato con accept_for_approval=True
        gate_l2.assert_called_once()
        self.assertTrue(gate_l2.call_args.kwargs["accept_for_approval"])

    @patch(
        "apps.vendite.services.contratti_service.contratti_suggerisci_prezzo_riga"
    )
    @patch(
        "apps.vendite.services._pricing_gate_helpers."
        "check_permesso_override_prezzo"
    )
    def test_resolve_or_check_override_prezzo_non_numerico_e_un_400_col_campo(
        self, gate_l1, resolver_fn,
    ):
        """⭐ Il punto che traduce (2026-09-18): il gate riceve il prezzo GREZZO
        del payload (contratti e offerte non lo coercono prima), e la
        coercizione e' del BB `PayloadValidator` — ma che esca col codice del
        DOMINIO chiamante (`error_code_validazione`) e col campo che il form
        accende resta scritto qui. `NaN` e' il valore che la copia locale
        lasciava passare: sarebbe arrivato al confronto `quantize` e al gate L2.
        ⚠️ Il rifiuto sta PRIMA di L1: un prezzo che non e' un numero non e' un
        override da autorizzare."""
        from apps.vendite.services.contratti_service import (
            resolve_or_check_override_prezzo_riga_contratto,
        )

        resolver_fn.return_value = {"prezzo_finale": "30.00", "origine": "LISTINO"}
        testata = {"id": 1, "billing_account_id": 10, "utility_id": 3, "listino_id": 100,
                   "data": "2026-05-15"}

        for raw in ("", "trenta", True, "NaN", "Infinity"):
            with self.subTest(raw=raw):
                with self.assertRaises(ServiceError) as ctx:
                    resolve_or_check_override_prezzo_riga_contratto(
                        testata=testata,
                        articolo_id="abc",
                        uom_id=5,
                        payload_prezzo=raw,
                        auth_user_id=42,
                        function_name="test",
                    )
                self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
                self.assertEqual(ctx.exception.context["field"], "prezzo_unitario")
        gate_l1.assert_not_called()


class ContrattiFatturazioneImmediataTests(TestCase):
    """Corsia di instradamento `fatturazione_immediata` sul contratto.

    Nasce da un difetto reale (2026-07-27, rilevato dal team DB): la chiave era
    stata aggiunta alle whitelist di create/update e alle `write_cols` del
    repository, ma i due mapper del contratto — unici fra i tre documenti a
    copiare campo per campo invece che con una dict-comprehension — non la
    leggevano. Sintomo peggiore: la PATCH dal drawer rispondeva **200 con
    «contratto salvato» senza persistere nulla**, perche' il payload conteneva
    comunque altri campi e quindi il guard «nessun campo aggiornabile» non
    scattava. Questi test presidiano l'anello che mancava.
    """

    # 1) CREATE: il flag arriva al dict che va alla fn madre.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_porta_il_flag_alla_fn_madre(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.create_contratto_atomico.return_value = 7
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().create_contratto({
            "billing_account_id": 1,
            "istanza_utility_id": 2,
            "utility_id": 3,
            "valido_dal": "2026-01-01",
            "fatturazione_immediata": True,
        })
        testata = repo.create_contratto_atomico.call_args.kwargs["testata"]
        self.assertIs(testata["fatturazione_immediata"], True)

    # 2) CREATE senza la chiave: NON deve finire nel dict — la fn madre filtra
    #    sulla PRESENZA, e mandarla a None darebbe 23502 su colonna NOT NULL
    #    invece del DEFAULT false (contratto §C4 del brief DB).
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_senza_chiave_non_la_inventa(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.create_contratto_atomico.return_value = 7
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().create_contratto({
            "billing_account_id": 1,
            "istanza_utility_id": 2,
            "utility_id": 3,
            "valido_dal": "2026-01-01",
        })
        testata = repo.create_contratto_atomico.call_args.kwargs["testata"]
        self.assertNotIn("fatturazione_immediata", testata)

    # 3) CREATE con la chiave a `null`: si OMETTE, non si propaga None (che sulla
    #    colonna NOT NULL diventerebbe un 23502 opaco per l'operatore).
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_chiave_nulla_viene_omessa(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.create_contratto_atomico.return_value = 7
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().create_contratto({
            "billing_account_id": 1,
            "istanza_utility_id": 2,
            "utility_id": 3,
            "valido_dal": "2026-01-01",
            "fatturazione_immediata": None,
        })
        testata = repo.create_contratto_atomico.call_args.kwargs["testata"]
        self.assertNotIn("fatturazione_immediata", testata)

    # 4) ⭐ PATCH: il flag raggiunge il repository. E' il test che sarebbe stato
    #    rosso col difetto — la whitelist bastava, il mapper no.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_patch_persiste_il_flag(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.update_contratto.return_value = True
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().update_contratto(1, {"fatturazione_immediata": True})

        data = repo.update_contratto.call_args.args[1]
        self.assertIs(data["fatturazione_immediata"], True)

    # 5) PATCH a `false`: valore legittimo, non «assente». Con un mapper che
    #    testasse la verita' del valore invece della presenza della chiave,
    #    riportare un contratto sulla corsia differita sarebbe impossibile.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_patch_false_e_un_valore_non_un_assenza(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.update_contratto.return_value = True
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().update_contratto(1, {"fatturazione_immediata": False})

        data = repo.update_contratto.call_args.args[1]
        self.assertIs(data["fatturazione_immediata"], False)

    # 6) Tipo sbagliato → 400. `bool("false")` sarebbe True: la validazione via
    #    `optional_bool` e' cio' che rende impossibile quella trappola.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_patch_valore_non_booleano_rifiutato(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()

        with self.assertRaises(ServiceError):
            ContrattiService().update_contratto(1, {"fatturazione_immediata": "false"})


class ContrattiWhitelistCreateAllineataAlDbTests(TestCase):
    """Guardrail §6a: la whitelist BE della create combacia con quella della fn madre.

    Il problema che chiude: `vendite.fn_create_contratto` costruisce l'INSERT
    da una whitelist SUA e **scarta in silenzio** le chiavi che non conosce
    (`WHERE key = ANY(v_testata_allowed)`) — nessun errore, nessun log, il campo
    sembra funzionare e non fa nulla. È così che `fatturazione_immediata` è
    rimasta inerte per un giro (brief-db-fatturazione-immediata-create-contratto).
    Senza un presidio, alla colonna successiva si ripete identico.

    Il confronto avviene con la **doc auto-generata**, che riflette l'oggetto
    vivo nel DB (regola di casa: le definizioni si leggono da `docs/it/dbzero/`,
    mai dagli YAML, che i `runOnChange` successivi rendono stale). Il test gira
    quindi senza DB, come richiesto in CI.

    ⚠️ **Limite da conoscere**: questo guardrail è vero quanto l'ultima
    rigenerazione della doc auto-gen. Non confronta il BE con il *database*, ma
    con un *documento*: se la fn madre cambia e la doc non viene rigenerata, il
    confronto avviene contro una definizione stale e il test può restare verde
    mentre il DB diverge davvero. La rigenerazione fa parte del rilascio di ogni
    changeset che tocchi la funzione — questo presidio la presuppone, non la
    sostituisce.

    Il momento in cui fallisce è l'unico utile: quando le due liste divergono.
    """

    # Sotto-entità, non colonna della testata: viaggia nel secondo parametro
    # (`p_utility`) della fn madre, che ha una whitelist sua (verificata dal
    # secondo test di questa classe).
    _NON_COLONNE = frozenset({"utility"})

    # Chiavi della riga utility che il service INIETTA (non arrivano dal
    # payload del client, che quindi non le ha nella sua whitelist): la fn
    # madre le accetta e `_build_utility_data` le valorizza in create.
    _UTILITY_INIETTATE = frozenset({"istanza_utility_id", "utility_id"})

    _DOC = (
        "docs/it/dbzero/vendite/funzioni/fn_create_contratto.md"
    )

    # Scopo: estrae una whitelist (`v_testata_allowed` / `v_util_allowed`)
    #        dalla definizione VIVA nella doc auto-gen.
    def _whitelist_db(self, nome: str) -> set[str]:
        import re
        from pathlib import Path

        # backend/apps/vendite/tests/services/<file> -> radice repo
        radice = Path(__file__).resolve().parents[5]
        doc = radice / self._DOC
        self.assertTrue(
            doc.is_file(),
            f"Doc auto-gen non trovata: {doc}. Se la funzione è stata rinominata "
            f"o la doc spostata, aggiornare questo guardrail — non rimuoverlo.",
        )
        testo = doc.read_text(encoding="utf-8")
        match = re.search(
            rf"{nome}\s+text\[\]\s*:=\s*ARRAY\[(.*?)\]", testo, re.S,
        )
        self.assertIsNotNone(
            match,
            f"{nome} non trovata nella doc auto-gen di fn_create_contratto: "
            f"la doc è stale o la funzione è cambiata forma.",
        )
        assert match is not None
        # `[a-z0-9_]` e non `[a-z_]`: esistono colonne con cifre nel nome
        # (`param_1_num`, `param_2_txt`) e una classe senza `0-9` le avrebbe
        # semplicemente NON viste, facendole apparire come divergenze.
        # Non serve irrobustirla oltre: il lato BE NON e' parsato (viene dal
        # frozenset Python), quindi una regex che perde chiavi puo' solo
        # produrre FALSI ROSSI sul caso grave (`be - db`), mai falsi verdi.
        # E' il modo sicuro di sbagliare.
        return set(re.findall(r"'([a-z0-9_]+)'", match.group(1)))

    def test_whitelist_be_e_db_combaciano(self) -> None:
        from apps.vendite.services.contratti_service import CREATE_KEYS_TESTATA

        be = set(CREATE_KEYS_TESTATA) - self._NON_COLONNE
        db = self._whitelist_db("v_testata_allowed")

        # Chiavi che il BE accetta e la fn madre NON conosce: sono quelle che
        # verrebbero SCARTATE IN SILENZIO. È il caso grave.
        scartate = sorted(be - db)
        self.assertEqual(
            scartate, [],
            f"Il BE accetta chiavi che vendite.fn_create_contratto scarterebbe "
            f"in silenzio: {scartate}. Aggiungerle a v_testata_allowed (brief DB) "
            f"oppure toglierle dalla whitelist BE.",
        )

        # Chiavi che la fn madre accetta e il BE non espone: non è un bug, ma è
        # capacità DB non raggiungibile — va vista, non subita.
        non_esposte = sorted(db - be)
        self.assertEqual(
            non_esposte, [],
            f"vendite.fn_create_contratto accetta chiavi che il BE non espone: "
            f"{non_esposte}. Se è voluto, escluderle esplicitamente qui con il "
            f"motivo; altrimenti aggiungerle a CREATE_KEYS_TESTATA.",
        )

    # La sotto-entità utility ha la STESSA struttura fail-open della testata
    # (`WHERE key = ANY(v_util_allowed)`), quindi la stessa trappola: una chiave
    # aggiunta al BE e non alla fn madre verrebbe scartata senza un fiato.
    # Presidiata qui, non perché sia già successo ma perché è lo stesso identico
    # meccanismo che è già costato un giro sulla testata.
    def test_whitelist_utility_be_e_db_combaciano(self) -> None:
        from apps.vendite.services.contratti_service import UTILITY_CREATE_KEYS

        be = set(UTILITY_CREATE_KEYS) | self._UTILITY_INIETTATE
        db = self._whitelist_db("v_util_allowed")

        scartate = sorted(be - db)
        self.assertEqual(
            scartate, [],
            f"Il BE compone la riga utility con chiavi che "
            f"vendite.fn_create_contratto scarterebbe in silenzio: {scartate}.",
        )
        non_esposte = sorted(db - be)
        self.assertEqual(
            non_esposte, [],
            f"vendite.fn_create_contratto accetta chiavi utility che il BE non "
            f"compone: {non_esposte}. Se è voluto, escluderle qui col motivo.",
        )


class ContrattiCatenaUpdateTests(TestCase):
    """Guardrail: i TRE anelli della PATCH di testata restano allineati.

    Il difetto del 2026-07-27 non è nato sulla create ma qui. La catena è:

        UPDATE_KEYS_TESTATA  →  _build_update_data_testata  →  TESTATA_UPDATE_COLUMNS
        (cosa si accetta)        (cosa si mappa)                (cosa si scrive)

    Basta che una colonna manchi in **uno solo** dei tre e l'UPDATE non la
    scrive — senza errore. Nel caso reale (`fatturazione_immediata`) mancava
    l'anello di mezzo: la PATCH dal drawer rispondeva 200 con «contratto
    salvato» e non persisteva nulla, perché il payload conteneva comunque altri
    campi e il guard «nessun campo aggiornabile» non scattava.

    È stato corretto a mano, e a mano si sarebbe ripetuto alla colonna dopo:
    il mapper è l'unico dei tre anelli che nessun test confrontava. Segnalato
    dal team DB come «il solo guardrail da aggiungere, se se ne aggiunge uno».

    Il test attraversa la catena **una chiave alla volta**, dal service pubblico
    fino alla chiamata al repository: è l'unico modo per accorgersi di un anello
    che non passa la palla.
    """

    # Valore valido per ogni chiave della whitelist. Il dizionario È parte del
    # guardrail: aggiungere una chiave a `UPDATE_KEYS_TESTATA` senza aggiungere
    # qui un campione fa fallire il primo test — che è il momento in cui serve
    # fermarsi a pensare se il mapper la gestisce.
    _CAMPIONI: dict[str, object] = {
        # Il cliente in coppia: il BB `risolvi_cliente_coppia` e' finto nel
        # test 2 e restituisce questi due.
        "billing_account_id": 7,
        "istanza_utility_id": 8,
        "ambito": "COMMODITY",
        "valido_dal": "2026-03-01",
        "valido_al": "2026-12-31",
        "parent_contratto_id": 5,
        "data": "2026-03-01",
        "listino_id": 200,
        "tipo_variazione_globale": "PERCENTUALE",
        "valore_variazione_globale": "-5",
        "categoria_cliente_id_snapshot": 3,
        "fatturazione_immediata": True,
        # Riferimenti dell'atto (I8/D9, 2026-08-29). Lunghezze entro i limiti
        # delle colonne: VARCHAR(15) per CIG e CUP, VARCHAR(100) per la commessa.
        "codice_cig": "1234567890ABCDE",
        "codice_cup": "H51B09000000001",
        "codice_commessa": "CONV-2026/17",
        "meta": {"nota": "guardrail"},
    }

    # Coppia che il dominio valida insieme (entrambe NULL o entrambe valorizzate):
    # testarne una da sola darebbe un errore di coerenza, non un esito sul mapper.
    _PARTNER: dict[str, str] = {
        "tipo_variazione_globale": "valore_variazione_globale",
        "valore_variazione_globale": "tipo_variazione_globale",
    }

    # 0) ⭐ L'invariante su cui si regge il FRONTEND, e che nessuno vedeva.
    #    `ContrattoDrawer.buildPayload()` costruisce il payload della PATCH, e
    #    `handleSave` lo SPREADA dentro il payload di CREATE. La create BE
    #    (`validate_allowed_keys` su `CREATE_KEYS_TESTATA`) RIFIUTA l'intero
    #    payload se contiene una chiave che non ammette — non la ignora.
    #    Quindi ogni chiave accettata in UPDATE dev'essere accettata anche in
    #    CREATE, oppure il drawer deve cancellarla esplicitamente prima di
    #    spedire: altrimenti la creazione contratto smette di funzionare.
    # ✅ 2026-08-31 — L'ECCEZIONE E' RIENTRATA, e questo test l'ha segnalato.
    #    Era dichiarata UNA SOLA: i tre riferimenti dell'atto (I8/D9), che la
    #    whitelist della fn madre `vendite.fn_create_contratto` non conosceva.
    #    Il changeSet `20260831-24` li ha ammessi, quindi sono entrati in
    #    `CREATE_KEYS_TESTATA` (slice S3-b) e il `v-if` nel drawer e' caduto.
    #    ⭐ Il segnalibro ha fatto il suo mestiere: e' diventato rosso il giorno
    #    in cui l'eccezione ha smesso di servire, invece di restare verde su una
    #    deroga sopravvissuta alla sua ragione.
    # ⛔ Ora l'invariante e' SECCA e senza deroghe: nessuna chiave puo' stare in
    #    UPDATE e non in CREATE. Chi ne aggiunge una deve o metterla in
    #    entrambe, o farla escludere dal drawer — e cambiare questo test
    #    dichiarando l'eccezione, che e' il gesto che la rende visibile.
    def test_update_keys_accettate_anche_in_create(self) -> None:
        from apps.vendite.services.contratti_service import (
            CREATE_KEYS_TESTATA,
            UPDATE_KEYS_CONTRATTO,
        )

        solo_update = sorted(set(UPDATE_KEYS_CONTRATTO) - set(CREATE_KEYS_TESTATA))
        self.assertEqual(
            solo_update, [],
            "Chiavi accettate in UPDATE ma non in CREATE. Il drawer spreda il "
            "payload della PATCH dentro quello della create, e la create "
            "rifiuta le chiavi ignote: o si aggiungono a CREATE_KEYS_TESTATA, "
            "o `ContrattoDrawer.buildPayload` deve escluderle esplicitamente.",
        )

    # 1) Ogni chiave accettata ha un campione: è il gancio che costringe a
    #    passare di qui quando si allarga la whitelist.
    def test_ogni_chiave_accettata_ha_un_campione(self) -> None:
        from apps.vendite.services.contratti_service import UPDATE_KEYS_TESTATA

        senza_campione = sorted(set(UPDATE_KEYS_TESTATA) - set(self._CAMPIONI))
        self.assertEqual(
            senza_campione, [],
            f"Chiavi in UPDATE_KEYS_TESTATA senza campione in questo test: "
            f"{senza_campione}. Aggiungerne uno valido e verificare che "
            f"_build_update_data_testata le legga davvero.",
        )

    # 2) ⭐ Anello 1 → 2: ogni chiave accettata ATTRAVERSA il mapper e arriva al
    #    repository. È il test che sarebbe stato rosso sul difetto reale.
    @patch(
        "apps.vendite.services.contratti_service.risolvi_cliente_coppia",
        return_value=(7, 8),
    )
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_ogni_chiave_attraversa_il_mapper(self, repo_cls, _cliente) -> None:
        from apps.vendite.services.contratti_service import (
            UPDATE_KEYS_TESTATA,
            ContrattiService,
        )

        repo = repo_cls.return_value
        repo.update_contratto.return_value = True
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        for chiave in sorted(UPDATE_KEYS_TESTATA):
            with self.subTest(chiave=chiave):
                repo.get_contratto.return_value = _testata_default()
                payload: dict[str, object] = {chiave: self._CAMPIONI[chiave]}
                partner = self._PARTNER.get(chiave)
                if partner is not None:
                    payload[partner] = self._CAMPIONI[partner]

                repo.update_contratto.reset_mock()
                ContrattiService().update_contratto(1, payload)

                self.assertTrue(
                    repo.update_contratto.called,
                    f"'{chiave}': la PATCH non ha raggiunto il repository.",
                )
                data = repo.update_contratto.call_args.args[1]
                self.assertIn(
                    chiave, data,
                    f"'{chiave}' è accettata da UPDATE_KEYS_TESTATA ma "
                    f"_build_update_data_testata NON la legge: l'UPDATE la "
                    f"ignorerebbe in silenzio (difetto 2026-07-27).",
                )

    # 3) Anello 1 ↔ 3: ciò che si accetta è esattamente ciò che si sa scrivere.
    #    Una colonna nella whitelist ma non in TESTATA_UPDATE_COLUMNS verrebbe
    #    mappata e poi rifiutata dal repository (`RuntimeError` del BB, 500 dal
    #    2026-09-26; fino ad allora era scartata in silenzio): l'errore c'e', ma
    #    lo deve trovare questo test e non l'operatore.
    def test_whitelist_e_colonne_scrivibili_combaciano(self) -> None:
        from apps.vendite.db.contratti_repository import ContrattiRepository
        from apps.vendite.services.contratti_service import UPDATE_KEYS_TESTATA

        accettate = set(UPDATE_KEYS_TESTATA)
        scrivibili = set(ContrattiRepository.TESTATA_UPDATE_COLUMNS)

        self.assertEqual(
            sorted(accettate - scrivibili), [],
            "Chiavi accettate dal service che il repository non scrive: "
            "verrebbero perse dopo il mapper.",
        )
        self.assertEqual(
            sorted(scrivibili - accettate), [],
            "Colonne scrivibili dal repository che il service non accetta: "
            "capacità irraggiungibile (o whitelist da allargare).",
        )


class ContrattiRigaAttivoMetaNotNullTests(TestCase):
    """`contratti_righe.attivo` e `meta` sono NOT NULL dal 2026-10-05
    (brief-db-righe-esclusione-solo-non-si-vende §10.7 R-BE-12, B4): un `null`
    ESPLICITO del client non deve arrivare alla INSERT/UPDATE, dove sarebbe un
    23502. Il mapper della riga lo tratta come «non toccare» (`attivo`) e come
    reset all'oggetto vuoto (`meta`, BB `optional_meta`): la stessa regola
    della gemella sull'offerta.

    Indice test:
    1) test_attivo_null_non_si_inoltra — create e update
    2) test_meta_null_diventa_oggetto_vuoto — create e update
    """

    def _data(self, payload: dict, *, for_create: bool) -> dict:
        from apps.vendite.services.contratti_service import ContrattiService
        base = {"articolo_id": "11111111-1111-1111-1111-111111111111", "tipo_eccezione": "ESCLUSIONE"}
        return ContrattiService()._build_data_riga(
            {**(base if for_create else {}), **payload}, for_create=for_create,
        )

    def test_attivo_null_non_si_inoltra(self):
        for for_create in (True, False):
            with self.subTest(create=for_create):
                self.assertNotIn("attivo", self._data({"attivo": None}, for_create=for_create))

    def test_meta_null_diventa_oggetto_vuoto(self):
        for for_create in (True, False):
            with self.subTest(create=for_create):
                self.assertEqual(self._data({"meta": None}, for_create=for_create)["meta"], {})
