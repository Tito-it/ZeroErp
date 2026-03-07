# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per pratiche_service (CRUD pratiche).
#        Mock DB, compatibile CI senza database reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) PraticheServiceTests.test_crea_pratica_ok
2) PraticheServiceTests.test_crea_pratica_errore_emittente_zero
3) PraticheServiceTests.test_crea_pratica_errore_tipo_prestazione_zero
4) PraticheServiceTests.test_crea_pratica_errore_priorita_zero
5) PraticheServiceTests.test_aggiorna_pratica_ok
6) PraticheServiceTests.test_aggiorna_pratica_non_trovata
7) PraticheServiceTests.test_aggiorna_pratica_errore_id_zero
8) PraticheServiceTests.test_cambia_stato_pratica_ok
9) PraticheServiceTests.test_cambia_stato_pratica_errore_id_zero
10) PraticheServiceTests.test_cambia_stato_pratica_errore_stato_vuoto
11) PraticheServiceTests.test_assegna_pratica_ok
12) PraticheServiceTests.test_assegna_pratica_nessun_dato
13) PraticheServiceTests.test_cerca_pratiche_ok
14) PraticheServiceTests.test_get_giornale_ok
"""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.pratiche.services import pratiche_service

# Path base per i mock del servizio.
_SVC = "apps.pratiche.services.pratiche_service"
_ATOMIC = "django.db.transaction.Atomic"


def _mock_pratica_row(pratica_id: int = 1) -> dict:
    """Genera una PraticaRow fittizia per i test."""
    return {
        "id": pratica_id,
        "emittente_fiscale_id": 10,
        "tipo_prestazione_id": 5,
        "soggetto_id": None,
        "stato_id": 1,
        "priorita_id": 2,
        "risorsa_umana_id": None,
        "unita_organizzativa_id": None,
        "pratica_padre_id": None,
        "flusso_origine_id": None,
        "canale_origine_id": None,
        "codice": "P-001",
        "descrizione": "Test pratica",
        "data_scadenza": None,
        "meta": {},
        "data_insert": "2026-03-04T10:00:00+00:00",
        "user_insert": "test_user",
    }


class PraticheServiceTests(SimpleTestCase):

    # Scopo: Disabilita transaction.atomic per tutti i test (no DB reale).
    def setUp(self) -> None:
        p_enter = patch(f"{_ATOMIC}.__enter__", return_value=None)
        p_exit = patch(f"{_ATOMIC}.__exit__", return_value=False)
        p_enter.start()
        p_exit.start()
        self.addCleanup(p_enter.stop)
        self.addCleanup(p_exit.stop)

    # Scopo: Verifica creazione pratica base con tutti i campi obbligatori.
    @patch(f"{_SVC}.PraticheRepository")
    def test_crea_pratica_ok(self, MockRepo):
        repo = MockRepo.return_value
        repo.resolve_stato_pratica.return_value = 1
        repo.create_pratica.return_value = 42

        result = pratiche_service.crea_pratica(
            emittente_fiscale_id=10,
            tipo_prestazione_id=5,
            priorita_id=2,
        )
        self.assertEqual(result, 42)
        repo.resolve_stato_pratica.assert_called_once_with("BOZZA")
        repo.create_pratica.assert_called_once()

    # Scopo: Verifica errore se emittente_fiscale_id <= 0.
    def test_crea_pratica_errore_emittente_zero(self):
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.crea_pratica(
                emittente_fiscale_id=0,
                tipo_prestazione_id=5,
                priorita_id=2,
            )
        self.assertEqual(ctx.exception.code, "E_PRATICA_VALIDATION")

    # Scopo: Verifica errore se tipo_prestazione_id <= 0.
    def test_crea_pratica_errore_tipo_prestazione_zero(self):
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.crea_pratica(
                emittente_fiscale_id=10,
                tipo_prestazione_id=0,
                priorita_id=2,
            )
        self.assertEqual(ctx.exception.code, "E_PRATICA_VALIDATION")

    # Scopo: Verifica errore se priorita_id <= 0.
    def test_crea_pratica_errore_priorita_zero(self):
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.crea_pratica(
                emittente_fiscale_id=10,
                tipo_prestazione_id=5,
                priorita_id=0,
            )
        self.assertEqual(ctx.exception.code, "E_PRATICA_VALIDATION")

    # Scopo: Verifica aggiornamento pratica con campi validi.
    @patch(f"{_SVC}.PraticheRepository")
    def test_aggiorna_pratica_ok(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_pratica.return_value = _mock_pratica_row(1)

        pratiche_service.aggiorna_pratica(1, {"descrizione": "Nuova desc"})

        repo.get_pratica.assert_called_once_with(1)
        repo.update_pratica.assert_called_once_with(1, {"descrizione": "Nuova desc"})

    # Scopo: Verifica errore quando la pratica non esiste.
    @patch(f"{_SVC}.PraticheRepository")
    def test_aggiorna_pratica_non_trovata(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_pratica.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.aggiorna_pratica(99, {"descrizione": "x"})
        self.assertEqual(ctx.exception.code, "E_PRATICA_NOT_FOUND")

    # Scopo: Verifica errore se pratica_id <= 0 in aggiornamento.
    def test_aggiorna_pratica_errore_id_zero(self):
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.aggiorna_pratica(0, {"descrizione": "x"})
        self.assertEqual(ctx.exception.code, "E_INVALID_ID")

    # Scopo: Verifica cambio stato pratica con esito positivo.
    @patch(f"{_SVC}.PraticheRepository")
    def test_cambia_stato_pratica_ok(self, MockRepo):
        repo = MockRepo.return_value

        pratiche_service.cambia_stato_pratica(1, "APERTA")

        repo.update_stato_pratica.assert_called_once_with(1, "APERTA")

    # Scopo: Verifica errore se pratica_id <= 0 in cambio stato.
    def test_cambia_stato_pratica_errore_id_zero(self):
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.cambia_stato_pratica(0, "APERTA")
        self.assertEqual(ctx.exception.code, "E_INVALID_ID")

    # Scopo: Verifica errore se nuovo_stato e' vuoto.
    def test_cambia_stato_pratica_errore_stato_vuoto(self):
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.cambia_stato_pratica(1, "")
        self.assertEqual(ctx.exception.code, "E_PRATICA_VALIDATION")

    # Scopo: Verifica assegnazione pratica con risorsa e UO.
    @patch(f"{_SVC}.PraticheRepository")
    def test_assegna_pratica_ok(self, MockRepo):
        repo = MockRepo.return_value

        pratiche_service.assegna_pratica(1, risorsa_umana_id=10, unita_organizzativa_id=20)

        repo.update_pratica.assert_called_once()
        call_data = repo.update_pratica.call_args[0][1]
        self.assertEqual(call_data["risorsa_umana_id"], 10)
        self.assertEqual(call_data["unita_organizzativa_id"], 20)

    # Scopo: Verifica che senza dati di assegnazione non viene chiamato update.
    @patch(f"{_SVC}.PraticheRepository")
    def test_assegna_pratica_nessun_dato(self, MockRepo):
        repo = MockRepo.return_value

        pratiche_service.assegna_pratica(1)

        repo.update_pratica.assert_not_called()

    # Scopo: Verifica delega a repository per ricerca pratiche.
    @patch(f"{_SVC}.PraticheRepository")
    def test_cerca_pratiche_ok(self, MockRepo):
        repo = MockRepo.return_value
        repo.list_pratiche.return_value = ([_mock_pratica_row()], 1)

        items, total = pratiche_service.cerca_pratiche(emittente_fiscale_id=10)

        self.assertEqual(total, 1)
        self.assertEqual(len(items), 1)
        repo.list_pratiche.assert_called_once()

    # Scopo: Verifica delega a repository per giornale pratica.
    @patch(f"{_SVC}.PraticheRepository")
    def test_get_giornale_ok(self, MockRepo):
        repo = MockRepo.return_value
        giornale_row = {
            "id": 1, "pratica_id": 1, "flusso_id": None,
            "azione": "PRATICA_CREATA", "origine": "SISTEMA",
            "dettaglio": {}, "tx_id": "abc-123",
            "data_insert": "2026-03-04T10:00:00+00:00", "user_insert": "sys",
        }
        repo.get_giornale_pratica.return_value = ([giornale_row], 1)

        items, total = pratiche_service.get_giornale(1, limit=50, offset=0)

        self.assertEqual(total, 1)
        self.assertEqual(items[0]["tx_id"], "abc-123")
