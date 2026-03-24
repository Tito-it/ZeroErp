# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per ClientiService — creazione manuale,
#        creazione con entita' pre-esistenti, validazioni, guard utility.
#        Mock repository, CI-compatible (no DB reale).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_list_clienti_ok — happy path lista paginata
 2) test_get_cliente_ok — dettaglio completo
 3) test_get_cliente_not_found — id inesistente → E_ANAG_NOT_FOUND
 4) test_crea_cliente_manuale_ok — creazione manuale completa (genera istanza + BA)
 5) test_crea_cliente_manuale_con_indirizzo — creazione manuale con indirizzo facoltativo
 6) test_crea_cliente_manuale_utility_pdp_bloccata — utility richiede_pdp=true → errore
 7) test_crea_cliente_con_istanza_preesistente — riusa istanza da pratiche
 8) test_crea_cliente_con_istanza_e_ba_preesistenti — riusa istanza + BA da pratiche
 9) test_crea_cliente_istanza_soggetto_mismatch — istanza di altro soggetto → errore
10) test_crea_cliente_ba_istanza_mismatch — BA di altra istanza → errore
11) test_crea_cliente_missing_soggetto — soggetto_id mancante → errore
12) test_crea_cliente_missing_utility — utility_id mancante → errore
13) test_crea_cliente_utility_non_trovata — utility inesistente → errore
14) test_crea_cliente_duplicato_istanza — IntegrityError UNIQUE istanza → E_ANAG_DUPLICATO
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.db import IntegrityError

from apps.core.services.service_errors import ServiceError


CLI_REPO = "apps.anagrafiche.services.clienti_service.ClientiRepository"
TX_ATOMIC = "apps.anagrafiche.services.clienti_service.transaction.atomic"

FAKE_UUID = "019bac81-3f96-7ce8-a086-7e0bd0a2fec1"

# --- Fixture helpers ---

def _utility_manifatturiero():
    return {"id": 10, "descrizione": "Manifatturiero", "codice": "MANIF", "richiede_pdp": False}

def _utility_gas():
    return {"id": 1, "descrizione": "Gas", "codice": "GAS", "richiede_pdp": True}

def _istanza(soggetto_id=FAKE_UUID, utility_id=10):
    return {"id": 100, "soggetto_id": soggetto_id, "utility_id": utility_id,
            "fittizia": True, "indirizzo_dettaglio_id": None}

def _billing_account(istanza_utility_id=100):
    return {"id": 200, "istanza_utility_id": istanza_utility_id,
            "soggetto_ruolo_id": 50, "utility_id": 10, "codice": "BA-001"}

def _base_payload(**overrides):
    payload = {"soggetto_id": FAKE_UUID, "utility_id": 10}
    payload.update(overrides)
    return payload


# =================================================================
# Lista e dettaglio
# =================================================================

class TestClientiListDetail(TestCase):

    @patch(CLI_REPO)
    def test_list_clienti_ok(self, mock_repo):
        """Happy path: lista paginata clienti."""
        mock_repo.return_value.list_clienti.return_value = (
            [{"id": 1, "ragione_sociale_completa": "Rossi Mario", "codice": "BA-001"}], 1
        )
        from apps.anagrafiche.services.clienti_service import ClientiService
        results, total = ClientiService().list_clienti()
        self.assertEqual(total, 1)
        self.assertEqual(results[0]["codice"], "BA-001")

    @patch(CLI_REPO)
    def test_get_cliente_ok(self, mock_repo):
        """Dettaglio cliente completo."""
        mock_repo.return_value.get_cliente.return_value = {
            "id": 1, "soggetto_id": FAKE_UUID, "ragione_sociale_completa": "Rossi",
            "ba_codice": "BA-001", "stato_codice": "AT",
        }
        from apps.anagrafiche.services.clienti_service import ClientiService
        result = ClientiService().get_cliente(1)
        self.assertEqual(result["ba_codice"], "BA-001")

    @patch(CLI_REPO)
    def test_get_cliente_not_found(self, mock_repo):
        """Cliente inesistente → E_ANAG_NOT_FOUND."""
        mock_repo.return_value.get_cliente.return_value = None
        from apps.anagrafiche.services.clienti_service import ClientiService
        with self.assertRaises(ServiceError) as ctx:
            ClientiService().get_cliente(999)
        self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")


