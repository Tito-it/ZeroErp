# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari service conteggio lotti/mese (badge sidebar registro
#        lotti, stile Lente Competenza). Mock repository, nessun DB.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) LottiMensileServiceTests.test_dodici_mesi_zero_riempiti_in_ordine
2) LottiMensileServiceTests.test_conteggi_mappati_sul_mese_giusto
3) LottiMensileServiceTests.test_anno_inoltrato_e_scope_passthrough
4) LottiMensileServiceTests.test_anno_fuori_range
"""

from unittest import TestCase
from unittest.mock import patch

from apps.core.services.service_errors import ServiceError
from apps.vendite.services import vendite_service
from apps.vendite.services.vendite_service import fn_lotti_mensile


class LottiMensileServiceTests(TestCase):

    # Scopo: sempre 12 mesi in ordine (gen..dic), 0-riempiti dove il repo non
    #        torna nulla; competenza YYYY-MM-01 come chiave stabile per il FE.
    @patch.object(
        vendite_service.VenditeRepository, "count_lotti_per_mese", autospec=True, return_value={},
    )
    def test_dodici_mesi_zero_riempiti_in_ordine(self, _mock_repo):
        out = fn_lotti_mensile(anno=2026)
        self.assertEqual(out["anno"], 2026)
        mesi = out["mesi"]
        self.assertEqual(len(mesi), 12)
        self.assertEqual(mesi[0]["competenza_mese"], "2026-01-01")
        self.assertEqual(mesi[11]["competenza_mese"], "2026-12-01")
        self.assertTrue(all(m["n_lotti"] == 0 for m in mesi))

    # Scopo: i conteggi del repo finiscono sul mese giusto (mese 1-based → idx 0).
    @patch.object(
        vendite_service.VenditeRepository,
        "count_lotti_per_mese", autospec=True,
        return_value={1: 3, 7: 5},
    )
    def test_conteggi_mappati_sul_mese_giusto(self, _mock_repo):
        mesi = fn_lotti_mensile(anno=2026)["mesi"]
        self.assertEqual(mesi[0]["n_lotti"], 3)   # gennaio
        self.assertEqual(mesi[6]["n_lotti"], 5)   # luglio
        self.assertEqual(mesi[1]["n_lotti"], 0)   # febbraio (assente → 0)

    # Scopo: anno e scope operatore inoltrati al repository senza alterazioni.
    @patch.object(
        vendite_service.VenditeRepository, "count_lotti_per_mese", autospec=True, return_value={},
    )
    def test_anno_inoltrato_e_scope_passthrough(self, mock_repo):
        fn_lotti_mensile(anno=2025, auth_user_id=42)
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual(kwargs["anno"], 2025)
        self.assertEqual(kwargs["auth_user_id"], 42)

    # Scopo: anno fuori range → E_VENDITE_VALIDATION (niente query su anno assurdo).
    def test_anno_fuori_range(self):
        for anno in (1999, 2101):
            with self.assertRaises(ServiceError) as ctx:
                fn_lotti_mensile(anno=anno)
            self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
