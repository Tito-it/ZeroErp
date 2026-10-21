# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Strumento AI per la ricerca billing_account (clienti in italiano).
#        Wrappa BillingAccountService.search_lookup, che e' l'endpoint
#        ricco di ricerca cross-dominio (codice, ragione sociale, id fiscale, PDP).
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from typing import Any

from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.ai_assistant.tools.base import AITool, EndpointGemello
from apps.anagrafiche.api.views_billing_account import BillingAccountLookupView


class CercaBillingAccountTool(AITool):
    """Tool per cercare billing_account (clienti) in anagrafica.

    In italiano l'utente chiama "cliente" cio' che nel modello tecnico e'
    un billing_account. Il tool accetta entrambe le terminologie: il
    prompt di sistema istruisce l'LLM a mappare "cliente" su questo tool.
    """

    def __init__(self) -> None:
        super().__init__(
            name="cerca_billing_account",
            description=(
                "Cerca un cliente (billing account) per codice, ragione sociale, "
                "codice fiscale, partita IVA o PDP (punto di prelievo). "
                "In ZeroERP 'cliente' e 'billing account' sono sinonimi: usare "
                "questo tool quando l'utente chiede 'cerca cliente', 'trova "
                "billing account', 'cliente ACEA', ecc. Restituisce codice BA, "
                "ragione sociale, utility collegata, PDP e validita'. "
                "Il sistema filtra automaticamente lo scope per emittente fiscale "
                "dell'operatore autenticato."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "q": {
                        "type": "string",
                        "description": "Testo di ricerca libero (min 2 caratteri). Cerca su codice BA, ragione sociale, codice fiscale / partita IVA, PDP.",
                    },
                    "utility_id": {
                        "type": "integer",
                        "description": "Id utility (gas/energia/idrico) per filtrare solo i BA di una specifica utility. Opzionale.",
                    },
                    "solo_validi": {
                        "type": "boolean",
                        "description": "Se true (default), restituisce solo BA validi alla data odierna. Mettere false per includere BA scaduti.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Numero risultati (default 10, max 50).",
                    },
                },
                "required": ["q"],
            },
            endpoint=EndpointGemello(BillingAccountLookupView, "GET"),
            # Nessun route_template per ora: la lista BA non ha una rotta
            # frontend dedicata "filtra per search". In futuro, se verra'
            # aggiunta, basta popolare route_template qui.
        )

    # Scopo: Esegue la ricerca BA tramite il service dedicato, che risolve
    #        lo scope emittente dell'operatore autenticato.
    def execute(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        from apps.anagrafiche.services.billing_account_service import BillingAccountService

        solo_validi_raw = params.get("solo_validi")
        solo_validi = True if solo_validi_raw is None else bool(solo_validi_raw)
        valid_at: date | None = oggi_aziendale() if solo_validi else None

        svc = BillingAccountService()
        # Lo scope emittente lo risolve il service dall'utente, come per il
        # gemello `BillingAccountLookupView`: fino al 2026-09-24 il tool lo
        # risolveva da se' con le PK al posto dei soggetto-ruolo.
        response = svc.search_lookup(
            user=request.user,
            q=params.get("q", ""),
            utility_id=params.get("utility_id"),
            solo_validi=solo_validi,
            valid_at=valid_at,
            limit=self.safe_limit(params),
        )

        items = response.get("results", []) if isinstance(response, dict) else []
        total = response.get("total_count", len(items)) if isinstance(response, dict) else len(items)

        _FIELD_MAP = {
            "id": "id",
            "codice": "codice",
            "ragione_sociale": "ragione_sociale_completa",
            "id_fiscale": "id_fiscale",
            "utility_codice": "utility_codice",
            "utility_descrizione": "utility_descrizione",
            "pdp": "pdp",
            "valido_dal": "valido_dal",
            "valido_al": "valido_al",
        }
        simplified = self.simplify_results(items, _FIELD_MAP)
        return {"count": total, "results": simplified}


# Scopo: Funzione di registrazione tool billing_account.
#        Chiamata da tool_registry.populate_registry() all'avvio dell'app.
def get_billing_account_tools() -> list[AITool]:
    return [
        CercaBillingAccountTool(),
    ]
