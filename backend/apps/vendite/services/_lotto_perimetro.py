# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il CANCELLO di perimetro di un lotto, in un posto solo: il lotto
#        letto NELLO SCOPE dell'operatore, oppure il 404 unificato
#        `E_LOTTO_NON_TROVATO` — inesistente e fuori scope danno la stessa
#        risposta, per non confermare l'esistenza del lotto di un altro
#        emittente (api.md §«Scope emittente»).
# ⛔ Ogni lettura di un SATELLITE del lotto (fatture, gruppi, segnalazioni,
#    task-run, giornale, e i loro export) passa di qui PRIMA della sua query.
#    Senza, un lotto fuori perimetro risponde `200` con zero righe o zero
#    conteggi, che si legge come «lotto vuoto» e non come «non lo puoi vedere»
#    (fino al 2026-10-20 sette rotte su nove facevano cosi').
# ⭐ Regola del 2: prima esisteva come `_get_lotto_visibile` in
#    `pipeline_service` e in due copie scritte a mano in `vendite_service`
#    (dettaglio e giornale del lotto), ritirate nello stesso giro.
# ------------------------------------------------------------
from __future__ import annotations

from typing import Any

from apps.core.services.error_manager import ErrorManager
from apps.vendite.types import LottoListRow


# Scopo: Il lotto visibile all'operatore, o il 404 `E_LOTTO_NON_TROVATO`.
#        `repository`: quello che il chiamante ha gia' in mano (una lettura
#        sola, e il repository che i suoi test sostituiscono); assente, se ne
#        crea uno.
# ⚠️ Import LOCALE del repository: la catena `vendite_repository` non va
#    caricata al boot dei service che importano questo modulo.
def lotto_visibile(
    *,
    lotto_id: int,
    auth_user_id: int | None,
    function_name: str = "vendite._lotto_perimetro.lotto_visibile",
    repository: Any = None,
) -> LottoListRow:
    if repository is None:
        from apps.vendite.db.vendite_repository import VenditeRepository
        repository = VenditeRepository()

    lotto = repository.get_lotto(lotto_id=lotto_id, auth_user_id=auth_user_id)
    ErrorManager.require(
        lotto is not None,
        code="E_LOTTO_NON_TROVATO",
        message="Lotto non trovato.",
        detail=f"Nessun lotto accessibile con id={lotto_id}",
        context={"lotto_id": lotto_id},
        function_name=function_name,
    )
    assert lotto is not None
    return lotto
