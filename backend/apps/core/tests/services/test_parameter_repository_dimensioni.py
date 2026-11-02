# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La SQL che il repository manda per OGNI livello che il backend scrive
#        e cancella (utente, emittente, categoria cliente): l'upsert passa dal
#        vincolo d'ambito (`ON CONFLICT ON CONSTRAINT uq_overrides_full_scope_v5`)
#        e scrive la sola colonna del suo scope; la delete filtra id e scope.
#        Senza DB. La giuntura col DB vero la prova
#        `tests/db/test_parameter_overrides_db.py`.
# Note: Fino al 2026-10-07 il perimetro «di livello puro» lo teneva il
#        repository (F-5, 2026-09-28): ogni livello filtrava tutte le altre
#        dimensioni NULL. Da allora lo tiene il DB
#        (`chk_parameter_overrides_un_ambito`) e quei filtri sono usciti.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) DimensioniOverrideTests.test_upsert_sul_vincolo_d_ambito
2) DimensioniOverrideTests.test_delete_filtra_id_e_scope
3) DimensioniOverrideTests.test_dimensione_sconosciuta_esplode
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.db.parameter_repository import (
    _DIMENSIONI_OVERRIDE,
    ParameterRepository,
    _colonna_di_scope,
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

    # Scopo: Ogni upsert scrive la sola colonna del suo scope e collide sul
    # vincolo d'ambito: e' il vincolo (NULLS NOT DISTINCT) a trovare la riga
    # esistente, non un match IS NULL scritto qui.
    def test_upsert_sul_vincolo_d_ambito(self):
        for metodo, scope in _UPSERT:
            with self.subTest(metodo=metodo), patch(_CONN) as mock_conn:
                cur = mock_conn.cursor.return_value.__enter__.return_value
                cur.fetchone.return_value = (1,)
                self.assertEqual(getattr(ParameterRepository(), metodo)("P", 5, "v"), 1)
                sql = _sql_mandata(mock_conn)
                self.assertIn(f"(parameter_id, {scope}, overridden_value)", sql)
                self.assertIn("ON CONFLICT ON CONSTRAINT uq_overrides_full_scope_v5 DO UPDATE", sql)
                self.assertIn("attivo = true", sql)
                for dim in _DIMENSIONI_OVERRIDE:
                    if dim != scope:
                        self.assertNotIn(dim, sql)

    # Scopo: Ogni delete cancella per id E scope: l'id di un altro proprietario
    # non basta.
    def test_delete_filtra_id_e_scope(self):
        for metodo, scope in _DELETE:
            with self.subTest(metodo=metodo), patch(_CONN) as mock_conn:
                cur = mock_conn.cursor.return_value.__enter__.return_value
                cur.rowcount = 1
                self.assertTrue(getattr(ParameterRepository(), metodo)(9, 5))
                sql = _sql_mandata(mock_conn)
                self.assertIn("WHERE id = %s", sql)
                self.assertIn(f"AND {scope} = %s", sql)
                self.assertEqual(cur.execute.call_args[0][1], [9, 5])

    # Scopo: Una colonna fuori tupla e' un errore di programmazione.
    def test_dimensione_sconosciuta_esplode(self):
        with self.assertRaises(ValueError):
            _colonna_di_scope("tx_id")
