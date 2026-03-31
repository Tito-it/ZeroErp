# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Strumenti AI per il dominio amministrazione software.
#        Wrappano i service esistenti (operatori) per renderli
#        disponibili all'LLM via function calling.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.ai_assistant.tools.base import AITool


class CercaOperatoriTool(AITool):
    """Tool per cercare operatori nel sistema."""

    def __init__(self) -> None:
        super().__init__(
            name="cerca_operatori",
            description=(
                "Cerca operatori (utenti del sistema) per nome, cognome, username, "
                "reparto o ruolo. Usare per trovare chi sta seguendo una pratica "
                "o per verificare i permessi di un operatore."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "search": {
                        "type": "string",
                        "description": "Ricerca libera su username, email, cognome, nome o ragione sociale",
                    },
                    "ruolo_sistema": {
                        "type": "string",
                        "enum": ["ADMIN", "USER"],
                        "description": "Filtro per ruolo sistema",
                    },
                    "solo_attivi": {
                        "type": "boolean",
                        "description": "Se true, restituisce solo operatori attivi (default true)",
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Numero risultati (default 10, max 50)",
                    },
                },
                "required": [],
            },
            required_area="amm_software",
            required_level="LETTURA",
        )

    _FIELD_MAP = {
        "id": "auth_user_id",
        "username": "username",
        "email": "email",
        "ruolo": "ruolo_sistema",
        "reparto": "unita_organizzativa_nome",
        "attivo": "is_active",
    }

    # Scopo: Esegue la ricerca operatori chiamando il service esistente.
    def execute(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        from apps.amm_software.services.amm_software_service import AmmSoftwareService

        svc = AmmSoftwareService()
        solo_attivi = params.get("solo_attivi", True)

        items, total = svc.list_operatori(
            search=params.get("search"),
            ruolo_sistema=params.get("ruolo_sistema"),
            is_active=True if solo_attivi else None,
            limit=self.safe_page_size(params),
            offset=0,
        )

        simplified = self.simplify_results(items, self._FIELD_MAP)
        # Arricchisci con nome_completo (campo calcolato)
        for i, item in enumerate(items):
            simplified[i]["nome_completo"] = (
                item.get("ragione_sociale_completa")
                or f"{item.get('first_name', '')} {item.get('last_name', '')}".strip()
                or item.get("username", "")
            )

        return {"count": total, "results": simplified}


# Scopo: Funzione di registrazione tool config/amm.
def get_config_tools() -> list[AITool]:
    return [
        CercaOperatoriTool(),
    ]
