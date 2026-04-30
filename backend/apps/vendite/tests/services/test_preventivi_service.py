# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari service preventivi vendita (CRUD, stato, righe, integrazione).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_crea_preventivo_ok — creazione con campi minimi
2) test_crea_preventivo_utility_mancante — validazione utility obbligatoria
3) test_aggiorna_preventivo_ok — aggiornamento in BOZZA
4) test_aggiorna_preventivo_stato_non_modificabile — guard su stato EMESSO
5) test_gestisci_riga_ok — aggiunta riga in BOZZA con ricalcolo totali
6) test_gestisci_riga_stato_non_modificabile — guard riga su stato EMESSO
7) test_gestisci_riga_articolo_mancante — validazione articolo_id obbligatorio
8) test_elimina_riga_ok — soft delete riga
9) test_elimina_riga_not_found — riga inesistente
10) test_push_a_commessa_ok — push preventivo ACCETTATO con righe eleggibili
11) test_push_a_commessa_stato_non_ammesso — guard su stato BOZZA
12) test_push_a_commessa_nessuna_riga — guard nessuna riga eleggibile
13) test_genera_pratica_ok — genera pratica da ACCETTATO via BB crea_pratica
14) test_genera_pratica_stato_non_ammesso — guard su stato BOZZA
15) test_genera_pratica_ba_mancante — guard billing_account_id obbligatorio
16) test_get_preventivo_not_found — preventivo inesistente
16b) test_get_preventivo_include_capabilities — Fase 1: capabilities + righe + indirizzi nel detail
17) test_list_preventivi_paginazione_invalida — page < 1
18) test_gestisci_riga_auto_fill_da_resolver — prezzo popolato da resolver se assente
19) test_gestisci_riga_prezzo_uguale_resolver_ok — payload = resolver ok senza permesso
20) test_gestisci_riga_override_non_autorizzato — L1 blocca override senza permesso
21) test_gestisci_riga_override_superuser_ok — superuser bypassa L1, meta MANUALE
22) test_gestisci_riga_L2_sconto_entro_limite_ok — L1 ok + sconto 10% <= limite 15%
23) test_gestisci_riga_L2_sconto_oltre_limite_bloccato — sconto 20% > limite 15% -> E_PREV_SCONTO_ECCESSIVO
24) test_gestisci_riga_L2_maggiorazione_oltre_limite_bloccato — +10% > limite 5% -> E_PREV_MAGGIORAZIONE_ECCESSIVA
25) test_gestisci_riga_L2_superuser_bypass — superuser salta anche L2
"""

import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from apps.core.services.service_errors import ServiceError


class TestPreventiviService(unittest.TestCase):

    def setUp(self):
        # Scopo: Prepara mock del repository per tutti i test.
        self.repo_patcher = patch(
            "apps.vendite.services.preventivi_service.PreventiviRepository"
        )
        self.MockRepoClass = self.repo_patcher.start()
        self.mock_repo = MagicMock()
        self.MockRepoClass.return_value = self.mock_repo

        # Default: lookup config
        self.mock_repo.get_stato_bozza_id.return_value = 1
        self.mock_repo.get_sorgente_tipo_preventivo_id.return_value = 10
        # Default: capabilities vuote per i test che non si interessano del blob
        # (Fase 1 refactor frontend vendite: get_preventivo invoca la fn DB).
        self.mock_repo.get_capabilities.return_value = {}

    def tearDown(self):
        self.repo_patcher.stop()

    # ── Creazione ──

    # Scopo: Verifica creazione preventivo con campi minimi.
    def test_crea_preventivo_ok(self):
        from apps.vendite.services.preventivi_service import crea_preventivo

        self.mock_repo.create_preventivo.return_value = {
            "id": 1, "uid": "abc-123", "numero": "P-0001",
        }
        result = crea_preventivo({"utility_id": 5})
        self.assertEqual(result["id"], 1)
        self.mock_repo.create_preventivo.assert_called_once()

    # Scopo: Verifica errore se utility_id mancante.
    def test_crea_preventivo_utility_mancante(self):
        from apps.vendite.services.preventivi_service import crea_preventivo

        with self.assertRaises(ServiceError) as ctx:
            crea_preventivo({})
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")

    # ── Aggiornamento ──

    # Scopo: Verifica aggiornamento in stato BOZZA.
    def test_aggiorna_preventivo_ok(self):
        from apps.vendite.services.preventivi_service import aggiorna_preventivo

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
        }
        self.mock_repo.update_preventivo.return_value = True
        result = aggiorna_preventivo(1, {"validita_dal": "2026-04-01"})
        self.assertEqual(result["status"], "ok")

    # Scopo: Verifica guard su stato EMESSO.
    def test_aggiorna_preventivo_stato_non_modificabile(self):
        from apps.vendite.services.preventivi_service import aggiorna_preventivo

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "EMESSO", "uid": "abc",
        }
        with self.assertRaises(ServiceError) as ctx:
            aggiorna_preventivo(1, {"validita_dal": "2026-04-01"})
        self.assertEqual(ctx.exception.code, "E_PREV_STATO_NON_MODIFICABILE")

    # ── Righe ──

    # Scopo: Verifica aggiunta riga in BOZZA con ricalcolo totali.
    def test_gestisci_riga_ok(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
        }
        self.mock_repo.create_riga.return_value = {"id": 10}
        result = gestisci_riga(1, {"articolo_id": "uuid-art-1"})
        self.assertEqual(result["id"], 10)
        self.mock_repo.create_riga.assert_called_once()

    # Scopo: Verifica guard riga su stato EMESSO.
    def test_gestisci_riga_stato_non_modificabile(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "EMESSO", "uid": "abc",
        }
        with self.assertRaises(ServiceError) as ctx:
            gestisci_riga(1, {"articolo_id": "uuid-art-1"})
        self.assertEqual(ctx.exception.code, "E_PREV_STATO_NON_MODIFICABILE")

    # Scopo: Verifica errore se articolo_id mancante.
    def test_gestisci_riga_articolo_mancante(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
        }
        with self.assertRaises(ServiceError) as ctx:
            gestisci_riga(1, {"quantita": "10"})
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")

    # Scopo: Verifica soft delete riga.
    def test_elimina_riga_ok(self):
        from apps.vendite.services.preventivi_service import elimina_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
        }
        self.mock_repo.delete_riga.return_value = True
        result = elimina_riga(1, 10)
        self.assertEqual(result["status"], "ok")

    # Scopo: Verifica errore riga inesistente.
    def test_elimina_riga_not_found(self):
        from apps.vendite.services.preventivi_service import elimina_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
        }
        self.mock_repo.delete_riga.return_value = False
        with self.assertRaises(ServiceError) as ctx:
            elimina_riga(1, 999)
        self.assertEqual(ctx.exception.code, "E_PREV_RIGA_NOT_FOUND")

    # ── Push commessa ──

    # Scopo: Verifica push preventivo ACCETTATO con righe eleggibili.
    def test_push_a_commessa_ok(self):
        from apps.vendite.services.preventivi_service import push_a_commessa

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "ACCETTATO", "uid": "abc",
        }
        self.mock_repo.count_righe_pushable.return_value = 3
        result = push_a_commessa(1)
        self.assertEqual(result["righe_pushable"], 3)

    # Scopo: Verifica guard su stato non ACCETTATO.
    def test_push_a_commessa_stato_non_ammesso(self):
        from apps.vendite.services.preventivi_service import push_a_commessa

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
        }
        with self.assertRaises(ServiceError) as ctx:
            push_a_commessa(1)
        self.assertEqual(ctx.exception.code, "E_PREV_STATO_TRANSIZIONE")

    # Scopo: Verifica guard nessuna riga eleggibile.
    def test_push_a_commessa_nessuna_riga(self):
        from apps.vendite.services.preventivi_service import push_a_commessa

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "ACCETTATO", "uid": "abc",
        }
        self.mock_repo.count_righe_pushable.return_value = 0
        with self.assertRaises(ServiceError) as ctx:
            push_a_commessa(1)
        self.assertEqual(ctx.exception.code, "E_PREV_NESSUNA_RIGA")

    # ── Genera pratica ──

    # Scopo: Verifica generazione pratica da preventivo ACCETTATO via BB crea_pratica.
    @patch("apps.pratiche.services.pratiche_service.crea_pratica", return_value=42)
    def test_genera_pratica_ok(self, mock_crea_pratica):
        from apps.vendite.services.preventivi_service import genera_pratica

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "ACCETTATO", "uid": "abc-uid",
            "billing_account_id": 10, "istanza_utility_id": 5,
        }
        self.mock_repo.resolve_contesto_pratica.return_value = {
            "emittente_fiscale_id": 100,
            "soggetto_id": "sogg-uuid",
            "soggetto_ruolo_id": 20,
        }
        self.mock_repo.link_pratica.return_value = {"id": 1}

        result = genera_pratica(1, tipo_prestazione_id=3, priorita_id=1)
        self.assertEqual(result["pratica_id"], 42)
        self.assertEqual(result["preventivo_id"], 1)
        # Verifica che crea_pratica BB sia stato chiamato con contesto corretto
        mock_crea_pratica.assert_called_once_with(
            emittente_fiscale_id=100,
            tipo_prestazione_id=3,
            soggetto_id="sogg-uuid",
            soggetto_ruolo_id=20,
            istanza_utility_id=5,
            priorita_id=1,
            descrizione=None,
        )
        # Verifica link pratica_sorgenti
        self.mock_repo.link_pratica.assert_called_once_with(
            pratica_id=42,
            sorgente_tipo_id=10,
            sorgente_uid="abc-uid",
        )

    # Scopo: Verifica guard su stato non ACCETTATO.
    def test_genera_pratica_stato_non_ammesso(self):
        from apps.vendite.services.preventivi_service import genera_pratica

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            "billing_account_id": 10,
        }
        with self.assertRaises(ServiceError) as ctx:
            genera_pratica(1, tipo_prestazione_id=3, priorita_id=1)
        self.assertEqual(ctx.exception.code, "E_PREV_PRATICA_STATO")

    # Scopo: Verifica guard billing_account_id obbligatorio per genera pratica.
    def test_genera_pratica_ba_mancante(self):
        from apps.vendite.services.preventivi_service import genera_pratica

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "ACCETTATO", "uid": "abc",
            "billing_account_id": None,
        }
        with self.assertRaises(ServiceError) as ctx:
            genera_pratica(1, tipo_prestazione_id=3, priorita_id=1)
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")

    # ── Not found ──

    # Scopo: Verifica errore preventivo non trovato.
    def test_get_preventivo_not_found(self):
        from apps.vendite.services.preventivi_service import get_preventivo

        self.mock_repo.get_preventivo.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            get_preventivo(999)
        self.assertEqual(ctx.exception.code, "E_PREV_NOT_FOUND")

    # Scopo: Verifica che get_preventivo includa capabilities + righe_count + indirizzi
    #        senza embeddare le righe (Fase 3.F6 refactor frontend vendite: il FE
    #        legge le righe via endpoint /righe/ autonomo).
    def test_get_preventivo_include_capabilities(self):
        from apps.vendite.services.preventivi_service import get_preventivo

        self.mock_repo.get_preventivo.return_value = {
            "id": 42, "uid": "abc", "numero": "P-0042",
            "stato_codice": "ACCETTATO", "stato_codice_interno": "ACCETTATO",
            "billing_account_id": 10, "utility_id": 3,
        }
        self.mock_repo.list_righe.return_value = [{"id": 1, "ordine": 1}, {"id": 2, "ordine": 2}]
        self.mock_repo.list_indirizzi.return_value = []
        self.mock_repo.get_capabilities.return_value = {
            "stato_codice": "ACCETTATO",
            "available_actions": [{"key": "annulla", "target_state": "ANNULLATO",
                                    "label_key": "preventivi.azione_annulla",
                                    "severity": "danger", "icon": "pi pi-times",
                                    "requires_confirm": True}],
            "can_edit_testata": False,
            "can_edit_righe": False,
            "can_create_revisione": True,
            "can_push_commessa": True,
            "can_push_commessa_reason": None,
            "non_editable_fields": ["billing_account_id", "utility_id"],
        }

        result = get_preventivo(42)

        # Testata + capability + summary leggero. NO `righe` embeddate.
        self.assertEqual(result["id"], 42)
        self.assertEqual(result["can_edit_testata"], False)
        self.assertEqual(result["can_edit_righe"], False)
        self.assertEqual(result["can_create_revisione"], True)
        self.assertEqual(result["can_push_commessa"], True)
        self.assertEqual(len(result["available_actions"]), 1)
        self.assertEqual(result["available_actions"][0]["key"], "annulla")
        self.assertIn("billing_account_id", result["non_editable_fields"])
        # Fase 3.F6: detail non include `righe` ma solo `righe_count` (summary).
        self.assertNotIn("righe", result)
        self.assertEqual(result["righe_count"], 2)
        self.assertEqual(result["indirizzi"], [])
        self.mock_repo.get_capabilities.assert_called_once_with(42)

    # ── Paginazione ──

    # Scopo: Verifica errore paginazione invalida.
    def test_list_preventivi_paginazione_invalida(self):
        from apps.vendite.services.preventivi_service import list_preventivi

        with self.assertRaises(ServiceError) as ctx:
            list_preventivi(page=0, page_size=50)
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")

    # ── Sprint 2: wiring pricing v5 + L1 override ──

    # Helper: testata completa (BA+utility+data) per attivare il resolver.
    def _testata_completa(self):
        return {
            "id": 1,
            "stato_codice_interno": "DRAFT",
            "uid": "abc",
            "billing_account_id": 10,
            "utility_id": 3,
            "data": "2026-04-17",
        }

    # Scopo: Auto-fill prezzo dal resolver quando payload non specifica
    #        prezzo_unitario e testata ha BA+utility+data validi.
    @patch("apps.vendite.services.preventivi_service.suggerisci_prezzo_riga")
    def test_gestisci_riga_auto_fill_da_resolver(self, mock_suggerisci):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = self._testata_completa()
        self.mock_repo.create_riga.return_value = {"id": 11}
        mock_suggerisci.return_value = {
            "prezzo_finale": "50.00", "origine": "CATEGORIA",
            "listino_id": 100, "contratto_id": None, "promo_id": None,
            "tipo_variazione_applicata": "PERCENTUALE",
            "valore_variazione_applicata": "-5.00",
        }

        gestisci_riga(
            1,
            {"articolo_id": "uuid-art-1", "uom_operativa_id": 1},
            auth_user_id=42,
        )

        call = self.mock_repo.create_riga.call_args.kwargs
        # Prezzo popolato dal resolver
        self.assertIsNotNone(call["prezzo_unitario"])
        # Meta audit con origine = valore resolver
        self.assertEqual(call["meta"]["origine_prezzo"], "CATEGORIA")
        self.assertEqual(call["meta"]["prezzo_resolver_context"]["listino_id"], 100)

    # Scopo: Override prezzo ammesso se payload == resolver (no check permesso).
    @patch("apps.vendite.services.preventivi_service.suggerisci_prezzo_riga")
    def test_gestisci_riga_prezzo_uguale_resolver_ok(self, mock_suggerisci):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = self._testata_completa()
        self.mock_repo.create_riga.return_value = {"id": 12}
        mock_suggerisci.return_value = {
            "prezzo_finale": "50.00", "origine": "CATEGORIA",
            "listino_id": 100, "contratto_id": None, "promo_id": None,
            "tipo_variazione_applicata": None,
            "valore_variazione_applicata": None,
        }

        # Prezzo passato uguale a quello del resolver -> accettato
        gestisci_riga(
            1,
            {"articolo_id": "uuid-art-1", "uom_operativa_id": 1, "prezzo_unitario": "50.00"},
            auth_user_id=42,
        )

        call = self.mock_repo.create_riga.call_args.kwargs
        self.assertEqual(str(call["prezzo_unitario"]), "50.00")
        # Origine = resolver (non MANUALE)
        self.assertEqual(call["meta"]["origine_prezzo"], "CATEGORIA")

    # Scopo: L1 — override prezzo (payload != resolver) bloccato se l'utente
    #        non ha permesso azione prezzo_override_manuale.
    @patch("apps.vendite.services.preventivi_service.get_user_model")
    @patch("apps.vendite.services.preventivi_service.PermissionResolver")
    @patch("apps.vendite.services.preventivi_service.suggerisci_prezzo_riga")
    def test_gestisci_riga_override_non_autorizzato(
        self, mock_suggerisci, mock_perm, mock_user_model
    ):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = self._testata_completa()
        mock_suggerisci.return_value = {
            "prezzo_finale": "50.00", "origine": "CATEGORIA",
            "listino_id": 100, "contratto_id": None, "promo_id": None,
            "tipo_variazione_applicata": None,
            "valore_variazione_applicata": None,
        }
        # User non superuser, azione NON abilitata
        mock_user = MagicMock()
        mock_user.is_superuser = False
        mock_user_model.return_value.objects.get.return_value = mock_user
        mock_perm.check_azione.return_value = False

        with self.assertRaises(ServiceError) as ctx:
            gestisci_riga(
                1,
                {"articolo_id": "uuid-art-1", "uom_operativa_id": 1, "prezzo_unitario": "45.00"},
                auth_user_id=42,
            )
        self.assertEqual(ctx.exception.code, "E_PREV_OVERRIDE_NON_AUTORIZZATO")
        self.mock_repo.create_riga.assert_not_called()

    # Scopo: L1 — override prezzo ammesso per superuser (bypass).
    @patch("apps.vendite.services.preventivi_service.get_user_model")
    @patch("apps.vendite.services.preventivi_service.suggerisci_prezzo_riga")
    def test_gestisci_riga_override_superuser_ok(
        self, mock_suggerisci, mock_user_model
    ):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = self._testata_completa()
        self.mock_repo.create_riga.return_value = {"id": 13}
        mock_suggerisci.return_value = {
            "prezzo_finale": "50.00", "origine": "CATEGORIA",
            "listino_id": 100, "contratto_id": None, "promo_id": None,
            "tipo_variazione_applicata": None,
            "valore_variazione_applicata": None,
        }
        # Superuser bypassa il check
        mock_user = MagicMock()
        mock_user.is_superuser = True
        mock_user_model.return_value.objects.get.return_value = mock_user

        gestisci_riga(
            1,
            {"articolo_id": "uuid-art-1", "uom_operativa_id": 1, "prezzo_unitario": "45.00"},
            auth_user_id=42,
        )

        call = self.mock_repo.create_riga.call_args.kwargs
        self.assertEqual(str(call["prezzo_unitario"]), "45.00")
        # Meta audit con origine MANUALE + delta tracciato
        self.assertEqual(call["meta"]["origine_prezzo"], "MANUALE")
        self.assertEqual(call["meta"]["prezzo_base_resolver"], "50.00")
        self.assertEqual(call["meta"]["delta_override"], "-5.00")

    # Scopo: L2 — sconto entro il limite VENDITE_MAX_SCONTO_PCT passa.
    #        Resolver 50, manuale 45 = -10% sconto, limite 15% -> OK.
    @patch("apps.vendite.services.preventivi_service.ParameterService")
    @patch("apps.vendite.services.preventivi_service.get_user_model")
    @patch("apps.vendite.services.preventivi_service.PermissionResolver")
    @patch("apps.vendite.services.preventivi_service.suggerisci_prezzo_riga")
    def test_gestisci_riga_L2_sconto_entro_limite_ok(
        self, mock_suggerisci, mock_perm, mock_user_model, mock_param_service
    ):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = self._testata_completa()
        self.mock_repo.create_riga.return_value = {"id": 30}
        mock_suggerisci.return_value = {
            "prezzo_finale": "50.00", "origine": "CATEGORIA",
            "listino_id": 100, "contratto_id": None, "promo_id": None,
            "tipo_variazione_applicata": None,
            "valore_variazione_applicata": None,
        }
        mock_user = MagicMock()
        mock_user.is_superuser = False
        mock_user_model.return_value.objects.get.return_value = mock_user
        mock_perm.check_azione.return_value = True  # L1 ok
        # L2: limite sconto 15% -> sconto 10% ammesso.
        mock_param_service.return_value.get_parameter_decimal.return_value = Decimal("15")

        gestisci_riga(
            1,
            {"articolo_id": "uuid-art-1", "uom_operativa_id": 1, "prezzo_unitario": "45.00"},
            auth_user_id=42,
        )

        call = self.mock_repo.create_riga.call_args.kwargs
        self.assertEqual(str(call["prezzo_unitario"]), "45.00")
        self.assertEqual(call["meta"]["origine_prezzo"], "MANUALE")

    # Scopo: L2 — sconto oltre il limite blocca con E_PREV_SCONTO_ECCESSIVO.
    #        Resolver 50, manuale 40 = -20% sconto, limite 15% -> bloccato.
    @patch("apps.vendite.services.preventivi_service.ParameterService")
    @patch("apps.vendite.services.preventivi_service.get_user_model")
    @patch("apps.vendite.services.preventivi_service.PermissionResolver")
    @patch("apps.vendite.services.preventivi_service.suggerisci_prezzo_riga")
    def test_gestisci_riga_L2_sconto_oltre_limite_bloccato(
        self, mock_suggerisci, mock_perm, mock_user_model, mock_param_service
    ):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = self._testata_completa()
        mock_suggerisci.return_value = {
            "prezzo_finale": "50.00", "origine": "CATEGORIA",
            "listino_id": 100, "contratto_id": None, "promo_id": None,
            "tipo_variazione_applicata": None,
            "valore_variazione_applicata": None,
        }
        mock_user = MagicMock()
        mock_user.is_superuser = False
        mock_user_model.return_value.objects.get.return_value = mock_user
        mock_perm.check_azione.return_value = True  # L1 ok
        mock_param_service.return_value.get_parameter_decimal.return_value = Decimal("15")  # limite

        with self.assertRaises(ServiceError) as ctx:
            gestisci_riga(
                1,
                {"articolo_id": "uuid-art-1", "uom_operativa_id": 1, "prezzo_unitario": "40.00"},
                auth_user_id=42,
            )
        self.assertEqual(ctx.exception.code, "E_PREV_SCONTO_ECCESSIVO")
        # Fase 5.B2: errore L2 retryable=True (utente puo' ritentare con
        # flag richiesta_approvazione=true per attivare workflow L3).
        self.assertTrue(ctx.exception.retryable)
        self.mock_repo.create_riga.assert_not_called()

    # Scopo: L2 — maggiorazione oltre il limite blocca con
    #        E_PREV_MAGGIORAZIONE_ECCESSIVA. Resolver 50, manuale 55 = +10%,
    #        limite 5% -> bloccato.
    @patch("apps.vendite.services.preventivi_service.ParameterService")
    @patch("apps.vendite.services.preventivi_service.get_user_model")
    @patch("apps.vendite.services.preventivi_service.PermissionResolver")
    @patch("apps.vendite.services.preventivi_service.suggerisci_prezzo_riga")
    def test_gestisci_riga_L2_maggiorazione_oltre_limite_bloccato(
        self, mock_suggerisci, mock_perm, mock_user_model, mock_param_service
    ):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = self._testata_completa()
        mock_suggerisci.return_value = {
            "prezzo_finale": "50.00", "origine": "CATEGORIA",
            "listino_id": 100, "contratto_id": None, "promo_id": None,
            "tipo_variazione_applicata": None,
            "valore_variazione_applicata": None,
        }
        mock_user = MagicMock()
        mock_user.is_superuser = False
        mock_user_model.return_value.objects.get.return_value = mock_user
        mock_perm.check_azione.return_value = True  # L1 ok
        # Maggiorazione: limite 5% per il secondo parametro.
        mock_param_service.return_value.get_parameter_decimal.return_value = Decimal("5")

        with self.assertRaises(ServiceError) as ctx:
            gestisci_riga(
                1,
                {"articolo_id": "uuid-art-1", "uom_operativa_id": 1, "prezzo_unitario": "55.00"},
                auth_user_id=42,
            )
        self.assertEqual(ctx.exception.code, "E_PREV_MAGGIORAZIONE_ECCESSIVA")
        # Fase 5.B2: errore L2 retryable=True (vedi commento test sconto).
        self.assertTrue(ctx.exception.retryable)
        self.mock_repo.create_riga.assert_not_called()

    # Scopo: L2 — superuser salta sia L1 che L2 anche con limiti a 0.
    @patch("apps.vendite.services.preventivi_service.ParameterService")
    @patch("apps.vendite.services.preventivi_service.get_user_model")
    @patch("apps.vendite.services.preventivi_service.suggerisci_prezzo_riga")
    def test_gestisci_riga_L2_superuser_bypass(
        self, mock_suggerisci, mock_user_model, mock_param_service
    ):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = self._testata_completa()
        self.mock_repo.create_riga.return_value = {"id": 31}
        mock_suggerisci.return_value = {
            "prezzo_finale": "50.00", "origine": "CATEGORIA",
            "listino_id": 100, "contratto_id": None, "promo_id": None,
            "tipo_variazione_applicata": None,
            "valore_variazione_applicata": None,
        }
        mock_user = MagicMock()
        mock_user.is_superuser = True  # bypass L1 e L2
        mock_user_model.return_value.objects.get.return_value = mock_user

        gestisci_riga(
            1,
            {"articolo_id": "uuid-art-1", "uom_operativa_id": 1, "prezzo_unitario": "30.00"},
            auth_user_id=99,
        )

        # ParameterService MAI chiamato (bypass L2 avviene prima).
        mock_param_service.return_value.get_parameter_decimal.assert_not_called()
        call = self.mock_repo.create_riga.call_args.kwargs
        self.assertEqual(str(call["prezzo_unitario"]), "30.00")

    # ── Sprint E: hook L3 richiesta_approvazione ──

    # Scopo: L3 — flag richiesta_approvazione=True + violazione L2 -> NON
    #        solleva, crea pratica via service e salva riga PENDING con FK
    #        pratica. Verifica che create_riga riceva i nuovi campi corretti.
    @patch("apps.vendite.services.approvazioni_prezzo_service.link_riga_a_pratica")
    @patch("apps.vendite.services.preventivi_service.ParameterService")
    @patch("apps.vendite.services.preventivi_service.get_user_model")
    @patch("apps.vendite.services.preventivi_service.PermissionResolver")
    @patch("apps.vendite.services.preventivi_service.suggerisci_prezzo_riga")
    @patch("apps.vendite.services.approvazioni_prezzo_service.crea_richiesta_approvazione")
    def test_gestisci_riga_L3_violazione_con_richiesta_crea_pratica_pending(
        self, mock_crea_pratica, mock_suggerisci, mock_perm, mock_user_model,
        mock_param_service, mock_link_riga,
    ):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = self._testata_completa()
        self.mock_repo.create_riga.return_value = {"id": 999}
        mock_suggerisci.return_value = {
            "prezzo_finale": "50.00", "origine": "CATEGORIA",
            "listino_id": 100, "contratto_id": None, "promo_id": None,
            "tipo_variazione_applicata": None,
            "valore_variazione_applicata": None,
        }
        mock_user = MagicMock()
        mock_user.is_superuser = False
        mock_user_model.return_value.objects.get.return_value = mock_user
        mock_perm.check_azione.return_value = True  # L1 ok
        mock_param_service.return_value.get_parameter_decimal.return_value = Decimal("15")
        mock_crea_pratica.return_value = 7777  # pratica_id ritornato dal service

        result = gestisci_riga(
            1,
            {
                "articolo_id": "uuid-art-1",
                "uom_operativa_id": 1,
                "prezzo_unitario": "40.00",  # -20% sconto, fuori limite 15%
                "richiesta_approvazione": True,
            },
            auth_user_id=42,
        )

        self.assertEqual(result["id"], 999)
        mock_crea_pratica.assert_called_once()
        crea_kwargs = mock_crea_pratica.call_args.kwargs
        self.assertEqual(crea_kwargs["preventivo_id"], 1)
        self.assertEqual(crea_kwargs["articolo_id"], "uuid-art-1")
        self.assertEqual(crea_kwargs["prezzo_resolver"], Decimal("50.00"))
        self.assertEqual(crea_kwargs["prezzo_manuale"], Decimal("40.00"))
        self.assertEqual(crea_kwargs["violazione"]["tipo_violazione"], "SCONTO")

        call = self.mock_repo.create_riga.call_args.kwargs
        self.assertEqual(call["stato_approvazione_prezzo"], "PENDING")
        self.assertEqual(call["pratica_approvazione_prezzo_id"], 7777)

    # Scopo: L3 — flag richiesta_approvazione=False (default): violazione L2
    #        solleva normalmente, NESSUNA pratica creata.
    @patch("apps.vendite.services.preventivi_service.ParameterService")
    @patch("apps.vendite.services.preventivi_service.get_user_model")
    @patch("apps.vendite.services.preventivi_service.PermissionResolver")
    @patch("apps.vendite.services.preventivi_service.suggerisci_prezzo_riga")
    @patch("apps.vendite.services.approvazioni_prezzo_service.crea_richiesta_approvazione")
    def test_gestisci_riga_L3_default_no_pratica_solo_errore_l2(
        self, mock_crea_pratica, mock_suggerisci, mock_perm, mock_user_model, mock_param_service
    ):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = self._testata_completa()
        mock_suggerisci.return_value = {
            "prezzo_finale": "50.00", "origine": "CATEGORIA",
            "listino_id": 100, "contratto_id": None, "promo_id": None,
            "tipo_variazione_applicata": None,
            "valore_variazione_applicata": None,
        }
        mock_user = MagicMock()
        mock_user.is_superuser = False
        mock_user_model.return_value.objects.get.return_value = mock_user
        mock_perm.check_azione.return_value = True
        mock_param_service.return_value.get_parameter_decimal.return_value = Decimal("15")

        with self.assertRaises(ServiceError) as ctx:
            gestisci_riga(
                1,
                {
                    "articolo_id": "uuid-art-1",
                    "uom_operativa_id": 1,
                    "prezzo_unitario": "40.00",
                    # Niente richiesta_approvazione (default False)
                },
                auth_user_id=42,
            )

        self.assertEqual(ctx.exception.code, "E_PREV_SCONTO_ECCESSIVO")
        mock_crea_pratica.assert_not_called()
        self.mock_repo.create_riga.assert_not_called()

    # Scopo: L3 — sotto limite L2 anche con richiesta_approvazione=True:
    #        pratica NON creata (violazione assente), riga normale (no PENDING).
    @patch("apps.vendite.services.preventivi_service.ParameterService")
    @patch("apps.vendite.services.preventivi_service.get_user_model")
    @patch("apps.vendite.services.preventivi_service.PermissionResolver")
    @patch("apps.vendite.services.preventivi_service.suggerisci_prezzo_riga")
    @patch("apps.vendite.services.approvazioni_prezzo_service.crea_richiesta_approvazione")
    def test_gestisci_riga_L3_sotto_limite_no_pratica(
        self, mock_crea_pratica, mock_suggerisci, mock_perm, mock_user_model, mock_param_service
    ):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = self._testata_completa()
        self.mock_repo.create_riga.return_value = {"id": 100}
        mock_suggerisci.return_value = {
            "prezzo_finale": "50.00", "origine": "CATEGORIA",
            "listino_id": 100, "contratto_id": None, "promo_id": None,
            "tipo_variazione_applicata": None,
            "valore_variazione_applicata": None,
        }
        mock_user = MagicMock()
        mock_user.is_superuser = False
        mock_user_model.return_value.objects.get.return_value = mock_user
        mock_perm.check_azione.return_value = True
        mock_param_service.return_value.get_parameter_decimal.return_value = Decimal("20")

        gestisci_riga(
            1,
            {
                "articolo_id": "uuid-art-1",
                "uom_operativa_id": 1,
                "prezzo_unitario": "45.00",  # -10%, sotto limite 20%
                "richiesta_approvazione": True,
            },
            auth_user_id=42,
        )

        mock_crea_pratica.assert_not_called()
        call = self.mock_repo.create_riga.call_args.kwargs
        self.assertIsNone(call["stato_approvazione_prezzo"])
        self.assertIsNone(call["pratica_approvazione_prezzo_id"])

    # Scopo: L3 — aggiorna_riga supporta lo stesso flag richiesta_approvazione.
    #        Modifica prezzo oltre L2 con flag -> crea pratica + UPDATE riga
    #        con stato_approvazione_prezzo=PENDING.
    @patch("apps.vendite.services.approvazioni_prezzo_service.link_riga_a_pratica")
    @patch("apps.vendite.services.preventivi_service.ParameterService")
    @patch("apps.vendite.services.preventivi_service.get_user_model")
    @patch("apps.vendite.services.preventivi_service.PermissionResolver")
    @patch("apps.vendite.services.preventivi_service.suggerisci_prezzo_riga")
    @patch("apps.vendite.services.approvazioni_prezzo_service.crea_richiesta_approvazione")
    def test_aggiorna_riga_L3_violazione_con_richiesta_crea_pratica(
        self, mock_crea_pratica, mock_suggerisci, mock_perm, mock_user_model,
        mock_param_service, mock_link_riga,
    ):
        from apps.vendite.services.preventivi_service import aggiorna_riga

        self.mock_repo.get_preventivo.return_value = self._testata_completa()
        self.mock_repo.list_righe.return_value = [
            {"id": 50, "articolo_id": "uuid-art-1", "uom_operativa_id": 1, "meta": {}}
        ]
        self.mock_repo.update_riga.return_value = True
        mock_suggerisci.return_value = {
            "prezzo_finale": "50.00", "origine": "CATEGORIA",
            "listino_id": 100, "contratto_id": None, "promo_id": None,
            "tipo_variazione_applicata": None,
            "valore_variazione_applicata": None,
        }
        mock_user = MagicMock()
        mock_user.is_superuser = False
        mock_user_model.return_value.objects.get.return_value = mock_user
        mock_perm.check_azione.return_value = True
        mock_param_service.return_value.get_parameter_decimal.return_value = Decimal("15")
        mock_crea_pratica.return_value = 8888

        aggiorna_riga(
            1, 50,
            {"prezzo_unitario": "40.00", "richiesta_approvazione": True},
            auth_user_id=42,
        )

        mock_crea_pratica.assert_called_once()
        call = self.mock_repo.update_riga.call_args
        # update_riga(riga_id, **kwargs) — verifica kwargs.
        self.assertEqual(call.kwargs["stato_approvazione_prezzo"], "PENDING")
        self.assertEqual(call.kwargs["pratica_approvazione_prezzo_id"], 8888)
