# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
#   6. esiti_chiede_solo_corsie_fatturazione_e_coda_scoped
#   7. esiti_filtra_per_competenza_normalizzando_al_primo_del_mese
#   8. esiti_coda_stampa_filtrata_per_competenza
#   9. esiti_senza_competenza_coda_non_filtrata
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
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

    # 3. Chiede al repo SOLO le corsie di fatturazione e ritorna la coda scoped
    #    all'operatore. Il filtro jobname vive in SQL (parametro del repo), non
    #    in un post-filtro Python: col `LIMIT` del summary un post-filtro
    #    taglierebbe prima di scartare i job estranei.
    def test_esiti_chiede_solo_corsie_fatturazione_e_coda_scoped(self) -> None:
        summary = [
            # last_run_at nel formato TESTO PG (spazio, non 'T'): il service lo
            # normalizza a ISO-8601 per il parse Date() cross-browser del FE.
            # `ultima_conclusa` arriva gia' in ISO-8601 dal repository
            # (2026-09-14) e passa cosi' com'e'.
            {
                "jobname": "run_fatturazione_batch:differita",
                "last_run_at": "2026-07-20 10:00:00.123+00",
                "in_corso": True,
                "ultima_conclusa": {
                    "started_at": "2026-07-19T10:00:00+00:00",
                    "ended_at": "2026-07-19T10:02:00+00:00", "ok": True,
                },
            },
            {
                "jobname": "run_fatturazione_batch:immediata",
                "last_run_at": None,
                "in_corso": False,
                "ultima_conclusa": None,
            },
        ]
        with patch(
            "apps.core.db.maintenance_repository.MaintenanceRepository"
        ) as MaintRepo, \
             patch(
                 "apps.core.services.coda_lavori.repository.CodaLavoriRepository"
             ) as CodaRepo, \
             patch(f"{_SVC}.VenditePipelineRepository") as PipeRepo:
            CodaRepo.return_value.summary_per_job_type.return_value = []
            MaintRepo.return_value.list_job_summary.return_value = (summary, 2)
            PipeRepo.return_value.count_coda_stampa_per_stato.return_value = {
                "PENDING": 2, "FATTO": 5,
            }

            result = esiti_fatturazione(auth_user_id=9)

        # Il repo e' interrogato col prefisso delle sole corsie: i worker
        # draina_* non devono nemmeno essere letti (2026-07-23).
        kwargs = MaintRepo.return_value.list_job_summary.call_args.kwargs
        self.assertEqual(kwargs["jobname_prefix"], "run_fatturazione_batch")
        # Senza competenza esplicita: nessun filtro di mese (totali da sempre).
        self.assertIsNone(kwargs["meta_month_equals"])

        jobnames = {g["jobname"] for g in result["giri"]}
        self.assertEqual(
            jobnames,
            {"run_fatturazione_batch:differita", "run_fatturazione_batch:immediata"},
        )
        # Timestamp normalizzato a ISO-8601 (spazio PG -> 'T', offset
        # completato a ±HH:MM per Safari); None preservato.
        by_name = {g["jobname"]: g for g in result["giri"]}
        self.assertEqual(
            by_name["run_fatturazione_batch:differita"]["last_run_at"],
            "2026-07-20T10:00:00.123+00:00",
        )
        self.assertIsNone(by_name["run_fatturazione_batch:immediata"]["last_run_at"])
        # ⛔ `in_corso` e `ultima_conclusa` attraversano il service INTATTI: e'
        #    il punto di trasporto fra il repository e il pannello, e un campo
        #    perso qui riporterebbe il pannello a leggere un esito senza data.
        differita = by_name["run_fatturazione_batch:differita"]
        self.assertTrue(differita["in_corso"])
        self.assertEqual(
            differita["ultima_conclusa"],
            {
                "started_at": "2026-07-19T10:00:00+00:00",
                "ended_at": "2026-07-19T10:02:00+00:00", "ok": True,
            },
        )
        self.assertIsNone(by_name["run_fatturazione_batch:immediata"]["ultima_conclusa"])
        self.assertEqual(result["coda_stampa"], {"PENDING": 2, "FATTO": 5})
        # La coda è letta con lo scope emittente dell'operatore (brief §5);
        # senza competenza esplicita resta cumulativa.
        PipeRepo.return_value.count_coda_stampa_per_stato.assert_called_once_with(
            auth_user_id=9, competenza_mese=None,
        )

    # 3-bis. Le DUE strade di lancio convivono nella stessa lista, marcate da
    #    `origine`: attivare o spegnere il batch schedulato non deve far sparire
    #    i giri lanciati dall'app, né viceversa. È la regressione che il pannello
    #    aveva già subito (leggeva solo il batch e dichiarava «nessun giro»
    #    mentre si fatturava ogni giorno dall'app).
    def test_esiti_unisce_giri_app_e_batch_marcandone_origine(self) -> None:
        with patch(
            "apps.core.db.maintenance_repository.MaintenanceRepository"
        ) as MaintRepo, \
             patch(
                 "apps.core.services.coda_lavori.repository.CodaLavoriRepository"
             ) as CodaRepo, \
             patch(
                 "apps.core.services.coda_lavori.gestione_service"
                 ".scope_key_operatore",
                 return_value="scope-1",
             ) as mock_scope, \
             patch(f"{_SVC}.VenditePipelineRepository") as PipeRepo:
            CodaRepo.return_value.summary_per_job_type.return_value = [
                {
                    "jobname": "FATTURAZIONE_GIRO", "total_runs": 13,
                    "ok_count": 10, "fail_count": 1, "mio_count": 5,
                    "last_run_at": "2026-07-23 00:43:24+00", "in_corso": False,
                    "ultima_conclusa": {
                        "started_at": "2026-07-23T00:43:00+00:00",
                        "ended_at": "2026-07-23T00:43:24+00:00", "ok": True,
                    },
                },
            ]
            MaintRepo.return_value.list_job_summary.return_value = ([
                {
                    "jobname": "run_fatturazione_batch:differita",
                    "total_runs": 24, "ok_count": 23, "fail_count": 1,
                    "last_run_at": "2026-06-20 00:31:09+00", "in_corso": False,
                    "ultima_conclusa": {
                        "started_at": "2026-06-20T00:31:00+00:00",
                        "ended_at": "2026-06-20T00:31:09+00:00", "ok": True,
                    },
                },
            ], 1)
            PipeRepo.return_value.count_coda_stampa_per_stato.return_value = {}

            result = esiti_fatturazione(
                auth_user_id=9, competenza_mese=date(2026, 6, 1), user=object(),
            )

        per_origine = {g["origine"]: g for g in result["giri"]}
        self.assertEqual(set(per_origine), {"app", "batch"})
        self.assertEqual(per_origine["app"]["jobname"], "FATTURAZIONE_GIRO")
        self.assertEqual(per_origine["app"]["ok_count"], 10)
        # Split miei/altri (decisione Tid 2026-07-23): il totale resta
        # COMPLESSIVO, `altri_count` derivato come total - mio. Le righe batch
        # non hanno split: sono di sistema, non di un operatore.
        self.assertEqual(per_origine["app"]["mio_count"], 5)
        self.assertEqual(per_origine["app"]["altri_count"], 8)
        self.assertNotIn("mio_count", per_origine["batch"])
        self.assertEqual(
            per_origine["batch"]["jobname"], "run_fatturazione_batch:differita",
        )
        # Timestamp normalizzati a ISO-8601 da ENTRAMBE le sorgenti
        # (offset completato a ±HH:MM per Safari).
        self.assertEqual(per_origine["app"]["last_run_at"], "2026-07-23T00:43:24+00:00")
        self.assertEqual(per_origine["batch"]["last_run_at"], "2026-06-20T00:31:09+00:00")
        # I giri dell'app: filtro per competenza DICHIARATA; la scope key del
        # chiamante serve allo SPLIT, non a filtrare (conteggi complessivi).
        kwargs = CodaRepo.return_value.summary_per_job_type.call_args.kwargs
        self.assertEqual(kwargs["competenza_mese"], date(2026, 6, 1))
        self.assertEqual(kwargs["caller_scope_key"], "scope-1")
        self.assertEqual(
            kwargs["job_types"], ["FATTURAZIONE_GIRO", "FATTURAZIONE_NUMERA"],
        )
        mock_scope.assert_called_once()

    # 4. `competenza_mese` → filtro sul mese attribuito al run, NORMALIZZATO al
    #    1° del mese (il batch scrive sempre il 1°: un 15/07 dal DatePicker non
    #    deve produrre zero risultati per un mese che invece ha girato).
    def test_esiti_filtra_per_competenza_normalizzando_al_primo_del_mese(self) -> None:
        with patch(
            "apps.core.db.maintenance_repository.MaintenanceRepository"
        ) as MaintRepo, \
             patch(
                 "apps.core.services.coda_lavori.repository.CodaLavoriRepository"
             ) as CodaRepo, \
             patch(f"{_SVC}.VenditePipelineRepository") as PipeRepo:
            CodaRepo.return_value.summary_per_job_type.return_value = []
            MaintRepo.return_value.list_job_summary.return_value = ([], 0)
            PipeRepo.return_value.count_coda_stampa_per_stato.return_value = {}

            result = esiti_fatturazione(
                auth_user_id=9, competenza_mese=date(2026, 7, 15),
            )

        kwargs = MaintRepo.return_value.list_job_summary.call_args.kwargs
        self.assertEqual(
            kwargs["meta_month_equals"], ("competenza", "2026-07-01"),
        )
        # Nessun giro per quel mese: lista vuota, non un errore.
        self.assertEqual(result["giri"], [])

    # 5. Anche la coda stampa segue il mese filtrato: senza, i suoi contatori
    #    sarebbero cumulativi da sempre e il pannello mescolerebbe due periodi
    #    (giri del mese X + coda di sempre).
    def test_esiti_coda_stampa_filtrata_per_competenza(self) -> None:
        with patch(
            "apps.core.db.maintenance_repository.MaintenanceRepository"
        ) as MaintRepo, \
             patch(
                 "apps.core.services.coda_lavori.repository.CodaLavoriRepository"
             ) as CodaRepo, \
             patch(f"{_SVC}.VenditePipelineRepository") as PipeRepo:
            CodaRepo.return_value.summary_per_job_type.return_value = []
            MaintRepo.return_value.list_job_summary.return_value = ([], 0)
            PipeRepo.return_value.count_coda_stampa_per_stato.return_value = {
                "PENDING": 3,
            }

            result = esiti_fatturazione(
                auth_user_id=9, competenza_mese=date(2026, 7, 1),
            )

        self.assertEqual(result["coda_stampa"], {"PENDING": 3})
        PipeRepo.return_value.count_coda_stampa_per_stato.assert_called_once_with(
            auth_user_id=9, competenza_mese=date(2026, 7, 1),
        )

    # 6. Senza competenza la coda resta cumulativa (nessun filtro propagato):
    #    è il caso "filtro svuotato" per le consultazioni storiche.
    def test_esiti_senza_competenza_coda_non_filtrata(self) -> None:
        with patch(
            "apps.core.db.maintenance_repository.MaintenanceRepository"
        ) as MaintRepo, \
             patch(
                 "apps.core.services.coda_lavori.repository.CodaLavoriRepository"
             ) as CodaRepo, \
             patch(f"{_SVC}.VenditePipelineRepository") as PipeRepo:
            CodaRepo.return_value.summary_per_job_type.return_value = []
            MaintRepo.return_value.list_job_summary.return_value = ([], 0)
            PipeRepo.return_value.count_coda_stampa_per_stato.return_value = {}

            esiti_fatturazione(auth_user_id=9)

        PipeRepo.return_value.count_coda_stampa_per_stato.assert_called_once_with(
            auth_user_id=9, competenza_mese=None,
        )
