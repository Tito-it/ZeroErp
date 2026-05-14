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
5b) test_gestisci_riga_padre_composito_prezzo_default_zero — composito senza prezzo → 0 placeholder
5c) test_gestisci_riga_non_composito_senza_prezzo_solleva — non composito + prezzo None → E_PREV_VALIDAZIONE
6) test_gestisci_riga_stato_non_modificabile — guard riga su stato EMESSO
7) test_gestisci_riga_articolo_mancante — validazione articolo_id obbligatorio
8) test_elimina_riga_ok — soft delete riga
9) test_elimina_riga_not_found — riga inesistente
10) test_push_a_commessa_ok — push preventivo ACCETTATO con righe eleggibili + transizione EVASO
10b) test_push_a_commessa_propaga_fatturazione_immediata — flag testata nel payload
10c) test_push_a_commessa_parziale_propaga_e_non_evade — all-or-nothing: ServiceError, niente transizione
10d) test_push_a_commessa_transizione_db_error_logged_no_raise — fallimento transizione e' soft (warning)
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
26) test_list_riepilogo_iva_delega_a_repo — facade lettura riepilogo IVA aggregato
27) test_list_preventivi_default_solo_revisione_attiva_true — filtro lista default
28) test_list_preventivi_solo_revisione_attiva_false — toggle "Mostra storico"
29) test_gestisci_riga_deriva_qta_operativa_da_factor — qta_op = quantita*factor
30) test_gestisci_riga_deriva_qta_operativa_factor_default_1 — fallback factor=1
31) test_repository_list_righe_filtra_solo_attive — righe soft-delete escluse
32) test_gestisci_riga_init_componenti_chiamato — post-create_riga la fn init e' invocata
33) test_gestisci_riga_init_componenti_skip_admin_globale — admin globale (no emittente) salta init
33b) test_gestisci_riga_init_componenti_usa_emittente_preventivo — admin + emittente esplicito sul preventivo OK
33c) test_gestisci_riga_init_componenti_overrides_passati — form atomic: componenti_overrides nel payload → init
33d) test_gestisci_riga_componenti_overrides_unauthorized — gating L1 senza override → 403 E_PREV_OVERRIDE_NON_AUTORIZZATO
33e) test_gestisci_riga_init_componenti_attivazioni_passate — modello unificato: componenti_attivazioni propagato a repo.init
33f) test_gestisci_riga_init_componenti_bom_vuota_propaga — repo solleva E_DOC_COMPOSITO_BOM_VUOTA → service propaga
33g) test_gestisci_riga_init_componenti_obbligatorio_disattivazione_bloccata — repo solleva E_DOC_COMPONENTE_OBBLIGATORIO → service propaga
33h) test_gestisci_riga_init_componenti_obbligatorio_prezzo_zero — repo solleva E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO → service propaga
34) test_aggiorna_riga_non_tocca_componenti — articolo_id immutabile, componenti stabili
34b) test_aggiorna_riga_rifiuta_componenti_overrides — PATCH con componenti_overrides → 422
34c) test_aggiorna_riga_rifiuta_componenti_attivazioni — PATCH con componenti_attivazioni → 422
35) test_list_componenti_riga_ok — lista componenti riga padre
36) test_list_componenti_riga_not_found — riga padre inesistente
37) test_list_componenti_riga_scope_violation — riga padre di altro preventivo
38) test_update_componente_ok — modifica prezzo componente
39) test_update_componente_not_found — componente inesistente
40) test_update_componente_url_tampering_riga_id — anti-tampering URL riga falsa
41) test_update_componente_scope_violation — componente di altro preventivo
42) test_update_componente_stato_non_modificabile — guard preventivo EMESSO
43) test_delete_componente_ok — soft delete componente
44) test_delete_componente_not_found — componente inesistente
45) test_preview_componenti_riga_ok — happy path preview (form atomic)
46) test_preview_componenti_riga_not_found — preventivo inesistente → 404
47) test_preview_componenti_riga_data_mancante — data NULL → 422
48) test_preview_componenti_riga_utility_mancante — utility NULL → 422 (no fallback 0)
49) test_preview_componenti_riga_emittente_non_risolvibile — admin globale + no emittente → 422
50) test_preview_componenti_riga_usa_emittente_preventivo — precedenza emittente preventivo

TestNormalizeComponentiOverrides:
- test_none_ritorna_none, test_dict_vuoto_ritorna_none
- test_decimal_string_normalizzato, test_numero_python_normalizzato,
  test_decimal_native_normalizzato
- test_valore_none_solleva, test_valore_stringa_vuota_solleva,
  test_valore_non_numerico_solleva, test_overrides_non_dict_solleva

