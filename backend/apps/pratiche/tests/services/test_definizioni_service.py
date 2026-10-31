# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test service edizioni workflow (Fase 2 Slice 1a): la pagina della
#        lista (drift piatto) e il dettaglio (drift annidato). Mock repository, nessun DB reale.
# ------------------------------------------------------------
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.tests.db_error_fakes import make_db_error
from apps.core.services.service_errors import ServiceError
from apps.pratiche.services import definizioni_service

_SVC = "apps.pratiche.services.definizioni_service"


class DefinizioniServiceTests(SimpleTestCase):
    # Scopo: la lista e' una pagina (lista `pratiche.definizioni_workflow`, dal
    # 2026-10-31): filtri, ricerca, pagina e ordinamento arrivano al repository,
    # e il drift resta PIATTO (`versioni_indietro` e' il `campo_sorgente` del
    # catalogo). Senza `order_by` decide il default del repository.
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_list_definizioni_pagina_e_drift_piatto(self, MockRepo):
        riga = {"id": 12, "tipo_prestazione_id": 9004, "versioni_indietro": 2}
        MockRepo.return_value.list_definizioni.return_value = ([riga], 1)
        rows, total = definizioni_service.list_definizioni(
            tipo_prestazione_id=9004, search="gas", limit=10, offset=0,
        )
        self.assertEqual((rows, total), ([riga], 1))
        self.assertNotIn("drift", rows[0])
        MockRepo.return_value.list_definizioni.assert_called_once_with(
            tipo_prestazione_id=9004, emittente_fiscale_id=None, search="gas",
            order_by=None, order_dir=None, limit=10, offset=0,
        )

    # Scopo: un `order_by` fuori whitelist e' un 400, prima del repository.
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_list_definizioni_ordine_fuori_whitelist(self, MockRepo):
        with self.assertRaises(ServiceError):
            definizioni_service.list_definizioni(order_by="id", limit=10, offset=0)
        MockRepo.return_value.list_definizioni.assert_not_called()

    # --- Dettaglio editing (Slice 2 anello 1) ---

    @staticmethod
    def _mock_dettaglio_repo(repo):
        """Configura il repo mock per un dettaglio a 2 step con figli/archi vuoti."""
        repo.get_definizione.return_value = {
            "id": 12, "tipo_prestazione_id": 9004, "stato": "BOZZA",
            "emittente_fiscale_id": 155, "versione": 2,
            "versioni_indietro": 1, "preset_corrente_id": 7,
            "versione_preset_corrente": 3,
        }
        repo.list_steps_definizione.return_value = [
            {"id": 100, "codice": "STEP_A", "sequenza": 10},
            {"id": 101, "codice": "STEP_B", "sequenza": 20},
        ]
        for m in ("list_canali_definizione", "list_handler_eventi_definizione",
                  "list_competenze_definizione", "list_prerequisiti_definizione",
                  "list_formule_tempo_definizione", "list_regole_generazione_definizione"):
            getattr(repo, m).return_value = []

    # Scopo: il dettaglio annida il drift nell'header e affianca gli steps; passa
    # l'id al repository per tutte le letture.
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_get_dettaglio_ok(self, MockRepo):
        repo = MockRepo.return_value
        self._mock_dettaglio_repo(repo)
        out = definizioni_service.get_definizione_dettaglio(12)
        self.assertEqual(out["definizione"]["id"], 12)
        self.assertEqual(out["definizione"]["drift"]["versioni_indietro"], 1)
        self.assertNotIn("versioni_indietro", out["definizione"])
        self.assertEqual([s["codice"] for s in out["steps"]], ["STEP_A", "STEP_B"])
        # ogni step ha le tre liste figlio (vuote qui) e il payload ha archi.
        self.assertEqual(out["steps"][0]["canali"], [])
        self.assertEqual(set(out["archi"]), {"prerequisiti", "formule_tempo", "regole_generazione"})
        repo.get_definizione.assert_called_once_with(12)
        repo.list_steps_definizione.assert_called_once_with(12)

    # Scopo: i figli per-nodo si annidano sotto lo step giusto (per template_flusso_id)
    # e la chiave di raggruppamento non resta nell'oggetto annidato.
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_get_dettaglio_annida_figli(self, MockRepo):
        repo = MockRepo.return_value
        self._mock_dettaglio_repo(repo)
        repo.list_canali_definizione.return_value = [
            {"id": 1, "template_flusso_id": 100, "canale_codice": "WEB"},
            {"id": 2, "template_flusso_id": 101, "canale_codice": "MAIL"},
        ]
        repo.list_prerequisiti_definizione.return_value = [
            {"id": 9, "template_flusso_id": 101, "prerequisito_id": 100, "esito_richiesto": None},
        ]
        out = definizioni_service.get_definizione_dettaglio(12)
        step_a, step_b = out["steps"]
        self.assertEqual([c["canale_codice"] for c in step_a["canali"]], ["WEB"])
        self.assertEqual([c["canale_codice"] for c in step_b["canali"]], ["MAIL"])
        self.assertNotIn("template_flusso_id", step_a["canali"][0])
        self.assertEqual(out["archi"]["prerequisiti"][0]["prerequisito_id"], 100)

    # Scopo: id inesistente → 404 parlante, senza interrogare gli steps.
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_get_dettaglio_non_trovata(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_definizione.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            definizioni_service.get_definizione_dettaglio(999)
        self.assertEqual(ctx.exception.code, "E_DEFINIZIONE_NOT_FOUND")
        repo.list_steps_definizione.assert_not_called()

    # Scopo: guard di bordo sull'id (0/negativo) → E_INVALID_ID, coerente con le azioni.
    def test_get_dettaglio_id_invalido(self):
        with self.assertRaises(ServiceError) as ctx:
            definizioni_service.get_definizione_dettaglio(0)
        self.assertEqual(ctx.exception.code, "E_INVALID_ID")

    # --- Azioni ciclo di vita (Slice 1b) ---

    @patch(f"{_SVC}.DefinizioniRepository")
    def test_fork_definizione_ok(self, MockRepo):
        MockRepo.return_value.fork_definizione.return_value = 12
        out = definizioni_service.fork_definizione(7, 155)
        self.assertEqual(out, {"definizione_id": 12})
        MockRepo.return_value.fork_definizione.assert_called_once_with(7, 155)

    def test_fork_definizione_emittente_invalido(self):
        with self.assertRaises(ServiceError) as ctx:
            definizioni_service.fork_definizione(7, 0)
        self.assertEqual(ctx.exception.code, "E_INVALID_ID")

    @patch(f"{_SVC}.DefinizioniRepository")
    def test_pubblica_definizione_ok(self, MockRepo):
        MockRepo.return_value.pubblica_definizione.return_value = 7
        out = definizioni_service.pubblica_definizione(7)
        self.assertEqual(out, {"definizione_id": 7})

    # Scopo: marker DB (id 511) → ServiceError parlante su pubblica non ammessa.
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_pubblica_definizione_non_pubblicabile(self, MockRepo):

        MockRepo.return_value.pubblica_definizione.side_effect = make_db_error(
            "Definizione workflow 9 non pubblicabile: la BOZZA non ha modifiche.",
            codice="E_DEFINIZIONE_NON_PUBBLICABILE",
 )
        with self.assertRaises(ServiceError) as ctx:
            definizioni_service.pubblica_definizione(9)
        self.assertEqual(ctx.exception.code, "E_DEFINIZIONE_NON_PUBBLICABILE")

    @patch(f"{_SVC}.DefinizioniRepository")
    def test_nuova_versione_ok(self, MockRepo):
        MockRepo.return_value.nuova_versione_definizione.return_value = 20
        out = definizioni_service.nuova_versione_definizione(7)
        self.assertEqual(out, {"definizione_id": 20})

    # Scopo: guard invariante «≤1 BOZZA per scope» (fork) → marker parlante.
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_fork_bozza_esistente(self, MockRepo):

        MockRepo.return_value.fork_definizione.side_effect = make_db_error(
            "Esiste gia' una bozza di edizione workflow per lo scope "
            "(tipo prestazione 9004, emittente 44): completarla o scartarla.",
            codice="E_DEFINIZIONE_BOZZA_ESISTENTE",
        )
        with self.assertRaises(ServiceError) as ctx:
            definizioni_service.fork_definizione(7, 44)
        self.assertEqual(ctx.exception.code, "E_DEFINIZIONE_BOZZA_ESISTENTE")

    # Scopo: nuova-versione da sorgente non PUBBLICATA → marker parlante.
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_nuova_versione_no_pubblicata(self, MockRepo):

        MockRepo.return_value.nuova_versione_definizione.side_effect = make_db_error(
            "Nuova versione non ammessa: la definizione 419 non e' in stato PUBBLICATA.",
            codice="E_DEFINIZIONE_NO_PUBBLICATA",
 )
        with self.assertRaises(ServiceError) as ctx:
            definizioni_service.nuova_versione_definizione(419)
        self.assertEqual(ctx.exception.code, "E_DEFINIZIONE_NO_PUBBLICATA")

    # --- Write step su BOZZA (Slice 2 anello 3) ---

    # Scopo: create risolve tipo dalla definizione, normalizza il payload e passa
    # definizione_id + tipo_prestazione_id espliciti al repository.
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_create_step_ok(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_definizione.return_value = {"id": 419, "tipo_prestazione_id": 9004, "stato": "BOZZA"}
        repo.create_step.return_value = 555
        out = definizioni_service.create_step(419, {
            "codice": " NUOVO ", "descrizione": "Nuovo step", "sequenza": 15,
            "esito_default": "  ",  # vuoto → None
        })
        self.assertEqual(out, {"step_id": 555})
        args = repo.create_step.call_args
        self.assertEqual(args.args[0], 419)          # definizione_id
        self.assertEqual(args.args[1], 9004)         # tipo_prestazione_id
        data = args.args[2]
        self.assertEqual(data["codice"], "NUOVO")    # trim
        self.assertIsNone(data["esito_default"])     # vuoto → None

    # Scopo: definizione inesistente → 404, senza toccare il repository di scrittura.
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_create_step_definizione_non_trovata(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_definizione.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            definizioni_service.create_step(999, {"codice": "X", "descrizione": "Y"})
        self.assertEqual(ctx.exception.code, "E_DEFINIZIONE_NOT_FOUND")
        repo.create_step.assert_not_called()

    # Scopo: codice/descrizione obbligatori → E_VALIDATION_INPUT prima dell'INSERT.
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_create_step_manca_core(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_definizione.return_value = {"id": 419, "tipo_prestazione_id": 9004, "stato": "BOZZA"}
        with self.assertRaises(ServiceError) as ctx:
            definizioni_service.create_step(419, {"descrizione": "manca il codice"})
        self.assertEqual(ctx.exception.code, "E_VALIDATION_INPUT")
        repo.create_step.assert_not_called()

    # Scopo: guard immutabilità (edizione emessa) → marker TEMPLATE_DEFINIZIONE_CONGELATA.
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_create_step_congelata_marker(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_definizione.return_value = {"id": 418, "tipo_prestazione_id": 9004, "stato": "PUBBLICATA"}
        repo.create_step.side_effect = make_db_error(
            "Struttura della definizione workflow 418 non modificabile: e' un'edizione "
            "per-emittente gia' emessa (pubblicata o ritirata), struttura congelata.",
            codice="E_TEMPLATE_DEFINIZIONE_CONGELATA",
        )
        with self.assertRaises(ServiceError) as ctx:
            definizioni_service.create_step(418, {"codice": "X", "descrizione": "Y"})
        self.assertEqual(ctx.exception.code, "E_TEMPLATE_DEFINIZIONE_CONGELATA")

    # Scopo: update tocca solo lo scope (id, definizione_id); rowcount 0 → 404.
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_update_step_non_trovato(self, MockRepo):
        MockRepo.return_value.update_step.return_value = 0
        with self.assertRaises(ServiceError) as ctx:
            definizioni_service.update_step(419, 12345, {"descrizione": "x"})
        self.assertEqual(ctx.exception.code, "E_DEFINIZIONE_NOT_FOUND")

    # Scopo: update senza campi core → E_VALIDATION_INPUT (no UPDATE vuoto).
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_update_step_payload_vuoto(self, MockRepo):
        with self.assertRaises(ServiceError) as ctx:
            definizioni_service.update_step(419, 100, {})
        self.assertEqual(ctx.exception.code, "E_VALIDATION_INPUT")
        MockRepo.return_value.update_step.assert_not_called()

    # Scopo: ⛔ una chiave fuori STEP_CORE_FIELDS (es. un campo display) è un 400
    # col nome della chiave, non uno scarto silenzioso (2026-09-26).
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_update_step_chiave_estranea_rifiutata(self, MockRepo):
        with self.assertRaises(ServiceError) as ctx:
            definizioni_service.update_step(419, 100, {"descrizione": "x", "campo_sconosciuto": 1})
        self.assertEqual(ctx.exception.code, "E_VALIDATION_INPUT")
        self.assertIn("campo_sconosciuto", ctx.exception.detail)
        MockRepo.return_value.update_step.assert_not_called()

    @patch(f"{_SVC}.DefinizioniRepository")
    def test_update_step_ok(self, MockRepo):
        MockRepo.return_value.update_step.return_value = 1
        out = definizioni_service.update_step(419, 100, {"descrizione": "aggiornato"})
        self.assertEqual(out, {"step_id": 100})

    @patch(f"{_SVC}.DefinizioniRepository")
    def test_delete_step_ok(self, MockRepo):
        MockRepo.return_value.delete_step.return_value = 1
        out = definizioni_service.delete_step(419, 100)
        self.assertEqual(out, {"deleted": True})

    @patch(f"{_SVC}.DefinizioniRepository")
    def test_delete_step_non_trovato(self, MockRepo):
        MockRepo.return_value.delete_step.return_value = 0
        with self.assertRaises(ServiceError) as ctx:
            definizioni_service.delete_step(419, 12345)
        self.assertEqual(ctx.exception.code, "E_DEFINIZIONE_NOT_FOUND")

    # --- Write figli per-nodo (Slice 2 anello 4) ---

    # Scopo: create verifica ownership step→definizione, pulisce il payload sui soli
    # campi scrivibili del kind e passa (kind, step_id, data) al repository.
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_create_figlio_ok(self, MockRepo):
        repo = MockRepo.return_value
        repo.step_in_definizione.return_value = True
        repo.create_child.return_value = 77
        out = definizioni_service.create_step_figlio(419, 100, "canali", {
            "canale_id": 3, "attivo": True,
        })
        self.assertEqual(out, {"id": 77})
        repo.step_in_definizione.assert_called_once_with(419, 100)
        kind, step, data = repo.create_child.call_args.args
        self.assertEqual((kind, step), ("canali", 100))
        self.assertEqual(data, {"canale_id": 3, "attivo": True})

    # Scopo: ⛔ una chiave fuori dai campi scrivibili del kind è un 400, non uno
    # scarto silenzioso (2026-09-26): nessun INSERT.
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_create_figlio_chiave_estranea_rifiutata(self, MockRepo):
        repo = MockRepo.return_value
        repo.step_in_definizione.return_value = True
        with self.assertRaises(ServiceError) as ctx:
            definizioni_service.create_step_figlio(419, 100, "canali", {
                "canale_id": 3, "attivo": True, "campo_ignoto": "x",
            })
        self.assertEqual(ctx.exception.code, "E_VALIDATION_INPUT")
        self.assertIn("campo_ignoto", ctx.exception.detail)
        repo.create_child.assert_not_called()

    # Scopo: step fuori dalla definizione → 404, senza INSERT.
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_create_figlio_step_fuori_scope(self, MockRepo):
        repo = MockRepo.return_value
        repo.step_in_definizione.return_value = False
        with self.assertRaises(ServiceError) as ctx:
            definizioni_service.create_step_figlio(419, 999, "canali", {"canale_id": 3})
        self.assertEqual(ctx.exception.code, "E_DEFINIZIONE_NOT_FOUND")
        repo.create_child.assert_not_called()

    # Scopo: campo required del kind mancante → 400 parlante (prima del NOT NULL DB).
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_create_figlio_required_mancante(self, MockRepo):
        repo = MockRepo.return_value
        repo.step_in_definizione.return_value = True
        with self.assertRaises(ServiceError) as ctx:
            definizioni_service.create_step_figlio(419, 100, "handler_eventi", {"evento": "AVVIO"})
        self.assertEqual(ctx.exception.code, "E_VALIDATION_INPUT")  # manca handler_id
        repo.create_child.assert_not_called()

    # Scopo: guard immutabilità sul figlio (edizione emessa) → marker parlante.
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_create_figlio_congelata_marker(self, MockRepo):
        repo = MockRepo.return_value
        repo.step_in_definizione.return_value = True
        repo.create_child.side_effect = make_db_error(
            "… e' un'edizione per-emittente gia' emessa, struttura congelata.",
            codice="E_TEMPLATE_DEFINIZIONE_CONGELATA",
        )
        with self.assertRaises(ServiceError) as ctx:
            definizioni_service.create_step_figlio(418, 9660, "canali", {"canale_id": 3})
        self.assertEqual(ctx.exception.code, "E_TEMPLATE_DEFINIZIONE_CONGELATA")

    # Scopo: update fuori scope (riga/step/definizione) → rowcount 0 → 404.
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_update_figlio_non_trovato(self, MockRepo):
        MockRepo.return_value.update_child.return_value = 0
        with self.assertRaises(ServiceError) as ctx:
            definizioni_service.update_step_figlio(419, 100, "handler_eventi", 55, {"sequenza": 2})
        self.assertEqual(ctx.exception.code, "E_DEFINIZIONE_NOT_FOUND")

    # Scopo: update senza campi scrivibili → 400 (no UPDATE vuoto).
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_update_figlio_payload_vuoto(self, MockRepo):
        with self.assertRaises(ServiceError) as ctx:
            definizioni_service.update_step_figlio(419, 100, "canali", 5, {})
        self.assertEqual(ctx.exception.code, "E_VALIDATION_INPUT")
        MockRepo.return_value.update_child.assert_not_called()

    @patch(f"{_SVC}.DefinizioniRepository")
    def test_delete_figlio_ok(self, MockRepo):
        MockRepo.return_value.delete_child.return_value = 1
        out = definizioni_service.delete_step_figlio(419, 100, "competenze", 9)
        self.assertEqual(out, {"deleted": True})
        MockRepo.return_value.delete_child.assert_called_once_with("competenze", 419, 100, 9)

    @patch(f"{_SVC}.DefinizioniRepository")
    def test_delete_figlio_non_trovato(self, MockRepo):
        MockRepo.return_value.delete_child.return_value = 0
        with self.assertRaises(ServiceError) as ctx:
            definizioni_service.delete_step_figlio(419, 100, "canali", 12345)
        self.assertEqual(ctx.exception.code, "E_DEFINIZIONE_NOT_FOUND")

    # --- Write archi del grafo (Slice 2 anello 5) ---

    # Scopo: create prerequisito valida entrambi gli endpoint step in-definizione
    # e inserisce i soli campi writable.
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_create_arco_prerequisito_ok(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_definizione.return_value = {"id": 419, "tipo_prestazione_id": 9004}
        repo.step_in_definizione.return_value = True
        repo.create_edge.return_value = 88
        out = definizioni_service.create_arco(419, "prerequisiti", {
            "template_flusso_id": 100, "prerequisito_id": 101, "esito_richiesto": "POSITIVO",
        })
        self.assertEqual(out, {"id": 88})
        # entrambi gli endpoint validati in-definizione
        self.assertEqual(repo.step_in_definizione.call_count, 2)
        kind, data = repo.create_edge.call_args.args
        self.assertEqual(kind, "prerequisiti")
        self.assertEqual(data["prerequisito_id"], 101)

    # Scopo: uno step-endpoint non nella definizione → 404, senza INSERT.
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_create_arco_endpoint_fuori_scope(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_definizione.return_value = {"id": 419, "tipo_prestazione_id": 9004}
        repo.step_in_definizione.side_effect = [True, False]  # prerequisito_id fuori scope
        with self.assertRaises(ServiceError) as ctx:
            definizioni_service.create_arco(419, "prerequisiti", {
                "template_flusso_id": 100, "prerequisito_id": 999})
        self.assertEqual(ctx.exception.code, "E_DEFINIZIONE_NOT_FOUND")
        repo.create_edge.assert_not_called()

    # Scopo: formule_tempo → il BE auto-imposta tipo_prestazione_id dal tipo della definizione.
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_create_arco_formule_autoset_tipo(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_definizione.return_value = {"id": 419, "tipo_prestazione_id": 9004}
        repo.step_in_definizione.return_value = True
        repo.create_edge.return_value = 5
        definizioni_service.create_arco(419, "formule_tempo", {
            "template_flusso_da_id": 100, "template_flusso_a_id": 101,
            "giorni_esecuzione": 5, "giorni_warning": 3, "giorni_critico": 7,
        })
        _, data = repo.create_edge.call_args.args
        self.assertEqual(data["tipo_prestazione_id"], 9004)  # auto-set dal BE

    # Scopo: campo required mancante → 400 prima dell'INSERT.
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_create_arco_required_mancante(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_definizione.return_value = {"id": 419, "tipo_prestazione_id": 9004}
        with self.assertRaises(ServiceError) as ctx:
            definizioni_service.create_arco(419, "regole_generazione", {
                "template_flusso_origine_id": 100})  # manca tipo_prestazione_dest_id
        self.assertEqual(ctx.exception.code, "E_VALIDATION_INPUT")
        repo.create_edge.assert_not_called()

    # Scopo: guard immutabilità sull'arco (edizione emessa) → marker parlante.
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_create_arco_congelata_marker(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_definizione.return_value = {"id": 418, "tipo_prestazione_id": 9004}
        repo.step_in_definizione.return_value = True
        repo.create_edge.side_effect = make_db_error(
            "… e' un'edizione per-emittente gia' emessa, struttura congelata.",
            codice="E_TEMPLATE_DEFINIZIONE_CONGELATA",
        )
        with self.assertRaises(ServiceError) as ctx:
            definizioni_service.create_arco(418, "prerequisiti", {
                "template_flusso_id": 1, "prerequisito_id": 2})
        self.assertEqual(ctx.exception.code, "E_TEMPLATE_DEFINIZIONE_CONGELATA")

    @patch(f"{_SVC}.DefinizioniRepository")
    def test_delete_arco_ok(self, MockRepo):
        MockRepo.return_value.delete_edge.return_value = 1
        out = definizioni_service.delete_arco(419, "prerequisiti", 88)
        self.assertEqual(out, {"deleted": True})
        MockRepo.return_value.delete_edge.assert_called_once_with("prerequisiti", 419, 88)

    @patch(f"{_SVC}.DefinizioniRepository")
    def test_delete_arco_non_trovato(self, MockRepo):
        MockRepo.return_value.delete_edge.return_value = 0
        with self.assertRaises(ServiceError) as ctx:
            definizioni_service.delete_arco(419, "prerequisiti", 12345)
        self.assertEqual(ctx.exception.code, "E_DEFINIZIONE_NOT_FOUND")

    # Scopo: update senza campi writable → 400 (no UPDATE vuoto).
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_update_arco_payload_vuoto(self, MockRepo):
        with self.assertRaises(ServiceError) as ctx:
            definizioni_service.update_arco(419, "formule_tempo", 5, {})
        self.assertEqual(ctx.exception.code, "E_VALIDATION_INPUT")
        MockRepo.return_value.update_edge.assert_not_called()

    # Scopo: ⛔ `attivo` non è scrivibile sui prerequisiti: 400, non scarto
    # silenzioso (2026-09-26).
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_update_arco_chiave_estranea_rifiutata(self, MockRepo):
        with self.assertRaises(ServiceError) as ctx:
            definizioni_service.update_arco(419, "prerequisiti", 5, {"attivo": False})
        self.assertEqual(ctx.exception.code, "E_VALIDATION_INPUT")
        MockRepo.return_value.update_edge.assert_not_called()

    # Scopo (regressione): un PATCH che ri-punta un endpoint dell'arco a uno step
    # fuori dalla definizione → 404, SENZA UPDATE (il guard DB non lo intercetta).
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_update_arco_endpoint_fuori_scope(self, MockRepo):
        repo = MockRepo.return_value
        repo.step_in_definizione.return_value = False
        with self.assertRaises(ServiceError) as ctx:
            definizioni_service.update_arco(419, "prerequisiti", 88, {"template_flusso_id": 999})
        self.assertEqual(ctx.exception.code, "E_DEFINIZIONE_NOT_FOUND")
        repo.update_edge.assert_not_called()

    # Scopo: update di soli attributi (nessun endpoint nel payload) → nessuna
    # rivalidazione step, procede.
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_update_arco_solo_attributo(self, MockRepo):
        repo = MockRepo.return_value
        repo.update_edge.return_value = 1
        out = definizioni_service.update_arco(419, "prerequisiti", 88, {"esito_richiesto": "NEGATIVO"})
        self.assertEqual(out, {"id": 88})
        repo.step_in_definizione.assert_not_called()
