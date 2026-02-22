# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB per pipeline vendite.
# ------------------------------------------------------------


from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import json
from typing import Any

from django.db import connection

from apps.core.services.error_manager import ErrorManager
from apps.core.services.value_normalizer import as_bool, empty_to_none
from apps.vendite.types import (
    LottoPipelineMeta,
    LottoSegnalazioniSummary,
    LottoTaskRunRow,
    ResetLottoDraftResult,
    ResetLottoFatturaDraftResult,
)

# Repository SQL: incapsula accesso DB per orchestrazione pipeline vendite.

@dataclass(frozen=True)
class LottoContext:
    competenza_mese: date
    tipo_doc_fiscale_id: int | None
    utility_id: int | None
    billing_account_id: int | None
    lock_batch_id: str | None
    emittente_soggetto_ruolo_id: int | None = None


@dataclass(frozen=True)
class PipelineStep:
    stato_doc_fiscale_id: int
    descrizione: str | None
    ordine: int | None


@dataclass(frozen=True)
class GroupAttivitaInput:
    attivita_id: int
    articolo_id: int
    dest_billing_account_id: int | None
    uom_id: int | None
    prezzo_unitario: Decimal | None
    iva_id: int | None
    competenza_dal: date | None
    competenza_al: date | None
    data_attivita: date | None
    visibilita_componenti: str
    calcolo_qta_padre: str
    arrotondamento_importi_dec: int
    arrotondamento_quantita_dec: int
    metodo_arrotondamento_importi: str
    metodo_arrotondamento_quantita: str


@dataclass(frozen=True)
class AttivitaDaFatturare:
    id: int
    articolo_id: int
    quantita: Decimal | None
    prezzo_unitario: Decimal | None
    uom_id: int | None
    sorgente_tipo_id: int | None
    sorgente_uid: str | None
    sorgente_riga: int | None
    articolo_descrizione: str | None


@dataclass(frozen=True)
class SdiPayloadRow:
    fattura_sdi_id: int
    fattura_id: int
    tentativo_num: int
    stato_sdi_id: int
    codice_documento: str | None
    numero_fattura: int | None
    data_fattura: date | None
    billing_account_id: int
    emittente_soggetto_ruolo_id: int
    valuta_id: int | None
    totale_a_pagare: Decimal | None


@dataclass(frozen=True)
class TaskRunResult:
    task_run_id: int
    tentativo: int


@dataclass(frozen=True)
class TaskExecutionMode:
    execution_mode: str  # RUN | SKIP | RESUME | RESET_REQUIRED
    annullabile: bool
    resume_mode: str
    last_task_stato: str | None
    last_tentativo: int | None
    policy_meta: dict[str, Any]
    run_meta: dict[str, Any]