TestNormalizeComponentiAttivazioni:
- test_none_ritorna_none, test_dict_vuoto_ritorna_none
- test_dict_bool_normalizzato
- test_valore_non_bool_solleva, test_attivazioni_non_dict_solleva
"""

import unittest
from decimal import Decimal
from types import SimpleNamespace
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

        # Mock BB anagrafiche usati da crea_preventivo per validator dominio
        # (post brief DB rev2: derivazione istanza dal BA + pre-check coerenza
        # utility/istanza). Default: coerenza ok, BA → istanza id=100.
        self.ba_repo_patcher = patch(
            "apps.vendite.services.preventivi_service.BillingAccountRepository"
        )
        self.MockBaRepoClass = self.ba_repo_patcher.start()
        self.mock_ba_repo = MagicMock()
        self.MockBaRepoClass.return_value = self.mock_ba_repo
        self.mock_ba_repo.get_istanza_utility_id.return_value = 100

        self.iu_repo_patcher = patch(
            "apps.vendite.services.preventivi_service.IstanzeUtilityRepository"
        )
        self.MockIuRepoClass = self.iu_repo_patcher.start()
        self.mock_iu_repo = MagicMock()
        self.MockIuRepoClass.return_value = self.mock_iu_repo
        self.mock_iu_repo.check_utility_istanza_coerenza.return_value = True

        # Default: lookup config
        self.mock_repo.get_stato_bozza_id.return_value = 1
        self.mock_repo.get_sorgente_tipo_preventivo_id.return_value = 10
        # Default: capabilities vuote per i test che non si interessano del blob
        # (Fase 1 refactor frontend vendite: get_preventivo invoca la fn DB).
        self.mock_repo.get_capabilities.return_value = {}

        # Mock transaction.atomic → no-op context manager (test mock-only,
        # no DB connection). Necessario per cambia_stato accettazione che
        # avvolge update_preventivo + cambia_stato in transaction.atomic.
        self.atomic_patcher = patch(
            "apps.vendite.services.preventivi_service.transaction.atomic"
        )
        mock_atomic = self.atomic_patcher.start()
        mock_atomic.return_value.__enter__ = MagicMock(return_value=None)
        mock_atomic.return_value.__exit__ = MagicMock(return_value=False)

        # Mock degli helper che fanno user_model.objects.get(pk=...): senza
        # DB reale (test unit) la query fallirebbe. I test che vogliono
        # testare la logica emittente specifica possono ri-patcharli
        # localmente con side_effect/return_value.
        self.emittente_patcher = patch(
            "apps.vendite.services.preventivi_service._resolve_emittente_sr_id_or_raise",
            return_value=100,
        )
        self.emittente_patcher.start()
        # Variante safe chiamata da gestisci_riga per init componenti CASO A
        # (mockata a 100; i test che testano admin globale possono override
        # localmente a None).
        self.emittente_safe_patcher = patch(
            "apps.vendite.services._componenti_service_helpers.resolve_emittente_sr_id_safe",
            return_value=100,
        )
        self.emittente_safe_patcher.start()
        # _validate_componenti_overrides_authorization chiama
        # PermissionResolver.check_azione (SQL diretto con user.id) quando il
        # payload contiene componenti_overrides. Per i test unit senza DB,
        # mocco il validator a no-op per default. Test specifici che vogliono
        # esercitare il gating L1 ri-patchano localmente.
        self.gating_overrides_patcher = patch(
            "apps.vendite.services.preventivi_service._validate_componenti_overrides_authorization",
            return_value=None,
        )
        self.gating_overrides_patcher.start()

    def tearDown(self):
        self.repo_patcher.stop()
        self.ba_repo_patcher.stop()
        self.iu_repo_patcher.stop()
        self.atomic_patcher.stop()
        self.emittente_patcher.stop()
        self.emittente_safe_patcher.stop()
        self.gating_overrides_patcher.stop()

    # ── Creazione ──

    # Scopo: Verifica creazione preventivo con campi minimi.
    def test_crea_preventivo_ok(self):
        from apps.vendite.services.preventivi_service import crea_preventivo

        self.mock_repo.create_preventivo.return_value = {
            "id": 1, "uid": "abc-123", "numero": "P-0001",
        }
        result = crea_preventivo({
            "utility_id": 5, "istanza_utility_id": 100,
        })
        self.assertEqual(result["id"], 1)
        self.mock_repo.create_preventivo.assert_called_once()
        # Pre-check coerenza eseguito (defense-in-depth lato service).
        self.mock_iu_repo.check_utility_istanza_coerenza.assert_called_once_with(
            100, 5,
        )

    # Scopo: Verifica errore se utility_id mancante.
    def test_crea_preventivo_utility_mancante(self):
        from apps.vendite.services.preventivi_service import crea_preventivo

        with self.assertRaises(ServiceError) as ctx:
            crea_preventivo({})
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")

    # Scopo: Verifica errore se istanza_utility_id mancante e nessun BA da cui
    # derivarla (regola di dominio post brief DB rev2: istanza obbligatoria).
    def test_crea_preventivo_istanza_mancante(self):
        from apps.vendite.services.preventivi_service import crea_preventivo

        with self.assertRaises(ServiceError) as ctx:
            crea_preventivo({"utility_id": 5})
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        self.assertIn("istanza_utility_id", ctx.exception.message)
        # Repo INSERT non viene chiamato.
        self.mock_repo.create_preventivo.assert_not_called()

    # Scopo: Quando il payload ha solo BA (no istanza), il service deriva
    # l'istanza dal BA via BillingAccountRepository.get_istanza_utility_id.
    def test_crea_preventivo_istanza_derivata_da_ba(self):
        from apps.vendite.services.preventivi_service import crea_preventivo

        self.mock_ba_repo.get_istanza_utility_id.return_value = 200
        self.mock_repo.create_preventivo.return_value = {
            "id": 1, "uid": "abc-123", "numero": "P-0001",
        }
        crea_preventivo({"utility_id": 5, "billing_account_id": 42})
        self.mock_ba_repo.get_istanza_utility_id.assert_called_once_with(42)
        # L'istanza derivata viene passata sia al check coerenza sia all'INSERT.
        self.mock_iu_repo.check_utility_istanza_coerenza.assert_called_once_with(
            200, 5,
        )
        kwargs = self.mock_repo.create_preventivo.call_args.kwargs
        self.assertEqual(kwargs["istanza_utility_id"], 200)
        self.assertEqual(kwargs["billing_account_id"], 42)

    # Scopo: Pre-check coerenza utility/istanza (defense-in-depth lato service):
    # se la coppia (istanza, utility) non e' dichiarata in BA / IDP / clienti
    # → errore parlante PRIMA del trigger DB.
    def test_crea_preventivo_utility_istanza_incoerente(self):
        from apps.vendite.services.preventivi_service import crea_preventivo

        self.mock_iu_repo.check_utility_istanza_coerenza.return_value = False
        with self.assertRaises(ServiceError) as ctx:
            crea_preventivo({
                "utility_id": 5, "istanza_utility_id": 100,
            })
        self.assertEqual(ctx.exception.code, "E_PREV_UTILITY_ISTANZA_INCOERENTE")
        self.mock_repo.create_preventivo.assert_not_called()

    # Scopo: emittente_fiscale_id esplicito (caso admin globale) viene passato
    # al repository senza alterazioni. Il trigger DB BEFORE INSERT lo lascia
    # invariato (skip auto-fill quando NEW.emittente_fiscale_id IS NOT NULL).
    def test_crea_preventivo_emittente_esplicito_admin_globale(self):
        from apps.vendite.services.preventivi_service import crea_preventivo

        self.mock_repo.create_preventivo.return_value = {
            "id": 1, "uid": "abc-123", "numero": "P-0001",
        }
        crea_preventivo({
            "utility_id": 5, "istanza_utility_id": 100,
            "emittente_fiscale_id": 77,
        })
        kwargs = self.mock_repo.create_preventivo.call_args.kwargs
        self.assertEqual(kwargs["emittente_fiscale_id"], 77)

    # ── Eliminazione bozza (abbandono drawer) ──

    # Scopo: hard-delete preventivo BOZZA senza righe ne' pratiche.
    def test_elimina_preventivo_bozza_orfana_ok(self):
        from apps.vendite.services.preventivi_service import elimina_preventivo

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT",
        }
        self.mock_repo.list_righe.return_value = []
        self.mock_repo.list_pratiche.return_value = []
        self.mock_repo.delete_preventivo.return_value = True

        result = elimina_preventivo(1)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["preventivo_id"], 1)
        self.mock_repo.delete_preventivo.assert_called_once_with(1)

    # Scopo: preventivo inesistente → E_PREV_NOT_FOUND, no DELETE.
    def test_elimina_preventivo_not_found(self):
        from apps.vendite.services.preventivi_service import elimina_preventivo

        self.mock_repo.get_preventivo.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            elimina_preventivo(999)
        self.assertEqual(ctx.exception.code, "E_PREV_NOT_FOUND")
        self.mock_repo.delete_preventivo.assert_not_called()

    # Scopo: stato non DRAFT → E_PREV_STATO_NON_MODIFICABILE.
    def test_elimina_preventivo_stato_non_bozza_bloccato(self):
        from apps.vendite.services.preventivi_service import elimina_preventivo

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "ACCETTATO",
        }
        with self.assertRaises(ServiceError) as ctx:
            elimina_preventivo(1)
        self.assertEqual(ctx.exception.code, "E_PREV_STATO_NON_MODIFICABILE")
        self.mock_repo.delete_preventivo.assert_not_called()

    # Scopo: BOZZA con almeno una riga → E_PREV_STATO_NON_MODIFICABILE.
    def test_elimina_preventivo_con_righe_bloccato(self):
        from apps.vendite.services.preventivi_service import elimina_preventivo

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT",
        }
        self.mock_repo.list_righe.return_value = [{"id": 10}]
        with self.assertRaises(ServiceError) as ctx:
            elimina_preventivo(1)
        self.assertEqual(ctx.exception.code, "E_PREV_STATO_NON_MODIFICABILE")
        self.mock_repo.delete_preventivo.assert_not_called()

    # ── Cambio stato → ACCETTATO (modalita' fatturazione) ──

    # Scopo: ACCETTATO con immediata=True forza competenza al primo del mese.
    def test_cambia_stato_accettato_immediata_force_competenza(self):
        from datetime import date
        from apps.vendite.services.preventivi_service import cambia_stato

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "EMESSO",
        }
        self.mock_repo.cambia_stato.return_value = {"status": "ok"}
        cambia_stato(1, "ACCETTATO", fatturazione_immediata=True,
                     competenza_mese=date(2026, 7, 15))  # ignorata
        # update_preventivo deve essere chiamato con immediata=True e
        # competenza=primo del mese corrente (oggi.replace(day=1)).
        kwargs = self.mock_repo.update_preventivo.call_args.kwargs
        self.assertTrue(kwargs["fatturazione_immediata"])
        expected = date.today().replace(day=1)
        self.assertEqual(kwargs["competenza_mese"], expected)
        self.mock_repo.cambia_stato.assert_called_once_with(
            1, "ACCETTATO", "django_api",
        )

    # Scopo: ACCETTATO con immediata=False richiede competenza esplicita.
    def test_cambia_stato_accettato_non_immediata_con_competenza_ok(self):
        from datetime import date
        from apps.vendite.services.preventivi_service import cambia_stato

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "EMESSO",
        }
        self.mock_repo.cambia_stato.return_value = {"status": "ok"}
        cambia_stato(1, "ACCETTATO", fatturazione_immediata=False,
                     competenza_mese=date(2026, 8, 1))
        kwargs = self.mock_repo.update_preventivo.call_args.kwargs
        self.assertFalse(kwargs["fatturazione_immediata"])
        self.assertEqual(kwargs["competenza_mese"], date(2026, 8, 1))

    # Scopo: ACCETTATO senza fatturazione_immediata → E_PREV_VALIDAZIONE.
    def test_cambia_stato_accettato_senza_immediata_bloccato(self):
        from apps.vendite.services.preventivi_service import cambia_stato

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "EMESSO",
        }
        with self.assertRaises(ServiceError) as ctx:
            cambia_stato(1, "ACCETTATO")
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        self.mock_repo.update_preventivo.assert_not_called()
        self.mock_repo.cambia_stato.assert_not_called()

    # Scopo: ACCETTATO con immediata=False senza competenza → E_PREV_VALIDAZIONE.
    def test_cambia_stato_accettato_non_immediata_senza_competenza_bloccato(self):
        from apps.vendite.services.preventivi_service import cambia_stato

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "EMESSO",
        }
        with self.assertRaises(ServiceError) as ctx:
            cambia_stato(1, "ACCETTATO", fatturazione_immediata=False,
                         competenza_mese=None)
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        self.mock_repo.update_preventivo.assert_not_called()

    # Scopo: transizioni diverse da ACCETTATO ignorano i 2 parametri (no
    # update testata, solo cambio stato). EMESSO triggera il hook PDF
    # atomico: lo isoliamo qui patchando _genera_pdf_emissione (i test
    # dedicati al hook stanno piu' sotto).
    def test_cambia_stato_emesso_ignora_immediata_e_competenza(self):
        from datetime import date
        from apps.vendite.services.preventivi_service import cambia_stato

        self.mock_repo.cambia_stato.return_value = {"status": "ok"}
        with patch(
            "apps.vendite.services.preventivi_service._genera_pdf_emissione"
        ) as mock_pdf:
            cambia_stato(1, "EMESSO", fatturazione_immediata=True,
                         competenza_mese=date(2026, 9, 1))
        # No get_preventivo sul gate, no update_preventivo.
        self.mock_repo.update_preventivo.assert_not_called()
        self.mock_repo.cambia_stato.assert_called_once_with(
            1, "EMESSO", "django_api",
        )
        # Hook PDF atomico chiamato post-cambio-stato.
        mock_pdf.assert_called_once()

    # Scopo: La transizione *->EMESSO genera atomicamente il PDF v1 dentro
    # la stessa transazione del cambio stato. Verifichiamo che il service
    # invochi DocumentGenerationService.genera_documento con i parametri
    # ricavati dal preventivo (emittente, sorgente PREVENTIVO, id, uid).
    def test_cambia_stato_emesso_genera_pdf_atomico(self):
        from apps.vendite.services.preventivi_service import cambia_stato

        self.mock_repo.cambia_stato.return_value = {"status": "ok"}
        self.mock_repo.get_preventivo.return_value = {
            "id": 42, "uid": "uid-42",
            "emittente_fiscale_id": 7,
        }

        with patch(
            "apps.vendite.services.preventivi_service.DocumentiRepository"
        ) as MockDocRepo, patch(
            "apps.vendite.services.preventivi_service.DocumentGenerationService"
        ) as MockGen:
            mock_doc_repo = MagicMock()
            MockDocRepo.return_value = mock_doc_repo
            mock_doc_repo.get_sorgente_tipo_id_by_codice.return_value = {
                "id": 99, "attivo": True,
            }
            mock_gen = MagicMock()
            MockGen.return_value = mock_gen

            user = MagicMock()
            cambia_stato(42, "EMESSO", user=user)

            # Cambio stato eseguito.
            self.mock_repo.cambia_stato.assert_called_once_with(
                42, "EMESSO", "django_api",
            )
            # genera_documento chiamato con i parametri attesi.
            mock_gen.genera_documento.assert_called_once_with(
                user,
                emittente_fiscale_id=7,
                sorgente_tipo_id=99,
                sorgente_id=42,
                sorgente_uid="uid-42",
            )

    # Scopo: Render fail durante l'emissione propaga l'eccezione del
    # DocumentGenerationService al chiamante. La transaction.atomic
    # esterna garantisce rollback atomico (testato a livello unit
    # solo per il fatto che l'eccezione passi: l'effetto rollback e'
    # garantito dal contract di transaction.atomic).
    def test_cambia_stato_emesso_render_fail_propaga(self):
        from apps.core.services.error_manager import ServiceError
        from apps.vendite.services.preventivi_service import cambia_stato

        self.mock_repo.cambia_stato.return_value = {"status": "ok"}
        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "uid": "uid-1", "emittente_fiscale_id": 7,
        }

        with patch(
            "apps.vendite.services.preventivi_service.DocumentiRepository"
        ) as MockDocRepo, patch(
            "apps.vendite.services.preventivi_service.DocumentGenerationService"
        ) as MockGen:
            mock_doc_repo = MagicMock()
            MockDocRepo.return_value = mock_doc_repo
            mock_doc_repo.get_sorgente_tipo_id_by_codice.return_value = {
                "id": 99, "attivo": True,
            }
            mock_gen = MagicMock()
            MockGen.return_value = mock_gen
            mock_gen.genera_documento.side_effect = ServiceError(
                code="E_DOCUMENTI_RENDER_FAILED",
                message="boom",
            )

            with self.assertRaises(ServiceError) as ctx:
                cambia_stato(1, "EMESSO", user=MagicMock())
            self.assertEqual(ctx.exception.code, "E_DOCUMENTI_RENDER_FAILED")

    # ── Eliminazione bozza (abbandono drawer) ──

    # Scopo: BOZZA senza righe ma con pratica collegata → bloccato.
    def test_elimina_preventivo_con_pratiche_bloccato(self):
        from apps.vendite.services.preventivi_service import elimina_preventivo

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT",
        }
        self.mock_repo.list_righe.return_value = []
        self.mock_repo.list_pratiche.return_value = [{"id": 50}]
        with self.assertRaises(ServiceError) as ctx:
            elimina_preventivo(1)
        self.assertEqual(ctx.exception.code, "E_PREV_STATO_NON_MODIFICABILE")
        self.mock_repo.delete_preventivo.assert_not_called()

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

    # Scopo: padre composito con payload senza prezzo_unitario → BE usa
    # placeholder 0 (sara' sovrascritto dal trigger DB _z90_ricalcola_padre
    # post fn_preventivo_riga_componenti_init). Verifica che repo.create_riga
    # riceva prezzo_unitario != None per non violare il NOT NULL DB.
    def test_gestisci_riga_padre_composito_prezzo_default_zero(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
        }
        self.mock_repo.is_articolo_composito.return_value = True
        self.mock_repo.create_riga.return_value = {"id": 10}

        gestisci_riga(1, {"articolo_id": "uuid-art-composito"})

        self.mock_repo.create_riga.assert_called_once()
        kwargs = self.mock_repo.create_riga.call_args.kwargs
        # Decimal(0) come placeholder, NON None
        self.assertIsNotNone(kwargs["prezzo_unitario"])
        self.assertEqual(Decimal(kwargs["prezzo_unitario"]), Decimal("0"))

    # Scopo: articolo NON composito + payload senza prezzo_unitario + resolver
    # che non valorizza → E_PREV_VALIDAZIONE parlante (defense-in-depth: FE
    # `canSave` blocca prima, ma il BE deve dare errore comprensibile invece
    # di lasciare passare None → E_DATABASE su NOT NULL violation).
    def test_gestisci_riga_non_composito_senza_prezzo_solleva(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            # missing_resolver_ctx: no BA/utility/data → resolver skip,
            # prezzo_finale=None propagato.
        }
        self.mock_repo.is_articolo_composito.return_value = False

        with self.assertRaises(ServiceError) as ctx:
            gestisci_riga(1, {"articolo_id": "uuid-art-semplice"})
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        self.mock_repo.create_riga.assert_not_called()

    # Scopo: Verifica errore se articolo_id mancante.
    def test_gestisci_riga_articolo_mancante(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
        }
        with self.assertRaises(ServiceError) as ctx:
            gestisci_riga(1, {"quantita": "10"})
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")

    # Scopo: Verifica che prezzo negativo venga bloccato lato BE con messaggio
    #        parlante (E_PREV_VALIDAZIONE) invece di lasciare il CHECK DB
    #        (chk_prevrighe_quantita_prezzo) sollevare un errore generico.
    def test_gestisci_riga_prezzo_negativo_ko(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
        }
        with self.assertRaises(ServiceError) as ctx:
            gestisci_riga(1, {"articolo_id": "uuid-art-1", "prezzo_unitario": "-5.00"})
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        # Repo non deve essere chiamato: validazione blocca PRIMA dell'INSERT.
        self.mock_repo.create_riga.assert_not_called()

    # Scopo: Verifica che quantita zero/negativa venga bloccata lato BE.
    def test_gestisci_riga_quantita_non_positiva_ko(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
        }
        with self.assertRaises(ServiceError) as ctx:
            gestisci_riga(1, {"articolo_id": "uuid-art-1", "quantita": "0"})
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        self.mock_repo.create_riga.assert_not_called()

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

    # ── Componenti BoM CASO A ──

    # Scopo: post-create riga, init_componenti_riga viene chiamato col
    # set di parametri attesi (emittente_sr_id dal helper safe, data dalla
    # testata). Refactor componenti 2026-05-11.
    def test_gestisci_riga_init_componenti_chiamato(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": 5,
        }
        self.mock_repo.create_riga.return_value = {"id": 42}
        gestisci_riga(
            1, {"articolo_id": "uuid-art-1", "uom_operativa_id": 1},
            auth_user_id=100,
        )
        self.mock_repo.init_componenti_riga.assert_called_once()
        kwargs = self.mock_repo.init_componenti_riga.call_args.kwargs
        self.assertEqual(kwargs["riga_id"], 42)
        self.assertEqual(kwargs["emittente_soggetto_ruolo_id"], 100)

    # Scopo: admin globale (helper safe ritorna None) e preventivo SENZA
    # emittente_fiscale_id esplicito NON triggera init. Caso edge: skip
    # silenzioso perche' non sappiamo come pricing.
    def test_gestisci_riga_init_componenti_skip_admin_globale(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": 5,
            "emittente_fiscale_id": None,
        }
        self.mock_repo.create_riga.return_value = {"id": 42}
        # Sovrascrivi mock setUp: emittente safe = None (admin globale)
        with patch(
            "apps.vendite.services._componenti_service_helpers.resolve_emittente_sr_id_safe",
            return_value=None,
        ):
            gestisci_riga(
                1, {"articolo_id": "uuid-art-1", "uom_operativa_id": 1},
                auth_user_id=100,
            )
        self.mock_repo.init_componenti_riga.assert_not_called()

    # Scopo: form atomic 2026-05-12 — il payload puo' includere
    # `componenti_overrides` (mappa componente_id → prezzo) raccolti dal
    # drawer FE. Il service li passa alla fn DB init, che applica gli
    # override invece del resolver. Gating L1 mockato (default no-op nei
    # test unit), il caso "unauthorized" e' coperto dal test apposito sotto.
    def test_gestisci_riga_init_componenti_overrides_passati(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": 5,
        }
        self.mock_repo.create_riga.return_value = {"id": 42}
        overrides = {"019d57c1-b2b2-7d3a-9ebb-421addc5f393": "75.00"}
        gestisci_riga(
            1, {
                "articolo_id": "uuid-art-1", "uom_operativa_id": 1,
                "componenti_overrides": overrides,
            },
            auth_user_id=100,
        )
        self.mock_repo.init_componenti_riga.assert_called_once()
        kwargs = self.mock_repo.init_componenti_riga.call_args.kwargs
        self.assertEqual(kwargs["componenti_overrides"], overrides)

    # Scopo: gating L1 — payload con componenti_overrides ma operatore
    # senza `prezzo_override_manuale` solleva E_PREV_OVERRIDE_NON_AUTORIZZATO
    # (ServiceError 403) PRIMA di qualsiasi tocco DB.
    def test_gestisci_riga_componenti_overrides_unauthorized(self):
        from apps.vendite.services.preventivi_service import gestisci_riga
        from apps.core.services.error_manager import ServiceError

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": 5,
        }
        # Sovrascrivi mock setUp: rimetti il vero validator + mock check_azione
        # a False (operatore senza azione prezzo_override_manuale).
        self.gating_overrides_patcher.stop()
        try:
            with patch(
                "apps.vendite.services.preventivi_service.PermissionResolver.check_azione",
                return_value=False,
            ), patch(
                "apps.vendite.services.preventivi_service.get_user_model",
            ) as mock_user_model:
                mock_user_model.return_value.objects.get.return_value = MagicMock()
                with self.assertRaises(ServiceError) as ctx:
                    gestisci_riga(
                        1, {
                            "articolo_id": "uuid-art-1", "uom_operativa_id": 1,
                            "componenti_overrides": {"uuid-c1": "10.00"},
                        },
                        auth_user_id=100,
                    )
                self.assertEqual(ctx.exception.code, "E_PREV_OVERRIDE_NON_AUTORIZZATO")
        finally:
            # Ripristina patcher per i test successivi (il setUp sara' rieseguito
            # ma per non rompere questo test specifico ricominciamo il patch).
            self.gating_overrides_patcher.start()

    # Scopo: modello unificato 2026-05-13 — il payload puo' includere
    # `componenti_attivazioni` (mappa componente_id → bool) per attivare
    # opzionali (default DB inserisce opzionali con `attivo=FALSE`) o
    # disattivare opzionali in re-init. Il service li propaga al repo;
    # il guard DB blocca tentativi su obbligatori.
    def test_gestisci_riga_init_componenti_attivazioni_passate(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": 5,
        }
        self.mock_repo.create_riga.return_value = {"id": 42}
        attivazioni = {
            "019d57c1-b2b2-7d3a-9ebb-421addc5f393": True,
            "019d57c1-b2b2-7d3a-9ebb-421addc5f394": False,
        }
        gestisci_riga(
            1, {
                "articolo_id": "uuid-art-1", "uom_operativa_id": 1,
                "componenti_attivazioni": attivazioni,
            },
            auth_user_id=100,
        )
        self.mock_repo.init_componenti_riga.assert_called_once()
        kwargs = self.mock_repo.init_componenti_riga.call_args.kwargs
        self.assertEqual(kwargs["componenti_attivazioni"], attivazioni)

    # Scopo: padre composito con BoM scaduta/non configurata alla data:
    # la fn DB solleva `E_DOC_COMPOSITO_BOM_VUOTA` e il service NON deve
    # ingoiare l'errore (no try/except attorno a init_componenti_riga).
    # Verifichiamo via side_effect sul mock repo.
    def test_gestisci_riga_init_componenti_bom_vuota_propaga(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": 5,
        }
        self.mock_repo.create_riga.return_value = {"id": 42}
        self.mock_repo.init_componenti_riga.side_effect = ServiceError(
            code="E_DOC_COMPOSITO_BOM_VUOTA",
            message="BoM vuota",
        )
        with self.assertRaises(ServiceError) as ctx:
            gestisci_riga(
                1, {"articolo_id": "uuid-art-1", "uom_operativa_id": 1},
                auth_user_id=100,
            )
        self.assertEqual(ctx.exception.code, "E_DOC_COMPOSITO_BOM_VUOTA")

    # Scopo: opzionale disattivato tramite componenti_attivazioni e' OK
    # via repo; obbligatorio disattivato fa scattare il trigger DB con
    # E_DOC_COMPONENTE_OBBLIGATORIO che si propaga al service.
    def test_gestisci_riga_init_componenti_obbligatorio_disattivazione_bloccata(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": 5,
        }
        self.mock_repo.create_riga.return_value = {"id": 42}
        self.mock_repo.init_componenti_riga.side_effect = ServiceError(
            code="E_DOC_COMPONENTE_OBBLIGATORIO",
            message="Componente obbligatorio: non disattivabile",
        )
        with self.assertRaises(ServiceError) as ctx:
            gestisci_riga(
                1, {
                    "articolo_id": "uuid-art-1", "uom_operativa_id": 1,
                    "componenti_attivazioni": {"uuid-c1": False},
                },
                auth_user_id=100,
            )
        self.assertEqual(ctx.exception.code, "E_DOC_COMPONENTE_OBBLIGATORIO")

    # Scopo: override prezzo=0 su componente obbligatorio e' bloccato dalla
    # fn DB con E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO; il service deve
    # propagare l'errore (no swallow).
    def test_gestisci_riga_init_componenti_obbligatorio_prezzo_zero(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": 5,
        }
        self.mock_repo.create_riga.return_value = {"id": 42}
        self.mock_repo.init_componenti_riga.side_effect = ServiceError(
            code="E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO",
            message="Componente obbligatorio: prezzo deve essere <> 0",
        )
        with self.assertRaises(ServiceError) as ctx:
            gestisci_riga(
                1, {
                    "articolo_id": "uuid-art-1", "uom_operativa_id": 1,
                    "componenti_overrides": {"uuid-c1": "0.00"},
                },
                auth_user_id=100,
            )
        self.assertEqual(
            ctx.exception.code, "E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO",
        )

    # Scopo: admin globale CON `emittente_fiscale_id` esplicito sul
    # preventivo triggera init usando quell'emittente (precedenza
    # preventivo > operatore). Risolve bug "admin non puo' creare CASO A
    # via API" — refactor componenti rev 2026-05-12.
    def test_gestisci_riga_init_componenti_usa_emittente_preventivo(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": 5,
            "emittente_fiscale_id": 99,  # PK emittente del preventivo
        }
        self.mock_repo.create_riga.return_value = {"id": 42}
        self.mock_repo.get_emittente_sr_id_by_fiscale_id.return_value = 200
        with patch(
            "apps.vendite.services._componenti_service_helpers.resolve_emittente_sr_id_safe",
            return_value=None,  # operatore admin globale, no emittente proprio
        ):
            gestisci_riga(
                1, {"articolo_id": "uuid-art-1", "uom_operativa_id": 1},
                auth_user_id=100,
            )
        self.mock_repo.get_emittente_sr_id_by_fiscale_id.assert_called_once_with(99)
        self.mock_repo.init_componenti_riga.assert_called_once()
        kwargs = self.mock_repo.init_componenti_riga.call_args.kwargs
        self.assertEqual(kwargs["emittente_soggetto_ruolo_id"], 200)

    # Scopo: `aggiorna_riga` NON ammette cambio articolo (whitelist update
    # exclude `articolo_id`). I componenti CASO A iniziali dell'init
    # restano stabili: nessun purge/re-init scatta dal flusso update.
    # Verifica defense-in-depth: anche se il caller passa `articolo_id`
    # nel payload, viene ignorato dalla whitelist e i componenti non
    # vengono toccati.
    def test_aggiorna_riga_non_tocca_componenti(self):
        from apps.vendite.services.preventivi_service import aggiorna_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": 5,
        }
        self.mock_repo.update_riga.return_value = True

        # Payload con articolo_id (ignorato) + descrizione (ammessa)
        aggiorna_riga(
            1, 10,
            {"articolo_id": "uuid-new-art", "descrizione": "nuova"},
            auth_user_id=100,
        )
        self.mock_repo.purge_componenti_riga.assert_not_called()
        self.mock_repo.init_componenti_riga.assert_not_called()

    # Scopo: PATCH riga con `componenti_overrides` o `componenti_attivazioni`
    # nel payload deve fallire rumorosamente (422 E_PREV_VALIDAZIONE) invece
    # di scartare i campi silenziosamente. Modifica componenti via endpoint
    # dedicato `/righe/<riga_id>/componenti/<componente_id>/`.
    def test_aggiorna_riga_rifiuta_componenti_overrides(self):
        from apps.vendite.services.preventivi_service import aggiorna_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": 5,
        }
        with self.assertRaises(ServiceError) as ctx:
            aggiorna_riga(
                1, 10,
                {"componenti_overrides": {"uuid-c1": "10.00"}},
                auth_user_id=100,
            )
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        self.mock_repo.update_riga.assert_not_called()

    def test_aggiorna_riga_rifiuta_componenti_attivazioni(self):
        from apps.vendite.services.preventivi_service import aggiorna_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": 5,
        }
        with self.assertRaises(ServiceError) as ctx:
            aggiorna_riga(
                1, 10,
                {"componenti_attivazioni": {"uuid-c1": True}},
                auth_user_id=100,
            )
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        self.mock_repo.update_riga.assert_not_called()

    # Scopo: list_componenti_riga ritorna la lista dal repo.
    def test_list_componenti_riga_ok(self):
        from apps.vendite.services.preventivi_service import list_componenti_riga

        self.mock_repo.get_riga.return_value = {
            "id": 10, "preventivo_id": 1,
            "articolo_id": "uuid-art", "meta": {},
        }
        self.mock_repo.list_componenti_riga.return_value = [
            {"id": 1, "componente_id": "c1", "prezzo_unitario": "200"},
            {"id": 2, "componente_id": "c2", "prezzo_unitario": "75"},
        ]
        result = list_componenti_riga(1, 10)
        self.assertEqual(len(result), 2)
        self.mock_repo.list_componenti_riga.assert_called_once_with(
            10, solo_attivi=True,
        )

    # Scopo: list su riga inesistente -> E_PREV_RIGA_NOT_FOUND.
    def test_list_componenti_riga_not_found(self):
        from apps.vendite.services.preventivi_service import list_componenti_riga

        self.mock_repo.get_riga.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            list_componenti_riga(1, 999)
        self.assertEqual(ctx.exception.code, "E_PREV_RIGA_NOT_FOUND")

    # Scopo: defense-in-depth — riga padre di altro preventivo -> 404.
    def test_list_componenti_riga_scope_violation(self):
        from apps.vendite.services.preventivi_service import list_componenti_riga

        self.mock_repo.get_riga.return_value = {
            "id": 10, "preventivo_id": 999,  # altro preventivo
            "articolo_id": "uuid-art", "meta": {},
        }
        with self.assertRaises(ServiceError) as ctx:
            list_componenti_riga(1, 10)
        self.assertEqual(ctx.exception.code, "E_PREV_RIGA_NOT_FOUND")

    # Scopo: update componente in BOZZA -> ok, delegato a repo.
    def test_update_componente_ok(self):
        from apps.vendite.services.preventivi_service import update_componente

        self.mock_repo.get_componente.return_value = {
            "id": 50, "riga_preventivo_id": 10,
            "componente_id": "c1", "prezzo_unitario": "200",
            "origine_prezzo": "CATEGORIA",
        }
        self.mock_repo.get_riga.return_value = {
            "id": 10, "preventivo_id": 1, "articolo_id": "uuid-art", "meta": {},
        }
        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
        }
        self.mock_repo.update_componente.return_value = True

        result = update_componente(
            1, 10, 50, {"prezzo_unitario": "150.00", "origine_prezzo": "MANUALE"},
        )
        self.assertEqual(result["componente_id"], 50)
        self.mock_repo.update_componente.assert_called_once()

    # Scopo: componente inesistente -> 404.
    def test_update_componente_not_found(self):
        from apps.vendite.services.preventivi_service import update_componente

        self.mock_repo.get_componente.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            update_componente(1, 10, 999, {"prezzo_unitario": "100"})
        self.assertEqual(ctx.exception.code, "E_PREV_COMPONENTE_NOT_FOUND")

    # Scopo: anti-tampering URL — `riga_id` URL non matcha la riga padre
    # reale del componente -> 404. Defense-in-depth contro URL forgiati.
    def test_update_componente_url_tampering_riga_id(self):
        from apps.vendite.services.preventivi_service import update_componente

        self.mock_repo.get_componente.return_value = {
            "id": 50, "riga_preventivo_id": 10,  # riga reale = 10
            "componente_id": "c1", "prezzo_unitario": "200",
        }
        with self.assertRaises(ServiceError) as ctx:
            # URL falso: riga_id=999 ma componente appartiene a riga=10
            update_componente(1, 999, 50, {"prezzo_unitario": "100"})
        self.assertEqual(ctx.exception.code, "E_PREV_COMPONENTE_NOT_FOUND")

    # Scopo: defense-in-depth — componente su altra riga/preventivo -> 404.
    def test_update_componente_scope_violation(self):
        from apps.vendite.services.preventivi_service import update_componente

        self.mock_repo.get_componente.return_value = {
            "id": 50, "riga_preventivo_id": 10,
            "componente_id": "c1", "prezzo_unitario": "200",
        }
        self.mock_repo.get_riga.return_value = {
            "id": 10, "preventivo_id": 999,  # altro preventivo
            "articolo_id": "uuid-art", "meta": {},
        }
        with self.assertRaises(ServiceError) as ctx:
            update_componente(1, 10, 50, {"prezzo_unitario": "100"})
        self.assertEqual(ctx.exception.code, "E_PREV_COMPONENTE_NOT_FOUND")

    # Scopo: guard stato preventivo non modificabile.
    def test_update_componente_stato_non_modificabile(self):
        from apps.vendite.services.preventivi_service import update_componente

        self.mock_repo.get_componente.return_value = {
            "id": 50, "riga_preventivo_id": 10,
            "componente_id": "c1", "prezzo_unitario": "200",
        }
        self.mock_repo.get_riga.return_value = {
            "id": 10, "preventivo_id": 1, "articolo_id": "uuid-art", "meta": {},
        }
        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "EMESSO", "uid": "abc",
        }
        with self.assertRaises(ServiceError) as ctx:
            update_componente(1, 10, 50, {"prezzo_unitario": "100"})
        self.assertEqual(ctx.exception.code, "E_PREV_STATO_NON_MODIFICABILE")

    # Scopo: soft delete componente in BOZZA.
    def test_delete_componente_ok(self):
        from apps.vendite.services.preventivi_service import delete_componente

        self.mock_repo.get_componente.return_value = {
            "id": 50, "riga_preventivo_id": 10,
        }
        self.mock_repo.get_riga.return_value = {
            "id": 10, "preventivo_id": 1, "articolo_id": "uuid-art", "meta": {},
        }
        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
        }
        self.mock_repo.delete_componente.return_value = True
        result = delete_componente(1, 10, 50)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["deleted"])
        self.mock_repo.delete_componente.assert_called_once_with(50)

    # Scopo: delete componente inesistente -> 404.
    def test_delete_componente_not_found(self):
        from apps.vendite.services.preventivi_service import delete_componente

        self.mock_repo.get_componente.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            delete_componente(1, 10, 999)
        self.assertEqual(ctx.exception.code, "E_PREV_COMPONENTE_NOT_FOUND")

    # ── Push commessa ──

    # Scopo: Verifica push preventivo ACCETTATO con righe eleggibili: il service
    # delega al CommessaPushOrchestrator filtrato (pr_run_commesse_push_one) e
    # restituisce il report aumentato di righe_pushable diagnostico.
    @patch("apps.vendite.services.commesse_service.pr_run_commesse_push_one")
    def test_push_a_commessa_ok(self, mock_push_one):
        from apps.vendite.services.preventivi_service import push_a_commessa

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "ACCETTATO", "uid": "abc",
        }
        self.mock_repo.count_righe_pushable.return_value = 3
        mock_push_one.return_value = {
            "stato": "COMPLETATO",
            "dry_run": False,
            "push_log_id": 42,
            "durata_ms": 12,
            "handlers": [{"handler_name": "HandlerPreventivi", "errors": []}],
        }

        result = push_a_commessa(1)

        # Orchestrator chiamato con codice + uid corretti.
        mock_push_one.assert_called_once_with(
            sorgente_codice="PREVENTIVO",
            sorgente_uid=1,
        )
        # Payload completo: campi orchestrator + righe_pushable diagnostico
        # + flag fatturazione_immediata dalla testata (per hint UX FE).
        self.assertEqual(result["preventivo_id"], 1)
        self.assertEqual(result["stato"], "COMPLETATO")
        self.assertEqual(result["push_log_id"], 42)
        self.assertEqual(result["durata_ms"], 12)
        self.assertEqual(result["righe_pushable"], 3)
        self.assertEqual(len(result["handlers"]), 1)
        # testata mock non ha "fatturazione_immediata" -> default False (no hint UX).
        self.assertFalse(result["fatturazione_immediata"])
        # Stato="COMPLETATO" -> transizione automatica a EVASO via fn DB.
        self.mock_repo.cambia_stato.assert_called_once_with(1, "EVASO", "django_api")

    # Scopo: post all-or-nothing, pr_run_commesse_push_one solleva
    # E_COMMESSA_PUSH_PARZIALE_VIETATO su PARZIALE/ERRORE rollando ogni
    # scrittura. push_a_commessa propaga l'eccezione e NON transita stato:
    # il preventivo resta ACCETTATO, niente righe orfane in commessa.
    @patch("apps.vendite.services.commesse_service.pr_run_commesse_push_one")
    def test_push_a_commessa_parziale_propaga_e_non_evade(self, mock_push_one):
        from apps.vendite.services.preventivi_service import push_a_commessa

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "ACCETTATO", "uid": "abc",
        }
        self.mock_repo.count_righe_pushable.return_value = 4
        mock_push_one.side_effect = ServiceError(
            code="E_COMMESSA_PUSH_PARZIALE_VIETATO",
            message="Push fallito: nessuna riga inviata.",
            detail="Errore riga segment_key=PREV:abc:R:3: ...",
        )

        with self.assertRaises(ServiceError) as ctx:
            push_a_commessa(1)

        self.assertEqual(ctx.exception.code, "E_COMMESSA_PUSH_PARZIALE_VIETATO")
        # All-or-nothing: nessuna transizione stato, nessuna chiamata DB.
        self.mock_repo.cambia_stato.assert_not_called()

    # Scopo: se la fn DB cambia_stato rifiuta la transizione (es. seed
    # EVASO non ancora atterrato in DB), il push e' gia' avvenuto e
    # ritorna comunque con stato COMPLETATO. La transizione fallita
    # viene loggata come warning, non fa fallire la richiesta utente.
    @patch("apps.vendite.services.commesse_service.pr_run_commesse_push_one")
    def test_push_a_commessa_transizione_db_error_logged_no_raise(self, mock_push_one):
        from django.db import DatabaseError
        from apps.vendite.services.preventivi_service import push_a_commessa

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "ACCETTATO", "uid": "abc",
        }
        self.mock_repo.count_righe_pushable.return_value = 1
        self.mock_repo.cambia_stato.side_effect = DatabaseError(
            "transizione ACCETTATO->EVASO non ammessa"
        )
        mock_push_one.return_value = {
            "stato": "COMPLETATO", "dry_run": False,
            "push_log_id": 44, "durata_ms": 10, "handlers": [],
        }

        # Non deve sollevare: il push e' atterrato, lo stato e' un effetto
        # collaterale che puo' restare disallineato finche' il deploy DB
        # non e' completo.
        result = push_a_commessa(1)
        self.assertEqual(result["stato"], "COMPLETATO")

    # Scopo: payload include flag `fatturazione_immediata=True` se settato in
    # testata: serve al FE per mostrare hint warn "emit AF al prossimo lotto"
    # (placeholder per PR2 servizio emissione immediata).
    @patch("apps.vendite.services.commesse_service.pr_run_commesse_push_one")
    def test_push_a_commessa_propaga_fatturazione_immediata(self, mock_push_one):
        from apps.vendite.services.preventivi_service import push_a_commessa

        self.mock_repo.get_preventivo.return_value = {
            "id": 1,
            "stato_codice_interno": "ACCETTATO",
            "uid": "abc",
            "fatturazione_immediata": True,
        }
        self.mock_repo.count_righe_pushable.return_value = 1
        mock_push_one.return_value = {
            "stato": "COMPLETATO", "dry_run": False,
            "push_log_id": 7, "durata_ms": 5, "handlers": [],
        }

        result = push_a_commessa(1)

        self.assertTrue(result["fatturazione_immediata"])

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
        # get_preventivo ora usa count_righe_per_stato_approvazione per
        # derivare righe_count + freeze pricing senza caricare l'elenco.
        self.mock_repo.count_righe_per_stato_approvazione.return_value = {
            "PENDING": 0, "APPROVED": 0, "REJECTED": 0, "TOTAL": 2,
        }
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

    # ── Sprint riepilogo IVA + filtri lista (sessione 03-05-2026) ──

    # Scopo: list_riepilogo_iva e' un thin facade su repo: verifica solo
    #        delegation + pass-through del payload.
    def test_list_riepilogo_iva_delega_a_repo(self):
        from apps.vendite.services.preventivi_service import list_riepilogo_iva

        self.mock_repo.list_riepilogo_iva.return_value = [
            {"iva_id": 1, "iva_aliquota": 22, "imponibile": "100.00", "imposta": "22.00",
             "arrotondamento": "0.0001"},
            {"iva_id": 2, "iva_aliquota": 10, "imponibile": "50.00", "imposta": "5.00",
             "arrotondamento": "-0.0002"},
        ]

        result = list_riepilogo_iva(42)

        self.mock_repo.list_riepilogo_iva.assert_called_once_with(42)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["iva_aliquota"], 22)

    # Scopo: filtro solo_revisione_attiva default True. Verifica che il
    #        service propaghi True al repo quando il parametro non e' passato.
    def test_list_preventivi_default_solo_revisione_attiva_true(self):
        from apps.vendite.services.preventivi_service import list_preventivi

        self.mock_repo.list_preventivi.return_value = ([], 0)

        list_preventivi(page=1, page_size=10)

        kwargs = self.mock_repo.list_preventivi.call_args.kwargs
        self.assertTrue(kwargs["solo_revisione_attiva"])

    # Scopo: filtro solo_revisione_attiva pass-through esplicito False
    #        (il FE col toggle "Mostra storico" passa false).
    def test_list_preventivi_solo_revisione_attiva_false(self):
        from apps.vendite.services.preventivi_service import list_preventivi

        self.mock_repo.list_preventivi.return_value = ([], 0)

        list_preventivi(page=1, page_size=10, solo_revisione_attiva=False)

        kwargs = self.mock_repo.list_preventivi.call_args.kwargs
        self.assertFalse(kwargs["solo_revisione_attiva"])

    # Scopo: derivazione qta_operativa quando il payload manda solo `quantita`
    #        (UX standard riga preventivo). Il service consulta factor_to_base
    #        della UoM operativa e calcola qta_operativa = quantita * factor.
    @patch("apps.vendite.services.preventivi_service.suggerisci_prezzo_riga")
    def test_gestisci_riga_deriva_qta_operativa_da_factor(self, mock_suggerisci):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = self._testata_completa()
        self.mock_repo.create_riga.return_value = {"id": 99}
        # factor_to_base = 12 (es. 1 confezione = 12 pezzi)
        self.mock_repo.get_articolo_uom_factor.return_value = Decimal("12")
        mock_suggerisci.return_value = {
            "prezzo_finale": "5.00", "origine": "CATEGORIA",
            "listino_id": 100, "contratto_id": None, "promo_id": None,
            "tipo_variazione_applicata": None, "valore_variazione_applicata": None,
        }

        gestisci_riga(
            1, {"articolo_id": "art-uuid", "uom_operativa_id": 8, "quantita": "3"},
            auth_user_id=42,
        )

        call = self.mock_repo.create_riga.call_args.kwargs
        # quantita 3 (UoM operativa) * factor 12 = 36 in UoM base
        self.assertEqual(Decimal(call["qta_operativa"]), Decimal("36"))
        self.assertEqual(Decimal(call["factor_to_base"]), Decimal("12"))

    # Scopo: derivazione qta_operativa fallback factor=1 quando l'articolo
    #        non ha mappa UoM operativa (caso edge: solo UoM base).
    #        Resolver ritorna stesso prezzo del payload per evitare check L1
    #        (focus del test e' la derivazione qta_operativa, non l'override).
    @patch("apps.vendite.services.preventivi_service.suggerisci_prezzo_riga")
    def test_gestisci_riga_deriva_qta_operativa_factor_default_1(self, mock_suggerisci):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = self._testata_completa()
        self.mock_repo.create_riga.return_value = {"id": 99}
        # Lookup factor_to_base ritorna None: UoM operativa non mappata
        self.mock_repo.get_articolo_uom_factor.return_value = None
        mock_suggerisci.return_value = {
            "prezzo_finale": "10.00", "origine": "CATEGORIA",
            "listino_id": 100, "contratto_id": None, "promo_id": None,
            "tipo_variazione_applicata": None, "valore_variazione_applicata": None,
        }

        gestisci_riga(
            1, {"articolo_id": "art-uuid", "uom_operativa_id": 8, "quantita": "5",
                "prezzo_unitario": "10.00"},
            auth_user_id=42,
        )

        call = self.mock_repo.create_riga.call_args.kwargs
        # Fallback factor=1: qta_operativa = quantita
        self.assertEqual(Decimal(call["qta_operativa"]), Decimal("5"))
        self.assertEqual(Decimal(call["factor_to_base"]), Decimal("1"))

    # ===========================================================
    # Sprint E (autorizzazioni prezzi L3): freeze preventivo
    # quando ci sono righe PENDING o REJECTED.
    # ===========================================================

    def _setup_get_preventivo_mocks(self, counts):
        """Helper per i 4 test sotto: mock minimi per get_preventivo() che
        prende testata + indirizzi + capabilities + count righe per stato."""
        self.mock_repo.get_preventivo.return_value = {
            "id": 42, "uid": "abc", "numero": "P-0042",
            "stato_codice": "DRAFT", "stato_codice_interno": "DRAFT",
            "billing_account_id": 10, "utility_id": 3,
        }
        self.mock_repo.list_indirizzi.return_value = []
        self.mock_repo.get_capabilities.return_value = {
            "stato_codice": "DRAFT",
            "available_actions": [{"key": "emetti", "target_state": "EMESSO"}],
            "can_edit_testata": True,
            "can_edit_righe": True,
            "non_editable_fields": [],
        }
        self.mock_repo.count_righe_per_stato_approvazione.return_value = counts

    def test_get_preventivo_frozen_pending_blocca_tutto(self):
        """Riga PENDING → can_edit_testata + can_edit_righe = false, no actions."""
        from apps.vendite.services.preventivi_service import get_preventivo
        self._setup_get_preventivo_mocks(
            {"PENDING": 1, "APPROVED": 0, "REJECTED": 0, "TOTAL": 5},
        )
        out = get_preventivo(42)
        self.assertEqual(out["available_actions"], [])
        self.assertFalse(out["can_edit_testata"])
        self.assertFalse(out["can_edit_righe"])
        self.assertTrue(out["frozen_for_pending_pricing"])
        self.assertFalse(out["frozen_for_rejected_pricing"])
        self.assertEqual(out["pending_pricing_count"], 1)
        self.assertEqual(out["rejected_pricing_count"], 0)

    def test_get_preventivo_frozen_rejected_only_lascia_edit_righe(self):
        """Solo REJECTED → operatore deve poter correggere la riga,
        quindi can_edit_righe=true (testata bloccata, no transitions)."""
        from apps.vendite.services.preventivi_service import get_preventivo
        self._setup_get_preventivo_mocks(
            {"PENDING": 0, "APPROVED": 0, "REJECTED": 2, "TOTAL": 4},
        )
        out = get_preventivo(42)
        self.assertEqual(out["available_actions"], [])
        self.assertFalse(out["can_edit_testata"])
        self.assertTrue(out["can_edit_righe"])  # ← chiave del fix
        self.assertFalse(out["frozen_for_pending_pricing"])
        self.assertTrue(out["frozen_for_rejected_pricing"])

    def test_get_preventivo_frozen_mixed_pending_vince(self):
        """PENDING + REJECTED → can_edit_righe=false (PENDING ha priorita')."""
        from apps.vendite.services.preventivi_service import get_preventivo
        self._setup_get_preventivo_mocks(
            {"PENDING": 1, "APPROVED": 0, "REJECTED": 1, "TOTAL": 6},
        )
        out = get_preventivo(42)
        self.assertFalse(out["can_edit_righe"])

    def test_get_preventivo_no_freeze_quando_solo_approved(self):
        """APPROVED non congela: il prezzo override e' stato approvato."""
        from apps.vendite.services.preventivi_service import get_preventivo
        self._setup_get_preventivo_mocks(
            {"PENDING": 0, "APPROVED": 3, "REJECTED": 0, "TOTAL": 3},
        )
        out = get_preventivo(42)
        # Capabilities originali preservate (no override BE).
        self.assertTrue(out["can_edit_testata"])
        self.assertEqual(len(out["available_actions"]), 1)
        self.assertFalse(out["frozen_for_pending_pricing"])
        self.assertFalse(out["frozen_for_rejected_pricing"])

    # ===========================================================
    # aggiorna_riga: auto-reset stato approvazione su correzione
    # prezzo (REJECTED/APPROVED → null se nuovo prezzo non viola L2).
    # ===========================================================

    def test_aggiorna_riga_rejected_reset_su_prezzo_corretto(self):
        """Riga REJECTED + nuovo prezzo entro L2 → reset stato + cleanup meta."""
        from apps.vendite.services.preventivi_service import aggiorna_riga
        # Setup: testata BOZZA, riga esistente REJECTED, nuovo prezzo = resolver.
        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT",
            "billing_account_id": 10, "utility_id": 3,
        }
        riga_esistente = {
            "id": 50, "articolo_id": "art-uuid", "uom_operativa_id": 7,
            "stato_approvazione_prezzo": "REJECTED",
            "pratica_approvazione_prezzo_id": 99,
            "meta": {
                "approvazione_rifiuto": {"motivazione": "test"},
                "altro_campo": "preserve",
            },
        }
        self.mock_repo.get_riga.return_value = riga_esistente

        # Mock _resolve_or_check_override_prezzo: ritorna prezzo allineato al
        # resolver (nessun override → no richiesta_approvazione_pending).
        with patch(
            "apps.vendite.services.preventivi_service._resolve_or_check_override_prezzo",
            return_value=(Decimal("10"), {"origine_prezzo": "CATEGORIA"}),
        ):
            aggiorna_riga(1, 50, {"prezzo_unitario": "10"}, auth_user_id=42)

        kwargs = self.mock_repo.update_riga.call_args.kwargs
        # Stato resettato a None.
        self.assertIsNone(kwargs["stato_approvazione_prezzo"])
        self.assertIsNone(kwargs["pratica_approvazione_prezzo_id"])
        # Meta cleanup: approvazione_rifiuto rimossa, altri campi preservati.
        self.assertNotIn("approvazione_rifiuto", kwargs["meta"])
        self.assertEqual(kwargs["meta"].get("altro_campo"), "preserve")

    def test_aggiorna_riga_no_reset_se_richiede_nuova_approvazione(self):
        """REJECTED + nuovo prezzo che richiede L3 → stato torna a PENDING,
        non viene resettato a None."""
        from apps.vendite.services.preventivi_service import aggiorna_riga
        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT",
            "billing_account_id": 10, "utility_id": 3,
        }
        self.mock_repo.get_riga.return_value = {
            "id": 50, "articolo_id": "art-uuid", "uom_operativa_id": 7,
            "stato_approvazione_prezzo": "REJECTED",
            "pratica_approvazione_prezzo_id": 99,
            "meta": {},
        }
        with patch(
            "apps.vendite.services.preventivi_service._resolve_or_check_override_prezzo",
            return_value=(Decimal("13"), {
                "origine_prezzo": "MANUALE",
                "richiesta_approvazione_pending": True,
                "violazione_l2": {"tipo_violazione": "MAGGIORAZIONE",
                                   "variazione_abs_pct": "30", "limite_pct": "5"},
            }),
        ), patch(
            "apps.vendite.services.preventivi_service._orchestrate_l3_request",
            return_value=200,
        ):
            aggiorna_riga(
                1, 50,
                {"prezzo_unitario": "13", "richiesta_approvazione": True},
                auth_user_id=42,
            )
        kwargs = self.mock_repo.update_riga.call_args.kwargs
        self.assertEqual(kwargs["stato_approvazione_prezzo"], "PENDING")
        self.assertEqual(kwargs["pratica_approvazione_prezzo_id"], 200)

    # ── preview_componenti_riga (form atomic 2026-05-12) ──

    # Scopo: happy path — testata valida → repo invocato con args corretti.
    def test_preview_componenti_riga_ok(self):
        from apps.vendite.services.preventivi_service import preview_componenti_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": 7,
            "emittente_fiscale_id": None,
        }
        self.mock_repo.preview_componenti_riga.return_value = [
            {"componente_id": "uuid-c1", "prezzo_suggerito": "10.00"},
        ]

        out = preview_componenti_riga(
            1, articolo_id="uuid-art", uom_operativa_id=2, quantita="3",
            auth_user_id=42,
        )
        self.assertEqual(len(out), 1)
        kwargs = self.mock_repo.preview_componenti_riga.call_args.kwargs
        self.assertEqual(kwargs["articolo_id"], "uuid-art")
        self.assertEqual(kwargs["uom_id"], 2)
        self.assertEqual(kwargs["utility_id"], 7)
        self.assertEqual(kwargs["ba_id"], 5)
        self.assertEqual(kwargs["emittente_soggetto_ruolo_id"], 100)

    # Scopo: preventivo inesistente → E_PREV_NOT_FOUND.
    def test_preview_componenti_riga_not_found(self):
        from apps.vendite.services.preventivi_service import preview_componenti_riga

        self.mock_repo.get_preventivo.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            preview_componenti_riga(
                999, articolo_id="uuid", uom_operativa_id=1, quantita="1",
            )
        self.assertEqual(ctx.exception.code, "E_PREV_NOT_FOUND")
        self.mock_repo.preview_componenti_riga.assert_not_called()

    # Scopo: data preventivo NULL → E_PREV_VALIDAZIONE.
    def test_preview_componenti_riga_data_mancante(self):
        from apps.vendite.services.preventivi_service import preview_componenti_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "data": None,
            "billing_account_id": 5, "utility_id": 7,
        }
        with self.assertRaises(ServiceError) as ctx:
            preview_componenti_riga(
                1, articolo_id="uuid", uom_operativa_id=1, quantita="1",
            )
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        self.mock_repo.preview_componenti_riga.assert_not_called()

    # Scopo: utility_id NULL → E_PREV_VALIDAZIONE (guard A2: niente fallback
    # silente a 0).
    def test_preview_componenti_riga_utility_mancante(self):
        from apps.vendite.services.preventivi_service import preview_componenti_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": None,
        }
        with self.assertRaises(ServiceError) as ctx:
            preview_componenti_riga(
                1, articolo_id="uuid", uom_operativa_id=1, quantita="1",
                auth_user_id=42,
            )
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        self.mock_repo.preview_componenti_riga.assert_not_called()

    # Scopo: emittente non risolvibile (no emittente sul preventivo + admin
    # globale senza emittenti assegnati) → E_PREV_VALIDAZIONE.
    def test_preview_componenti_riga_emittente_non_risolvibile(self):
        from apps.vendite.services.preventivi_service import preview_componenti_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": 7,
            "emittente_fiscale_id": None,
        }
        # Sovrascrivi mock setUp: admin globale → safe ritorna None.
        self.emittente_safe_patcher.stop()
        try:
            with patch(
                "apps.vendite.services._componenti_service_helpers.resolve_emittente_sr_id_safe",
                return_value=None,
            ):
                with self.assertRaises(ServiceError) as ctx:
                    preview_componenti_riga(
                        1, articolo_id="uuid", uom_operativa_id=1,
                        quantita="1", auth_user_id=None,
                    )
                self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        finally:
            self.emittente_safe_patcher.start()
        self.mock_repo.preview_componenti_riga.assert_not_called()

    # Scopo: emittente esplicito sul preventivo ha precedenza sul fallback
    # operatore — verifica helper di risoluzione condiviso.
    def test_preview_componenti_riga_usa_emittente_preventivo(self):
        from apps.vendite.services.preventivi_service import preview_componenti_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": 7,
            "emittente_fiscale_id": 77,
        }
        self.mock_repo.get_emittente_sr_id_by_fiscale_id.return_value = 999
        self.mock_repo.preview_componenti_riga.return_value = []

        preview_componenti_riga(
            1, articolo_id="uuid", uom_operativa_id=1, quantita="1",
            auth_user_id=42,
        )
        kwargs = self.mock_repo.preview_componenti_riga.call_args.kwargs
        # 999 dal preventivo, NON 100 dall'operatore (precedenza preventivo).
        self.assertEqual(kwargs["emittente_soggetto_ruolo_id"], 999)


