# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari del cambio di cliente del contratto in bozza e della
#        scheda di fornitura inline della PATCH (brief-db-indirizzi-documento-
#        seguono-il-cliente §8.3, R-BE-7; B-1 e B-4 di Tid).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) cambio_ba_risolve_la_coppia_col_bb — BA e istanza arrivano al repository
   risolti dal BB, sulla utility della testata
2) sola_istanza_risolve_il_ba — il BB riceve l'istanza senza il BA
3) utility_ed_emittente_rifiutati — B-4: non si cambiano in modifica
4) scheda_inline_aggiorna — senza cambio di coppia la scheda del form si scrive
5) scheda_inline_crea_se_manca — contratto senza scheda: la si crea con la
   coppia della testata
6) cambio_cliente_non_applica_la_scheda — R-BE-6/7: la scheda la rifa' il DB
7) stesso_cliente_in_testo_non_e_un_cambio — un id "10" dal JSON vale 10
8) scheda_con_identificativi_rifiutata — la coppia della scheda e' della testata
9) solo_scheda_basta — una PATCH col solo `utility` non e' vuota
10) ba_fuori_coppia_errore_sul_ba — il BB vero: messaggio del contratto, campo BA
11) scheda_vuota_da_sola_e_400 — `{"utility": {}}` non e' una modifica: 400,
    niente scritto (fino al 2026-10-14 «salvato» a vuoto)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.contratti_service import ContrattiService

_SVC = "apps.vendite.services.contratti_service"


def _testata() -> dict[str, Any]:
    return {
        "id": 1,
        "numero": "CNT0000001",
        "billing_account_id": 10,
        "istanza_utility_id": 20,
        "utility_id": 3,
        "stato_codice_interno": "DRAFT",
        "listino_id": None,
        "tipo_variazione_globale": None,
        "valore_variazione_globale": None,
    }


