# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
2) test_atomico_whitelist_rifiuta_ignoti  — chiave non whitelisted -> RuntimeError, nessuna SELECT (2026-09-26)
2b) test_atomico_whitelist_rifiuta_le_sei_chiavi_migrate — idem per le sei chiavi di I0/I8
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
            7, ba_categoria_cliente_id=9, cliente_fields={"modalita_pagamento_id": 5},
        )
        sql = cursor.execute.call_args.args[0]
        self.assertIn("anagrafiche.fn_update_cliente", sql)
        params = cursor.execute.call_args.args[1]
        self.assertEqual(params[0], 7)
        self.assertEqual(params[1], 9)
        self.assertEqual(_payload_jsonb(cursor), {"modalita_pagamento_id": 5})

    # ⛔ Dal 2026-09-26 la whitelist e' RIGIDA: fino a quel giorno la chiave
    #    ignota veniva SCARTATA in silenzio e il salvataggio «riusciva» senza
    #    averla scritta. Il 400 educato lo da' il service
    #    (`ClientiService.update_cliente`); qui si prova che il repository non
    #    spedisce niente alla fn madre.
    @patch(CURSOR)
    def test_atomico_whitelist_rifiuta_ignoti(self, mocked_factory):
        """Una chiave non whitelisted e' RuntimeError, e la fn madre non si chiama."""
        cursor = _mock_cursor(mocked_factory)
        with self.assertRaises(RuntimeError) as ctx:
            ClientiRepository().update_cliente_atomico(
                1, ba_categoria_cliente_id=None,
                cliente_fields={"modalita_pagamento_id": 5, "campo_ignoto": "x", "id": 999},
            )
        self.assertIn("campo_ignoto", str(ctx.exception))
        self.assertIn("id", str(ctx.exception))
        cursor.execute.assert_not_called()

    @patch(CURSOR)
    def test_atomico_whitelist_rifiuta_le_sei_chiavi_migrate(self, mocked_factory):
        """Le sei chiavi di I0/I8 non arrivano alla fn madre: sono rifiutate.

        ⭐ Il test guarda il lato che quello sopra non guarda: quelle chiavi
        non sono "ignote" (un typo), sono chiavi che il FE ha spedito per mesi.
        Se un giorno rientrassero nella whitelist senza che la colonna esista,
        la fn le scarterebbe in silenzio e il salvataggio sembrerebbe riuscito.
        Sedi nuove: i due flag su `anagrafiche.soggetti` (D8), i tre codici su
        `vendite.contratti` (D9), l'IVA da nessuna parte (D7-bis).
        """
        cursor = _mock_cursor(mocked_factory)
        for chiave in ("iva_id", "cliente_pa", "split_payment",
                       "codice_cig", "codice_cup", "codice_commessa"):
            with self.subTest(chiave=chiave), self.assertRaises(RuntimeError):
                ClientiRepository().update_cliente_atomico(
                    1, ba_categoria_cliente_id=None,
                    cliente_fields={chiave: "S", "modalita_pagamento_id": 5},
                )
        cursor.execute.assert_not_called()

    @patch(CURSOR)
    def test_atomico_normalizza_empty_nullable(self, mocked_factory):
        """Stringa whitespace -> None nel jsonb; stringa piena invariata.

        ⚠️ Il veicolo era `codice_cig`/`codice_cup`, colonne uscite da
        `anagrafiche.clienti` con I8. La PROPRIETA' e' la stessa e vale per
        tutti i campi editabili (`feedback_null_vs_empty`): qui la porta
        `garanzia_tipo`, che e' l'unico campo stringa rimasto in whitelist —
        quindi le due meta' stanno in due chiamate invece che in due colonne.
        """
        cursor = _mock_cursor(mocked_factory)
        ClientiRepository().update_cliente_atomico(
            1, ba_categoria_cliente_id=None,
            cliente_fields={"garanzia_tipo": "   "},
        )
        self.assertIsNone(_payload_jsonb(cursor)["garanzia_tipo"])

        cursor = _mock_cursor(mocked_factory)
        ClientiRepository().update_cliente_atomico(
            1, ba_categoria_cliente_id=None,
            cliente_fields={"garanzia_tipo": "F"},
        )
        self.assertEqual(_payload_jsonb(cursor)["garanzia_tipo"], "F")

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
