# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
 8) test_search_lookup_emittente_scope_passed — scope emittente risolto dall'utente (soggetto-ruolo) e propagato
 9) test_search_lookup_solo_validi_default — default true
10) test_search_lookup_no_results — zero risultati
11) test_get_lookup_by_id_ok — restore BA esistente
12) test_get_lookup_by_id_not_found — BA inesistente solleva E_ANAG_NOT_FOUND
13) test_get_lookup_by_id_invalid_id — id 0 o negativo rifiutato
14) test_get_lookup_by_id_bool_rejected — bool rifiutato come id
15) test_list_utilities_ok_operatore_in_scope — operatore con BA del proprio EF → utility ritornate
16) test_list_utilities_admin_globale_bypass — user_emittente_id=None → no scope check
17) test_list_utilities_superuser_bypass — is_superuser=True → no scope check anche se user_emittente_id valorizzato
18) test_list_utilities_403_ba_di_altro_emittente — operatore + BA di altro EF → E_PERMESSO_NEGATO
19) test_list_utilities_404_ba_inesistente — id BA non esistente → E_ANAG_NOT_FOUND prima dello scope
20) test_list_utilities_ruolo_invalido — ruolo non in whitelist → E_ANAG_VALIDAZIONE
21) test_categoria_da_query_assente_none — parametro assente o vuoto → None, nessun lookup
22) test_categoria_da_query_malformato — non numerico o <= 0 → ValueError, nessun lookup
23) test_categoria_da_query_ok — BA visibile → la sua categoria
24) test_categoria_da_query_non_risulta — BA inesistente o fuori scope → E_ANAG_NOT_FOUND (F-6)
25) test_istanza_del_ba_deriva — istanza assente → quella del BA
26) test_istanza_del_ba_coincide — istanza indicata uguale a quella del BA → ammessa
27) test_istanza_del_ba_altra_istanza — istanza diversa → errore del dominio sul campo del BA
28) test_istanza_del_ba_non_risulta — BA inesistente o fuori RLS → errore del dominio sul campo del BA
29) test_istanza_del_ba_campo_istanza — col BA gia' scritto (onere della commessa) l'errore cade sull'istanza
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.service_errors import ServiceError

