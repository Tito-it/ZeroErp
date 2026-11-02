# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari del service form-defaults vendite
#        (Fase 2.B3-B5 refactor frontend vendite). DB mockato per CI.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_contratto_no_ba_solo_parameters     — payload minimo con default_data/valido_dal
 2) test_contratto_con_ba_popola_categoria   — categoria_cliente_id_snapshot dal BA lookup
 3) test_contratto_ba_inesistente_404        — E_VENDITE_NOT_FOUND
 4) test_contratto_param_int_fallback        — parameter mancante -> fallback (0)
 5) test_preventivo_no_ba_solo_parameters    — default_validita_al = oggi + N
 6) test_preventivo_con_ba_termini_da_cliente — termine_pagamento_id da clienti
 7) test_preventivo_valuta_da_emittente_se_ba_null — fallback emittente del BA
 8) test_preventivo_no_ba_valuta_da_user_ef        — fallback EF utente loggato
 8-bis) test_contratto/offerta_scheda_fornitura_dal_cliente — R-BE-5: la scheda
        dell'anagrafica della coppia del BA; senza BA niente lettura
 8a) test_ddt_no_ba_no_user_payload_vuoto     — utility/valuta None (no BA/user)
 8b) test_ddt_con_ba_popola_utility_e_valuta  — utility+valuta dal BA, no pagamento
 8c) test_ddt_ba_inesistente_404              — E_VENDITE_NOT_FOUND
 9) test_versione_new_defaults                — payload + existing_drafts
 9) test_versione_clone_codice_con_suffisso   — suffisso da parameter
