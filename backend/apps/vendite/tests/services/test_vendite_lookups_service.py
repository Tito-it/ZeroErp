# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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
"""

from unittest import TestCase

from apps.vendite.services.contratti_service import _AMBITI_VALIDI, _TIPI_VARIAZIONE
from apps.vendite.services.promo_articoli_service import (
    _TIPI_VARIAZIONE as PROMO_TIPI_VARIAZIONE,
)
from apps.vendite.services.vendite_lookups_service import (
    fn_list_ambiti_contratto,
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
