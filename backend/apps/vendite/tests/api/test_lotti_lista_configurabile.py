# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidi specifici della lista configurabile `vendite.lotti` che NON
#        sono del contratto generale seed<->whitelist.
#
# Note: l'allineamento fra `ui.lista_colonna` e la whitelist di ordinamento
#       (chiavata sul `campo_sorgente`, colonna azione mai ordinabile, preset
#       default) e' presidiato in modo TRASVERSALE da
#       `apps/core/tests/test_liste_configurabili_seed.py`, che copre tutte le
#       liste convertite: qui resta solo cio' che riguarda i lotti soltanto.
# ------------------------------------------------------------
"""Indice test:

1. test_export_non_passa_dal_cap_della_lista
   L'export chiede piu' righe del tetto di pagina della lista: se passasse da
   `fn_list_lotti` (page_size <= MAX_LIMIT) non potrebbe nemmeno rilevare
   il superamento del limite, e consegnerebbe un file troncato in silenzio.

2. test_lista_ed_export_condividono_la_stessa_whitelist
   Il contratto dell'export e' «stessi filtri e stesso ordinamento della
   lista»: se le due viste validassero `order_by` contro whitelist diverse, un
   ordinamento valido a video darebbe 400 in export (o viceversa).
"""

import unittest


class LottiExportTests(unittest.TestCase):
    # Scopo: l'export non puo' passare dalla porta della lista.
    def test_export_non_passa_dal_cap_della_lista(self) -> None:
        from apps.core.api.constants import MAX_LIMIT
        from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS

        self.assertGreater(
            EXPORT_MAX_ROWS,
            MAX_LIMIT,
            "se il tetto export scendesse al cap di lista, l'endpoint dedicato "
            "non servirebbe piu': andrebbe rimosso invece di restare a doppione.",
        )

    # Scopo: una sola whitelist per lista ed export.
    def test_lista_ed_export_condividono_la_stessa_whitelist(self) -> None:
        from apps.vendite.api.views import _ORDER_BY_LOTTI
        from apps.vendite.db.vendite_repository import VenditeRepository

        self.assertEqual(
            _ORDER_BY_LOTTI,
            frozenset(VenditeRepository.LOTTI_SORT_COLUMNS),
            "la whitelist delle view deve essere DERIVATA dalla mappa del "
            "repository, non ricopiata: due elenchi divergono al primo che "
            "qualcuno tocca.",
        )
