# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Routing unificato errori pipeline vendite (scope LOTTO/FATTURA).
# ------------------------------------------------------------


from typing import Any, Literal

from apps.core.services.error_manager import ErrorManager
from apps.vendite.db.pipeline_repository import VenditePipelineRepository

# Contratto unico errori applicativi pipeline:
# - scope LOTTO/FATTURA
# - severity I/W/C
# - code stabile
# - ids dominio + context/meta

ErrorScope = Literal["LOTTO", "FATTURA"]
ErrorSeverity = Literal["I", "W", "C"]


class PipelineErrorLogger:
    """Logger unificato per errori funzionali pipeline vendite."""

    # Scopo: Inizializza la istanza.
    def __init__(self, repository: VenditePipelineRepository | None = None) -> None:
        self.repository = repository or VenditePipelineRepository()

    # Scopo: Gestisce `log_error` nel flusso applicativo del modulo.
    def log_error(
        self,
        *,
        scope: ErrorScope,
        severity: ErrorSeverity,
        code: str,
        message: str,
        detail: str | None = None,
        lotto_id: int | None = None,
        fattura_id: int | None = None,
        stato_doc_fiscale_id: int | None = None,
        context: dict[str, Any] | None = None,
        function_name: str = "vendite.pipeline_error_logger.log_error",
        gruppo_key: str | None = None,
        commessa_id: int | None = None,
    ) -> None:
        # ⭐ `commessa_id` — DI QUALE COMMESSA parla la segnalazione di LOTTO
        #    (V-7-bis, brief-db-sorgente-documento-e-riga §8.23): la dichiara chi
        #    la solleva, come la `gruppo_key`. ⛔ Non si ricava dal `context`:
        #    il JSON non ha contratto, la colonna si'. Vale solo per
        #    `scope="LOTTO"`, come la `gruppo_key`.
        # ⭐ `gruppo_key` — DI QUALE DOCUMENTO parla la segnalazione di LOTTO
        #    (brief-db-uscita-documento-dal-giro §6.1). `None` = e' del GIRO, ed
        #    e' il default che dice il vero: chi non lo dichiara sta parlando del
        #    giro, e una segnalazione del giro deve fermare il giro.
        # ⚠️ Vale solo per `scope="LOTTO"`: sulle FATTURE il proprietario e' gia'
        #    la fattura, e la colonna non esiste.
        # Non inferire dal testo: scope e severity sono espliciti.
        #
        # ⛔ `error_code` e NON `code`, ed e' una lezione gia' pagata una volta.
        #    La chiave del codice su una riga di log e' `error_code`: la scrivono
        #    cosi' le funzioni DB, la dichiara cosi' il seed della lista delle
        #    segnalazioni come `campo_sorgente`, e `marca_fattura_in_errore` ha
        #    lo stesso commento dal giorno in cui il difetto emerse su
        #    `fatture_log`. Qui era rimasta `code`, cioe' la stessa cosa scritta
        #    in due modi da due scrittori.
        # 🔴 Misurato dal team DB il 2026-08-24: su `fatturazione_lotti_log` le
        #    righe con `code` erano **17 su 588, TUTTE di livello C** — il
        #    codice spariva a video proprio sulle critiche, dove serve di piu'.
        #    Nessuno se n'era accorto perche' il percorso DB funziona, quindi il
        #    meccanismo *sembrava* a posto: e' il modo peggiore di sbagliare.
        # ⚠️ Il lettore ha un `COALESCE` sulle due chiavi (regge le 17 righe
        #    storiche), ma quello e' un rattoppo sul LETTORE: il rimedio e'
        #    questa riga. Le righe vecchie restano leggibili, le nuove sono
        #    giuste, e non serve nessun backfill.
        meta: dict[str, Any] = {
            "scope": scope,
            "severity": severity,
            "error_code": code,
            "detail": detail,
            "context": context or {},
            "function_name": function_name,
        }
        if lotto_id is not None:
            meta["lotto_id"] = lotto_id
        if fattura_id is not None:
            meta["fattura_id"] = fattura_id
        if stato_doc_fiscale_id is not None:
            meta["stato_doc_fiscale_id"] = stato_doc_fiscale_id

        # Sempre log tecnico centralizzato (best effort).
        ErrorManager.log_error_only(
            code=code,
            context=meta,
            area="backend",
            function_name=function_name,
        )

        if scope == "LOTTO":
            if lotto_id is None:
                return
            self.repository.log_pipeline_fase(
                lotto_id=lotto_id,
                stato_doc_fiscale_id=stato_doc_fiscale_id,
                fase="Errore pipeline",
                status=severity,
                messaggio=message,
                meta=meta,
                gruppo_key=gruppo_key,
                commessa_id=commessa_id,
            )
            return

        if scope == "FATTURA":
            if fattura_id is None:
                return
            self.repository.log_fattura(
                fattura_id=fattura_id,
                status=severity,
                messaggio=message,
                critical=severity == "C",
                meta=meta,
            )
