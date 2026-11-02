# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Classe base per gli strumenti AI (tool).
#        Ogni tool wrappa un'API interna esistente e definisce
#        lo schema JSON per il function calling dell'LLM.
# ------------------------------------------------------------

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any

from apps.core.db._helpers import RICERCA_MIN_CARATTERI


# Scopo: L'endpoint della UI che fa la stessa cosa di un tool: la classe della
#        view e il metodo HTTP. Da qui si DERIVA il permesso del tool
#        (`apps.core.api.permissions.valuta_accesso_endpoint`), con la stessa
#        regola che `ZeroERPPermission` applica alla UI.
# ⛔ Il permesso non si dichiara sul tool (brief-db-area-funzionale-assistente-ai
#    §5.2). Fino al 2026-09-24 ogni tool scriveva a mano `required_area`,
#    `required_level`, `required_action`: una seconda copia della regola, che
#    gia' divergeva dalla UI — il cambio stato pratica chiedeva area `TUTTO`
#    dove l'endpoint chiede solo l'azione, l'elenco operatori un'area che non
#    esiste. E un tool che scrive, dichiarato `LETTURA` per svista, avrebbe
#    scritto per un operatore in sola lettura.
# ⚠️ Il gemello e' l'endpoint che chiama lo STESSO service con lo stesso
#    significato, non uno che «somiglia». Lo verifica
#    `test_tool_endpoint_gemello`: la view esiste e implementa il metodo.
@dataclass(frozen=True)
class EndpointGemello:
    view: type
    metodo: str


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
        endpoint: EndpointGemello,
        route_template: dict[str, Any] | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.endpoint = endpoint
        self.route_template = route_template

    # Scopo: Il tool scrive? Si DERIVA dal gemello (`chiamata_in_scrittura`),
    #        con la stessa regola che decide il tipo di accesso della UI.
    # ⛔ Non si dichiara (brief-db-area-funzionale-assistente-ai §5.3 punto 2).
    #    Fino al 2026-09-25 era `requires_confirmation=True` scritto a mano sui
    #    tre tool di scrittura: un tool che scrive con il flag dimenticato
    #    avrebbe scritto senza conferma, senza sola lettura a DB e col solo
    #    livello `LETTURA` sull'assistente.
    @property
    def scrive(self) -> bool:
        from apps.core.api.permissions import chiamata_in_scrittura

        return chiamata_in_scrittura(self.endpoint.view, method=self.endpoint.metodo)

    # Scopo: Il tool chiede conferma prima di eseguire: se e solo se scrive.
    #        Nome del contratto col frontend (`requires_confirmation` nel
    #        payload della preview), non una seconda regola.
    @property
    def requires_confirmation(self) -> bool:
        return self.scrive

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

    # Scopo: Il `limit` (quante righe) che l'LLM ha chiesto, normalizzato e
    #        messo sotto al tetto del tool (default 10, max 50).
    # ⭐ Fino al 2026-10-21 il parametro dei tool si chiamava `page_size` (e il
    #    metodo `safe_page_size`): rinominato col dialetto unico delle liste
    #    (Tid), perche' il modello e il frontend chiedano righe con lo stesso nome.
    #
    # 🔴 PERCHE' NON E' PIU' UN `min()` SECCO (2026-09-10). Era
    #    `min(params.get("limit", 10), max_size)`, e su tre input plausibili
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
    def safe_limit(params: dict[str, Any], max_size: int = 50) -> int:
        grezzo = params.get("limit")
        if grezzo is None:
            return min(10, max_size)
        # `bool` e' sottoclasse di `int`: senza questo, `True` diventerebbe 1.
        if isinstance(grezzo, bool) or (
            isinstance(grezzo, float) and not grezzo.is_integer()
        ):
            raise ValueError(
                f"limit deve essere un intero fra 1 e {max_size}: "
                f"ricevuto {grezzo!r}.",
            )
        try:
            valore = int(grezzo)
        except (TypeError, ValueError):
            raise ValueError(
                f"limit deve essere un intero fra 1 e {max_size}: "
                f"ricevuto {grezzo!r}.",
            ) from None
        if valore < 1:
            raise ValueError(
                f"limit deve essere almeno 1: ricevuto {valore}. "
                f"Per meno risultati chiedine 1, non 0.",
            )
        return min(valore, max_size)

    # Scopo: Il termine di ricerca libera che l'LLM ha chiesto, pronto per il
    #        service della lista: `None` se assente o vuoto, altrimenti il
    #        termine senza spazi ai bordi.
    # 🔴 SOTTO LA SOGLIA E' UN ERRORE, non un filtro ignorato (Tid,
    #    2026-09-24). Le liste che cercano col BB `add_ricerca_full_condition`
    #    IGNORANO un termine corto: a video va bene, perche' la casella
    #    manda il termine a ogni tasto e l'operatore vede la lista intera. Un
    #    modello invece riceverebbe TUTTE le righe credendole filtrate, e le
    #    riporterebbe all'utente come risultato della ricerca. Il messaggio
    #    nomina il dato e la soglia: un errore azionabile il modello lo
    #    corregge al giro dopo (stesso criterio di `safe_limit`).
    # ⭐ La soglia e' quella del BB (`RICERCA_MIN_CARATTERI`), non un 3 scritto
    #    qui: il giorno che cambia, strumenti e liste cambiano insieme.
    @staticmethod
    def termine_ricerca(params: dict[str, Any]) -> str | None:
        grezzo = params.get("search")
        if grezzo is None:
            return None
        if not isinstance(grezzo, str):
            raise ValueError(f"search deve essere un testo: ricevuto {grezzo!r}.")
        termine = grezzo.strip()
        if not termine:
            return None
        if len(termine) < RICERCA_MIN_CARATTERI:
            raise ValueError(
                f"search deve avere almeno {RICERCA_MIN_CARATTERI} caratteri: "
                f"ricevuto {termine!r}. Allunga il termine o togli il filtro.",
            )
        return termine

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
