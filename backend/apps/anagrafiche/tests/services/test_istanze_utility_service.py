# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per IstanzeUtilityService — lookup ricco istanze.
#        Mock del repository, nessun accesso DB (compatibilita' CI).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_search_lookup_ok — ricerca valida con risultati
 2) test_search_lookup_query_too_short — q < 2 char rifiutata
 3) test_search_lookup_query_empty — q vuota rifiutata
 4) test_search_lookup_whitespace_trimmed — spazi rimossi
 5) test_search_lookup_limit_cap — limit > 50 capped a 50
 6) test_search_lookup_limit_default — limit None/0 usa default 20
 7) test_search_lookup_utility_filter_passed — utility_id propagato al repo
 8) test_search_lookup_soggetto_filter_passed — soggetto_id propagato al repo
 9) test_search_lookup_emittente_scope_passed — scope sr_ids propagato
10) test_search_lookup_no_results — zero risultati
11) test_get_lookup_by_id_ok — restore istanza esistente
12) test_get_lookup_by_id_not_found — istanza inesistente solleva E_ANAG_NOT_FOUND
13) test_get_lookup_by_id_invalid_id — id 0 o negativo rifiutato
14) test_get_lookup_by_id_bool_rejected — bool rifiutato come id
"""

from unittest import TestCase
from unittest.mock import patch

from apps.core.services.service_errors import ServiceError

_REPO = "apps.anagrafiche.services.istanze_utility_service.IstanzeUtilityRepository"

_FAKE_ROW = {
    "id": 900,
    "codice": "IU-000900",
    "fittizia": False,
    "soggetto_id": "11111111-1111-1111-1111-111111111111",
    "ragione_sociale_completa": "Rossi Mario",
    "id_fiscale": "RSSMRA80A01H501U",
    "indirizzo_dettaglio_id": 12,
    "indirizzo_display": "Via Roma 1, 00100 Roma RM",
    "billing_account_id": 123,
    "billing_account_codice": "BA-000123",
    "utility_id": 1,
    "utility_codice": "GAS",
    "utility_descrizione": "Gas naturale",
}


class TestIstanzeUtilitySearchLookup(TestCase):
    """Test search_lookup — validazioni + propagazione parametri."""

    @patch(_REPO)
    def test_search_lookup_ok(self, mock_repo):
        """Ricerca valida con risultati."""
        repo = mock_repo.return_value
        repo.search_lookup.return_value = ([_FAKE_ROW], 1)
        from apps.anagrafiche.services.istanze_utility_service import IstanzeUtilityService
        result = IstanzeUtilityService().search_lookup(q="Rossi")
        self.assertEqual(result["total_count"], 1)
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["results"][0]["id"], 900)
        self.assertEqual(result["limit"], 20)

    @patch(_REPO)
    def test_search_lookup_query_too_short(self, mock_repo):
        """q < 2 char solleva E_ANAG_VALIDAZIONE senza chiamare il repo."""
        from apps.anagrafiche.services.istanze_utility_service import IstanzeUtilityService
        with self.assertRaises(ServiceError) as ctx:
            IstanzeUtilityService().search_lookup(q="R")
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        mock_repo.return_value.search_lookup.assert_not_called()

    @patch(_REPO)
    def test_search_lookup_query_empty(self, mock_repo):
        """q vuota solleva E_ANAG_VALIDAZIONE."""
        from apps.anagrafiche.services.istanze_utility_service import IstanzeUtilityService
        with self.assertRaises(ServiceError):
            IstanzeUtilityService().search_lookup(q="")
        mock_repo.return_value.search_lookup.assert_not_called()

    @patch(_REPO)
    def test_search_lookup_whitespace_trimmed(self, mock_repo):
        """Spazi iniziali/finali rimossi prima della validazione."""
        repo = mock_repo.return_value
        repo.search_lookup.return_value = ([], 0)
        from apps.anagrafiche.services.istanze_utility_service import IstanzeUtilityService
        IstanzeUtilityService().search_lookup(q="  IU  ")
        _, kwargs = repo.search_lookup.call_args
        self.assertEqual(kwargs["q"], "IU")

    @patch(_REPO)
    def test_search_lookup_limit_cap(self, mock_repo):
        """limit > 50 viene capped a 50."""
        repo = mock_repo.return_value
        repo.search_lookup.return_value = ([], 0)
        from apps.anagrafiche.services.istanze_utility_service import IstanzeUtilityService
        result = IstanzeUtilityService().search_lookup(q="Rossi", limit=200)
        self.assertEqual(result["limit"], 50)
        _, kwargs = repo.search_lookup.call_args
        self.assertEqual(kwargs["limit"], 50)

    @patch(_REPO)
    def test_search_lookup_limit_default(self, mock_repo):
        """limit <= 0 o None usa default 20."""
        repo = mock_repo.return_value
        repo.search_lookup.return_value = ([], 0)
        from apps.anagrafiche.services.istanze_utility_service import IstanzeUtilityService
        result_zero = IstanzeUtilityService().search_lookup(q="Rossi", limit=0)
        self.assertEqual(result_zero["limit"], 20)
        result_neg = IstanzeUtilityService().search_lookup(q="Rossi", limit=-5)
        self.assertEqual(result_neg["limit"], 20)
        result_none = IstanzeUtilityService().search_lookup(q="Rossi", limit=None)
        self.assertEqual(result_none["limit"], 20)

    @patch(_REPO)
    def test_search_lookup_utility_filter_passed(self, mock_repo):
        """utility_id propagato al repo (strict filter)."""
        repo = mock_repo.return_value
        repo.search_lookup.return_value = ([], 0)
        from apps.anagrafiche.services.istanze_utility_service import IstanzeUtilityService
        IstanzeUtilityService().search_lookup(q="Rossi", utility_id=42)
        _, kwargs = repo.search_lookup.call_args
        self.assertEqual(kwargs["utility_id"], 42)

    @patch(_REPO)
    def test_search_lookup_soggetto_filter_passed(self, mock_repo):
        """soggetto_id (UUID) propagato al repo."""
        repo = mock_repo.return_value
        repo.search_lookup.return_value = ([], 0)
        from apps.anagrafiche.services.istanze_utility_service import IstanzeUtilityService
        soggetto_uuid = "22222222-2222-2222-2222-222222222222"
        IstanzeUtilityService().search_lookup(q="Rossi", soggetto_id=soggetto_uuid)
        _, kwargs = repo.search_lookup.call_args
        self.assertEqual(kwargs["soggetto_id"], soggetto_uuid)

    @patch(_REPO)
    def test_search_lookup_emittente_scope_passed(self, mock_repo):
        """scope emittente sr_ids propagato al repo."""
        repo = mock_repo.return_value
        repo.search_lookup.return_value = ([], 0)
        from apps.anagrafiche.services.istanze_utility_service import IstanzeUtilityService
        IstanzeUtilityService().search_lookup(q="Rossi", emittente_ids=[10, 20])
        _, kwargs = repo.search_lookup.call_args
        self.assertEqual(kwargs["emittente_ids"], [10, 20])

    @patch(_REPO)
    def test_search_lookup_no_results(self, mock_repo):
        """Zero risultati ammesso (non e' un errore)."""
        repo = mock_repo.return_value
        repo.search_lookup.return_value = ([], 0)
        from apps.anagrafiche.services.istanze_utility_service import IstanzeUtilityService
        result = IstanzeUtilityService().search_lookup(q="ZZZ")
        self.assertEqual(result["results"], [])
        self.assertEqual(result["total_count"], 0)


class TestIstanzeUtilityGetLookupById(TestCase):
    """Test get_lookup_by_id — restore singolo per AutoComplete in edit."""

    @patch(_REPO)
    def test_get_lookup_by_id_ok(self, mock_repo):
        """Restore istanza esistente."""
        repo = mock_repo.return_value
        repo.get_lookup_by_id.return_value = _FAKE_ROW
        from apps.anagrafiche.services.istanze_utility_service import IstanzeUtilityService
        result = IstanzeUtilityService().get_lookup_by_id(900)
        self.assertEqual(result["id"], 900)
        self.assertEqual(result["codice"], "IU-000900")

    @patch(_REPO)
    def test_get_lookup_by_id_not_found(self, mock_repo):
        """Istanza inesistente → E_ANAG_NOT_FOUND."""
        mock_repo.return_value.get_lookup_by_id.return_value = None
        from apps.anagrafiche.services.istanze_utility_service import IstanzeUtilityService
        with self.assertRaises(ServiceError) as ctx:
            IstanzeUtilityService().get_lookup_by_id(99999)
        self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")

    @patch(_REPO)
    def test_get_lookup_by_id_invalid_id(self, mock_repo):
        """id 0 o negativo → E_ANAG_VALIDAZIONE senza chiamare il repo."""
        from apps.anagrafiche.services.istanze_utility_service import IstanzeUtilityService
        for bad_id in (0, -1, -99):
            with self.assertRaises(ServiceError) as ctx:
                IstanzeUtilityService().get_lookup_by_id(bad_id)
            self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        mock_repo.return_value.get_lookup_by_id.assert_not_called()

    @patch(_REPO)
    def test_get_lookup_by_id_bool_rejected(self, mock_repo):
        """bool e' sottoclasse di int in Python: deve essere rifiutato."""
        from apps.anagrafiche.services.istanze_utility_service import IstanzeUtilityService
        with self.assertRaises(ServiceError) as ctx:
            IstanzeUtilityService().get_lookup_by_id(True)  # type: ignore[arg-type]
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        mock_repo.return_value.get_lookup_by_id.assert_not_called()
