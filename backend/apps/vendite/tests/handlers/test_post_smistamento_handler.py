# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per l'handler flusso `vendita.post_smistamento` —
#        completamento SMISTAMENTO. DB mockato (SimpleTestCase + patch).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_ordine_presente_crea_conferma — ordine merce → aggancio COLLEGATO + crea SOLO
   CONFERMA_ORDINE (9013); INVIO_COMMESSA non percorribile (prereq 9013) → non creato
2) test_tutto_servizi_nessun_ordine — nessun ordine → niente aggancio/flussi
3) test_crea_solo_percorribile_non_istanziato — conferma istanziata (skip) + invio
   percorribile/non istanziato → crea solo INVIO_COMMESSA
4) test_preventivo_non_collegato — nessun ROOT → E_VENDITA_PREVENTIVO_NON_COLLEGATO
"""

from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.handlers.post_smistamento_handler import PostSmistamentoHandler

_MOD = "apps.vendite.handlers.post_smistamento_handler"
_PREV_REPO = f"{_MOD}.PreventiviRepository"
_ORD_REPO = f"{_MOD}.OrdiniRepository"
_PRAT_REPO = "apps.pratiche.db.pratiche_repository.PraticheRepository"
_CREA_FLUSSO = "apps.pratiche.services.pratiche_service.crea_flusso"


def _percorso(
    conferma_flusso_id=None, invio_flusso_id=None,
    conferma_percorribile=True, invio_percorribile=False,
):
    # `percorribile` = prerequisiti soddisfatti ora. Alla chiusura di SMISTAMENTO
    # solo CONFERMA_ORDINE e' percorribile (prereq SMISTAMENTO POSITIVO);
    # INVIO_COMMESSA lo diventa dopo la chiusura di CONFERMA_ORDINE.
    return [
        {"template_flusso_codice": "SMISTAMENTO", "template_flusso_id": 9012,
         "flusso_id": 1, "percorribile": False},
        {"template_flusso_codice": "CONFERMA_ORDINE", "template_flusso_id": 9013,
         "flusso_id": conferma_flusso_id, "percorribile": conferma_percorribile},
        {"template_flusso_codice": "INVIO_COMMESSA", "template_flusso_id": 9014,
         "flusso_id": invio_flusso_id, "percorribile": invio_percorribile},
    ]


class PostSmistamentoHandlerTests(SimpleTestCase):

    @patch(_CREA_FLUSSO)
    @patch(_PRAT_REPO)
    @patch(_ORD_REPO)
    @patch(_PREV_REPO)
    def test_ordine_presente_crea_conferma(self, MockPrev, MockOrd, MockPrat, mock_crea):
        MockPrev.return_value.get_preventivo_id_by_pratica_root.return_value = 375
        MockOrd.return_value.get_ordine_by_documento_origine.return_value = {"id": 143, "numero": "ORD1"}
        # smistamento appena chiuso: CONFERMA_ORDINE percorribile, INVIO_COMMESSA no.
        MockPrat.return_value.get_percorso_pratica.return_value = _percorso()
        mock_crea.return_value = 9101

        out = PostSmistamentoHandler().execute(
            flusso_id=500, pratica_id=290, meta={}, handler_params={}, user="op1",
        )

        self.assertEqual(out["ordine_id"], 143)
        # crea SOLO CONFERMA_ORDINE (9014 non percorribile: prereq 9013)
        self.assertEqual(out["flussi_creati"], [9101])
        MockPrat.return_value.upsert_pratica_sorgente.assert_called_once_with(
            pratica_id=290, sorgente_codice="ORDINE_VENDITA",
            sorgente_uid="143", ruolo_link="COLLEGATO",
        )
        mock_crea.assert_called_once()
        self.assertEqual(mock_crea.call_args.kwargs["template_flusso_id"], 9013)

    @patch(_CREA_FLUSSO)
    @patch(_PRAT_REPO)
    @patch(_ORD_REPO)
    @patch(_PREV_REPO)
    def test_tutto_servizi_nessun_ordine(self, MockPrev, MockOrd, MockPrat, mock_crea):
        MockPrev.return_value.get_preventivo_id_by_pratica_root.return_value = 375
        MockOrd.return_value.get_ordine_by_documento_origine.return_value = None
        # tutto-servizi: nessun residuo merce → ok, niente flussi ordine.
        MockPrev.return_value.preventivo_ha_residuo_ordine.return_value = False

        out = PostSmistamentoHandler().execute(
            flusso_id=500, pratica_id=290, meta={}, handler_params={},
        )

        self.assertEqual(out, {"ordine_id": None, "flussi_creati": []})
        MockPrat.return_value.upsert_pratica_sorgente.assert_not_called()
        mock_crea.assert_not_called()

    # Scopo: SMISTAMENTO completato senza aver smistato la merce (residuo merce,
    # nessun ordine) → blocca con E_VENDITA_SMISTAMENTO_NON_ESEGUITO.
    @patch(_CREA_FLUSSO)
    @patch(_PRAT_REPO)
    @patch(_ORD_REPO)
    @patch(_PREV_REPO)
    def test_merce_non_smistata_blocca(self, MockPrev, MockOrd, MockPrat, mock_crea):
        MockPrev.return_value.get_preventivo_id_by_pratica_root.return_value = 383
        MockOrd.return_value.get_ordine_by_documento_origine.return_value = None
        MockPrev.return_value.preventivo_ha_residuo_ordine.return_value = True

        with self.assertRaises(ServiceError) as ctx:
            PostSmistamentoHandler().execute(
                flusso_id=500, pratica_id=290, meta={}, handler_params={},
            )
        self.assertEqual(ctx.exception.code, "E_VENDITA_SMISTAMENTO_NON_ESEGUITO")
        mock_crea.assert_not_called()

    @patch(_CREA_FLUSSO)
    @patch(_PRAT_REPO)
    @patch(_ORD_REPO)
    @patch(_PREV_REPO)
    def test_crea_solo_percorribile_non_istanziato(self, MockPrev, MockOrd, MockPrat, mock_crea):
        MockPrev.return_value.get_preventivo_id_by_pratica_root.return_value = 375
        MockOrd.return_value.get_ordine_by_documento_origine.return_value = {"id": 143}
        # CONFERMA gia' istanziato (skip), INVIO non istanziato E percorribile
        # (CONFERMA chiuso) → crea solo INVIO_COMMESSA.
        MockPrat.return_value.get_percorso_pratica.return_value = _percorso(
            conferma_flusso_id=9101, invio_flusso_id=None, invio_percorribile=True,
        )
        mock_crea.return_value = 9102

        out = PostSmistamentoHandler().execute(
            flusso_id=500, pratica_id=290, meta={}, handler_params={},
        )

        self.assertEqual(out["flussi_creati"], [9102])
        mock_crea.assert_called_once()
        self.assertEqual(mock_crea.call_args.kwargs["template_flusso_id"], 9014)

    @patch(_CREA_FLUSSO)
    @patch(_PRAT_REPO)
    @patch(_ORD_REPO)
    @patch(_PREV_REPO)
    def test_preventivo_non_collegato(self, MockPrev, MockOrd, MockPrat, mock_crea):
        MockPrev.return_value.get_preventivo_id_by_pratica_root.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            PostSmistamentoHandler().execute(
                flusso_id=500, pratica_id=290, meta={}, handler_params={},
            )
        self.assertEqual(ctx.exception.code, "E_VENDITA_PREVENTIVO_NON_COLLEGATO")
        mock_crea.assert_not_called()
