# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del telaio delle scritture di diagnosi
#        (`apps/core/services/diagnostica_best_effort.py`).
#
#        ⭐ I DUE VERSI VANNO LETTI IN COPPIA, e da soli non dicono niente:
#        «non solleva» lo farebbe anche un `except: pass`, che e' proprio la
#        cosa da cui il telaio esiste per distinguersi. La differenza fra
#        best-effort e SILENZIO e' la riga nel log tecnico — test 2.
# ------------------------------------------------------------

"""Indice test previsti.

 1) test_azione_riuscita_non_logga_niente
       il caso normale: nessuna riga di errore per una scrittura andata bene.
 2) test_azione_fallita_non_solleva_ma_lascia_traccia
       ⭐ il verso che conta: il chiamante prosegue E il guasto e' visibile,
       col contesto e col messaggio dell'eccezione originale.
 3) test_contesto_e_function_name_arrivano_al_log
       le coordinate sono l'unica cosa che distingue due fallimenti dello
       stesso telaio: se si perdessero, la riga del punto 2 sarebbe inutile.
 4) test_la_scrittura_gira_dentro_un_savepoint
       ⭐ il verso che i primi tre non vedono: senza savepoint il telaio e'
       inutilizzabile dentro una transazione, e i test 1-3 resterebbero verdi
       lo stesso.
"""

from contextlib import contextmanager, nullcontext
from unittest import TestCase
from unittest.mock import patch

from apps.core.services.diagnostica_best_effort import (
    CODICE_DIAGNOSTICA_FALLITA,
    diagnostica_best_effort,
)

_TELAIO = "apps.core.services.diagnostica_best_effort"


# Scopo: neutralizza il SAVEPOINT del telaio, registrando se e' stato aperto.
#
# ⚠️ SERVE, e non e' pigrizia: `transaction.atomic()` apre una connessione, e
#    questi test devono girare in CI SENZA un database (regola in
#    `.codex/AGENTS.md`, «Regole test Django per compatibilita' CI»). Senza la
#    patch il telaio fallirebbe sull'`atomic` invece che sull'azione, e i due
#    versi sotto misurerebbero il guasto sbagliato — passando o fallendo per
#    una ragione che non c'entra niente con quello che presidiano.
#
# ⭐ E il contatore non e' decorativo: il savepoint E' il motivo per cui questo
#    telaio si puo' usare dentro una transazione. Se qualcuno lo togliesse
#    «tanto c'e' il try», i due versi resterebbero verdi — in PostgreSQL una
#    transazione abortita non si recupera ingoiando l'eccezione lato Python, e
#    il guasto si vedrebbe molto piu' in la'. Il test 4 e' li' per quello.
@contextmanager
def _senza_savepoint():
    aperture: list[bool] = []

    def _finto_atomic(*args, **kwargs):
        aperture.append(True)
        return nullcontext()

    with patch(f"{_TELAIO}.transaction.atomic", side_effect=_finto_atomic):
        yield aperture


class DiagnosticaBestEffortTests(TestCase):
    # Scopo: caso normale — l'azione passa, nessuna riga di errore.
    def test_azione_riuscita_non_logga_niente(self):
        eseguita: list[bool] = []
        with _senza_savepoint(), patch(f"{_TELAIO}.ErrorManager.log_error_only") as mock_log:
            diagnostica_best_effort(
                lambda: eseguita.append(True),
                contesto={"lotto_id": 10},
                function_name="vendite.test",
            )
        self.assertEqual(eseguita, [True])
        mock_log.assert_not_called()

    # Scopo: ⭐ il verso che conta. L'azione fallisce: il chiamante NON vede
    #        l'eccezione, ma il guasto lascia una riga nel log tecnico.
    #        Ingoiare senza traccia ricrea il difetto BE-1 — un diario che non
    #        scrive e nessuno che se ne accorga per mesi.
    def test_azione_fallita_non_solleva_ma_lascia_traccia(self):
        def rompi() -> None:
            raise RuntimeError("E_EVENT_LOG_SCOPE_NON_RISOLTO: niente perimetro")

        with _senza_savepoint(), patch(f"{_TELAIO}.ErrorManager.log_error_only") as mock_log:
            # Nessun assertRaises: il punto e' che qui non arriva niente.
            diagnostica_best_effort(
                rompi, contesto={"lotto_id": 10}, function_name="vendite.test"
            )

        mock_log.assert_called_once()
        kw = mock_log.call_args.kwargs
        self.assertEqual(kw["code"], CODICE_DIAGNOSTICA_FALLITA)
        # Il messaggio originale sopravvive: senza, la riga direbbe «qualcosa
        # e' andato storto» e non quale scrittura.
        self.assertIn("E_EVENT_LOG_SCOPE_NON_RISOLTO", kw["context"]["mark_error"])

    # Scopo: le coordinate passate dal chiamante arrivano intatte nel contesto,
    #        insieme al punto del codice che ha tentato la scrittura.
    def test_contesto_e_function_name_arrivano_al_log(self):
        def rompi() -> None:
            raise ValueError("qualunque")

        with _senza_savepoint(), patch(f"{_TELAIO}.ErrorManager.log_error_only") as mock_log:
            diagnostica_best_effort(
                rompi,
                contesto={"commessa_id": 812, "evento": "EMITTIBILITA_FALLITA"},
                function_name="vendite.commesse_service.pr_run_commesse_push",
            )

        kw = mock_log.call_args.kwargs
        self.assertEqual(kw["context"]["commessa_id"], 812)
        self.assertEqual(kw["context"]["evento"], "EMITTIBILITA_FALLITA")
        self.assertEqual(
            kw["function_name"], "vendite.commesse_service.pr_run_commesse_push"
        )

    # Scopo: ⭐ la scrittura gira DENTRO un savepoint, in entrambi i casi.
    #
    #        E' cio' che rende il telaio usabile dentro una transazione: in
    #        PostgreSQL, quando un comando fallisce, l'INTERA transazione entra
    #        in stato abortito, e ingoiare l'eccezione lato Python non la
    #        recupera — il comando successivo muore con «current transaction is
    #        aborted». Il `try` da solo sposta soltanto il punto in cui il giro
    #        si rompe.
    #
    # ⚠️ Il verso conta anche sul SUCCESSO: un savepoint aperto solo nel ramo
    #    d'errore non esisterebbe quando serve, cioe' prima di sapere se
    #    l'azione fallira'.
    def test_la_scrittura_gira_dentro_un_savepoint(self):
        def rompi() -> None:
            raise RuntimeError("qualunque")

        with _senza_savepoint() as aperture:
            with patch(f"{_TELAIO}.ErrorManager.log_error_only"):
                diagnostica_best_effort(
                    lambda: None, contesto={}, function_name="vendite.test"
                )
                diagnostica_best_effort(rompi, contesto={}, function_name="vendite.test")

        self.assertEqual(len(aperture), 2, "savepoint non aperto su uno dei due rami")
