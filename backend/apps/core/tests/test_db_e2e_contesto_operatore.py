# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le risposte di `apri_contesto_operatore` (BB `apps/core/tests/db_e2e.py`)
#        dopo D-AH (brief-db-porte-aperte-dalla-sola-guc §14.9): nessun
#        operatore -> SKIP (ambiente); operatori tutti SUPER_ADMIN -> ROSSO,
#        senza aprire il contesto; un operatore che non lo e' -> il contesto
#        si apre su di lui. Senza DB: il cursore e' finto.
# Note: ⛔ Il secondo caso e' quello che prima consegnava un SUPER_ADMIN preso
#       dai dati: su dbdev il primo operatore lo e', e i test passavano per
#       chi era l'operatore, non per la regola.
# ------------------------------------------------------------

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.tests.db_e2e import apri_contesto_operatore


# Scopo: un cursore finto la cui SELECT dell'operatore risponde `riga`.
def _cursore(riga: tuple | None) -> MagicMock:
    cur = MagicMock()
    cur.fetchone.return_value = riga
    return cur


# Scopo: le SET LOCAL di `app.current_user_id` che il cursore ha ricevuto.
def _utenti_impostati(cur: MagicMock) -> list:
    return [c.args[1] for c in cur.execute.call_args_list if "app.current_user_id" in c.args[0]]


@patch("django.db.connection", MagicMock(in_atomic_block=True))
class ApriContestoOperatoreTests(SimpleTestCase):
    # 1. Nessun operatore attivo: e' l'ambiente, il test salta.
    def test_nessun_operatore_salta(self) -> None:
        cur = _cursore(None)
        with self.assertRaises(unittest.SkipTest):
            apri_contesto_operatore(cur)
        self.assertEqual(_utenti_impostati(cur), [])

    # 2. ⛔ Il primo operatore (l'ORDER BY mette in testa chi non e'
    #    SUPER_ADMIN) e' SUPER_ADMIN: lo sono tutti. Rosso, e il contesto non
    #    si apre su di lui.
    def test_tutti_super_admin_fallisce_senza_aprire_il_contesto(self) -> None:
        cur = _cursore((1, True))
        with self.assertRaises(AssertionError) as ctx:
            apri_contesto_operatore(cur)
        self.assertIn("SUPER_ADMIN", str(ctx.exception))
        self.assertEqual(_utenti_impostati(cur), [])

    # 3. Un operatore che non e' SUPER_ADMIN: il contesto si apre su di lui.
    def test_operatore_non_super_admin_apre_il_contesto(self) -> None:
        cur = _cursore((7, False))
        self.assertEqual(apri_contesto_operatore(cur), 7)
        self.assertEqual(_utenti_impostati(cur), [["7"]])

    # 4. La SELECT ordina chi non e' SUPER_ADMIN in testa: senza, il caso 2
    #    scatterebbe anche su un DB che ha operatori adatti.
    def test_la_scelta_mette_in_testa_chi_non_e_super_admin(self) -> None:
        cur = _cursore((7, False))
        apri_contesto_operatore(cur)
        select = next(c.args[0] for c in cur.execute.call_args_list if "auth_user" in c.args[0])
        self.assertIn("fn_is_super_admin", select)
        self.assertIn("ORDER BY sa, u.id", select)

    # 5. Fuori da una transazione il BB fallisce prima di scegliere.
    def test_fuori_transazione_fallisce(self) -> None:
        cur = _cursore((7, False))
        with patch("django.db.connection", MagicMock(in_atomic_block=False)), \
                self.assertRaises(AssertionError):
            apri_contesto_operatore(cur)
        cur.execute.assert_not_called()
