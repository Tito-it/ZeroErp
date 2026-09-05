# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per il management command sync_auth_user_active.
#        Verifica il flusso batch di disattivazione utenti scaduti
#        e l'invalidazione cache permessi.
# Note: Usa unittest.TestCase con mock (no DB reale, compatibile CI).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) SyncAuthUserActiveTests.test_command_calls_fn_sync_and_reports_count
2) SyncAuthUserActiveTests.test_command_invalidates_cache_for_affected_users
3) SyncAuthUserActiveTests.test_command_dry_run_does_not_call_sync
4) SyncAuthUserActiveTests.test_command_dry_run_reports_affected_count
5) SyncAuthUserActiveTests.test_command_zero_affected_no_invalidation
6) SyncAuthUserActiveTests.test_command_handles_db_error_gracefully
"""

from io import StringIO
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.tests.job_run_fakes import registered_job_muto

from django.core.management import call_command
from django.core.management.base import CommandError


_REPO = "apps.anagrafiche.management.commands.sync_auth_user_active.AnagraficheRepository"
# ⛔ Il run-log NON si scrive davvero nei test: `registered_job` apre e chiude
#    una riga vera su `maintenance.job_run_log`, e il test del percorso
#    d'errore ce ne lasciava una ROSSA. Misurato il 2026-09-05: 93 corse OK
#    e 31 fallite in un giorno, tutte di qui, che accendevano
#    `maintenance.vw_job_run_da_guardare` — un presidio che deve restare
#    vuoto. Il perche' per esteso sta in `apps/core/tests/job_run_fakes.py`.
_JOB = "apps.anagrafiche.management.commands.sync_auth_user_active.registered_job"
_INVALIDATE = "apps.anagrafiche.management.commands.sync_auth_user_active.invalidate_user"


class SyncAuthUserActiveTests(TestCase):

    # Scopo: Verifica che il command chiami fn_sync_auth_user_expired
    # e riporti il conteggio degli utenti disattivati.
    @patch(_JOB, new=registered_job_muto())
    @patch(_INVALIDATE)
    @patch(_REPO)
    def test_command_calls_fn_sync_and_reports_count(
        self, mock_repo_cls, mock_invalidate
    ):
        repo = MagicMock()
        repo.list_expired_auth_user_ids.return_value = [10, 20, 30]
        repo.call_sync_auth_user_expired.return_value = 3
        mock_repo_cls.return_value = repo

        out = StringIO()
        call_command("sync_auth_user_active", stdout=out)

        repo.call_sync_auth_user_expired.assert_called_once()
        output = out.getvalue()
        self.assertIn("3", output)
        self.assertIn("disattivati", output)

    # Scopo: Verifica che invalidate_user venga chiamata per ogni
    # auth_user_id coinvolto nella sync.
    @patch(_JOB, new=registered_job_muto())
    @patch(_INVALIDATE)
    @patch(_REPO)
    def test_command_invalidates_cache_for_affected_users(
        self, mock_repo_cls, mock_invalidate
    ):
        repo = MagicMock()
        repo.list_expired_auth_user_ids.return_value = [10, 20]
        repo.call_sync_auth_user_expired.return_value = 2
        mock_repo_cls.return_value = repo

        out = StringIO()
        call_command("sync_auth_user_active", stdout=out)

        self.assertEqual(mock_invalidate.call_count, 2)
        mock_invalidate.assert_any_call(10)
        mock_invalidate.assert_any_call(20)

    # Scopo: In modalita' dry-run, la funzione SQL di sync NON deve
    # essere chiamata (nessuna modifica al DB).
    @patch(_JOB, new=registered_job_muto())
    @patch(_INVALIDATE)
    @patch(_REPO)
    def test_command_dry_run_does_not_call_sync(
        self, mock_repo_cls, mock_invalidate
    ):
        repo = MagicMock()
        repo.list_expired_auth_user_ids.return_value = [10, 20]
        mock_repo_cls.return_value = repo

        out = StringIO()
        call_command("sync_auth_user_active", "--dry-run", stdout=out)

        repo.call_sync_auth_user_expired.assert_not_called()
        mock_invalidate.assert_not_called()

    # Scopo: In dry-run, il command deve stampare il numero di utenti
    # che sarebbero coinvolti.
    @patch(_JOB, new=registered_job_muto())
    @patch(_INVALIDATE)
    @patch(_REPO)
    def test_command_dry_run_reports_affected_count(
        self, mock_repo_cls, mock_invalidate
    ):
        repo = MagicMock()
        repo.list_expired_auth_user_ids.return_value = [10, 20, 30]
        mock_repo_cls.return_value = repo

        out = StringIO()
        call_command("sync_auth_user_active", "--dry-run", stdout=out)

        output = out.getvalue()
        self.assertIn("3", output)
        self.assertIn("DRY-RUN", output)

    # Scopo: Se non ci sono utenti scaduti, nessuna chiamata a
    # fn_sync_auth_user_expired ne' a invalidate_user.
    @patch(_JOB, new=registered_job_muto())
    @patch(_INVALIDATE)
    @patch(_REPO)
    def test_command_zero_affected_no_invalidation(
        self, mock_repo_cls, mock_invalidate
    ):
        repo = MagicMock()
        repo.list_expired_auth_user_ids.return_value = []
        mock_repo_cls.return_value = repo

        out = StringIO()
        call_command("sync_auth_user_active", stdout=out)

        repo.call_sync_auth_user_expired.assert_not_called()
        mock_invalidate.assert_not_called()
        self.assertIn("Nessun utente", out.getvalue())

    # Scopo: Se il repository solleva un'eccezione, il command deve
    # emetterne una CommandError senza crash incontrollato.
    @patch(_JOB, new=registered_job_muto())
    @patch(_INVALIDATE)
    @patch(_REPO)
    def test_command_handles_db_error_gracefully(
        self, mock_repo_cls, mock_invalidate
    ):
        repo = MagicMock()
        repo.list_expired_auth_user_ids.side_effect = RuntimeError("DB non raggiungibile")
        mock_repo_cls.return_value = repo

        with self.assertRaises(CommandError) as ctx:
            call_command("sync_auth_user_active")

        self.assertIn("DB non raggiungibile", str(ctx.exception))
        mock_invalidate.assert_not_called()
