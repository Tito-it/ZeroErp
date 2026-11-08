# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per il management command sync_auth_user_active.
#        Verifica il flusso batch di riallineamento degli utenti (spegne e accende)
#        e l'invalidazione cache permessi.
# Note: Usa unittest.TestCase con mock (no DB reale, compatibile CI).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) SyncAuthUserActiveTests.test_command_calls_fn_sync_and_reports_count
2) SyncAuthUserActiveTests.test_command_invalidates_cache_for_affected_users
3) SyncAuthUserActiveTests.test_command_dry_run_chiede_la_corsa_ritirata
4) SyncAuthUserActiveTests.test_command_dry_run_reports_affected_count
5) SyncAuthUserActiveTests.test_command_zero_affected_no_invalidation
6) SyncAuthUserActiveTests.test_command_handles_db_error_gracefully
7) SyncAuthUserActiveTests.test_il_command_non_registra_un_run   ⭐
"""

from io import StringIO
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection


_REPO = "apps.anagrafiche.management.commands.sync_auth_user_active.AnagraficheRepository"
# ⛔ NIENTE PATCH DEL RUN-LOG, e non perche' sia diventato innocuo: dal
#    2026-09-07 questo command NON si registra piu' affatto. Fino a quel giorno
#    qui c'era `@patch(..., registered_job_muto())` su ogni caso, perche'
#    `registered_job` apriva e chiudeva una riga VERA su
#    `maintenance.job_run_log` e il test del percorso d'errore ne lasciava una
#    ROSSA (93 corse OK e 31 fallite in un giorno, misurate il 2026-09-05, tutte
#    di qui, che accendevano un presidio che deve restare vuoto).
#    ⚠️ Se un giorno il command tornasse a registrarsi, quei patch tornano
#    OBBLIGATORI insieme: `apps/core/tests/job_run_fakes.py` spiega il perche'.
_INVALIDATE = "apps.anagrafiche.management.commands.sync_auth_user_active.invalidate_user"


class SyncAuthUserActiveTests(TestCase):

    # Scopo: Verifica che il command chiami fn_sync_auth_user_expired
    # e riporti il conteggio degli utenti riallineati.
    @patch(_INVALIDATE)
    @patch(_REPO, autospec=True)
    def test_command_calls_fn_sync_and_reports_count(
        self, mock_repo_cls, mock_invalidate
    ):
        repo = MagicMock()
        repo.sync_auth_user_expired.return_value = (3, [10, 20, 30])
        mock_repo_cls.return_value = repo

        out = StringIO()
        call_command("sync_auth_user_active", stdout=out)

        repo.sync_auth_user_expired.assert_called_once_with(dry_run=False)
        output = out.getvalue()
        self.assertIn("3", output)
        self.assertIn("riallineati", output)

    # Scopo: Verifica che invalidate_user venga chiamata per ogni
    # auth_user_id coinvolto nella sync.
    @patch(_INVALIDATE)
    @patch(_REPO, autospec=True)
    def test_command_invalidates_cache_for_affected_users(
        self, mock_repo_cls, mock_invalidate
    ):
        repo = MagicMock()
        repo.sync_auth_user_expired.return_value = (2, [10, 20])
        mock_repo_cls.return_value = repo

        out = StringIO()
        call_command("sync_auth_user_active", stdout=out)

        self.assertEqual(mock_invalidate.call_count, 2)
        mock_invalidate.assert_any_call(10)
        mock_invalidate.assert_any_call(20)

    # Scopo: In dry-run il command chiede al repository la corsa RITIRATA
    # (`dry_run=True`: stessa funzione, transazione annullata) e non invalida
    # nessuna cache — non e' cambiato niente.
    @patch(_INVALIDATE)
    @patch(_REPO, autospec=True)
    def test_command_dry_run_chiede_la_corsa_ritirata(
        self, mock_repo_cls, mock_invalidate
    ):
        repo = MagicMock()
        repo.sync_auth_user_expired.return_value = (2, [10, 20])
        mock_repo_cls.return_value = repo

        out = StringIO()
        call_command("sync_auth_user_active", "--dry-run", stdout=out)

        repo.sync_auth_user_expired.assert_called_once_with(dry_run=True)
        mock_invalidate.assert_not_called()

    # Scopo: In dry-run, il command deve stampare il numero di utenti
    # che sarebbero coinvolti.
    @patch(_INVALIDATE)
    @patch(_REPO, autospec=True)
    def test_command_dry_run_reports_affected_count(
        self, mock_repo_cls, mock_invalidate
    ):
        repo = MagicMock()
        repo.sync_auth_user_expired.return_value = (3, [10, 20, 30])
        mock_repo_cls.return_value = repo

        out = StringIO()
        call_command("sync_auth_user_active", "--dry-run", stdout=out)

        output = out.getvalue()
        self.assertIn("3", output)
        self.assertIn("DRY-RUN", output)

    # Scopo: Se la funzione non ha toccato nessuno, nessuna cache da
    # invalidare e il messaggio lo dice.
    @patch(_INVALIDATE)
    @patch(_REPO, autospec=True)
    def test_command_zero_affected_no_invalidation(
        self, mock_repo_cls, mock_invalidate
    ):
        repo = MagicMock()
        repo.sync_auth_user_expired.return_value = (0, [])
        mock_repo_cls.return_value = repo

        out = StringIO()
        call_command("sync_auth_user_active", stdout=out)

        mock_invalidate.assert_not_called()
        self.assertIn("Nessun utente", out.getvalue())

    # Scopo: Se il repository solleva un'eccezione, il command deve
    # emetterne una CommandError senza crash incontrollato.
    @patch(_INVALIDATE)
    @patch(_REPO, autospec=True)
    def test_command_handles_db_error_gracefully(
        self, mock_repo_cls, mock_invalidate
    ):
        repo = MagicMock()
        repo.sync_auth_user_expired.side_effect = RuntimeError("DB non raggiungibile")
        mock_repo_cls.return_value = repo

        with self.assertRaises(CommandError) as ctx:
            call_command("sync_auth_user_active")

        self.assertIn("DB non raggiungibile", str(ctx.exception))
        mock_invalidate.assert_not_called()

    # 7. ⭐ IL COMMAND NON APRE NESSUNA CONNESSIONE, cioe' non registra un run.
    #
    # ⛔ ESISTE PERCHE' TOGLIENDO I PATCH SI E' TOLTO ANCHE L'ALLARME. Fino al
    #    2026-09-07 la protezione era il `@patch` su `registered_job`: il giorno
    #    che il command ha smesso di registrarsi i patch sono spariti, e con
    #    loro l'unica cosa che si sarebbe accorta di una registrazione. Chi
    #    riaggiungesse `registered_job` avrebbe SEI test verdi e righe VERE su
    #    `maintenance.job_run_log` — che e' esattamente l'incidente del
    #    2026-09-05, ricomparso dalla porta di servizio.
    # ⭐ Si asserisce il COMPORTAMENTO, non l'assenza di un import: un
    #    `hasattr(modulo, 'registered_job')` coprirebbe una sola forma di
    #    import e non l'altra. `registered_job` apre un cursore alla prima riga,
    #    quindi «nessun cursore» e' la stessa cosa detta in un modo che non si
    #    puo' aggirare per distrazione.
    # ⚠️ Regge perche' repository e cache sono mockati: in questo test nessun
    #    percorso legittimo parla col database.
    @patch(_INVALIDATE)
    @patch(_REPO, autospec=True)
    def test_il_command_non_registra_un_run(self, mock_repo_cls, mock_invalidate):
        repo = MagicMock()
        repo.sync_auth_user_expired.return_value = (1, [10])
        mock_repo_cls.return_value = repo

        with patch.object(connection, "cursor") as mock_cursor:
            call_command("sync_auth_user_active", stdout=StringIO())

        self.assertFalse(
            mock_cursor.called,
            "il command ha aperto una connessione: se e' tornato a registrarsi "
            "sul giornale dei run, il processo di catalogo e' RITIRATO "
            "(obsoleto_dal 2026-09-07) e la corsa a mano accecherebbe il "
            "confronto GIRA_E_NON_REGISTRA sul gemello pgAgent. Vedi l'header "
            "del command e brief-db-sveglia-dei-processi §9.5-bis.",
        )
