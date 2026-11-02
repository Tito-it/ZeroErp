# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La lista del log email dell'operatore (`GET /core/email/log/`) passa
#        al repository cio' che la lista configurabile manda: ordinamento
#        compreso.
# Note: Repository mockato, nessun DB. Il perimetro (chi vede quale riga) lo
#       prova `core/tests/db/test_email_bozza_invio_db` n. 4.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_l_ordinamento_della_colonna_arriva_al_repository
   ⛔ Fino al 2026-09-26 `order_by`/`order_dir` erano ignorati in silenzio.
2) test_senza_verso_il_registro_si_apre_dal_piu_recente
   Default `data_insert DESC`, come la gemella admin.
"""

import json
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from apps.core.api.email_views import EmailLogOperatoreListView

_REPO = "apps.core.api.email_views.EmailRepository"


class EmailLogOperatoreViewTests(SimpleTestCase):

    # Scopo: chiama la view con la query data; torna gli argomenti di list_logs.
    def _chiama(self, query: str) -> dict:
        with patch(_REPO) as repo:
            repo.return_value.list_logs.return_value = ([], 0)
            richiesta = APIRequestFactory().get(f"/api/v1/core/email/log/{query}")
            view = EmailLogOperatoreListView()
            view.request = view.initialize_request(richiesta)
            view.request.user = MagicMock()
            risposta = view.get(view.request)
        self.assertEqual(json.loads(risposta.content)["data"]["count"], 0)
        return repo.return_value.list_logs.call_args.kwargs

    # 1. La colonna cliccata ordina davvero.
    def test_l_ordinamento_della_colonna_arriva_al_repository(self):
        kwargs = self._chiama("?order_by=destinatario&order_dir=asc&limit=10&offset=20")
        self.assertEqual(kwargs["order_by"], "destinatario")
        self.assertEqual(kwargs["order_dir"], "asc")
        self.assertEqual((kwargs["limit"], kwargs["offset"]), (10, 20))

    # 2. Un registro si legge dal piu' recente. ⭐ Senza verso la view passa
    #    `None` (dal 2026-09-26 `parse_list_params` non inventa piu' "asc"):
    #    il DESC lo applica `EmailRepository.list_logs`, in una sede sola —
    #    prima lo forzava anche la view, con un `or "desc"` gemello.
    def test_senza_verso_il_registro_si_apre_dal_piu_recente(self):
        kwargs = self._chiama("")
        self.assertEqual(kwargs["order_by"], "data_insert")
        self.assertIsNone(kwargs["order_dir"])
