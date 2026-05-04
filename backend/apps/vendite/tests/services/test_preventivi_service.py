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
26) test_list_riepilogo_iva_delega_a_repo — facade lettura riepilogo IVA aggregato
27) test_list_preventivi_default_solo_revisione_attiva_true — filtro lista default
28) test_list_preventivi_solo_revisione_attiva_false — toggle "Mostra storico"
29) test_gestisci_riga_deriva_qta_operativa_da_factor — qta_op = quantita*factor
30) test_gestisci_riga_deriva_qta_operativa_factor_default_1 — fallback factor=1
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

    def tearDown(self):
        self.repo_patcher.stop()
        self.ba_repo_patcher.stop()
        self.iu_repo_patcher.stop()
        self.atomic_patcher.stop()

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