_REPO = "apps.anagrafiche.services.billing_account_service.BillingAccountRepository"
_RESOLVER = "apps.anagrafiche.services.billing_account_service.PermissionResolver"
_USER = MagicMock(id=1)

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

    def setUp(self) -> None:
        patcher = patch(_RESOLVER)
        self.mock_resolver = patcher.start()
        self.addCleanup(patcher.stop)
        self.mock_resolver.get_emittenti_sr_ids.return_value = None

    @patch(_REPO, autospec=True)
    def test_search_lookup_ok(self, mock_repo):
        """Ricerca valida con risultati."""
        repo = mock_repo.return_value
        repo.search_lookup.return_value = ([_FAKE_ROW], 1)
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        result = BillingAccountService().search_lookup(user=_USER, q="Rossi")
        self.assertEqual(result["total_count"], 1)
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["results"][0]["id"], 123)
        self.assertEqual(result["limit"], 20)

    @patch(_REPO, autospec=True)
    def test_search_lookup_query_too_short(self, mock_repo):
        """q < 2 char solleva E_ANAG_VALIDAZIONE senza chiamare il repo."""
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        with self.assertRaises(ServiceError) as ctx:
            BillingAccountService().search_lookup(user=_USER, q="R")
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        mock_repo.return_value.search_lookup.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_search_lookup_query_empty(self, mock_repo):
        """q vuota solleva E_ANAG_VALIDAZIONE."""
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        with self.assertRaises(ServiceError):
            BillingAccountService().search_lookup(user=_USER, q="")
        mock_repo.return_value.search_lookup.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_search_lookup_whitespace_trimmed(self, mock_repo):
        """Spazi iniziali/finali rimossi prima della validazione."""
        repo = mock_repo.return_value
        repo.search_lookup.return_value = ([], 0)
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        BillingAccountService().search_lookup(user=_USER, q="  BA  ")
        # Verifica che al repo sia passato il trimmed "BA".
        _, kwargs = repo.search_lookup.call_args
        self.assertEqual(kwargs["q"], "BA")

    @patch(_REPO, autospec=True)
    def test_search_lookup_limit_cap(self, mock_repo):
        """limit > 50 viene capped a 50."""
        repo = mock_repo.return_value
        repo.search_lookup.return_value = ([], 0)
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        result = BillingAccountService().search_lookup(user=_USER, q="Rossi", limit=200)
        self.assertEqual(result["limit"], 50)
        _, kwargs = repo.search_lookup.call_args
        self.assertEqual(kwargs["limit"], 50)

    @patch(_REPO, autospec=True)
    def test_search_lookup_limit_default(self, mock_repo):
        """limit <= 0 o None usa default 20."""
        repo = mock_repo.return_value
        repo.search_lookup.return_value = ([], 0)
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        result_zero = BillingAccountService().search_lookup(user=_USER, q="Rossi", limit=0)
        self.assertEqual(result_zero["limit"], 20)
        result_none = BillingAccountService().search_lookup(user=_USER, q="Rossi", limit=None)  # type: ignore[arg-type]
        self.assertEqual(result_none["limit"], 20)

    @patch(_REPO, autospec=True)
    def test_search_lookup_utility_filter_passed(self, mock_repo):
        """utility_id viene propagato al repository."""
        repo = mock_repo.return_value
        repo.search_lookup.return_value = ([], 0)
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        BillingAccountService().search_lookup(user=_USER, q="Rossi", utility_id=7)
        _, kwargs = repo.search_lookup.call_args
        self.assertEqual(kwargs["utility_id"], 7)

    @patch(_REPO, autospec=True)
    def test_search_lookup_emittente_scope_passed(self, mock_repo):
        """Lo scope emittente lo risolve il service dall'utente, coi
        soggetto_ruolo_id (non le PK: la query confronta col soggetto-ruolo
        dell'emittente), e lo propaga al repository."""
        repo = mock_repo.return_value
        repo.search_lookup.return_value = ([], 0)
        self.mock_resolver.get_emittenti_sr_ids.return_value = [10, 20]
        self.mock_resolver.get_emittenti_pk_ids.return_value = [1, 2]
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        BillingAccountService().search_lookup(user=_USER, q="Rossi")
        self.mock_resolver.get_emittenti_sr_ids.assert_called_once()
        self.assertIs(self.mock_resolver.get_emittenti_sr_ids.call_args.args[0], _USER)
        _, kwargs = repo.search_lookup.call_args
        self.assertEqual(kwargs["emittente_ids"], [10, 20])

    @patch(_REPO, autospec=True)
    def test_search_lookup_solo_validi_default(self, mock_repo):
        """solo_validi default True quando non specificato."""
        repo = mock_repo.return_value
        repo.search_lookup.return_value = ([], 0)
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        BillingAccountService().search_lookup(user=_USER, q="Rossi")
        _, kwargs = repo.search_lookup.call_args
        self.assertIs(kwargs["solo_validi"], True)

    @patch(_REPO, autospec=True)
    def test_search_lookup_no_results(self, mock_repo):
        """Zero risultati restituisce results vuoto e total_count 0."""
        repo = mock_repo.return_value
        repo.search_lookup.return_value = ([], 0)
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        result = BillingAccountService().search_lookup(user=_USER, q="NoMatch")
        self.assertEqual(result["results"], [])
        self.assertEqual(result["total_count"], 0)


class TestBillingAccountGetLookupById(TestCase):
    """Test get_lookup_by_id — restore per edit."""

    @patch(_REPO, autospec=True)
    def test_get_lookup_by_id_ok(self, mock_repo):
        """Restore BA esistente."""
        repo = mock_repo.return_value
        repo.get_lookup_by_id.return_value = _FAKE_ROW
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        result = BillingAccountService().get_lookup_by_id(123)
        self.assertEqual(result["id"], 123)
        self.assertEqual(result["codice"], "BA-000123")

    @patch(_REPO, autospec=True)
    def test_get_lookup_by_id_not_found(self, mock_repo):
        """BA inesistente solleva E_ANAG_NOT_FOUND."""
        repo = mock_repo.return_value
        repo.get_lookup_by_id.return_value = None
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        with self.assertRaises(ServiceError) as ctx:
            BillingAccountService().get_lookup_by_id(9999)
        self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")

    @patch(_REPO, autospec=True)
    def test_get_lookup_by_id_invalid_id(self, mock_repo):
        """id <= 0 rifiutato con E_ANAG_VALIDAZIONE."""
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        with self.assertRaises(ServiceError) as ctx:
            BillingAccountService().get_lookup_by_id(0)
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        mock_repo.return_value.get_lookup_by_id.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_get_lookup_by_id_bool_rejected(self, mock_repo):
        """Un bool (True/False) non e' un id valido anche se Python lo tratta come int."""
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        with self.assertRaises(ServiceError) as ctx:
            BillingAccountService().get_lookup_by_id(True)  # type: ignore[arg-type]
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        mock_repo.return_value.get_lookup_by_id.assert_not_called()


# =================================================================
# list_utilities_for_ba — refactor operatore-emittenti, BE-3
# =================================================================

