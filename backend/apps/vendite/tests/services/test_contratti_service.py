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

    # Scopo: modalita' A (listino + variazione, nessun override) -> tutte
    #        le righe da listino, modalita' derivata 'A'.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_list_righe_preview_modalita_A(self, repo_cls):
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

        self.assertEqual(result["modalita"], "A")
        self.assertEqual(result["listino_id"], 100)
        self.assertEqual(len(result["righe"]), 1)
        self.assertEqual(result["righe"][0]["origine"], "DA_LISTINO")

    # Scopo: modalita' B (listino + almeno un override) -> modalita'
    #        derivata 'B' grazie al riconoscimento origine='OVERRIDE'.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_list_righe_preview_modalita_B(self, repo_cls):
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

        self.assertEqual(result["modalita"], "B")
        self.assertEqual(len(result["righe"]), 2)

    # Scopo: modalita' C (listino_id NULL) -> nessuna preview, lista vuota,
    #        nessuna chiamata a list_righe_preview del repository.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_list_righe_preview_modalita_C(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        testata_c = _testata_default()
        testata_c["listino_id"] = None
        testata_c["tipo_variazione_globale"] = None
        testata_c["valore_variazione_globale"] = None
        repo.get_contratto.return_value = testata_c

        result = ContrattiService().list_righe_preview(1)

        self.assertEqual(result["modalita"], "C")
        self.assertEqual(result["listino_id"], None)
        self.assertEqual(result["righe"], [])
        # Per design C non e` "senza versione": la lista vuota e' attesa.
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

    # Scopo: contratto modalita' B con override per articoli NON presenti nel
    #        listino (caso "extra-listino"). La query SQL prende le righe
    #        con UNION ALL: la parte 2 cattura override senza match listino
    #        e li espone come origine='OVERRIDE'. Modalita' resta 'B' (ha
    #        almeno un override). Flag listino_senza_versione_oggi=True
    #        perche' nessuna riga ha origine='DA_LISTINO'.
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_list_righe_preview_solo_override_extra_listino(self, repo_cls):
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

        self.assertEqual(result["modalita"], "B")
        self.assertEqual(len(result["righe"]), 1)
        self.assertEqual(result["righe"][0]["origine"], "OVERRIDE")
        self.assertTrue(result["listino_senza_versione_oggi"])

    # --- create contratto ---------------------------------------------

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_contratto_modalita_A_ok(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.generate_numero.return_value = "CNT0000001"
        repo.get_stato_id_by_codice.return_value = 1
        repo.create_contratto.return_value = 1
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
    def test_create_contratto_modalita_C_con_variazione_fallisce(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().create_contratto({
                "billing_account_id": 10,
                "istanza_utility_id": 20,
                "utility_id": 3,
                "valido_dal": "2026-01-01",
                # Nessun listino -> modalita' C. Variazione NON ammessa.
                "tipo_variazione_globale": "PERCENTUALE",
                "valore_variazione_globale": "5",
            })
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertIn("modalita' C", ctx.exception.detail or "")

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_contratto_variazione_coppia_incompleta_fallisce(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().create_contratto({
                "billing_account_id": 10,
                "istanza_utility_id": 20,
                "utility_id": 3,
                "valido_dal": "2026-01-01",
                "listino_id": 100,
                "tipo_variazione_globale": "PERCENTUALE",
                # valore_variazione_globale mancante -> coppia incoerente.
            })
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

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

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_contratto_ok_variazione(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.update_contratto.return_value = True
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().update_contratto(1, {
            "listino_id": 200,
            "tipo_variazione_globale": "VALORE_FISSO",
            "valore_variazione_globale": "5",
        })

        args = repo.update_contratto.call_args.args
        self.assertEqual(args[0], 1)
        self.assertEqual(args[1]["listino_id"], 200)
        self.assertEqual(args[1]["tipo_variazione_globale"], "VALORE_FISSO")
        self.assertEqual(args[1]["valore_variazione_globale"], Decimal("5"))

    # --- cambio stato --------------------------------------------------

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_cambia_stato_codice_sconosciuto(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo_cls.return_value.get_stato_id_by_codice.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().cambia_stato(1, codice_interno="ATTIVO")
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_cambia_stato_modalita_C_senza_righe_tradotto(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_stato_id_by_codice.return_value = 2
        repo.update_stato.side_effect = DatabaseError(
            "Contratto CNT0000001 modalita' C senza righe attive: non attivabile."
        )

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().cambia_stato(1, codice_interno="ATTIVO")
        self.assertEqual(ctx.exception.code, "E_CONTRATTO_MODALITA_C_SENZA_RIGHE")

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

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_riga_modalita_C_senza_prezzo_tradotto(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()  # DRAFT
        repo.create_riga.side_effect = DatabaseError(
            "Contratto CNT0001 riga 5 (articolo X): prezzo_unitario obbligatorio in modalita' C."
        )

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().create_riga(
                1,
                {"articolo_id": "00000000-0000-0000-0000-000000000001"},
            )
        self.assertEqual(ctx.exception.code, "E_CONTRATTO_MODALITA_C_RIGA_SENZA_PREZZO")

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_riga_ok(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()  # DRAFT
        repo.create_riga.return_value = 77
        repo.get_riga.return_value = {"id": 77, "prezzo_unitario": Decimal("25.50")}

        result = ContrattiService().create_riga(
            1,
            {
                "articolo_id": "00000000-0000-0000-0000-000000000001",
                "prezzo_unitario": "25.50",
                "ordine": 10,
            },
        )

        self.assertEqual(result["id"], 77)
        args = repo.create_riga.call_args.args
        self.assertEqual(args[0], 1)
        self.assertEqual(args[1]["prezzo_unitario"], Decimal("25.50"))

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
        "apps.vendite.services.contratti_service.ContrattiService."
        "_resolve_emittente_sr_id_for_contratto",
        return_value=99,
    )
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_preview_componenti_riga_ok(self, repo_cls, _mock_resolve):
        """Preview chiama repo.preview_componenti_riga con args derivati dal contratto."""
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
    def test_create_riga_articolo_composito_skip_init_senza_emittente(
        self, repo_cls, _mock_resolve, _mock_atomic,
    ):
        """Articolo composito + emittente non risolvibile → skip init con log warning."""
        from apps.vendite.services.contratti_service import ContrattiService

        repo = MagicMock()
        repo.get_contratto.return_value = _testata_default()
        repo.create_riga.return_value = 500
        repo.is_articolo_composito.return_value = True
        repo.get_riga.return_value = {"id": 500, "contratto_id": 1}
        repo_cls.return_value = repo

        with self.assertLogs(
            "apps.vendite.services.contratti_service", level="WARNING",
        ) as logs:
            ContrattiService().create_riga(
                1,
                {"articolo_id": "019d544c-7ef6-7993-9dcb-0cd1ad77d4aa", "prezzo_unitario": "0", "quantita": "1"},
                auth_user_id=None,
            )

        # Init NON chiamato + warning emesso per audit.
        repo.init_componenti_riga.assert_not_called()
        self.assertTrue(
            any("auto_init_componenti_skipped" in msg for msg in logs.output),
            f"Atteso warning skip in: {logs.output}",
        )

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
            {"articolo_id": "019d53f6-58ca-7cb7-b77b-86d201ce9787", "prezzo_unitario": "10", "quantita": "1"},
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
