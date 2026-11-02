# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API view documenti generati a partire da ORDINE_VENDITA (stampa
#        conferma d'ordine). Le view vengono dal factory condiviso
#        `build_documenti_sorgente_views` (apps/documenti/api/
#        sorgente_documenti_views.py — estrazione regola-del-2 dei 5 cloni
#        `*_documenti_views`); qui vivono SOLO i delta di dominio: sorgente
#        ORDINE_VENDITA, repo/service ordini, chiave response `ordine`.
#
#        Emissione (`POST emetti/`, multipart): DRAFT->CONFERMATO + genera
#        documento + allegati in transazione atomica (flusso §6
#        brief-ordini-stampa.md, rettifica 2026-06-05: la conferma d'ordine
#        e' l'atto formale verso il cliente ed e' il trigger del push a
#        commessa — momento naturale di generazione/persistenza del PDF).
#        Se la generazione fallisce, il rollback annulla la conferma.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from rest_framework.request import Request

from apps.config.sorgenti import SORGENTE_ORDINE_VENDITA
from apps.documenti.api.sorgente_documenti_views import (
    build_documenti_sorgente_views,
)
from apps.documenti.services.document_generation_service import (
    DocumentGenerationService,
)
from apps.vendite.db.ordini_repository import TESTATA_ORDINI, OrdiniRepository
from apps.vendite.services import ordini_service


# Scopo: Closure di dominio per il factory: contesto minimo (id, uid,
#        emittente) dal repo ordini. Legge il global del modulo a call-time
#        (patchabile nei test come ordini_documenti_views.OrdiniRepository).
def _get_entity(ordine_id: int) -> dict[str, Any] | None:
    return OrdiniRepository().get_for_documento_generation(ordine_id)


# Scopo: Closure di dominio: istanza del motore documentale (patchabile nei
#        test come ordini_documenti_views.DocumentGenerationService).
def _doc_service() -> DocumentGenerationService:
    return DocumentGenerationService()


# Scopo: Closure di dominio: la conferma (lo stato di emissione dell'ordine)
#        dal verbo, con lo step della pratica nella stessa transazione: lo
#        step lo chiude l'utente della richiesta (dopo il ritiro di
#        `/conferma/` questa e' l'unica strada della conferma).
#        Patchabile nei test come ordini_documenti_views.ordini_service.
def _emetti_call(request: Request, ordine_id: int) -> dict[str, Any]:
    return ordini_service.conferma(
        int(ordine_id),
        user=getattr(request.user, "username", None) or None,
    )


_views = build_documenti_sorgente_views(
    schema_prefix="Ordine",
    sorgente_codice=SORGENTE_ORDINE_VENDITA,
    not_found_message="Ordine non trovato.",
    emittente_message="Emittente fiscale non risolto per l'ordine.",
    get_entity=_get_entity,
    doc_service=_doc_service,
    emetti_call=_emetti_call,
    emetti_response_key="ordine",
    # ⭐ L'azione dell'emissione la dice la riga della matrice verso lo stato
    #    di emissione (oggi `emetti_ordine` su DRAFT -> CONFERMATO), non questa
    #    view: il 403 arriva dalla stessa riga che legge il verbo (M-3,
    #    brief-modello-documento-vendita §9.6 C-5); lo stato lo dice il
    #    vocabolario a ogni richiesta (§8.11 B-2).
    emetti_passaggio=TESTATA_ORDINI,
    model_permission=("vendite", "ordine"),
)

ApiOrdineEmetti = _views.emetti
ApiOrdineDocumentoGenera = _views.genera
ApiOrdineDocumentoAnteprima = _views.anteprima
ApiOrdineDocumentiList = _views.lista
ApiOrdineDocumentoAllegati = _views.allegati
ApiOrdineDocumentoFile = _views.file
ApiOrdineDocumentoFileDownload = _views.file_download
# Percorso 3 (ristampa fedele): ri-renderizza l'originale dalla versione
# pinnata + contesto congelato. Vedi brief-ristampa-fedele-documenti.
ApiOrdineDocumentoRistampa = _views.ristampa
