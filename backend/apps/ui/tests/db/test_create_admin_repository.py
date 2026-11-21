# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il ripiego di `attivo` nelle tre INSERT di `UiAdminRepository`,
#        quando il chiamante non lo nomina. Deve dire cio' che dicono il DB
#        (`DEFAULT true` su definizione e colonna) e i service admin:
#        - definizione e colonna nascono ACCESE (service: default True);
#        - il preset nasce SPENTO (Q26 di brief-db-revisione-ui: la bozza si
#          compone spenta, accenderla incontra il preset gia' acceso del posto).
# Note: ⚠️ Rilievo della verifica del 2026-11-20: il ripiego di definizione e
#       colonna era passato a False insieme a quello del preset, senza che il
#       modello lo chiedesse, e due test DB contavano su colonne nate spente
#       senza dirlo. Unit, cursore finto: si legge il parametro legato.
#
# Indice test:
#   1. test_definizione_senza_attivo_nasce_accesa
#   2. test_colonna_senza_attivo_nasce_accesa
#   3. test_preset_senza_attivo_nasce_spento
# ------------------------------------------------------------

from __future__ import annotations

import unittest
from typing import Any
from unittest.mock import MagicMock, patch

from apps.ui.db.ui_admin_repository import UiAdminRepository

_CONN = "apps.ui.db.ui_admin_repository.connection"


class CreateAttivoRipiegoTests(unittest.TestCase):
    # Scopo: l'ultimo parametro legato dall'INSERT (`attivo` chiude le tre liste).
    def _attivo_legato(self, crea: str, data: dict[str, Any]) -> Any:
        cursore = MagicMock()
        cursore.fetchone.return_value = (1,)
        with patch(_CONN) as conn:
            conn.cursor.return_value.__enter__.return_value = cursore
            getattr(UiAdminRepository(), crea)(data)
        sql, parametri = cursore.execute.call_args.args
        # `attivo` e' l'ultima colonna dell'INSERT, quindi l'ultimo parametro.
        self.assertRegex(sql, r"attivo\s*\)\s*VALUES")
        return parametri[-1]

    def test_definizione_senza_attivo_nasce_accesa(self) -> None:
        self.assertIs(self._attivo_legato("create_definizione", {
            "codice": "x.y", "descrizione": "X", "schema_dati": "ui",
        }), True)

    def test_colonna_senza_attivo_nasce_accesa(self) -> None:
        self.assertIs(self._attivo_legato("create_colonna", {
            "lista_id": 1, "codice": "c", "etichetta": "C",
            "tipo_colonna": "informazione", "tipo_dato": "string", "ordine_default": 1,
        }), True)

    def test_preset_senza_attivo_nasce_spento(self) -> None:
        self.assertIs(self._attivo_legato("create_preset", {
            "lista_id": 1, "codice": "p", "descrizione": "P", "ambito": "sistema",
        }), False)
