# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del BB `resolve_config_id_by_codice_interno`: chi ha scelto il
#        codice decide il codice d'errore. Un codice scritto nel codice che non
#        si trova e' un seed mancante (`E_CONFIG_MANCANTE`, 500); un codice del
#        client che non si trova e' un valore sbagliato (il codice di
#        validazione del chiamante, 400, col campo). Cursore mockato.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_trovato_restituisce_l_id
2) test_default_e_il_seed_mancante — nessun codice passato: E_CONFIG_MANCANTE, senza campo
3) test_codice_del_client_e_un_400_col_campo — codice_errore + campo dal chiamante
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.db._helpers import resolve_config_id_by_codice_interno
from apps.core.services.service_errors import ServiceError


class TestResolveConfigId(TestCase):

    def _con_riga(self, riga):
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = riga
        return patch("apps.core.db._helpers.connection", connection)

    def test_trovato_restituisce_l_id(self):
        with self._con_riga((7,)):
            self.assertEqual(
                resolve_config_id_by_codice_interno("config.x", "A", etichetta="X"), 7,
            )

    def test_default_e_il_seed_mancante(self):
        with self._con_riga(None), self.assertRaises(ServiceError) as ctx:
            resolve_config_id_by_codice_interno("config.x", "A", etichetta="X")
        self.assertEqual(ctx.exception.code, "E_CONFIG_MANCANTE")
        self.assertNotIn("field", ctx.exception.context or {})

    # Scopo: ⛔ fino al 2026-10-20 anche un `nuovo_stato` inventato dal client
    #        era il 500 di un seed mancante.
    def test_codice_del_client_e_un_400_col_campo(self):
        with self._con_riga(None), self.assertRaises(ServiceError) as ctx:
            resolve_config_id_by_codice_interno(
                "config.x", "PIPPO", etichetta="X",
                codice_errore="E_PRATICA_VALIDATION", campo="nuovo_stato",
            )
        self.assertEqual(ctx.exception.code, "E_PRATICA_VALIDATION")
        self.assertEqual(ctx.exception.context["field"], "nuovo_stato")