class TestNormalizeComponentiOverrides(unittest.TestCase):
    """Form atomic 2026-05-12: validazione/normalizzazione overrides
    prima del cast jsonb lato repo. Decimal-safe.
    """

    def test_none_ritorna_none(self):
        from apps.vendite.services.preventivi_service import (
            _normalize_componenti_overrides,
        )
        self.assertIsNone(_normalize_componenti_overrides(None, function_name="t"))

    def test_dict_vuoto_ritorna_none(self):
        from apps.vendite.services.preventivi_service import (
            _normalize_componenti_overrides,
        )
        self.assertIsNone(_normalize_componenti_overrides({}, function_name="t"))

    def test_decimal_string_normalizzato(self):
        from apps.vendite.services.preventivi_service import (
            _normalize_componenti_overrides,
        )
        out = _normalize_componenti_overrides(
            {"uuid-c1": "12.500"}, function_name="t",
        )
        self.assertEqual(out, {"uuid-c1": "12.500"})

    def test_numero_python_normalizzato(self):
        from apps.vendite.services.preventivi_service import (
            _normalize_componenti_overrides,
        )
        out = _normalize_componenti_overrides(
            {"uuid-c1": 75}, function_name="t",
        )
        self.assertEqual(out, {"uuid-c1": "75"})

    def test_decimal_native_normalizzato(self):
        from apps.vendite.services.preventivi_service import (
            _normalize_componenti_overrides,
        )
        out = _normalize_componenti_overrides(
            {"uuid-c1": Decimal("3.14")}, function_name="t",
        )
        self.assertEqual(out, {"uuid-c1": "3.14"})

    def test_valore_none_solleva(self):
        from apps.vendite.services.preventivi_service import (
            _normalize_componenti_overrides,
        )
        with self.assertRaises(ServiceError) as ctx:
            _normalize_componenti_overrides(
                {"uuid-c1": None}, function_name="t",
            )
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")

    def test_valore_stringa_vuota_solleva(self):
        from apps.vendite.services.preventivi_service import (
            _normalize_componenti_overrides,
        )
        with self.assertRaises(ServiceError) as ctx:
            _normalize_componenti_overrides(
                {"uuid-c1": ""}, function_name="t",
            )
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")

    def test_valore_non_numerico_solleva(self):
        from apps.vendite.services.preventivi_service import (
            _normalize_componenti_overrides,
        )
        with self.assertRaises(ServiceError) as ctx:
            _normalize_componenti_overrides(
                {"uuid-c1": "abc"}, function_name="t",
            )
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")

    def test_overrides_non_dict_solleva(self):
        from apps.vendite.services.preventivi_service import (
            _normalize_componenti_overrides,
        )
        with self.assertRaises(ServiceError) as ctx:
            _normalize_componenti_overrides(
                ["uuid-c1", "10"], function_name="t",
            )
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")


