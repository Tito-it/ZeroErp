# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit `draina_coda_stampa` (worker drainer coda stampa, C-2b/C-2d).
#        Mock-only su repository + VenditeRepository + DocumentGenerationService
#        (nessun accesso DB). Verifica: claim vuota, happy-path (numera backstop
#        + genera in contesto sistema + FATTO), resilienza per-riga, ERRORE
#        terminale vs PENDING riprovabile, fattura sparita, reaper stantie.
#
# Indice test (0..N):
#   0. claim_vuota_nessun_lavoro
#   1. happy_path_numera_genera_sistema_fatto
#   2. genera_contesto_sistema_kwargs
#   2b. genera_riceve_il_tipo_della_riga
#   3. errore_terminale_incrementa_e_marca_errore
#   4. errore_sotto_soglia_e_riprovabile
#   5. fattura_sparita_marca_errore_senza_render
#   5b. emittente_non_risolto_marca_errore_senza_render
#   6. resilienza_per_riga_una_fallisce_le_altre_proseguono
#   7. reaper_chiamato_con_stale_minuti
#   8. reaper_disabilitato_con_stale_zero
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.stampa_coda_drainer_service import draina_coda_stampa


# L'emittente per cui il giro sta lavorando: nei mock e' lo stesso della
# fattura (11), perche' il caso normale e' che la coda mostri le proprie
# righe — la RLS ci pensa a monte.
_EMITTENTE = 11


def _item(
    coda_id: int, fattura_id: int, *, template_id=None, tipo_id=None,
) -> dict[str, Any]:
    """Work-item come lo ritorna claim_stampe_pending."""
    return {
        "id": coda_id,
        "sorgente_tipo_id": 10,
        "sorgente_id": fattura_id,
        "sorgente_uid": str(fattura_id),
        "lotto_id": 7,
        "template_documento_id": template_id,
        "tipo_documento_output_id": tipo_id,
        "tentativi": 0,
    }


def _mocks(*, claim, entity=None, genera=None):
    """Costruisce (repo, vendite_repo, doc_service) mock con default sensati."""
    repo = MagicMock()
    repo.reset_stale_stampe_in_corso.return_value = 0
    repo.claim_stampe_pending.return_value = claim
    repo.marca_stampa_errore.return_value = "ERRORE"

    vendite_repo = MagicMock()
    vendite_repo.get_fattura_for_documento_generation.return_value = (
        entity if entity is not None
        else {"id": 1, "uid": "u", "emittente_fiscale_id": 11}
    )

    doc_service = MagicMock()
    doc_service.genera_documento.return_value = genera or {
        "id": 100, "uid": "doc-100", "nome_file": "fattura.pdf",
    }
    return repo, vendite_repo, doc_service


