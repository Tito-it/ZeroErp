# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Strumenti AI per il dominio vendite.
#        Espone la ricerca contratti e il dettaglio contratto
#        (via ContrattiService) all'LLM tramite function calling.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.ai_assistant.tools.base import AITool, EndpointGemello
from apps.vendite.api.preventivi_views import ApiPreventiviList, ApiPreventivoDetail
from apps.vendite.api.views_contratti import ApiContrattiList, ApiContrattoDetail
from apps.vendite.api.views_listini import ApiListiniList
from apps.vendite.api.views_promo_articoli import PromoArticoliView
from apps.core.db._helpers import RICERCA_MIN_CARATTERI


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
                        "description": f"Ricerca libera su numero contratto o ragione sociale cliente (min {RICERCA_MIN_CARATTERI} caratteri).",
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
                        "description": "Filtro validita' - data inizio (YYYY-MM-DD). Nessun default backend.",
                    },
                    "data_a": {
                        "type": "string",
                        "description": "Filtro validita' - data fine (YYYY-MM-DD).",
                    },
                    "scadenza_mese": {
                        "type": "string",
                        "description": "Mese di scadenza in formato YYYY-MM (es. 2026-07). Filtra contratti che scadono nel mese indicato.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Numero risultati (default 10, max 50).",
                    },
                },
                "required": [],
            },
            endpoint=EndpointGemello(ApiContrattiList, "GET"),
            # Naviga alla lista contratti con filtro search pre-impostato sul numero
            route_template={
                "name": "vendite-contratti",
                "query": {"search": "{numero}"},
            },
        )

    _FIELD_MAP = {
        "id": "id",
        "numero": "numero",
        "cliente": "ragione_sociale_completa",
        "cliente_codice": "ba_codice",
        "utility": "utility_codice",
        "ambito": "ambito",
        "listino": "listino_codice",
        "categoria_cliente": "categoria_cliente_snapshot_codice",
        "valido_dal": "valido_dal",
        "valido_al": "valido_al",
        "stato": "stato_codice_interno",
        "stato_descrizione": "stato_descrizione",
    }

    # Scopo: Esegue la ricerca contratti chiamando il service esistente.
    def execute(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        from apps.vendite.services.contratti_service import ContrattiService

        svc = ContrattiService()
        items, total = svc.list_contratti(
            search=self.termine_ricerca(params),
            billing_account_id=params.get("billing_account_id"),
            stato_doc_contratto_id=params.get("stato_doc_contratto_id"),
            utility_id=params.get("utility_id"),
            ambito=params.get("ambito"),
            listino_id=params.get("listino_id"),
            data_da=params.get("data_da"),
            data_a=params.get("data_a"),
            scadenza_mese=params.get("scadenza_mese"),
            limit=self.safe_limit(params),
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
            endpoint=EndpointGemello(ApiContrattoDetail, "GET"),
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
                "quantita": str(r.get("quantita") or ""),
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
            "stato": contratto.get("stato_codice_interno"),
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


class CercaPreventiviTool(AITool):
    """Tool per cercare preventivi vendita.

    Wrappa preventivi_service.list_preventivi() — stessi filtri dell'endpoint
    GET /api/v1/vendite/preventivi/. Lo scope emittente del JWT viene applicato
    automaticamente passando `auth_user_id` al service (PermissionResolver
    risolve la whitelist EF dell'operatore).
    """

    def __init__(self) -> None:
        super().__init__(
            name="cerca_preventivi",
            description=(
                "Cerca preventivi di vendita nel sistema. Un preventivo e' la "
                "proposta commerciale al cliente con righe articoli e totali; "
                "il ciclo di vita e' DRAFT (BOZZA) -> EMESSO -> ACCETTATO/"
                "RIFIUTATO/SCADUTO/ANNULLATO. Usare quando l'utente chiede di "
                "trovare preventivi per stato, cliente (billing_account), "
                "utility, periodo o numero. Restituisce numero, data, cliente, "
                "totale documento, stato, validita'."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "search": {
                        "type": "string",
                        "description": f"Ricerca libera su numero preventivo o ragione sociale cliente (min {RICERCA_MIN_CARATTERI} caratteri).",
                    },
                    "stato_codice": {
                        "type": "string",
                        "description": "Codice interno stato preventivo: DRAFT (BOZZA), EMESSO, ACCETTATO, RIFIUTATO, SCADUTO, ANNULLATO.",
                    },
                    "billing_account_id": {
                        "type": "integer",
                        "description": "ID cliente (billing account). Usare prima cerca_billing_account per ottenerlo.",
                    },
                    "utility_id": {
                        "type": "integer",
                        "description": "ID utility (gas/energia/idrico) per filtrare preventivi della utility.",
                    },
                    "data_da": {
                        "type": "string",
                        "description": "Filtro data documento - inizio (YYYY-MM-DD).",
                    },
                    "data_al": {
                        "type": "string",
                        "description": "Filtro data documento - fine (YYYY-MM-DD).",
                    },
                    "solo_ultima_revisione": {
                        "type": "boolean",
                        "description": "True (default) ritorna solo l'ultima revisione per numero. False per vedere lo storico revisioni.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Numero risultati (default 10, max 50).",
                    },
                },
                "required": [],
            },
            endpoint=EndpointGemello(ApiPreventiviList, "GET"),
            route_template={
                "name": "vendite-preventivi",
                "query": {"search": "{numero}"},
            },
        )

    _FIELD_MAP = {
        "id": "id",
        "numero": "numero",
        "rev": "rev",
        "data": "data",
        "cliente": "cliente_denominazione",
        "cliente_codice": "billing_account_codice",
        "utility": "utility_descrizione",
        "totale_documento": "totale_documento",
        "validita_al": "validita_al",
        "stato": "stato_codice_interno",
        "stato_descrizione": "stato_descrizione",
    }

    # Scopo: Esegue la ricerca preventivi via service. Passa auth_user_id
    #        per applicare lo scope emittente (whitelist EF dell'operatore).
    def execute(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        from apps.vendite.services import preventivi_service

        user = getattr(request, "user", None)
        auth_user_id = getattr(user, "id", None) if user else None
        envelope = preventivi_service.list_preventivi(
            stato_codice=params.get("stato_codice"),
            billing_account_id=params.get("billing_account_id"),
            utility_id=params.get("utility_id"),
            data_da=params.get("data_da"),
            data_al=params.get("data_al"),
            search=self.termine_ricerca(params),
            solo_ultima_revisione=params.get("solo_ultima_revisione", True),
            auth_user_id=auth_user_id,
            limit=self.safe_limit(params),
        )
        results = envelope.get("results") or []
        total = int(envelope.get("count") or 0)

        return {
            "count": total,
            "results": self.simplify_results(
                results,
                self._FIELD_MAP,
                str_fields={"data", "validita_al", "totale_documento"},
            ),
        }


class DettaglioPreventivoTool(AITool):
    """Tool per recuperare dati completi di un preventivo (testata + summary)."""

    def __init__(self) -> None:
        super().__init__(
            name="dettaglio_preventivo",
            description=(
                "Recupera i dati completi di un preventivo per ID: testata "
                "(numero, rev, cliente, utility, validita', totali), "
                "indirizzi, capabilities e numero righe. Le righe vere si "
                "ottengono in un secondo passo se servono. Usare dopo "
                "cerca_preventivi per ottenere i dettagli di un record specifico."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "preventivo_id": {
                        "type": "integer",
                        "description": "ID numerico del preventivo.",
                    },
                },
                "required": ["preventivo_id"],
            },
            endpoint=EndpointGemello(ApiPreventivoDetail, "GET"),
        )

    # Scopo: Recupera il dettaglio del preventivo dal service.
    def execute(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        del request
        from apps.core.services.error_manager import ServiceError
        from apps.vendite.services import preventivi_service

        try:
            detail = preventivi_service.get_preventivo(params["preventivo_id"])
        except ServiceError as exc:
            return {"error": exc.message or "Preventivo non trovato."}

        return {
            "id": detail.get("id"),
            "numero": detail.get("numero"),
            "rev": detail.get("rev"),
            "data": str(detail.get("data") or ""),
            "cliente": detail.get("cliente_denominazione"),
            "billing_account_id": detail.get("billing_account_id"),
            "utility": detail.get("utility_descrizione"),
            "stato": detail.get("stato_codice_interno"),
            "stato_descrizione": detail.get("stato_descrizione"),
            "validita_dal": str(detail.get("validita_dal") or ""),
            "validita_al": str(detail.get("validita_al") or ""),
            "totale_imponibile": str(detail.get("totale_imponibile") or ""),
            "totale_iva": str(detail.get("totale_iva") or ""),
            "totale_documento": str(detail.get("totale_documento") or ""),
            "fatturazione_immediata": detail.get("fatturazione_immediata"),
            "competenza_mese": str(detail.get("competenza_mese") or ""),
            "righe_count": detail.get("righe_count"),
            "indirizzi_count": len(detail.get("indirizzi") or []),
        }


class CercaPromoArticoliTool(AITool):
    """Tool per cercare promo articoli (variazione prezzo a tempo per articolo)."""

    def __init__(self) -> None:
        super().__init__(
            name="cerca_promo_articoli",
            description=(
                "Cerca promo articolo nel sistema. Una promo e' una variazione "
                "di prezzo (PERCENTUALE / VALORE_FISSO / PREZZO_FISSO) "
                "applicata a un articolo specifico in una finestra temporale, "
                "che il resolver di pricing (STADIO 0) usa prima del listino. "
                "Usare quando l'utente chiede promo attive su un articolo, "
                "promo per tipo di variazione o promo valide a una certa data."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "search": {
                        "type": "string",
                        "description": f"Ricerca libera su codice/descrizione della promo o codice/descrizione articolo (min {RICERCA_MIN_CARATTERI} caratteri).",
                    },
                    "articolo_id": {
                        "type": "string",
                        "description": "UUID dell'articolo per filtrare le promo di un articolo specifico. Usare prima cerca_articoli.",
                    },
                    "uom_id": {
                        "type": "integer",
                        "description": "ID unita' di misura operativa: filtra le promo per uom specifica.",
                    },
                    "tipo_variazione": {
                        "type": "string",
                        "enum": ["PERCENTUALE", "VALORE_FISSO", "PREZZO_FISSO"],
                        "description": "Tipo di variazione applicata dalla promo.",
                    },
                    "attivo": {
                        "type": "boolean",
                        "description": "True per solo promo attive (flag tecnico).",
                    },
                    "valid_at": {
                        "type": "string",
                        "description": "Data per filtrare le promo valide in quel giorno (YYYY-MM-DD).",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Numero risultati (default 10, max 50).",
                    },
                },
                "required": [],
            },
            endpoint=EndpointGemello(PromoArticoliView, "GET"),
            route_template={
                "name": "vendite-promo-articoli",
                "query": {"search": "{codice}"},
            },
        )

    _FIELD_MAP = {
        "id": "id",
        "codice": "codice",
        "articolo_codice": "articolo_codice",
        "articolo_descrizione": "articolo_descrizione",
        "uom": "uom_codice",
        "tipo_variazione": "tipo_variazione",
        "valore_variazione": "valore_variazione",
        "valido_dal": "valido_dal",
        "valido_al": "valido_al",
        "attivo": "attivo",
    }

    # Scopo: Esegue la ricerca promo via service.
    def execute(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        del request
        from apps.vendite.services.promo_articoli_service import PromoArticoliService

        items, total = PromoArticoliService().list_promo(
            search=self.termine_ricerca(params),
            attivo=params.get("attivo"),
            articolo_id=params.get("articolo_id"),
            uom_id=params.get("uom_id"),
            tipo_variazione=params.get("tipo_variazione"),
            valid_at=params.get("valid_at"),
            limit=self.safe_limit(params),
            offset=0,
            order_by="valido_dal",
            order_dir="desc",
        )

        return {
            "count": total,
            "results": self.simplify_results(
                items,
                self._FIELD_MAP,
                str_fields={"valido_dal", "valido_al", "valore_variazione"},
            ),
        }


class CercaListiniTool(AITool):
    """Tool per cercare listini di pricing."""

    def __init__(self) -> None:
        super().__init__(
            name="cerca_listini",
            description=(
                "Cerca listini di pricing nel sistema. Un listino raggruppa "
                "righe articolo-prezzo per una utility e una tipologia "
                "(commercio/utility), applicato dai contratti via il resolver "
                "di pricing. Usare quando l'utente chiede di trovare listini "
                "per utility, tipologia o codice/descrizione."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "search": {
                        "type": "string",
                        "description": f"Ricerca libera su codice o descrizione listino (min {RICERCA_MIN_CARATTERI} caratteri).",
                    },
                    "utility_id": {
                        "type": "integer",
                        "description": "ID utility (gas/energia/idrico) per filtrare i listini di una utility.",
                    },
                    "tipologia_id": {
                        "type": "integer",
                        "description": "ID tipologia listino (codice da config.listini_tipologie).",
                    },
                    "attivo": {
                        "type": "boolean",
                        "description": "True per solo listini attivi.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Numero risultati (default 10, max 50).",
                    },
                },
                "required": [],
            },
            endpoint=EndpointGemello(ApiListiniList, "GET"),
            route_template={
                "name": "vendite-listini",
                "query": {"search": "{codice}"},
            },
        )

    _FIELD_MAP = {
        "id": "id",
        "codice": "codice",
        "descrizione": "descrizione",
        "utility": "utility_codice",
        "tipologia": "tipologia_codice",
        "dominio": "dominio",
        "attivo": "attivo",
    }

    # Scopo: Esegue la ricerca listini via service.
    def execute(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        del request
        from apps.vendite.services.listini_service import fn_list_listini

        items, total = fn_list_listini(
            search=self.termine_ricerca(params),
            utility_id=params.get("utility_id"),
            tipologia_id=params.get("tipologia_id"),
            attivo=params.get("attivo"),
            limit=self.safe_limit(params),
            offset=0,
            order_by="codice",
            order_dir="asc",
        )

        return {
            "count": total,
            "results": self.simplify_results(items, self._FIELD_MAP),
        }


# Scopo: Funzione di registrazione tool vendite.
#        Chiamata da tool_registry.populate_registry() all'avvio dell'app.
def get_vendite_tools() -> list[AITool]:
    return [
        CercaContrattiTool(),
        DettaglioContrattoTool(),
        CercaPreventiviTool(),
        DettaglioPreventivoTool(),
        CercaPromoArticoliTool(),
        CercaListiniTool(),
    ]