class VenditePipelineRepository:
    """Wrapper SQL a basso livello per l'orchestrazione pipeline vendite."""

    DOMINIO_CODE = "FATTURAZIONE"

    # `fn` nei JSON task e` mantenuto come token di compatibilita` SQL legacy.
    ALLOWED_TASK_FUNCTIONS = {
        "select_attivita": "vendite.fn_select_attivita_fatturabili",
        "generate_fatture_righe": "vendite.fn_generate_fatture_righe",
        "genera_fondi_source_lotto": "vendite.fn_genera_fondi_fattura_source",
        "applica_fondi_lotto": "vendite.fn_applica_fondi_fattura",
        "ricalcola_iva_lotto": "vendite.fn_ricalcola_riepiloghi_iva_lotto",
        "prepare_sdi_payload_lotto": "vendite.fn_prepare_sdi_payload",
        "numera_fatture": "vendite.fn_numera_fattura_opz_emessa",
        "close_lotto": None,
        "reset_lotto_draft": "vendite.fn_reset_lotto_draft",
    }

    # Scopo: Gestisce `_to_jsonb_param` nel flusso applicativo del modulo.
    @staticmethod
    def _to_jsonb_param(value: LottoPipelineMeta | None) -> str | None:
        if value is None:
            return None
        # Serializza esplicitamente per evitare errori adapter psycopg su dict/list.
        return json.dumps(value)

    # Scopo: Risolve o crea il lotto di fatturazione delegando al DB la logica di consistenza dominio.
    def get_or_create_lotto(
        self,
        lotto_id: int | None,
        competenza_mese: date | None,
        tipo_doc_fiscale_id: int | None,
        utility_id: int | None,
        billing_account_id: int | None,
        emittente_soggetto_ruolo_id: int | None,
        lock_batch_id: str | None,
        meta: LottoPipelineMeta | None,
        tipo_lotto: str | None,
    ) -> int:
        # Delega al DB la risoluzione/creazione lotto per mantenere coerenza funzionale.
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_get_or_create_lotto(
                    %s, %s, %s, %s, %s, %s::uuid, %s::jsonb, %s::text, %s
                )
                """,
                [
                    lotto_id,
                    competenza_mese,
                    tipo_doc_fiscale_id,
                    utility_id,
                    billing_account_id,
                    lock_batch_id,
                    self._to_jsonb_param(meta),
                    tipo_lotto,
                    emittente_soggetto_ruolo_id,
                ],
            )
            row = cursor.fetchone()
            assert row is not None
        return int(row[0])

    # Scopo: Recupera `lotto_tipo` dal contesto applicativo o dal database.
    def get_lotto_tipo(self, lotto_id: int) -> str | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT tipo_lotto FROM vendite.fatturazione_lotti WHERE id = %s",
                [lotto_id],
            )
            row = cursor.fetchone()
        if not row:
            return None
        return row[0]

    # Scopo: Recupera `lotto_job_stato` dal contesto applicativo o dal database.
    def get_lotto_job_stato(self, lotto_id: int) -> str | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT stato_lotto FROM vendite.fatturazione_lotti WHERE id = %s",
                [lotto_id],
            )
            row = cursor.fetchone()
        if not row:
            return None
        return row[0]

    # Scopo: Determina in modo univoco se il lotto e` in errore basandosi su stato_lotto persistito.
    def is_lotto_in_errore(self, lotto_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT (stato_lotto = 'ERRORE')
                FROM vendite.fatturazione_lotti
                WHERE id = %s
                """,
                [lotto_id],
            )
            row = cursor.fetchone()
        if not row:
            return False
        return bool(row[0])

    # Scopo: Restituisce il riepilogo segnalazioni attive del lotto per severita` e sorgente (fatture/lotto).
    def get_lotto_segnalazioni_summary(self, lotto_id: int) -> LottoSegnalazioniSummary:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    fatture_critical_count,
                    fatture_warning_count,
                    lotto_critical_count,
                    lotto_warning_count,
                    lotto_info_count
                FROM vendite.fn_get_lotto_segnalazioni_summary(%s)
                """,
                [lotto_id],
            )
            row = cursor.fetchone()
        if not row:
            return {
                "fatture_critical_count": 0,
                "fatture_warning_count": 0,
                "lotto_critical_count": 0,
                "lotto_warning_count": 0,
                "lotto_info_count": 0,
            }
        return {
            "fatture_critical_count": int(row[0]),
            "fatture_warning_count": int(row[1]),
            "lotto_critical_count": int(row[2]),
            "lotto_warning_count": int(row[3]),
            "lotto_info_count": int(row[4]),
        }

    # Scopo: Restituisce i task run runtime del lotto ordinati dal più recente per consultazione API/UI.
    def list_lotto_task_runs(self, lotto_id: int, *, limit: int = 100) -> list[LottoTaskRunRow]:
        safe_limit = max(1, min(int(limit), 500))
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    lotto_id,
                    pipeline_id,
                    stato_doc_fiscale_id,
                    task_code,
                    fase,
                    tentativo,
                    task_stato,
                    started_at,
                    ended_at,
                    error_code,
                    error_message,
                    meta
                FROM vendite.fatturazione_lotti_task_runs
                WHERE lotto_id = %s
                  AND attivo IS TRUE
                ORDER BY started_at DESC, id DESC
                LIMIT %s
                """,
                [lotto_id, safe_limit],
            )
            rows = cursor.fetchall()
        result: list[LottoTaskRunRow] = []
        for row in rows:
            meta_raw = row[12]
            if isinstance(meta_raw, str):
                try:
                    meta_raw = json.loads(meta_raw)
                except json.JSONDecodeError:
                    meta_raw = {}
            result.append(
                {
                    "id": int(row[0]),
                    "lotto_id": int(row[1]),
                    "pipeline_id": None if row[2] is None else int(row[2]),
                    "stato_doc_fiscale_id": None if row[3] is None else int(row[3]),
                    "task_code": str(row[4]),
                    "fase": row[5],
                    "tentativo": int(row[6]),
                    "task_stato": str(row[7]),
                    "started_at": None if row[8] is None else row[8].isoformat(),
                    "ended_at": None if row[9] is None else row[9].isoformat(),
                    "error_code": row[10],
                    "error_message": row[11],
                    "meta": meta_raw if isinstance(meta_raw, dict) else {},
                }
            )
        return result

    # Scopo: Recupera `lotto_stato_doc_fiscale_id` dal contesto applicativo o dal database.
    def get_lotto_stato_doc_fiscale_id(self, lotto_id: int) -> int | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT stato_doc_fiscale_id
                FROM vendite.fatturazione_lotti
                WHERE id = %s
                """,
                [lotto_id],
            )
            row = cursor.fetchone()
        if not row or row[0] is None:
            return None
        return int(row[0])

    # Scopo: Risolve l'identificativo dominio task attivo a partire dal codice richiesto.
    def get_dominio_id(self, codice: str | None = None) -> int:
        dominio_code = codice or self.DOMINIO_CODE
        ErrorManager.require(
            bool(dominio_code and str(dominio_code).strip()),
            code="E_PIPELINE_DOMINIO",
            message="Dominio pipeline non valido.",
            detail="codice dominio obbligatorio",
            context={"codice": dominio_code},
            function_name="vendite.pipeline_repository.get_dominio_id",
            log_to_db=True,
        )
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id
                FROM dbops.domini_task
                WHERE codice = %s
                  AND attivo IS TRUE
                ORDER BY id
                LIMIT 1
                """,
                [dominio_code],
            )
            row = cursor.fetchone()
        if not row:
            ErrorManager.raise_error(
                code="E_PIPELINE_DOMINIO_NOT_FOUND",
                message="Dominio pipeline non trovato.",
                detail=f"Dominio non trovato: {dominio_code}",
                context={"codice": dominio_code},
                function_name="vendite.pipeline_repository.get_dominio_id",
                log_to_db=True,
            )
        return int(row[0])

    # Scopo: Risolve dal registry DB l'handler effettivo per task e implementation_key richiesti.
    def get_task_handler_code(
        self,
        *,
        task_code: str,
        implementation_key: str | None,
        dominio_code: str | None = None,
    ) -> str:
        ErrorManager.require(
            bool(task_code and str(task_code).strip()),
            code="E_PIPELINE_TASK",
            message="Task pipeline non valido.",
            detail="task_code obbligatorio",
            context={"task_code": task_code},
            function_name="vendite.pipeline_repository.get_task_handler_code",
            log_to_db=True,
        )
        dominio_id = self.get_dominio_id(dominio_code)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT handler_code
                FROM dbops.fn_get_pipeline_task_implementation(%s, %s, %s)
                """,
                [dominio_id, task_code, implementation_key],
            )
            row = cursor.fetchone()
        if not row:
            ErrorManager.raise_error(
                code="E_PIPELINE_TASK_HANDLER_NOT_FOUND",
                message="Handler task non trovato.",
                detail=(
                    "Nessun handler per task "
                    f"{task_code} (implementation_key={implementation_key})"
                ),
                context={
                    "dominio_id": dominio_id,
                    "task_code": task_code,
                    "implementation_key": implementation_key,
                },
                function_name="vendite.pipeline_repository.get_task_handler_code",
                log_to_db=True,
            )
        return str(row[0])

    # Scopo: Recupera `stato_doc_fiscale_id` dal contesto applicativo o dal database.
    def get_stato_doc_fiscale_id(self, codice: str) -> int | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id
                FROM config.stati_doc_fiscale
                WHERE codice = %s
                  AND attivo IS TRUE
                ORDER BY ordine
                LIMIT 1
                """,
                [codice],
            )
            row = cursor.fetchone()
        if not row:
            return None
        return int(row[0])

    # Scopo: Verifica se lo stato documento corrente richiede la chiusura operativa del lotto.
    def is_stato_doc_chiude_lotto(self, stato_doc_fiscale_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COALESCE(chiude_lotto, false)
                FROM config.stati_doc_fiscale
                WHERE id = %s
                  AND attivo IS TRUE
                """,
                [stato_doc_fiscale_id],
            )
            row = cursor.fetchone()
        if not row:
            return False
        return bool(row[0])

    # Scopo: Aggiorna `lotto_job_stato` con i valori richiesti dal flusso corrente.
    def set_lotto_job_stato(self, lotto_id: int, stato: str, messaggio: str) -> None:
        stato_input = (stato or "").strip().upper()
        if stato_input not in {"IN_ESECUZIONE", "COMPLETATO", "ERRORE"}:
            ErrorManager.raise_error(
                code="E_PIPELINE_STATO_LOTTO",
                message="stato_lotto non valido.",
                detail=f"stato_lotto non valido: {stato}",
                context={"lotto_id": lotto_id, "stato_lotto": stato},
                function_name="vendite.pipeline_repository.set_lotto_job_stato",
                log_to_db=True,
            )
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT stato_lotto
                FROM vendite.fatturazione_lotti
                WHERE id = %s
                FOR UPDATE
                """,
                [lotto_id],
            )
            row = cursor.fetchone()
            if not row:
                ErrorManager.raise_error(
                    code="E_PIPELINE_LOTTO_NOT_FOUND",
                    message="Lotto pipeline non trovato.",
                    detail=f"Lotto non trovato: {lotto_id}",
                    context={"lotto_id": lotto_id},
                    function_name="vendite.pipeline_repository.set_lotto_job_stato",
                    log_to_db=True,
                )
            stato_corrente = str(row[0]) if row[0] is not None else ""
            if stato_corrente == stato_input:
                return
            if stato_corrente == "IN_ESECUZIONE" and stato_input not in {"COMPLETATO", "ERRORE"}:
                ErrorManager.raise_error(
                    code="E_PIPELINE_STATO_LOTTO",
                    message="Transizione stato_lotto non ammessa.",
                    detail=f"Transizione non ammessa: {stato_corrente} -> {stato_input}",
                    context={
                        "lotto_id": lotto_id,
                        "stato_corrente": stato_corrente,
                        "stato_target": stato_input,
                    },
                    function_name="vendite.pipeline_repository.set_lotto_job_stato",
                    log_to_db=True,
                )
            if stato_corrente == "ERRORE" and stato_input != "IN_ESECUZIONE":
                ErrorManager.raise_error(
                    code="E_PIPELINE_STATO_LOTTO",
                    message="Transizione stato_lotto non ammessa.",
                    detail=f"Transizione non ammessa: {stato_corrente} -> {stato_input}",
                    context={
                        "lotto_id": lotto_id,
                        "stato_corrente": stato_corrente,
                        "stato_target": stato_input,
                    },
                    function_name="vendite.pipeline_repository.set_lotto_job_stato",
                    log_to_db=True,
                )
            if stato_corrente == "COMPLETATO" and stato_input != "IN_ESECUZIONE":
                ErrorManager.raise_error(
                    code="E_PIPELINE_STATO_LOTTO",
                    message="Transizione stato_lotto non ammessa.",
                    detail=f"Transizione non ammessa: {stato_corrente} -> {stato_input}",
                    context={
                        "lotto_id": lotto_id,
                        "stato_corrente": stato_corrente,
                        "stato_target": stato_input,
                    },
                    function_name="vendite.pipeline_repository.set_lotto_job_stato",
                    log_to_db=True,
                )
            cursor.execute(
                """
                UPDATE vendite.fatturazione_lotti
                SET stato_lotto = %s,
                    meta = CASE
                              WHEN %s IS NULL THEN meta
                              ELSE jsonb_set(
                                COALESCE(meta, '{}'::jsonb),
                                '{note_stato}',
                                to_jsonb(%s::text),
                                true
                              )
                           END,
                    data_update = now(),
                    user_update = current_user
                WHERE id = %s
                """,
                [stato_input, messaggio, messaggio, lotto_id],
            )

    # Scopo: Recupera gli step pipeline applicabili con fallback per tipo lotto, utility e tipo documento.
    def list_pipeline_steps(
        self,
        tipo_lotto: str,
        utility_id: int | None,
        tipo_doc_fiscale_id: int | None,
    ) -> list[PipelineStep]:
        # Delega al DB la risoluzione step con fallback e precedenza.
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT stato_doc_fiscale_id, descrizione, ordine
                FROM vendite.fn_list_fatturazione_pipeline_steps(%s, %s, %s)
                """,
                [tipo_lotto, utility_id, tipo_doc_fiscale_id],
            )
            rows = cursor.fetchall()
        return [
            PipelineStep(
                stato_doc_fiscale_id=int(row[0]),
                descrizione=row[1],
                ordine=row[2],
            )
            for row in rows
        ]

    # Scopo: Recupera pipeline_id risolto per lo step indicato via fn_resolve_fatturazione_pipeline_step.
    def get_pipeline_id_for_step(
        self,
        tipo_lotto: str,
        stato_doc_fiscale_id: int,
        utility_id: int | None,
        tipo_doc_fiscale_id: int | None,
    ) -> int | None:
        # Riusa fn_resolve_fatturazione_pipeline_step: pipeline_id è la prima colonna restituita.
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT pipeline_id
                FROM vendite.fn_resolve_fatturazione_pipeline_step(
                    p_tipo_lotto => %s,
                    p_stato_doc_fiscale_id => %s,
                    p_utility_id => %s,
                    p_tipo_doc_fiscale_id => %s,
                    p_rollback => false
                )
                """,
                [tipo_lotto, stato_doc_fiscale_id, utility_id, tipo_doc_fiscale_id],
            )
            row = cursor.fetchone()
        if not row or row[0] is None:
            return None
        return int(row[0])

    # Scopo: Verifica se esiste una policy attiva per il task indicato nel pipeline dato.
    def task_policy_exists(self, pipeline_id: int, task_code: str) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM vendite.fatturazione_pipeline_task_policy
                    WHERE pipeline_id = %s
                      AND task_code = %s
                      AND attivo IS TRUE
                )
                """,
                [pipeline_id, task_code],
            )
            row = cursor.fetchone()
        if not row:
            return False
        return bool(row[0])

    # Scopo: Risolve la modalità di esecuzione task (RUN/SKIP/RESUME/RESET_REQUIRED) delegando al DB.
    def resolve_lotto_task_execution_mode(
        self,
        lotto_id: int,
        pipeline_id: int,
        stato_doc_fiscale_id: int,
        task_code: str,
    ) -> TaskExecutionMode:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT execution_mode, annullabile, resume_mode,
                       last_task_stato, last_tentativo, policy_meta, run_meta
                FROM vendite.fn_resolve_lotto_task_execution_mode(%s, %s, %s, %s)
                """,
                [lotto_id, pipeline_id, stato_doc_fiscale_id, task_code],
            )
            row = cursor.fetchone()
        assert row is not None
        policy_meta: Any = row[5]
        run_meta: Any = row[6]
        if isinstance(policy_meta, str):
            try:
                policy_meta = json.loads(policy_meta)
            except json.JSONDecodeError:
                policy_meta = {}
        if isinstance(run_meta, str):
            try:
                run_meta = json.loads(run_meta)
            except json.JSONDecodeError:
                run_meta = {}
        return TaskExecutionMode(
            execution_mode=str(row[0]),
            annullabile=bool(row[1]),
            resume_mode=str(row[2]) if row[2] is not None else "",
            last_task_stato=row[3],
            last_tentativo=None if row[4] is None else int(row[4]),
            policy_meta=policy_meta if isinstance(policy_meta, dict) else {},
            run_meta=run_meta if isinstance(run_meta, dict) else {},
        )

    # Scopo: Apre un nuovo task run in stato IN_ESECUZIONE delegando al DB.
    def start_lotto_task_run(
        self,
        *,
        lotto_id: int,
        pipeline_id: int,
        stato_doc_fiscale_id: int,
        task_code: str,
        fase: str | None,
        meta: LottoPipelineMeta | None,
    ) -> TaskRunResult:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT task_run_id, tentativo
                FROM vendite.fn_start_lotto_task_run(%s, %s, %s, %s, %s, %s::jsonb)
                """,
                [
                    lotto_id,
                    pipeline_id,
                    stato_doc_fiscale_id,
                    task_code,
                    fase,
                    self._to_jsonb_param(meta),
                ],
            )
            row = cursor.fetchone()
        assert row is not None
        return TaskRunResult(
            task_run_id=int(row[0]),
            tentativo=int(row[1]),
        )

    # Scopo: Chiude un task run con esito COMPLETATO delegando al DB.
    def complete_lotto_task_run(
        self,
        task_run_id: int,
        meta: LottoPipelineMeta | None = None,
    ) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_complete_lotto_task_run(%s, %s::jsonb)",
                [task_run_id, self._to_jsonb_param(meta)],
            )

    # Scopo: Chiude un task run con esito ERRORE delegando al DB.
    def fail_lotto_task_run(
        self,
        task_run_id: int,
        error_code: str,
        error_message: str,
        meta: LottoPipelineMeta | None = None,
    ) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_fail_lotto_task_run(%s, %s, %s, %s::jsonb)",
                [task_run_id, error_code, error_message, self._to_jsonb_param(meta)],
            )

    # Scopo: Gestisce `update_lotto_stato_doc` nel flusso applicativo del modulo.
    def update_lotto_stato_doc(self, lotto_id: int, stato_doc_fiscale_id: int) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE vendite.fatturazione_lotti
                SET stato_doc_fiscale_id = %s,
                    data_update = now(),
                    user_update = current_user
                WHERE id = %s
                """,
                [stato_doc_fiscale_id, lotto_id],
            )

    # Scopo: Gestisce `close_giornaliero_lotto` nel flusso applicativo del modulo.
    def close_giornaliero_lotto(self, lotto_id: int, inviata_id: int) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_close_giornaliero_lotto(%s, %s)
                """,
                [lotto_id, inviata_id],
            )

    # Scopo: Chiude il lotto a livello operativo senza forzare transizioni stato documento.
    def close_lotto_operativo(self, lotto_id: int) -> None:
        # Chiusura operativa lotto senza vincolare lo stato documentale.
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE vendite.fatturazione_lotti
                SET stato_operativo = 'CHIUSO',
                    data_update = now(),
                    user_update = current_user
                WHERE id = %s
                """,
                [lotto_id],
            )

    # Scopo: Scrive il log di fase lotto su tabella/funzione dominio con metadati strutturati.
    def log_pipeline_fase(
        self,
        lotto_id: int,
        stato_doc_fiscale_id: int | None,
        fase: str,
        status: str,
        messaggio: str | None,
        meta: LottoPipelineMeta | None,
    ) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_log_pipeline_fase(
                    %s, %s, %s, %s, %s, %s::jsonb
                )
                """,
                [
                    lotto_id,
                    stato_doc_fiscale_id,
                    fase,
                    status,
                    messaggio,
                    self._to_jsonb_param(meta),
                ],
            )

    # Scopo: Scrive un log puntuale su singola fattura in `vendite.fatture_log`.
    def log_fattura(
        self,
        *,
        fattura_id: int,
        status: str,
        messaggio: str,
        critical: bool,
        meta: LottoPipelineMeta | None = None,
    ) -> None:
        # Inserisce un log funzionale puntuale su singola fattura.
        self._insert_fatture_log(
            fattura_id_select_sql="SELECT %s::bigint AS fattura_id",
            fattura_id_select_params=[fattura_id],
            status=status,
            messaggio=messaggio,
            meta=meta,
        )

    # Scopo: Gestisce `log_lotto_esito_fatture` nel flusso applicativo del modulo.
    def log_lotto_esito_fatture(self, lotto_id: int) -> None:
        # Deriva severita` lotto da fatture_log (C > W > I) e scrive su fatturazione_lotti_log.
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_log_lotto_esito_fatture(%s)",
                [lotto_id],
            )

    # Scopo: Scrive un log massivo su tutte le fatture collegate al lotto.
    def log_fatture_lotto(
        self,
        *,
        lotto_id: int,
        status: str,
        messaggio: str,
        meta: LottoPipelineMeta | None = None,
    ) -> None:
        # Logga un messaggio tecnico su tutte le fatture collegate al lotto.
        self._insert_fatture_log(
            fattura_id_select_sql="""
                SELECT lf.fattura_id
                FROM vendite.fatturazione_lotti_fatture lf
                WHERE lf.lotto_id = %s
            """,
            fattura_id_select_params=[lotto_id],
            status=status,
            messaggio=messaggio,
            meta=meta,
        )

    # Scopo: Inserisce righe su `vendite.fatture_log` usando una SELECT sorgente dei fattura_id.
    def _insert_fatture_log(
        self,
        *,
        fattura_id_select_sql: str,
        fattura_id_select_params: list[Any],
        status: str,
        messaggio: str,
        meta: LottoPipelineMeta | None,
    ) -> None:
        # Helper unico INSERT fatture_log; la SELECT fattura_id proviene solo da SQL interno.
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO vendite.fatture_log (
                    fattura_id,
                    data_ora,
                    messaggio,
                    status,
                    disabilitato,
                    meta
                )
                SELECT
                    src.fattura_id,
                    now(),
                    %s,
                    %s,
                    false,
                    COALESCE(%s::jsonb, '{{}}'::jsonb)
                FROM (
                    {fattura_id_select_sql}
                ) AS src
                """,
                [
                    messaggio,
                    status,
                    self._to_jsonb_param(meta),
                    *fattura_id_select_params,
                ],
            )

    # Scopo: Recupera `lotto_context` dal contesto applicativo o dal database.
    def get_lotto_context(self, lotto_id: int) -> LottoContext | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT competenza_mese,
                       tipo_doc_fiscale_id,
                       utility_id,
                       billing_account_id,
                       lock_batch_id,
                       emittente_soggetto_ruolo_id
                FROM vendite.fatturazione_lotti
                WHERE id = %s
                """,
                [lotto_id],
            )
            row = cursor.fetchone()
        if not row:
            return None
        return LottoContext(
            competenza_mese=row[0],
            tipo_doc_fiscale_id=row[1],
            utility_id=row[2],
            billing_account_id=row[3],
            lock_batch_id=row[4],
            emittente_soggetto_ruolo_id=None if row[5] is None else int(row[5]),
        )

    # Scopo: Recupera i task JSON dello step (processi o rollback) e normalizza il payload in lista Python.
    def get_step_processes(
        self,
        stato_doc_fiscale_id: int,
        *,
        tipo_lotto: str,
        utility_id: int | None,
        tipo_doc_fiscale_id: int | None,
        rollback: bool,
    ) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT processi
                FROM vendite.fn_resolve_fatturazione_pipeline_step(
                    p_tipo_lotto => %s,
                    p_stato_doc_fiscale_id => %s,
                    p_utility_id => %s,
                    p_tipo_doc_fiscale_id => %s,
                    p_rollback => %s
                )
                """,
                [
                    tipo_lotto,
                    stato_doc_fiscale_id,
                    utility_id,
                    tipo_doc_fiscale_id,
                    rollback,
                ],
            )
            row = cursor.fetchone()

        if not row:
            return []

        value = row[0]
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            # In alcuni ambienti il jsonb puo` arrivare serializzato come stringa.
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError:
                return []
            if isinstance(decoded, list):
                return decoded
            return []
        return []

    # Scopo: Gestisce `has_step_processes` nel flusso applicativo del modulo.
    def has_step_processes(
        self,
        *,
        stato_doc_fiscale_id: int,
        tipo_lotto: str,
        utility_id: int | None,
        tipo_doc_fiscale_id: int | None,
        rollback: bool,
    ) -> bool:
        return bool(
            self.get_step_processes(
                stato_doc_fiscale_id,
                tipo_lotto=tipo_lotto,
                utility_id=utility_id,
                tipo_doc_fiscale_id=tipo_doc_fiscale_id,
                rollback=rollback,
            )
        )

    # Scopo: Invoca la funzione SQL di selezione attivita fatturabili normalizzando i parametri runtime.
    def run_select_attivita_task(
        self,
        context: LottoContext,
        params: dict[str, Any],
    ) -> None:
        assert context is not None
        # Normalizza i parametri JSON prima della chiamata alla funzione SQL.
        lock = as_bool(params.get("lock"), default=False)
        data_fatturazione = empty_to_none(params.get("data_fatturazione"))
        valuta_id = empty_to_none(params.get("valuta_id"))
        # Emittente: fonte primaria e` il lotto persistito (context); i params JSON non lo sovrascrivono.
        emittente_id = context.emittente_soggetto_ruolo_id
        limit_value = empty_to_none(params.get("limit"))

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_select_attivita_fatturabili(
                    p_competenza_mese => %s,
                    p_tipo_doc_fiscale_id => %s,
                    p_lock_batch_id => %s::uuid,
                    p_lock => %s,
                    p_data_fatturazione => COALESCE(%s, CURRENT_DATE),
                    p_billing_account_id => %s,
                    p_utility_id => %s,
                    p_valuta_id => %s,
                    p_emittente_soggetto_ruolo_id => %s,
                    p_limit => %s
                )
                """,
                [
                    context.competenza_mese,
                    context.tipo_doc_fiscale_id,
                    context.lock_batch_id if lock else None,
                    lock,
                    data_fatturazione,
                    context.billing_account_id,
                    context.utility_id,
                    valuta_id,
                    emittente_id,
                    limit_value,
                ],
            )

    # Scopo: Recupera `group_attivita_input` dal contesto applicativo o dal database.
    def get_group_attivita_input(self, attivita_id: int) -> GroupAttivitaInput | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    a.id,
                    a.articolo_id,
                    a.billing_account_id AS dest_billing_account_id,
                    COALESCE(a.uom_id, art.uom_id) AS uom_id,
                    a.prezzo_unitario,
                    art.iva_id,
                    a.competenza_dal,
                    a.competenza_al,
                    a.data_attivita,
                    COALESCE(r.visibilita_componenti, 'solo_padre') AS visibilita_componenti,
                    COALESCE(r.calcolo_qta_padre, 'fissa') AS calcolo_qta_padre,
                    COALESCE(r.arrotondamento_importi_dec, 2) AS arrotondamento_importi_dec,
                    COALESCE(r.arrotondamento_quantita_dec, 3) AS arrotondamento_quantita_dec,
                    COALESCE(r.metodo_arrotondamento_importi, 'HALF_UP') AS metodo_arrotondamento_importi,
                    COALESCE(r.metodo_arrotondamento_quantita, 'HALF_UP') AS metodo_arrotondamento_quantita
                FROM vendite.attivita_fatturabili a
                JOIN catalogo.articoli art
                  ON art.id = a.articolo_id
                LEFT JOIN vendite.articolo_regole_fatturazione r
                  ON r.articolo_id = a.articolo_id
                WHERE a.id = %s
                """,
                [attivita_id],
            )
            row = cursor.fetchone()
        if not row:
            return None
        return GroupAttivitaInput(
            attivita_id=int(row[0]),
            articolo_id=int(row[1]),
            dest_billing_account_id=None if row[2] is None else int(row[2]),
            uom_id=None if row[3] is None else int(row[3]),
            prezzo_unitario=row[4],
            iva_id=None if row[5] is None else int(row[5]),
            competenza_dal=row[6],
            competenza_al=row[7],
            data_attivita=row[8],
            visibilita_componenti=row[9],
            calcolo_qta_padre=row[10],
            arrotondamento_importi_dec=int(row[11]),
            arrotondamento_quantita_dec=int(row[12]),
            metodo_arrotondamento_importi=row[13],
            metodo_arrotondamento_quantita=row[14],
        )

    # Scopo: Restituisce elenco `attivita_da_fatturare` in base ai filtri disponibili.
    def list_attivita_da_fatturare(self, lotto_id: int) -> list[AttivitaDaFatturare]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    a.id,
                    a.articolo_id,
                    a.quantita,
                    a.prezzo_unitario,
                    a.uom_id,
                    a.sorgente_tipo_id,
                    a.sorgente_uid,
                    a.sorgente_riga,
                    art.descrizione
                FROM vendite.attivita_fatturabili a
                JOIN catalogo.articoli art
                  ON art.id = a.articolo_id
                WHERE a.lock_batch_id = (
                        SELECT fl.lock_batch_id
                        FROM vendite.fatturazione_lotti fl
                        WHERE fl.id = %s
                      )
                  AND a.fatturato IS FALSE
                  AND COALESCE(a.lock_in_fatturazione, false) IS TRUE
                ORDER BY a.id
                """,
                [lotto_id],
            )
            rows = cursor.fetchall()
        return [
            AttivitaDaFatturare(
                id=int(row[0]),
                articolo_id=int(row[1]),
                quantita=row[2],
                prezzo_unitario=row[3],
                uom_id=None if row[4] is None else int(row[4]),
                sorgente_tipo_id=None if row[5] is None else int(row[5]),
                sorgente_uid=row[6],
                sorgente_riga=row[7],
                articolo_descrizione=row[8],
            )
            for row in rows
        ]

    # Scopo: Restituisce elenco `fatture_by_lotto` in base ai filtri disponibili.
    def list_fatture_by_lotto(self, lotto_id: int) -> list[int]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT f.id
                FROM vendite.fatturazione_lotti_fatture lf
                JOIN vendite.fatture f
                  ON f.id = lf.fattura_id
                WHERE lf.lotto_id = %s
                ORDER BY f.id
                """,
                [lotto_id],
            )
            rows = cursor.fetchall()
        return [int(row[0]) for row in rows]

    # Scopo: Recupera `tipo_fondo_fattura_id` dal contesto applicativo o dal database.
    def get_tipo_fondo_fattura_id(self, codice_interno: str = "F_F_ADD_ACC") -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id
                FROM vendite.tipi_fondi_fattura
                WHERE codice_interno = %s
                  AND attivo IS TRUE
                ORDER BY id
                LIMIT 1
                """,
                [codice_interno],
            )
            row = cursor.fetchone()
        if not row:
            ErrorManager.raise_error(
                code="E_TIPO_FONDO_NOT_FOUND",
                message="Tipo fondo fattura non trovato.",
                detail=f"Tipo fondo non trovato: {codice_interno}",
                context={"codice_interno": codice_interno},
                function_name="vendite.pipeline_repository.get_tipo_fondo_fattura_id",
                log_to_db=True,
            )
        return int(row[0])

    # Scopo: Restituisce lo scope minimo per fattura del lotto validando i campi obbligatori per task EMESSA.
    def list_fatture_scope_by_lotto(self, lotto_id: int) -> list[dict[str, int]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT
                  f.id AS fattura_id,
                  f.billing_account_id,
                  COALESCE(fl.utility_id, ba.utility_id) AS utility_id,
                  f.tipo_doc_fiscale_id,
                  f.emittente_soggetto_ruolo_id,
                  f.valuta_id
                FROM vendite.fatturazione_lotti_fatture lf
                JOIN vendite.fatture f
                  ON f.id = lf.fattura_id
                JOIN vendite.fatturazione_lotti fl
                  ON fl.id = lf.lotto_id
                LEFT JOIN anagrafiche.billing_account ba
                  ON ba.id = f.billing_account_id
                WHERE lf.lotto_id = %s
                ORDER BY f.id
                """,
                [lotto_id],
            )
            rows = cursor.fetchall()
        scopes: list[dict[str, int]] = []
        for row in rows:
            if (
                row[0] is None
                or row[1] is None
                or row[2] is None
                or row[3] is None
                or row[4] is None
                or row[5] is None
            ):
                ErrorManager.raise_error(
                    code="E_PIPELINE_SCOPE_INCOMPLETE",
                    message="Scope fattura incompleto per task EMESSA.",
                    detail=(
                        "Dati mancanti su fattura lotto: utility/tipo_doc/"
                        "emittente/valuta obbligatori"
                    ),
                    context={
                        "lotto_id": lotto_id,
                        "fattura_id": row[0],
                        "billing_account_id": row[1],
                        "utility_id": row[2],
                        "tipo_doc_fiscale_id": row[3],
                        "emittente_soggetto_ruolo_id": row[4],
                        "valuta_id": row[5],
                    },
                    function_name="vendite.pipeline_repository.list_fatture_scope_by_lotto",
                    log_to_db=True,
                )
            scopes.append(
                {
                    "fattura_id": int(row[0]),
                    "billing_account_id": int(row[1]),
                    "utility_id": int(row[2]),
                    "tipo_doc_fiscale_id": int(row[3]),
                    "emittente_soggetto_ruolo_id": int(row[4]),
                    "valuta_id": int(row[5]),
                }
            )
        return scopes

    # Scopo: Gestisce generazione fondi source per ogni scope fattura del lotto
    def run_genera_fondi_source_lotto_task(
        self,
        *,
        lotto_id: int,
        tipo_fondo_codice_interno: str = "F_F_ADD_ACC",
    ) -> None:
        tipo_fondo_id = self.get_tipo_fondo_fattura_id(tipo_fondo_codice_interno)
        for scope in self.list_fatture_scope_by_lotto(lotto_id):
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT vendite.fn_genera_fondi_fattura_source(
                      %s, %s, %s, %s, %s, %s
                    )
                    """,
                    [
                        scope["billing_account_id"],
                        scope["utility_id"],
                        scope["tipo_doc_fiscale_id"],
                        scope["emittente_soggetto_ruolo_id"],
                        scope["valuta_id"],
                        tipo_fondo_id,
                    ],
                )

    # Scopo: Gestisce applicazione fondi per ogni scope fattura del lotto
    def run_applica_fondi_lotto_task(
        self,
        *,
        lotto_id: int,
        tipo_fondo_codice_interno: str = "F_F_ADD_ACC",
    ) -> None:
        tipo_fondo_id = self.get_tipo_fondo_fattura_id(tipo_fondo_codice_interno)
        for scope in self.list_fatture_scope_by_lotto(lotto_id):
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT vendite.fn_applica_fondi_fattura(
                      %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    [
                        scope["billing_account_id"],
                        scope["utility_id"],
                        scope["tipo_doc_fiscale_id"],
                        scope["emittente_soggetto_ruolo_id"],
                        scope["valuta_id"],
                        scope["fattura_id"],
                        tipo_fondo_id,
                    ],
                )

    # Scopo: Avvia il ricalcolo IVA del lotto con aggiornamento riepiloghi/totali via funzione SQL.
    def run_ricalcola_iva_lotto_task(
        self,
        *,
        lotto_id: int,
        batch_size: int = 1000,
    ) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM vendite.fn_ricalcola_riepiloghi_iva_lotto(%s, %s)
                """,
                [lotto_id, batch_size],
            )

    # Scopo: Prepara e restituisce il dataset SDI del lotto mappato in oggetti tipizzati.
    def run_prepare_sdi_payload_lotto_task(
        self,
        *,
        lotto_id: int,
        stato_sdi_codice_interno: str = "DA_INVIARE",
        force_new_tentativo: bool = False,
    ) -> list[SdiPayloadRow]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM vendite.fn_prepare_sdi_payload(%s, %s, %s)
                """,
                [lotto_id, stato_sdi_codice_interno, force_new_tentativo],
            )
            rows = cursor.fetchall()
        # Il payload viene preparato lato DB e qui reso disponibile all'applicazione.
        return [
            SdiPayloadRow(
                fattura_sdi_id=int(row[0]),
                fattura_id=int(row[1]),
                tentativo_num=int(row[2]),
                stato_sdi_id=int(row[3]),
                codice_documento=row[4],
                numero_fattura=None if row[5] is None else int(row[5]),
                data_fattura=row[6],
                billing_account_id=int(row[7]),
                emittente_soggetto_ruolo_id=int(row[8]),
                valuta_id=None if row[9] is None else int(row[9]),
                totale_a_pagare=row[10],
            )
            for row in rows
        ]

    # Scopo: Gestisce `numera_fattura_opz_emessa` nel flusso applicativo del modulo.
    def numera_fattura_opz_emessa(self, fattura_id: int) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_numera_fattura_opz_emessa(%s)",
                [fattura_id],
            )

    # Scopo: Gestisce `sync_lotto_fatture_stato` nel flusso applicativo del modulo.
    def sync_lotto_fatture_stato(
        self,
        *,
        lotto_id: int,
        stato_doc_fiscale_id: int | None = None,
    ) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_sync_lotto_fatture_stato(%s, %s)",
                [lotto_id, stato_doc_fiscale_id],
            )

    # Scopo: Recupera `or_create_fattura_header` dal contesto applicativo o dal database.
    def get_or_create_fattura_header(self, lotto_id: int, attivita_id: int) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_get_or_create_fattura_header(%s, %s)",
                [lotto_id, attivita_id],
            )
            row = cursor.fetchone()
            assert row is not None
        return int(row[0])

    # Scopo: Gestisce `build_fattura_key` nel flusso applicativo del modulo.
    def build_fattura_key(self, attivita_id: int) -> dict[str, object]:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_build_fattura_key(%s)",
                [attivita_id],
            )
            row = cursor.fetchone()
            assert row is not None
        return row[0]

    # Scopo: Gestisce `reset_lotto_draft` nel flusso applicativo del modulo.
    def reset_lotto_draft(self, lotto_id: int) -> ResetLottoDraftResult:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT updated_lotti, updated_attivita, deleted_fatture, deleted_righe "
                "FROM vendite.fn_reset_lotto_draft(%s)",
                [lotto_id],
            )
            row = cursor.fetchone()
            assert row is not None
        return {
            "updated_lotti": int(row[0]),
            "updated_attivita": int(row[1]),
            "deleted_fatture": int(row[2]),
            "deleted_righe": int(row[3]),
        }

    # Scopo: Gestisce `reset_lotto_fattura_draft` nel flusso applicativo del modulo.
    def reset_lotto_fattura_draft(
        self,
        lotto_id: int,
        fattura_id: int,
    ) -> ResetLottoFatturaDraftResult:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT updated_attivita, deleted_fatture, deleted_righe "
                "FROM vendite.fn_reset_lotto_fattura_draft(%s, %s)",
                [lotto_id, fattura_id],
            )
            row = cursor.fetchone()
            assert row is not None
        return {
            "updated_attivita": int(row[0]),
            "deleted_fatture": int(row[1]),
            "deleted_righe": int(row[2]),
        }

    # Scopo: Recupera `next_fattura_riga_nr` dal contesto applicativo o dal database.
    def get_next_fattura_riga_nr(self, fattura_id: int) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COALESCE(MAX(riga_nr), 0) + 1
                FROM vendite.fatture_righe
                WHERE fattura_id = %s
                """,
                [fattura_id],
            )
            row = cursor.fetchone()
            assert row is not None
        return int(row[0])

    # Scopo: Gestisce `insert_fattura_riga` nel flusso applicativo del modulo.
    def insert_fattura_riga(
        self,
        *,
        fattura_id: int,
        riga_nr: int,
        articolo_id: int,
        descrizione: str | None,
        uom_id: int | None,
        qta: Decimal | None,
        prezzo_unitario: Decimal | None,
        iva_id: int | None,
        dest_billing_account_id: int,
        sorgente_tipo_id: int | None,
        sorgente_uid: str | None,
        sorgente_riga: int | None,
        meta: LottoPipelineMeta | None,
    ) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO vendite.fatture_righe (
                    fattura_id,
                    riga_nr,
                    articolo_id,
                    descrizione,
                    uom_id,
                    qta,
                    prezzo_unitario,
                    iva_id,
                    dest_billing_account_id,
                    sorgente_tipo_id,
                    sorgente_uid,
                    sorgente_riga,
                    meta
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                RETURNING id
                """,
                [
                    fattura_id,
                    riga_nr,
                    articolo_id,
                    descrizione,
                    uom_id,
                    qta,
                    prezzo_unitario,
                    iva_id,
                    dest_billing_account_id,
                    sorgente_tipo_id,
                    sorgente_uid,
                    sorgente_riga,
                    self._to_jsonb_param(meta),
                ],
            )
            row = cursor.fetchone()
            assert row is not None
        return int(row[0])

    # Scopo: Gestisce `mark_attivita_fatturata` nel flusso applicativo del modulo.
    def mark_attivita_fatturata(self, attivita_id: int, fattura_riga_id: int) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE vendite.attivita_fatturabili
                SET fattura_riga_id = %s,
                    fatturato = TRUE,
                    data_update = now(),
                    user_update = current_user
                WHERE id = %s
                """,
                [fattura_riga_id, attivita_id],
            )
