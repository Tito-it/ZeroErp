# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit di `SorgentiRepository.get_sorgente_attiva` (cursor finto,
#        regola CI: niente DB reale): la lettura unica di config.sorgenti per
#        codice, che ha ritirato le tre copie di documenti, resi e lineage.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) test_riga_attiva_restituita_con_chiave_e_tabella
2) test_solo_sorgenti_attive_e_codice_come_parametro
3) test_codice_assente_o_spento_e_none
4) test_target_table_null_resta_none
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.config.db.sorgenti_repository import SorgentiRepository

_CURSOR = "apps.config.db.sorgenti_repository.connection.cursor"


def _cursor(riga: tuple | None) -> MagicMock:
    cursor = MagicMock()
    cursor.fetchone.return_value = riga
    contesto = MagicMock()
    contesto.__enter__.return_value = cursor
    contesto.__exit__.return_value = False
    return contesto


class SorgentiRepositoryTests(TestCase):

    # Scopo: la riga porta tutto cio' che i tre chiamanti di prima leggevano:
    #        l'id (documenti, resi), la chiave del nodo e la tabella (lineage).
    @patch(_CURSOR)
    def test_riga_attiva_restituita_con_chiave_e_tabella(self, factory) -> None:
        factory.return_value = _cursor((2, "PREVENTIVO", "uid", "vendite.preventivi"))
        self.assertEqual(
            SorgentiRepository().get_sorgente_attiva("PREVENTIVO"),
            {"id": 2, "codice": "PREVENTIVO", "key_selector": "uid",
             "target_table": "vendite.preventivi"},
        )

    # Scopo: l'attivita' la decide la query, una volta, e il codice viaggia
    #        come parametro (mai interpolato).
    @patch(_CURSOR)
    def test_solo_sorgenti_attive_e_codice_come_parametro(self, factory) -> None:
        contesto = _cursor((8, "DDT_VENDITA", "id", "vendite.ddt"))
        factory.return_value = contesto
        SorgentiRepository().get_sorgente_attiva("DDT_VENDITA")
        sql, params = contesto.__enter__.return_value.execute.call_args.args
        self.assertIn("s.codice_interno = %s", sql)
        self.assertIn("s.attivo IS TRUE", sql)
        self.assertEqual(params, ["DDT_VENDITA"])

    # Scopo: codice inesistente o sorgente spenta: per chi chiama e' la stessa
    #        cosa, la sorgente non si usa.
    @patch(_CURSOR)
    def test_codice_assente_o_spento_e_none(self, factory) -> None:
        factory.return_value = _cursor(None)
        self.assertIsNone(SorgentiRepository().get_sorgente_attiva("INESISTENTE"))

    # Scopo: `config.sorgenti.target_table` e' nullable: NULL resta None. La
    #        lettura del lineage che questo BB sostituisce faceva `str()` e
    #        restituiva la tabella 'None'.
    @patch(_CURSOR)
    def test_target_table_null_resta_none(self, factory) -> None:
        factory.return_value = _cursor((1, "ATTIVITA", "id", None))
        riga = SorgentiRepository().get_sorgente_attiva("ATTIVITA")
        assert riga is not None
        self.assertIsNone(riga["target_table"])
