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
class AttivitaTaskRunResult:
    task_run_id: int
    tentativo: int


class AttivitaPipelineRepository:
    """Wrapper SQL a basso livello per l'orchestrazione pipeline attivita fatturabili."""

    DOMINIO_CODE = "ATTIVITA_FATTURABILI"

    # Scopo: Serializza esplicitamente per evitare errori adapter psycopg su dict/list.
    @staticmethod
    def _to_jsonb_param(value: Any) -> str | None:
        if value is None:
            return None
        return json.dumps(value)

    # Scopo: Decodifica un valore JSONB che puo` arrivare come list/dict o come stringa serializzata.
    @staticmethod
    def _decode_jsonb(value: Any, default: Any) -> Any:
        if isinstance(value, (list, dict)):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        return default

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

    # Scopo: Recupera in un unico round-trip stato_lotto, stato_operativo e flag is_in_esecuzione.
    def get_lotto_attivita_info(self, lotto_id: int) -> dict | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT stato_lotto, stato_operativo, is_in_esecuzione "
                "FROM vendite.fn_get_attivita_lotto_info(%s)",
                [lotto_id],
            )
            row = cursor.fetchone()
        if not row:
            return None
        return {
            "stato_lotto": row[0],
            "stato_operativo": row[1],
            "is_in_esecuzione": bool(row[2]),
        }

    # Scopo: Recupera stato_lotto dal DB per il lotto attivita.
    def get_lotto_attivita_stato(self, lotto_id: int) -> str | None:
        info = self.get_lotto_attivita_info(lotto_id)
        return info["stato_lotto"] if info else None

    # Scopo: Recupera stato_lotto e stato_operativo per l'endpoint status.
    def get_lotto_attivita_full_stato(self, lotto_id: int) -> dict | None:
        info = self.get_lotto_attivita_info(lotto_id)
        if not info:
            return None
        return {"stato_lotto": info["stato_lotto"], "stato_operativo": info["stato_operativo"]}

    # Scopo: Verifica se il lotto attivita e` in esecuzione.
    def is_lotto_attivita_in_esecuzione(self, lotto_id: int) -> bool:
        info = self.get_lotto_attivita_info(lotto_id)
        return info["is_in_esecuzione"] if info else False

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

    # --- Gruppo 2: Task runs ---

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
            depends_on_raw: Any = self._decode_jsonb(row[10], [])
            meta_raw: Any = self._decode_jsonb(row[15], {})
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

    # Scopo: Restituisce contatori task run aggregati per branch_code e task_stato via funzione DB.
    def get_attivita_branch_summary(self, lotto_id: int) -> dict[str, dict[str, int]]:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT branch_code, task_stato, cnt "
                "FROM vendite.fn_get_attivita_branch_summary(%s)",
                [lotto_id],
            )
            rows = cursor.fetchall()
        summary: dict[str, dict[str, int]] = {}
        for row in rows:
            branch = str(row[0])
            stato = str(row[1])
            cnt = int(row[2])
            if branch not in summary:
                summary[branch] = {}
            summary[branch][stato] = cnt
        return summary
