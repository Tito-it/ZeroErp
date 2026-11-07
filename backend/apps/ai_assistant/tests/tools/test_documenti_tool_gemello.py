# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il tool `cerca_documenti_generati` serve solo la sorgente del suo
#        endpoint gemello.
#
# ⭐ PERCHE' ESISTE (2026-09-25). Il permesso del tool e' quello del gemello,
#    la lista documenti del PREVENTIVO (area `vendite`). Le sorgenti che il
#    tool accetta stanno invece in `_SORGENTE_VERIFICHE`: aggiungerne una
#    seconda (un contratto, un ordine) la metterebbe sotto il permesso del
#    preventivo — nessun errore, e un operatore senza l'area della sorgente
#    nuova ne leggerebbe i documenti dall'AI. Il commento sul tool lo dice; qui
#    si fa rispettare.
#
# Indice test:
#   1) le sorgenti del tool sono esattamente quella del gemello
# ------------------------------------------------------------

from __future__ import annotations

import unittest

from apps.ai_assistant.tools.documenti_tools import _SORGENTE_VERIFICHE
# Il codice della sorgente del gemello: la view `preventivi_documenti_views` lo
# prende da qui (dal 2026-10-11 non ne tiene piu' una copia locale).
from apps.config.sorgenti import SORGENTE_PREVENTIVO


class TestDocumentiToolGemello(unittest.TestCase):

    # 1) Una sorgente nuova vuol dire un tool nuovo col suo gemello, non una
    #    voce in piu' nella mappa.
    def test_le_sorgenti_sono_quella_del_gemello(self) -> None:
        self.assertEqual(
            set(_SORGENTE_VERIFICHE), {SORGENTE_PREVENTIVO},
            "cerca_documenti_generati ha il permesso della lista documenti del "
            "preventivo: una sorgente diversa vuole il suo tool e il suo gemello",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
