# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: BE30 di brief-db-revisione-ui (Q51 (c), deciso da Tid il
#        2026-11-22): sulle due code dei resi, quando l'ordinamento di
#        partenza (o il clic dell'operatore) nomina la PRIMA colonna del
#        default (`data`, desc), l'ORDER BY e' quello di oggi, criteri
#        successivi compresi: le righe di un reso restano raggruppate e nel
#        loro ordine.
# Note: ⭐ Il codice lo fa gia' (2026-11-22): `_list_coda` chiude con una coda
#       FISSA (`v.reso_id DESC, v.resi_riga_id ASC`), indipendente dalla
#       colonna chiesta. Questo e' il presidio che la tiene: portare la coda
#       su `sql_order_clause` la sostituirebbe con il solo spareggio, senza
#       errore. Senza DB: `fetch_paged_with_total` e' finto, l'SQL si legge
#       da cio' che il repository gli passa.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) CriteriSuccessiviResiTests.test_da_accreditare
2) CriteriSuccessiviResiTests.test_da_riconsegnare
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.vendite.db.resi_repository import ResiRepository

_MOD = "apps.vendite.db.resi_repository"


# Scopo: la sola clausola `ORDER BY … LIMIT` dell'SQL passato al BB di lettura.
def _order_by(sql: str) -> str:
    return sql.split("ORDER BY", 1)[1].split("LIMIT", 1)[0].strip()


class CriteriSuccessiviResiTests(SimpleTestCase):
    def _clausola(self, chiama: Callable[..., Any], **ordine: Any) -> str:
        with patch(f"{_MOD}.fetch_paged_with_total", return_value=([], 0)) as lettura:
            chiama(
                billing_account_id=None, data_da=None, data_al=None,
                auth_user_id=None, limit=10, offset=0, **ordine,
            )
        return _order_by(str(lettura.call_args.args[0]))

    # Il default della view (`order_by="data"`, nessun verso) e la proposta del
    # preset (`data`, `desc`) danno la STESSA clausola, coda compresa.
    def _stessa(self, chiama: Callable[..., Any]) -> None:
        default = self._clausola(chiama, order_by="data", order_dir=None)
        proposto = self._clausola(chiama, order_by="data", order_dir="desc")
        self.assertEqual(proposto, default)
        self.assertIn("v.reso_id DESC, v.resi_riga_id ASC", default)

    def test_da_accreditare(self) -> None:
        self._stessa(ResiRepository().list_da_accreditare)

    def test_da_riconsegnare(self) -> None:
        self._stessa(ResiRepository().list_da_riconsegnare)
