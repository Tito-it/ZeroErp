# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Strumenti AI per il dominio catalogo.
#        Espone la ricerca articoli (via fn_lookup_articoli del service
#        catalogo_service) all'LLM tramite function calling.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.ai_assistant.tools.base import AITool


class CercaArticoliTool(AITool):
    """Tool per cercare articoli a catalogo (merceologia / prodotti / servizi)."""

    def __init__(self) -> None:
        super().__init__(
            name="cerca_articoli",
            description=(
                "Cerca articoli nel catalogo per codice o descrizione. "
                "Restituisce codice, descrizione, unita' di misura base e flag "
                "(attivo, composito). Usare quando l'utente chiede di trovare "
                "un prodotto, un servizio o una voce merceologica "
                "(es. 'cerca articolo energia', 'trova prodotto ACQUA')."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "search": {
                        "type": "string",
                        "description": "Ricerca libera su codice e descrizione articolo (min 2 caratteri).",
                    },
                    "solo_attivi": {
                        "type": "boolean",
                        "description": "Se true (default), restituisce solo articoli attivi.",
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Numero risultati (default 10, max 50).",
                    },
                },
                "required": [],
            },
            required_area="catalogo",
            required_level="LETTURA",
            # Naviga alla lista articoli con filtro search pre-impostato
            route_template={
                "name": "catalogo-articoli",
                "query": {"search": "{codice}"},
            },
        )

    # Scopo: Esegue la ricerca articoli chiamando il service esistente.
    def execute(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        from apps.catalogo.services import catalogo_service

        solo_attivi = params.get("solo_attivi")
        attivo: bool | None = True if solo_attivi is None else bool(solo_attivi)

        response = catalogo_service.fn_lookup_articoli(
            search=params.get("search"),
            attivo=attivo,
            limit=self.safe_page_size(params),
        )

        # catalogo_service._build_results_response -> {"count": N, "results": [...]}
        items = response.get("results", []) if isinstance(response, dict) else []
        total = response.get("count", len(items)) if isinstance(response, dict) else len(items)

        _FIELD_MAP = {
            "id": "id",
            "codice": "codice",
            "descrizione": "descrizione",
            "uom_codice": "uom_codice",
            "uom_descrizione": "uom_descrizione",
            "attivo": "attivo",
            "is_composito": "is_composito",
        }
        simplified = self.simplify_results(items, _FIELD_MAP)
        return {"count": total, "results": simplified}


# Scopo: Funzione di registrazione tool catalogo.
#        Chiamata da tool_registry.populate_registry() all'avvio dell'app.
def get_catalogo_tools() -> list[AITool]:
    return [
        CercaArticoliTool(),
    ]
