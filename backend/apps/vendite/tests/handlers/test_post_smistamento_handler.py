# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per l'handler flusso `vendita.post_smistamento` —
#        completamento SMISTAMENTO MERCE-ONLY (bivio-per-esito rev.3). DB mockato
#        (SimpleTestCase + patch).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_ordine_presente_aggancia — ordine merce → aggancio COLLEGATO, nessun
   flusso creato (9013/9014 compaiono via roadmap, non li crea l'handler)
2) test_ordine_assente_fail_safe — bindato su MERCE_PRESENTE ma nessun ordine →
   incoerenza esito/artefatti → E_VENDITA_SMISTAMENTO_NON_ESEGUITO (fail rumoroso)
3) test_preventivo_non_collegato — nessun ROOT → E_VENDITA_PREVENTIVO_NON_COLLEGATO
"""

from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.handlers.post_smistamento_handler import PostSmistamentoHandler

_MOD = "apps.vendite.handlers.post_smistamento_handler"
_PREV_REPO = f"{_MOD}.PreventiviRepository"
_ORD_REPO = f"{_MOD}.OrdiniRepository"
_PRAT_REPO = "apps.pratiche.db.pratiche_repository.PraticheRepository"


class PostSmistamentoHandlerTests(SimpleTestCase):

    @patch(_PRAT_REPO, autospec=True)
    @patch(_ORD_REPO, autospec=True)
    @patch(_PREV_REPO, autospec=True)
    def test_ordine_presente_aggancia(self, MockPrev, MockOrd, MockPrat):
        MockPrev.return_value.get_preventivo_id_by_pratica_root.return_value = 375
        MockOrd.return_value.get_ordine_by_documento_origine.return_value = {"id": 143, "numero": "ORD1"}

        out = PostSmistamentoHandler().execute(
            flusso_id=500, pratica_id=290, meta={}, handler_params={}, user="op1",
        )

        self.assertEqual(out, {"ordine_id": 143})
        # Merce-only: aggancia l'ordine, NON crea flussi a valle (9013/9014 via roadmap).
        MockPrat.return_value.upsert_pratica_sorgente.assert_called_once_with(
            pratica_id=290, sorgente_codice="ORDINE_VENDITA",
            sorgente_chiave="143", ruolo_link="COLLEGATO",
        )

    # Scopo: fail-safe — l'handler scatta solo su MERCE_PRESENTE (esito calcolato da
    # exists_ordine_da_preventivo), quindi un ordine DEVE esistere. Ordine assente =
    # incoerenza → errore rumoroso, non silenzio.
    @patch(_PRAT_REPO, autospec=True)
    @patch(_ORD_REPO, autospec=True)
    @patch(_PREV_REPO, autospec=True)
    def test_ordine_assente_fail_safe(self, MockPrev, MockOrd, MockPrat):
        MockPrev.return_value.get_preventivo_id_by_pratica_root.return_value = 383
        MockOrd.return_value.get_ordine_by_documento_origine.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            PostSmistamentoHandler().execute(
                flusso_id=500, pratica_id=290, meta={}, handler_params={},
            )
        self.assertEqual(ctx.exception.code, "E_VENDITA_SMISTAMENTO_NON_ESEGUITO")
        MockPrat.return_value.upsert_pratica_sorgente.assert_not_called()

    @patch(_PRAT_REPO, autospec=True)
    @patch(_ORD_REPO, autospec=True)
    @patch(_PREV_REPO, autospec=True)
    def test_preventivo_non_collegato(self, MockPrev, MockOrd, MockPrat):
        MockPrev.return_value.get_preventivo_id_by_pratica_root.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            PostSmistamentoHandler().execute(
                flusso_id=500, pratica_id=290, meta={}, handler_params={},
            )
        self.assertEqual(ctx.exception.code, "E_VENDITA_PREVENTIVO_NON_COLLEGATO")
