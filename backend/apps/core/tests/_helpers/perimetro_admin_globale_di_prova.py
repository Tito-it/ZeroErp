# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il perimetro emittente di un ADMIN GLOBALE in un test senza DB: il
#        patch di `fetch_emittenti_scope_ids` che risponde `None` («nessuna
#        restrizione», come la funzione DB per l'admin globale), da decoratore
#        (di metodo o di classe) o da context manager. Serve ai test che
#        leggono la SQL di una lista e non provano il perimetro.
# Note: ⭐ Regola del 2, ok Tid 2026-11-24 (brief-db-porte-aperte-dalla-sola-guc
#       §4.7, «il `None` del perimetro si rifiuta»). Fino a quel giorno questi
#       test passavano `auth_user_id=None` e ricevevano una SQL senza
#       clausola di perimetro. Ora `None` solleva `E_SCOPE_SENZA_UTENTE`, e
#       il test passa un utente: senza questo patch il risolutore andrebbe
#       sul database. Il test DICHIARA cosi' che legge la lista come la vede
#       chi non ha restrizioni, invece di ripetere il percorso del patch.
#       ⚠️ Patch con `new`, non con `return_value`: il decoratore non aggiunge
#       un argomento al test.
#       ⚠️ Una funzione che rende un patch NUOVO a ogni uso: un `_patch`
#       condiviso fra due test annidati si fermerebbe al primo `stop`.
#       ⚠️ Si patcha il nome nel modulo del BB, l'unico da cui passano
#       `add_emittente_scope_condition` e i giri che risolvono il perimetro una
#       volta: un modulo che lo importa con `from ... import` ne ha una copia
#       sua, e va patchata a parte (`gestione_service`). Per questo
#       `pagamenti_repository` lo chiama dal modulo
#       (`emittente_scope_helpers.fetch_emittenti_scope_ids`).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from unittest.mock import _patch, patch

_FETCH = "apps.core.db.emittente_scope_helpers.fetch_emittenti_scope_ids"


def _nessuna_restrizione(*_args: Any, **_kwargs: Any) -> None:
    return None


# Scopo: il patch che fa rispondere al perimetro «nessuna restrizione».
def perimetro_admin_globale_di_prova() -> _patch[Any]:
    return patch(_FETCH, new=_nessuna_restrizione)
