# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per accesso in lettura a maintenance.job_run_log
#        (tracciamento esecuzioni job pgAgent).
# ------------------------------------------------------------

from django.db import connection

from apps.core.types import JobRunLogRow


class MaintenanceRepository:
    """Repository per job_run_log e funzioni maintenance."""

    # Scopo: Restituisce la lista delle esecuzioni job con filtri opzionali su
    # jobname, esito (ok), intervallo temporale. Ordinamento cronologico decrescente.
    # Perimetro: sola lettura su maintenance.job_run_log.
    def list_job_runs(
        self,
        *,
        jobname: str | None = None,
        ok: bool | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[JobRunLogRow], int]:
        search_pattern = f"%{search.strip()}%" if search and search.strip() else None
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, jobname, stepname,
                       started_at::text, ended_at::text,
                       ok, rows_affected, message,
                       error_code, error_detail,
                       agent_host, run_uuid::text,
                       COUNT(*) OVER () AS total_count
                  FROM maintenance.job_run_log
                 WHERE (%s::text IS NULL OR jobname = %s)
                   AND (%s::boolean IS NULL OR ok = %s)
                   AND (%s::text IS NULL OR started_at >= %s::timestamptz)
                   AND (%s::text IS NULL OR started_at <= %s::timestamptz + interval '1 day')
                   AND (%s::text IS NULL
                        OR jobname ILIKE %s
                        OR stepname ILIKE %s
                        OR message ILIKE %s)
                 ORDER BY started_at DESC, id DESC
                 LIMIT %s OFFSET %s
                """,
                [
                    jobname, jobname,
                    ok, ok,
                    date_from, date_from,
                    date_to, date_to,
                    search_pattern, search_pattern, search_pattern, search_pattern,
                    limit, offset,
                ],
            )
            rows = cursor.fetchall()

        if not rows:
            return [], 0

        total_count: int = rows[0][12]
        results: list[JobRunLogRow] = [
            JobRunLogRow(
                id=r[0], jobname=r[1], stepname=r[2],
                started_at=r[3], ended_at=r[4],
                ok=r[5], rows_affected=r[6], message=r[7],
                error_code=r[8], error_detail=r[9],
                agent_host=r[10], run_uuid=r[11],
            )
            for r in rows
        ]
        return results, total_count

    # Scopo: Restituisce la lista dei jobname distinti con conteggio esecuzioni e ultimo esito.
    # Utile per dashboard riepilogativa dei job schedulati.
    def list_job_summary(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH summary AS (
                    SELECT jobname,
                           COUNT(*) AS total_runs,
                           COUNT(*) FILTER (WHERE ok = true) AS ok_count,
                           COUNT(*) FILTER (WHERE ok = false) AS fail_count,
                           MAX(started_at) AS last_run_at,
                           (ARRAY_AGG(ok ORDER BY started_at DESC))[1] AS last_ok
                      FROM maintenance.job_run_log
                     GROUP BY jobname
                )
                SELECT jobname, total_runs, ok_count, fail_count,
                       last_run_at::text, last_ok,
                       COUNT(*) OVER () AS total_count
                  FROM summary
                 ORDER BY last_run_at DESC NULLS LAST, jobname
                 LIMIT %s OFFSET %s
                """,
                [limit, offset],
            )
            rows = cursor.fetchall()

        if not rows:
            return [], 0

        total_count: int = rows[0][6]
        results = [
            {
                "jobname": r[0],
                "total_runs": r[1],
                "ok_count": r[2],
                "fail_count": r[3],
                "last_run_at": r[4],
                "last_ok": r[5],
            }
            for r in rows
        ]
        return results, total_count