class ContrattoCambioClienteTests(SimpleTestCase):
    def setUp(self) -> None:
        p_repo = patch(f"{_SVC}.ContrattiRepository", autospec=True)
        self.repo = p_repo.start().return_value
        self.addCleanup(p_repo.stop)
        self.repo.get_contratto.return_value = _testata()
        self.repo.update_contratto.return_value = True
        self.repo.get_utility.return_value = {"id": 99, "istanza_utility_id": 20, "utility_id": 3}
        self.repo.list_righe.return_value = []
        self.repo.get_capabilities.return_value = {}
        # Il contatore note del dettaglio legge il DB: SimpleTestCase lo vieta.
        p_cont = patch(f"{_SVC}.contatori_documento", return_value={"note": 0})
        p_cont.start()
        self.addCleanup(p_cont.stop)
        # Niente transazione vera: SimpleTestCase vieta il DB.
        p_atomic = patch(f"{_SVC}.transaction.atomic", MagicMock())
        p_atomic.start()
        self.addCleanup(p_atomic.stop)
        p_bb = patch(f"{_SVC}.risolvi_cliente_coppia", return_value=(11, 21))
        self.bb = p_bb.start()
        self.addCleanup(p_bb.stop)

    def _dati_testata(self) -> dict[str, Any]:
        return self.repo.update_contratto.call_args.args[1]

    def test_1_cambio_ba_risolve_la_coppia_col_bb(self) -> None:
        ContrattiService().update_contratto(1, {"billing_account_id": 11, "istanza_utility_id": 21})
        kwargs = self.bb.call_args.kwargs
        self.assertEqual(kwargs["billing_account_id"], 11)
        self.assertEqual(kwargs["istanza_utility_id"], 21)
        self.assertEqual(kwargs["utility_id"], 3)
        self.assertEqual(kwargs["code"], "E_VENDITE_VALIDATION")
        self.assertEqual(self._dati_testata()["billing_account_id"], 11)
        self.assertEqual(self._dati_testata()["istanza_utility_id"], 21)

    def test_2_sola_istanza_risolve_il_ba(self) -> None:
        ContrattiService().update_contratto(1, {"istanza_utility_id": 21})
        self.assertIsNone(self.bb.call_args.kwargs["billing_account_id"])
        self.assertEqual(self._dati_testata()["billing_account_id"], 11)

    def test_3_utility_ed_emittente_rifiutati(self) -> None:
        for chiave in ("utility_id", "emittente_fiscale_id"):
            with self.subTest(chiave=chiave), self.assertRaises(ServiceError):
                ContrattiService().update_contratto(1, {chiave: 4})
        self.repo.update_contratto.assert_not_called()

    def test_4_scheda_inline_aggiorna(self) -> None:
        ContrattiService().update_contratto(
            1, {"ambito": "COMMODITY", "utility": {"classe_utenza_id": 5, "param_1_num": "3"}},
        )
        self.repo.update_utility.assert_called_once()
        rid, data = self.repo.update_utility.call_args.args
        self.assertEqual(rid, 99)
        self.assertEqual(data["classe_utenza_id"], 5)
        self.assertNotIn("istanza_utility_id", data)

    def test_5_scheda_inline_crea_se_manca(self) -> None:
        self.repo.get_utility.return_value = None
        ContrattiService().update_contratto(1, {"utility": {"tipo_utenza_id": 2}})
        self.repo.create_utility.assert_called_once()
        cid, data = self.repo.create_utility.call_args.args
        self.assertEqual(cid, 1)
        self.assertEqual((data["istanza_utility_id"], data["utility_id"]), (20, 3))
        self.assertEqual(data["tipo_utenza_id"], 2)

    def test_6_cambio_cliente_non_applica_la_scheda(self) -> None:
        ContrattiService().update_contratto(
            1, {"billing_account_id": 11, "istanza_utility_id": 21, "utility": {"classe_utenza_id": 5}},
        )
        self.repo.update_contratto.assert_called_once()
        self.repo.update_utility.assert_not_called()
        self.repo.create_utility.assert_not_called()

    def test_7_stesso_cliente_in_testo_non_e_un_cambio(self) -> None:
        self.bb.return_value = (10, 20)
        ContrattiService().update_contratto(
            1, {"billing_account_id": "10", "istanza_utility_id": "20", "utility": {"classe_utenza_id": 5}},
        )
        self.repo.update_utility.assert_called_once()

    def test_8_scheda_con_identificativi_rifiutata(self) -> None:
        with self.assertRaises(ServiceError):
            ContrattiService().update_contratto(1, {"utility": {"istanza_utility_id": 21}})
        self.repo.update_utility.assert_not_called()

    def test_9_solo_scheda_basta(self) -> None:
        ContrattiService().update_contratto(1, {"utility": {"classe_utenza_id": 5}})
        self.repo.update_contratto.assert_not_called()
        self.repo.update_utility.assert_called_once()

    def test_11_scheda_vuota_da_sola_e_400(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().update_contratto(1, {"utility": {}})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.repo.update_contratto.assert_not_called()
        self.repo.update_utility.assert_not_called()
        self.repo.create_utility.assert_not_called()


class ContrattoBaFuoriCoppiaTests(SimpleTestCase):
    # Il BB vero, col repository del BA finto: il BA dichiarato non e' quello
    # della coppia (istanza del BA, utility del contratto).
    @patch("apps.vendite.services._cliente_coppia_documento.BillingAccountRepository", autospec=True)
    @patch("apps.anagrafiche.services.billing_account_service.BillingAccountRepository", autospec=True)
    @patch(f"{_SVC}.ContrattiRepository", autospec=True)
    def test_10_ba_fuori_coppia_errore_sul_ba(self, repo_cls, ba_bb_cls, ba_cls) -> None:
        repo_cls.return_value.get_contratto.return_value = _testata()
        ba_bb_cls.return_value.get_istanza_utility_id.return_value = 21
        ba_cls.return_value.get_id_by_coppia.return_value = 12
        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().update_contratto(1, {"billing_account_id": 11})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertEqual(ctx.exception.context.get("field"), "billing_account_id")
        self.assertIn("contratto", ctx.exception.message)
        repo_cls.return_value.update_contratto.assert_not_called()
