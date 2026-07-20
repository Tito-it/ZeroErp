# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Core del worker DRAINER della coda stampa (outbox documentale, Fase C
#        C-2b/C-2d). Drena `vendite.fatture_stampa_coda`: per ogni fattura in
#        coda numera (backstop C-2d, idempotente) e genera il PDF via il motore
#        documentale in CONTESTO SISTEMA (C-0, `emittente_scope=None`), poi
#        aggiorna lo stato della riga (FATTO / PENDING-riprova / ERRORE).
#
#        Invarianti (brief-be-fe-processi-fatturazione, §FASE C):
#         - I-4/D-7: la stampa è stupida. Il drainer non conosce «lotto» né
#           «fatturazione»: sa solo drenare la coda un work-item alla volta.
#         - I-4b: il render avviene FUORI dalla transazione di numerazione; la
#           connessione non tiene lock fiscali durante l'I/O di rendering.
#         - Resilienza per-riga: un render fallito incrementa i tentativi e non
#           ferma gli altri (`ERRORE` oltre soglia, altrimenti `PENDING` per il
#           PROSSIMO giro — non ri-lavorato nello stesso, per non ciclare).
#         - Idempotenza: l'indice unico parziale della coda impedisce doppioni
#           vivi; il claim `FOR UPDATE SKIP LOCKED` regge più worker paralleli.
#
#        È il CORE unico (I-1): il management command `draina_coda_stampa` ne è
#        un chiamante sottile (argparse + canale sistema + registered_job).
#        Assume di girare DENTRO `system_process_context` (canale BYPASSRLS):
#        `genera_documento` fallirebbe fail-loud (`_guard_canale_sistema`) se
#        invocato fuori dal canale di sistema — difesa in profondità.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from apps.core.services.error_manager import ServiceError
from apps.documenti.services.document_generation_service import (
    DocumentGenerationService,
)
from apps.vendite.db.pipeline_repository import VenditePipelineRepository
from apps.vendite.db.vendite_repository import VenditeRepository

logger = logging.getLogger(__name__)

# Soglia oltre cui una riga passa a ERRORE terminale (P-2: default sensato,
# tarabile). Cadenza worker e cap batch tarabili su volumi veri (P-5).
_SOGLIA_TENTATIVI_DEFAULT = 5
# Righe claimate per giro: batch unico per run (niente re-claim delle righe
# fallite nello stesso giro → nessun ciclo di retry immediato). Backlog >
# limit: lo raccoglie il giro successivo del cron.
_LIMIT_DEFAULT = 500
# Reaper: righe IN_CORSO più vecchie di N minuti = worker morto → riportate a
# PENDING. Soglia larga (≫ tempo di un render) per non toccare worker lenti.
_STALE_MINUTI_DEFAULT = 30


# Scopo: Drena la coda stampa. Perimetro e risultato:
#         1. (opz.) reaper delle righe IN_CORSO stantie → PENDING;
#         2. claim atomico di ≤ `limit` work-item PENDING (SKIP LOCKED);
#         3. per ciascuno: risolve l'emittente dalla fattura, numera (backstop
#            C-2d), genera il PDF in contesto sistema, marca l'esito;
#         4. esito strutturato aggregato per il run-log e la console.
#        Best-effort per-riga: nessun fallimento di render propaga oltre la
#        riga. Un fallimento di scrittura sulla coda (DB) invece propaga: la
#        run va marcata fallita (job_run_log), non mascherata.
def draina_coda_stampa(
    *,
    limit: int = _LIMIT_DEFAULT,
    soglia_tentativi: int = _SOGLIA_TENTATIVI_DEFAULT,
    stale_minuti: int = _STALE_MINUTI_DEFAULT,
    on_item_esito: Callable[[dict[str, Any], dict[str, Any]], None] | None = None,
    repo: VenditePipelineRepository | None = None,
    vendite_repo: VenditeRepository | None = None,
    doc_service: DocumentGenerationService | None = None,
) -> dict[str, Any]:
    repo = repo or VenditePipelineRepository()
    vendite_repo = vendite_repo or VenditeRepository()
    doc_service = doc_service or DocumentGenerationService()

    recuperate = (
        repo.reset_stale_stampe_in_corso(stale_minuti) if stale_minuti > 0 else 0
    )

    items = repo.claim_stampe_pending(limit)

    fatto = 0
    errore = 0        # righe passate a ERRORE terminale
    riprovabili = 0   # righe rimesse a PENDING (ritenteranno al prossimo giro)
    for item in items:
        esito = _lavora_item(
            repo, vendite_repo, doc_service, item, soglia_tentativi,
        )
        if esito["esito"] == "fatto":
            fatto += 1
        elif esito["esito"] == "errore":
            errore += 1
        else:
            riprovabili += 1
        if on_item_esito is not None:
            on_item_esito(item, esito)

    return {
        "recuperate": recuperate,
        "claimate": len(items),
        "fatto": fatto,
        "errore": errore,
        "riprovabili": riprovabili,
        "soglia_tentativi": soglia_tentativi,
        "limit": limit,
    }


