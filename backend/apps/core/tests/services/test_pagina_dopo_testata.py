# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: il contratto del BB `pagina_dopo_testata`: la testata si legge
#        PRIMA, e se solleva la pagina non si legge.
# Note: i sette consumatori (le righe dei documenti di vendita e la distinta)
#       si provano uno per uno nei test dei loro domini: un BB unifica la
#       lettura, non il trasporto, e ogni punto che lo chiama vuole il suo.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_testata_prima_poi_la_pagina
2) test_testata_che_solleva_ferma_la_pagina
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from apps.core.services.testata_guard import pagina_dopo_testata


class PaginaDopoTestataTests(unittest.TestCase):

    def test_testata_prima_poi_la_pagina(self) -> None:
        ordine: list[str] = []
        leggi_pagina = MagicMock(side_effect=lambda *a, **k: (ordine.append("pagina"), ([{"id": 1}], 1))[1])
        risultato = pagina_dopo_testata(
            lambda: ordine.append("testata"), leggi_pagina, 7, search="x", limit=10,
        )
        self.assertEqual(risultato, ([{"id": 1}], 1))
        self.assertEqual(ordine, ["testata", "pagina"])
        leggi_pagina.assert_called_once_with(7, search="x", limit=10)

    # ⛔ Il caso che il BB esiste per tenere: padre fuori perimetro = errore,
    #    mai una lista vuota letta dietro la RLS.
    def test_testata_che_solleva_ferma_la_pagina(self) -> None:
        leggi_pagina = MagicMock()

        def testata() -> None:
            raise LookupError("fuori perimetro")

        with self.assertRaises(LookupError):
            pagina_dopo_testata(testata, leggi_pagina, 7, limit=10)
        leggi_pagina.assert_not_called()
