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
 3a) test_get_cliente_propagates_evento_stato_corrente — Fase 4: fn DB risolve sosp/riatt
 3b) test_get_cliente_evento_stato_null_when_no_dates — entrambe NULL → output NULL
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
15) test_update_cliente_ok — aggiorna campi editabili
16) test_update_cliente_not_found — id inesistente → E_ANAG_NOT_FOUND
17) test_update_cliente_no_fields — nessun campo valido → E_ANAG_NOT_FOUND
18) test_guard_admin_globale_blocca_creazione_ba — admin globale + emittenti → E_BA_ADMIN_GLOBALE_VIETATO
19) test_guard_skip_quando_auth_user_id_none — contesto sistema → no check
20) test_guard_skip_quando_ba_preesistente — riuso BA → no check (no nuovo INSERT)
21) test_guard_passa_per_operatore_di_emittente — operatore con emittente → ok
22) test_db_trigger_error_propaga_codice — errore trigger DB propagato come ServiceError
23) test_crea_cliente_con_ba_categoria — F2-BE-04: ba_categoria_cliente_id passato al repo
24) test_crea_cliente_senza_ba_categoria_errore — F3-FE-04: categoria obbligatoria, no default
25) test_update_cliente_solo_categoria — F2-BE-04: PATCH solo ba_categoria_cliente_id -> update BA
26) test_update_cliente_categoria_e_campi — F2-BE-04: PATCH misto BA + cliente
27) test_update_cliente_categoria_invalida_zero — F2-BE-04: ba_categoria_cliente_id=0 -> VALIDAZIONE
28) test_update_cliente_categoria_invalida_bool — F2-BE-04: ba_categoria_cliente_id=True -> VALIDAZIONE
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
    # F3-FE-04: ba_categoria_cliente_id obbligatorio quando si crea un nuovo
    # BA (no default implicito). Le fixture includono un valore fittizio;
    # i test che riusano un BA pre-esistente possono ometterlo via override.
    payload = {
        "soggetto_id": FAKE_UUID,
        "utility_id": 10,
        "ba_categoria_cliente_id": 1,
    }
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
    def test_list_clienti_propaga_scope_emittente(self, mock_repo):
        """Refactor operatore-emittenti BE-3.5: il param emittente_ids
        passato al service deve raggiungere il repository senza
        modifiche (lista bigint[] o None)."""
        mock_repo.return_value.list_clienti.return_value = ([], 0)
        from apps.anagrafiche.services.clienti_service import ClientiService
        ClientiService().list_clienti(emittente_ids=[10, 20])
        kwargs = mock_repo.return_value.list_clienti.call_args.kwargs
        self.assertEqual(kwargs["emittente_ids"], [10, 20])

    @patch(CLI_REPO)
    def test_list_clienti_scope_none_bypass(self, mock_repo):
        """Superuser/admin globale: emittente_ids=None passa intatto
        e il repository non applica filtro scope."""
        mock_repo.return_value.list_clienti.return_value = ([], 0)
        from apps.anagrafiche.services.clienti_service import ClientiService
        ClientiService().list_clienti(emittente_ids=None)
        kwargs = mock_repo.return_value.list_clienti.call_args.kwargs
        self.assertIsNone(kwargs["emittente_ids"])

    @patch(CLI_REPO)
    def test_get_cliente_ok(self, mock_repo):
        """Dettaglio cliente completo."""
        mock_repo.return_value.get_cliente.return_value = {
            "id": 1, "soggetto_id": FAKE_UUID, "ragione_sociale_completa": "Rossi",
            "ba_codice": "BA-001", "stato_codice_interno": "AT", "stato_codice": "AT",
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

    @patch(CLI_REPO)
    def test_get_cliente_propagates_evento_stato_corrente(self, mock_repo):
        """Fase 4: i campi data_evento_stato/tipo_evento_stato risolti dalla
        fn DB anagrafiche.fn_get_evento_stato_corrente_cliente devono
        arrivare al frontend nel detail (sostituiscono il computed FE
        sosp vs riatt)."""
        mock_repo.return_value.get_cliente.return_value = {
            "id": 1,
            "data_sospensione": "2026-03-10",
            "data_riattivazione": "2026-04-05",
            # Campi risolti dal LATERAL JOIN sulla fn DB:
            "data_evento_stato": "2026-04-05",
            "tipo_evento_stato": "RIATTIVAZIONE",
        }
        from apps.anagrafiche.services.clienti_service import ClientiService
        result = ClientiService().get_cliente(1)
        self.assertEqual(result["data_evento_stato"], "2026-04-05")
        self.assertEqual(result["tipo_evento_stato"], "RIATTIVAZIONE")

    @patch(CLI_REPO)
    def test_get_cliente_evento_stato_null_when_no_dates(self, mock_repo):
        """Cliente senza sosp/riatt → fn DB ritorna (NULL, NULL)."""
        mock_repo.return_value.get_cliente.return_value = {
            "id": 1,
            "data_sospensione": None,
            "data_riattivazione": None,
            "data_evento_stato": None,
            "tipo_evento_stato": None,
        }
        from apps.anagrafiche.services.clienti_service import ClientiService
        result = ClientiService().get_cliente(1)
        self.assertIsNone(result["data_evento_stato"])
        self.assertIsNone(result["tipo_evento_stato"])


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


# =================================================================
# Update cliente
# =================================================================

class TestUpdateCliente(TestCase):

    @patch(CLI_REPO)
    def test_update_cliente_ok(self, mock_repo):
        """Aggiorna campi editabili — happy path (una sola fn madre atomica)."""
        repo = mock_repo.return_value
        repo.get_cliente.return_value = {"id": 1, "utility_id": 10}
        repo.update_cliente_atomico.return_value = {
            "categoria_aggiornata": False, "campi_aggiornati": True,
        }
        from apps.anagrafiche.services.clienti_service import ClientiService
        result = ClientiService().update_cliente(1, {
            "iva_id": 5, "cliente_pa": "S", "garanzia_importo": 500,
        })
        self.assertTrue(result["updated"])
        repo.update_cliente_atomico.assert_called_once_with(
            1,
            ba_categoria_cliente_id=None,
            cliente_fields={"iva_id": 5, "cliente_pa": "S", "garanzia_importo": 500},
        )

    @patch(CLI_REPO)
    def test_update_cliente_not_found(self, mock_repo):
        """Cliente inesistente → E_ANAG_NOT_FOUND."""
        mock_repo.return_value.get_cliente.return_value = None
        from apps.anagrafiche.services.clienti_service import ClientiService
        with self.assertRaises(ServiceError) as ctx:
            ClientiService().update_cliente(999, {"iva_id": 5})
        self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")

    @patch(CLI_REPO)
    def test_update_cliente_no_fields(self, mock_repo):
        """Nessun campo valido → E_ANAG_VALIDAZIONE (400): il cliente esiste (guard
        get_cliente), quindi 'niente da aggiornare' e' validazione, non not-found."""
        repo = mock_repo.return_value
        repo.get_cliente.return_value = {"id": 1, "utility_id": 10}
        repo.update_cliente_atomico.return_value = {
            "categoria_aggiornata": False, "campi_aggiornati": False,
        }
        from apps.anagrafiche.services.clienti_service import ClientiService
        with self.assertRaises(ServiceError) as ctx:
            ClientiService().update_cliente(1, {"campo_ignoto": "valore"})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")


# =================================================================
# F2-BE-04 — ba_categoria_cliente_id (pricing v5 STADIO 2)
# =================================================================


class TestBaCategoriaF2BE04(TestCase):

    def _setup_crea(self, mock_repo):
        repo = mock_repo.return_value
        repo.get_utility.return_value = _utility_manifatturiero()
        repo.get_or_create_ruolo_cliente.return_value = 50
        repo.create_istanza_fittizia.return_value = 100
        repo.create_billing_account.return_value = 200
        repo.create_cliente.return_value = 1
        return repo

    @patch(TX_ATOMIC)
    @patch(CLI_REPO)
    def test_crea_cliente_con_ba_categoria(self, mock_repo, _tx):
        """F2-BE-04: ba_categoria_cliente_id del payload passato al repo."""
        repo = self._setup_crea(mock_repo)
        from apps.anagrafiche.services.clienti_service import ClientiService
        ClientiService().crea_cliente(_base_payload(ba_categoria_cliente_id=7))
        kwargs = repo.create_billing_account.call_args.kwargs
        self.assertEqual(kwargs["categoria_cliente_id"], 7)

    @patch(TX_ATOMIC)
    @patch(CLI_REPO)
    def test_crea_cliente_senza_ba_categoria_errore(self, mock_repo, _tx):
        """F3-FE-04: ba_categoria_cliente_id omesso -> E_ANAG_VALIDAZIONE.
        Nessun default implicito: la categoria cliente e' dimensione
        commerciale e deve essere scelta esplicitamente."""
        self._setup_crea(mock_repo)
        from apps.anagrafiche.services.clienti_service import ClientiService
        payload = {"soggetto_id": FAKE_UUID, "utility_id": 10}
        with self.assertRaises(ServiceError) as ctx:
            ClientiService().crea_cliente(payload)
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        self.assertIn("ba_categoria_cliente_id", ctx.exception.message)

    @patch(CLI_REPO)
    def test_update_cliente_solo_categoria(self, mock_repo):
        """PATCH con solo ba_categoria_cliente_id -> fn madre con categoria, campi vuoti."""
        repo = mock_repo.return_value
        repo.get_cliente.return_value = {"id": 1, "billing_account_id": 200}
        repo.update_cliente_atomico.return_value = {
            "categoria_aggiornata": True, "campi_aggiornati": False,
        }
        from apps.anagrafiche.services.clienti_service import ClientiService
        result = ClientiService().update_cliente(1, {"ba_categoria_cliente_id": 9})
        self.assertTrue(result["updated"])
        repo.update_cliente_atomico.assert_called_once_with(
            1, ba_categoria_cliente_id=9, cliente_fields={},
        )

    @patch(CLI_REPO)
    def test_update_cliente_categoria_e_campi(self, mock_repo):
        """PATCH misto: categoria BA + campi cliente in un'unica fn madre atomica."""
        repo = mock_repo.return_value
        repo.get_cliente.return_value = {"id": 1, "billing_account_id": 200}
        repo.update_cliente_atomico.return_value = {
            "categoria_aggiornata": True, "campi_aggiornati": True,
        }
        from apps.anagrafiche.services.clienti_service import ClientiService
        ClientiService().update_cliente(1, {
            "ba_categoria_cliente_id": 9,
            "iva_id": 5,
        })
        repo.update_cliente_atomico.assert_called_once()
        kwargs = repo.update_cliente_atomico.call_args.kwargs
        self.assertEqual(kwargs["ba_categoria_cliente_id"], 9)
        # ba_categoria_cliente_id NON deve finire tra i campi cliente.
        self.assertNotIn("ba_categoria_cliente_id", kwargs["cliente_fields"])
        self.assertEqual(kwargs["cliente_fields"]["iva_id"], 5)

    @patch(CLI_REPO)
    def test_update_cliente_categoria_invalida_zero(self, mock_repo):
        """ba_categoria_cliente_id=0 -> E_ANAG_VALIDAZIONE."""
        repo = mock_repo.return_value
        repo.get_cliente.return_value = {"id": 1, "billing_account_id": 200}
        from apps.anagrafiche.services.clienti_service import ClientiService
        with self.assertRaises(ServiceError) as ctx:
            ClientiService().update_cliente(1, {"ba_categoria_cliente_id": 0})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(CLI_REPO)
    def test_update_cliente_categoria_invalida_bool(self, mock_repo):
        """ba_categoria_cliente_id=True rifiutato (bool trap)."""
        repo = mock_repo.return_value
        repo.get_cliente.return_value = {"id": 1, "billing_account_id": 200}
        from apps.anagrafiche.services.clienti_service import ClientiService
        with self.assertRaises(ServiceError) as ctx:
            ClientiService().update_cliente(1, {"ba_categoria_cliente_id": True})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")


# =================================================================
# Refactor operatore-emittenti — guard E_BA_ADMIN_GLOBALE_VIETATO
# =================================================================

class TestCreaClienteGuardEmittente(TestCase):
    """Test guard refactor operatore-emittenti (Q6): admin globale
    non puo' creare BA quando esistono emittenti fiscali."""

    def _setup_repo(self, mock_repo, can_create_ba: bool = True):
        repo = mock_repo.return_value
        repo.get_utility.return_value = _utility_manifatturiero()
        repo.get_or_create_ruolo_cliente.return_value = 50
        repo.create_istanza_fittizia.return_value = 100
        repo.create_billing_account.return_value = 200
        repo.create_cliente.return_value = 1
        repo.check_user_can_create_ba.return_value = can_create_ba
        return repo

    @patch(TX_ATOMIC)
    @patch(CLI_REPO)
    def test_guard_admin_globale_blocca_creazione_ba(self, mock_repo, _tx):
        """Admin globale + emittenti presenti → E_BA_ADMIN_GLOBALE_VIETATO,
        nessuna chiamata a create_billing_account."""
        repo = self._setup_repo(mock_repo, can_create_ba=False)
        from apps.anagrafiche.services.clienti_service import ClientiService
        with self.assertRaises(ServiceError) as ctx:
            ClientiService().crea_cliente(_base_payload(), auth_user_id=42)
        self.assertEqual(ctx.exception.code, "E_BA_ADMIN_GLOBALE_VIETATO")
        repo.check_user_can_create_ba.assert_called_once_with(42)
        # Early reject: nessuna scrittura DB
        repo.create_billing_account.assert_not_called()
        repo.create_istanza_fittizia.assert_not_called()
        repo.create_cliente.assert_not_called()

    @patch(TX_ATOMIC)
    @patch(CLI_REPO)
    def test_guard_skip_quando_auth_user_id_none(self, mock_repo, _tx):
        """Contesto di sistema (auth_user_id=None) → guard skippato,
        creazione procede (defense-in-depth via trigger DB)."""
        repo = self._setup_repo(mock_repo, can_create_ba=False)
        from apps.anagrafiche.services.clienti_service import ClientiService
        result = ClientiService().crea_cliente(_base_payload(), auth_user_id=None)
        self.assertEqual(result["id"], 1)
        repo.check_user_can_create_ba.assert_not_called()
        repo.create_billing_account.assert_called_once()

    @patch(TX_ATOMIC)
    @patch(CLI_REPO)
    def test_guard_skip_quando_ba_preesistente(self, mock_repo, _tx):
        """Se billing_account_id e' fornito (riuso da pratiche),
        non si crea un nuovo BA → niente guard."""
        repo = self._setup_repo(mock_repo, can_create_ba=False)
        repo.get_billing_account.return_value = _billing_account()
        repo.get_istanza.return_value = _istanza()
        from apps.anagrafiche.services.clienti_service import ClientiService
        ClientiService().crea_cliente(
            _base_payload(istanza_utility_id=100, billing_account_id=200),
            auth_user_id=42,
        )
        # Guard NON deve essere chiamato perche' non si crea nuovo BA
        repo.check_user_can_create_ba.assert_not_called()
        # E nessun create_billing_account perche' si riusa quello fornito
        repo.create_billing_account.assert_not_called()

    @patch(TX_ATOMIC)
    @patch(CLI_REPO)
    def test_guard_passa_per_operatore_di_emittente(self, mock_repo, _tx):
        """Operatore con riga in user_emittenti_fiscali → check_user_can_create_ba
        ritorna True → creazione BA procede."""
        repo = self._setup_repo(mock_repo, can_create_ba=True)
        from apps.anagrafiche.services.clienti_service import ClientiService
        result = ClientiService().crea_cliente(_base_payload(), auth_user_id=99)
        self.assertEqual(result["id"], 1)
        repo.check_user_can_create_ba.assert_called_once_with(99)
        repo.create_billing_account.assert_called_once()

    @patch(TX_ATOMIC)
    @patch(CLI_REPO)
    def test_db_trigger_error_propaga_codice(self, mock_repo, _tx):
        """Se il trigger DB solleva un'eccezione (defense-in-depth oltre
        il guard applicativo), la repository la propaga e il service
        lascia salire al middleware (ApiExceptionMiddleware) che la
        traduce via ErrorTranslator. Test: il side_effect del repo
        viene rilanciato senza essere mascherato."""
        repo = self._setup_repo(mock_repo, can_create_ba=True)
        # Simula il trigger DB che blocca con un'eccezione applicativa
        repo.create_billing_account.side_effect = RuntimeError(
            "ERROR: E_BA_ADMIN_GLOBALE_VIETATO ..."
        )
        from apps.anagrafiche.services.clienti_service import ClientiService
        with self.assertRaises(RuntimeError) as ctx:
            ClientiService().crea_cliente(_base_payload(), auth_user_id=99)
        # L'eccezione DB sale invariata; il middleware/translator la
        # estrae come E_BA_ADMIN_GLOBALE_VIETATO via _APP_ERROR_CODE_RE.
        self.assertIn("E_BA_ADMIN_GLOBALE_VIETATO", str(ctx.exception))
