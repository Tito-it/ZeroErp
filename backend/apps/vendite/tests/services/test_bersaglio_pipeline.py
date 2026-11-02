# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: IL BERSAGLIO sulla strada del PILOTA — il giro per-fattura della
#        pipeline, che e' dove nasce `E_FATTURA_RETTIFICATA_SENZA_NUMERO`.
#        Brief: `brief-db-bersaglio-errore.md` §7-bis (B6, B7).
# ------------------------------------------------------------

"""Indice test previsti.

Il giro per-fattura (`_run_per_fattura_task`), che e' il punto 4:
 1) test_il_bersaglio_sopravvive_al_giro_per_fattura
 2) test_e_con_lui_il_campo_e_la_soluzione

Il `meta` che PERSISTE l'errore (giro asincrono):
 3) test_meta_porta_i_bersagli
 4) test_meta_senza_bersagli_non_mette_la_chiave

Il blob `errore` del runner, che NON passa da un envelope HTTP:
 5) test_errore_del_runner_porta_il_bersaglio
"""

from __future__ import annotations

from contextlib import nullcontext
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.services.db_error_fields import Bersaglio
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_error_fakes import make_db_error
from apps.vendite.services.pipeline_runner import _meta_errore_fattura
from apps.vendite.services.pipeline_step_executor import PipelineStepExecutor


# Scopo: L'errore pilota come il database lo solleva davvero: codice, campo,
#        soluzione e bersaglio, tutti e quattro sui loro canali.
#
#        ⚠️ FORMA AGGIORNATA AL `T-3b` (changeSet `20260824-13`, 2026-08-24):
#        la frase ha perso entrambi gli id e porta il CONTEGGIO dei bloccanti;
#        il bersaglio ne ha DUE, e l'ORDINE e' portante — prima il documento da
#        numerare (835, che e' quello del giro), poi il padre bloccante (820).
#        ⛔ Qui l'ordine non e' un dettaglio: e' cio' che dice QUALE fattura ha
#        rifiutato dentro un giro di lotto, ora che la frase non lo dice piu'.
def _errore_937():
    return make_db_error(
        "Non si puo' numerare il documento: rettifica righe di altri documenti"
        " che non risultano ancora numerati. Documenti da numerare prima: 1.",
        codice="E_FATTURA_RETTIFICATA_SENZA_NUMERO",
        campo="numero",
        hint="Numerare prima i documenti che questo rettifica, poi ripetere.",
        bersaglio="FATTURA:835,FATTURA:820",
    )


