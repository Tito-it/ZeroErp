# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API view documenti generati a partire da FATTURA (stampa/ristampa
#        della fattura). Le view vengono dal factory condiviso
#        `build_documenti_sorgente_views` (apps/documenti/api/
#        sorgente_documenti_views.py — estrazione regola-del-2 dei cloni
#        `*_documenti_views`); qui vivono SOLO i delta di dominio: sorgente
#        FATTURA, repo fattura (VenditeRepository), chiave response `fattura`.
#
#        A differenza dei 5 domini pre-esistenti, FATTURA NON ha emissione
#        manuale: la fattura è già prodotta dalla pipeline di fatturazione,
#        si stampa/ristampa soltanto. La factory viene quindi istanziata
#        SENZA `emetti_call` → `namespace.emetti = None` e nessuna rotta
#        `emetti/` viene cablata (I-4/D-7: la stampa è stupida, non cambia
#        stato). La stampa singola sincrona passa da `documenti/genera/`
#        (I-3); la ristampa massiva del lotto passa dalla coda
#        `fatture_stampa_coda` drenata dal worker (C-2b), non da qui.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.config.sorgenti import SORGENTE_FATTURA
from apps.documenti.api.sorgente_documenti_views import (
    build_documenti_sorgente_views,
)
from apps.documenti.services.document_generation_service import (
    DocumentGenerationService,
)
from apps.vendite.db.vendite_repository import VenditeRepository



# Scopo: Closure di dominio per il factory: contesto minimo (id, uid,
#        emittente_fiscale_id) dal repo vendite. La testata fattura espone
#        l'emittente come soggetto_ruolo (SR): il repo risolve la PK EF via
#        JOIN. Legge il global del modulo a call-time (patchabile nei test
#        come fatture_documenti_views.VenditeRepository).
def _get_entity(fattura_id: int) -> dict[str, Any] | None:
    return VenditeRepository().get_fattura_for_documento_generation(fattura_id)


# Scopo: Closure di dominio: istanza del motore documentale (patchabile nei
#        test come fatture_documenti_views.DocumentGenerationService).
def _doc_service() -> DocumentGenerationService:
    return DocumentGenerationService()


# FATTURA: nessun `emetti_call` → la view emetti non viene costruita
# (namespace.emetti = None). La fattura non si emette da UI: si stampa/ristampa.
_views = build_documenti_sorgente_views(
    schema_prefix="Fattura",
    sorgente_codice=SORGENTE_FATTURA,
    not_found_message="Fattura non trovata.",
    emittente_message="Emittente fiscale non risolto per la fattura.",
    get_entity=_get_entity,
    doc_service=_doc_service,
    model_permission=("vendite", "fattura"),
)

ApiFatturaDocumentoGenera = _views.genera
ApiFatturaDocumentoAnteprima = _views.anteprima
ApiFatturaDocumentiList = _views.lista
ApiFatturaDocumentoAllegati = _views.allegati
ApiFatturaDocumentoFile = _views.file
ApiFatturaDocumentoFileDownload = _views.file_download
# Percorso 3 (ristampa fedele): ri-renderizza l'originale dalla versione
# pinnata + contesto congelato. Vedi brief-ristampa-fedele-documenti.
ApiFatturaDocumentoRistampa = _views.ristampa
