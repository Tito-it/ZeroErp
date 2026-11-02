# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
#   6) 🔴 il `jsonb` arriva come STRINGA — la forma che il driver consegna
#      davvero — e l'esito si legge lo stesso
#   7) e arriva anche come dict: il ripiego regge entrambe le forme
#   8) un `jsonb` malformato non fa fallire il lavoro: ripiega su un esito vuoto
#
# 🔴 PERCHE' I TEST 6 E 7 ESISTONO (2026-09-09), ed e' la lezione di questo file.
#    Fino a oggi la riga finta di ogni test qui dentro conteneva un **dict**
#    (`({"vendite.contratti": 4},)`), e l'handler faceva `dict(riga[0])`: verde.
#    In produzione il driver consegna quel `jsonb` come **str**, e `dict("{...}")`
#    itera i caratteri ⇒ `ValueError: dictionary update sequence element #0 has
#    length 1; 2 is required`. Il job ha fallito **quattro notti di fila**
#    (5-8 settembre), due volte per notte, mentre questo test era verde.
#    ⛔ Il difetto non era la mancanza di un test: era che il test **mockava una
#    forma che il driver non produce**. Un mock non sbaglia mai da solo — sbaglia
#    quando la forma che finge non e' quella vera, e allora presidia il contrario
#    di quello per cui e' stato scritto.
#    ⚠️ Il commento in testa diceva gia' «Database MOCKATO: qui si prova cio' che
#    l'handler DECIDE», delegando il resto al guardrail del binding. Giusto — ma
#    fra le due cose c'era una terza, **la forma del valore che torna**, e non la
#    guardava nessuno.
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
    # ⛔ La riga finta porta una **STRINGA**, che e' cio' che il driver consegna
    #    davvero: e' l'unico test che verifica l'esito INTERO, e farlo su una
    #    forma che il driver non produce e' esattamente il difetto raccontato in
    #    testa a questo file. ⚠️ Il caso `dict` non sparisce — vive nel test 6-7,
    #    dove e' dichiarato per quello che e': un ripiego, non il caso normale.
    def test_chiama_la_funzione_di_dominio_senza_perimetro(self):
        conn, cursore = _connection(('{"vendite.contratti": 4}',))
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

    # 6-7. La FORMA del valore che torna dal cursor: e' la riga che e' costata
    #      quattro notti. Le due sottoprove non sono ridondanti — la prima e' il
    #      caso REALE (il driver non decodifica i jsonb fuori dall'ORM), la
    #      seconda e' il ripiego difensivo per il giorno in cui lo facesse.
    def test_il_jsonb_si_legge_sia_come_stringa_sia_come_dict(self):
        atteso = {"_total": 3, "vendite.contratti": 3}
        forme = {
            "stringa (cio' che il driver consegna davvero)":
                '{"_total": 3, "vendite.contratti": 3}',
            "dict (se un giorno il driver decodificasse)":
                {"_total": 3, "vendite.contratti": 3},
        }
        for nome, valore in forme.items():
            with self.subTest(forma=nome):
                conn, _cur = _connection((valore,))
                with patch(f"{_MOD}.connection", conn):
                    esito = chiusura_scadenze_handler({"emittente_codice": "ACME"})
                self.assertEqual(esito["chiusure"], atteso)

    # 8. ⚠️ E un JSON che non e' un oggetto non deve far esplodere il job notturno:
    #    `coerce_jsonb_dict` ripiega su `{}` invece di sollevare, perche' questo
    #    e' un percorso di LETTURA — «niente da chiudere» resta un esito.
    def test_un_jsonb_malformato_non_fa_fallire_il_lavoro(self):
        for valore in ("non-json", "[1, 2]", "null"):
            with self.subTest(valore=valore):
                conn, _cur = _connection((valore,))
                with patch(f"{_MOD}.connection", conn):
                    esito = chiusura_scadenze_handler({})
                self.assertEqual(esito["chiusure"], {})

    # 5. Il binding col seed: `handler_code` e' la chiave del dispatch.
    def test_si_registra_sotto_il_codice_del_seed(self):
        with patch(
            "apps.core.services.coda_lavori.handler_registry.register_handler"
        ) as reg:
            register()
        reg.assert_called_once_with(HANDLER_CODE, chiusura_scadenze_handler)
        self.assertEqual(HANDLER_CODE, "chiusura_scadenze_default")
