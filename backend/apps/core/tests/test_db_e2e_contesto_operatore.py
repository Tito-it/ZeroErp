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
#       Dal 2026-11-27 anche `apri_contesto_su`, la sede unica delle due
#       `SET LOCAL` (brief-be-accessi-credenziale-e-vesti §4): le apre per la
#       sola transazione, e fuori da una transazione fallisce senza scrivere.
#       E `apri_operatore_costruito` (regola del 2, ok Tid 2026-11-27): il
#       builder con la sigla, poi il contesto; fuori transazione non costruisce.
# ------------------------------------------------------------

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.tests.db_e2e import apri_contesto_operatore, apri_contesto_su, apri_operatore_costruito


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


@patch("django.db.connection", MagicMock(in_atomic_block=True))
class ApriContestoSuTests(SimpleTestCase):
    # 6. Le due GUC per la sola transazione (`SET LOCAL`, mai `set_config` di
    #    sessione), sull'utente dato; torna l'utente.
    def test_apre_le_due_guc_per_la_transazione(self) -> None:
        cur = MagicMock()
        self.assertEqual(apri_contesto_su(cur, 42), 42)
        sql = [c.args[0] for c in cur.execute.call_args_list]
        self.assertEqual(len(sql), 2)
        self.assertTrue(all(s.startswith("SET LOCAL app.") for s in sql), sql)
        self.assertEqual(_utenti_impostati(cur), [["42"]])

    # 7. Fuori da una transazione fallisce prima di scrivere.
    def test_fuori_transazione_fallisce_senza_scrivere(self) -> None:
        cur = MagicMock()
        with patch("django.db.connection", MagicMock(in_atomic_block=False)), \
                self.assertRaises(AssertionError) as ctx:
            apri_contesto_su(cur, 42)
        self.assertIn("apri_contesto_su", str(ctx.exception))
        cur.execute.assert_not_called()


@patch("django.db.connection", MagicMock(in_atomic_block=True))
class ApriOperatoreCostruitoTests(SimpleTestCase):
    # 8. Il builder riceve la sigla (NULL senza), e il contesto si apre
    #    sull'utente che ha costruito.
    def test_costruisce_e_apre_il_contesto_sul_costruito(self) -> None:
        for sigla in (None, "B2"):
            with self.subTest(sigla=sigla):
                cur = _cursore((77,))
                self.assertEqual(apri_operatore_costruito(cur, sigla=sigla), 77)
                primo = cur.execute.call_args_list[0]
                self.assertIn("dbops.fn_pgtap_crea_emittente_operatore(", primo.args[0])
                self.assertEqual(primo.args[1], [sigla])
                self.assertEqual(_utenti_impostati(cur), [["77"]])

    # 9. Fuori da una transazione non costruisce niente: l'operatore
    #    resterebbe nel DB.
    def test_fuori_transazione_non_costruisce(self) -> None:
        cur = _cursore((77,))
        with patch("django.db.connection", MagicMock(in_atomic_block=False)), \
                self.assertRaises(AssertionError) as ctx:
            apri_operatore_costruito(cur)
        self.assertIn("apri_operatore_costruito", str(ctx.exception))
        cur.execute.assert_not_called()
