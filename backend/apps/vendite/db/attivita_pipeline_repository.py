# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB per pipeline attivita fatturabili.
# ------------------------------------------------------------


from dataclasses import dataclass
from datetime import date
import json
from typing import Any

from django.db import connection

from apps.core.services.error_manager import ErrorManager
from apps.vendite.types import AttivitaTaskRunRow

# Repository SQL: incapsula accesso DB per orchestrazione pipeline attivita fatturabili.


@dataclass(frozen=True)
class LottoAttivitaContext:
    competenza_mese: date
    utility_id: int | None
    billing_account_id: int | None
    sorgente_tipo_id: int | None
    emittente_soggetto_ruolo_id: int | None
    lock_batch_id: str | None


@dataclass(frozen=True)
class AttivitaPipelineStep:
    codice_step: str
    descrizione: str | None
    ordine: int | None


@dataclass(frozen=True)
class AttivitaTaskRunResult:
    task_run_id: int
    tentativo: int


@dataclass(frozen=True)
class AttivitaTaskPolicy:
    annullabile: bool
    resume_mode: str
    block_scope: str  # 'BRANCH' | 'GLOBAL'
    depends_on: list[Any]
    attivo: bool
    meta: dict[str, Any]


@dataclass(frozen=True)
class AttivitaSorgenteBranchPolicy:
    sorgente_tipo_id: int
    branch_code: str
    abilitata: bool
    acquisizione_mode: str
    block_scope: str  # 'BRANCH' | 'GLOBAL'
    priorita: int
    meta: dict[str, Any]