# =================================================================
# Creazione manuale (genera istanza + BA)
# =================================================================

class TestCreaClienteManuale(TestCase):

    def _setup_repo(self, mock_repo):
        repo = mock_repo.return_value
        repo.get_utility.return_value = _utility_manifatturiero()
        repo.get_or_create_ruolo_cliente.return_value = 50
        repo.create_istanza_fittizia.return_value = 100
        repo.create_billing_account.return_value = 200
        repo.create_cliente.return_value = 1
        return repo

    @patch(TX_ATOMIC)
    @patch(CLI_REPO)
    def test_crea_cliente_manuale_ok(self, mock_repo, _tx):
        """Creazione manuale: genera istanza fittizia + BA + cliente."""
        repo = self._setup_repo(mock_repo)
        from apps.anagrafiche.services.clienti_service import ClientiService
        result = ClientiService().crea_cliente(_base_payload())
        self.assertEqual(result["id"], 1)
        self.assertEqual(result["istanza_utility_id"], 100)
        self.assertEqual(result["billing_account_id"], 200)
        repo.create_istanza_fittizia.assert_called_once()
        repo.create_billing_account.assert_called_once()
        repo.create_cliente.assert_called_once()

    @patch(TX_ATOMIC)
    @patch(CLI_REPO)
    def test_crea_cliente_manuale_con_indirizzo(self, mock_repo, _tx):
        """Creazione manuale con indirizzo facoltativo."""
        repo = self._setup_repo(mock_repo)
        from apps.anagrafiche.services.clienti_service import ClientiService
        ClientiService().crea_cliente(_base_payload(indirizzo_dettaglio_id=42))
        kwargs = repo.create_istanza_fittizia.call_args.kwargs
        self.assertEqual(kwargs["indirizzo_dettaglio_id"], 42)
        # utility_id non deve essere passato a create_istanza_fittizia
        self.assertNotIn("utility_id", kwargs)

    @patch(CLI_REPO)
    def test_crea_cliente_manuale_utility_pdp_bloccata(self, mock_repo):
        """Utility con richiede_pdp=true → creazione manuale bloccata."""
        mock_repo.return_value.get_utility.return_value = _utility_gas()
        from apps.anagrafiche.services.clienti_service import ClientiService
        with self.assertRaises(ServiceError) as ctx:
            ClientiService().crea_cliente(_base_payload(utility_id=1))
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        self.assertIn("PDP", ctx.exception.message)


# =================================================================
# Creazione con entita' pre-esistenti (da pratiche)
# =================================================================

class TestCreaClientePreesistenti(TestCase):

    @patch(TX_ATOMIC)
    @patch(CLI_REPO)
    def test_crea_cliente_con_istanza_preesistente(self, mock_repo, _tx):
        """Riusa istanza da pratiche, genera solo BA + cliente."""
        repo = mock_repo.return_value
        repo.get_utility.return_value = _utility_gas()
        repo.get_or_create_ruolo_cliente.return_value = 50
        repo.get_istanza.return_value = _istanza(utility_id=1)
        repo.create_billing_account.return_value = 200
        repo.create_cliente.return_value = 1
        from apps.anagrafiche.services.clienti_service import ClientiService
        result = ClientiService().crea_cliente(
            _base_payload(utility_id=1, istanza_utility_id=100))
        self.assertEqual(result["istanza_utility_id"], 100)
        repo.create_istanza_fittizia.assert_not_called()
        repo.create_billing_account.assert_called_once()

    @patch(TX_ATOMIC)
    @patch(CLI_REPO)
    def test_crea_cliente_con_istanza_e_ba_preesistenti(self, mock_repo, _tx):
        """Riusa istanza + BA da pratiche, genera solo cliente."""
        repo = mock_repo.return_value
        repo.get_utility.return_value = _utility_gas()
        repo.get_or_create_ruolo_cliente.return_value = 50
        repo.get_istanza.return_value = _istanza(utility_id=1)
        repo.get_billing_account.return_value = _billing_account()
        repo.create_cliente.return_value = 1
        from apps.anagrafiche.services.clienti_service import ClientiService
        result = ClientiService().crea_cliente(
            _base_payload(utility_id=1, istanza_utility_id=100, billing_account_id=200))
        repo.create_istanza_fittizia.assert_not_called()
        repo.create_billing_account.assert_not_called()
        repo.create_cliente.assert_called_once()
        self.assertEqual(result["id"], 1)


