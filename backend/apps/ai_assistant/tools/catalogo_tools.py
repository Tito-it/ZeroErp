# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Strumenti AI per il dominio catalogo.
#        Espone la ricerca articoli (via fn_lookup_articoli del service
#        catalogo_service) all'LLM tramite function calling.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.ai_assistant.tools.base import AITool, EndpointGemello
from apps.catalogo.api.views import ApiArticoliLookup


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
                "(es. 'cerca articolo energia', 'trova prodotto ACQUA'). "
                # ⛔ IL CAMPO VA SPIEGATO QUI, non solo emesso: questa
                #    descrizione e' l'unica cosa che il modello legge per sapere
                #    cosa riceve. Il flag `troncato` era gia' nel payload e non
                #    era nominato da nessuna parte — cioe' emesso e non
                #    consumato, che su un tool AI significa esattamente il
                #    difetto che il flag doveva chiudere: «ho trovato 10
                #    articoli» detto su un catalogo che ne ha centinaia.
                "IMPORTANTE: `troncato: true` significa che i risultati sono i "
                "PRIMI `count` di un insieme piu' grande, non tutti quelli che "
                "esistono. In quel caso non dire mai un totale: di' che sono i "
                "primi N e invita a restringere la ricerca o ad alzare "
                "`limit` (max 50)."
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
                    "limit": {
                        "type": "integer",
                        "description": "Numero risultati (default 10, max 50).",
                    },
                },
                "required": [],
            },
            endpoint=EndpointGemello(ApiArticoliLookup, "GET"),
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
            limit=self.safe_limit(params),
        )

        # `catalogo_service._lookup_response` -> {"count": N, "results": [...], "troncato": bool}
        # 🔴 `troncato` si propaga, e su questo tool conta piu' che altrove
        #    (2026-09-10). `safe_limit` chiede 10 righe di default: senza
        #    quel campo il modello legge `count: 10` e dice a una persona «ho
        #    trovato 10 articoli» — anche quando a catalogo ce ne sono centinaia.
        #    ⇒ Non e' un numero impreciso: e' una frase falsa, detta con
        #    sicurezza. Con `troncato` il modello puo' dire «i primi 10 di piu'».
        items = response.get("results", []) if isinstance(response, dict) else []
        total = response.get("count", len(items)) if isinstance(response, dict) else len(items)
        troncato = bool(response.get("troncato")) if isinstance(response, dict) else False

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
        return {"count": total, "results": simplified, "troncato": troncato}


# Scopo: Funzione di registrazione tool catalogo.
#        Chiamata da tool_registry.populate_registry() all'avvio dell'app.
def get_catalogo_tools() -> list[AITool]:
    return [
        CercaArticoliTool(),
    ]
