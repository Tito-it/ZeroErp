# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API view documenti generati a partire da DDT_VENDITA (stampa DDT
#        accompagnatorio). Quinto dominio del motore `documenti`: le view
#        vengono dal factory condiviso `build_documenti_sorgente_views`
#        (apps/documenti/api/sorgente_documenti_views.py — estrazione
#        regola-del-2 dei 5 cloni `*_documenti_views`); qui vivono SOLO i
#        delta di dominio: sorgente DDT_VENDITA, repo/service DDT, chiave
#        response `ddt`.
#
#        Emissione (`POST emetti/`, multipart): DRAFT->EMESSO (il trigger DB
#        assegna il `numero` + gate componenti BoM) + genera documento +
#        allegati in transazione atomica. Se la generazione fallisce, il
#        rollback annulla l'emissione: stato resta DRAFT, numero non
#        consumato. L'accompagnatorio viaggia con la merce: l'emissione e'
#        il momento naturale di generazione/persistenza (mirror ordini).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from rest_framework.request import Request

from apps.config.sorgenti import SORGENTE_DDT_VENDITA
from apps.documenti.api.sorgente_documenti_views import (
    build_documenti_sorgente_views,
)
from apps.documenti.services.document_generation_service import (
    DocumentGenerationService,
)
from apps.vendite.db.ddt_repository import DdtRepository
from apps.vendite.services import ddt_service



# Scopo: Closure di dominio per il factory: contesto minimo (id, uid,
#        emittente) dal repo DDT. Legge il global del modulo a call-time
#        (patchabile nei test come ddt_documenti_views.DdtRepository).
def _get_entity(ddt_id: int) -> dict[str, Any] | None:
    return DdtRepository().get_for_documento_generation(ddt_id)


# Scopo: Closure di dominio: istanza del motore documentale (patchabile nei
#        test come ddt_documenti_views.DocumentGenerationService).
def _doc_service() -> DocumentGenerationService:
    return DocumentGenerationService()


# Scopo: Closure di dominio: transizione DRAFT->EMESSO (guard dal trigger DB,
#        ritorno light — parita' ordini_service.conferma). Patchabile nei test
#        come ddt_documenti_views.ddt_service.
def _emetti_call(request: Request, ddt_id: int) -> dict[str, Any]:
    return ddt_service.emetti(int(ddt_id))


_views = build_documenti_sorgente_views(
    schema_prefix="Ddt",
    sorgente_codice=SORGENTE_DDT_VENDITA,
    not_found_message="DDT non trovato.",
    emittente_message="Emittente fiscale non risolto per il DDT.",
    get_entity=_get_entity,
    doc_service=_doc_service,
    emetti_call=_emetti_call,
    emetti_response_key="ddt",
    model_permission=("vendite", "ddt"),
    # ⛔ L'azione di processo che il verbo DB applica all'emissione
    #    (`fn_cambia_stato_ddt` -> EMESSO: `emetti_ddt`), dichiarata qui come il
    #    gemello preventivo dichiara `cambia_stato_preventivi`
    #    (brief-be-verifica-documentazione-api §A5, 2026-10-20).
    emetti_post_permission="emetti_ddt",
)

ApiDdtEmetti = _views.emetti
ApiDdtDocumentoGenera = _views.genera
ApiDdtDocumentoAnteprima = _views.anteprima
ApiDdtDocumentiList = _views.lista
ApiDdtDocumentoAllegati = _views.allegati
ApiDdtDocumentoFile = _views.file
ApiDdtDocumentoFileDownload = _views.file_download
# Percorso 3 (ristampa fedele): ri-renderizza l'originale dalla versione
# pinnata + contesto congelato. Vedi brief-ristampa-fedele-documenti.
ApiDdtDocumentoRistampa = _views.ristampa
