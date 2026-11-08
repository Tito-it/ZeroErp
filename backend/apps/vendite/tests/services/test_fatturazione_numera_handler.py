# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit dell'handler del job FATTURAZIONE_NUMERA (C-4, numerazione di
#        perimetro). Mock di get_stato_doc_fiscale_id + discovery lotti +
#        pipeline_service.numera_lotto: verifica risoluzione EMESSA + discovery
#        con competenza normalizzata, numera per-lotto con auth_user_id dallo
#        scope, best-effort per-lotto, no-op su zero lotti, fail-loud su EMESSA
#        non configurato, guard payload, e registrazione.
#
# Indice test:
#   0. happy_path_numera_tutti_i_lotti
#   1. best_effort_un_lotto_fallito_non_blocca
#   2. nessun_lotto_numerabile_noop
#   3. emessa_non_configurato_raises_fail_loud
#   4. competenza_mancante_raises_payload
#   5. competenza_invalida_raises_payload
#   6. handler_registrato_dopo_boot
#   7. data_documento_dichiarata_arriva_al_core
#   8. data_documento_non_e_normalizzata_al_primo_del_mese
#   9. selezione_lotti_restringe_il_perimetro   ⭐ il quinto anello
#  10. selezione_lotti_non_passa_anche_la_competenza
#  11. selezione_vuota_rifiutata
#  12. selezione_malformata_rifiutata
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.fatturazione_numera_handler import (
    HANDLER_CODE,
    fatturazione_numera_handler,
)

_PIPE_REPO = "apps.vendite.db.pipeline_repository.VenditePipelineRepository"
_VEND_REPO = "apps.vendite.db.vendite_repository.VenditeRepository"
_NUMERA = "apps.vendite.services.pipeline_service.numera_lotto"


