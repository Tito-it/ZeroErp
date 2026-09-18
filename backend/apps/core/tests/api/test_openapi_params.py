# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio di `apps.core.api.openapi_params` — la frase di `order_by`
#        nello schema OpenAPI si LEGGE dalla whitelist del repository, quindi
#        non puo' elencare colonne che non ci sono ne' perderne una.
# Note: Nessun DB, nessuna view: e' una funzione pura. Il test che conta e'
#       il secondo — le view di pagamenti e magazzino passano le mappe vere,
#       e questo pinna che ogni chiave della mappa compaia nella frase.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_frase_elenca_le_chiavi_della_mappa_nell_ordine — la whitelist entra intera, in ordine
2) test_le_view_leggono_le_mappe_vere                  — pagamenti e magazzino: ogni chiave ordinabile sta nella descrizione
3) test_senza_nota_la_frase_finisce_col_punto          — `nota` opzionale, niente spazio pendente
"""

from django.test import SimpleTestCase

from apps.core.api.openapi_params import descrizione_order_by


class DescrizioneOrderByTests(SimpleTestCase):
    # Scopo: la frase porta TUTTE le chiavi, nell'ordine della mappa.
    def test_frase_elenca_le_chiavi_della_mappa_nell_ordine(self) -> None:
        frase = descrizione_order_by(
            {"data": "t.data", "codice": "t.codice"}, "Senza: data.",
        )
        self.assertEqual(
            frase, "Whitelist (nome FISICO della colonna): data | codice. Senza: data.",
        )

    # Scopo: le due aree che hanno adottato il BB passano le mappe del
    #        repository: se una colonna ordinabile nasce, la frase la dice da se'.
    def test_le_view_leggono_le_mappe_vere(self) -> None:
        from apps.magazzino.db.magazzino_repository import MOVIMENTI_SORT_COLUMNS
        from apps.pagamenti.db.pagamenti_repository import (
            DISTINTE_SORT_COLUMNS,
            RATE_SORT_COLUMNS,
        )

        for mappa in (DISTINTE_SORT_COLUMNS, RATE_SORT_COLUMNS, MOVIMENTI_SORT_COLUMNS):
            frase = descrizione_order_by(mappa, "nota")
            for chiave in mappa:
                self.assertIn(chiave, frase)

    # Scopo: senza nota la frase e' chiusa dal punto, senza spazio in coda.
    def test_senza_nota_la_frase_finisce_col_punto(self) -> None:
        self.assertEqual(
            descrizione_order_by(["a"]), "Whitelist (nome FISICO della colonna): a.",
        )