class TestNormalizeComponentiAttivazioni(unittest.TestCase):
    """Modello unificato 2026-05-13: validazione/normalizzazione mappa
    {componente_id: bool}. Bool-only, no coercion da int/str."""

    def test_none_ritorna_none(self):
        from apps.vendite.services.preventivi_service import (
            _normalize_componenti_attivazioni,
        )
        self.assertIsNone(
            _normalize_componenti_attivazioni(None, function_name="t"),
        )

    def test_dict_vuoto_ritorna_none(self):
        from apps.vendite.services.preventivi_service import (
            _normalize_componenti_attivazioni,
        )
        self.assertIsNone(
            _normalize_componenti_attivazioni({}, function_name="t"),
        )

    def test_dict_bool_normalizzato(self):
        from apps.vendite.services.preventivi_service import (
            _normalize_componenti_attivazioni,
        )
        out = _normalize_componenti_attivazioni(
            {"uuid-c1": True, "uuid-c2": False}, function_name="t",
        )
        self.assertEqual(out, {"uuid-c1": True, "uuid-c2": False})

    def test_valore_non_bool_solleva(self):
        from apps.vendite.services.preventivi_service import (
            _normalize_componenti_attivazioni,
        )
        with self.assertRaises(ServiceError) as ctx:
            _normalize_componenti_attivazioni(
                {"uuid-c1": "true"}, function_name="t",
            )
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")

    def test_attivazioni_non_dict_solleva(self):
        from apps.vendite.services.preventivi_service import (
            _normalize_componenti_attivazioni,
        )
        with self.assertRaises(ServiceError) as ctx:
            _normalize_componenti_attivazioni(
                ["uuid-c1", True], function_name="t",
            )
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")


