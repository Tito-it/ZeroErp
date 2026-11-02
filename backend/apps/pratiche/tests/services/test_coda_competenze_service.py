# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per coda lavoro, prendi in carico e competenze flussi.
#        Mock DB, compatibile CI senza database reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) CodaLavoroServiceTests.test_get_coda_lavoro_ok
 2) CodaLavoroServiceTests.test_get_coda_lavoro_errore_risorsa_zero
 3) CodaLavoroServiceTests.test_get_coda_lavoro_errore_emittente_zero
 4) PrendiInCaricoServiceTests.test_prendi_in_carico_ok
 5) PrendiInCaricoServiceTests.test_prendi_in_carico_gia_assegnato
 6) PrendiInCaricoServiceTests.test_prendi_in_carico_errore_flusso_zero
 7) PrendiInCaricoServiceTests.test_prendi_in_carico_errore_risorsa_zero
 8) CompetenzeFlussiServiceTests.test_get_competenze_ok
 9) CompetenzeFlussiServiceTests.test_crea_competenza_ok
10) CompetenzeFlussiServiceTests.test_crea_competenza_errore_template_zero
11) CompetenzeFlussiServiceTests.test_elimina_competenza_ok
12) CompetenzeFlussiServiceTests.test_elimina_competenza_non_trovata
"""

from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.pratiche.services import pratiche_service

_SVC = "apps.pratiche.services.pratiche_service"
_ATOMIC = "django.db.transaction.Atomic"


def _mock_coda_row(livello: str = "ASSEGNATO") -> dict:
    """Genera una CodaLavoroRow fittizia per i test."""
    return {
        "livello": livello,
        "flusso_id": 10,
        "pratica_id": 1,
        "pratica_codice": "PRA-0000001",
        "pratica_descrizione": "Test pratica",
        "priorita_codice": "NORMALE",
        "tipo_prestazione_codice": "MANUTENZIONE",
        "template_flusso_codice": "VALUTAZIONE",
        "template_flusso_desc": "Valutazione iniziale",
        "stato_flusso_codice_interno": "DA_ESEGUIRE", "stato_flusso_codice": "DA_ESEGUIRE",
        "sequenza": 10,
        "data_scadenza": None,
        "risorsa_assegnata": None,
    }


def _mock_competenza_row(competenza_id: int = 1) -> dict:
    """Genera una CompetenzaFlussoRow fittizia per i test."""
    return {
        "id": competenza_id,
        "template_flusso_id": 5,
        "unita_organizzativa_id": 3,
        "risorsa_umana_id": 100,
        "attivo": True,
        "template_flusso_codice": "VALUTAZIONE",
        "template_flusso_descrizione": "Valutazione iniziale",
        "unita_organizzativa_descrizione": "Reparto Tecnico",
        "risorsa_umana_display": "Mario Rossi",
    }


# ================================================================== #
# Coda lavoro                                                          #
# ================================================================== #


class CodaLavoroServiceTests(SimpleTestCase):

    def setUp(self):
        p_enter = patch(f"{_ATOMIC}.__enter__", return_value=None)
        p_exit = patch(f"{_ATOMIC}.__exit__", return_value=False)
        p_enter.start()
        p_exit.start()
        self.addCleanup(p_enter.stop)
        self.addCleanup(p_exit.stop)

    @patch(f"{_SVC}.PraticheRepository")
    def test_get_coda_lavoro_ok(self, MockRepo):
        # Scopo: verifica che get_coda_lavoro restituisca i risultati del repository.
        repo = MockRepo.return_value
        repo.list_coda_lavoro.return_value = [
            _mock_coda_row("ASSEGNATO"),
            _mock_coda_row("COMPETENZA"),
        ]

        result = pratiche_service.get_coda_lavoro(risorsa_umana_id=100, emittente_fiscale_id=10)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["livello"], "ASSEGNATO")
        repo.list_coda_lavoro.assert_called_once_with(100, 10)

    def test_get_coda_lavoro_errore_risorsa_zero(self):
        # Scopo: verifica errore per risorsa_umana_id <= 0.
        with self.assertRaises(ServiceError):
            pratiche_service.get_coda_lavoro(risorsa_umana_id=0, emittente_fiscale_id=10)

    def test_get_coda_lavoro_errore_emittente_zero(self):
        # Scopo: verifica errore per emittente_fiscale_id <= 0.
        with self.assertRaises(ServiceError):
            pratiche_service.get_coda_lavoro(risorsa_umana_id=100, emittente_fiscale_id=0)


# ================================================================== #
# Prendi in carico                                                     #
# ================================================================== #


class PrendiInCaricoServiceTests(SimpleTestCase):

    def setUp(self):
        p_enter = patch(f"{_ATOMIC}.__enter__", return_value=None)
        p_exit = patch(f"{_ATOMIC}.__exit__", return_value=False)
        p_enter.start()
        p_exit.start()
        self.addCleanup(p_enter.stop)
        self.addCleanup(p_exit.stop)

    @patch(f"{_SVC}.PraticheRepository")
    def test_prendi_in_carico_ok(self, MockRepo):
        # Scopo: verifica assegnazione riuscita.
        repo = MockRepo.return_value
        repo.prendi_in_carico_flusso.return_value = True

        result = pratiche_service.prendi_in_carico(flusso_id=10, risorsa_umana_id=100)
        self.assertTrue(result)
        repo.prendi_in_carico_flusso.assert_called_once_with(10, 100)

    @patch(f"{_SVC}.PraticheRepository")
    def test_prendi_in_carico_gia_assegnato(self, MockRepo):
        # Scopo: verifica ritorno False se gia' assegnato allo stesso operatore.
        repo = MockRepo.return_value
        repo.prendi_in_carico_flusso.return_value = False

        result = pratiche_service.prendi_in_carico(flusso_id=10, risorsa_umana_id=100)
        self.assertFalse(result)

    def test_prendi_in_carico_errore_flusso_zero(self):
        # Scopo: verifica errore per flusso_id <= 0.
        with self.assertRaises(ServiceError):
            pratiche_service.prendi_in_carico(flusso_id=0, risorsa_umana_id=100)

    def test_prendi_in_carico_errore_risorsa_zero(self):
        # Scopo: verifica errore per risorsa_umana_id <= 0.
        with self.assertRaises(ServiceError):
            pratiche_service.prendi_in_carico(flusso_id=10, risorsa_umana_id=0)


# ================================================================== #
# Competenze flussi                                                    #
# ================================================================== #


class CompetenzeFlussiServiceTests(SimpleTestCase):

    def setUp(self):
        p_enter = patch(f"{_ATOMIC}.__enter__", return_value=None)
        p_exit = patch(f"{_ATOMIC}.__exit__", return_value=False)
        p_enter.start()
        p_exit.start()
        self.addCleanup(p_enter.stop)
        self.addCleanup(p_exit.stop)

    @patch(f"{_SVC}.PraticheRepository")
    def test_get_competenze_ok(self, MockRepo):
        # Scopo: verifica che get_competenze_flussi restituisca i risultati.
        repo = MockRepo.return_value
        repo.list_competenze_flussi.return_value = [_mock_competenza_row()]

        result = pratiche_service.get_competenze_flussi()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["template_flusso_codice"], "VALUTAZIONE")

    @patch(f"{_SVC}.PraticheRepository")
    def test_crea_competenza_ok(self, MockRepo):
        # Scopo: verifica creazione riuscita.
        repo = MockRepo.return_value
        repo.create_competenza_flusso.return_value = 42

        result = pratiche_service.crea_competenza_flusso(
            template_flusso_id=5,
            unita_organizzativa_id=3,
            risorsa_umana_id=100,
        )
        self.assertEqual(result, 42)
        repo.create_competenza_flusso.assert_called_once()

    def test_crea_competenza_errore_template_zero(self):
        # Scopo: verifica errore per template_flusso_id <= 0.
        with self.assertRaises(ServiceError):
            pratiche_service.crea_competenza_flusso(
                template_flusso_id=0,
                unita_organizzativa_id=3,
                risorsa_umana_id=100,
            )

    @patch(f"{_SVC}.PraticheRepository")
    def test_elimina_competenza_ok(self, MockRepo):
        # Scopo: verifica eliminazione riuscita.
        repo = MockRepo.return_value
        repo.delete_competenza_flusso.return_value = True

        pratiche_service.elimina_competenza_flusso(42)
        repo.delete_competenza_flusso.assert_called_once_with(42)

    @patch(f"{_SVC}.PraticheRepository")
    def test_elimina_competenza_non_trovata(self, MockRepo):
        # Scopo: verifica errore se competenza non trovata.
        repo = MockRepo.return_value
        repo.delete_competenza_flusso.return_value = False

        with self.assertRaises(ServiceError):
            pratiche_service.elimina_competenza_flusso(42)
