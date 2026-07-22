# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit di regressione per `CodaLavoriRepository` sul decode dei
#        jsonb da cursor RAW: il backend Django per psycopg 3 restituisce i
#        jsonb come `str` — il repository DEVE normalizzarli (`jsonb_out`)
#        prima di esporli a worker/API. Bug reale scoperto dallo smoke C-9
#        «parte alta» (2026-07-22): il worker riceveva payload/scope come
#        stringa e l'handler moriva al primo `.get`.
#
# Indice test:
#   1. claim_decodifica_payload_e_scope_da_str
#   2. claim_scope_null_resta_none
#   3. get_stato_decodifica_result_e_ultimo_errore
#   4. get_dettaglio_decodifica_payload_result_errore
# ------------------------------------------------------------

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.services.coda_lavori.repository import CodaLavoriRepository

_MOD = "apps.core.services.coda_lavori.repository"


def _cursor_with(rows_or_row, *, many: bool) -> MagicMock:
    cursor = MagicMock()
    if many:
        cursor.fetchall.return_value = rows_or_row
    else:
        cursor.fetchone.return_value = rows_or_row
    cm = MagicMock()
    cm.__enter__.return_value = cursor
    cm.__exit__.return_value = False
    return cm


class CodaLavoriRepositoryJsonbTests(SimpleTestCase):

    # 1. claim: payload e scope arrivano come str dal driver → dict al worker.
    @patch(f"{_MOD}.connection")
    def test_claim_decodifica_payload_e_scope_da_str(self, conn) -> None:
        row = (
            5, "FATTURAZIONE_GIRO",
            '{"competenza_mese": "2026-06-01"}',  # payload jsonb come str
            "OPERATORE",
            '{"auth_user_id": 1, "scope_key": "ALL"}',  # scope jsonb come str
            0, 5, "handler_x",
        )
        conn.cursor.return_value = _cursor_with([row], many=True)

        items = CodaLavoriRepository().claim(limit=1)

        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item.payload, {"competenza_mese": "2026-06-01"})
        self.assertEqual(item.payload.get("competenza_mese"), "2026-06-01")
        self.assertEqual(item.scope, {"auth_user_id": 1, "scope_key": "ALL"})

    # 2. claim: job SISTEMA ha scope NULL → resta None (mai coercizzato a {}).
    @patch(f"{_MOD}.connection")
    def test_claim_scope_null_resta_none(self, conn) -> None:
        row = (6, "JOB_SISTEMA", "{}", "SISTEMA", None, 0, 5, "handler_y")
        conn.cursor.return_value = _cursor_with([row], many=True)

        items = CodaLavoriRepository().claim(limit=1)

        self.assertIsNone(items[0].scope)
        self.assertEqual(items[0].payload, {})

    # 3. get_stato: result/ultimo_errore str → dict (o None se NULL).
    @patch(f"{_MOD}.connection")
    def test_get_stato_decodifica_result_e_ultimo_errore(self, conn) -> None:
        row = (5, "FATTURAZIONE_GIRO", "ERRORE", 1, 5,
               '{"lotti": 3}', '{"code": "X"}', 42)
        conn.cursor.return_value = _cursor_with(row, many=False)

        stato = CodaLavoriRepository().get_stato(5)

        assert stato is not None
        self.assertEqual(stato["result"], {"lotti": 3})
        self.assertEqual(stato["ultimo_errore"], {"code": "X"})

    # 4. get_dettaglio: payload/result/ultimo_errore str → oggetti; NULL → None.
    @patch(f"{_MOD}.connection")
    def test_get_dettaglio_decodifica_payload_result_errore(self, conn) -> None:
        row = (
            5, "FATTURAZIONE_GIRO", "PENDING", 100, "API",
            '{"competenza_mese": "2026-06-01"}',  # payload
            1, 5,
            None,  # result NULL
            '{"code": "AttributeError"}',  # ultimo_errore
            None, None, None, None, None, 42,
            "tid", "ALL", True,
        )
        conn.cursor.return_value = _cursor_with(row, many=False)

        det = CodaLavoriRepository().get_dettaglio(5, caller_scope_key="ALL")

        assert det is not None
        self.assertEqual(det["payload"], {"competenza_mese": "2026-06-01"})
        self.assertIsNone(det["result"])
        self.assertEqual(det["ultimo_errore"], {"code": "AttributeError"})
