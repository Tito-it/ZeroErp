# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per sospensione/riattivazione pratiche e flussi.
#        Mock DB, compatibile CI senza database reale.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) SospensioniServiceTests.test_sospendi_pratica_ok
2) SospensioniServiceTests.test_sospendi_pratica_errore_id_zero
3) SospensioniServiceTests.test_sospendi_pratica_errore_motivo_vuoto
4) SospensioniServiceTests.test_sospendi_pratica_errore_gia_sospesa
5) SospensioniServiceTests.test_riattiva_pratica_ok
6) SospensioniServiceTests.test_riattiva_pratica_errore_id_zero
7) SospensioniServiceTests.test_riattiva_pratica_errore_nessuna_sospensione
8) SospensioniServiceTests.test_sospendi_flusso_ok
9) SospensioniServiceTests.test_sospendi_flusso_errore_id_zero
10) SospensioniServiceTests.test_sospendi_flusso_errore_motivo_vuoto
11) SospensioniServiceTests.test_sospendi_flusso_errore_ownership
12) SospensioniServiceTests.test_sospendi_flusso_errore_gia_sospeso
13) SospensioniServiceTests.test_riattiva_flusso_ok
14) SospensioniServiceTests.test_riattiva_flusso_errore_nessuna_sospensione
15) SospensioniServiceTests.test_get_sospensioni_ok
16) SospensioniServiceTests.test_get_calcoli_tempo_ok
"""

from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.pratiche.services import pratiche_service

_SVC = "apps.pratiche.services.pratiche_service"
_ATOMIC = "django.db.transaction.Atomic"


def _mock_flusso_row(flusso_id: int = 10, pratica_id: int = 1) -> dict:
    return {
        "id": flusso_id,
        "pratica_id": pratica_id,
        "template_flusso_id": 5,
        "stato_id": 2,
        "flusso_padre_id": None,
        "risorsa_umana_id": None,
        "unita_organizzativa_id": None,
        "sequenza": 0,
        "esito": None,
        "note_esito": None,
        "data_scadenza": None,
        "meta": {},
        "data_insert": "2026-03-06T10:00:00+00:00",
        "user_insert": "test",
    }


def _mock_sospensione_row(sospensione_id: int = 100) -> dict:
    return {
        "id": sospensione_id,
        "pratica_id": 1,
        "flusso_id": None,
        "data_inizio": "2026-03-06T10:00:00+00:00",
        "data_fine": None,
        "data_riattivazione_prevista": None,
        "motivo": "Test motivo",
        "data_insert": "2026-03-06T10:00:00+00:00",
        "user_insert": "test",
        "data_update": None,
        "user_update": None,
    }


class SospensioniServiceTests(SimpleTestCase):

    # Scopo: Disabilita transaction.atomic per tutti i test (no DB reale).
    def setUp(self) -> None:
        p_enter = patch(f"{_ATOMIC}.__enter__", return_value=None)
        p_exit = patch(f"{_ATOMIC}.__exit__", return_value=False)
        p_enter.start()
        p_exit.start()
        self.addCleanup(p_enter.stop)
        self.addCleanup(p_exit.stop)

    # -- SOSPENDI PRATICA ------------------------------------------------

    # Scopo: Verifica sospensione pratica con esito positivo.
    @patch(f"{_SVC}.PraticheRepository")
    def test_sospendi_pratica_ok(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_sospensione_attiva_pratica.return_value = None
        repo.create_sospensione.return_value = 100

        result = pratiche_service.sospendi_pratica(1, "Attesa documenti")

        self.assertEqual(result, 100)
        repo.update_stato_pratica.assert_called_once_with(1, "SOSPESA")
        repo.create_sospensione.assert_called_once_with(
            1, "Attesa documenti",
            data_riattivazione_prevista=None,
        )

    # Scopo: Verifica errore se pratica_id <= 0.
    def test_sospendi_pratica_errore_id_zero(self):
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.sospendi_pratica(0, "motivo")
        self.assertEqual(ctx.exception.code, "E_INVALID_ID")

    # Scopo: Verifica errore se motivo e' vuoto.
    def test_sospendi_pratica_errore_motivo_vuoto(self):
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.sospendi_pratica(1, "")
        self.assertEqual(ctx.exception.code, "E_PRATICA_VALIDATION")

    # Scopo: Verifica errore se pratica ha gia' sospensione attiva.
    @patch(f"{_SVC}.PraticheRepository")
    def test_sospendi_pratica_errore_gia_sospesa(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_sospensione_attiva_pratica.return_value = _mock_sospensione_row()

        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.sospendi_pratica(1, "motivo")
        self.assertEqual(ctx.exception.code, "E_PRATICA_VALIDATION")

    # -- RIATTIVA PRATICA ------------------------------------------------

    # Scopo: Verifica riattivazione pratica con esito positivo.
    @patch(f"{_SVC}.PraticheRepository")
    def test_riattiva_pratica_ok(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_sospensione_attiva_pratica.return_value = _mock_sospensione_row(100)

        pratiche_service.riattiva_pratica(1)

        repo.update_stato_pratica.assert_called_once_with(1, "APERTA")
        repo.chiudi_sospensione.assert_called_once_with(100)

    # Scopo: Verifica errore se pratica_id <= 0.
    def test_riattiva_pratica_errore_id_zero(self):
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.riattiva_pratica(0)
        self.assertEqual(ctx.exception.code, "E_INVALID_ID")

    # Scopo: Verifica errore se pratica non ha sospensione attiva.
    @patch(f"{_SVC}.PraticheRepository")
    def test_riattiva_pratica_errore_nessuna_sospensione(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_sospensione_attiva_pratica.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.riattiva_pratica(1)
        self.assertEqual(ctx.exception.code, "E_PRATICA_VALIDATION")

    # -- SOSPENDI FLUSSO -------------------------------------------------

    # Scopo: Verifica sospensione flusso con esito positivo.
    @patch(f"{_SVC}.PraticheRepository")
    def test_sospendi_flusso_ok(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(10, 1)
        repo.get_sospensione_attiva_flusso.return_value = None
        repo.create_sospensione.return_value = 200

        result = pratiche_service.sospendi_flusso(1, 10, "Attesa tecnico")

        self.assertEqual(result, 200)
        repo.update_stato_flusso.assert_called_once_with(10, "SOSPESO")
        repo.create_sospensione.assert_called_once_with(
            1, "Attesa tecnico",
            flusso_id=10,
            data_riattivazione_prevista=None,
        )

    # Scopo: Verifica errore se flusso_id <= 0.
    def test_sospendi_flusso_errore_id_zero(self):
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.sospendi_flusso(1, 0, "motivo")
        self.assertEqual(ctx.exception.code, "E_INVALID_ID")

    # Scopo: Verifica errore se motivo e' vuoto.
    def test_sospendi_flusso_errore_motivo_vuoto(self):
        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.sospendi_flusso(1, 10, "  ")
        self.assertEqual(ctx.exception.code, "E_FLUSSO_VALIDATION")

    # Scopo: Verifica errore se flusso non appartiene alla pratica.
    @patch(f"{_SVC}.PraticheRepository")
    def test_sospendi_flusso_errore_ownership(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(10, 99)

        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.sospendi_flusso(1, 10, "motivo")
        self.assertEqual(ctx.exception.code, "E_FLUSSO_OWNERSHIP")

    # Scopo: Verifica errore se flusso ha gia' sospensione attiva.
    @patch(f"{_SVC}.PraticheRepository")
    def test_sospendi_flusso_errore_gia_sospeso(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(10, 1)
        sosp = _mock_sospensione_row()
        sosp["flusso_id"] = 10
        repo.get_sospensione_attiva_flusso.return_value = sosp

        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.sospendi_flusso(1, 10, "motivo")
        self.assertEqual(ctx.exception.code, "E_FLUSSO_VALIDATION")

    # -- RIATTIVA FLUSSO -------------------------------------------------

    # Scopo: Verifica riattivazione flusso con esito positivo.
    @patch(f"{_SVC}.PraticheRepository")
    def test_riattiva_flusso_ok(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(10, 1)
        sosp = _mock_sospensione_row(200)
        sosp["flusso_id"] = 10
        repo.get_sospensione_attiva_flusso.return_value = sosp

        pratiche_service.riattiva_flusso(1, 10)

        repo.update_stato_flusso.assert_called_once_with(10, "IN_CORSO")
        repo.chiudi_sospensione.assert_called_once_with(200)

    # Scopo: Verifica errore se flusso non ha sospensione attiva.
    @patch(f"{_SVC}.PraticheRepository")
    def test_riattiva_flusso_errore_nessuna_sospensione(self, MockRepo):
        repo = MockRepo.return_value
        repo.get_flusso.return_value = _mock_flusso_row(10, 1)
        repo.get_sospensione_attiva_flusso.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            pratiche_service.riattiva_flusso(1, 10)
        self.assertEqual(ctx.exception.code, "E_FLUSSO_VALIDATION")

    # -- LETTURA SOSPENSIONI / CALCOLI TEMPO -----------------------------

    # Scopo: Verifica delega a repository per lista sospensioni.
    @patch(f"{_SVC}.PraticheRepository")
    def test_get_sospensioni_ok(self, MockRepo):
        repo = MockRepo.return_value
        repo.list_sospensioni.return_value = [_mock_sospensione_row()]

        items = pratiche_service.get_sospensioni(1)

        self.assertEqual(len(items), 1)
        repo.list_sospensioni.assert_called_once_with(1)

    # Scopo: Verifica delega a repository per lista calcoli tempo.
    @patch(f"{_SVC}.PraticheRepository")
    def test_get_calcoli_tempo_ok(self, MockRepo):
        repo = MockRepo.return_value
        calcolo = {
            "id": 1, "pratica_id": 1, "flusso_da_id": 10, "flusso_a_id": 20,
            "formula_tempo_id": 5, "data_inizio_calcolo": "2026-03-06",
            "data_fine_calcolo": None, "giorni_lordi": None,
            "giorni_sospensione": None, "giorni_netti": None,
            "giorni_formula": 30, "sforato": None,
        }
        repo.list_calcoli_tempo.return_value = [calcolo]

        items = pratiche_service.get_calcoli_tempo(1)

        self.assertEqual(len(items), 1)
        repo.list_calcoli_tempo.assert_called_once_with(1)
