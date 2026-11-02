# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `AuthRepository.get_nomi_credenziale` sul DB vero: la ragione sociale
#        completa del soggetto della credenziale, che il saluto delle email
#        (reset, conferma del cambio password, «invitato da») usa per prima
#        (decisione di Tid, 2026-10-02). La query attraversa veste, ruolo e
#        soggetto: un nome di colonna sbagliato lo vede solo il DB.
# ------------------------------------------------------------

"""Indice test (opt-in `ZEROERP_TEST_DB_E2E=1`).

1. test_operatore_porta_la_ragione_sociale_del_suo_soggetto
2. test_credenziale_senza_vesti_ragione_sociale_vuota
"""

from __future__ import annotations

import unittest
import uuid

from django.contrib.auth.models import User
from django.db import connection

from apps.core.db.auth_repository import AuthRepository
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto


class NomiCredenzialeDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        self.repo = AuthRepository()

    def test_operatore_porta_la_ragione_sociale_del_suo_soggetto(self):
        with connection.cursor() as cur:
            cur.execute("SELECT auth_user_id, soggetto_id FROM dbops.fn_pgtap_crea_operatore_umano('nomi')")
            auth_user_id, soggetto_id = cur.fetchone()
            cur.execute(
                "SELECT ragione_sociale_completa FROM anagrafiche.soggetti WHERE id = %s", [soggetto_id],
            )
            attesa = cur.fetchone()[0]
        nomi = self.repo.get_nomi_credenziale(auth_user_id)
        self.assertTrue(attesa)
        self.assertEqual(nomi["ragione_sociale_completa"], attesa.strip())

    def test_credenziale_senza_vesti_ragione_sociale_vuota(self):
        user = User.objects.create_user(username=f"test_nomi_{uuid.uuid4().hex[:12]}", email="")
        nomi = self.repo.get_nomi_credenziale(user.id)
        self.assertEqual(nomi["ragione_sociale_completa"], "")
        self.assertEqual(nomi["username"], user.username)