class FatturazioneNumeraHandlerTests(SimpleTestCase):

    # 0. Scopre i lotti EMESSA del mese (competenza normalizzata al 1° + id
    #    EMESSA risolto) e numera ciascuno con l'auth_user_id dello scope.
    @patch(_NUMERA)
    @patch(_VEND_REPO, autospec=True)
    @patch(_PIPE_REPO, autospec=True)
    def test_happy_path_numera_tutti_i_lotti(
        self, pipe_repo, vend_repo, mock_numera,
    ) -> None:
        pipe_repo.return_value.get_stato_doc_fiscale_id.side_effect = (
            lambda codice: {"EMESSA": 7, "DEFINITIVA": 8}[codice]
        )
        vend_repo.return_value.list_lotti_numerabili.return_value = [
            {"id": 1, "codice": "LOT1"}, {"id": 2, "codice": "LOT2"},
        ]
        mock_numera.return_value = {
            "stato_doc_fiscale_id": 8, "motivo_stop": "COMPLETATO",
        }

        result = fatturazione_numera_handler(
            {"competenza_mese": "2026-06-15"},
            scope={"auth_user_id": 9, "username": "op9", "identita_id": 5,
                   "emittente_ids": [3]},
        )

        vend_repo.return_value.list_lotti_numerabili.assert_called_once_with(
            competenza_mese=date(2026, 6, 1), stato_doc_fiscale_id=7,
        )
        self.assertEqual(mock_numera.call_count, 2)
        # auth_user_id dello scope passato al core (defense-in-depth oltre RLS)
        # ⚠️ `data_documento=None` e' ESPLICITO nell'asserzione: None qui vuol
        #    dire «nessuna dichiarazione», e il core deve ricevere quel None —
        #    non un default inventato dall'handler.
        mock_numera.assert_any_call(lotto_id=1, auth_user_id=9, data_documento=None)
        mock_numera.assert_any_call(lotto_id=2, auth_user_id=9, data_documento=None)
        self.assertIsNone(result["data_documento"])
        self.assertEqual(result["competenza"], "2026-06-01")
        self.assertEqual(result["lotti"], 2)
        self.assertEqual(result["numerati"], 2)
        self.assertEqual(result["saltati"], 0)
        self.assertEqual(result["falliti"], 0)
        self.assertEqual(result["falliti_dett"], [])

    # 7. La data documento dichiarata arriva al core, uguale per TUTTI i lotti
    #    dell'atto (decisione 5 del brief numerazione: una data per l'atto, non
    #    una per lotto), e torna nell'esito.
    @patch(_NUMERA)
    @patch(_VEND_REPO, autospec=True)
    @patch(_PIPE_REPO, autospec=True)
    def test_data_documento_dichiarata_arriva_al_core(
        self, pipe_repo, vend_repo, mock_numera,
    ) -> None:
        pipe_repo.return_value.get_stato_doc_fiscale_id.side_effect = (
            lambda codice: {"EMESSA": 7, "DEFINITIVA": 8}[codice]
        )
        vend_repo.return_value.list_lotti_numerabili.return_value = [
            {"id": 1, "codice": "LTF-1"}, {"id": 2, "codice": "LTF-2"},
        ]
        mock_numera.return_value = {
            "stato_doc_fiscale_id": 8, "motivo_stop": "COMPLETATO",
        }

        result = fatturazione_numera_handler(
            {"competenza_mese": "2026-06-15", "data_documento": "2026-08-25"},
            scope={"auth_user_id": 9},
        )

        mock_numera.assert_any_call(
            lotto_id=1, auth_user_id=9, data_documento=date(2026, 8, 25),
        )
        mock_numera.assert_any_call(
            lotto_id=2, auth_user_id=9, data_documento=date(2026, 8, 25),
        )
        self.assertEqual(result["data_documento"], "2026-08-25")

    # 8. ⛔ IL TEST CHE PRESIDIA IL DIFETTO SILENZIOSO: la data documento NON si
    #    normalizza al 1° del mese. `parse_competenza_mese` lo fa — perche' una
    #    competenza E' un mese — e riusarla qui trasformerebbe il 25/08 scelto
    #    dall'operatore in un 01/08 senza sollevare niente, scrivendo sui
    #    documenti una data che nessuno ha deciso. Nel cantiere che nasce
    #    proprio per togliere le date che nessuno ha deciso.
    @patch(_NUMERA)
    @patch(_VEND_REPO, autospec=True)
    @patch(_PIPE_REPO, autospec=True)
    def test_data_documento_non_e_normalizzata_al_primo_del_mese(
        self, pipe_repo, vend_repo, mock_numera,
    ) -> None:
        pipe_repo.return_value.get_stato_doc_fiscale_id.side_effect = (
            lambda codice: {"EMESSA": 7, "DEFINITIVA": 8}[codice]
        )
        vend_repo.return_value.list_lotti_numerabili.return_value = [
            {"id": 1, "codice": "LTF-1"},
        ]
        mock_numera.return_value = {
            "stato_doc_fiscale_id": 8, "motivo_stop": "COMPLETATO",
        }

        fatturazione_numera_handler(
            {"competenza_mese": "2026-06-15", "data_documento": "2026-08-31"},
            scope={"auth_user_id": 9},
        )

        passata = mock_numera.call_args.kwargs["data_documento"]
        self.assertEqual(passata, date(2026, 8, 31))
        self.assertNotEqual(passata.day, 1)

    # 1. Best-effort: un lotto in errore NON blocca gli altri; falliti_dett
    #    riporta lotto+codice+code.
    @patch(_NUMERA)
    @patch(_VEND_REPO, autospec=True)
    @patch(_PIPE_REPO, autospec=True)
    def test_best_effort_un_lotto_fallito_non_blocca(
        self, pipe_repo, vend_repo, mock_numera,
    ) -> None:
        pipe_repo.return_value.get_stato_doc_fiscale_id.side_effect = (
            lambda codice: {"EMESSA": 7, "DEFINITIVA": 8}[codice]
        )
        vend_repo.return_value.list_lotti_numerabili.return_value = [
            {"id": 1, "codice": "LOT1"}, {"id": 2, "codice": "LOT2"},
        ]
        mock_numera.side_effect = [
            ServiceError(code="E_LOTTO_NON_NUMERABILE", message="x"),
            {"stato_doc_fiscale_id": 8, "motivo_stop": "COMPLETATO"},
        ]

        result = fatturazione_numera_handler(
            {"competenza_mese": "2026-06-01"}, scope=None,
        )

        self.assertEqual(result["numerati"], 1)
        self.assertEqual(result["falliti"], 1)
        self.assertEqual(result["falliti_dett"][0]["lotto_id"], 1)
        self.assertEqual(result["falliti_dett"][0]["codice"], "LOT1")
        self.assertEqual(result["falliti_dett"][0]["code"], "E_LOTTO_NON_NUMERABILE")
        # il 2° lotto è stato comunque lavorato
        self.assertEqual(mock_numera.call_count, 2)

    # 1-bis. Lotto che NON transita a DEFINITIVA (es. legacy pre-G1: pipeline
    #        si ferma senza step, nessuna eccezione) → conteggiato SALTATO con
    #        motivo_stop, MAI «numerato» (smoke C-9: fatture senza numero
    #        nascoste da un contatore ottimista).
    @patch(_NUMERA)
    @patch(_VEND_REPO, autospec=True)
    @patch(_PIPE_REPO, autospec=True)
    def test_lotto_non_transitato_conta_saltato(
        self, pipe_repo, vend_repo, mock_numera,
    ) -> None:
        pipe_repo.return_value.get_stato_doc_fiscale_id.side_effect = (
            lambda codice: {"EMESSA": 7, "DEFINITIVA": 8}[codice]
        )
        vend_repo.return_value.list_lotti_numerabili.return_value = [
            {"id": 106, "codice": "LEGACY"},
        ]
        mock_numera.return_value = {
            "stato_doc_fiscale_id": 7,  # resta EMESSA
            "motivo_stop": "NESSUNO_STEP_ESEGUIBILE",
        }

        result = fatturazione_numera_handler(
            {"competenza_mese": "2026-06-01"}, scope=None,
        )

        self.assertEqual(result["numerati"], 0)
        self.assertEqual(result["saltati"], 1)
        self.assertEqual(result["falliti"], 0)
        self.assertEqual(result["saltati_dett"][0]["lotto_id"], 106)
        self.assertEqual(
            result["saltati_dett"][0]["motivo_stop"], "NESSUNO_STEP_ESEGUIBILE",
        )

    # 2. Nessun lotto EMESSA nel mese → job no-op (lotti=0), numera mai chiamato.
    @patch(_NUMERA)
    @patch(_VEND_REPO, autospec=True)
    @patch(_PIPE_REPO, autospec=True)
    def test_nessun_lotto_numerabile_noop(
        self, pipe_repo, vend_repo, mock_numera,
    ) -> None:
        pipe_repo.return_value.get_stato_doc_fiscale_id.return_value = 7
        vend_repo.return_value.list_lotti_numerabili.return_value = []

        result = fatturazione_numera_handler(
            {"competenza_mese": "2026-06-01"}, scope=None,
        )

        self.assertEqual(result["lotti"], 0)
        self.assertEqual(result["numerati"], 0)
        mock_numera.assert_not_called()

    # 3. EMESSA non configurato → fail-loud (niente discovery, niente 0-lotti
    #    silenzioso che maschererebbe una config rotta).
    @patch(_NUMERA)
    @patch(_VEND_REPO, autospec=True)
    @patch(_PIPE_REPO, autospec=True)
    def test_emessa_non_configurato_raises_fail_loud(
        self, pipe_repo, vend_repo, mock_numera,
    ) -> None:
        pipe_repo.return_value.get_stato_doc_fiscale_id.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            fatturazione_numera_handler(
                {"competenza_mese": "2026-06-01"}, scope=None,
            )

        self.assertEqual(ctx.exception.code, "E_PIPELINE_VALIDATION")
        vend_repo.return_value.list_lotti_numerabili.assert_not_called()
        mock_numera.assert_not_called()

    # 4. Competenza mancante → codice payload, nessuna discovery.
    def test_competenza_mancante_raises_payload(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            fatturazione_numera_handler({}, scope=None)
        self.assertEqual(ctx.exception.code, "E_FATTURAZIONE_NUMERA_PAYLOAD")

    # 5. Competenza malformata → stesso codice payload.
    def test_competenza_invalida_raises_payload(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            fatturazione_numera_handler(
                {"competenza_mese": "non-una-data"}, scope=None,
            )
        self.assertEqual(ctx.exception.code, "E_FATTURAZIONE_NUMERA_PAYLOAD")

    # 6. L'handler è registrato nel registry dopo il boot (VenditeConfig.ready()).
    def test_handler_registrato_dopo_boot(self) -> None:
        from apps.core.services.coda_lavori.handler_registry import (
            get_handler,
            registered_handlers,
        )
        self.assertIn(HANDLER_CODE, registered_handlers())
        self.assertIs(get_handler(HANDLER_CODE), fatturazione_numera_handler)

    # ═══ IL PERIMETRO SELEZIONATO — il quinto anello ════════════════════════
    #
    # ⛔ Gli id partono dalla lista a video, attraversano endpoint, payload JSON
    #    della coda e worker, e arrivano qui. Se uno solo di questi anelli li
    #    perde, il giro numera l'INTERO MESE invece dei lotti spuntati — e non
    #    fallisce, RIESCE. E' un atto fiscale: i numeri consumati non tornano.
    #    Questi test presidiano l'ultimo anello, quello dove il difetto
    #    diventerebbe irreversibile.

    # 9. La selezione arriva alla discovery, e come `lotti_ids`.
    @patch("apps.vendite.services.pipeline_service.numera_lotto")
    @patch("apps.vendite.db.vendite_repository.VenditeRepository", autospec=True)
    @patch("apps.vendite.db.pipeline_repository.VenditePipelineRepository", autospec=True)
    def test_selezione_lotti_restringe_il_perimetro(
        self, pipe_repo, vend_repo, mock_numera,
    ):
        pipe_repo.return_value.get_stato_doc_fiscale_id.side_effect = (
            lambda codice: {"EMESSA": 8, "DEFINITIVA": 9}[codice]
        )
        vend_repo.return_value.list_lotti_numerabili.return_value = []
        fatturazione_numera_handler(
            {"competenza_mese": "2026-06-01", "lotti": [12, 15]}, scope=None,
        )
        kwargs = vend_repo.return_value.list_lotti_numerabili.call_args.kwargs
        self.assertEqual(kwargs["lotti_ids"], [12, 15])

    # 10. ⛔ E la competenza NON viene passata insieme: sono due perimetri
    #     alternativi, e passarli entrambi e' un errore che il costruttore
    #     rifiuta. Se questo test si spegne, il perimetro torna a essere il mese.
    @patch("apps.vendite.services.pipeline_service.numera_lotto")
    @patch("apps.vendite.db.vendite_repository.VenditeRepository", autospec=True)
    @patch("apps.vendite.db.pipeline_repository.VenditePipelineRepository", autospec=True)
    def test_selezione_lotti_non_passa_anche_la_competenza(
        self, pipe_repo, vend_repo, mock_numera,
    ):
        pipe_repo.return_value.get_stato_doc_fiscale_id.side_effect = (
            lambda codice: {"EMESSA": 8, "DEFINITIVA": 9}[codice]
        )
        vend_repo.return_value.list_lotti_numerabili.return_value = []
        fatturazione_numera_handler(
            {"competenza_mese": "2026-06-01", "lotti": [12]}, scope=None,
        )
        kwargs = vend_repo.return_value.list_lotti_numerabili.call_args.kwargs
        self.assertNotIn("competenza_mese", kwargs)
        # ⚠️ Lo stato resta sempre: un lotto scelto a mano non e' per questo
        #    numerabile. La selezione decide il perimetro, non le regole.
        self.assertEqual(kwargs["stato_doc_fiscale_id"], 8)

    # 11. ⛔ Selezione VUOTA = rifiuto, non «tutti». E' una richiesta ambigua, e
    #     su un atto fiscale non si indovina.
    def test_selezione_vuota_rifiutata(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            fatturazione_numera_handler(
                {"competenza_mese": "2026-06-01", "lotti": []}, scope=None,
            )
        self.assertEqual(ctx.exception.code, "E_FATTURAZIONE_NUMERA_PAYLOAD")

    # 12. Selezione malformata → stesso codice payload, non un job che numera
    #     il mese perche' non ha capito il campo.
    def test_selezione_malformata_rifiutata(self) -> None:
        for sbagliata in (["dodici"], [0], [-3], [True], "12", {"a": 1}):
            with self.assertRaises(ServiceError, msg=repr(sbagliata)) as ctx:
                fatturazione_numera_handler(
                    {"competenza_mese": "2026-06-01", "lotti": sbagliata},
                    scope=None,
                )
            self.assertEqual(ctx.exception.code, "E_FATTURAZIONE_NUMERA_PAYLOAD")
