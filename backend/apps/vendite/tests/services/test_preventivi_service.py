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
17) test_list_preventivi_paginazione_invalida — page < 1
"""

import unittest
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

    # ── Paginazione ──

    # Scopo: Verifica errore paginazione invalida.
    def test_list_preventivi_paginazione_invalida(self):
        from apps.vendite.services.preventivi_service import list_preventivi

        with self.assertRaises(ServiceError) as ctx:
            list_preventivi(page=0, page_size=50)
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
