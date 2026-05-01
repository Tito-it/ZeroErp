# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari del BB `resolve_valuta_default` (catena standard
#        BA -> EF-del-BA -> EF-utente). DB mockato per CI.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_no_ba_no_user_returns_empty           — nessuna sorgente -> {}
 2) test_ba_con_valuta_vince                    — livello 1: ba.valuta_id wins
 3) test_ba_senza_valuta_fallback_ef_del_ba     — livello 2: get_emittente_valuta
 4) test_no_ba_user_ef_valuta                   — livello 3: EF utente
 5) test_no_ba_user_ef_senza_valuta             — EF utente con valuta_id NULL -> {}
 6) test_no_ba_admin_globale_no_ef              — admin globale (ef_id None) -> {}
 7) test_ba_obj_pre_fetched_riusa                — ba_obj passato salta query lookup
 8) test_ba_inesistente_lookup_none_fallback_user — BA non trovato + user EF -> usa user EF
"""

from unittest import TestCase
from unittest.mock import patch

from apps.anagrafiche.services.valuta_resolver import resolve_valuta_default


_MOD = "apps.anagrafiche.services.valuta_resolver"
_BA_REPO = f"{_MOD}.BillingAccountRepository"
_EF_REPO = f"{_MOD}.EmittentiFiscaliRepository"
_PARAM = f"{_MOD}.ParameterService"


class TestResolveValutaDefault(TestCase):

    def test_no_ba_no_user_returns_empty(self):
        # Scopo: nessuna sorgente -> dict vuoto.
        result = resolve_valuta_default()
        self.assertEqual(result, {})

    @patch(_BA_REPO)
    def test_ba_con_valuta_vince(self, mock_ba_repo_cls):
        # Scopo: livello 1 = ba.valuta_id direttamente.
        mock_ba_repo_cls.return_value.get_lookup_by_id.return_value = {
            "id": 10,
            "valuta_id": 1,
            "valuta_codice": "EUR",
            "valuta_descrizione": "Euro",
        }
        result = resolve_valuta_default(billing_account_id=10)
        self.assertEqual(result["valuta_id"], 1)
        self.assertEqual(result["valuta_codice"], "EUR")
        # Livello 2/3 mai chiamato.
        mock_ba_repo_cls.return_value.get_emittente_valuta.assert_not_called()

    @patch(_BA_REPO)
    def test_ba_senza_valuta_fallback_ef_del_ba(self, mock_ba_repo_cls):
        # Scopo: livello 2 = EF del BA via get_emittente_valuta(ba_id).
        ba_repo = mock_ba_repo_cls.return_value
        ba_repo.get_lookup_by_id.return_value = {
            "id": 10, "valuta_id": None,
        }
        ba_repo.get_emittente_valuta.return_value = {
            "valuta_id": 2, "valuta_codice": "USD", "valuta_descrizione": "Dollaro",
        }
        result = resolve_valuta_default(billing_account_id=10)
        self.assertEqual(result["valuta_id"], 2)
        self.assertEqual(result["valuta_codice"], "USD")
        ba_repo.get_emittente_valuta.assert_called_once_with(10)

    @patch(_EF_REPO)
    @patch(_PARAM)
    def test_no_ba_user_ef_valuta(self, mock_param_cls, mock_ef_repo_cls):
        # Scopo: livello 3 = EF dell'utente. Mappa valuta_iso -> valuta_codice
        #        per omogeneita' di shape col payload form-defaults.
        mock_param_cls.return_value.get_emittente_fiscale_id_for_user.return_value = 42
        mock_ef_repo_cls.return_value.get_emittente.return_value = {
            "id": 42,
            "valuta_id": 1,
            "valuta_iso": "EUR",
            "valuta_descrizione": "Euro",
        }
        result = resolve_valuta_default(auth_user_id=99)
        self.assertEqual(result["valuta_id"], 1)
        self.assertEqual(result["valuta_codice"], "EUR")  # mapping iso -> codice
        self.assertEqual(result["valuta_descrizione"], "Euro")

    @patch(_EF_REPO)
    @patch(_PARAM)
    def test_no_ba_user_ef_senza_valuta(self, mock_param_cls, mock_ef_repo_cls):
        # Scopo: EF utente esiste ma valuta_id NULL -> dict vuoto.
        mock_param_cls.return_value.get_emittente_fiscale_id_for_user.return_value = 42
        mock_ef_repo_cls.return_value.get_emittente.return_value = {
            "id": 42, "valuta_id": None,
        }
        result = resolve_valuta_default(auth_user_id=99)
        self.assertEqual(result, {})

    @patch(_EF_REPO)
    @patch(_PARAM)
    def test_no_ba_admin_globale_no_ef(self, mock_param_cls, mock_ef_repo_cls):
        # Scopo: admin globale senza EF assegnato (e senza gestore globale)
        #        -> dict vuoto.
        mock_param_cls.return_value.get_emittente_fiscale_id_for_user.return_value = None
        result = resolve_valuta_default(auth_user_id=99)
        self.assertEqual(result, {})
        # EF repo mai consultato perche' ef_id None.
        mock_ef_repo_cls.return_value.get_emittente.assert_not_called()

    @patch(_BA_REPO)
    def test_ba_obj_pre_fetched_riusa(self, mock_ba_repo_cls):
        # Scopo: caller passa ba_obj gia' fetched -> nessuna query lookup.
        ba_pre_fetched = {
            "id": 10, "valuta_id": 1,
            "valuta_codice": "EUR", "valuta_descrizione": "Euro",
        }
        result = resolve_valuta_default(
            billing_account_id=10, ba_obj=ba_pre_fetched,
        )
        self.assertEqual(result["valuta_id"], 1)
        # get_lookup_by_id NON deve essere chiamato (ottimizzazione).
        mock_ba_repo_cls.return_value.get_lookup_by_id.assert_not_called()

    @patch(_EF_REPO)
    @patch(_PARAM)
    @patch(_BA_REPO)
    def test_ba_inesistente_lookup_none_fallback_user(
        self, mock_ba_repo_cls, mock_param_cls, mock_ef_repo_cls,
    ):
        # Scopo: BA con id valido ma get_lookup_by_id ritorna None
        #        (BA inesistente) e get_emittente_valuta vuoto -> il resolver
        #        non solleva, prosegue con il fallback user EF.
        ba_repo = mock_ba_repo_cls.return_value
        ba_repo.get_lookup_by_id.return_value = None
        ba_repo.get_emittente_valuta.return_value = {}
        mock_param_cls.return_value.get_emittente_fiscale_id_for_user.return_value = 42
        mock_ef_repo_cls.return_value.get_emittente.return_value = {
            "valuta_id": 1, "valuta_iso": "EUR", "valuta_descrizione": "Euro",
        }
        result = resolve_valuta_default(billing_account_id=999, auth_user_id=99)
        self.assertEqual(result["valuta_id"], 1)
