# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Handler del job `FATTURAZIONE_NUMERA` (coda lavori generica, C-4): la
#        numerazione di PERIMETRO — «Rendi definitive competenza M» — sui lotti
#        EMESSA di un mese di competenza. Gemello di `fatturazione_giro_handler`
#        (C-3) per il verbo numerazione. Registrato nel registry handler
#        (`handler_code = fatturazione_numera_default`, dal seed DB) al boot di
#        `VenditeConfig.ready()`.
#
#        Contesto d'esecuzione: il drainer lo invoca DENTRO
#        `operator_identity_context` (run_as=OPERATORE) → RLS ATTIVA con
#        l'identità dell'operatore che ha accodato (5 GUC, stessa risoluzione del
#        web). La discovery dei lotti EMESSA è quindi **scoped all'operatore via
#        RLS**; la numerazione per-lotto riusa il core single-lotto
#        `pipeline_service.numera_lotto` (I-1: nessuna seconda implementazione).
#
#        Gate fiscale I-7: è un atto SEPARATO dalla fatturazione («Fattura» ferma
#        a EMESSA; qui si numera). Best-effort per-lotto: un lotto in errore non
#        blocca gli altri; l'esito strutturato diventa il `result` del job.
#        Idempotente per costruzione: la discovery ritorna solo i lotti ancora
#        EMESSA → un retry non ri-numera quelli già passati a DEFINITIVA.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any

from apps.core.services.error_manager import ErrorManager
from apps.vendite.services._fatturazione_job_helpers import parse_competenza_mese

logger = logging.getLogger(__name__)

# handler_code seedato in dbops.coda_lavori_tipi per il tipo FATTURAZIONE_NUMERA.
HANDLER_CODE = "fatturazione_numera_default"

# Codice errore per payload di numerazione malformato (finisce in
# `coda.ultimo_errore`; non è una risposta HTTP → non va in error_policies).
E_NUMERA_PAYLOAD = "E_FATTURAZIONE_NUMERA_PAYLOAD"


# Scopo: Esegue la numerazione di perimetro. `payload`: `{competenza_mese: ISO}`.
#        `scope`: catturato all'enqueue (`{auth_user_id, username, identita_id,
#        emittente_ids}`) — l'identità è già impostata dal drainer
#        (operator_identity_context); qui `auth_user_id` va al core single-lotto
#        come defense-in-depth applicativa (oltre alla RLS). Ritorna l'esito
#        compatto (contatori + dettaglio dei soli falliti) come `result` del job.
def fatturazione_numera_handler(
    payload: dict[str, Any], *, scope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    competenza = parse_competenza_mese(
        payload.get("competenza_mese"), error_code=E_NUMERA_PAYLOAD,
    )
    auth_user_id = (scope or {}).get("auth_user_id")

    # Import locali: evitano di caricare la catena pipeline al boot del modulo
    # (registrato in ready()); il core numera è l'unico punto di verità (I-1).
    from apps.vendite.db.pipeline_repository import VenditePipelineRepository
    from apps.vendite.db.vendite_repository import VenditeRepository
    from apps.vendite.services import pipeline_service

    # Gate fiscale: risoluzione+guard dell'id EMESSA nel service layer (non nel
    # repo). Config rotta → fail-loud, non 0 lotti silenziosi.
    emessa_id = VenditePipelineRepository().get_stato_doc_fiscale_id("EMESSA")
    ErrorManager.require(
        emessa_id is not None,
        code="E_PIPELINE_VALIDATION",
        message="Stato EMESSA non configurato in config.stati_doc_fiscale.",
    )
    assert emessa_id is not None

    lotti = VenditeRepository().list_lotti_numerabili(
        competenza_mese=competenza, stato_doc_fiscale_id=emessa_id,
    )

    # `numerato` = transizione DEFINITIVA VERIFICATA sull'esito, non «nessuna
    # eccezione»: un lotto legacy la cui pipeline si ferma senza step (es.
    # emesso pre-G1, motivo_stop parlante) NON è numerato — contarlo tale
    # nasconderebbe fatture rimaste senza numero (smoke C-9, 2026-07-22:
    # lotti 106/107 EMESSA con fatture DRAFT «numerati» due volte no-op).
    definitiva_id = VenditePipelineRepository().get_stato_doc_fiscale_id(
        "DEFINITIVA",
    )
    ErrorManager.require(
        definitiva_id is not None,
        code="E_PIPELINE_VALIDATION",
        message="Stato DEFINITIVA non configurato in config.stati_doc_fiscale.",
    )
    numerati = 0
    saltati_dett: list[dict[str, Any]] = []
    falliti_dett: list[dict[str, Any]] = []
    for lotto in lotti:
        try:
            # Riusa il core single-lotto: gate EMESSA (I-7) + step DEFINITIVA
            # (numera + accoda stampa). Idempotente/resume-safe (C-2d).
            esito = pipeline_service.numera_lotto(
                lotto_id=lotto["id"], auth_user_id=auth_user_id,
            )
            if esito.get("stato_doc_fiscale_id") == definitiva_id:
                numerati += 1
            else:
                saltati_dett.append({
                    "lotto_id": lotto["id"], "codice": lotto["codice"],
                    "motivo_stop": esito.get("motivo_stop"),
                })
                logger.warning(
                    "fatturazione_numera.lotto_non_transitato lotto_id=%s "
                    "codice=%s motivo_stop=%s",
                    lotto["id"], lotto["codice"], esito.get("motivo_stop"),
                )
        except Exception as exc:  # noqa: BLE001 — resilienza per-lotto voluta
            code = getattr(exc, "code", type(exc).__name__)
            falliti_dett.append(
                {"lotto_id": lotto["id"], "codice": lotto["codice"], "code": code},
            )
            logger.warning(
                "fatturazione_numera.lotto_fallito lotto_id=%s codice=%s code=%s",
                lotto["id"], lotto["codice"], code,
            )

    return {
        "competenza": competenza.isoformat(),
        "lotti": len(lotti),
        "numerati": numerati,
        "saltati": len(saltati_dett),
        "falliti": len(falliti_dett),
        # Solo saltati/falliti (pochi, per mese): utili al FE per il toast.
        "saltati_dett": saltati_dett,
        "falliti_dett": falliti_dett,
    }


# Scopo: Registra l'handler nel registry della coda. Chiamata da
#        `VenditeConfig.ready()` (import del modulo). Dispatch controllato:
#        `dbops.coda_lavori_tipi.handler_code` → questa funzione.
def register() -> None:
    from apps.core.services.coda_lavori.handler_registry import register_handler
    register_handler(HANDLER_CODE, fatturazione_numera_handler)
