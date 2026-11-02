# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: L'operatore VERO per la catena dei permessi in un test senza DB:
#        autenticato e non superuser. Un `Mock()` nudo ha `is_superuser`
#        vero (un attributo Mock e' veritiero), e la catena non verrebbe mai
#        attraversata: il test passerebbe come super admin senza dirlo.
# Note: ⭐ Estratto il 2026-10-27 (regola del 2, ok Tid) dalle copie scritte
#       nei test API e service (`_operatore`, `_utente`, e i blocchi inline
#       `user.is_superuser = False`), con l'id come unica differenza.
#       ⚠️ E' un `MagicMock`: gli attributi non dichiarati restano mock, come
#       nelle copie; chi ne vuole uno (`username`, ...) lo assegna dopo.
# ------------------------------------------------------------

from __future__ import annotations

from unittest.mock import MagicMock


# Scopo: l'operatore autenticato con `user_id` (per i test che lo confrontano con
#        uno scope o una chiamata); `is_superuser=True` per il caso opposto,
#        dichiarato dal test.
def operatore_di_prova(*, user_id: int = 1, is_superuser: bool = False) -> MagicMock:
    user = MagicMock()
    user.id = user_id
    user.is_authenticated = True
    user.is_superuser = is_superuser
    return user
