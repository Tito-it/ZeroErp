# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `TipiRuoloTipiIndirizzoRepository.update_matrice` sul BB
#        `execute_dynamic_update` (2026-09-26): `attivo` trascina `valido_al`
#        con una clausola `extra_set` LITERAL scelta dal valore Python — prima
#        era un `CASE WHEN %s`, che il BB non puo' portare (non conosce i
#        parametri di `extra_set`).
# Note: Mock del BB, CI-compatible.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) UpdateMatriceTests.test_attivo_true_azzera_valido_al
2) UpdateMatriceTests.test_attivo_false_chiude_valido_al_a_oggi
3) UpdateMatriceTests.test_senza_attivo_nessun_extra_set
"""

from unittest import TestCase
from unittest.mock import patch

_BB = "apps.config.db.tipi_ruolo_tipi_indirizzo_repository.execute_dynamic_update"


class UpdateMatriceTests(TestCase):

    def _aggiorna(self, fields):
        from apps.config.db.tipi_ruolo_tipi_indirizzo_repository import (
            TipiRuoloTipiIndirizzoRepository,
        )
        with patch(_BB, return_value=True) as bb:
            self.assertTrue(TipiRuoloTipiIndirizzoRepository().update_matrice(7, fields))
        return bb.call_args

    def test_attivo_true_azzera_valido_al(self):
        chiamata = self._aggiorna({"attivo": True})
        self.assertEqual("valido_al = NULL", chiamata.kwargs["extra_set"])

    def test_attivo_false_chiude_valido_al_a_oggi(self):
        chiamata = self._aggiorna({"attivo": False, "obbligatorio": True})
        self.assertEqual("valido_al = (SELECT script.fn_data_operativa())", chiamata.kwargs["extra_set"])
        self.assertEqual(
            ("config.tipi_ruolo_tipi_indirizzo", 7, {"attivo": False, "obbligatorio": True}),
            chiamata.args,
        )

    def test_senza_attivo_nessun_extra_set(self):
        chiamata = self._aggiorna({"fallback_tipo_indirizzo_id": None})
        self.assertIsNone(chiamata.kwargs["extra_set"])
