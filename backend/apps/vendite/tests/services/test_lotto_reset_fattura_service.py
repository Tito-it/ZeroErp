# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test reset singola fattura lotto DRAFT.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) LottoResetFatturaServiceUnitTests.test_reset_lotto_fattura_draft_requires_ids
2) LottoResetFatturaServiceUnitTests.test_reset_lotto_fattura_draft_ok
"""

from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.lotto_reset_service import LottoResetService


class LottoResetFatturaServiceUnitTests(SimpleTestCase):
    # Scopo: Verifica il caso `test_reset_lotto_fattura_draft_requires_ids`.
    def test_reset_lotto_fattura_draft_requires_ids(self):
        repo = MagicMock()
        service = LottoResetService(repository=repo)

        with self.assertRaises(ServiceError) as exc:
            service.elimina_fattura_draft_da_lotto(lotto_id=0, fattura_id=0)

        self.assertEqual(exc.exception.code, "E_RESET_LOTTO_FATTURA_VALIDATION")
        repo.elimina_fattura_draft_da_lotto.assert_not_called()

    # Scopo: Verifica il caso `test_reset_lotto_fattura_draft_ok`.
    def test_reset_lotto_fattura_draft_ok(self):
        repo = MagicMock()
        repo.elimina_fattura_draft_da_lotto.return_value = {
            "updated_attivita": 1,
            "deleted_fatture": 1,
            "deleted_righe": 1,
        }
        service = LottoResetService(repository=repo)

        result = service.elimina_fattura_draft_da_lotto(lotto_id=10, fattura_id=22)

        repo.elimina_fattura_draft_da_lotto.assert_called_once_with(10, 22)
        self.assertEqual(result["deleted_fatture"], 1)
