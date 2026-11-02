# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API view documenti generati a partire da CONTRATTO. Le view vengono
#        dal factory condiviso `build_documenti_sorgente_views`
#        (apps/documenti/api/sorgente_documenti_views.py — estrazione
#        regola-del-2 dei 5 cloni `*_documenti_views`); qui vivono SOLO i
#        delta di dominio: sorgente CONTRATTO, repo/service contratti,
#        chiave response `contratto`.
#
#        Emissione (`POST emetti/`, multipart): DRAFT->ATTIVO + genera
#        documento + allegati in transazione atomica. Se il render fallisce,
#        il rollback annulla l'attivazione (stato resta DRAFT). L'azione la
#        dice la riga della matrice verso lo stato di emissione
#        (`emetti_contratto` su DRAFT -> ATTIVO), non questa view
#        (`emetti_passaggio`, brief-modello-documento-vendita §11.6).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from rest_framework.request import Request

from apps.config.sorgenti import SORGENTE_CONTRATTO
from apps.documenti.api.sorgente_documenti_views import (
    build_documenti_sorgente_views,
)
from apps.documenti.services.document_generation_service import (
    DocumentGenerationService,
)
from apps.vendite.db.contratti_repository import TESTATA_CONTRATTI, ContrattiRepository
from apps.vendite.services.contratti_service import ContrattiService



# Scopo: Closure di dominio per il factory: contesto minimo (id, uid,
#        emittente) dal repo contratti. Patchabile nei test come
#        contratti_documenti_views.ContrattiRepository.
def _get_entity(contratto_id: int) -> dict[str, Any] | None:
    return ContrattiRepository().get_for_documento_generation(contratto_id)


# Scopo: Closure di dominio: istanza del motore documentale (patchabile nei
#        test come contratti_documenti_views.DocumentGenerationService).
def _doc_service() -> DocumentGenerationService:
    return DocumentGenerationService()


# Scopo: Closure di dominio: attivazione DRAFT->ATTIVO (guard di dominio nel
#        service). Patchabile nei test come
#        contratti_documenti_views.ContrattiService.
def _emetti_call(request: Request, contratto_id: int) -> dict[str, Any]:
    return ContrattiService().emetti(contratto_id)


_views = build_documenti_sorgente_views(
    schema_prefix="Contratto",
    sorgente_codice=SORGENTE_CONTRATTO,
    not_found_message="Contratto non trovato.",
    emittente_message="Emittente fiscale non risolto per il contratto.",
    get_entity=_get_entity,
    doc_service=_doc_service,
    emetti_call=_emetti_call,
    emetti_response_key="contratto",
    # ⭐ Il 403 dalla stessa riga che legge il verbo (M-3, §11.6 punto 3); lo
    #    stato di emissione lo dice il vocabolario a ogni richiesta.
    emetti_passaggio=TESTATA_CONTRATTI,
    model_permission=("vendite", "contratto"),
)

ApiContrattoEmetti = _views.emetti
ApiContrattoDocumentoGenera = _views.genera
ApiContrattoDocumentoAnteprima = _views.anteprima
ApiContrattoDocumentiList = _views.lista
ApiContrattoDocumentoAllegati = _views.allegati
ApiContrattoDocumentoFile = _views.file
ApiContrattoDocumentoFileDownload = _views.file_download
# Percorso 3 (ristampa fedele): ri-renderizza l'originale dalla versione
# pinnata + contesto congelato. Vedi brief-ristampa-fedele-documenti.
ApiContrattoDocumentoRistampa = _views.ristampa