class DrainerHappyPathTests(SimpleTestCase):

    # 0. Coda vuota: nessun render, summary a zero.
    def test_claim_vuota_nessun_lavoro(self) -> None:
        repo, vr, ds = _mocks(claim=[])
        summary = draina_coda_stampa(
            emittente_fiscale_id=_EMITTENTE, repo=repo, vendite_repo=vr,
            doc_service=ds,
        )
        self.assertEqual(summary["claimate"], 0)
        self.assertEqual(summary["fatto"], 0)
        ds.genera_documento.assert_not_called()

    # 1. Happy path: numera backstop → genera → marca FATTO col documento.
    def test_happy_path_numera_genera_sistema_fatto(self) -> None:
        repo, vr, ds = _mocks(claim=[_item(1, 42)])
        summary = draina_coda_stampa(
            emittente_fiscale_id=_EMITTENTE, repo=repo, vendite_repo=vr,
            doc_service=ds,
        )

        self.assertEqual(summary["fatto"], 1)
        self.assertEqual(summary["errore"], 0)
        self.assertEqual(summary["riprovabili"], 0)
        repo.numera_fattura_backstop.assert_called_once_with(42)
        repo.marca_stampa_fatto.assert_called_once_with(1, 100)
        repo.marca_stampa_errore.assert_not_called()

    # 2. ⭐ Il render riceve il PERIMETRO dell'utente tecnico, non piu' `None`
    #    (2026-09-05): user=None resta — il worker non e' una richiesta web —
    #    ma «per conto di chi» adesso c'e', ed e' quello che rende il guard
    #    `guard_emittente_in_scope` capace di dire qualcosa.
    def test_genera_con_perimetro_esplicito_kwargs(self) -> None:
        repo, vr, ds = _mocks(claim=[_item(1, 42, template_id=5)])
        draina_coda_stampa(
            emittente_fiscale_id=_EMITTENTE, repo=repo, vendite_repo=vr,
            doc_service=ds,
        )

        args, kwargs = ds.genera_documento.call_args
        self.assertIsNone(args[0])  # user posizionale = None
        self.assertEqual(kwargs["emittente_scope"], [_EMITTENTE])
        self.assertEqual(kwargs["emittente_fiscale_id"], 11)
        self.assertEqual(kwargs["sorgente_tipo_id"], 10)
        self.assertEqual(kwargs["sorgente_id"], 42)
        self.assertEqual(kwargs["sorgente_uid"], "42")
        self.assertEqual(kwargs["template_documento_id"], 5)
        self.assertIsNone(kwargs["tipo_documento_output_id"])

    # 2b. Il tipo di documento della riga arriva al render (§9): senza, su
    #     una sorgente con piu' tipi la risoluzione si ferma con AMBIGUO.
    def test_genera_riceve_il_tipo_della_riga(self) -> None:
        repo, vr, ds = _mocks(claim=[_item(1, 42, tipo_id=3)])
        draina_coda_stampa(
            emittente_fiscale_id=_EMITTENTE, repo=repo, vendite_repo=vr,
            doc_service=ds,
        )
        self.assertEqual(ds.genera_documento.call_args.kwargs["tipo_documento_output_id"], 3)
        self.assertIsNone(ds.genera_documento.call_args.kwargs["template_documento_id"])