# =================================================================
# Validazione entita' pre-esistenti
# =================================================================

class TestCreaClienteValidazione(TestCase):

    @patch(TX_ATOMIC)
    @patch(CLI_REPO)
    def test_crea_cliente_istanza_soggetto_mismatch(self, mock_repo, _tx):
        """Istanza di altro soggetto → errore."""
        repo = mock_repo.return_value
        repo.get_utility.return_value = _utility_gas()
        repo.get_or_create_ruolo_cliente.return_value = 50
        repo.get_istanza.return_value = _istanza(soggetto_id="altro-uuid")
        from apps.anagrafiche.services.clienti_service import ClientiService
        with self.assertRaises(ServiceError) as ctx:
            ClientiService().crea_cliente(
                _base_payload(utility_id=1, istanza_utility_id=100))
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        self.assertIn("soggetto", ctx.exception.message)

    @patch(TX_ATOMIC)
    @patch(CLI_REPO)
    def test_crea_cliente_ba_istanza_mismatch(self, mock_repo, _tx):
        """BA di altra istanza → errore."""
        repo = mock_repo.return_value
        repo.get_utility.return_value = _utility_gas()
        repo.get_or_create_ruolo_cliente.return_value = 50
        repo.get_istanza.return_value = _istanza(utility_id=1)
        repo.get_billing_account.return_value = _billing_account(istanza_utility_id=999)
        from apps.anagrafiche.services.clienti_service import ClientiService
        with self.assertRaises(ServiceError) as ctx:
            ClientiService().crea_cliente(
                _base_payload(utility_id=1, istanza_utility_id=100, billing_account_id=200))
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        self.assertIn("billing account", ctx.exception.message)


# =================================================================
# Validazione input obbligatori
# =================================================================

class TestCreaClienteInputMancanti(TestCase):

    @patch(CLI_REPO)
    def test_crea_cliente_missing_soggetto(self, mock_repo):
        """soggetto_id mancante → errore."""
        from apps.anagrafiche.services.clienti_service import ClientiService
        with self.assertRaises(ServiceError) as ctx:
            ClientiService().crea_cliente({"utility_id": 10})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(CLI_REPO)
    def test_crea_cliente_missing_utility(self, mock_repo):
        """utility_id mancante → errore."""
        from apps.anagrafiche.services.clienti_service import ClientiService
        with self.assertRaises(ServiceError) as ctx:
            ClientiService().crea_cliente({"soggetto_id": FAKE_UUID})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(CLI_REPO)
    def test_crea_cliente_utility_non_trovata(self, mock_repo):
        """Utility inesistente → errore."""
        mock_repo.return_value.get_utility.return_value = None
        from apps.anagrafiche.services.clienti_service import ClientiService
        with self.assertRaises(ServiceError) as ctx:
            ClientiService().crea_cliente(_base_payload())
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        self.assertIn("Utility", ctx.exception.message)


# =================================================================
# Duplicato
# =================================================================

class TestCreaClienteDuplicato(TestCase):

    @patch(TX_ATOMIC)
    @patch(CLI_REPO)
    def test_crea_cliente_duplicato_istanza(self, mock_repo, _tx):
        """UNIQUE istanza violato → E_ANAG_DUPLICATO."""
        repo = mock_repo.return_value
        repo.get_utility.return_value = _utility_manifatturiero()
        repo.get_or_create_ruolo_cliente.return_value = 50
        repo.create_istanza_fittizia.return_value = 100
        repo.create_billing_account.return_value = 200
        repo.create_cliente.side_effect = IntegrityError("uq_clienti_istanza_utility")
        from apps.anagrafiche.services.clienti_service import ClientiService
        with self.assertRaises(ServiceError) as ctx:
            ClientiService().crea_cliente(_base_payload())
        self.assertEqual(ctx.exception.code, "E_ANAG_DUPLICATO")