10) test_versione_close_default_oggi_se_no_chiusura — default oggi+lead_gg
11) test_versione_close_usa_existing_se_presente    — modifica chiusura
11bis) test_versione_close_fine_passata_non_riproposta — fine passata: default oggi+lead_gg
12) test_listino_inesistente_404               — E_VENDITE_NOT_FOUND
13) test_versione_inesistente_404              — E_VENDITE_NOT_FOUND
"""

from datetime import date, timedelta
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.core.services.service_errors import ServiceError
from apps.vendite.services.vendite_form_defaults_service import (
    fn_get_contratto_form_defaults,
    fn_get_ddt_form_defaults,
    fn_get_offerta_form_defaults,
    fn_get_ordine_form_defaults,
    fn_get_preventivo_form_defaults,
    fn_get_versione_clone_defaults,
    fn_get_versione_close_defaults,
    fn_get_versione_new_defaults,
)


# Path patch comuni: il service istanzia ParameterService/repo dentro le
# funzioni — patchamo le classi importate dal modulo target.
_MOD = "apps.vendite.services.vendite_form_defaults_service"
_PARAM = f"{_MOD}.ParameterService"
_BA_REPO = f"{_MOD}.BillingAccountRepository"
# Il BB resolve_valuta_default ha un livello 4 (fallback gestore) che fa
# una query diretta su anagrafiche.gestori. Va mockata la `connection` nei
# test che esercitano il path "no BA / no EF utente", altrimenti il
# resolver finisce a fare una query DB reale.
_RESOLVER_CONN = "apps.anagrafiche.services.valuta_resolver.connection"
_LISTINI_REPO = f"{_MOD}.ListiniRepository"
# La scheda di fornitura dall'anagrafica (R-BE-5): una lettura del DB, finta
# in tutti i test di contratto e offerta.
_FORNITURA = f"{_MOD}.fornitura_da_anagrafica"
_SCHEDA = {
    "istanza_dati_precontrattuali_id": 55, "classe_utenza_id": 4, "tipo_utenza_id": 2,
    "param_1_num": "3.50", "param_2_txt": "B1", "meta": {},
}


# Scopo: finge la lettura della scheda per una classe di test (setUp).
def _finge_fornitura(test: TestCase) -> MagicMock:
    patcher = patch(_FORNITURA, return_value=_SCHEDA)
    mock = patcher.start()
    test.addCleanup(patcher.stop)
    return mock


def _ba_lookup_row(*, ba_id=10, categoria_id=7, valuta_id=None):
    return {
        "id": ba_id,
        "categoria_cliente_id": categoria_id,
        "categoria_cliente_codice": "STANDARD",
        "categoria_cliente_descrizione": "Standard",
        "utility_id": 1,
        "utility_codice": "GAS",
        "utility_descrizione": "Gas",
        "istanza_utility_id": 100,
        "soggetto_ruolo_id": 200,
        "valuta_id": valuta_id,
        "valuta_codice": "EUR" if valuta_id is not None else None,
        "valuta_descrizione": "Euro" if valuta_id is not None else None,
    }


# ──────────────────────────────────────────────────────────
# Contratti form-defaults
# ──────────────────────────────────────────────────────────


class TestContrattoFormDefaults(TestCase):

    def setUp(self):
        self.fornitura = _finge_fornitura(self)

    @patch(f"{_MOD}.resolve_valuta_default", return_value={})
    @patch(_BA_REPO)
    @patch(_PARAM)
    def test_contratto_scheda_fornitura_dal_cliente(
        self, mock_param_cls, mock_ba_repo_cls, _mock_resolve,
    ):
        # Scopo: col BA la scheda e' quella che l'anagrafica da' alla coppia
        #        (istanza, utility) del BA, letta dal DB e restituita com'e'.
        mock_param_cls.return_value.get_defaults.return_value = {}
        mock_ba_repo_cls.return_value.get_lookup_by_id.return_value = _ba_lookup_row()
        result = fn_get_contratto_form_defaults(billing_account_id=10)
        self.fornitura.assert_called_once_with(100, 1)
        self.assertEqual(result["fornitura"], _SCHEDA)

    @patch(_PARAM)
    def test_contratto_senza_ba_nessuna_scheda(self, mock_param_cls):
        mock_param_cls.return_value.get_defaults.return_value = {}
        with patch(_RESOLVER_CONN):
            result = fn_get_contratto_form_defaults(billing_account_id=None)
        self.fornitura.assert_not_called()
        self.assertIsNone(result["fornitura"])

    @patch(_PARAM)
    def test_contratto_no_ba_solo_parameters(self, mock_param_cls):
        # Scopo: Senza BA il payload contiene solo i default da parameter
        #        (default_data, default_valido_dal). Tutti i campi BA-derived
        #        restano None.
        mock_param_cls.return_value.get_defaults.return_value = {
            "VENDITE_CONTRATTO_DEFAULT_VALIDO_DAL_LEAD_GG": "0",
            "VENDITE_CONTRATTO_DEFAULT_DATA_LEAD_GG": "0",
        }
        result = fn_get_contratto_form_defaults(billing_account_id=None)
        self.assertEqual(result["billing_account_id"], None)
        self.assertEqual(result["categoria_cliente_id_snapshot"], None)
        self.assertEqual(result["default_data"], oggi_aziendale().isoformat())
        self.assertEqual(result["default_valido_dal"], oggi_aziendale().isoformat())

    @patch(f"{_MOD}.resolve_valuta_default", return_value={})
    @patch(_BA_REPO)
    @patch(_PARAM)
    def test_contratto_con_ba_popola_categoria(
        self, mock_param_cls, mock_ba_repo_cls, _mock_resolve,
    ):
        # Scopo: Con BA, categoria_cliente_id_snapshot e utility/istanza
        #        sono popolati dal lookup BA.
        # Resolver valuta mockato: con valuta_id=None nel lookup il livello 2
        # istanzierebbe un BillingAccountRepository REALE dentro valuta_resolver
        # (il patch _BA_REPO copre solo il modulo service) -> query DB su
        # fn_get_emittente_fiscale_pk(10), che in CI fallisce (nessun EF
        # default seedato per BA 10). La catena valuta e' gia' coperta da
        # test_valuta_resolver (single source of truth).
        mock_param_cls.return_value.get_defaults.return_value = {
            "VENDITE_CONTRATTO_DEFAULT_VALIDO_DAL_LEAD_GG": "0",
            "VENDITE_CONTRATTO_DEFAULT_DATA_LEAD_GG": "0",
        }
        mock_ba_repo_cls.return_value.get_lookup_by_id.return_value = _ba_lookup_row(
            ba_id=10, categoria_id=7,
        )
        result = fn_get_contratto_form_defaults(billing_account_id=10)
        self.assertEqual(result["billing_account_id"], 10)
        self.assertEqual(result["categoria_cliente_id_snapshot"], 7)
        self.assertEqual(result["categoria_cliente_codice"], "STANDARD")
        self.assertEqual(result["utility_id"], 1)
        self.assertEqual(result["istanza_utility_id"], 100)

    @patch(_BA_REPO)
    @patch(_PARAM)
    def test_contratto_ba_inesistente_404(self, mock_param_cls, mock_ba_repo_cls):
        # Scopo: BA non trovato -> E_VENDITE_NOT_FOUND.
        mock_param_cls.return_value.get_defaults.return_value = {}
        mock_ba_repo_cls.return_value.get_lookup_by_id.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            fn_get_contratto_form_defaults(billing_account_id=999)
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")

    @patch(_RESOLVER_CONN)
    @patch(_PARAM)
    def test_contratto_param_int_fallback(self, mock_param_cls, mock_resolver_conn):
        # Scopo: parameter mancante -> il service usa il fallback hardcoded
        #        (0 per i lead_gg). Niente raise.
        mock_param_cls.return_value.get_defaults.return_value = {}
        # Resolver livello 4: nessun gestore configurato -> {} silente.
        cur = MagicMock()
        cur.fetchone.return_value = None
        mock_resolver_conn.cursor.return_value.__enter__.return_value = cur
        result = fn_get_contratto_form_defaults(billing_account_id=None)
        self.assertEqual(result["default_data"], oggi_aziendale().isoformat())

    @patch(_BA_REPO)
    @patch(_PARAM)
    def test_contratto_valuta_dal_ba(self, mock_param_cls, mock_ba_repo_cls):
        # Scopo: BA con valuta_id valorizzata -> il payload espone valuta_id
        #        + valuta_codice + valuta_descrizione (livello 1 resolver).
        mock_param_cls.return_value.get_defaults.return_value = {}
        mock_ba_repo_cls.return_value.get_lookup_by_id.return_value = _ba_lookup_row(
            valuta_id=1,
        )
        result = fn_get_contratto_form_defaults(billing_account_id=10)
        self.assertEqual(result["valuta_id"], 1)
        self.assertEqual(result["valuta_codice"], "EUR")
        self.assertEqual(result["valuta_descrizione"], "Euro")


# ──────────────────────────────────────────────────────────
# Offerte form-defaults
# ──────────────────────────────────────────────────────────


class TestOffertaFormDefaults(TestCase):

    def setUp(self):
        self.fornitura = _finge_fornitura(self)

    @patch(_BA_REPO)
    def test_offerta_scheda_fornitura_dal_cliente(self, mock_ba_repo_cls):
        # Scopo: stessa scheda del contratto, dalla stessa sede.
        mock_ba_repo_cls.return_value.get_lookup_by_id.return_value = _ba_lookup_row(valuta_id=1)
        result = fn_get_offerta_form_defaults(billing_account_id=10)
        self.fornitura.assert_called_once_with(100, 1)
        self.assertEqual(result["fornitura"], _SCHEDA)

    @patch(_RESOLVER_CONN)
    def test_offerta_senza_ba_nessuna_scheda(self, _mock_resolver_conn):
        result = fn_get_offerta_form_defaults(billing_account_id=None)
        self.fornitura.assert_not_called()
        self.assertIsNone(result["fornitura"])

    @patch(_RESOLVER_CONN)
    def test_offerta_no_ba_no_user_payload_vuoto(self, mock_resolver_conn):
        # Scopo: nessun BA + nessun user + nessun gestore -> payload con
        #        tutti i campi a None (BA-derived + valuta).
        cur = MagicMock()
        cur.fetchone.return_value = None
        mock_resolver_conn.cursor.return_value.__enter__.return_value = cur
        result = fn_get_offerta_form_defaults(billing_account_id=None)
        self.assertEqual(result["billing_account_id"], None)
        self.assertEqual(result["valuta_id"], None)
        self.assertEqual(result["categoria_cliente_id_snapshot"], None)
        self.assertEqual(result["utility_id"], None)

    @patch(_BA_REPO)
    def test_offerta_con_ba_popola_categoria_e_valuta(self, mock_ba_repo_cls):
        # Scopo: BA con valuta_id valorizzata -> popola categoria_cliente,
        #        utility/istanza e valuta dal livello 1 resolver.
        mock_ba_repo_cls.return_value.get_lookup_by_id.return_value = _ba_lookup_row(
            ba_id=10, categoria_id=7, valuta_id=1,
        )
        result = fn_get_offerta_form_defaults(billing_account_id=10)
        self.assertEqual(result["billing_account_id"], 10)
        self.assertEqual(result["categoria_cliente_id_snapshot"], 7)
        self.assertEqual(result["utility_id"], 1)
        self.assertEqual(result["istanza_utility_id"], 100)
        self.assertEqual(result["valuta_id"], 1)
        self.assertEqual(result["valuta_codice"], "EUR")

    @patch(_BA_REPO)
    def test_offerta_ba_inesistente_404(self, mock_ba_repo_cls):
        # Scopo: BA non trovato -> E_VENDITE_NOT_FOUND.
        mock_ba_repo_cls.return_value.get_lookup_by_id.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            fn_get_offerta_form_defaults(billing_account_id=999)
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")


class TestOrdineFormDefaults(TestCase):

    @patch(_RESOLVER_CONN)
    def test_ordine_no_ba_no_user_payload_vuoto(self, mock_resolver_conn):
        # Scopo: nessun BA + nessun user + nessun gestore -> payload con
        #        utility/valuta a None (utility globale la risolve il FE).
        cur = MagicMock()
        cur.fetchone.return_value = None
        mock_resolver_conn.cursor.return_value.__enter__.return_value = cur
        result = fn_get_ordine_form_defaults(billing_account_id=None)
        self.assertEqual(result["billing_account_id"], None)
        self.assertEqual(result["valuta_id"], None)
        self.assertEqual(result["utility_id"], None)

    @patch(_BA_REPO)
    def test_ordine_con_ba_popola_utility_valuta_e_pagamento(self, mock_ba_repo_cls):
        # Scopo: BA con valuta -> popola utility/istanza + valuta (resolver L1) +
        #        termine/modalita pagamento dall'anagrafica cliente del BA.
        mock_ba_repo_cls.return_value.get_lookup_by_id.return_value = _ba_lookup_row(
            ba_id=10, categoria_id=7, valuta_id=1,
        )
        mock_ba_repo_cls.return_value.get_cliente_defaults.return_value = {
            "termine_pagamento_id": 3,
            "termine_pagamento_codice": "30GG",
            "modalita_pagamento_id": 5,
            "modalita_pagamento_codice": "BB",
            "iva_id": 99,  # l'ordine NON ha iva in testata: deve essere ignorata
        }
        result = fn_get_ordine_form_defaults(billing_account_id=10)
        self.assertEqual(result["billing_account_id"], 10)
        self.assertEqual(result["utility_id"], 1)
        self.assertEqual(result["istanza_utility_id"], 100)
        self.assertEqual(result["valuta_id"], 1)
        self.assertEqual(result["valuta_codice"], "EUR")
        self.assertEqual(result["termine_pagamento_id"], 3)
        self.assertEqual(result["modalita_pagamento_id"], 5)
        # iva non e' una chiave del payload ordine (testata senza IVA).
        self.assertNotIn("iva_id", result)

    @patch(_BA_REPO)
    def test_ordine_ba_inesistente_404(self, mock_ba_repo_cls):
        # Scopo: BA non trovato -> E_VENDITE_NOT_FOUND.
        mock_ba_repo_cls.return_value.get_lookup_by_id.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            fn_get_ordine_form_defaults(billing_account_id=999)
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")


# ──────────────────────────────────────────────────────────
# DDT form-defaults
# ──────────────────────────────────────────────────────────


class TestDdtFormDefaults(TestCase):

    @patch(_RESOLVER_CONN)
    def test_ddt_no_ba_no_user_payload_vuoto(self, mock_resolver_conn):
        # Scopo: nessun BA + nessun user + nessun gestore -> payload con
        #        utility/valuta a None (utility globale la risolve il FE).
        cur = MagicMock()
        cur.fetchone.return_value = None
        mock_resolver_conn.cursor.return_value.__enter__.return_value = cur
        result = fn_get_ddt_form_defaults(billing_account_id=None)
        self.assertEqual(result["billing_account_id"], None)
        self.assertEqual(result["valuta_id"], None)
        self.assertEqual(result["utility_id"], None)

    @patch(_BA_REPO)
    def test_ddt_con_ba_popola_utility_e_valuta(self, mock_ba_repo_cls):
        # Scopo: BA con valuta -> popola utility/istanza + valuta (resolver L1).
        #        Il DDT NON ha termini/modalita di pagamento in testata: non li
        #        chiede al cliente (nessun get_cliente_defaults).
        mock_ba_repo_cls.return_value.get_lookup_by_id.return_value = _ba_lookup_row(
            ba_id=10, categoria_id=7, valuta_id=1,
        )
        result = fn_get_ddt_form_defaults(billing_account_id=10)
        self.assertEqual(result["billing_account_id"], 10)
        self.assertEqual(result["utility_id"], 1)
        self.assertEqual(result["istanza_utility_id"], 100)
        self.assertEqual(result["valuta_id"], 1)
        self.assertEqual(result["valuta_codice"], "EUR")
        # Il DDT non ha pagamento in testata: nessuna chiave termine/modalita.
        self.assertNotIn("termine_pagamento_id", result)
        self.assertNotIn("modalita_pagamento_id", result)
        mock_ba_repo_cls.return_value.get_cliente_defaults.assert_not_called()

    @patch(_BA_REPO)
    def test_ddt_ba_inesistente_404(self, mock_ba_repo_cls):
        # Scopo: BA non trovato -> E_VENDITE_NOT_FOUND.
        mock_ba_repo_cls.return_value.get_lookup_by_id.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            fn_get_ddt_form_defaults(billing_account_id=999)
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")


# ──────────────────────────────────────────────────────────
# Preventivi form-defaults
# ──────────────────────────────────────────────────────────


class TestPreventivoFormDefaults(TestCase):

    @patch(_RESOLVER_CONN)
    @patch(_PARAM)
    def test_preventivo_no_ba_solo_parameters(
        self, mock_param_cls, mock_resolver_conn,
    ):
        # Scopo: Senza BA il payload calcola validita_al = oggi + N.
        mock_param_cls.return_value.get_defaults.return_value = {
            "VENDITE_PREVENTIVO_DEFAULT_VALIDITA_GG": "30",
        }
        # Resolver livello 4: nessun gestore configurato (-> {} silente).
        cur = MagicMock()
        cur.fetchone.return_value = None
        mock_resolver_conn.cursor.return_value.__enter__.return_value = cur
        result = fn_get_preventivo_form_defaults(billing_account_id=None)
        self.assertEqual(result["billing_account_id"], None)
        expected = (oggi_aziendale() + timedelta(days=30)).isoformat()
        self.assertEqual(result["default_validita_al"], expected)
        self.assertEqual(result["valuta_id"], None)
        self.assertEqual(result["termine_pagamento_id"], None)

    @patch(_BA_REPO)
    @patch(_PARAM)
    def test_preventivo_con_ba_termini_da_cliente(
        self, mock_param_cls, mock_ba_repo_cls,
    ):
        # Scopo: termine_pagamento_id/modalita_pagamento_id arrivano dal cliente
        #        del BA; valuta dal BA stesso (LOOKUP_SELECT_COLUMNS la espone).
        # ⛔ `iva_id` NON e' piu' fra i defaults (I0/D7-bis, decisione Q3 del
        #    2026-08-29): la colonna e' uscita da `anagrafiche.clienti`. Il dict
        #    del repo qui sotto NON la porta, ed e' il punto — se un giorno
        #    tornasse, il payload la ri-esporrebbe senza che nessuno se ne
        #    accorga. L'assenza e' asserita sotto.
        mock_param_cls.return_value.get_defaults.return_value = {
            "VENDITE_PREVENTIVO_DEFAULT_VALIDITA_GG": "30",
        }
        ba_repo = mock_ba_repo_cls.return_value
        ba_repo.get_lookup_by_id.return_value = _ba_lookup_row(valuta_id=1)
        ba_repo.get_cliente_defaults.return_value = {
            "termine_pagamento_id": 12,
            "termine_pagamento_codice": "30GG",
            "termine_pagamento_descrizione": "30 giorni",
            "modalita_pagamento_id": 5,
            "modalita_pagamento_codice": "BONIFICO",
            "modalita_pagamento_descrizione": "Bonifico bancario",
        }
        result = fn_get_preventivo_form_defaults(billing_account_id=10)
        self.assertEqual(result["termine_pagamento_id"], 12)
        self.assertEqual(result["modalita_pagamento_id"], 5)
        for chiave in ("iva_id", "iva_codice", "iva_descrizione"):
            self.assertNotIn(chiave, result)
        # Valuta dal BA (no fallback emittente perche' BA ha valuta_id=1).
        self.assertEqual(result["valuta_id"], 1)
        self.assertEqual(result["valuta_codice"], "EUR")
        ba_repo.get_emittente_valuta.assert_not_called()

    @patch(f"{_MOD}.resolve_valuta_default")
    @patch(_BA_REPO)
    @patch(_PARAM)
    def test_preventivo_valuta_da_emittente_se_ba_null(
        self, mock_param_cls, mock_ba_repo_cls, mock_resolve,
    ):
        # Scopo: BA senza valuta -> il service delega al BB
        #        resolve_valuta_default che applica il fallback EF-del-BA.
        #        La logica di fallback e' verificata in test_valuta_resolver
        #        (single source of truth): qui ci basta che il service la
        #        invochi con BA pre-fetched + auth_user_id.
        mock_param_cls.return_value.get_defaults.return_value = {}
        ba_repo = mock_ba_repo_cls.return_value
        ba_repo.get_lookup_by_id.return_value = _ba_lookup_row(valuta_id=None)
        ba_repo.get_cliente_defaults.return_value = {}
        mock_resolve.return_value = {
            "valuta_id": 1, "valuta_codice": "EUR", "valuta_descrizione": "Euro",
        }
        result = fn_get_preventivo_form_defaults(billing_account_id=10)
        self.assertEqual(result["valuta_id"], 1)
        self.assertEqual(result["valuta_codice"], "EUR")
        # Resolver invocato con BA pre-fetched (ottimizzazione: niente
        # seconda query in get_lookup_by_id).
        _, kwargs = mock_resolve.call_args
        self.assertEqual(kwargs["billing_account_id"], 10)
        self.assertIsNotNone(kwargs["ba_obj"])

    @patch(f"{_MOD}.resolve_valuta_default")
    @patch(_PARAM)
    def test_preventivo_no_ba_valuta_da_user_ef(
        self, mock_param_cls, mock_resolve,
    ):
        # Scopo: senza BA il service delega comunque al BB resolve_valuta_default
        #        passando auth_user_id; il resolver applica il fallback user EF
        #        (gestore globale per admin globale).
        mock_param_cls.return_value.get_defaults.return_value = {}
        mock_resolve.return_value = {
            "valuta_id": 1, "valuta_codice": "EUR", "valuta_descrizione": "Euro",
        }
        result = fn_get_preventivo_form_defaults(
            billing_account_id=None, auth_user_id=99,
        )
        self.assertEqual(result["valuta_id"], 1)
        self.assertEqual(result["valuta_codice"], "EUR")
        # Resolver chiamato con BA None e ba_obj None (no pre-fetch).
        mock_resolve.assert_called_once_with(
            billing_account_id=None, ba_obj=None, auth_user_id=99,
        )


# ──────────────────────────────────────────────────────────
# Listini-versioni form-defaults
# ──────────────────────────────────────────────────────────


class TestListinoVersioneFormDefaults(TestCase):

    @patch(_LISTINI_REPO)
    @patch(_PARAM)
    def test_versione_new_defaults(self, mock_param_cls, mock_repo_cls):
        # Scopo: Payload include default_valido_dal (oggi+lead) ed esistenti BOZZE.
        mock_param_cls.return_value.get_defaults.return_value = {
            "VENDITE_LISTINI_NEW_VERSIONE_LEAD_GG": "0",
        }
        repo = mock_repo_cls.return_value
        repo.get_listino.return_value = {"id": 12}
        repo.list_versioni.return_value = [
            {"id": 33, "stato": "BOZZA", "codice_versione": "v_draft"},
            {"id": 30, "stato": "ATTIVA", "codice_versione": "v1"},
        ]
        result = fn_get_versione_new_defaults(listino_id=12)
        self.assertEqual(result["listino_id"], 12)
        self.assertEqual(result["default_valido_dal"], oggi_aziendale().isoformat())
        self.assertTrue(result["has_existing_draft"])
        self.assertEqual(len(result["existing_drafts"]), 1)
        self.assertEqual(result["existing_drafts"][0]["codice_versione"], "v_draft")

    @patch(_LISTINI_REPO)
    @patch(_PARAM)
    def test_versione_clone_codice_con_suffisso(self, mock_param_cls, mock_repo_cls):
        # Scopo: codice clone = source_codice + suffisso parameter.
        mock_param_cls.return_value.get_defaults.return_value = {
            "VENDITE_LISTINI_CLONE_VERSIONE_LEAD_GG": "1",
            "VENDITE_LISTINI_CLONE_VERSIONE_CODICE_SUFFIX": "-bis",
        }
        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {
            "id": 33,
            "codice_versione": "v1",
            "valido_dal": date(2026, 1, 1),
            "valido_al": None,
        }
        result = fn_get_versione_clone_defaults(listino_id=12, src_versione_id=33)
        self.assertEqual(result["default_codice_versione"], "v1-bis")
        # ⛔ D2 la dice il verbo del DB (§16.16, BE-C3): niente copia qui.
        self.assertNotIn("min_valido_dal", result)
        self.assertEqual(
            result["default_valido_dal"],
            (oggi_aziendale() + timedelta(days=1)).isoformat(),
        )
        # is_retroactive_default deve riflettere SOLO default_valido_dal vs oggi.
        # Lead_gg=+1 -> default in futuro -> non retroattivo.
        self.assertFalse(result["is_retroactive_default"])

    @patch(_LISTINI_REPO)
    @patch(_PARAM)
    def test_versione_clone_retroactive_default_anche_se_src_senza_valido_dal(
        self, mock_param_cls, mock_repo_cls,
    ):
        # Regressione B1: il flag is_retroactive_default deve dipendere SOLO
        # da default_valido_dal < today, indipendentemente da src.valido_dal.
        # Lead_gg=-5 (passato) -> default retroattivo anche con src senza data.
        mock_param_cls.return_value.get_defaults.return_value = {
            "VENDITE_LISTINI_CLONE_VERSIONE_LEAD_GG": "-5",
        }
        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {
            "id": 33,
            "codice_versione": "v1",
            "valido_dal": None,  # nessuna data sulla sorgente
            "valido_al": None,
        }
        result = fn_get_versione_clone_defaults(listino_id=12, src_versione_id=33)
        self.assertTrue(result["is_retroactive_default"])

    @patch(_LISTINI_REPO)
    @patch(_PARAM)
    def test_versione_close_default_oggi_se_no_chiusura(self, mock_param_cls, mock_repo_cls):
        # Scopo: Versione senza valido_al -> default = oggi + lead_gg.
        mock_param_cls.return_value.get_defaults.return_value = {
            "VENDITE_LISTINI_CLOSE_VERSIONE_LEAD_GG": "0",
        }
        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {
            "id": 33,
            "stato": "ATTIVA",
            "valido_al": None,
        }
        result = fn_get_versione_close_defaults(listino_id=12, versione_id=33)
        self.assertEqual(result["default_valido_al"], oggi_aziendale().isoformat())
        self.assertEqual(result["current_valido_al"], None)
        self.assertFalse(result["has_existing_chiusura"])
        # ⛔ La fine nel passato la rifiuta il verbo «Chiudi» (C-2 = a): niente copia.
        self.assertNotIn("min_valido_al", result)

    @patch(_LISTINI_REPO)
    @patch(_PARAM)
    def test_versione_close_usa_existing_se_presente(self, mock_param_cls, mock_repo_cls):
        # Scopo: Versione con valido_al gia' programmata -> default = quello.
        mock_param_cls.return_value.get_defaults.return_value = {}
        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {
            "id": 33,
            "stato": "ATTIVA",
            "valido_al": date(2027, 12, 31),
        }
        result = fn_get_versione_close_defaults(listino_id=12, versione_id=33)
        self.assertEqual(result["default_valido_al"], "2027-12-31")
        self.assertEqual(result["current_valido_al"], "2027-12-31")
        self.assertTrue(result["has_existing_chiusura"])

    @patch(_LISTINI_REPO)
    @patch(_PARAM)
    def test_versione_close_fine_passata_non_riproposta(self, mock_param_cls, mock_repo_cls):
        # Scopo: Fine gia' passata (ATTIVA in attesa del job) -> il default e'
        #        oggi + lead_gg, non la fine vecchia che il verbo rifiuterebbe;
        #        la fine attuale resta esposta in `current_valido_al`.
        mock_param_cls.return_value.get_defaults.return_value = {
            "VENDITE_LISTINI_CLOSE_VERSIONE_LEAD_GG": "0",
        }
        ieri = oggi_aziendale() - timedelta(days=1)
        mock_repo_cls.return_value.get_versione.return_value = {
            "id": 33, "stato": "ATTIVA", "valido_al": ieri,
        }
        result = fn_get_versione_close_defaults(listino_id=12, versione_id=33)
        self.assertEqual(result["default_valido_al"], oggi_aziendale().isoformat())
        self.assertEqual(result["current_valido_al"], ieri.isoformat())
        self.assertTrue(result["has_existing_chiusura"])

    @patch(_LISTINI_REPO)
    @patch(_PARAM)
    def test_listino_inesistente_404(self, mock_param_cls, mock_repo_cls):
        # Scopo: listino non trovato -> E_VENDITE_NOT_FOUND in new_defaults.
        mock_param_cls.return_value.get_defaults.return_value = {}
        mock_repo_cls.return_value.get_listino.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            fn_get_versione_new_defaults(listino_id=999)
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")

    @patch(_LISTINI_REPO)
    @patch(_PARAM)
    def test_versione_inesistente_404(self, mock_param_cls, mock_repo_cls):
        # Scopo: versione non trovata -> E_VENDITE_NOT_FOUND in clone/close.
        mock_param_cls.return_value.get_defaults.return_value = {}
        mock_repo_cls.return_value.get_versione.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            fn_get_versione_clone_defaults(listino_id=12, src_versione_id=999)
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")
        with self.assertRaises(ServiceError) as ctx:
            fn_get_versione_close_defaults(listino_id=12, versione_id=999)
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")