class DrainerErrorPathTests(SimpleTestCase):

    # 3. Render fallito, soglia raggiunta → ERRORE terminale.
    def test_errore_terminale_incrementa_e_marca_errore(self) -> None:
        repo, vr, ds = _mocks(claim=[_item(1, 42)])
        ds.genera_documento.side_effect = ServiceError(
            code="E_RENDER_FAILED", message="boom", detail="x",
        )
        repo.marca_stampa_errore.return_value = "ERRORE"

        summary = draina_coda_stampa(
            emittente_fiscale_id=_EMITTENTE, repo=repo, vendite_repo=vr,
            doc_service=ds,
        )

        self.assertEqual(summary["errore"], 1)
        self.assertEqual(summary["riprovabili"], 0)
        repo.marca_stampa_fatto.assert_not_called()
        errore_arg = repo.marca_stampa_errore.call_args.kwargs["errore"]
        self.assertEqual(errore_arg["code"], "E_RENDER_FAILED")

    # 4. Render fallito ma sotto soglia → PENDING (riprovabile).
    def test_errore_sotto_soglia_e_riprovabile(self) -> None:
        repo, vr, ds = _mocks(claim=[_item(1, 42)])
        ds.genera_documento.side_effect = RuntimeError("weasy down")
        repo.marca_stampa_errore.return_value = "PENDING"

        summary = draina_coda_stampa(
            emittente_fiscale_id=_EMITTENTE, repo=repo, vendite_repo=vr,
            doc_service=ds,
        )

        self.assertEqual(summary["riprovabili"], 1)
        self.assertEqual(summary["errore"], 0)

    # 5. Fattura sparita/fuori portata → errore registrato, nessun render.
    def test_fattura_sparita_marca_errore_senza_render(self) -> None:
        repo, vr, ds = _mocks(claim=[_item(1, 42)], entity=None)
        vr.get_fattura_for_documento_generation.return_value = None

        summary = draina_coda_stampa(
            emittente_fiscale_id=_EMITTENTE, repo=repo, vendite_repo=vr,
            doc_service=ds,
        )

        ds.genera_documento.assert_not_called()
        repo.numera_fattura_backstop.assert_not_called()
        errore_arg = repo.marca_stampa_errore.call_args.kwargs["errore"]
        self.assertEqual(errore_arg["code"], "E_FATTURA_NON_TROVATA")
        self.assertEqual(summary["errore"], 1)

    # 5b. Fattura esistente ma senza record EF (LEFT JOIN → emittente NULL):
    #     errore PARLANTE registrato, nessun render né numerazione.
    def test_emittente_non_risolto_marca_errore_senza_render(self) -> None:
        repo, vr, ds = _mocks(claim=[_item(1, 42)])
        vr.get_fattura_for_documento_generation.return_value = {
            "id": 42, "uid": "42", "emittente_fiscale_id": None,
        }

        summary = draina_coda_stampa(
            emittente_fiscale_id=_EMITTENTE, repo=repo, vendite_repo=vr,
            doc_service=ds,
        )

        ds.genera_documento.assert_not_called()
        repo.numera_fattura_backstop.assert_not_called()
        errore_arg = repo.marca_stampa_errore.call_args.kwargs["errore"]
        self.assertEqual(errore_arg["code"], "E_FATTURA_EMITTENTE_NON_RISOLTO")
        self.assertEqual(summary["errore"], 1)

    # 6. Resilienza per-riga: la prima fallisce, la seconda completa comunque.
    def test_resilienza_per_riga(self) -> None:
        repo, vr, ds = _mocks(claim=[_item(1, 42), _item(2, 43)])
        ds.genera_documento.side_effect = [
            ServiceError(code="E_RENDER_FAILED", message="boom"),
            {"id": 200, "uid": "doc-200", "nome_file": "f.pdf"},
        ]
        repo.marca_stampa_errore.return_value = "ERRORE"

        summary = draina_coda_stampa(
            emittente_fiscale_id=_EMITTENTE, repo=repo, vendite_repo=vr,
            doc_service=ds,
        )

        self.assertEqual(summary["claimate"], 2)
        self.assertEqual(summary["fatto"], 1)
        self.assertEqual(summary["errore"], 1)
        repo.marca_stampa_fatto.assert_called_once_with(2, 200)


class DrainerReaperTests(SimpleTestCase):

    # 7. Il reaper viene invocato con soglia stantie + soglia tentativi (anti
    #    poison-job: il recupero consuma un tentativo) e conteggiato.
    def test_reaper_chiamato_con_stale_minuti(self) -> None:
        repo, vr, ds = _mocks(claim=[])
        repo.reset_stale_stampe_in_corso.return_value = 3

        summary = draina_coda_stampa(
            emittente_fiscale_id=_EMITTENTE,
            repo=repo, vendite_repo=vr, doc_service=ds,
            stale_minuti=15, soglia_tentativi=4,
        )

        repo.reset_stale_stampe_in_corso.assert_called_once_with(
            15, soglia_tentativi=4,
        )
        self.assertEqual(summary["recuperate"], 3)

    # 8. stale_minuti=0 disabilita il reaper (nessuna chiamata).
    def test_reaper_disabilitato_con_stale_zero(self) -> None:
        repo, vr, ds = _mocks(claim=[])
        summary = draina_coda_stampa(
            emittente_fiscale_id=_EMITTENTE,
            repo=repo, vendite_repo=vr, doc_service=ds, stale_minuti=0,
        )
        repo.reset_stale_stampe_in_corso.assert_not_called()
        self.assertEqual(summary["recuperate"], 0)
