# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per BillingAccountService — lookup ricco BA.
#        Mock del repository, nessun accesso DB (compatibilita' CI).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_search_lookup_ok — ricerca valida con risultati
 2) test_search_lookup_query_too_short — query < 2 char rifiutata
 3) test_search_lookup_query_empty — query vuota rifiutata
 4) test_search_lookup_whitespace_trimmed — spazi iniziali/finali rimossi
 5) test_search_lookup_limit_cap — limit > 50 capped a 50
 6) test_search_lookup_limit_default — limit None o <=0 usa default 20
 7) test_search_lookup_utility_filter_passed — utility_id passato al repo
 8) test_search_lookup_emittente_scope_passed — scope emittente propagato
 9) test_search_lookup_solo_validi_default — default true
10) test_search_lookup_no_results — zero risultati
11) test_get_lookup_by_id_ok — restore BA esistente
12) test_get_lookup_by_id_not_found — BA inesistente solleva E_ANAG_NOT_FOUND
13) test_get_lookup_by_id_invalid_id — id 0 o negativo rifiutato
14) test_get_lookup_by_id_bool_rejected — bool rifiutato come id
"""

from unittest import TestCase
from unittest.mock import patch

from apps.core.services.service_errors import ServiceError

_REPO = "apps.anagrafiche.services.billing_account_service.BillingAccountRepository"

_FAKE_ROW = {
    "id": 123,
    "codice": "BA-000123",
    "parent_account_id": None,
    "parent_codice": None,
    "utility_id": 1,
    "utility_codice": "GAS",
    "utility_descrizione": "Gas naturale",
    "soggetto_ruolo_id": 55,
    "ragione_sociale_completa": "Rossi Mario",
    "id_fiscale": "RSSMRA80A01H501U",
    "istanza_utility_id": 900,
    "istanza_fittizia": False,
    "pdp": "IT001E00012345",
    "valido_dal": None,
    "valido_al": None,
}


class TestBillingAccountSearchLookup(TestCase):
    """Test search_lookup — validazioni + propagazione parametri."""

    @patch(_REPO)
    def test_search_lookup_ok(self, mock_repo):
        """Ricerca valida con risultati."""
        repo = mock_repo.return_value
        repo.search_lookup.return_value = ([_FAKE_ROW], 1)
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        result = BillingAccountService().search_lookup(q="Rossi")
        self.assertEqual(result["total_count"], 1)
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["results"][0]["id"], 123)
        self.assertEqual(result["limit"], 20)

    @patch(_REPO)
    def test_search_lookup_query_too_short(self, mock_repo):
        """q < 2 char solleva E_ANAG_VALIDAZIONE senza chiamare il repo."""
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        with self.assertRaises(ServiceError) as ctx:
            BillingAccountService().search_lookup(q="R")
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        mock_repo.return_value.search_lookup.assert_not_called()

    @patch(_REPO)
    def test_search_lookup_query_empty(self, mock_repo):
        """q vuota solleva E_ANAG_VALIDAZIONE."""
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        with self.assertRaises(ServiceError):
            BillingAccountService().search_lookup(q="")
        mock_repo.return_value.search_lookup.assert_not_called()

    @patch(_REPO)
    def test_search_lookup_whitespace_trimmed(self, mock_repo):
        """Spazi iniziali/finali rimossi prima della validazione."""
        repo = mock_repo.return_value
        repo.search_lookup.return_value = ([], 0)
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        BillingAccountService().search_lookup(q="  BA  ")
        # Verifica che al repo sia passato il trimmed "BA".
        _, kwargs = repo.search_lookup.call_args
        self.assertEqual(kwargs["q"], "BA")

    @patch(_REPO)
    def test_search_lookup_limit_cap(self, mock_repo):
        """limit > 50 viene capped a 50."""
        repo = mock_repo.return_value
        repo.search_lookup.return_value = ([], 0)
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        result = BillingAccountService().search_lookup(q="Rossi", limit=200)
        self.assertEqual(result["limit"], 50)
        _, kwargs = repo.search_lookup.call_args
        self.assertEqual(kwargs["limit"], 50)

    @patch(_REPO)
    def test_search_lookup_limit_default(self, mock_repo):
        """limit <= 0 o None usa default 20."""
        repo = mock_repo.return_value
        repo.search_lookup.return_value = ([], 0)
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        result_zero = BillingAccountService().search_lookup(q="Rossi", limit=0)
        self.assertEqual(result_zero["limit"], 20)
        result_none = BillingAccountService().search_lookup(q="Rossi", limit=None)  # type: ignore[arg-type]
        self.assertEqual(result_none["limit"], 20)

    @patch(_REPO)
    def test_search_lookup_utility_filter_passed(self, mock_repo):
        """utility_id viene propagato al repository."""
        repo = mock_repo.return_value
        repo.search_lookup.return_value = ([], 0)
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        BillingAccountService().search_lookup(q="Rossi", utility_id=7)
        _, kwargs = repo.search_lookup.call_args
        self.assertEqual(kwargs["utility_id"], 7)

    @patch(_REPO)
    def test_search_lookup_emittente_scope_passed(self, mock_repo):
        """emittente_ids viene propagato al repository."""
        repo = mock_repo.return_value
        repo.search_lookup.return_value = ([], 0)
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        BillingAccountService().search_lookup(q="Rossi", emittente_ids=[10, 20])
        _, kwargs = repo.search_lookup.call_args
        self.assertEqual(kwargs["emittente_ids"], [10, 20])

    @patch(_REPO)
    def test_search_lookup_solo_validi_default(self, mock_repo):
        """solo_validi default True quando non specificato."""
        repo = mock_repo.return_value
        repo.search_lookup.return_value = ([], 0)
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        BillingAccountService().search_lookup(q="Rossi")
        _, kwargs = repo.search_lookup.call_args
        self.assertIs(kwargs["solo_validi"], True)

    @patch(_REPO)
    def test_search_lookup_no_results(self, mock_repo):
        """Zero risultati restituisce results vuoto e total_count 0."""
        repo = mock_repo.return_value
        repo.search_lookup.return_value = ([], 0)
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        result = BillingAccountService().search_lookup(q="NoMatch")
        self.assertEqual(result["results"], [])
        self.assertEqual(result["total_count"], 0)


class TestBillingAccountGetLookupById(TestCase):
    """Test get_lookup_by_id — restore per edit."""

    @patch(_REPO)
    def test_get_lookup_by_id_ok(self, mock_repo):
        """Restore BA esistente."""
        repo = mock_repo.return_value
        repo.get_lookup_by_id.return_value = _FAKE_ROW
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        result = BillingAccountService().get_lookup_by_id(123)
        self.assertEqual(result["id"], 123)
        self.assertEqual(result["codice"], "BA-000123")

    @patch(_REPO)
    def test_get_lookup_by_id_not_found(self, mock_repo):
        """BA inesistente solleva E_ANAG_NOT_FOUND."""
        repo = mock_repo.return_value
        repo.get_lookup_by_id.return_value = None
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        with self.assertRaises(ServiceError) as ctx:
            BillingAccountService().get_lookup_by_id(9999)
        self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")

    @patch(_REPO)
    def test_get_lookup_by_id_invalid_id(self, mock_repo):
        """id <= 0 rifiutato con E_ANAG_VALIDAZIONE."""
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        with self.assertRaises(ServiceError) as ctx:
            BillingAccountService().get_lookup_by_id(0)
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        mock_repo.return_value.get_lookup_by_id.assert_not_called()

    @patch(_REPO)
    def test_get_lookup_by_id_bool_rejected(self, mock_repo):
        """Un bool (True/False) non e' un id valido anche se Python lo tratta come int."""
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        with self.assertRaises(ServiceError) as ctx:
            BillingAccountService().get_lookup_by_id(True)  # type: ignore[arg-type]
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        mock_repo.return_value.get_lookup_by_id.assert_not_called()
