# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il contesto-pricing di contratto e preventivo legge PRIMA la testata:
#        un documento inesistente o fuori perimetro e' il 404 del dominio, e
#        il contesto non si legge. Fino al 2026-10-20 rispondeva `200 {}`,
#        diversamente da tutte le altre GET del dominio. Repository mockati.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_contratto_inesistente_e_404
2) test_preventivo_inesistente_e_404
"""

from unittest import TestCase
from unittest.mock import patch

from apps.core.services.service_errors import ServiceError


class ContestoPricingPerimetroTests(TestCase):

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_contratto_inesistente_e_404(self, repo_cls) -> None:
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = None
        repo.get_contratto.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().get_contesto_pricing(9)
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")
        repo.resolve_contesto_pricing_contratto.assert_not_called()

    @patch("apps.vendite.services.preventivi_service.PreventiviRepository")
    def test_preventivo_inesistente_e_404(self, repo_cls) -> None:
        from apps.vendite.services import preventivi_service

        repo = repo_cls.return_value
        repo.get_preventivo.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            preventivi_service.get_contesto_pricing(9)
        self.assertEqual(ctx.exception.code, "E_PREV_NOT_FOUND")
        repo.resolve_contesto_pricing.assert_not_called()