class TestCoerceMetaToDict(unittest.TestCase):
    """Test edge case `_coerce_meta_to_dict`: helper difensivo contro
    psycopg jsonb deserializzato come stringa."""

    def test_dict_passthrough(self):
        from apps.vendite.services.preventivi_service import _coerce_meta_to_dict
        out = _coerce_meta_to_dict({"a": 1})
        self.assertEqual(out, {"a": 1})

    def test_none_to_empty(self):
        from apps.vendite.services.preventivi_service import _coerce_meta_to_dict
        self.assertEqual(_coerce_meta_to_dict(None), {})

    def test_empty_string_to_empty(self):
        from apps.vendite.services.preventivi_service import _coerce_meta_to_dict
        self.assertEqual(_coerce_meta_to_dict(""), {})

    def test_empty_dict_passthrough(self):
        from apps.vendite.services.preventivi_service import _coerce_meta_to_dict
        self.assertEqual(_coerce_meta_to_dict({}), {})

    def test_json_string_dict(self):
        from apps.vendite.services.preventivi_service import _coerce_meta_to_dict
        out = _coerce_meta_to_dict('{"foo": "bar"}')
        self.assertEqual(out, {"foo": "bar"})

    def test_json_string_malformed(self):
        from apps.vendite.services.preventivi_service import _coerce_meta_to_dict
        self.assertEqual(_coerce_meta_to_dict("{not json"), {})

    def test_json_string_list_to_empty(self):
        # Una lista JSON deserializzata non e' un dict — ritorna {}.
        from apps.vendite.services.preventivi_service import _coerce_meta_to_dict
        self.assertEqual(_coerce_meta_to_dict('[1,2,3]'), {})

    def test_unexpected_type_to_empty(self):
        from apps.vendite.services.preventivi_service import _coerce_meta_to_dict
        self.assertEqual(_coerce_meta_to_dict(123), {})
        self.assertEqual(_coerce_meta_to_dict(True), {})


class TestPreventiviRepository(unittest.TestCase):
    # Scopo: Verifica che la lettura righe escluda le righe soft-delete
    #        (`attivo=false`), evitando che la UI mostri righe gia' eliminate.
    @patch("apps.vendite.db.preventivi_repository.connection")
    def test_repository_list_righe_filtra_solo_attive(self, mock_connection):
        from apps.vendite.db.preventivi_repository import PreventiviRepository

        cursor = MagicMock()
        cursor.description = [SimpleNamespace(name="id")]
        cursor.fetchall.return_value = []
        mock_connection.cursor.return_value.__enter__.return_value = cursor

        PreventiviRepository().list_righe(40)

        sql, params = cursor.execute.call_args.args
        self.assertIn("attivo IS TRUE", sql)
        self.assertEqual(params, [40])
