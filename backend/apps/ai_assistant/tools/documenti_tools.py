# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Strumenti AI per il dominio documenti (motore documentale).
#        Espone la ricerca dei documenti generati persistiti (PDF
#        archiviati) per sorgente applicativa, con scope emittente
#        applicato automaticamente dal service.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any, Callable

from apps.config.sorgenti import SORGENTE_PREVENTIVO
from apps.ai_assistant.tools.base import AITool, EndpointGemello
from apps.vendite.api.preventivi_documenti_views import ApiPreventivoDocumentiList


# Mappa codice sorgente -> resolver (sorgente_id -> sorgente_uid). Un
# resolver e' una callable che, dato l'id applicativo del record sorgente,
# ritorna l'uid stabile usato dal motore documentale come chiave di
# correlazione dei documenti generati. Estendere questa mappa quando una
# nuova sorgente viene attivata (es. CONTRATTO -> contratti_service.get).
def _resolve_uid_preventivo(sorgente_id: int) -> str | None:
    from apps.core.services.error_manager import ServiceError
    from apps.vendite.services import preventivi_service

    try:
        detail = preventivi_service.get_preventivo(sorgente_id)
    except ServiceError:
        return None
    return str(detail.get("uid") or "") or None


_SORGENTE_UID_RESOLVERS: dict[str, Callable[[int], str | None]] = {
    SORGENTE_PREVENTIVO: _resolve_uid_preventivo,
}


class CercaDocumentiGeneratiTool(AITool):
    """Tool per cercare documenti generati (PDF archiviati) di un record sorgente.

    Wrappa DocumentGenerationService.list_documenti_per_sorgente() — stesso
    payload dell'endpoint GET /api/v1/vendite/preventivi/<id>/documenti/.
    Lo scope emittente del JWT viene applicato automaticamente dal service
    (`resolve_emittente_scope(user)`).

    Cross-sorgente: il tool risolve l'`uid` della sorgente partendo dal
    `sorgente_code` + `sorgente_id`. Oggi e' attiva solo la sorgente
    PREVENTIVO; nuove sorgenti si abilitano aggiungendo un resolver alla
    mappa `_SORGENTE_UID_RESOLVERS` (no schema change).
    """

    def __init__(self) -> None:
        super().__init__(
            name="cerca_documenti_generati",
            description=(
                "Cerca documenti PDF persistiti (snapshot del motore "
                "documentale) generati a partire da un record sorgente "
                "applicativo (es. preventivo). Restituisce la timeline "
                "delle versioni archiviate (numero progressivo, data "
                "generazione, nome file, stato). Usare quando l'utente "
                "chiede 'i PDF del preventivo X' o 'l'ultima versione "
                "del documento'. Il tool NON genera nuovi PDF: per la "
                "generazione occorre un'azione di scrittura dedicata."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "sorgente_code": {
                        "type": "string",
                        "enum": list(_SORGENTE_UID_RESOLVERS.keys()),
                        "description": "Codice della sorgente applicativa. Oggi e' attiva 'PREVENTIVO'; le altre saranno aggiunte quando il dominio espone la sorgente.",
                    },
                    "sorgente_id": {
                        "type": "integer",
                        "description": "ID applicativo del record sorgente (es. preventivo_id). Usare prima il tool di ricerca del dominio per ottenere l'ID.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Numero versioni da restituire (default 10, max 50).",
                    },
                },
                "required": ["sorgente_code", "sorgente_id"],
            },
            # ⚠️ Il gemello e' la lista documenti del PREVENTIVO perche'
            #    `_SORGENTE_UID_RESOLVERS` ne attiva una sola. Ogni sorgente
            #    ha la sua lista, con la sua area (`build_documenti_sorgente_views`):
            #    attivarne una seconda vuol dire un tool per sorgente, non una
            #    voce in piu' nella mappa sotto il gemello di un'altra.
            endpoint=EndpointGemello(ApiPreventivoDocumentiList, "GET"),
        )

    _FIELD_MAP = {
        "id": "id",
        "progressivo": "progressivo_sorgente",
        "generato_at": "generato_at",
        "titolo": "titolo",
        "nome_file": "nome_file",
        "stato": "stato",
        "template_codice": "template_codice",
    }

    # Scopo: Risolve sorgente_uid + sorgente_tipo_id e delega al service.
    def execute(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        from apps.config.db.sorgenti_repository import SorgentiRepository
        from apps.documenti.services.document_generation_service import (
            DocumentGenerationService,
        )

        sorgente_code = str(params["sorgente_code"]).upper()
        resolver = _SORGENTE_UID_RESOLVERS.get(sorgente_code)
        if resolver is None:
            return {
                "error": f"Sorgente '{sorgente_code}' non supportata.",
                "supportate": sorted(_SORGENTE_UID_RESOLVERS.keys()),
            }

        sorgente_uid = resolver(int(params["sorgente_id"]))
        if not sorgente_uid:
            return {"error": "Record sorgente non trovato o non accessibile."}

        sorgente = SorgentiRepository().get_sorgente_attiva(sorgente_code)
        if sorgente is None:
            return {
                "error": f"Sorgente '{sorgente_code}' non configurata o non attiva.",
            }
        sorgente_tipo_id = int(sorgente["id"])

        user = getattr(request, "user", None)
        result = DocumentGenerationService().list_documenti_per_sorgente(
            user,
            sorgente_tipo_id=sorgente_tipo_id,
            sorgente_uid=sorgente_uid,
            limit=self.safe_limit(params),
            offset=0,
        )
        rows = result.get("results") or []
        total = int(result.get("total_count") or 0)

        return {
            "count": total,
            "sorgente_code": sorgente_code,
            "sorgente_id": int(params["sorgente_id"]),
            "results": self.simplify_results(
                rows,
                self._FIELD_MAP,
                str_fields={"generato_at"},
            ),
        }


# Scopo: Funzione di registrazione tool documenti.
#        Chiamata da tool_registry.populate_registry() all'avvio dell'app.
def get_documenti_tools() -> list[AITool]:
    return [
        CercaDocumentiGeneratiTool(),
    ]
