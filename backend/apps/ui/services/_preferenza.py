# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Regole comuni alle due preferenze utente del modulo `ui` —
#        `ListaPreferenzaService` e `DashboardPreferenzaService` —, e i loro
#        codici d'errore. Regola del 2 (ok Tid 2026-11-02): la preferenza
#        senza chiavi era rifiutata con lo stesso controllo in tutti e due.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.core.services.error_manager import ErrorManager

E_UI_PREFERENZA_VALIDAZIONE = "E_UI_PREFERENZA_VALIDAZIONE"
E_UI_PREFERENZA_NON_TROVATA = "E_UI_PREFERENZA_NON_TROVATA"


# Scopo: Rifiuta una preferenza senza chiavi e ritorna la configurazione.
# ⭐ Ogni chiave e' facoltativa: quella assente vale «come lo standard»
#    (`fn_resolve_lista_config` / `fn_resolve_dashboard_config` risolvono per
#    chiave, `origine`). Ma una preferenza SENZA chiavi non e' una preferenza:
#    si toglie con il DELETE, non si salva vuota (decisione di Tid, 2026-11-01).
def richiedi_preferenza_non_vuota(
    config: dict[str, Any], *, message: str,
) -> dict[str, Any]:
    ErrorManager.require(
        bool(config),
        code=E_UI_PREFERENZA_VALIDAZIONE,
        message=message,
        detail="La preferenza non ha nessuna chiave: per tornare allo standard si elimina.",
    )
    return config
