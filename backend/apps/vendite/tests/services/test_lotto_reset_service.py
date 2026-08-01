"""
Indice test eseguiti:
1) LottoResetServiceUnitTests.test_reset_lotto_requires_valid_id
2) LottoResetServiceUnitTests.test_reset_lotto_calls_repository
"""

from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.lotto_reset_service import LottoResetService


class LottoResetServiceUnitTests(SimpleTestCase):
    # Scopo: Verifica il caso `test_reset_lotto_requires_valid_id`.
    def test_reset_lotto_requires_valid_id(self):
        service = LottoResetService(repository=MagicMock())
        with self.assertRaises(ServiceError) as exc:
            service.annulla_lotto_da_draft(0)
        self.assertEqual(exc.exception.code, "E_RESET_LOTTO_VALIDATION")

    # Scopo: Verifica il caso `test_reset_lotto_calls_repository`.
    def test_reset_lotto_calls_repository(self):
        repo = MagicMock()
        repo.annulla_lotto_da_draft.return_value = {
            "updated_lotti": 1,
            "updated_attivita": 2,
            "deleted_fatture": 3,
            "deleted_righe": 4,
        }
        service = LottoResetService(repository=repo)
        result = service.annulla_lotto_da_draft(10)
        repo.annulla_lotto_da_draft.assert_called_once_with(10)
        self.assertEqual(result["updated_lotti"], 1)
