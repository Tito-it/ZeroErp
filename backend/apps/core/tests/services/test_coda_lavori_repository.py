# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
#   5. claim_riordina_per_priorita_e_id
#   6. claim_priorita_vince_sull_id
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
            0, 5, "handler_x", 100,  # ultima colonna: priorita (riordino)
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
        row = (6, "JOB_SISTEMA", "{}", "SISTEMA", None, 0, 5, "handler_y", 100)
        conn.cursor.return_value = _cursor_with([row], many=True)

        items = CodaLavoriRepository().claim(limit=1)

        self.assertIsNone(items[0].scope)
        self.assertEqual(items[0].payload, {})

    # 5. claim: l'ordine di ESECUZIONE e' FIFO (priorita, id) anche se il driver
    #    restituisce le righe in ordine sparso. `UPDATE ... RETURNING` non
    #    garantisce l'ordine della CTE: senza il riordino esplicito, due giri di
    #    fatturazione lanciati di seguito si eseguivano al contrario e il
    #    secondo vinceva la contesa sulle righe (misurato in app 2026-08-17).
    @patch(f"{_MOD}.connection")
    def test_claim_riordina_per_priorita_e_id(self, conn) -> None:
        def _riga(job_id: int, priorita: int = 100) -> tuple:
            return (
                job_id, "FATTURAZIONE_GIRO", "{}", "OPERATORE", None,
                0, 5, "handler_x", priorita,
            )

        # Il driver le restituisce al contrario dell'ordine di accodamento.
        conn.cursor.return_value = _cursor_with(
            [_riga(31), _riga(12), _riga(27)], many=True,
        )

        items = CodaLavoriRepository().claim(limit=10)

        self.assertEqual([i.id for i in items], [12, 27, 31])

    # 6. claim: a parita' di nulla, la priorita' viene PRIMA dell'id — e' la
    #    stessa chiave della CTE, non una FIFO pura (un tipo lungo non deve
    #    affamare gli altri).
    @patch(f"{_MOD}.connection")
    def test_claim_priorita_vince_sull_id(self, conn) -> None:
        conn.cursor.return_value = _cursor_with(
            [
                (10, "T", "{}", "SISTEMA", None, 0, 5, "h", 100),
                (99, "T", "{}", "SISTEMA", None, 0, 5, "h", 10),
            ],
            many=True,
        )

        items = CodaLavoriRepository().claim(limit=10)

        self.assertEqual([i.id for i in items], [99, 10])

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

        det = CodaLavoriRepository().get_dettaglio(5, chiamante=None)

        assert det is not None
        self.assertEqual(det["payload"], {"competenza_mese": "2026-06-01"})
        self.assertIsNone(det["result"])
        self.assertEqual(det["ultimo_errore"], {"code": "AttributeError"})


class CodaLavoriRepositoryStatiDopoAccodamentoTests(SimpleTestCase):

    # Lo stato VERO di ciascun lavoro appena accodato, una query per tutti.
    @patch(f"{_MOD}.connection")
    def test_stati_veri(self, conn) -> None:
        conn.cursor.return_value = _cursor_with([(1, "IN_CORSO"), (2, "PENDING")], many=True)
        self.assertEqual(
            CodaLavoriRepository().stati_dopo_accodamento([1, 2]),
            {1: "IN_CORSO", 2: "PENDING"},
        )

    # ⛔ Un id che la porta ha dato e che chi accoda non vede: porta e policy
    #    non concordano, e non si inventa uno stato.
    @patch(f"{_MOD}.connection")
    def test_id_non_visibile_solleva(self, conn) -> None:
        conn.cursor.return_value = _cursor_with([(1, "PENDING")], many=True)
        with self.assertRaises(RuntimeError) as ctx:
            CodaLavoriRepository().stati_dopo_accodamento([1, 2])
        self.assertIn("[2]", str(ctx.exception))