class BersaglioGiroPerFatturaTest(SimpleTestCase):
    """⭐ IL PUNTO 4, che e' la strada del pilota.

    Il 937 nasce dentro un task per-fattura, non in un service qualunque: se il
    bersaglio si perdesse QUI, il caso che ha fatto nascere l'intero cantiere
    sarebbe l'unico a restare senza gesto.
    """

    # Scopo: `transaction.atomic` neutralizzato — stessa ragione e stessa
    #        convenzione di `test_pipeline_step_executor`: il savepoint per
    #        fattura e' una query vera, e qui non c'e' database.
    def setUp(self):
        super().setUp()
        patcher = patch(
            "apps.vendite.services.pipeline_step_executor.transaction.atomic",
            new=lambda *a, **k: nullcontext(),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    # Scopo: Costruisce l'executor con un'azione che fallisce come il DB vero.
    def _executor(self):
        repo = MagicMock()
        return PipelineStepExecutor(
            repository=repo,
            fatture_righe_service=MagicMock(),
            error_logger=MagicMock(),
        )

    # Scopo: Fa girare il task per-fattura fino al primo fallimento e ritorna
    #        il `ServiceError` che ne esce.
    def _solleva(self) -> ServiceError:
        executor = self._executor()

        def _azione(_fattura_id):
            raise _errore_937()

        with self.assertRaises(ServiceError) as ctx:
            executor._run_per_fattura_task(
                lotto_id=6034,
                stato_doc_fiscale_id=8,
                task="numera_fatture",
                fattura_ids=[835],
                action=_azione,
            )
        return ctx.exception

    # Scopo: Verifica il caso `test_il_bersaglio_sopravvive_al_giro_per_fattura`.
    def test_il_bersaglio_sopravvive_al_giro_per_fattura(self):
        exc = self._solleva()
        self.assertEqual(exc.code, "E_FATTURA_RETTIFICATA_SENZA_NUMERO")
        # ⭐ Due bersagli, nell'ordine: il documento del giro e poi il padre.
        self.assertEqual(
            exc.targets,
            (Bersaglio(tipo="FATTURA", id="835"), Bersaglio(tipo="FATTURA", id="820")),
        )

    # Scopo: ⭐ Con lui passano il campo da correggere e la SOLUZIONE a catalogo.
    #        Da questa strada non erano mai usciti: usciva il solo
    #        `message_primary`.
    def test_e_con_lui_il_campo_e_la_soluzione(self):
        exc = self._solleva()
        self.assertEqual(exc.fields, ("numero",))
        self.assertIn("Numerare prima", exc.hint or "")


class BersaglioPersistitoTest(SimpleTestCase):
    """Il `meta` della riga di `vendite.fatture_log` — la strada ASINCRONA.

    ⭐ E' il lettore che conta: un giro batch fallisce quando davanti allo
    schermo non c'e' nessuno, e l'unica cosa che resta e' questa riga.
    """

    # Scopo: Verifica il caso `test_meta_porta_i_bersagli`.
    def test_meta_porta_i_bersagli(self):
        exc = ServiceError(
            code="E_FATTURA_RETTIFICATA_SENZA_NUMERO",
            message="x",
            detail="dettaglio",
            targets=(
                Bersaglio(tipo="FATTURA", id="835"),
                Bersaglio(tipo="FATTURA", id="820"),
            ),
        )
        meta = _meta_errore_fattura({"task": "numera_fatture"}, exc)
        self.assertEqual(
            meta["bersagli"],
            [{"type": "FATTURA", "id": "835"}, {"type": "FATTURA", "id": "820"}],
        )
        # ⚠️ Le chiavi sono INGLESI come nell'envelope: il consumatore a video e'
        #    lo stesso, e due forme sarebbero due strade da tenere allineate.
        self.assertEqual(meta["task"], "numera_fatture")

    # Scopo: ⛔ La chiave si mette SOLO se c'e' qualcosa da dire. E' la stessa
    #        disciplina scritta nel pilota lato database: una chiave presente e
    #        inutilizzabile non vuol dire «nessun bersaglio», vuol dire
    #        «bersaglio rotto» — un difetto segnalato su un ramo che funziona.
    def test_meta_senza_bersagli_non_mette_la_chiave(self):
        exc = ServiceError(code="E_X", message="x", detail=None)
        self.assertNotIn("bersagli", _meta_errore_fattura({}, exc))


class BersaglioEsitoRunnerTest(SimpleTestCase):
    """⚠️ Il blob `errore` del runner, che NON e' un envelope HTTP.

    Questi endpoint rispondono **200 anche quando la catena si ferma**: il
    fallimento e' un campo del payload. Chi legge un 200 non guarda l'envelope
    d'errore, quindi tutto cio' che non entra in questo dizionario a video non
    arriva — ed e' proprio la strada del pilota.
    """

    # Scopo: Verifica il caso `test_errore_del_runner_porta_il_bersaglio`.
    def test_errore_del_runner_porta_il_bersaglio(self):
        from apps.vendite.services.pipeline_runner import LottoPipelineRunner

        exc = ServiceError(
            code="E_FATTURA_RETTIFICATA_SENZA_NUMERO",
            message="Non si puo' numerare il documento: rettifica righe di"
            " altri documenti che non risultano ancora numerati.",
            detail="dettaglio",
            hint="Numerare prima i documenti che questo rettifica.",
            fields=("numero",),
            targets=(
                Bersaglio(tipo="FATTURA", id="835"),
                Bersaglio(tipo="FATTURA", id="820"),
            ),
        )
        repo = MagicMock()
        repo.get_lotto_stato_doc_fiscale_id.return_value = 8
        repo.is_lotto_in_errore.return_value = False
        repo.get_lotto_job_stato.return_value = "ERRORE"
        runner = LottoPipelineRunner(repository=repo)
        with patch.object(runner, "run_pipeline", side_effect=exc), patch.object(
            runner, "_persist_fattura_error_safely"
        ), patch.object(runner, "_mark_lotto_error_safely", create=True):
            esito = runner._drive_lotto_until_done(
                _params_lotto(6034)
            )
        self.assertEqual(esito["motivo_stop"], "ERRORE")
        errore = esito["errore"]
        self.assertEqual(
            errore["targets"],
            [{"type": "FATTURA", "id": "835"}, {"type": "FATTURA", "id": "820"}],
        )
        self.assertEqual(errore["fields"], ["numero"])
        self.assertIn("Numerare prima", errore["hint"])


# Scopo: I parametri minimi del driver, senza dipendere dai default del dominio.
def _params_lotto(lotto_id: int):
    from apps.vendite.services.pipeline_runner import LottoPipelineParams

    return LottoPipelineParams(lotto_id=lotto_id)