_LOOKUP_REPO = "apps.anagrafiche.services.billing_account_service.LookupRepository"
_FAKE_UTILITIES = [
    {
        "utility_id": 1, "codice": "EE", "descrizione": "Energia Elettrica",
        "is_personalizzata_per_ef": True,
        "minimo_soglia_min": 0.5, "minimo_soglia_max": 1000.0,
        "arrotondamento_importi_dec": 2, "metodo_arrotondamento_importi": "HALF_UP",
    },
    {
        "utility_id": 2, "codice": "GAS", "descrizione": "Gas Naturale",
        "is_personalizzata_per_ef": False,
        "minimo_soglia_min": None, "minimo_soglia_max": None,
        "arrotondamento_importi_dec": None, "metodo_arrotondamento_importi": None,
    },
]


class TestBillingAccountListUtilitiesForBa(TestCase):
    """Test list_utilities_for_ba — scope emittente + delega lookup.

    L'esistenza del BA viene controllata via BillingAccountRepository.exists()
    (l'id positivo e' gia' garantito dall'URL converter <int:...>, quindi
    nessun test di id <= 0 a livello di service).
    """

    @patch(_LOOKUP_REPO, autospec=True)
    @patch(_REPO, autospec=True)
    def test_list_utilities_ok_operatore_in_scope(self, mock_repo, mock_lookup):
        """Operatore con BA del proprio emittente → utility ritornate."""
        mock_repo.return_value.exists.return_value = True
        mock_repo.return_value.get_emittente_fiscale_id.return_value = 7
        mock_lookup.return_value.list_utilities_per_billing_account.return_value = _FAKE_UTILITIES
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        result = BillingAccountService().list_utilities_for_ba(
            billing_account_id=200,
            ruolo_codice_soggetto="CL",
            user_emittente_id=7,
        )
        self.assertEqual(len(result["results"]), 2)
        mock_repo.return_value.exists.assert_called_once_with(200)
        mock_repo.return_value.get_emittente_fiscale_id.assert_called_once_with(200)
        mock_lookup.return_value.list_utilities_per_billing_account.assert_called_once_with(
            billing_account_id=200, ruolo_codice_soggetto="CL"
        )

    @patch(_LOOKUP_REPO, autospec=True)
    @patch(_REPO, autospec=True)
    def test_list_utilities_admin_globale_bypass(self, mock_repo, mock_lookup):
        """Admin globale (user_emittente_id=None) → nessun scope check."""
        mock_repo.return_value.exists.return_value = True
        mock_lookup.return_value.list_utilities_per_billing_account.return_value = _FAKE_UTILITIES
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        result = BillingAccountService().list_utilities_for_ba(
            billing_account_id=200,
            ruolo_codice_soggetto="CL",
            user_emittente_id=None,
        )
        self.assertEqual(len(result["results"]), 2)
        mock_repo.return_value.get_emittente_fiscale_id.assert_not_called()

    @patch(_LOOKUP_REPO, autospec=True)
    @patch(_REPO, autospec=True)
    def test_list_utilities_superuser_bypass(self, mock_repo, mock_lookup):
        """is_superuser=True → bypass anche se user_emittente_id valorizzato."""
        mock_repo.return_value.exists.return_value = True
        mock_lookup.return_value.list_utilities_per_billing_account.return_value = []
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        BillingAccountService().list_utilities_for_ba(
            billing_account_id=200,
            ruolo_codice_soggetto="FO",
            user_emittente_id=7,
            is_superuser=True,
        )
        mock_repo.return_value.get_emittente_fiscale_id.assert_not_called()

    @patch(_LOOKUP_REPO, autospec=True)
    @patch(_REPO, autospec=True)
    def test_list_utilities_403_ba_di_altro_emittente(self, mock_repo, mock_lookup):
        """Operatore + BA di altro EF → E_PERMESSO_NEGATO, no lookup."""
        mock_repo.return_value.exists.return_value = True
        mock_repo.return_value.get_emittente_fiscale_id.return_value = 99
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        with self.assertRaises(ServiceError) as ctx:
            BillingAccountService().list_utilities_for_ba(
                billing_account_id=200,
                ruolo_codice_soggetto="CL",
                user_emittente_id=7,
            )
        self.assertEqual(ctx.exception.code, "E_PERMESSO_NEGATO")
        mock_lookup.return_value.list_utilities_per_billing_account.assert_not_called()

    @patch(_LOOKUP_REPO, autospec=True)
    @patch(_REPO, autospec=True)
    def test_list_utilities_404_ba_inesistente(self, mock_repo, mock_lookup):
        """BA inesistente → E_ANAG_NOT_FOUND prima del check scope."""
        mock_repo.return_value.exists.return_value = False
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        with self.assertRaises(ServiceError) as ctx:
            BillingAccountService().list_utilities_for_ba(
                billing_account_id=999,
                ruolo_codice_soggetto="CL",
                user_emittente_id=7,
            )
        self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")
        mock_repo.return_value.get_emittente_fiscale_id.assert_not_called()
        mock_lookup.return_value.list_utilities_per_billing_account.assert_not_called()

    @patch(_LOOKUP_REPO, autospec=True)
    @patch(_REPO, autospec=True)
    def test_list_utilities_ruolo_invalido(self, mock_repo, mock_lookup):
        """Ruolo non in whitelist (es. 'XX') → E_ANAG_VALIDAZIONE."""
        from apps.anagrafiche.services.billing_account_service import BillingAccountService
        with self.assertRaises(ServiceError) as ctx:
            BillingAccountService().list_utilities_for_ba(
                billing_account_id=200,
                ruolo_codice_soggetto="XX",
                user_emittente_id=7,
            )
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        mock_lookup.return_value.list_utilities_per_billing_account.assert_not_called()


