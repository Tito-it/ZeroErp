# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test dei lookup statici vendite (Fase 2 refactor frontend vendite).
#        Difesa coerenza enum descrizioni vs whitelist gia' presenti nei
#        service di dominio (single source of truth): se qualcuno aggiunge
#        un codice senza propagare alla mappa descrizioni, il test fallisce
#        in CI prima del runtime.
# ------------------------------------------------------------

"""
Indice test:
1) test_tipi_variazione_contratto_coverage — codici lookup == _TIPI_VARIAZIONE
2) test_tipi_variazione_promo_coverage     — codici lookup == promo._TIPI_VARIAZIONE
3) test_ambiti_contratto_coverage          — codici lookup == _AMBITI_VALIDI
4) test_payload_shape                       — codice/descrizione/ordering presenti
5) test_listini_selezionabili_delega_repository — fn delega utility ed emittente, senza trasformazioni, a ListiniRepository.list_lookup_selezionabili
"""

from unittest import TestCase
from unittest.mock import ANY, patch

from apps.vendite.services.contratti_service import (
    _AMBITI_VALIDI,
    _TIPI_VARIAZIONE_GLOBALE_AMMESSI as _TIPI_VARIAZIONE,
)
from apps.vendite.services.promo_articoli_service import (
    _TIPI_VARIAZIONE as PROMO_TIPI_VARIAZIONE,
)
from apps.vendite.services.vendite_lookups_service import (
    fn_list_ambiti_contratto,
    fn_list_listini_selezionabili,
    fn_list_tipi_variazione_contratto,
    fn_list_tipi_variazione_promo,
)


def _codes(rows):
    return frozenset(r["codice"] for r in rows)


class TestVenditeLookupsService(TestCase):

    # Scopo: i tipi_variazione_contratto del lookup devono coincidere con
    #        la whitelist gia' usata da contratti_service per la validazione.
    def test_tipi_variazione_contratto_coverage(self):
        self.assertEqual(_codes(fn_list_tipi_variazione_contratto()), _TIPI_VARIAZIONE)

    # Scopo: i tipi_variazione_promo del lookup devono coincidere con la
    #        whitelist gia' usata da promo_articoli_service. PREZZO_FISSO
    #        e' ammesso solo qui (vincolo CHECK DB).
    def test_tipi_variazione_promo_coverage(self):
        self.assertEqual(_codes(fn_list_tipi_variazione_promo()), PROMO_TIPI_VARIAZIONE)
        self.assertIn("PREZZO_FISSO", _codes(fn_list_tipi_variazione_promo()))
        self.assertNotIn("PREZZO_FISSO", _codes(fn_list_tipi_variazione_contratto()))

    # Scopo: ambiti contratto allineati con _AMBITI_VALIDI di contratti_service.
    def test_ambiti_contratto_coverage(self):
        self.assertEqual(_codes(fn_list_ambiti_contratto()), _AMBITI_VALIDI)

    # Scopo: shape uniforme dei payload (codice + descrizione + ordering int).
    def test_payload_shape(self):
        for fn in (
            fn_list_tipi_variazione_contratto,
            fn_list_tipi_variazione_promo,
            fn_list_ambiti_contratto,
        ):
            for row in fn():
                self.assertIn("codice", row)
                self.assertTrue(row["descrizione"])
                self.assertIsInstance(row["ordering"], int)

    # Scopo: fn_list_listini_selezionabili e' thin wrapper sul repository:
    #        passa utility ed emittente del form com'erano e non trasforma
    #        niente. La regola la dice il DB (`vendite.fn_listini_selezionabili`).
    @patch(
        "apps.vendite.db.listini_repository.ListiniRepository."
        "list_lookup_selezionabili",
        return_value=[
            {"id": 1, "codice": "STD", "descrizione": "Listino standard"},
            {"id": 2, "codice": "PREM", "descrizione": "Listino premium"},
        ], autospec=True,
    )
    def test_listini_selezionabili_delega_repository(self, mock_repo):
        result = fn_list_listini_selezionabili(3, 41)
        # Mock `autospec` di un metodo: il primo argomento e' `self`.
        mock_repo.assert_called_once_with(ANY, 3, 41)
        self.assertEqual(len(result), 2)
        self.assertEqual(set(result[0].keys()), {"id", "codice", "descrizione"})
        self.assertEqual([r["codice"] for r in result], ["STD", "PREM"])
