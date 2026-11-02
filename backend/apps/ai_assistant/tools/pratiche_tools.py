# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Strumenti AI per il dominio pratiche.
#        Wrappano i service/repository esistenti di pratiche
#        per renderli disponibili all'LLM via function calling.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.ai_assistant.services.user_context import get_emittente_fiscale_id
from apps.ai_assistant.tools.base import AITool, EndpointGemello
from apps.pratiche.api.views import (
    ApiPraticaDetail,
    ApiPraticaFlussiList,
    ApiPraticaNoteList,
    ApiPraticaStato,
    ApiPraticheList,
)
from apps.core.db._helpers import RICERCA_MIN_CARATTERI


class CercaPraticheTool(AITool):
    """Tool per cercare pratiche nel sistema.

    Wrappa pratiche_service.cerca_pratiche() con gli stessi
    parametri dell'endpoint GET /api/v1/pratiche/.
    """

    def __init__(self) -> None:
        super().__init__(
            name="cerca_pratiche",
            description=(
                "Cerca pratiche nel sistema. Usare quando l'utente vuole trovare "
                "pratiche per cliente, stato, priorita', scadenza o operatore assegnato. "
                "Restituisce un elenco paginato con codice, descrizione, stato, "
                "priorita' e nominativo soggetto."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "search": {
                        "type": "string",
                        "description": f"Ricerca libera su codice, descrizione o nominativo soggetto (min {RICERCA_MIN_CARATTERI} caratteri).",
                    },
                    "stato": {
                        "type": "string",
                        # Valori da config.stati_pratiche.codice_interno.
                        # Se vengono aggiunti nuovi stati nel DB, aggiornare qui.
                        "enum": ["BOZZA", "APERTA", "SOSPESA", "CHIUSA", "ANNULLATA"],
                        "description": "Stato corrente della pratica (codice_interno)",
                    },
                    "data_da": {
                        "type": "string",
                        "description": "Data inserimento da (formato YYYY-MM-DD)",
                    },
                    "data_a": {
                        "type": "string",
                        "description": "Data inserimento a (formato YYYY-MM-DD)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Numero risultati per pagina (default 10, max 50)",
                    },
                },
                "required": [],
            },
            endpoint=EndpointGemello(ApiPraticheList, "GET"),
            # Naviga alla lista pratiche con filtro search pre-impostato
            route_template={
                "name": "pratiche-gestione",
                "query": {"search": "{codice}"},
            },
        )

    _FIELD_MAP = {
        "id": "id",
        "codice": "codice",
        "descrizione": "descrizione",
        "stato": "stato_codice_interno",
        "priorita": "priorita_descrizione",
        "soggetto": "soggetto_display",
        "operatore": "risorsa_umana_display",
        "data_insert": "data_insert",
    }

    # Scopo: Esegue la ricerca pratiche chiamando il service esistente.
    def execute(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        from apps.pratiche.services import pratiche_service

        items, total = pratiche_service.cerca_pratiche(
            emittente_fiscale_id=get_emittente_fiscale_id(request),
            stato_codice_interno=params.get("stato"),
            search=self.termine_ricerca(params),
            data_da=params.get("data_da"),
            data_a=params.get("data_a"),
            limit=self.safe_limit(params),
            offset=0,
            order_by="data_insert",
            order_dir="desc",
        )

        return {
            "count": total,
            "results": self.simplify_results(items, self._FIELD_MAP, str_fields={"data_insert"}),
        }


class DettaglioPraticaTool(AITool):
    """Tool per recuperare i dati completi di una pratica."""

    def __init__(self) -> None:
        super().__init__(
            name="dettaglio_pratica",
            description=(
                "Recupera i dati completi di una pratica per ID. Usare dopo "
                "cerca_pratiche per ottenere dettagli come tipo prestazione, "
                "soggetto associato, operatore, stato e date."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "pratica_id": {
                        "type": "integer",
                        "description": "ID numerico della pratica",
                    },
                },
                "required": ["pratica_id"],
            },
            endpoint=EndpointGemello(ApiPraticaDetail, "GET"),
        )

    # Scopo: Recupera il dettaglio di una pratica dal repository.
    def execute(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        from apps.pratiche.db.pratiche_repository import PraticheRepository

        repo = PraticheRepository()
        pratica = repo.get_pratica(params["pratica_id"])
        if pratica is None:
            return {"error": "Pratica non trovata."}

        return {
            "id": pratica.get("id"),
            "codice": pratica.get("codice"),
            "descrizione": pratica.get("descrizione"),
            "stato": pratica.get("stato_codice_interno"),
            "stato_descrizione": pratica.get("stato_descrizione"),
            "priorita": pratica.get("priorita_descrizione"),
            "tipo_prestazione": pratica.get("tipo_prestazione_descrizione"),
            "soggetto": pratica.get("soggetto_display"),
            "operatore": pratica.get("risorsa_umana_display"),
            "unita_organizzativa": pratica.get("unita_organizzativa_descrizione"),
            "data_apertura": str(pratica.get("data_apertura", "") or ""),
            "data_scadenza": str(pratica.get("data_scadenza", "") or ""),
            "data_insert": str(pratica.get("data_insert", "")),
        }


class CercaFlussiPraticaTool(AITool):
    """Tool per elencare i flussi operativi di una pratica."""

    def __init__(self) -> None:
        super().__init__(
            name="cerca_flussi_pratica",
            description=(
                "Elenca i flussi (step operativi) di una pratica. Usare per "
                "vedere a che punto e' una pratica, quali step sono completati "
                "e quali sono ancora da eseguire."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "pratica_id": {
                        "type": "integer",
                        "description": "ID numerico della pratica",
                    },
                },
                "required": ["pratica_id"],
            },
            endpoint=EndpointGemello(ApiPraticaFlussiList, "GET"),
        )

    # Scopo: Elenca i flussi di una pratica dal repository.
    def execute(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        from apps.pratiche.db.pratiche_repository import PraticheRepository

        repo = PraticheRepository()
        flussi = repo.list_flussi(params["pratica_id"])

        simplified = []
        for f in flussi:
            simplified.append({
                "id": f.get("id"),
                "descrizione": f.get("template_flusso_descrizione") or f.get("descrizione"),
                "stato": f.get("stato_codice_interno"),
                "esito": f.get("esito"),
                "sequenza": f.get("sequenza"),
                "data_scadenza": str(f.get("data_scadenza", "") or ""),
            })

        return {"count": len(simplified), "results": simplified}


class CreaPraticaTool(AITool):
    """Tool per creare una nuova pratica (richiede conferma)."""

    def __init__(self) -> None:
        super().__init__(
            name="crea_pratica",
            description=(
                "Crea una nuova pratica nel sistema. Richiede tipo prestazione, "
                "priorita' e opzionalmente soggetto, operatore e descrizione. "
                "L'operazione richiede conferma dell'utente prima dell'esecuzione."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "tipo_prestazione_id": {
                        "type": "integer",
                        "description": "ID del tipo prestazione",
                    },
                    "priorita_id": {
                        "type": "integer",
                        # ID da config.priorita_pratiche — non hardcodare valori.
                        "description": "ID della priorita' (da tabella config)",
                    },
                    "descrizione": {
                        "type": "string",
                        "description": "Descrizione libera della pratica",
                    },
                    "soggetto_id": {
                        "type": "string",
                        "description": "UUID del soggetto associato (opzionale)",
                    },
                    "data_scadenza": {
                        "type": "string",
                        "description": "Data scadenza (formato YYYY-MM-DD, opzionale)",
                    },
                },
                "required": ["tipo_prestazione_id", "priorita_id"],
            },
            endpoint=EndpointGemello(ApiPraticheList, "POST"),
        )

    # Scopo: Genera il sommario dell'operazione per la conferma utente.
    def preview(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        return {
            "summary": (
                f"Creare nuova pratica — "
                f"tipo prestazione ID {params.get('tipo_prestazione_id')}, "
                f"priorita' ID {params.get('priorita_id')}"
                + (f", descrizione: {params['descrizione']}" if params.get("descrizione") else "")
                + (f", soggetto: {params['soggetto_id']}" if params.get("soggetto_id") else "")
            ),
            "details": params,
        }

    # Scopo: Esegue la creazione della pratica chiamando il service.
    def execute(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        from apps.pratiche.services import pratiche_service

        emittente_id = get_emittente_fiscale_id(request)

        pratica_id = pratiche_service.crea_pratica(
            emittente_fiscale_id=emittente_id,
            tipo_prestazione_id=int(params["tipo_prestazione_id"]),
            priorita_id=int(params["priorita_id"]),
            soggetto_id=params.get("soggetto_id"),
            descrizione=params.get("descrizione"),
            data_scadenza=params.get("data_scadenza"),
        )

        return {
            "message": f"Pratica creata con successo (ID: {pratica_id}).",
            "pratica_id": pratica_id,
        }


class CambiaStatoPraticaTool(AITool):
    """Tool per cambiare lo stato di una pratica (richiede conferma)."""

    def __init__(self) -> None:
        super().__init__(
            name="cambia_stato_pratica",
            description=(
                "Cambia lo stato di una pratica esistente. Usare per attivare "
                "(BOZZA→APERTA), sospendere (APERTA→SOSPESA), chiudere "
                "(APERTA→CHIUSA), annullare o riattivare una pratica."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "pratica_id": {
                        "type": "integer",
                        "description": "ID della pratica",
                    },
                    "nuovo_stato": {
                        "type": "string",
                        # Valori da config.stati_pratiche.codice_interno.
                        "enum": ["APERTA", "SOSPESA", "CHIUSA", "ANNULLATA"],
                        "description": "Nuovo stato della pratica",
                    },
                },
                "required": ["pratica_id", "nuovo_stato"],
            },
            endpoint=EndpointGemello(ApiPraticaStato, "POST"),
        )

    # Scopo: Genera il sommario del cambio stato per la conferma.
    def preview(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        return {
            "summary": (
                f"Cambiare stato pratica #{params['pratica_id']} "
                f"→ {params['nuovo_stato']}"
            ),
            "details": params,
        }

    # Scopo: Esegue il cambio stato chiamando il service.
    def execute(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        from apps.pratiche.services import pratiche_service

        pratiche_service.cambia_stato_pratica(
            int(params["pratica_id"]),
            str(params["nuovo_stato"]),
        )

        return {
            "message": f"Stato pratica #{params['pratica_id']} cambiato in {params['nuovo_stato']}.",
        }


class AggiungiNotaPraticaTool(AITool):
    """Tool per aggiungere una nota a una pratica (richiede conferma)."""

    def __init__(self) -> None:
        super().__init__(
            name="aggiungi_nota_pratica",
            description=(
                "Aggiunge una nota testuale a una pratica esistente. "
                "Specificare il tipo nota (GENERALE, INTERNA, CLIENTE, TECNICA, LEGALE) "
                "e il contenuto."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "pratica_id": {
                        "type": "integer",
                        "description": "ID della pratica",
                    },
                    "tipo_nota": {
                        "type": "string",
                        "enum": ["GENERALE", "INTERNA", "CLIENTE", "TECNICA", "LEGALE"],
                        "description": "Tipo di nota",
                    },
                    "contenuto": {
                        "type": "string",
                        "description": "Testo della nota",
                    },
                },
                "required": ["pratica_id", "tipo_nota", "contenuto"],
            },
            endpoint=EndpointGemello(ApiPraticaNoteList, "POST"),
        )

    # Scopo: Genera il sommario della nota per la conferma.
    def preview(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        contenuto_preview = params.get("contenuto", "")[:80]
        return {
            "summary": (
                f"Aggiungere nota {params.get('tipo_nota', 'GENERALE')} "
                f"alla pratica #{params['pratica_id']}: "
                f"\"{contenuto_preview}{'...' if len(params.get('contenuto', '')) > 80 else ''}\""
            ),
            "details": params,
        }

    # Scopo: Esegue l'inserimento della nota chiamando il service.
    def execute(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        from apps.pratiche.services import pratiche_service

        nota_id = pratiche_service.crea_nota_pratica(
            pratica_id=int(params["pratica_id"]),
            tipo_nota_codice=str(params.get("tipo_nota", "GENERALE")),
            contenuto=str(params["contenuto"]),
        )

        return {
            "message": f"Nota aggiunta alla pratica #{params['pratica_id']} (ID nota: {nota_id}).",
            "nota_id": nota_id,
        }


# Scopo: Funzione di registrazione tool pratiche.
#        Chiamata dal tool_registry per popolare il catalogo.
def get_pratiche_tools() -> list[AITool]:
    return [
        CercaPraticheTool(),
        DettaglioPraticaTool(),
        CercaFlussiPraticaTool(),
        CreaPraticaTool(),
        CambiaStatoPraticaTool(),
        AggiungiNotaPraticaTool(),
    ]
