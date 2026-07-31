# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari repository clienti — metodo update_cliente_atomico.
#        Verifica whitelist campi, normalizzazione stringa-vuota -> NULL sui
#        campi nullable e serializzazione jsonb del delta prima della chiamata
#        alla funzione madre anagrafiche.fn_update_cliente
#        (fix analisi-fix-transazioni Classe A, finding #1).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_atomico_chiama_fn_madre           — una sola SELECT su fn_update_cliente con (id, categoria, jsonb)
2) test_atomico_whitelist_scarta_ignoti   — chiavi non whitelisted escluse dal jsonb
3) test_atomico_normalizza_empty_nullable — stringa vuota su campo nullable -> None nel jsonb
4) test_atomico_normalizza_empty_numerico  — termine_pagamento_id/garanzia_importo "" -> None (no crash ::integer/::numeric)
5) test_atomico_ritorna_flag              — mappa la row (categoria_aggiornata, campi_aggiornati)
"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.anagrafiche.db.clienti_repository import ClientiRepository

CURSOR = "apps.anagrafiche.db.clienti_repository.connection.cursor"


def _mock_cursor(mocked_factory, row=(False, True)):
    """Scopo: Configura il cursor mockato come context manager con una row."""
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    mocked_factory.return_value = cursor
    cursor.fetchone.return_value = row
    return cursor


def _payload_jsonb(cursor):
    """Scopo: Estrae e decodifica il 3° parametro (jsonb) passato a execute."""
    params = cursor.execute.call_args.args[1]
    return json.loads(params[2])


class UpdateClienteAtomicoTests(TestCase):

    @patch(CURSOR)
    def test_atomico_chiama_fn_madre(self, mocked_factory):
        """Una sola SELECT su anagrafiche.fn_update_cliente con id + categoria + jsonb."""
        cursor = _mock_cursor(mocked_factory, row=(True, True))
        ClientiRepository().update_cliente_atomico(
            7, ba_categoria_cliente_id=9, cliente_fields={"iva_id": 5},
        )
        sql = cursor.execute.call_args.args[0]
        self.assertIn("anagrafiche.fn_update_cliente", sql)
        params = cursor.execute.call_args.args[1]
        self.assertEqual(params[0], 7)
        self.assertEqual(params[1], 9)
        self.assertEqual(_payload_jsonb(cursor), {"iva_id": 5})

    @patch(CURSOR)
    def test_atomico_whitelist_scarta_ignoti(self, mocked_factory):
        """Le chiavi non whitelisted non finiscono nel jsonb passato alla fn."""
        cursor = _mock_cursor(mocked_factory)
        ClientiRepository().update_cliente_atomico(
            1, ba_categoria_cliente_id=None,
            cliente_fields={"iva_id": 5, "campo_ignoto": "x", "id": 999},
        )
        self.assertEqual(_payload_jsonb(cursor), {"iva_id": 5})

    @patch(CURSOR)
    def test_atomico_normalizza_empty_nullable(self, mocked_factory):
        """Stringa vuota su campo nullable (codice_cig) -> None nel jsonb."""
        cursor = _mock_cursor(mocked_factory)
        ClientiRepository().update_cliente_atomico(
            1, ba_categoria_cliente_id=None,
            cliente_fields={"codice_cig": "   ", "codice_cup": "ABC"},
        )
        payload = _payload_jsonb(cursor)
        self.assertIsNone(payload["codice_cig"])
        self.assertEqual(payload["codice_cup"], "ABC")

    @patch(CURSOR)
    def test_atomico_normalizza_empty_numerico(self, mocked_factory):
        """Empty su campi numerici nullable (termine_pagamento_id, garanzia_importo)
        -> None: la fn madre non deve ricevere '' e crashare su ::integer/::numeric."""
        cursor = _mock_cursor(mocked_factory)
        ClientiRepository().update_cliente_atomico(
            1, ba_categoria_cliente_id=None,
            cliente_fields={"termine_pagamento_id": "", "garanzia_importo": "  "},
        )
        payload = _payload_jsonb(cursor)
        self.assertIsNone(payload["termine_pagamento_id"])
        self.assertIsNone(payload["garanzia_importo"])

    @patch(CURSOR)
    def test_atomico_ritorna_flag(self, mocked_factory):
        """Mappa la row della fn madre in dict {categoria_aggiornata, campi_aggiornati}."""
        _mock_cursor(mocked_factory, row=(True, False))
        out = ClientiRepository().update_cliente_atomico(
            1, ba_categoria_cliente_id=9, cliente_fields={},
        )
        self.assertEqual(
            out, {"categoria_aggiornata": True, "campi_aggiornati": False},
        )