# Scopo: Lavora un singolo work-item della coda (render di una fattura).
#        Best-effort: qualunque errore di dominio/render viene CATTURATO e
#        registrato sulla riga (marca_stampa_errore decide ERRORE vs PENDING);
#        non propaga, così le altre righe del batch proseguono. Ritorna un dict
#        {esito: 'fatto'|'errore'|'riprovabile', ...} per il tally/console.
def _lavora_item(
    repo: VenditePipelineRepository,
    vendite_repo: VenditeRepository,
    doc_service: DocumentGenerationService,
    item: dict[str, Any],
    soglia_tentativi: int,
) -> dict[str, Any]:
    coda_id = int(item["id"])
    fattura_id = int(item["sorgente_id"])
    try:
        # Emittente autoritativo dalla fattura (la coda non lo denormalizza:
        # brief §5). None = fattura sparita/fuori-portata → errore registrato.
        entity = vendite_repo.get_fattura_for_documento_generation(fattura_id)
        if entity is None:
            stato = repo.marca_stampa_errore(
                coda_id,
                errore={
                    "code": "E_FATTURA_NON_TROVATA",
                    "message": "Fattura in coda non risolta (sparita o fuori portata).",
                    "fattura_id": fattura_id,
                },
                soglia_tentativi=soglia_tentativi,
            )
            return _esito_da_stato(stato, code="E_FATTURA_NON_TROVATA")

        # Il repo risolve la PK emittente con LEFT JOIN: fattura esistente ma
        # senza record EF (dato sporco) → errore PARLANTE sulla riga, non un
        # TypeError generico a valle.
        if entity.get("emittente_fiscale_id") is None:
            stato = repo.marca_stampa_errore(
                coda_id,
                errore={
                    "code": "E_EMITTENTE_NON_RISOLTO",
                    "message": "Emittente fiscale non risolto per la fattura in coda.",
                    "fattura_id": fattura_id,
                },
                soglia_tentativi=soglia_tentativi,
            )
            return _esito_da_stato(stato, code="E_EMITTENTE_NON_RISOLTO")

        # C-2d: numerazione backstop PRIMA del render (idempotente).
        repo.numera_fattura_backstop(fattura_id)

        # Render in contesto sistema (C-0): user=None + emittente_scope=None
        # → nessuna derivazione scope, l'emittente è input autoritativo; gira
        # sul canale BYPASSRLS (guard fail-loud lato service se non lo fosse).
        documento = doc_service.genera_documento(
            None,
            emittente_fiscale_id=int(entity["emittente_fiscale_id"]),
            sorgente_tipo_id=int(item["sorgente_tipo_id"]),
            sorgente_id=fattura_id,
            sorgente_uid=str(item["sorgente_uid"]),
            template_documento_id=item.get("template_documento_id"),
            emittente_scope=None,
        )
        repo.marca_stampa_fatto(coda_id, int(documento["id"]))
        return {"esito": "fatto", "documento_id": int(documento["id"])}

    except ServiceError as exc:
        stato = repo.marca_stampa_errore(
            coda_id,
            errore={
                "code": exc.code,
                "message": str(exc.message or exc),
                "detail": exc.detail,
            },
            soglia_tentativi=soglia_tentativi,
        )
        logger.warning(
            "stampa_coda.render_fallito coda_id=%s fattura_id=%s code=%s stato=%s",
            coda_id, fattura_id, exc.code, stato,
        )
        return _esito_da_stato(stato, code=exc.code)

    except Exception as exc:  # noqa: BLE001 — resilienza per-riga voluta
        stato = repo.marca_stampa_errore(
            coda_id,
            errore={"code": type(exc).__name__, "message": str(exc)},
            soglia_tentativi=soglia_tentativi,
        )
        logger.warning(
            "stampa_coda.render_errore_imprevisto coda_id=%s fattura_id=%s "
            "type=%s stato=%s",
            coda_id, fattura_id, type(exc).__name__, stato,
        )
        return _esito_da_stato(stato, code=type(exc).__name__)


# Scopo: Traduce lo stato risultante della coda (ERRORE terminale vs PENDING
#        riprovabile) nell'esito del tally del drainer. Confronto sulla
#        costante del repo (owner del vocabolario stati), non su letterale.
def _esito_da_stato(stato: str, *, code: str) -> dict[str, Any]:
    if stato == VenditePipelineRepository.STAMPA_STATO_ERRORE:
        return {"esito": "errore", "code": code}
    return {"esito": "riprovabile", "code": code}
