# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Strumenti AI per il dominio amministrazione software.
#        Wrappano i service esistenti (operatori) per renderli
#        disponibili all'LLM via function calling.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.ai_assistant.tools.base import AITool, EndpointGemello
from apps.amm_software.api.views import OperatoriListView
from apps.core.db._helpers import RICERCA_MIN_CARATTERI


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
                        "description": f"Ricerca libera su username, email, cognome, nome o ragione sociale (min {RICERCA_MIN_CARATTERI} caratteri).",
                    },
                    "is_super_admin": {
                        "type": "boolean",
                        "description": "Se true, ritorna solo i super admin; se false, solo i non super admin",
                    },
                    "solo_attivi": {
                        "type": "boolean",
                        "description": "Se true, restituisce solo operatori attivi (default true)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Numero risultati (default 10, max 50)",
                    },
                },
                "required": [],
            },
            endpoint=EndpointGemello(OperatoriListView, "GET"),
        )

    _FIELD_MAP = {
        "id": "auth_user_id",
        "username": "username",
        "email": "email",
        "is_super_admin": "is_super_admin",
        "ruolo_applicativo": "ruolo_applicativo",
        "reparto": "unita_organizzativa_nome",
        "attivo": "is_active",
    }

    # Scopo: Esegue la ricerca operatori chiamando il service esistente.
    def execute(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        from apps.amm_software.services.amm_software_service import AmmSoftwareService

        svc = AmmSoftwareService()
        solo_attivi = params.get("solo_attivi", True)

        items, total = svc.list_operatori(
            search=self.termine_ricerca(params),
            is_super_admin=params.get("is_super_admin"),
            is_active=True if solo_attivi else None,
            limit=self.safe_limit(params),
            offset=0,
        )

        simplified = self.simplify_results(items, self._FIELD_MAP)
        # Arricchisci con nome_completo (campo calcolato)
        # ⚠️ `soggetto_ragione_sociale`, il nome che `list_operatori` proietta
        #    (dal 2026-09-24): fino ad allora qui si leggeva
        #    `ragione_sociale_completa`, una chiave che la lista non ha mai
        #    restituito, e il ramo era sempre vuoto.
        for i, item in enumerate(items):
            simplified[i]["nome_completo"] = (
                item.get("soggetto_ragione_sociale")
                or f"{item.get('first_name', '')} {item.get('last_name', '')}".strip()
                or item.get("username", "")
            )

        return {"count": total, "results": simplified}


# Scopo: Funzione di registrazione tool config/amm.
def get_config_tools() -> list[AITool]:
    return [
        CercaOperatoriTool(),
    ]
