# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il command `crea_primo_amministratore` contro il DB vero: il binding
#        per nome con `anagrafiche.fn_crea_primo_amministratore` (dodici
#        argomenti, due jsonb) e la traduzione del rifiuto del verbo, che un
#        mock non vede (memoria del binding mockato). R-DB-K1, passo 3j di
#        brief-db-porte-aperte-dalla-sola-guc §4.9.7.
# Note: opt-in `ZEROERP_TEST_DB_E2E=1`, transazione annullata.
#       ⭐ Lo stato si COSTRUISCE: un SUPER_ADMIN di fixture
#       (`dbops.fn_pgtap_crea_operatore_umano(…, true)`) chiude il primo
#       impianto qualunque cosa ci sia sul DB, anche su quello che la CI
#       ricostruisce da zero, che dopo R-DB-K4 potrebbe non averne.
#       ⚠️ Il ramo che CREA non si prova qui: chiede un sistema senza nessun
#       legame SUPER_ADMIN, che i guard dell'ultimo amministratore non
#       lasciano costruire all'app. Lo prova il pgTAP
#       `anagrafiche/test-crea-primo-amministratore-v1` (runner owner).
#
# Indice test:
#   1) test_primo_impianto_chiuso_e_un_messaggio
#        con un SUPER_ADMIN presente il comando esce con
#        E_PRIMO_AMMINISTRATORE_GIA_PRESENTE, come messaggio
# ------------------------------------------------------------

from __future__ import annotations

import io
import os
import unittest
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection

from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto

_PASSWORD = "Una-Password-Lunga-42!"


class CreaPrimoAmministratoreDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            cur.execute("SELECT auth_user_id FROM dbops.fn_pgtap_crea_operatore_umano('primo impianto', true)")
            row = cur.fetchone()
        assert row is not None

    # 1) Il primo impianto e' chiuso: il verbo risponde, per nome, col suo
    #    codice, e il comando lo dice come messaggio.
    def test_primo_impianto_chiuso_e_un_messaggio(self) -> None:
        with patch.dict(os.environ, {"ZEROERP_PRIMO_AMMINISTRATORE_PASSWORD": _PASSWORD}):
            with self.assertRaises(CommandError) as ctx:
                call_command(
                    "crea_primo_amministratore",
                    "--cognome", "Rossi", "--nome", "Anna",
                    "--codice-fiscale", "RSSNNA80A41H501X", "--sesso", "F",
                    "--email", "primo.impianto@esempio.invalid", "--username", "primo.impianto",
                    "--residenza", '{"indirizzo_libero": "Via Roma 1", "stato_id": 1}',
                    "--noinput",
                    stdout=io.StringIO(),
                )
        # La frase e la soluzione arrivano dal catalogo (messaggio e HINT del
        # rifiuto): la soluzione dice dove andare, con l'invito.
        self.assertIn("E_PRIMO_AMMINISTRATORE_GIA_PRESENTE", str(ctx.exception))
        self.assertIn("il primo impianto è chiuso", str(ctx.exception))
        self.assertIn("con l'invito", str(ctx.exception))
