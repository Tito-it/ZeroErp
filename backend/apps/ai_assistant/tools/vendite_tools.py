# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Strumenti AI per il dominio vendite.
#        Espone la ricerca contratti e il dettaglio contratto
#        (via ContrattiService) all'LLM tramite function calling.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.ai_assistant.tools.base import AITool


class CercaContrattiTool(AITool):
    """Tool per cercare contratti commerciali cliente-listino.

    Wrappa ContrattiService.list_contratti() — stessi filtri dell'endpoint
    GET /api/v1/vendite/contratti/. L'LLM puo' filtrare per stato, utility,
    ambito, billing_account, intervallo validita' e mese di scadenza.
    """

    def __init__(self) -> None:
        super().__init__(
            name="cerca_contratti",
            description=(
                "Cerca contratti commerciali nel sistema. Un contratto e' il "
                "ponte tra un cliente (billing_account) e un listino, e veicola "
                "le modalita' pricing A/B/C (A: listino + variazione globale, "
                "B: listino + override righe, C: interamente negoziato). "
                "Usare quando l'utente chiede di trovare contratti per stato "
                "(DRAFT/ATTIVO/SOSPESO/CESSATO), utility (gas/energia/idrico), "
                "ambito (COMMODITY/COMMERCIO), cliente, periodo di validita' o "
                "mese di scadenza. Restituisce numero contratto, cliente, "
                "utility, ambito, listino, categoria cliente snapshot, date di "
                "validita' e stato corrente."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "search": {
                        "type": "string",
                        "description": "Ricerca libera su numero contratto o ragione sociale cliente (min 2 caratteri).",
                    },
                    "billing_account_id": {
                        "type": "integer",
                        "description": "ID cliente (billing account) per filtrare i contratti di un cliente specifico. Usare prima cerca_billing_account per ottenere l'ID.",
                    },
                    "stato_doc_contratto_id": {
                        "type": "integer",
                        "description": "ID stato documentale. Usare la lookup se serve: gli stati sono DRAFT, ATTIVO, SOSPESO, CESSATO (vedi contesto stati contratto).",
                    },
                    "utility_id": {
                        "type": "integer",
                        "description": "ID utility (gas/energia/idrico) per filtrare contratti di una specifica utility. Opzionale.",
                    },
                    "ambito": {
                        "type": "string",
                        "enum": ["COMMODITY", "COMMERCIO"],
                        "description": "Ambito commerciale del contratto.",
                    },
                    "listino_id": {
                        "type": "integer",
                        "description": "ID listino di pricing. Utile per capire quali contratti usano un listino specifico.",
                    },
                    "data_da": {
                        "type": "string",
                        "description": "Filtro validita' - data inizio (YYYY-MM-DD). Default backend: 1 gennaio anno-1.",
                    },
                    "data_a": {
                        "type": "string",
                        "description": "Filtro validita' - data fine (YYYY-MM-DD).",
                    },
                    "scadenza_mese": {
                        "type": "string",
                        "description": "Mese di scadenza in formato YYYY-MM (es. 2026-07). Filtra contratti che scadono nel mese indicato.",
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Numero risultati (default 10, max 50).",
                    },
                },
                "required": [],
            },
            required_area="vendite",
            required_level="LETTURA",
            # Naviga alla lista contratti con filtro search pre-impostato sul numero
            route_template={
                "name": "vendite-contratti",
                "query": {"search": "{numero}"},
            },
        )

    _FIELD_MAP = {
        "id": "id",
        "numero": "numero",
        "cliente": "ba_ragione_sociale",
        "cliente_codice": "ba_codice",
        "utility": "utility_codice",
        "ambito": "ambito",
        "listino": "listino_codice",
        "categoria_cliente": "categoria_cliente_snapshot_codice",
        "valido_dal": "valido_dal",
        "valido_al": "valido_al",
        "stato": "stato_codice",
        "stato_descrizione": "stato_descrizione",
    }

    # Scopo: Esegue la ricerca contratti chiamando il service esistente.
    def execute(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        from apps.vendite.services.contratti_service import ContrattiService

        svc = ContrattiService()
        items, total = svc.list_contratti(
            search=params.get("search"),
            billing_account_id=params.get("billing_account_id"),
            stato_doc_contratto_id=params.get("stato_doc_contratto_id"),
            utility_id=params.get("utility_id"),
            ambito=params.get("ambito"),
            listino_id=params.get("listino_id"),
            data_da=params.get("data_da"),
            data_a=params.get("data_a"),
            scadenza_mese=params.get("scadenza_mese"),
            limit=self.safe_page_size(params),
            offset=0,
            order_by="data",
            order_dir="desc",
        )

        return {
            "count": total,
            "results": self.simplify_results(
                items,
                self._FIELD_MAP,
                str_fields={"valido_dal", "valido_al"},
            ),
        }


class DettaglioContrattoTool(AITool):
    """Tool per recuperare i dati completi di un contratto (testata + utility + righe)."""

    def __init__(self) -> None:
        super().__init__(
            name="dettaglio_contratto",
            description=(
                "Recupera i dati completi di un contratto per ID: testata con "
                "cliente/listino/modalita' pricing, utility 1:1 (tipo e classe "
                "utenza), elenco righe con articoli e prezzi. Usare dopo "
                "cerca_contratti per ottenere i dettagli di un contratto specifico."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "contratto_id": {
                        "type": "integer",
                        "description": "ID numerico del contratto.",
                    },
                },
                "required": ["contratto_id"],
            },
            required_area="vendite",
            required_level="LETTURA",
        )

    # Scopo: Recupera il dettaglio di un contratto dal service.
    def execute(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        from apps.core.services.service_errors import ServiceError
        from apps.vendite.services.contratti_service import ContrattiService

        try:
            contratto = ContrattiService().get_contratto(params["contratto_id"])
        except ServiceError as exc:
            return {"error": exc.message or "Contratto non trovato."}

        # Righe: riduciamo ai campi rilevanti per l'LLM.
        righe_input = contratto.get("righe") or []
        righe_out = [
            {
                "articolo_codice": r.get("articolo_codice"),
                "articolo_descrizione": r.get("articolo_descrizione"),
                "uom": r.get("uom_codice"),
                "tipo_erogazione": r.get("tipo_erogazione"),
                "prezzo_unitario": str(r.get("prezzo_unitario") or ""),
                "quantita_fissa": str(r.get("quantita_fissa") or ""),
                "attivo": r.get("attivo"),
            }
            for r in righe_input
        ]

        # Utility 1:1 (opzionale).
        utility = contratto.get("utility") or {}

        return {
            "id": contratto.get("id"),
            "numero": contratto.get("numero"),
            "cliente": contratto.get("ba_ragione_sociale"),
            "cliente_codice": contratto.get("ba_codice"),
            "utility": contratto.get("utility_codice"),
            "ambito": contratto.get("ambito"),
            "stato": contratto.get("stato_codice"),
            "stato_descrizione": contratto.get("stato_descrizione"),
            "listino": contratto.get("listino_codice"),
            "tipo_variazione_globale": contratto.get("tipo_variazione_globale"),
            "valore_variazione_globale": str(contratto.get("valore_variazione_globale") or ""),
            "categoria_cliente_snapshot": contratto.get("categoria_cliente_snapshot_codice"),
            "categoria_cliente_snapshot_descrizione": contratto.get("categoria_cliente_snapshot_descrizione"),
            "valido_dal": str(contratto.get("valido_dal") or ""),
            "valido_al": str(contratto.get("valido_al") or ""),
            "data": str(contratto.get("data") or ""),
            "tipo_utenza": utility.get("tipo_utenza_codice"),
            "classe_utenza": utility.get("classe_utenza_codice"),
            "righe_count": len(righe_out),
            "righe": righe_out,
        }


# Scopo: Funzione di registrazione tool vendite.
#        Chiamata da tool_registry.populate_registry() all'avvio dell'app.
def get_vendite_tools() -> list[AITool]:
    return [
        CercaContrattiTool(),
        DettaglioContrattoTool(),
    ]