class AttivitaPipelineRepository:
    """Wrapper SQL a basso livello per l'orchestrazione pipeline attivita fatturabili."""

    DOMINIO_CODE = "ATTIVITA_FATTURABILI"

    # Scopo: Serializza esplicitamente per evitare errori adapter psycopg su dict/list.
    @staticmethod
    def _to_jsonb_param(value: Any) -> str | None:
        if value is None:
            return None
        return json.dumps(value)

    # --- Gruppo 1: Lotto management ---

    # Scopo: Risolve o crea il lotto attivita delegando al DB la logica di consistenza dominio.
    def get_or_create_lotto_attivita(
        self,
        lotto_id: int | None,
        competenza_mese: date | None,
        utility_id: int | None,
        billing_account_id: int | None,
        sorgente_tipo_id: int | None,
        lock_batch_id: str | None,
        meta: dict | None,
        emittente_soggetto_ruolo_id: int | None,
    ) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_get_or_create_lotto_attivita(
                    %s, %s, %s, %s, %s, %s::uuid, %s::jsonb, %s
                )
                """,
                [
                    lotto_id,
                    competenza_mese,
                    utility_id,
                    billing_account_id,
                    sorgente_tipo_id,
                    lock_batch_id,
                    self._to_jsonb_param(meta),
                    emittente_soggetto_ruolo_id,
                ],
            )
            row = cursor.fetchone()
            assert row is not None
        return int(row[0])

    # Scopo: Recupera stato_lotto dal DB per il lotto attivita.
    def get_lotto_attivita_stato(self, lotto_id: int) -> str | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT stato_lotto FROM vendite.attivita_fatturabili_lotti WHERE id = %s",
                [lotto_id],
            )
            row = cursor.fetchone()
        if not row:
            return None
        return row[0]

    # Scopo: Recupera stato_lotto e stato_operativo in un'unica query per l'endpoint status.
    def get_lotto_attivita_full_stato(self, lotto_id: int) -> dict | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT stato_lotto, stato_operativo
                FROM vendite.attivita_fatturabili_lotti
                WHERE id = %s
                """,
                [lotto_id],
            )
            row = cursor.fetchone()
        if not row:
            return None
        return {"stato_lotto": row[0], "stato_operativo": row[1]}

    # Scopo: Verifica se il lotto attivita e` in esecuzione basandosi su stato_lotto persistito.
    def is_lotto_attivita_in_esecuzione(self, lotto_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT (stato_lotto = 'IN_ESECUZIONE')
                FROM vendite.attivita_fatturabili_lotti
                WHERE id = %s
                """,
                [lotto_id],
            )
            row = cursor.fetchone()
        if not row:
            return False
        return bool(row[0])

    # Scopo: Aggiorna stato_lotto delegando al DB la gestione della state machine.
    def set_lotto_attivita_stato(
        self, lotto_id: int, stato_lotto: str, note: str | None = None
    ) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_set_attivita_lotto_stato(%s, %s, %s)",
                [lotto_id, stato_lotto, note],
            )

    # Scopo: Sincronizza lo stato di esecuzione del lotto attivita via funzione DB.
    def sync_attivita_stato_esecuzione(
        self, lotto_id: int, target_stato: str | None = None
    ) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_sync_attivita_stato_esecuzione(%s, %s)",
                [lotto_id, target_stato],
            )

    # Scopo: Recupera il contesto del lotto attivita dal DB.
    def get_lotto_attivita_context(self, lotto_id: int) -> LottoAttivitaContext | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT competenza_mese, utility_id, billing_account_id,
                       sorgente_tipo_id, emittente_soggetto_ruolo_id, lock_batch_id
                FROM vendite.attivita_fatturabili_lotti
                WHERE id = %s
                """,
                [lotto_id],
            )
            row = cursor.fetchone()
        if not row:
            return None
        return LottoAttivitaContext(
            competenza_mese=row[0],
            utility_id=row[1],
            billing_account_id=row[2],
            sorgente_tipo_id=row[3],
            emittente_soggetto_ruolo_id=None if row[4] is None else int(row[4]),
            lock_batch_id=row[5],
        )

    # --- Gruppo 2: Pipeline steps ---

    # Scopo: Recupera gli step pipeline attivita applicabili con fallback per utility e sorgente.
    def list_attivita_pipeline_steps(
        self,
        utility_id: int | None = None,
        sorgente_tipo_id: int | None = None,
    ) -> list[AttivitaPipelineStep]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT codice_step, descrizione, ordine
                FROM vendite.fn_list_attivita_pipeline_steps(%s, %s)
                """,
                [utility_id, sorgente_tipo_id],
            )
            rows = cursor.fetchall()
        return [
            AttivitaPipelineStep(
                codice_step=str(row[0]),
                descrizione=row[1],
                ordine=row[2],
            )
            for row in rows
        ]

    # Scopo: Recupera i task JSON dello step e normalizza il payload in lista Python.
    def get_attivita_step_processes(
        self,
        codice_step: str,
        *,
        utility_id: int | None,
        sorgente_tipo_id: int | None,
        rollback: bool,
    ) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT processi
                FROM vendite.fn_resolve_attivita_pipeline_step(%s, %s, %s, %s)
                """,
                [codice_step, utility_id, sorgente_tipo_id, rollback],
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

    # Scopo: Recupera pipeline_id risolto per lo step indicato via fn_resolve_attivita_pipeline_step.
    def get_attivita_pipeline_id_for_step(
        self,
        codice_step: str,
        *,
        utility_id: int | None,
        sorgente_tipo_id: int | None,
    ) -> int | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT pipeline_id
                FROM vendite.fn_resolve_attivita_pipeline_step(%s, %s, %s, false)
                """,
                [codice_step, utility_id, sorgente_tipo_id],
            )
            row = cursor.fetchone()
        if not row or row[0] is None:
            return None
        return int(row[0])

    # --- Gruppo 3: Sorgenti abilitate ---

    # Scopo: Restituisce le sorgenti abilitate ordinate per priorita`.
    def list_sorgenti_abilitate(
        self,
        utility_id: int | None = None,  # accettato per interface consistency, non usato in WHERE
    ) -> list[AttivitaSorgenteBranchPolicy]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT sorgente_tipo_id, branch_code, abilitata,
                       acquisizione_mode, block_scope, priorita, meta
                FROM vendite.attivita_fatturabili_sorgenti_branch_policy
                WHERE abilitata IS TRUE
                  AND attivo IS TRUE
                ORDER BY priorita, id
                """
            )
            rows = cursor.fetchall()
        result: list[AttivitaSorgenteBranchPolicy] = []
        for row in rows:
            meta_raw: Any = row[6]
            if isinstance(meta_raw, str):
                try:
                    meta_raw = json.loads(meta_raw)
                except json.JSONDecodeError:
                    meta_raw = {}
            result.append(
                AttivitaSorgenteBranchPolicy(
                    sorgente_tipo_id=int(row[0]),
                    branch_code=str(row[1]),
                    abilitata=bool(row[2]),
                    acquisizione_mode=str(row[3]),
                    block_scope=str(row[4]),
                    priorita=int(row[5]),
                    meta=meta_raw if isinstance(meta_raw, dict) else {},
                )
            )
        return result

    # --- Gruppo 4: Task registry ---

    # Scopo: Risolve l'identificativo dominio task attivo a partire dal codice richiesto.
    def get_dominio_id(self, codice: str | None = None) -> int:
        dominio_code = codice or self.DOMINIO_CODE
        ErrorManager.require(
            bool(dominio_code and str(dominio_code).strip()),
            code="E_ATTIVITA_PIPELINE",
            message="Dominio pipeline non valido.",
            detail="codice dominio obbligatorio",
            context={"codice": dominio_code},
            function_name="vendite.attivita_pipeline_repository.get_dominio_id",
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
                code="E_ATTIVITA_PIPELINE",
                message="Dominio pipeline non trovato.",
                detail=f"Dominio non trovato: {dominio_code}",
                context={"codice": dominio_code},
                function_name="vendite.attivita_pipeline_repository.get_dominio_id",
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
            code="E_ATTIVITA_PIPELINE",
            message="Task pipeline non valido.",
            detail="task_code obbligatorio",
            context={"task_code": task_code},
            function_name="vendite.attivita_pipeline_repository.get_task_handler_code",
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
                code="E_ATTIVITA_PIPELINE",
                message="Handler task non trovato.",
                detail=(
                    f"Nessun handler per task "
                    f"{task_code} (implementation_key={implementation_key})"
                ),
                context={
                    "dominio_id": dominio_id,
                    "task_code": task_code,
                    "implementation_key": implementation_key,
                },
                function_name="vendite.attivita_pipeline_repository.get_task_handler_code",
                log_to_db=True,
            )
        return str(row[0])

    # --- Gruppo 5: Task policy ---

    # Scopo: Recupera la policy task dal DB per pipeline/task/branch indicati.
    def get_attivita_task_policy(
        self,
        pipeline_id: int,
        task_code: str,
        branch_code: str = "DEFAULT",
    ) -> AttivitaTaskPolicy | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT annullabile, resume_mode, block_scope, depends_on, attivo, meta
                FROM vendite.fn_get_attivita_pipeline_task_policy(%s, %s, %s)
                """,
                [pipeline_id, task_code, branch_code],
            )
            row = cursor.fetchone()
        if not row:
            return None
        depends_on_raw: Any = row[3]
        if isinstance(depends_on_raw, str):
            try:
                depends_on_raw = json.loads(depends_on_raw)
            except json.JSONDecodeError:
                depends_on_raw = []
        meta_raw: Any = row[5]
        if isinstance(meta_raw, str):
            try:
                meta_raw = json.loads(meta_raw)
            except json.JSONDecodeError:
                meta_raw = {}
        return AttivitaTaskPolicy(
            annullabile=bool(row[0]),
            resume_mode=str(row[1]),
            block_scope=str(row[2]),
            depends_on=depends_on_raw if isinstance(depends_on_raw, list) else [],
            attivo=bool(row[4]),
            meta=meta_raw if isinstance(meta_raw, dict) else {},
        )

    # Scopo: Verifica se esiste una policy attiva per il task indicato nel pipeline dato.
    def task_policy_exists(
        self,
        pipeline_id: int,
        task_code: str,
        branch_code: str = "DEFAULT",
    ) -> bool:
        # La fn DB solleva eccezione se la policy non esiste; wrap → False.
        try:
            policy = self.get_attivita_task_policy(pipeline_id, task_code, branch_code)
            return policy is not None
        except Exception:
            return False

    # --- Gruppo 6: Task runs ---

    # Scopo: Apre un nuovo task run in stato IN_ESECUZIONE delegando al DB.
    def start_attivita_task_run(
        self,
        *,
        lotto_id: int,
        pipeline_id: int,
        task_code: str,
        branch_code: str,
        sorgente_tipo_id: int | None,
        fase: str | None,
        block_scope: str,
        depends_on: list[Any],
        meta: dict | None,
    ) -> AttivitaTaskRunResult:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT task_run_id, tentativo
                FROM vendite.fn_start_attivita_lotto_task_run(
                    %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb
                )
                """,
                [
                    lotto_id,
                    pipeline_id,
                    task_code,
                    branch_code,
                    sorgente_tipo_id,
                    fase,
                    block_scope,
                    self._to_jsonb_param(depends_on),
                    self._to_jsonb_param(meta),
                ],
            )
            row = cursor.fetchone()
        assert row is not None
        return AttivitaTaskRunResult(
            task_run_id=int(row[0]),
            tentativo=int(row[1]),
        )

    # Scopo: Chiude un task run con esito COMPLETATO delegando al DB.
    def complete_attivita_task_run(
        self, task_run_id: int, meta: dict | None = None
    ) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_complete_attivita_lotto_task_run(%s, %s::jsonb)",
                [task_run_id, self._to_jsonb_param(meta)],
            )

    # Scopo: Chiude un task run con esito ERRORE delegando al DB.
    def fail_attivita_task_run(
        self,
        task_run_id: int,
        error_code: str,
        error_message: str,
        meta: dict | None = None,
    ) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_fail_attivita_lotto_task_run(%s, %s, %s, %s::jsonb)",
                [task_run_id, error_code, error_message, self._to_jsonb_param(meta)],
            )

    # Scopo: Restituisce i task run runtime del lotto attivita per consultazione.
    def list_attivita_task_runs(
        self,
        lotto_id: int,
        *,
        branch_code: str | None = None,
        task_code: str | None = None,
        limit: int = 100,
    ) -> list[AttivitaTaskRunRow]:
        safe_limit = max(1, min(int(limit), 500))
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id, lotto_attivita_id, pipeline_id, sorgente_tipo_id,
                    branch_code, task_code, fase, tentativo, task_stato,
                    block_scope, depends_on, started_at, ended_at,
                    error_code, error_message, meta
                FROM vendite.fn_list_attivita_lotto_task_runs(%s, %s, %s)
                LIMIT %s
                """,
                [lotto_id, branch_code, task_code, safe_limit],
            )
            rows = cursor.fetchall()
        result: list[AttivitaTaskRunRow] = []
        for row in rows:
            depends_on_raw: Any = row[10]
            if isinstance(depends_on_raw, str):
                try:
                    depends_on_raw = json.loads(depends_on_raw)
                except json.JSONDecodeError:
                    depends_on_raw = []
            meta_raw: Any = row[15]
            if isinstance(meta_raw, str):
                try:
                    meta_raw = json.loads(meta_raw)
                except json.JSONDecodeError:
                    meta_raw = {}
            result.append(
                {
                    "id": int(row[0]),
                    "lotto_attivita_id": int(row[1]),
                    "pipeline_id": None if row[2] is None else int(row[2]),
                    "sorgente_tipo_id": None if row[3] is None else int(row[3]),
                    "branch_code": str(row[4]),
                    "task_code": str(row[5]),
                    "fase": row[6],
                    "tentativo": int(row[7]),
                    "task_stato": str(row[8]),
                    "block_scope": str(row[9]),
                    "depends_on": depends_on_raw if isinstance(depends_on_raw, list) else [],
                    "started_at": None if row[11] is None else row[11].isoformat(),
                    "ended_at": None if row[12] is None else row[12].isoformat(),
                    "error_code": row[13],
                    "error_message": row[14],
                    "meta": meta_raw if isinstance(meta_raw, dict) else {},
                }
            )
        return result
