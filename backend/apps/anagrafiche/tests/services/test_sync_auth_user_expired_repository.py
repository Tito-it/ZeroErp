# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `AnagraficheRepository.sync_auth_user_expired` — la disattivazione
#        batch degli utenti scaduti letta dall'EFFETTO, non da una copia della
#        regola (analisi-software-per-dati-morti §2.1, passo 1, 2026-09-12).
#
#        ⭐ PERCHE' UN PRESIDIO. Fino a quel giorno il command si faceva l'elenco
#        dei candidati con una `WHERE` ricopiata in Python — a meta' (solo il
#        ramo legacy) e sulla vista col nome vecchio, che il DB ritira. Ora la
#        regola vive nella sola funzione DB e il repository fotografa gli
#        `auth_user` attivi prima e dopo: chi cambia stato e' chi ha una cache
#        da buttare. Questi test tengono ferme le tre proprieta' che rendono la
#        forma corretta: la differenza e' simmetrica, il dry-run e' la stessa
#        corsa ritirata, e la funzione vera lega davvero (il binding non lo
#        vede nessun mock).
# ------------------------------------------------------------
"""Indice test (0..N):

0. test_gli_id_sono_la_differenza_fra_prima_e_dopo
   Prima {1,2,3} e dopo {1,3}: l'utente 2 e' quello toccato; il conteggio e'
   quello della funzione. Nessuna `WHERE` di dominio nelle query del
   repository: la regola non e' qui.

1. test_la_differenza_e_simmetrica
   Un utente che la funzione RIACCENDESSE ha la stessa cache da buttare di uno
   spento: {1,2} → {1,3} tocca 2 e 3.

2. test_il_dry_run_ritira_la_transazione
   `dry_run=True`: la funzione gira lo stesso (e' cosi' che l'elenco e' quello
   vero) e la transazione viene marcata per il rollback come ULTIMA cosa.

3. test_la_funzione_vera_lega_in_dry_run  [DB provvisto]
   Chiamata reale in dry-run: il binding regge, il risultato ha la forma
   dichiarata, e dopo la corsa gli utenti attivi sono quelli di prima.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from django.db import connection
from django.test import SimpleTestCase

from apps.anagrafiche.db.anagrafiche_repository import AnagraficheRepository
from apps.core.tests.db_e2e import richiedi_db_provvisto
from apps.vendite.tests._helpers.mock_cursor import mock_cursor as _mock_cursor

_MOD = "apps.anagrafiche.db.anagrafiche_repository"


# Scopo: un cursore che risponde in sequenza alle tre query del repository —
#        attivi prima, la funzione, attivi dopo.
def _cursore(prima: set[int], disattivati: int, dopo: set[int]):
    cur = _mock_cursor()
    cur.fetchall.side_effect = [
        [(i,) for i in sorted(prima)],
        [(i,) for i in sorted(dopo)],
    ]
    cur.fetchone.return_value = (disattivati,)
    return cur


class SyncAuthUserExpiredRepositoryTests(SimpleTestCase):
    # Scopo: test 0.
    def test_gli_id_sono_la_differenza_fra_prima_e_dopo(self):
        cur = _cursore({1, 2, 3}, 1, {1, 3})
        with (
            patch(f"{_MOD}.connection") as conn,
            patch(f"{_MOD}.transaction") as tx,
        ):
            conn.cursor.return_value = cur
            n, ids = AnagraficheRepository().sync_auth_user_expired()
        self.assertEqual((n, ids), (1, [2]))
        sql = [c.args[0] for c in cur.execute.call_args_list]
        self.assertEqual(len(sql), 3)
        self.assertIn("fn_sync_auth_user_expired()", sql[1])
        # La regola non e' qui: le due fotografie non conoscono ne' finestre
        # ne' risorse umane ne' identita'.
        for q in (sql[0], sql[2]):
            self.assertIn("django.auth_user", q)
            self.assertNotIn("valido_al", q)
            self.assertNotIn("identita_digitali", q)
            self.assertNotIn("risorse_umane", q)
        tx.set_rollback.assert_not_called()

    # Scopo: test 1.
    def test_la_differenza_e_simmetrica(self):
        cur = _cursore({1, 2}, 1, {1, 3})
        with patch(f"{_MOD}.connection") as conn, patch(f"{_MOD}.transaction"):
            conn.cursor.return_value = cur
            _, ids = AnagraficheRepository().sync_auth_user_expired()
        self.assertEqual(ids, [2, 3])

    # Scopo: test 2.
    def test_il_dry_run_ritira_la_transazione(self):
        cur = _cursore({1, 2}, 1, {1})
        with (
            patch(f"{_MOD}.connection") as conn,
            patch(f"{_MOD}.transaction") as tx,
        ):
            conn.cursor.return_value = cur
            n, ids = AnagraficheRepository().sync_auth_user_expired(dry_run=True)
        self.assertEqual((n, ids), (1, [2]))
        self.assertIn("fn_sync_auth_user_expired()", cur.execute.call_args_list[1].args[0])
        tx.set_rollback.assert_called_once_with(True)
        # Ultima istruzione del blocco: nessuna query DOPO il rollback.
        self.assertEqual(cur.execute.call_count, 3)


# ⚠️ `unittest.TestCase`, NON `django.test.TestCase`: il primo test che
#    dichiarasse un database farebbe creare al runner un DB usa-e-getta per
#    TUTTA la suite, vuoto — dove queste funzioni non esistono (AGENTS.md).
class SyncAuthUserExpiredSulDatabaseTests(unittest.TestCase):
    """Il binding con la funzione vera (opt-in ZEROERP_TEST_DB_E2E)."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # Scopo: test 3 — in dry-run non resta niente, e la forma e' quella dichiarata.
    def test_la_funzione_vera_lega_in_dry_run(self):
        with connection.cursor() as cur:
            cur.execute("SELECT id FROM django.auth_user WHERE is_active = true")
            attivi_prima = {int(r[0]) for r in cur.fetchall()}
        n, ids = AnagraficheRepository().sync_auth_user_expired(dry_run=True)
        self.assertIsInstance(n, int)
        self.assertGreaterEqual(n, 0)
        self.assertEqual(ids, sorted(ids))
        self.assertTrue(all(isinstance(i, int) for i in ids))
        with connection.cursor() as cur:
            cur.execute("SELECT id FROM django.auth_user WHERE is_active = true")
            attivi_dopo = {int(r[0]) for r in cur.fetchall()}
        self.assertEqual(attivi_prima, attivi_dopo)