class CategoriaClienteDaQueryTests(TestCase):
    """BB `categoria_cliente_da_query` (F-6): BA del query param → categoria."""

    @patch(_REPO, autospec=True)
    def test_categoria_da_query_assente_none(self, mock_repo):
        from apps.anagrafiche.services.billing_account_service import categoria_cliente_da_query
        for raw in (None, "", "   "):
            with self.subTest(raw=raw):
                self.assertIsNone(categoria_cliente_da_query(raw))
        mock_repo.return_value.get_categoria_cliente_id.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_categoria_da_query_malformato(self, mock_repo):
        from apps.anagrafiche.services.billing_account_service import categoria_cliente_da_query
        for raw in ("abc", "1.0", "0", "-3"):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    categoria_cliente_da_query(raw)
        mock_repo.return_value.get_categoria_cliente_id.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_categoria_da_query_ok(self, mock_repo):
        from apps.anagrafiche.services.billing_account_service import categoria_cliente_da_query
        mock_repo.return_value.get_categoria_cliente_id.return_value = 4
        self.assertEqual(categoria_cliente_da_query(" 77 "), 4)
        mock_repo.return_value.get_categoria_cliente_id.assert_called_once_with(77)

    @patch(_REPO, autospec=True)
    def test_categoria_da_query_non_risulta(self, mock_repo):
        """Inesistente e fuori scope (RLS) sono lo stesso None: un 404 solo."""
        from apps.anagrafiche.services.billing_account_service import categoria_cliente_da_query
        mock_repo.return_value.get_categoria_cliente_id.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            categoria_cliente_da_query("77")
        self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")


class TestIstanzaDelBillingAccount(TestCase):
    """BB `istanza_del_billing_account`: l'istanza del BA che il payload indica
    (pratica, preventivo — regola del 2, ok Tid 2026-10-09)."""

    @staticmethod
    def _chiama(istanza_utility_id):
        from apps.anagrafiche.services.billing_account_service import istanza_del_billing_account
        return istanza_del_billing_account(
            33, istanza_utility_id, code="E_DOMINIO_VALIDATION", function_name="test",
        )

    @patch(_REPO, autospec=True)
    def test_istanza_del_ba_deriva(self, mock_repo):
        mock_repo.return_value.get_istanza_utility_id.return_value = 200
        self.assertEqual(self._chiama(None), 200)
        mock_repo.return_value.get_istanza_utility_id.assert_called_once_with(33)

    @patch(_REPO, autospec=True)
    def test_istanza_del_ba_coincide(self, mock_repo):
        mock_repo.return_value.get_istanza_utility_id.return_value = 200
        self.assertEqual(self._chiama(200), 200)

    @patch(_REPO, autospec=True)
    def test_istanza_del_ba_altra_istanza(self, mock_repo):
        mock_repo.return_value.get_istanza_utility_id.return_value = 200
        with self.assertRaises(ServiceError) as ctx:
            self._chiama(999)
        self.assertEqual(ctx.exception.code, "E_DOMINIO_VALIDATION")
        self.assertEqual(ctx.exception.context.get("field"), "billing_account_id")

    @patch(_REPO, autospec=True)
    def test_istanza_del_ba_non_risulta(self, mock_repo):
        mock_repo.return_value.get_istanza_utility_id.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            self._chiama(None)
        self.assertEqual(ctx.exception.code, "E_DOMINIO_VALIDATION")
        self.assertEqual(ctx.exception.context.get("field"), "billing_account_id")

    @patch(_REPO, autospec=True)
    def test_istanza_del_ba_campo_istanza(self, mock_repo):
        from apps.anagrafiche.services.billing_account_service import istanza_del_billing_account
        mock_repo.return_value.get_istanza_utility_id.return_value = 200
        with self.assertRaises(ServiceError) as ctx:
            istanza_del_billing_account(
                33, 999, code="E_DOMINIO_VALIDATION", function_name="test",
                campo="istanza_utility_id",
            )
        self.assertEqual(ctx.exception.context.get("field"), "istanza_utility_id")
