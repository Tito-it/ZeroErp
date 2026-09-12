# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Classe base per gli strumenti AI (tool).
#        Ogni tool wrappa un'API interna esistente e definisce
#        lo schema JSON per il function calling dell'LLM.
# ------------------------------------------------------------

from __future__ import annotations

import abc
from typing import Any


class AITool(abc.ABC):
    """Definizione di uno strumento AI per il function calling.

    Ogni tool corrisponde a un'operazione disponibile nel sistema
    (cerca pratiche, dettaglio soggetto, ecc.) e wrappa un
    service/repository esistente.
    """

    def __init__(
        self,
        *,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        required_area: str | None,
        required_level: str = "LETTURA",
        route_template: dict[str, Any] | None = None,
        requires_confirmation: bool = False,
        required_action: str | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.required_area = required_area
        self.required_level = required_level
        self.route_template = route_template
        self.requires_confirmation = requires_confirmation
        # Azione di processo fine (codename) richiesta, speculare al
        # `<action>_permission` dell'endpoint UI corrispondente. Se valorizzata,
        # il filtro/ri-check verifica anche check_azione → l'AI ha la STESSA
        # granularita' (area + azione fine) della UI. None = solo area-level.
        self.required_action = required_action

    # Scopo: Esegue il tool con i parametri forniti dall'LLM.
    #        Ogni sottoclasse deve implementare questo metodo.
    #        Il request originale viene passato per ereditare il contesto
    #        di autenticazione (user, emittente_fiscale_id).
    @abc.abstractmethod
    def execute(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        """Esegue il tool e restituisce il risultato come dict.

        Args:
            params: Parametri estratti dall'LLM (validati contro input_schema).
            request: Request Django originale per contesto autenticazione.

        Returns:
            Dizionario con i risultati, restituito all'LLM come tool_result.
        """

    # Scopo: Genera un sommario dell'operazione senza eseguirla.
    #        I tool in scrittura sovrascrivono questo metodo per restituire
    #        un summary leggibile dall'utente prima della conferma.
    def preview(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        return {"summary": f"Eseguire {self.name} con i parametri forniti"}

    # Scopo: Il `page_size` che l'LLM ha chiesto, normalizzato e messo sotto al
    #        tetto del tool (default 10, max 50).
    #
    # 🔴 PERCHE' NON E' PIU' UN `min()` SECCO (2026-09-10). Era
    #    `min(params.get("page_size", 10), max_size)`, e su tre input plausibili
    #    si rompeva o taceva:
    #
    #      · `"20"` — la forma in cui un LLM manda un intero — sollevava
    #        `TypeError: '<' not supported between 'str' and 'int'`. Non e' un
    #        500 (l'executor cattura e gira il testo al modello), ma quel testo
    #        il modello non lo puo' usare per correggersi: il giro fallisce e
    #        basta;
    #      · `null` esplicito faceva lo stesso — `params.get(k, 10)` restituisce
    #        `None` quando la chiave c'e' col valore nullo, non il default;
    #      · `0` o un negativo PASSAVANO il tetto e morivano piu' giu', nel
    #        service, con un errore che parla di un altro parametro.
    #
    # ⭐ IL CRITERIO E' QUELLO DEL PROGETTO, non uno nuovo: rigore sui tipi come
    #    `PayloadValidator` (bool != int, float non intero rifiutato, stringhe
    #    numeriche ammesse) e messaggio che NOMINA il dato e i valori ammessi —
    #    qui chi legge e' un modello, e un errore azionabile lo corregge al giro
    #    dopo, mentre uno criptico gli fa abbandonare lo strumento.
    # ⚠️ Il tetto superiore resta un CLAMP silenzioso, ed e' voluto: «max 50» e'
    #    scritto nella `description` di ogni tool, quindi chiedere 200 non e' un
    #    errore del chiamante — e' una richiesta che il contratto riduce.
    @staticmethod
    def safe_page_size(params: dict[str, Any], max_size: int = 50) -> int:
        grezzo = params.get("page_size")
        if grezzo is None:
            return min(10, max_size)
        # `bool` e' sottoclasse di `int`: senza questo, `True` diventerebbe 1.
        if isinstance(grezzo, bool) or (
            isinstance(grezzo, float) and not grezzo.is_integer()
        ):
            raise ValueError(
                f"page_size deve essere un intero fra 1 e {max_size}: "
                f"ricevuto {grezzo!r}.",
            )
        try:
            valore = int(grezzo)
        except (TypeError, ValueError):
            raise ValueError(
                f"page_size deve essere un intero fra 1 e {max_size}: "
                f"ricevuto {grezzo!r}.",
            ) from None
        if valore < 1:
            raise ValueError(
                f"page_size deve essere almeno 1: ricevuto {valore}. "
                f"Per meno risultati chiedine 1, non 0.",
            )
        return min(valore, max_size)

    # Scopo: Semplifica una lista di risultati estraendo solo i campi specificati.
    #        field_map: {nome_output: nome_input} o {nome: nome} se uguale.
    #        Funzione ausiliaria per evitare loop ripetitivi nei tool.
    @staticmethod
    def simplify_results(
        items: list[dict[str, Any]],
        field_map: dict[str, str],
        *,
        str_fields: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        str_fields = str_fields or set()
        simplified = []
        for item in items:
            row: dict[str, Any] = {}
            for out_key, in_key in field_map.items():
                value = item.get(in_key)
                if out_key in str_fields:
                    value = str(value or "")
                row[out_key] = value
            simplified.append(row)
        return simplified

    # Scopo: Converte la definizione tool nel formato JSON richiesto
    #        dall'API Anthropic per il function calling.
    def to_tool_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }

    # Scopo: Genera azioni di navigazione dai risultati del tool.
    #        Se route_template e' definito, crea un'azione per ogni
    #        risultato che ha un campo "id".
    def extract_actions(self, result: dict[str, Any]) -> list[dict[str, Any]]:
        if not self.route_template:
            return []

        actions: list[dict[str, Any]] = []
        items = result.get("results", [])
        for item in items[:5]:  # Max 5 azioni di navigazione
            item_id = item.get("id")
            if item_id is None:
                continue

            # Sostituisci placeholder {id} con il valore reale
            route = _resolve_route_template(self.route_template, item)

            # Costruisci label dal primo campo descrittivo disponibile
            label = (
                item.get("codice")
                or item.get("descrizione")
                or item.get("ragione_sociale_completa")
                or f"#{item_id}"
            )

            actions.append({
                "type": "navigate",
                "label": f"Apri {label}",
                "route": route,
            })

        return actions


# Scopo: Risolve i placeholder nel route_template sostituendo
#        {campo} con i valori reali dall'item.
def _resolve_route_template(
    template: dict[str, Any], item: dict[str, Any]
) -> dict[str, Any]:
    route = {}
    for key, value in template.items():
        if isinstance(value, dict):
            route[key] = _resolve_route_template(value, item)
        elif isinstance(value, str) and value.startswith("{") and value.endswith("}"):
            field_name = value[1:-1]
            route[key] = item.get(field_name, value)
        else:
            route[key] = value
    return route
