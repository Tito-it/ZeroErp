# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per generazione_service (generazione cross-pratica).
#        Mock DB, compatibile CI senza database reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) GenerazioneServiceTests.test_genera_pratica_manuale_ok
2) GenerazioneServiceTests.test_genera_pratica_manuale_flusso_non_trovato
3) GenerazioneServiceTests.test_genera_pratica_manuale_errore_flusso_id_zero
4) GenerazioneServiceTests.test_genera_pratica_manuale_errore_regola_id_zero
5) GenerazioneServiceTests.test_get_regole_applicabili_ok
6) GenerazioneServiceTests.test_get_regole_applicabili_senza_template
7) GenerazioneServiceTests.test_get_pratiche_generate_ok
"""

from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.pratiche.services import generazione_service

_GEN_SVC = "apps.pratiche.services.generazione_service"
_ATOMIC = "django.db.transaction.Atomic"


def _mock_flusso_row(flusso_id: int = 1, *, template_flusso_id: int | None = 10) -> dict:
    return {
        "id": flusso_id,
        "pratica_id": 1,
        "template_flusso_id": template_flusso_id,
        "stato_id": 1,
        "flusso_padre_id": None,
        "risorsa_umana_id": None,
        "unita_organizzativa_id": None,
        "sequenza": 0,
        "esito": None,
        "note_esito": None,
        "data_scadenza": None,
        "meta": {},
        "data_insert": "2026-03-04T10:00:00+00:00",
        "user_insert": "test_user",
    }


def _mock_regola_row(regola_id: int = 1) -> dict:
    return {
        "id": regola_id,
        "template_flusso_origine_id": 10,
        "tipo_prestazione_dest_id": 5,
        "template_flusso_dest_id": None,
        "esito_richiesto": "POSITIVO",
        "auto": False,
        "attivo": True,
        "descrizione": "Regola test",
        "meta": {},
    }


class GenerazioneServiceTests(SimpleTestCase):

    # Scopo: Disabilita transaction.atomic per tutti i test (no DB reale).
    def setUp(self) -> None:
        p_enter = patch(f"{_ATOMIC}.__enter__", return_value=None)
        p_exit = patch(f"{_ATOMIC}.__exit__", return_value=False)
        p_enter.start()
        p_exit.start()
        self.addCleanup(p_enter.stop)
        self.addCleanup(p_exit.stop)

    # Scopo: Verifica generazione manuale pratica con esito positivo.
    @patch(f"{_GEN_SVC}.GenerazioneRepository")
    @patch(f"{_GEN_SVC}.PraticheRepository")
    def test_genera_pratica_manuale_ok(self, MockPratRepo, MockGenRepo):
        prat_repo = MockPratRepo.return_value
        prat_repo.get_flusso.return_value = _mock_flusso_row(1)

        gen_repo = MockGenRepo.return_value
        gen_repo.genera_pratica_manuale.return_value = 100

        result = generazione_service.genera_pratica_manuale(1, 5)

        self.assertEqual(result, 100)
        gen_repo.genera_pratica_manuale.assert_called_once_with(1, 5)

    # Scopo: Verifica errore quando il flusso non esiste.
    @patch(f"{_GEN_SVC}.PraticheRepository")
    def test_genera_pratica_manuale_flusso_non_trovato(self, MockPratRepo):
        prat_repo = MockPratRepo.return_value
        prat_repo.get_flusso.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            generazione_service.genera_pratica_manuale(99, 5)
        self.assertEqual(ctx.exception.code, "E_FLUSSO_NOT_FOUND")

    # Scopo: Verifica errore se flusso_id <= 0.
    def test_genera_pratica_manuale_errore_flusso_id_zero(self):
        with self.assertRaises(ServiceError) as ctx:
            generazione_service.genera_pratica_manuale(0, 5)
        self.assertEqual(ctx.exception.code, "E_INVALID_ID")

    # Scopo: Verifica errore se regola_id <= 0.
    def test_genera_pratica_manuale_errore_regola_id_zero(self):
        with self.assertRaises(ServiceError) as ctx:
            generazione_service.genera_pratica_manuale(1, 0)
        self.assertEqual(ctx.exception.code, "E_INVALID_ID")

    # Scopo: Verifica lista regole applicabili con template flusso.
    @patch(f"{_GEN_SVC}.GenerazioneRepository")
    @patch(f"{_GEN_SVC}.PraticheRepository")
    def test_get_regole_applicabili_ok(self, MockPratRepo, MockGenRepo):
        prat_repo = MockPratRepo.return_value
        prat_repo.get_flusso.return_value = _mock_flusso_row(1, template_flusso_id=10)

        gen_repo = MockGenRepo.return_value
        gen_repo.list_regole_generazione.return_value = [_mock_regola_row()]

        result = generazione_service.get_regole_applicabili(1)

        self.assertEqual(len(result), 1)
        gen_repo.list_regole_generazione.assert_called_once_with(10)

    # Scopo: Verifica lista vuota quando flusso non ha template.
    @patch(f"{_GEN_SVC}.PraticheRepository")
    def test_get_regole_applicabili_senza_template(self, MockPratRepo):
        prat_repo = MockPratRepo.return_value
        prat_repo.get_flusso.return_value = _mock_flusso_row(1, template_flusso_id=None)

        result = generazione_service.get_regole_applicabili(1)

        self.assertEqual(result, [])

    # Scopo: Verifica lista pratiche generate delegata al repository.
    @patch(f"{_GEN_SVC}.GenerazioneRepository")
    def test_get_pratiche_generate_ok(self, MockGenRepo):
        gen_repo = MockGenRepo.return_value
        gen_repo.get_pratiche_generate_da_flusso.return_value = []

        result = generazione_service.get_pratiche_generate(1)

        self.assertEqual(result, [])
        gen_repo.get_pratiche_generate_da_flusso.assert_called_once_with(1)
