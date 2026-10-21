# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Strumenti AI per il dominio anagrafiche.
#        Wrappano i service esistenti di anagrafiche (soggetti)
#        per renderli disponibili all'LLM via function calling.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.ai_assistant.tools.base import AITool, EndpointGemello
from apps.anagrafiche.api.views_soggetti import SoggettiDetailView, SoggettiView
from apps.core.db._helpers import RICERCA_MIN_CARATTERI


class CercaSoggettiTool(AITool):
    """Tool per cercare soggetti in anagrafica (PF/PG/ENTE)."""

    def __init__(self) -> None:
        super().__init__(
            name="cerca_soggetti",
            description=(
                "Cerca soggetti in anagrafica per nominativo, codice fiscale, "
                "partita IVA o tipo soggetto. Restituisce persone fisiche, "
                "giuridiche o enti. Usare per trovare clienti, fornitori o "
                "qualsiasi soggetto registrato nel sistema."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "search": {
                        "type": "string",
                        # ⚠️ Le colonne le decide il catalogo della lista
                        #    `anagrafiche.soggetti` (dal 2026-09-24 sul BB): qui
                        #    si nominano solo per orientare il modello.
                        "description": f"Ricerca libera su ragione sociale (cognome e nome per le persone fisiche) o identificativo fiscale unico, che porta codice fiscale e partita IVA (min {RICERCA_MIN_CARATTERI} caratteri).",
                    },
                    "natura": {
                        "type": "string",
                        "enum": ["PF", "PG", "ENTE"],
                        "description": "Tipo soggetto: PF (persona fisica), PG (persona giuridica), ENTE",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Numero risultati (default 10, max 50)",
                    },
                },
                "required": [],
            },
            endpoint=EndpointGemello(SoggettiView, "GET"),
            # Naviga alla lista soggetti con filtro search pre-impostato
            route_template={
                "name": "anagrafiche-soggetti",
                "query": {"search": "{ragione_sociale_completa}"},
            },
        )

    # Scopo: Esegue la ricerca soggetti chiamando il service esistente.
    def execute(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        svc = SoggettiService()

        items, total = svc.list_soggetti(
            search=self.termine_ricerca(params),
            limit=self.safe_limit(params),
            offset=0,
            order_by="ragione_sociale_completa",
            order_dir="asc",
        )

        _FIELD_MAP = {
            "id": "id",
            "ragione_sociale_completa": "ragione_sociale_completa",
            "codice_fiscale": "codice_fiscale",
            "partita_iva": "partita_iva",
            "natura": "natura_soggetto",
        }
        simplified = self.simplify_results(items, _FIELD_MAP)

        # Arricchisci con ruoli (campo JSON che richiede parsing)
        for i, item in enumerate(items):
            simplified[i]["ruoli"] = _parse_ruoli(item.get("ruoli"))

        return {"count": total, "results": simplified}


class DettaglioSoggettoTool(AITool):
    """Tool per recuperare i dati completi di un soggetto."""

    def __init__(self) -> None:
        super().__init__(
            name="dettaglio_soggetto",
            description=(
                "Recupera i dati completi di un soggetto per ID. Usare dopo "
                "cerca_soggetti per ottenere dettagli come contatti, indirizzi, "
                "ruoli e dati societari."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "soggetto_id": {
                        "type": "string",
                        "description": "UUID del soggetto da recuperare",
                    },
                },
                "required": ["soggetto_id"],
            },
            endpoint=EndpointGemello(SoggettiDetailView, "GET"),
        )

    # Scopo: Recupera il dettaglio completo di un soggetto.
    def execute(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        svc = SoggettiService()
        soggetto = svc.get_soggetto(params["soggetto_id"])

        return {
            "id": soggetto.get("id"),
            "ragione_sociale_completa": soggetto.get("ragione_sociale_completa"),
            "codice_fiscale": soggetto.get("codice_fiscale"),
            "partita_iva": soggetto.get("partita_iva"),
            "cognome": soggetto.get("cognome"),
            "nome": soggetto.get("nome"),
            "sesso": soggetto.get("sesso"),
            "contatti": soggetto.get("contatti", []),
            "indirizzi": soggetto.get("indirizzi", []),
            "ruoli": soggetto.get("ruoli", []),
        }


# Scopo: Parsa il campo ruoli — puo' essere stringa JSON o lista Python.
def _parse_ruoli(ruoli_raw: Any) -> list[str]:
    if not ruoli_raw:
        return []
    if isinstance(ruoli_raw, str):
        try:
            import json as _json
            ruoli_raw = _json.loads(ruoli_raw)
        except (ValueError, TypeError):
            return []
    return [r.get("descrizione", "") for r in ruoli_raw if isinstance(r, dict) and r.get("descrizione")]


# Scopo: Funzione di registrazione tool anagrafiche.
def get_anagrafiche_tools() -> list[AITool]:
    return [
        CercaSoggettiTool(),
        DettaglioSoggettoTool(),
    ]
