# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API view documenti generati a partire da OFFERTA_COMMERCIALE. Le
#        view vengono dal factory condiviso `build_documenti_sorgente_views`
#        (apps/documenti/api/sorgente_documenti_views.py — estrazione
#        regola-del-2 dei 5 cloni `*_documenti_views`); qui vivono SOLO i
#        delta di dominio: sorgente OFFERTA_COMMERCIALE, repo/service
#        offerte, chiave response `offerta`.
#
#        Specificita' offerta (decisione 2026-05-27): la GENERAZIONE avviene
#        SOLO all'emissione (BOZZA->EMESSA, `POST emetti/` multipart, atomica
#        con allegati) — la route `documenti/genera/` NON e' esposta (il
#        factory la produce, urls_offerte non la cabla). Gli allegati restano
#        aggiungibili anche dopo l'emissione via `documenti/<id>/allegati/`.
#        L'azione la dice la riga della matrice verso lo stato di emissione
#        (`emetti_offerta` su BOZZA -> EMESSA), non questa view
#        (`emetti_passaggio`, brief-modello-documento-vendita §13.6 punto 5).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from rest_framework.request import Request

from apps.config.sorgenti import SORGENTE_OFFERTA_COMMERCIALE
from apps.documenti.api.sorgente_documenti_views import (
    build_documenti_sorgente_views,
)
from apps.documenti.services.document_generation_service import (
    DocumentGenerationService,
)
from apps.vendite.db.offerte_repository import TESTATA_OFFERTE, OfferteRepository
from apps.vendite.services.offerte_service import OfferteService



# Scopo: Closure di dominio per il factory: contesto minimo (id, uid,
#        emittente) dal repo offerte. Patchabile nei test come
#        offerte_documenti_views.OfferteRepository.
def _get_entity(offerta_id: int) -> dict[str, Any] | None:
    return OfferteRepository().get_for_documento_generation(offerta_id)


# Scopo: Closure di dominio: istanza del motore documentale (patchabile nei
#        test come offerte_documenti_views.DocumentGenerationService).
def _doc_service() -> DocumentGenerationService:
    return DocumentGenerationService()


# Scopo: Closure di dominio: emissione BOZZA->EMESSA dal verbo di stato (il
#        guard DB congela la versione di listino). Patchabile nei test come
#        offerte_documenti_views.OfferteService.
def _emetti_call(request: Request, offerta_id: int) -> dict[str, Any]:
    return OfferteService().emetti(offerta_id)


_views = build_documenti_sorgente_views(
    schema_prefix="Offerta",
    sorgente_codice=SORGENTE_OFFERTA_COMMERCIALE,
    not_found_message="Offerta commerciale non trovata.",
    emittente_message="Emittente fiscale non risolto per l'offerta.",
    get_entity=_get_entity,
    doc_service=_doc_service,
    emetti_call=_emetti_call,
    emetti_response_key="offerta",
    model_permission=("vendite", "offerta_commerciale"),
    emetti_passaggio=TESTATA_OFFERTE,
)

ApiOffertaEmetti = _views.emetti
# NB: `_views.genera` esiste ma NON e' esportata/cablata: per le offerte la
# generazione definitiva passa solo dall'emissione (decisione 2026-05-27).
ApiOffertaDocumentoAnteprima = _views.anteprima
ApiOffertaDocumentiList = _views.lista
ApiOffertaDocumentoAllegati = _views.allegati
ApiOffertaDocumentoFile = _views.file
ApiOffertaDocumentoFileDownload = _views.file_download
# Percorso 3 (ristampa fedele): ri-renderizza l'originale dalla versione
# pinnata + contesto congelato. Vedi brief-ristampa-fedele-documenti.
ApiOffertaDocumentoRistampa = _views.ristampa
