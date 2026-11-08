# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il porting di `UiAdminRepository.update_colonna` sul BB
#        `execute_dynamic_update` con `casts` (2026-09-26): prima il SET era
#        scritto a mano, con una mappa di cast per i tre enum della tabella, e
#        scartava in silenzio ogni chiave fuori elenco.
#        - Unit (sempre): la STRINGA e i PARAMETRI prodotti, cursore finto.
#        - E2E (ZEROERP_TEST_DB_E2E=1): il binding dei tre cast sul DB vero —
#          un cast sbagliato (nome del tipo, schema) i mock non lo vedono.
#
# Indice test (0..N):
#   0. test_set_con_i_tre_cast_senza_audit_e_where
#   1. test_chiave_fuori_whitelist_rifiutata
#   2. test_payload_vuoto_nessuna_query
#   3. test_i_tre_cast_legano_sul_db_vero                 (E2E)
# ------------------------------------------------------------

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from django.db import connection, transaction

from apps.core.tests.db_e2e import richiedi_db_provvisto
from apps.ui.db.ui_admin_repository import UiAdminRepository

_BB = "apps.core.db.sql_write_helpers.connection"


class UpdateColonnaSqlTests(unittest.TestCase):
    def _sql(self, data):
        cursore = MagicMock()
        cursore.rowcount = 1
        with patch(_BB) as conn:
            conn.cursor.return_value.__enter__.return_value = cursore
            esito = UiAdminRepository().update_colonna(9, data)
        return esito, cursore

    # L'audit non compare: lo scrive il trigger del DB (BE11, 2026-11-08).
    def test_set_con_i_tre_cast_senza_audit_e_where(self) -> None:
        esito, cursore = self._sql({
            "etichetta": " Et ", "tipo_colonna": "informazione",
            "tipo_dato": "testo", "allineamento": "right",
        })
        self.assertTrue(esito)
        sql, params = cursore.execute.call_args.args
        self.assertEqual(
            sql,
            "UPDATE ui.lista_colonna SET etichetta = %s, "
            "tipo_colonna = %s::ui.tipo_colonna, tipo_dato = %s::ui.tipo_dato, "
            "allineamento = %s::ui.allineamento_colonna WHERE id = %s",
        )
        self.assertEqual(params, ["Et", "informazione", "testo", "right", 9])

    # ⛔ Il SET a mano scartava `lista_id` (e qualunque altra chiave) in
    #    silenzio. Ora e' un errore di programmazione: il service la
    #    rifiuta prima (`E_COLONNA_VALIDATION`), il repository non la scrive.
    def test_chiave_fuori_whitelist_rifiutata(self) -> None:
        with patch(_BB) as conn:
            with self.assertRaises(RuntimeError):
                UiAdminRepository().update_colonna(9, {"lista_id": 3})
            conn.cursor.assert_not_called()

    def test_payload_vuoto_nessuna_query(self) -> None:
        with patch(_BB) as conn:
            self.assertFalse(UiAdminRepository().update_colonna(9, {}))
            conn.cursor.assert_not_called()


class UpdateColonnaCastDbTests(unittest.TestCase):
    """Presidio di BINDING, non di regola: prova che i tre nomi di tipo
    dichiarati in `_COLONNA_CASTS` esistono e legano sul DB vero. Usa una
    colonna qualunque come appoggio e annulla tutto (rollback)."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    def test_i_tre_cast_legano_sul_db_vero(self) -> None:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT id, tipo_colonna::text, tipo_dato::text, allineamento::text "
                "FROM ui.lista_colonna ORDER BY id LIMIT 1"
            )
            riga = cur.fetchone()
        if riga is None:
            self.skipTest("nessuna ui.lista_colonna su cui appoggiare l'UPDATE")
        colonna_id, tipo_colonna, tipo_dato, allineamento = riga
        # L'allineamento si CAMBIA (a un'altra etichetta dell'enum, letta dal
        # catalogo): un UPDATE allo stesso valore non distinguerebbe il cast.
        with connection.cursor() as cur:
            cur.execute(
                "SELECT e.enumlabel FROM pg_enum e "
                "JOIN pg_type t ON t.oid = e.enumtypid "
                "JOIN pg_namespace n ON n.oid = t.typnamespace "
                "WHERE n.nspname = 'ui' AND t.typname = 'allineamento_colonna' "
                "AND e.enumlabel <> %s ORDER BY e.enumsortorder LIMIT 1",
                [allineamento],
            )
            altro = cur.fetchone()
        self.assertIsNotNone(altro, "ui.allineamento_colonna ha una sola etichetta?")
        assert altro is not None
        with transaction.atomic():
            esito = UiAdminRepository().update_colonna(
                colonna_id,
                {
                    "tipo_colonna": tipo_colonna, "tipo_dato": tipo_dato,
                    "allineamento": altro[0],
                },
            )
            with connection.cursor() as cur:
                cur.execute(
                    "SELECT allineamento::text FROM ui.lista_colonna WHERE id = %s",
                    [colonna_id],
                )
                letto = cur.fetchone()
            transaction.set_rollback(True)
        self.assertTrue(esito)
        self.assertEqual(letto, (altro[0],))
