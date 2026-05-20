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
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.db import DatabaseError, IntegrityError

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
        "stato_codice": "DRAFT",
        "valido_dal": date.today() - timedelta(days=1),
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
    #        ritornato da script.fn_available_actions_contratto (Fase 1.B2).
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_get_contratto_include_capabilities(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []
        repo.list_righe_preview.return_value = []
        repo.get_capabilities.return_value = {
            "stato_codice": "ATTIVO",
            "available_actions": [{
                "key": "cessa", "target_state": "CESSATO",
                "label_key": "contratti.azione_cessa",
                "severity": "danger", "icon": "pi pi-stop",
                "requires_confirm": True, "requires_date": True,
                "default_date": "2026-04-30", "min_date": "2026-04-25",
            }],
            "can_change_state": True,
            "can_edit_testata": True,
            "can_edit_righe": False,
            "non_editable_fields": ["billing_account_id", "utility_id"],
        }

        result = ContrattiService().get_contratto(1)

        self.assertEqual(result["can_change_state"], True)
        self.assertEqual(result["can_edit_righe"], False)
        self.assertEqual(len(result["available_actions"]), 1)
        action = result["available_actions"][0]
        self.assertEqual(action["key"], "cessa")
        self.assertEqual(action["default_date"], "2026-04-30")
        self.assertIn("billing_account_id", result["non_editable_fields"])
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

    # --- preview righe applicate -------------------------------------

    # Scopo: contratto inesistente -> E_VENDITE_NOT_FOUND.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_list_righe_preview_not_found(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo_cls.return_value.get_contratto.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().list_righe_preview(7)
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")

    # Scopo: forma "con_listino" senza eccezioni (refactor 2026-05-15:
    # ex-modalita' A) -> righe tutte da listino + forma derivata correttamente.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_list_righe_preview_con_listino_solo_da_listino(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()
        repo.list_righe_preview.return_value = [
            {
                "articolo_id": "uuid-1",
                "uom_id": 1,
                "prezzo_listino": Decimal("100.00"),
                "prezzo_finale": Decimal("90.00"),
                "origine": "DA_LISTINO",
                "override_riga_id": None,
            },
        ]

        result = ContrattiService().list_righe_preview(1)

        self.assertEqual(result["forma"], "con_listino")
        self.assertEqual(result["listino_id"], 100)
        self.assertEqual(len(result["righe"]), 1)
        self.assertEqual(result["righe"][0]["origine"], "DA_LISTINO")

    # Scopo: forma "con_listino" con eccezione OVERRIDE (refactor 2026-05-15:
    # ex-modalita' B). La forma resta "con_listino" — niente piu' A vs B come
    # distinzione di modello.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_list_righe_preview_con_listino_con_override(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()
        repo.list_righe_preview.return_value = [
            {
                "articolo_id": "uuid-1",
                "uom_id": 1,
                "prezzo_listino": Decimal("100.00"),
                "prezzo_finale": Decimal("90.00"),
                "origine": "DA_LISTINO",
                "override_riga_id": None,
            },
            {
                "articolo_id": "uuid-2",
                "uom_id": 1,
                "prezzo_listino": Decimal("200.00"),
                "prezzo_finale": Decimal("150.00"),
                "origine": "OVERRIDE",
                "override_riga_id": 42,
            },
        ]

        result = ContrattiService().list_righe_preview(1)

        self.assertEqual(result["forma"], "con_listino")
        self.assertEqual(len(result["righe"]), 2)

    # Scopo: forma "senza_listino" (refactor 2026-05-15: ex-modalita' C
    # interamente negoziata) -> listino_id NULL, nessuna preview di righe
    # listino, nessuna chiamata al repo.list_righe_preview.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_list_righe_preview_senza_listino(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        testata = _testata_default()
        testata["listino_id"] = None
        testata["tipo_variazione_globale"] = None
        testata["valore_variazione_globale"] = None
        repo.get_contratto.return_value = testata

        result = ContrattiService().list_righe_preview(1)

        self.assertEqual(result["forma"], "senza_listino")
        self.assertEqual(result["listino_id"], None)
        self.assertEqual(result["righe"], [])
        # Per design forma "senza_listino" non e' "senza versione": la lista
        # vuota e' attesa, non sintomo di errore.
        self.assertFalse(result["listino_senza_versione_oggi"])
        repo.list_righe_preview.assert_not_called()

    # Scopo: contratto modalita' A con listino associato ma senza versione
    #        operativa alla data odierna (validita @> CURRENT_DATE non matcha)
    #        -> lista preview vuota + flag listino_senza_versione_oggi=True
    #        per consentire al FE di mostrare hint esplicito.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_list_righe_preview_listino_senza_versione_oggi(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()
        repo.list_righe_preview.return_value = []  # nessuna versione operativa

        result = ContrattiService().list_righe_preview(1)

        self.assertEqual(result["listino_id"], 100)
        self.assertEqual(result["righe"], [])
        self.assertTrue(result["listino_senza_versione_oggi"])

    # Scopo: contratto "con_listino" con sole eccezioni per articoli NON
    # presenti nel listino (caso "extra-listino", future AGGIUNTE). La query
    # SQL ritorna l'eccezione con origine='OVERRIDE'. La forma resta
    # "con_listino" (refactor 2026-05-15: niente piu' A vs B). Flag
    # listino_senza_versione_oggi=True perche' nessuna riga DA_LISTINO.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_list_righe_preview_solo_eccezioni_extra_listino(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()
        repo.list_righe_preview.return_value = [
            {
                "articolo_id": "uuid-extra",
                "uom_id": 1,
                "prezzo_listino": None,
                "prezzo_finale": Decimal("75.00"),
                "origine": "OVERRIDE",
                "override_riga_id": 99,
            },
        ]

        result = ContrattiService().list_righe_preview(1)

        self.assertEqual(result["forma"], "con_listino")
        self.assertEqual(len(result["righe"]), 1)
        self.assertEqual(result["righe"][0]["origine"], "OVERRIDE")
        self.assertTrue(result["listino_senza_versione_oggi"])

    # --- create contratto ---------------------------------------------

    @patch("apps.vendite.services.contratti_service.ListiniRepository")
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_contratto_modalita_A_ok(self, repo_cls, listini_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.generate_numero.return_value = "CNT0000001"
        repo.get_stato_id_by_codice.return_value = 1
        repo.create_contratto.return_value = 1
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []
        # Decisione 2026-05-18: listino_id richiede versione ATTIVA.
        listini_cls.return_value.has_versione_attiva.return_value = True

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
        args = repo.create_contratto.call_args.args[0]
        self.assertEqual(args["numero"], "CNT0000001")
        self.assertEqual(args["stato_doc_contratto_id"], 1)
        self.assertEqual(args["tipo_variazione_globale"], "PERCENTUALE")

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_contratto_modalita_C_ok(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.generate_numero.return_value = "CNT0000002"
        repo.get_stato_id_by_codice.return_value = 1
        repo.create_contratto.return_value = 2
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().create_contratto({
            "billing_account_id": 10,
            "istanza_utility_id": 20,
            "utility_id": 3,
            "valido_dal": "2026-01-01",
        })

        args = repo.create_contratto.call_args.args[0]
        self.assertNotIn("listino_id", args)
        self.assertNotIn("tipo_variazione_globale", args)

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
        repo.generate_numero.return_value = "CNT0000003"
        repo.get_stato_id_by_codice.return_value = 1
        repo.create_contratto.return_value = 3
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

        args = repo.create_contratto.call_args.args[0]
        self.assertEqual(args["tipo_variazione_globale"], "PERCENTUALE")
        self.assertNotIn("listino_id", args)

    @patch("apps.vendite.services.contratti_service.ListiniRepository")
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_contratto_variazione_coppia_incompleta_fallisce(
        self, repo_cls, listini_cls,
    ):
        # Resta valido il vincolo strutturale: tipo+valore devono essere
        # coppia coerente (entrambi NULL o entrambi NOT NULL).
        # Listini mockata → guard listino-versione-attiva passa.
        from apps.vendite.services.contratti_service import ContrattiService

        listini_cls.return_value.has_versione_attiva.return_value = True

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
        repo.generate_numero.return_value = "CNT0000003"
        repo.get_stato_id_by_codice.return_value = 1
        # Scopo: PG18 temporal UNIQUE (WITHOUT OVERLAPS) sulla colonna `validita`
        #        STORED generated → messaggio standard "unique constraint",
        #        nome `uq_contratti_no_overlap` (migration 20260514-10).
        repo.create_contratto.side_effect = IntegrityError(
            "duplicate key value violates unique constraint \"uq_contratti_no_overlap\""
        )

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().create_contratto({
                "billing_account_id": 10,
                "istanza_utility_id": 20,
                "utility_id": 3,
                "valido_dal": "2026-01-01",
            })
        self.assertEqual(ctx.exception.code, "E_VENDITE_CONTRATTO_OVERLAP")

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_contratto_genera_numero_e_stato_draft(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.generate_numero.return_value = "CNT0000077"
        repo.get_stato_id_by_codice.return_value = 42
        repo.create_contratto.return_value = 7
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().create_contratto({
            "billing_account_id": 10,
            "istanza_utility_id": 20,
            "utility_id": 3,
            "valido_dal": "2026-01-01",
        })

        repo.generate_numero.assert_called_once_with()
        repo.get_stato_id_by_codice.assert_called_once_with("DRAFT")
        args = repo.create_contratto.call_args.args[0]
        self.assertEqual(args["numero"], "CNT0000077")
        self.assertEqual(args["stato_doc_contratto_id"], 42)

    # --- update contratto ---------------------------------------------

    def test_update_contratto_rifiuta_identificativi_immutabili(self):
        from apps.vendite.services.contratti_service import ContrattiService

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().update_contratto(1, {"numero": "CNT9999999"})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: contratto ATTIVO -> categoria_cliente_id_snapshot non e' nella
    #        whitelist di campi ammessi per ATTIVO -> errore parlante
    #        E_CONTRATTO_NON_MODIFICABILE.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_contratto_attivo_rifiuta_categoria_snapshot(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = {
            **_testata_default(),
            "stato_codice": "ATTIVO",
            "categoria_cliente_id_snapshot": 1,
        }

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().update_contratto(1, {"categoria_cliente_id_snapshot": 5})
        self.assertEqual(ctx.exception.code, "E_CONTRATTO_NON_MODIFICABILE")

    # Scopo: contratto ATTIVO -> ammessa solo modifica valido_al/meta
    #        (programma cessazione + note). Il PATCH valido_al passa.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_contratto_attivo_ammette_solo_valido_al(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = {
            **_testata_default(),
            "stato_codice": "ATTIVO",
        }
        repo.update_contratto.return_value = True
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().update_contratto(1, {"valido_al": "2026-12-31"})

        args = repo.update_contratto.call_args.args
        self.assertEqual(args[0], 1)
        self.assertEqual(args[1]["valido_al"], date(2026, 12, 31))

    # Scopo: contratto CESSATO -> tutti i campi rifiutati (whitelist vuota).
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_contratto_cessato_rifiuta_qualsiasi_campo(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = {
            **_testata_default(),
            "stato_codice": "CESSATO",
        }

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().update_contratto(1, {"valido_al": "2026-12-31"})
        self.assertEqual(ctx.exception.code, "E_CONTRATTO_NON_MODIFICABILE")

    # Scopo: contratto ATTIVO -> create_riga rifiutato.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_riga_rifiutata_su_contratto_attivo(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = {
            **_testata_default(),
            "stato_codice": "ATTIVO",
        }

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().create_riga(1, {
                "articolo_id": "uuid",
                "uom_operativa_id": 1,
                "prezzo_unitario": "10",
                "qta_operativa": "1",
            })
        self.assertEqual(ctx.exception.code, "E_CONTRATTO_NON_MODIFICABILE")

    # Scopo: contratto ATTIVO -> update_riga rifiutato (risale dal contratto
    #        della riga via get_riga).
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_riga_rifiutata_su_contratto_attivo(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_riga.return_value = {"id": 99, "contratto_id": 1}
        repo.get_contratto.return_value = {
            **_testata_default(),
            "stato_codice": "ATTIVO",
        }

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().update_riga(99, {"prezzo_unitario": "20"})
        self.assertEqual(ctx.exception.code, "E_CONTRATTO_NON_MODIFICABILE")

    # Scopo: contratto ATTIVO -> delete_riga rifiutato.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_delete_riga_rifiutata_su_contratto_attivo(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_riga.return_value = {"id": 99, "contratto_id": 1}
        repo.get_contratto.return_value = {
            **_testata_default(),
            "stato_codice": "ATTIVO",
        }

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().delete_riga(99)
        self.assertEqual(ctx.exception.code, "E_CONTRATTO_NON_MODIFICABILE")

    # Scopo: contratto ATTIVO -> update_utility rifiutato.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_utility_rifiutata_su_contratto_attivo(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = {
            **_testata_default(),
            "stato_codice": "ATTIVO",
        }

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().update_utility(1, {"tipo_utenza_id": 5})
        self.assertEqual(ctx.exception.code, "E_CONTRATTO_NON_MODIFICABILE")

    # Scopo: cessazione immediata (valido_al passata) -> applica entrambi
    #        in transazione: PATCH valido_al + UPDATE stato CESSATO.
    @patch("apps.vendite.services.contratti_service.transaction.atomic")
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_cambia_stato_cessazione_immediata_data_passata(self, repo_cls, _atomic):
        from apps.vendite.services.contratti_service import ContrattiService

        ieri = date.today() - timedelta(days=1)
        repo = repo_cls.return_value
        repo.get_stato_id_by_codice.return_value = 5  # CESSATO id
        repo.update_contratto.return_value = True
        repo.update_stato.return_value = True
        repo.get_contratto.return_value = {
            **_testata_default(),
            "stato_codice": "CESSATO",
        }
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        result = ContrattiService().cambia_stato(
            1, codice_interno="CESSATO", valido_al=ieri,
        )

        # update_contratto chiamato per valido_al, poi update_stato.
        repo.update_contratto.assert_called_once_with(1, {"valido_al": ieri})
        repo.update_stato.assert_called_once_with(1, 5)
        self.assertEqual(result["stato_codice"], "CESSATO")

    # Scopo: cessazione PROGRAMMATA (valido_al futura) -> applica solo
    #        PATCH valido_al, lo stato resta invariato. Il job notturno
    #        DB allineera' a CESSATO quando la data scade.
    @patch("apps.vendite.services.contratti_service.transaction.atomic")
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_cambia_stato_cessazione_programmata_data_futura(self, repo_cls, _atomic):
        from apps.vendite.services.contratti_service import ContrattiService

        domani = date.today() + timedelta(days=1)
        repo = repo_cls.return_value
        repo.get_stato_id_by_codice.return_value = 5
        repo.update_contratto.return_value = True
        repo.get_contratto.return_value = {
            **_testata_default(),
            "stato_codice": "ATTIVO",  # stato resta ATTIVO post-call
        }
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        result = ContrattiService().cambia_stato(
            1, codice_interno="CESSATO", valido_al=domani,
        )

        # Solo PATCH valido_al; UPDATE stato NON chiamato (programmazione).
        repo.update_contratto.assert_called_once_with(1, {"valido_al": domani})
        repo.update_stato.assert_not_called()
        self.assertEqual(result["stato_codice"], "ATTIVO")

    # Scopo: cessazione data oggi -> stato resta invariato (programmazione
    #        per oggi: il job notturno scattera' alle 00:05 della notte
    #        prossima e applichera' lo stato CESSATO).
    @patch("apps.vendite.services.contratti_service.transaction.atomic")
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_cambia_stato_cessazione_data_oggi_e_programmata(self, repo_cls, _atomic):
        from apps.vendite.services.contratti_service import ContrattiService

        oggi = date.today()
        repo = repo_cls.return_value
        repo.get_stato_id_by_codice.return_value = 5
        repo.update_contratto.return_value = True
        repo.get_contratto.return_value = {
            **_testata_default(),
            "stato_codice": "ATTIVO",
        }
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().cambia_stato(
            1, codice_interno="CESSATO", valido_al=oggi,
        )

        repo.update_contratto.assert_called_once_with(1, {"valido_al": oggi})
        repo.update_stato.assert_not_called()

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
    @patch("apps.vendite.services.contratti_service.transaction.atomic")
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_cambia_stato_senza_valido_al_no_patch(self, repo_cls, _atomic):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_stato_id_by_codice.return_value = 2  # ATTIVO id
        repo.update_stato.return_value = True
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().cambia_stato(1, codice_interno="ATTIVO")

        repo.update_contratto.assert_not_called()
        repo.update_stato.assert_called_once_with(1, 2)

    # Scopo: cambia_stato con valido_al < valido_dal -> errore parlante
    #        (anti CHK constraint DB generico).
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_cambia_stato_valido_al_anteriore_a_valido_dal_rifiutato(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_stato_id_by_codice.return_value = 5  # CESSATO id
        repo.get_contratto.return_value = {
            **_testata_default(),
            "valido_dal": date(2026, 6, 1),
        }

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().cambia_stato(
                1, codice_interno="CESSATO", valido_al=date(2026, 1, 1),
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertIn("valido_dal", ctx.exception.detail)
        repo.update_contratto.assert_not_called()
        repo.update_stato.assert_not_called()

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_contratto_campi_vuoto_fallisce(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().update_contratto(1, {})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch("apps.vendite.services.contratti_service.ListiniRepository")
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_contratto_ok_variazione(self, repo_cls, listini_cls):
        """Update happy path: variazione globale PERCENTUALE accettata sulla testata.

        Refactor 2026-05-18: VALORE_FISSO non e' piu' ammesso come variazione
        globale (decisione di dominio: resta solo per OVERRIDE su singola
        riga). Vedi `test_update_contratto_variazione_valore_fisso_rifiutata`.
        Decisione 2026-05-18 §4.4: listino_id richiede versione ATTIVA.
        """
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.update_contratto.return_value = True
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []
        # Lock listino_id richiede 0 righe attive (refactor 2026-05-20).
        repo.count_righe_attive.return_value = 0
        listini_cls.return_value.has_versione_attiva.return_value = True

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

    @patch("apps.vendite.services.contratti_service.ListiniRepository")
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_contratto_listino_senza_versione_attiva_rifiutato(
        self, repo_cls, listini_cls,
    ):
        """Decisione 2026-05-18 §4.4: listino senza versione ATTIVA non selezionabile.

        Caso classico: l'operatore prova ad associare un contratto a un
        listino BOZZA (nessuna versione mai attivata). Il guard pre-save
        solleva `E_CONTRATTO_LISTINO_SENZA_VERSIONE_ATTIVA` (422) con
        messaggio parlante. Il listino non puo' essere riferito perche'
        non ci sarebbero righe da applicare.
        """
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        listini_cls.return_value.has_versione_attiva.return_value = False

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().create_contratto({
                "billing_account_id": 10,
                "istanza_utility_id": 20,
                "utility_id": 3,
                "valido_dal": "2026-01-01",
                "listino_id": 100,
                "tipo_variazione_globale": "PERCENTUALE",
                "valore_variazione_globale": "-10",
            })
        self.assertEqual(
            ctx.exception.code, "E_CONTRATTO_LISTINO_SENZA_VERSIONE_ATTIVA",
        )
        # Il create non deve essere stato chiamato (early fail nel build).
        repo.create_contratto.assert_not_called()
        listini_cls.return_value.has_versione_attiva.assert_called_once_with(100)

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

    # Scopo: refactor 2026-05-15. update_riga non puo' settare prezzo NOT NULL
    # su riga ESCLUSIONE esistente.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_riga_esclusione_prezzo_non_null_fallisce(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_riga.return_value = {
            "id": 7, "contratto_id": 1, "tipo_eccezione": "ESCLUSIONE",
            "prezzo_unitario": None,
        }
        repo.get_contratto.return_value = _testata_default()  # DRAFT

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().update_riga(7, {"prezzo_unitario": "10"})

        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertIn("ESCLUSIONE", ctx.exception.detail or "")
        repo.update_riga.assert_not_called()

    # Scopo: BE 2.6. get_contesto_pricing delega al repository e ritorna
    # l'envelope per il banner FE.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_get_contesto_pricing(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.resolve_contesto_pricing_contratto.return_value = {
            "contratto_id": 1,
            "forma": "con_listino",
            "stato_codice": "ATTIVO",
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

    # Scopo: refactor §3-bis-F. Rimuovere il listino con eccezioni
    # OVERRIDE/ESCLUSIONE attive deve sollevare 422 con codice dedicato e
    # NON tentare l'UPDATE del contratto.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_contratto_rimuove_listino_con_eccezioni_bloccato(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()  # listino_id=100
        repo.count_eccezioni_bloccanti.return_value = {
            "OVERRIDE": 3, "ESCLUSIONE": 2,
        }

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().update_contratto(1, {"listino_id": None})

        self.assertEqual(
            ctx.exception.code,
            "E_CONTRATTO_LISTINO_RIMOZIONE_CON_ECCEZIONI",
        )
        self.assertIn("3 OVERRIDE", ctx.exception.detail or "")
        self.assertIn("2 ESCLUSIONE", ctx.exception.detail or "")
        repo.update_contratto.assert_not_called()

    # Scopo: aggiungere o sostituire il `listino_id` con righe attive blocca
    # (refactor 2026-05-20). Caso: contratto DRAFT senza listino, AGGIUNTE
    # caricate, l'utente prova a settare un listino → blocco semantico.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_contratto_aggiunge_listino_con_righe_bloccato(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        # Contratto attualmente senza listino (negoziato puro).
        testata = _testata_default()
        testata["listino_id"] = None
        repo.get_contratto.return_value = testata
        repo.count_righe_attive.return_value = 2  # 2 AGGIUNTE persistite

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().update_contratto(1, {"listino_id": 500})

        self.assertEqual(ctx.exception.code, "E_CONTRATTO_CAMPI_BLOCCATI_CON_RIGHE")
        self.assertIn("listino", (ctx.exception.detail or "").lower())
        repo.update_contratto.assert_not_called()

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_contratto_sostituisce_listino_con_righe_bloccato(self, repo_cls):
        # Sostituzione listino_id (100 → 200) con righe attive: blocco
        # anche se ci sono solo AGGIUNTE (potrebbero conflittare col nuovo listino).
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()  # listino_id=100
        repo.count_righe_attive.return_value = 1

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().update_contratto(1, {"listino_id": 200})

        self.assertEqual(ctx.exception.code, "E_CONTRATTO_CAMPI_BLOCCATI_CON_RIGHE")
        repo.update_contratto.assert_not_called()

    # Scopo: rimuovere il listino con SOLE AGGIUNTE (no OVERRIDE/ESCLUSIONE)
    # e' ammesso — le AGGIUNTE restano valide anche senza listino.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_contratto_rimuove_listino_solo_aggiunte_ok(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()  # listino_id=100
        repo.count_eccezioni_bloccanti.return_value = {
            "OVERRIDE": 0, "ESCLUSIONE": 0,
        }
        repo.update_contratto.return_value = True
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().update_contratto(1, {"listino_id": None})

        repo.update_contratto.assert_called_once()
        args = repo.update_contratto.call_args.args
        self.assertIsNone(args[1]["listino_id"])

    # --- cambio stato --------------------------------------------------

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_cambia_stato_codice_sconosciuto(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo_cls.return_value.get_stato_id_by_codice.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().cambia_stato(1, codice_interno="ATTIVO")
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_cambia_stato_negoziato_puro_senza_righe_tradotto(self, repo_cls):
        # Refactor modalita 2026-05-15: il guard `modalita_c_activation`
        # e' stato sostituito dal nuovo trigger DB che blocca attivazione di
        # un contratto senza listino se non ci sono AGGIUNTA con prezzo.
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_stato_id_by_codice.return_value = 2
        # Il messaggio simula il template emesso dal trigger DB: il marker
        # del service esige "contratto senza listino" + "almeno un'AGGIUNTA".
        repo.update_stato.side_effect = DatabaseError(
            "contratto senza listino e nessuna riga AGGIUNTA con prezzo: "
            "serve almeno un'AGGIUNTA prima di attivare."
        )

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().cambia_stato(1, codice_interno="ATTIVO")
        self.assertEqual(ctx.exception.code, "E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE")

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_cambia_stato_ok(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_stato_id_by_codice.return_value = 2
        repo.get_stato_codice.return_value = "ATTIVO"
        repo.update_stato.return_value = True
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().cambia_stato(1, codice_interno="ATTIVO")

        repo.update_stato.assert_called_once_with(1, 2)

    @patch("apps.vendite.services.contratti_service.transaction.atomic")
    @patch("apps.vendite.services.contratti_service.DocumentGenerationService")
    @patch("apps.vendite.services.contratti_service.DocumentiRepository")
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_cambia_stato_attivo_da_draft_genera_pdf_atomico(
        self, repo_cls, doc_repo_cls, gen_cls, _atomic,
    ):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_stato_id_by_codice.return_value = 2
        repo.get_stato_codice.return_value = "DRAFT"
        repo.update_stato.return_value = True
        repo.get_for_documento_generation.return_value = {
            "id": 1,
            "uid": "uid-contratto-1",
            "emittente_fiscale_id": 7,
        }
        repo.get_contratto.return_value = {
            **_testata_default(),
            "stato_codice": "ATTIVO",
        }
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []
        doc_repo_cls.return_value.get_sorgente_tipo_id_by_codice.return_value = {
            "id": 99,
            "attivo": True,
        }

        user = MagicMock()
        ContrattiService().cambia_stato(1, codice_interno="ATTIVO", user=user)

        gen_cls.return_value.genera_documento.assert_called_once_with(
            user,
            emittente_fiscale_id=7,
            sorgente_tipo_id=99,
            sorgente_id=1,
            sorgente_uid="uid-contratto-1",
        )

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
    def test_create_riga_esclusione_con_prezzo_fallisce(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()  # DRAFT

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().create_riga(
                1,
                {
                    "articolo_id": "00000000-0000-0000-0000-000000000001",
                    "tipo_eccezione": "ESCLUSIONE",
                    "prezzo_unitario": "10",  # vietato su ESCLUSIONE
                },
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertIn("prezzo_unitario deve essere NULL", ctx.exception.detail or "")
        repo.create_riga.assert_not_called()

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


# Scopo: REGRESSIONE review — il repository usa `%s::jsonb` per la colonna meta
#        (non `%s`) cosi' che driver senza auto-adattamento dict->jsonb non falliscano.
class ContrattiRepositoryJsonbTests(TestCase):
    @patch("apps.vendite.db.contratti_repository.connection")
    def test_repository_create_contratto_usa_cast_jsonb_per_meta(self, mock_connection):
        from apps.vendite.db.contratti_repository import ContrattiRepository

        cursor = MagicMock()
        cursor.fetchone.return_value = (1,)
        mock_connection.cursor.return_value.__enter__.return_value = cursor

        ContrattiRepository().create_contratto({
            "numero": "CNT0000001",
            "billing_account_id": 10,
            "istanza_utility_id": 20,
            "utility_id": 3,
            "valido_dal": date(2026, 1, 1),
            "stato_doc_contratto_id": 1,
            "meta": {"note": "test"},
        })

        sql = cursor.execute.call_args[0][0]
        self.assertIn("%s::jsonb", sql)
        params = cursor.execute.call_args[0][1]
        # meta serializzato a JSON string (non dict).
        meta_param = next(p for p in params if isinstance(p, str) and p.startswith("{"))
        self.assertEqual(meta_param, '{"note": "test"}')


# Scopo: smoke che il repository genera il numero tramite fn_generate_codice
#        (verifica solo l'SQL parametrico — la DB call e' mockata).
class ContrattiRepositoryNumberTests(TestCase):
    @patch("apps.vendite.db.contratti_repository.connection")
    def test_generate_numero_calls_fn_generate_codice(self, mock_connection):
        from apps.vendite.db.contratti_repository import ContrattiRepository

        cursor = MagicMock()
        cursor.fetchone.return_value = ("CNT0000001",)
        mock_connection.cursor.return_value.__enter__.return_value = cursor

        result = ContrattiRepository().generate_numero()

        self.assertEqual(result, "CNT0000001")
        cursor.execute.assert_called_once_with(
            "SELECT script.fn_generate_codice(%s)", ["contratto"]
        )


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
    def test_update_componente_anti_tampering_riga(self, repo_cls):
        """riga_id URL non matcha riga reale → E_VENDITE_NOT_FOUND."""
        from apps.vendite.services.contratti_service import ContrattiService

        repo = MagicMock()
        # 1-JOIN: componente esiste ma appartiene a riga 99, non 5
        repo.load_componente_with_scope.return_value = {
            "componente_id": 100,
            "riga_contratto_id": 99,
            "contratto_id": 1,
            "stato_codice": "DRAFT",
        }
        repo_cls.return_value = repo

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().update_componente_riga(
                1, 5, 100, {"prezzo_unitario": "10"},
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")

    @patch("apps.vendite.services.contratti_service.transaction.atomic")
    @patch(
        "apps.vendite.services.contratti_service.ContrattiService."
        "_resolve_emittente_sr_id_for_contratto",
        return_value=99,
    )
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_riga_articolo_composito_auto_init(
        self, repo_cls, _mock_resolve, _mock_atomic,
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
            "stato_codice": "DRAFT",
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


class ContrattiServiceFonteQuantitaTests(TestCase):
    """Suite refactor 2026-05-19: coerenza (tipo_erogazione, fonte_quantita_attesa)
    e normalizzazione `quantita` in `_apply_fonte_quantita_logic`.

    Defense-in-depth lato BE: il DB applica CHECK chk_contrighe_coerenza_fonte_erogazione
    + trigger trg_contratti_righe_a10_default_fonte_qta_ins_upd (migrations
    20260519-05/06). Qui verifichiamo che il service applichi la stessa logica
    PRIMA del round-trip DB, con errore parlante.

    Riferimento: docs/it/dev/work-done/refactor-contratti-fonte-quantita.md §2.

    Indice test:
    1) test_apply_default_fonte_per_tipo_in_create — 4 sub-test
    2) test_apply_no_default_fonte_in_update — i default sono solo create
    3) test_combinazione_vietata_solleva — 7 sub-test (matrice CHECK DB)
    4) test_combinazione_ammessa_passa — sub-test sulle combo default/valide
    5) test_fonte_fissa_richiede_quantita_positiva
    6) test_fonte_downstream_forza_quantita_null — 3 sub-test (MANUALE/TIMESHEET/LETTURE)
    7) test_fonte_downstream_forza_qta_operativa_anche_se_assente_dal_payload
       (regressione bug 2026-05-19 asimmetria normalizzazione)
    8) test_fonte_derivata_componenti_non_normalizza_quantita
    """

    def _service(self):
        # Service stateless rispetto a _apply_fonte_quantita_logic. Niente mock.
        from apps.vendite.services.contratti_service import ContrattiService
        return ContrattiService()

    # -- Default --------------------------------------------------------

    def test_apply_default_fonte_per_tipo_in_create(self):
        svc = self._service()
        attesi = {
            "CANONE": "FISSA",
            "UNA_TANTUM": "FISSA",
            "ORARIO": "MANUALE",
            "CONSUMO": "LETTURE",
        }
        for tipo, fonte_attesa in attesi.items():
            with self.subTest(tipo=tipo):
                data = {"tipo_erogazione": tipo, "quantita": Decimal("1")}
                svc._apply_fonte_quantita_logic(data, for_create=True)
                self.assertEqual(data.get("fonte_quantita_attesa"), fonte_attesa)

    def test_apply_no_default_fonte_in_update(self):
        # In update non auto-applichiamo default: la decisione del trigger DB
        # (reset solo se la combo diventa vietata) e' speculare lato BE.
        svc = self._service()
        data = {"tipo_erogazione": "CANONE"}
        svc._apply_fonte_quantita_logic(data, for_create=False)
        self.assertNotIn("fonte_quantita_attesa", data)

    # -- Guard combinazioni vietate --------------------------------------

    def test_combinazione_vietata_solleva(self):
        svc = self._service()
        vietate = [
            ("CANONE", "TIMESHEET"),
            ("CANONE", "LETTURE"),
            ("UNA_TANTUM", "TIMESHEET"),
            ("UNA_TANTUM", "LETTURE"),
            ("ORARIO", "LETTURE"),
            ("CONSUMO", "FISSA"),
            ("CONSUMO", "TIMESHEET"),
        ]
        for tipo, fonte in vietate:
            with self.subTest(tipo=tipo, fonte=fonte):
                data = {
                    "tipo_erogazione": tipo,
                    "fonte_quantita_attesa": fonte,
                    "quantita": Decimal("1"),
                }
                with self.assertRaises(ServiceError) as ctx:
                    svc._apply_fonte_quantita_logic(data, for_create=True)
                self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
                self.assertIn("Combinazione vietata", ctx.exception.detail or "")

    def test_combinazione_ammessa_passa(self):
        svc = self._service()
        ammesse = [
            ("CANONE", "FISSA"),
            ("CANONE", "MANUALE"),
            ("CANONE", "DERIVATA_COMPONENTI"),
            ("UNA_TANTUM", "FISSA"),
            ("ORARIO", "MANUALE"),
            ("ORARIO", "TIMESHEET"),
            ("CONSUMO", "MANUALE"),
            ("CONSUMO", "LETTURE"),
            ("CONSUMO", "DERIVATA_COMPONENTI"),
        ]
        for tipo, fonte in ammesse:
            with self.subTest(tipo=tipo, fonte=fonte):
                # Per FISSA serve qta positiva (guard 2.3); usiamo DERIVATA o
                # qta_operativa per le altre per non rompere la guard FISSA.
                data = {
                    "tipo_erogazione": tipo,
                    "fonte_quantita_attesa": fonte,
                    "qta_operativa": Decimal("1") if fonte == "FISSA" else None,
                }
                # Non deve sollevare.
                svc._apply_fonte_quantita_logic(data, for_create=True)

    # -- Normalizzazione quantita ---------------------------------------

    def test_fonte_fissa_richiede_quantita_positiva(self):
        svc = self._service()
        data = {
            "tipo_erogazione": "CANONE",
            "fonte_quantita_attesa": "FISSA",
            # nessuna quantita ne' qta_operativa
        }
        with self.assertRaises(ServiceError) as ctx:
            svc._apply_fonte_quantita_logic(data, for_create=True)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertIn("quantita > 0", ctx.exception.detail or "")

    def test_fonte_downstream_forza_quantita_null(self):
        svc = self._service()
        fonti_downstream = [
            ("CANONE", "MANUALE"),    # rara ma ammessa
            ("ORARIO", "TIMESHEET"),  # naturale
            ("CONSUMO", "LETTURE"),   # naturale
        ]
        for tipo, fonte in fonti_downstream:
            with self.subTest(tipo=tipo, fonte=fonte):
                data = {
                    "tipo_erogazione": tipo,
                    "fonte_quantita_attesa": fonte,
                    "quantita": Decimal("5"),  # ignorata
                    "qta_operativa": Decimal("3"),  # ignorata
                }
                svc._apply_fonte_quantita_logic(data, for_create=True)
                self.assertIsNone(data["quantita"])
                self.assertIsNone(data["qta_operativa"])

    def test_fonte_downstream_forza_qta_operativa_anche_se_assente_dal_payload(self):
        # Regressione bug 2026-05-19: in update parziale `{fonte_quantita_attesa:
        # 'MANUALE'}` (l'utente cambia solo la fonte da FISSA a MANUALE), il
        # service deve forzare a NULL ENTRAMBI `quantita` e `qta_operativa` nel
        # `data`, anche se il payload non contiene `qta_operativa`. Altrimenti
        # il trigger DB `trgfn_qta_from_operativa` riscrive `quantita` =
        # `qta_operativa` post-UPDATE, vanificando il NULL.
        svc = self._service()
        data = {
            "tipo_erogazione": "CANONE",
            "fonte_quantita_attesa": "MANUALE",
            # nessuna quantita/qta_operativa nel data
        }
        # Payload vuoto (simula update parziale senza qta).
        svc._apply_fonte_quantita_logic(data, for_create=False)
        self.assertIsNone(data.get("quantita"))
        self.assertIsNone(data.get("qta_operativa"))

    def test_fonte_derivata_componenti_non_normalizza_quantita(self):
        # DERIVATA_COMPONENTI: il trigger DB z90_propaga_qta_componenti scrive
        # `quantita` post-INSERT figli. Il service NON deve toccarla
        # (ne' forzare NULL, ne' validare > 0). Lascia passare il valore del
        # payload o NULL se assente.
        svc = self._service()
        data = {
            "tipo_erogazione": "CANONE",
            "fonte_quantita_attesa": "DERIVATA_COMPONENTI",
            # nessuna quantita: il trigger DB la calcola
        }
        # Non deve sollevare ne' settare quantita.
        svc._apply_fonte_quantita_logic(data, for_create=True)
        self.assertNotIn("quantita", data)


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

        with patch(
            "apps.vendite.services.contratti_service."
            "resolve_emittente_sr_id_for_testata",
            return_value=999,
        ), patch(
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
