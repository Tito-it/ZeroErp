# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: BE30 di brief-db-revisione-ui (Q51 (c), deciso da Tid il
#        2026-11-22): quando l'ordinamento di partenza (o il clic
#        dell'operatore) nomina la PRIMA colonna del default del repository,
#        l'ORDER BY e' quello di oggi, criteri successivi compresi — non la
#        colonna piu' il solo spareggio tecnico.
# Note: ⭐ Il codice lo fa gia' (2026-11-22): gli ordinamenti di magazzino a
#       piu' criteri chiudono con una coda FISSA, indipendente dalla colonna
#       chiesta. Questo e' il presidio che lo tiene: portarli su
#       `sql_order_clause` «per uniformita'» toglierebbe la coda senza errore,
#       e le righe con lo stesso articolo cambierebbero ordine.
#       Senza DB: `lista_paginata` e il guard del canale sono finti, la
#       clausola si legge da cio' che il repository passa.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) CriteriSuccessiviMagazzinoTests.test_disponibilita
2) CriteriSuccessiviMagazzinoTests.test_disponibilita_articoli
3) CriteriSuccessiviMagazzinoTests.test_piano_inventario
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.magazzino.db.magazzino_repository import MagazzinoRepository
from apps.core.tests._helpers.perimetro_admin_globale_di_prova import perimetro_admin_globale_di_prova

_MOD = "apps.magazzino.db.magazzino_repository"


# ⭐ Legge la SQL della lista, non prova il perimetro: il risolutore risponde
#    «nessuna restrizione» (admin globale). Dal 2026-11-24 `auth_user_id=None`
#    solleva, quindi il test passa un utente e dichiara il perimetro qui.
@perimetro_admin_globale_di_prova()
class CriteriSuccessiviMagazzinoTests(SimpleTestCase):
    # La clausola che il repository passa a `lista_paginata`, per la chiamata data.
    def _clausola(self, chiama: Callable[..., Any], **ordine: Any) -> str:
        with patch(f"{_MOD}.lista_paginata", return_value=([], 0)) as pagina, \
                patch(f"{_MOD}.guard_canale_sistema"):
            chiama(limit=10, offset=0, **ordine)
        return str(pagina.call_args.kwargs["order_clause"])

    # Il default di oggi (nessun `order_by`) e la prima colonna col verso del
    # preset danno la STESSA clausola.
    # ⚠️ L'uguaglianza da sola non basta: una coda tolta sparirebbe da tutti e
    #    due i lati. Per questo si nomina anche la coda attesa.
    def _stessa(
        self, chiama: Callable[..., Any], chiave: str, verso: str, *, coda: str,
    ) -> None:
        default = self._clausola(chiama)
        proposto = self._clausola(chiama, order_by=chiave, order_dir=verso)
        self.assertEqual(proposto, default)
        self.assertIn(coda, proposto)

    def test_disponibilita(self) -> None:
        repo = MagazzinoRepository()
        self._stessa(
            lambda **kw: repo.list_disponibilita(auth_user_id=7, **kw), "articolo_codice", "asc",
            coda="articolo_id ASC, magazzino_id ASC",
        )

    def test_disponibilita_articoli(self) -> None:
        # Qui il default e' colonna piu' spareggio, e lo spareggio E' il criterio
        # successivo: resta quello.
        self._stessa(
            MagazzinoRepository().list_disponibilita_articoli, "articolo_codice", "asc",
            coda="articolo_id ASC",
        )

    def test_piano_inventario(self) -> None:
        repo = MagazzinoRepository()
        self._stessa(
            lambda **kw: repo.list_piano(1, **kw), "articolo_codice", "asc",
            coda="articolo_id, ubicazione_id, lotto_id, asset_id",
        )
