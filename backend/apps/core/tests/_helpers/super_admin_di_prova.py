# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il SUPER_ADMIN per la catena dei permessi in un test senza DB: il
#        patch di `PermissionResolver.is_super_admin` a `True`, da usare come
#        decoratore (di metodo o di classe) o come context manager. Va con
#        l'utente di `operatore_di_prova`.
# Note: ⭐ Regola del 2, ok Tid 2026-11-24 (D-J di
#       brief-db-porte-aperte-dalla-sola-guc §4.7). Il superuser Django non
#       concede piu' niente, e fino a quel giorno 77 file di test passavano la
#       catena con un `Mock()` nudo, il cui `is_superuser` e' vero: super
#       admin senza dirlo. Ora il test lo DICHIARA, nel solo modo che la catena
#       conosce.
#       ⚠️ Patch con `new`, non con `return_value`: il decoratore non aggiunge
#       un argomento al test, e la firma dei metodi resta quella di prima.
#       ⚠️ Una funzione che rende un patch NUOVO a ogni uso: un `_patch`
#       condiviso fra due test annidati si fermerebbe al primo `stop`.
#       ⚠️ Da decoratore di classe vale per i metodi `test*`, non per
#       `setUp`: e' il default di `unittest.mock`.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from unittest.mock import _patch, patch

from apps.core.services.permissions_resolver import PermissionResolver


def _sempre_super_admin(*_args: Any, **_kwargs: Any) -> bool:
    return True


# Scopo: il patch che fa rispondere SUPER_ADMIN a ogni utente del test.
def super_admin_di_prova() -> _patch[Any]:
    return patch.object(PermissionResolver, "is_super_admin", new=_sempre_super_admin)
