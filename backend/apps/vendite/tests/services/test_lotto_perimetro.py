# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio del cancello di perimetro dei satelliti del lotto
#        (`_lotto_perimetro.lotto_visibile`): un lotto inesistente o fuori
#        scope e' `E_LOTTO_NON_TROVATO` (404) PRIMA di ogni elenco o conteggio.
#        Fino al 2026-10-20 fatture, gruppi, segnalazioni (riepilogo ed elenco)
#        e task-run rispondevano `200` con zero righe, cioe' «lotto vuoto».
#        Repository mockati, nessun accesso DB.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_lotto_non_visibile_e_404_su_ogni_satellite — cinque letture (gli export
   passano dalle stesse): 404, la query dell'elenco non parte, lo scope arriva
2) test_lotto_visibile_restituisce_la_testata
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.service_errors import ServiceError
from apps.vendite.services import pipeline_service, vendite_service
from apps.vendite.services._lotto_perimetro import lotto_visibile


class LottoPerimetroTests(TestCase):

    def test_lotto_non_visibile_e_404_su_ogni_satellite(self) -> None:
        letture = (
            ("fatture", lambda: vendite_service.fn_list_lotto_fatture(lotto_id=7, auth_user_id=3),
             "list_lotto_fatture"),
            ("gruppi", lambda: vendite_service.fn_list_lotto_gruppi(lotto_id=7, auth_user_id=3),
             "list_lotto_gruppi"),
            ("segnalazioni", lambda: pipeline_service.fn_list_lotto_segnalazioni(lotto_id=7, auth_user_id=3),
             "list_lotto_segnalazioni"),
            ("riepilogo", lambda: pipeline_service.fn_get_lotto_segnalazioni_summary(lotto_id=7, auth_user_id=3),
             "get_lotto_segnalazioni_summary"),
            ("task-run", lambda: pipeline_service.fn_get_lotto_task_runs(lotto_id=7, auth_user_id=3),
             "list_lotto_task_runs"),
        )
        for nome, lettura, query in letture:
            with self.subTest(nome), \
                    patch("apps.vendite.db.vendite_repository.VenditeRepository") as vendite_cls, \
                    patch.object(vendite_service, "VenditeRepository", vendite_cls), \
                    patch("apps.vendite.services.pipeline_service.VenditePipelineRepository") as pipe_cls, \
                    patch("apps.vendite.services.lotto_segnalazioni_service.VenditePipelineRepository", pipe_cls):
                vendite_cls.return_value.get_lotto.return_value = None
                with self.assertRaises(ServiceError) as ctx:
                    lettura()
                self.assertEqual(ctx.exception.code, "E_LOTTO_NON_TROVATO")
                vendite_cls.return_value.get_lotto.assert_called_once_with(lotto_id=7, auth_user_id=3)
                getattr(vendite_cls.return_value, query).assert_not_called()
                getattr(pipe_cls.return_value, query).assert_not_called()

    def test_lotto_visibile_restituisce_la_testata(self) -> None:
        repo = MagicMock()
        repo.get_lotto.return_value = {"id": 7}
        self.assertEqual(lotto_visibile(lotto_id=7, auth_user_id=3, repository=repo), {"id": 7})
