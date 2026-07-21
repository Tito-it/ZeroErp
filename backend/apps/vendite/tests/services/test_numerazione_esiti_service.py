# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit dei service cockpit C-4 (numera_lotto) e C-5
#        (esiti_fatturazione). Mock-only (nessun DB): guard fiscali della
#        numerazione + aggregazione esiti/coda.
#
# Indice test (0..N):
#   0. numera_lotto_ok_esegue_step_definitiva
#   1. numera_lotto_fuori_scope_o_inesistente_404
#   2. numera_lotto_non_emessa_raises
#   3. ristampa_lotto_ok_accoda
#   4. ristampa_lotto_fuori_scope_o_inesistente_404
#   5. ristampa_lotto_non_definitiva_raises
#   6. esiti_filtra_jobname_fatturazione_e_coda_scoped
# ------------------------------------------------------------

from __future__ import annotations

from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.pipeline_service import (
    esiti_fatturazione,
    numera_lotto,
    ristampa_lotto,
)

_SVC = "apps.vendite.services.pipeline_service"
_VEN_REPO = "apps.vendite.db.vendite_repository.VenditeRepository"


class NumeraLottoTests(SimpleTestCase):

    # 0. Lotto EMESSA in scope → esegue lo step fino a DEFINITIVA.
    def test_numera_lotto_ok_esegue_step_definitiva(self) -> None:
        with patch(_VEN_REPO) as VenRepo, \
             patch(f"{_SVC}.VenditePipelineRepository") as PipeRepo, \
             patch(f"{_SVC}.run_lotto_pipeline_until_done") as mock_run:
            VenRepo.return_value.get_lotto.return_value = {
                "id": 5, "stato_doc_fiscale_id": 2,
            }
            PipeRepo.return_value.get_stato_doc_fiscale_id.return_value = 2  # EMESSA
            mock_run.return_value = {
                "lotto_id": 5, "stato_lotto": "COMPLETATO",
                "stato_doc_fiscale_id": 8, "step_eseguiti": 1,
                "motivo_stop": "FERMATO_A_STATO",
            }

            esito = numera_lotto(lotto_id=5, auth_user_id=9)

        self.assertEqual(esito["motivo_stop"], "FERMATO_A_STATO")
        mock_run.assert_called_once_with(lotto_id=5, fino_a_stato="DEFINITIVA")
        VenRepo.return_value.get_lotto.assert_called_once_with(
            lotto_id=5, auth_user_id=9,
        )

    # 1. Lotto fuori scope o inesistente (get_lotto None) → 404 unificato.
    def test_numera_lotto_fuori_scope_o_inesistente_404(self) -> None:
        with patch(_VEN_REPO) as VenRepo, \
             patch(f"{_SVC}.VenditePipelineRepository"), \
             patch(f"{_SVC}.run_lotto_pipeline_until_done") as mock_run:
            VenRepo.return_value.get_lotto.return_value = None
            with self.assertRaises(ServiceError) as ctx:
                numera_lotto(lotto_id=999, auth_user_id=9)

        self.assertEqual(ctx.exception.code, "E_LOTTO_NON_TROVATO")
        mock_run.assert_not_called()

    # 2. Lotto non in EMESSA (es. DRAFT) → gate fiscale: non numerabile.
    def test_numera_lotto_non_emessa_raises(self) -> None:
        with patch(_VEN_REPO) as VenRepo, \
             patch(f"{_SVC}.VenditePipelineRepository") as PipeRepo, \
             patch(f"{_SVC}.run_lotto_pipeline_until_done") as mock_run:
            VenRepo.return_value.get_lotto.return_value = {
                "id": 5, "stato_doc_fiscale_id": 1,  # DRAFT
            }
            PipeRepo.return_value.get_stato_doc_fiscale_id.return_value = 2  # EMESSA
            with self.assertRaises(ServiceError) as ctx:
                numera_lotto(lotto_id=5, auth_user_id=9)

        self.assertEqual(ctx.exception.code, "E_LOTTO_NON_NUMERABILE")
        mock_run.assert_not_called()


