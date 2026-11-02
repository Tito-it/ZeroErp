# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del BB `richiedi_codice_a_vocabolario`: un filtro assente passa,
#        un valore che la tabella conosce passa, uno che non conosce e' il 400
#        del chiamante col campo. Cursore mockato (la giuntura con le tabelle
#        vere la prova `test_vocabolari_dei_filtri_db`).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_assente_passa_senza_query
2) test_valore_noto_passa
3) test_valore_ignoto_e_400_col_parametro
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.db._helpers import richiedi_codice_a_vocabolario
from apps.core.services.service_errors import ServiceError


class TestRichiediCodiceAVocabolario(TestCase):

    def _con_riga(self, riga):
        connection = MagicMock()
        connection.cursor.return_value.__enter__.return_value.fetchone.return_value = riga
        return patch("apps.core.db._helpers.connection", connection), connection

    def test_assente_passa_senza_query(self):
        ctx, connection = self._con_riga(None)
        with ctx:
            self.assertIsNone(richiedi_codice_a_vocabolario(
                "config.x", "codice", None, codice_errore="E_X", parametro="stato",
            ))
        connection.cursor.assert_not_called()

    def test_valore_noto_passa(self):
        ctx, _ = self._con_riga((1,))
        with ctx:
            self.assertEqual(richiedi_codice_a_vocabolario(
                "config.x", "codice", "A", codice_errore="E_X", parametro="stato",
            ), "A")

    def test_valore_ignoto_e_400_col_parametro(self):
        ctx, _ = self._con_riga(None)
        with ctx, self.assertRaises(ServiceError) as err:
            richiedi_codice_a_vocabolario(
                "config.x", "codice", "PIPPO", codice_errore="E_VENDITE_VALIDATION", parametro="stato",
            )
        self.assertEqual(err.exception.code, "E_VENDITE_VALIDATION")
        # Il nome del parametro nel context diagnostico, e NON `field`: un
        # filtro di query non e' un input del form (api.md, Tid 2026-10-20).
        self.assertEqual(err.exception.context["parametro"], "stato")
        self.assertNotIn("field", err.exception.context)
