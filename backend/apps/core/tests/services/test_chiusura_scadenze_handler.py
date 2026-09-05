# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test dell'handler `CHIUSURA_SCADENZE` — il lavoro che fino al
#        2026-09-04 girava DENTRO il job pgAgent e che adesso passa dalla coda,
#        un'azienda alla volta, con l'identita' tecnica di quell'azienda.
#
# ⚠️ Database MOCKATO: qui si prova cio' che l'handler DECIDE. Che la funzione
#    esista e faccia il suo lavoro e' provato dal pgTAP del team DB; che il
#    binding regga contro il catalogo vero lo prova
#    `apps/core/tests/db/test_coda_lavori_tipi_handler_guardrail.py` — un mock
#    non vedrebbe una funzione rinominata.
#
# Indice test:
#   1) chiama la funzione di dominio e consegna il suo esito INTERO
#   2) ⛔ NON passa nessun perimetro: il perimetro e' l'identita', e un secondo
#      posto che lo dichiara e' il posto che si dimentica
#   3) l'azienda del payload viaggia nell'esito — un riepilogo senza nome non si
#      legge quando le aziende sono tre
#   4) un esito vuoto non diventa un errore: «niente da chiudere» e' un esito
#   5) l'handler e' registrato sotto l'`handler_code` del seed
# ------------------------------------------------------------

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from apps.core.services.coda_lavori.chiusura_scadenze_handler import (
    HANDLER_CODE,
    chiusura_scadenze_handler,
    register,
)

_MOD = "apps.core.services.coda_lavori.chiusura_scadenze_handler"


# Scopo: un `connection` finto il cui cursore risponde `riga` alla fetchone.
def _connection(riga):
    cursore = MagicMock()
    cursore.fetchone.return_value = riga
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursore
    return conn, cursore


class ChiusuraScadenzeHandlerTests(unittest.TestCase):

    # 1-2-3. Una sola chiamata, senza argomenti, e l'esito consegnato intero.
    def test_chiama_la_funzione_di_dominio_senza_perimetro(self):
        conn, cursore = _connection(({"vendite.contratti": 4},))
        with patch(f"{_MOD}.connection", conn):
            esito = chiusura_scadenze_handler(
                {"emittente_fiscale_id": 3, "emittente_codice": "ACME"},
                scope={"auth_user_id": 7},
            )

        sql, *resto = cursore.execute.call_args.args
        self.assertIn("dbops.fn_apply_chiusura_scadenze()", sql)
        # ⛔ Il punto del cantiere: nessun argomento. Il perimetro arriva
        #    dall'identita' con cui il drenatore ha aperto la sessione, e
        #    passarlo anche qui sarebbe la seconda sede della stessa cosa.
        self.assertEqual(resto, [], "l'handler passa un argomento alla funzione")
        self.assertEqual(esito["chiusure"], {"vendite.contratti": 4})
        self.assertEqual(esito["emittente_codice"], "ACME")
        self.assertEqual(esito["emittente_fiscale_id"], 3)

    # 4. Nessuna riga da chiudere e' un ESITO, non un guasto: un handler che
    #    solleva su «niente da fare» farebbe fallire il lavoro ogni notte in cui
    #    tutto e' a posto, e la coda si riempirebbe di rossi che non lo sono.
    def test_esito_vuoto_non_e_un_errore(self):
        for riga in ((None,), None):
            with self.subTest(riga=riga):
                conn, _cur = _connection(riga)
                with patch(f"{_MOD}.connection", conn):
                    esito = chiusura_scadenze_handler({}, scope=None)
                self.assertEqual(esito["chiusure"], {})
                self.assertIsNone(esito["emittente_codice"])

    # 5. Il binding col seed: `handler_code` e' la chiave del dispatch.
    def test_si_registra_sotto_il_codice_del_seed(self):
        with patch(
            "apps.core.services.coda_lavori.handler_registry.register_handler"
        ) as reg:
            register()
        reg.assert_called_once_with(HANDLER_CODE, chiusura_scadenze_handler)
        self.assertEqual(HANDLER_CODE, "chiusura_scadenze_default")
