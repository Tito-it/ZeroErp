# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API view documenti generati a partire da PREVENTIVO (Tranche K
#        motore documentale + emissione 2026-05-28). Le view vengono dal
#        factory condiviso `build_documenti_sorgente_views`
#        (apps/documenti/api/sorgente_documenti_views.py — estrazione
#        regola-del-2 dei 5 cloni `*_documenti_views`); qui vivono SOLO i
#        delta di dominio: sorgente PREVENTIVO, repo/service preventivi,
#        chiave response `preventivo`, il permesso dell'emissione dalla riga
#        del passaggio (`emetti_passaggio`, modello del documento).
#
#        Emissione (`POST emetti/`, multipart): BOZZA->EMESSO + genera
#        documento + allegati in transazione atomica. Se la generazione
#        fallisce, il rollback annulla l'emissione (stato resta BOZZA).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from rest_framework.request import Request

from apps.config.sorgenti import SORGENTE_PREVENTIVO
from apps.documenti.api.sorgente_documenti_views import (
    build_documenti_sorgente_views,
)
from apps.documenti.services.document_generation_service import (
    DocumentGenerationService,
)
from apps.vendite.db.preventivi_repository import TESTATA_PREVENTIVI, PreventiviRepository
from apps.vendite.services import preventivi_service



# Scopo: Closure di dominio per il factory: contesto minimo (id, uid,
#        emittente) dal repo preventivi. Patchabile nei test come
#        preventivi_documenti_views.PreventiviRepository.
def _get_entity(preventivo_id: int) -> dict[str, Any] | None:
    return PreventiviRepository().get_for_documento_generation(preventivo_id)


# Scopo: Closure di dominio: istanza del motore documentale (patchabile nei
#        test come preventivi_documenti_views.DocumentGenerationService).
def _doc_service() -> DocumentGenerationService:
    return DocumentGenerationService()


# Scopo: Closure di dominio: emissione BOZZA->EMESSO con audit utente (il
#        service preventivi traccia lo username). Patchabile nei test come
#        preventivi_documenti_views.preventivi_service.
def _emetti_call(request: Request, preventivo_id: int) -> dict[str, Any]:
    return preventivi_service.emetti(
        preventivo_id,
        user=getattr(request.user, "username", None) or None,
    )


_views = build_documenti_sorgente_views(
    schema_prefix="Preventivo",
    sorgente_codice=SORGENTE_PREVENTIVO,
    not_found_message="Preventivo non trovato.",
    emittente_message="Emittente fiscale non risolto per il preventivo.",
    get_entity=_get_entity,
    doc_service=_doc_service,
    emetti_call=_emetti_call,
    emetti_response_key="preventivo",
    # ⭐ L'azione dell'emissione la dice la riga DRAFT -> EMESSO della matrice
    #    (oggi `emetti_preventivo`), non questa view: il 403 arriva dalla stessa
    #    riga che legge il verbo (M-3, brief-modello-documento-vendita §8.7).
    emetti_passaggio=(TESTATA_PREVENTIVI, preventivi_service.STATO_EMESSO),
    model_permission=("vendite", "preventivo"),
)

ApiPreventivoEmetti = _views.emetti
ApiPreventivoDocumentoGenera = _views.genera
ApiPreventivoDocumentoAnteprima = _views.anteprima
ApiPreventivoDocumentiList = _views.lista
ApiPreventivoDocumentoAllegati = _views.allegati
ApiPreventivoDocumentoFile = _views.file
ApiPreventivoDocumentoFileDownload = _views.file_download
# Percorso 3 (ristampa fedele): ri-renderizza l'originale dalla versione
# pinnata + contesto congelato. Vedi brief-ristampa-fedele-documenti.
ApiPreventivoDocumentoRistampa = _views.ristampa