class RistampaLottoTests(SimpleTestCase):

    # 3. Lotto DEFINITIVA in scope → accoda le stampe e ritorna il conteggio.
    def test_ristampa_lotto_ok_accoda(self) -> None:
        with patch(_VEN_REPO) as VenRepo, \
             patch(f"{_SVC}.VenditePipelineRepository") as PipeRepo:
            VenRepo.return_value.get_lotto.return_value = {
                "id": 5, "stato_doc_fiscale_id": 8,  # DEFINITIVA
            }
            PipeRepo.return_value.get_stato_doc_fiscale_id.return_value = 8
            PipeRepo.return_value.accoda_stampe_lotto.return_value = 4

            esito = ristampa_lotto(lotto_id=5, auth_user_id=9)

        self.assertEqual(esito, {"lotto_id": 5, "accodate": 4})
        PipeRepo.return_value.accoda_stampe_lotto.assert_called_once_with(5)
        VenRepo.return_value.get_lotto.assert_called_once_with(
            lotto_id=5, auth_user_id=9,
        )

    # 4. Lotto fuori scope o inesistente (get_lotto None) → 404, niente accoda.
    def test_ristampa_lotto_fuori_scope_o_inesistente_404(self) -> None:
        with patch(_VEN_REPO) as VenRepo, \
             patch(f"{_SVC}.VenditePipelineRepository") as PipeRepo:
            VenRepo.return_value.get_lotto.return_value = None
            with self.assertRaises(ServiceError) as ctx:
                ristampa_lotto(lotto_id=999, auth_user_id=9)

        self.assertEqual(ctx.exception.code, "E_LOTTO_NON_TROVATO")
        PipeRepo.return_value.accoda_stampe_lotto.assert_not_called()

    # 5. Lotto non DEFINITIVA (es. EMESSA) → gate I-7: niente ristampa (che
    #    numererebbe via backstop), niente accoda.
    def test_ristampa_lotto_non_definitiva_raises(self) -> None:
        with patch(_VEN_REPO) as VenRepo, \
             patch(f"{_SVC}.VenditePipelineRepository") as PipeRepo:
            VenRepo.return_value.get_lotto.return_value = {
                "id": 5, "stato_doc_fiscale_id": 2,  # EMESSA
            }
            PipeRepo.return_value.get_stato_doc_fiscale_id.return_value = 8  # DEFINITIVA
            with self.assertRaises(ServiceError) as ctx:
                ristampa_lotto(lotto_id=5, auth_user_id=9)

        self.assertEqual(ctx.exception.code, "E_LOTTO_NON_RISTAMPABILE")
        PipeRepo.return_value.accoda_stampe_lotto.assert_not_called()


class EsitiFatturazioneTests(SimpleTestCase):

    # 3. Filtra i jobname di fatturazione e ritorna la coda scoped all'operatore.
    def test_esiti_filtra_jobname_fatturazione_e_coda_scoped(self) -> None:
        summary = [
            # last_run_at nel formato TESTO PG (spazio, non 'T'): il service lo
            # normalizza a ISO-8601 per il parse Date() cross-browser del FE.
            {
                "jobname": "run_fatturazione_batch:differita",
                "last_ok": True,
                "last_run_at": "2026-07-20 10:00:00.123+00",
            },
            {"jobname": "draina_coda_stampa", "last_ok": True, "last_run_at": None},
            {"jobname": "pulizia_storico_notturna", "last_ok": True},  # estraneo
        ]
        with patch(
            "apps.core.db.maintenance_repository.MaintenanceRepository"
        ) as MaintRepo, \
             patch(f"{_SVC}.VenditePipelineRepository") as PipeRepo:
            MaintRepo.return_value.list_job_summary.return_value = (summary, 3)
            PipeRepo.return_value.count_coda_stampa_per_stato.return_value = {
                "PENDING": 2, "FATTO": 5,
            }

            result = esiti_fatturazione(auth_user_id=9)

        jobnames = {g["jobname"] for g in result["giri"]}
        self.assertEqual(
            jobnames,
            {"run_fatturazione_batch:differita", "draina_coda_stampa"},
        )
        self.assertNotIn("pulizia_storico_notturna", jobnames)
        # Timestamp normalizzato a ISO-8601 (spazio PG -> 'T'); None preservato.
        by_name = {g["jobname"]: g for g in result["giri"]}
        self.assertEqual(
            by_name["run_fatturazione_batch:differita"]["last_run_at"],
            "2026-07-20T10:00:00.123+00",
        )
        self.assertIsNone(by_name["draina_coda_stampa"]["last_run_at"])
        self.assertEqual(result["coda_stampa"], {"PENDING": 2, "FATTO": 5})
        # La coda è letta con lo scope emittente dell'operatore (brief §5).
        PipeRepo.return_value.count_coda_stampa_per_stato.assert_called_once_with(
            auth_user_id=9,
        )
