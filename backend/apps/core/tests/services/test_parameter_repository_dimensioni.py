# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il perimetro «di livello puro» degli override parametri, per OGNI
#        livello che il backend scrive e cancella (utente, emittente,
#        categoria cliente): tutte le altre dimensioni di
#        `_DIMENSIONI_OVERRIDE` sono NULL, in upsert e in delete. Senza DB:
#        si legge la SQL che il repository manda (F-5 dell'analisi difetti doc
#        API core, 2026-09-28). La giuntura col DB vero la prova
#        `tests/db/test_parameter_overrides_db.py`.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) DimensioniOverrideTests.test_upsert_azzera_tutte_le_altre_dimensioni
2) DimensioniOverrideTests.test_delete_azzera_tutte_le_altre_dimensioni
3) DimensioniOverrideTests.test_dimensione_sconosciuta_esplode
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.db.parameter_repository import (
    _DIMENSIONI_OVERRIDE,
    ParameterRepository,
    _altre_dimensioni_nulle,
)

_CONN = "apps.core.db.parameter_repository.connection"

# (metodo, colonna di scope)
_UPSERT = (
    ("upsert_user_override", "django_user_id"),
    ("upsert_emittente_override", "emittente_fiscale_id"),
    ("upsert_categoria_cliente_override", "categoria_cliente_id"),
)
_DELETE = (
    ("delete_user_override", "django_user_id"),
    ("delete_emittente_override", "emittente_fiscale_id"),
    ("delete_categoria_cliente_override", "categoria_cliente_id"),
)


def _sql_mandata(mock_conn: MagicMock) -> str:
    cur = mock_conn.cursor.return_value.__enter__.return_value
    return cur.execute.call_args[0][0]


class DimensioniOverrideTests(TestCase):

    # Scopo: Ogni upsert filtra la riga esistente con TUTTE le altre
    # dimensioni NULL (prima utente ed emittente non azzeravano la categoria).
    def test_upsert_azzera_tutte_le_altre_dimensioni(self):
        for metodo, scope in _UPSERT:
            with self.subTest(metodo=metodo), patch(_CONN) as mock_conn:
                cur = mock_conn.cursor.return_value.__enter__.return_value
                cur.fetchone.return_value = (1,)
                getattr(ParameterRepository(), metodo)("P", 5, "v")
                sql = _sql_mandata(mock_conn)
                for dim in _DIMENSIONI_OVERRIDE:
                    if dim == scope:
                        self.assertIn(f"po.{scope} = %s", sql)
                    else:
                        self.assertIn(f"po.{dim} IS NULL", sql)

    # Scopo: Ogni delete cancella solo la riga pura del suo livello (prima la
    # delete emittente guardava solo utente e gruppo).
    def test_delete_azzera_tutte_le_altre_dimensioni(self):
        for metodo, scope in _DELETE:
            with self.subTest(metodo=metodo), patch(_CONN) as mock_conn:
                cur = mock_conn.cursor.return_value.__enter__.return_value
                cur.rowcount = 1
                self.assertTrue(getattr(ParameterRepository(), metodo)(9, 5))
                sql = _sql_mandata(mock_conn)
                self.assertIn(f"{scope} = %s", sql)
                for dim in _DIMENSIONI_OVERRIDE:
                    if dim != scope:
                        self.assertIn(f"{dim} IS NULL", sql)

    # Scopo: Una colonna fuori tupla e' un errore di programmazione.
    def test_dimensione_sconosciuta_esplode(self):
        with self.assertRaises(ValueError):
            _altre_dimensioni_nulle("tx_id")
