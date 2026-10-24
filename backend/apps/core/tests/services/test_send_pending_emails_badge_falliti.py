# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test di `send_pending_emails` sui badge falliti (D9 di
#        brief-db-presidio-job-run-a-chi-tocca): un'azienda il cui giro non
#        parte non lascia righe in `config.email_log`, quindi la corsa chiude
#        rossa con E_JOB_ELEMENTI_NON_COMPLETATI dopo aver servito le altre.
#        Senza DB: giornale, roster e giro sono sostituiti.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) BadgeFallitiTests.test_badge_fallito_chiude_rossa_dopo_le_altre
2) BadgeFallitiTests.test_tutti_i_badge_buoni_chiude_verde
"""
from __future__ import annotations

from contextlib import contextmanager
from io import StringIO
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.core.management import call_command

from apps.core.services.job_run import E_JOB_ELEMENTI_NON_COMPLETATI
from apps.core.services.service_errors import ServiceError
from apps.core.tests.job_run_fakes import fake_registered_job

_CMD = "apps.core.management.commands.send_pending_emails"


def _badge(codice: str, auth_user_id: int) -> dict:
    return {
        "auth_user_id": auth_user_id, "username": f"tecnico.{codice.lower()}",
        "identita_id": auth_user_id, "emittente_fiscale_id": auth_user_id,
        "emittente_codice": codice,
    }


class BadgeFallitiTests(TestCase):

    def _lancia(self, *, falliscono: set[str]):
        cm, self.handle, _catturato = fake_registered_job()
        processi = MagicMock()
        processi.roster_processo.return_value = [_badge("ACME", 7), _badge("BETA", 8)]
        processi.emittenti_non_serviti.return_value = []
        self.serviti: list[str] = []

        @contextmanager
        def _identita(auth_user_id, **kwargs):
            if kwargs["username"] in {f"tecnico.{c.lower()}" for c in falliscono}:
                raise RuntimeError("identita' spenta")
            self.serviti.append(kwargs["username"])
            yield

        giro = {"processate": 1, "inviate": 1, "fallite": 0}
        with patch(f"{_CMD}.registered_job", cm), \
                patch(f"{_CMD}.ProcessiRepository", return_value=processi), \
                patch(f"{_CMD}.operator_identity_context", _identita), \
                patch(f"{_CMD}.Command._esegui_giro", return_value=giro):
            call_command("send_pending_emails", stdout=StringIO(), stderr=StringIO())

    # 1. ⭐ Il giro di ACME non parte: BETA e' servita lo stesso, il meta col
    #    dettaglio arriva al giornale, e la corsa chiude rossa col codice D9.
    def test_badge_fallito_chiude_rossa_dopo_le_altre(self):
        with self.assertRaises(ServiceError) as ctx:
            self._lancia(falliscono={"ACME"})
        self.assertEqual(ctx.exception.code, E_JOB_ELEMENTI_NON_COMPLETATI)
        self.assertIn("ACME", ctx.exception.detail or "")
        self.assertEqual(self.serviti, ["tecnico.beta"])
        meta = self.handle.set_meta.call_args.args[0]
        self.assertEqual([b["emittente_codice"] for b in meta["badge_falliti"]], ["ACME"])

    # 2. Tutti i badge funzionano: la corsa resta verde, come prima.
    def test_tutti_i_badge_buoni_chiude_verde(self):
        self._lancia(falliscono=set())
        self.assertEqual(self.serviti, ["tecnico.acme", "tecnico.beta"])
        self.assertEqual(self.handle.set_meta.call_args.args[0]["badge_falliti"], [])
