# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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


# Scopo: La regola dell'API sul corpo di un salvataggio di preferenza: un
#        oggetto con almeno una chiave. Ritorna la configurazione da salvare.
# ⭐ Ogni chiave e' facoltativa: quella assente vale «come lo standard»
#    (`fn_resolve_lista_config` / `fn_resolve_dashboard_config` risolvono per
#    chiave, `origine`). Ma una preferenza SENZA chiavi non e' una preferenza:
#    si toglie con il DELETE, non si salva vuota (decisione di Tid, 2026-11-01).
# ⛔ La FORMA (chiavi ammesse, voci, tipi, codici della lista o della
#    dashboard, tetto di `dimensione_max`) non si giudica qui: la giudica il
#    guard del DB, `ui.trgfn_preferenza_guard_forma`, che risponde
#    `E_UI_CONFIGURAZIONE_FORMA` (400) con la chiave e il motivo. La copia del
#    BE e' ritirata (BE8 e BE11 di brief-db-revisione-ui, giro 2): due copie
#    della stessa regola rispondono prima o poi in due modi diversi.
def richiedi_preferenza_non_vuota(
    config: Any, *, message: str,
) -> dict[str, Any]:
    ErrorManager.require(
        isinstance(config, dict),
        code=E_UI_PREFERENZA_VALIDAZIONE,
        message=message,
        detail="Il payload deve essere un oggetto JSON.",
    )
    assert isinstance(config, dict)
    ErrorManager.require(
        bool(config),
        code=E_UI_PREFERENZA_VALIDAZIONE,
        message=message,
        detail="La preferenza non ha nessuna chiave: per tornare allo standard si elimina.",
    )
    return config


# Scopo: L'id del preset di base di OGGI, letto dalla risoluzione (BE5 di
#        brief-db-revisione-ui, giro 1a). `preset_base` e' la chiave che
#        `fn_resolve_lista_config` / `fn_resolve_dashboard_config` espongono:
#        `{id, ambito, contenuto_aggiornato_il}` oppure `null`. La scelta la fa
#        il DB in una sede sola (`ui.fn_preset_di_base`): qui nessuna cascata.
# ⭐ Si salva solo l'id. Lo snapshot (`preset_base_contenuto_aggiornato_il`)
#    lo scrive il trigger `ui.trgfn_preferenza_preset_base_snapshot` a ogni
#    scrittura che nomina `preset_base_id` (BE6): salvare e' riallineare.
def preset_base_id_di_oggi(risoluzione: dict[str, Any]) -> int | None:
    preset_base = risoluzione.get("preset_base")
    if not preset_base:
        return None
    return int(preset_base["id"])
