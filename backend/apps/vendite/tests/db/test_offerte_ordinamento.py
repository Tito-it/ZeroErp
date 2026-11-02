# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: l'ORDER BY della lista offerte passa dal BB `sql_order_clause`.
# Note: mock su connection.cursor — nessun DB (regola CI di AGENTS.md).
# ------------------------------------------------------------
"""⛔ PERCHE' QUESTO FILE ESISTE.

Fino al 2026-09-26 `OfferteRepository.list_offerte` scriveva la direzione a
mano: `"ASC" if order_dir.upper() == "ASC" else "DESC"`. Qualunque valore
estraneo (`giu`, `ASC NULLS LAST`) diventava DESC in silenzio, e lo spareggio
`v.id` restava DESC anche ordinando ASC. Ora la clausola la scrive il BB.

Indice test:

 1) test_desc_maiuscolo_ammesso_e_spareggio_allineato
 2) test_asc_allinea_lo_spareggio
 3) test_direzione_estranea_rifiutata_senza_query
 4) test_data_senza_direzione_parte_desc   — `colonne_desc`, regola del 02/09
"""

import unittest
from unittest.mock import patch

from apps.vendite.db.offerte_repository import OfferteRepository
from apps.vendite.tests._helpers.mock_cursor import mock_cursor as _mock_cursor


def _sql(**kwargs) -> str:
    with patch("apps.vendite.db.offerte_repository.connection.cursor") as fab:
        fab.return_value = _mock_cursor(fetchall=[], description=[])
        OfferteRepository().list_offerte(limit=10, offset=0, **kwargs)
        return fab.return_value.execute.call_args[0][0]


class OfferteOrdinamentoTests(unittest.TestCase):

    # Scopo: `DESC` maiuscolo e' la stessa cosa di `desc`.
    def test_desc_maiuscolo_ammesso_e_spareggio_allineato(self):
        self.assertIn(
            "ORDER BY v.codice DESC NULLS LAST, v.id DESC",
            _sql(order_by="codice", order_dir="DESC"),
        )

    # Scopo: prima lo spareggio era DESC fisso anche ordinando ASC.
    def test_asc_allinea_lo_spareggio(self):
        self.assertIn(
            "ORDER BY v.codice ASC NULLS FIRST, v.id ASC",
            _sql(order_by="codice", order_dir="asc"),
        )

    # Scopo: ⛔ una direzione estranea e' `ValueError`, non DESC; la query non
    #        parte.
    def test_direzione_estranea_rifiutata_senza_query(self):
        with patch("apps.vendite.db.offerte_repository.connection.cursor") as fab:
            with self.assertRaisesRegex(ValueError, "order_dir_invalid"):
                OfferteRepository().list_offerte(order_by="codice", order_dir="giu")
            fab.assert_not_called()

    # Scopo: una colonna data senza direzione parte dalla piu' recente.
    def test_data_senza_direzione_parte_desc(self):
        self.assertIn(
            "ORDER BY v.data_emissione DESC NULLS LAST, v.id DESC",
            _sql(order_by="data_emissione"),
        )
