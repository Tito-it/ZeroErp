# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per accesso in lettura a maintenance.job_run_log
#        (tracciamento esecuzioni job pgAgent).
# ------------------------------------------------------------

from typing import Any

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

    # Scopo: Liveness dei worker schedulati (badge UI code, BE-4): per ogni
    #        jobname ritorna ultimo run, esito dell'ultimo run e flag
    #        `attivo` = ultimo run entro `soglia_minuti` (confronto in SQL col
    #        clock DB — nessun parsing timestamp in Python, tz-safe). Jobname
    #        MAI girati non compaiono nel dict (il caller li tratta come
    #        "worker giù"). Sola lettura su maintenance.job_run_log.
    #
    # ⭐ DUE CHIAVI, UNA DOMANDA (2026-09-10). Si chiede per `jobnames` — il caso
    #    dei due drainer, dove il jobname È il codice del processo — oppure per
    #    `processo_codice`, che è la chiave ONESTA (FK dura verso
    #    `dbops.processi`) e serve ai processi con PIÙ CORSIE: quelli si
    #    registrano come `<codice>:<corsia>`, quindi chiederli per nome
    #    vorrebbe dire COMPORRE quei nomi in una seconda sede — e il giorno in
    #    cui la forma cambia il lettore guarderebbe nomi che non esistono,
    #    rispondendo «mai girato» invece di «non lo so».
    # ⚠️ È la risposta alla domanda che `coda_lavori/gestione_service` dichiara
    #    aperta: «dove jobname e processo non coincidono, la liveness non si fa
    #    da qui». Adesso si fa, dall'altra chiave.
    # ⛔ Esattamente UNA delle due, e mai nessuna: senza filtro questa query
    #    leggerebbe il giornale INTERO e risponderebbe la liveness di tutto —
    #    un errore che non fallisce, restituisce solo la cosa sbagliata.
    # ⭐ `ok` ha TRE facce — true, false, NULL = corsa ancora aperta — e
    #    `last_ok` risponde per l'ultima corsa CONCLUSA (`ended_at IS NOT
    #    NULL`), non per la riga piu' recente. Fino al 2026-09-14 prendeva la
    #    riga piu' recente: mentre il digest componeva la mail, per la PROPRIA
    #    corsia quella riga era la corsa in esecuzione (ok NULL), e la mail la
    #    chiamava «FALLITA» — con `job_run_log.ok = true` scritto mezzo minuto
    #    dopo. `last_run_at` e `attivo` restano sulla riga piu' recente: una
    #    corsa aperta e' un segno di vita legittimo. `last_ok` e' NULL solo se
    #    nessuna corsa e' mai stata conclusa, e chi lo rende deve dirlo.
    def job_liveness(
        self,
        jobnames: list[str] | None = None,
        *,
        soglia_minuti: int,
        processo_codice: str | None = None,
    ) -> dict[str, dict]:
        if (jobnames is None) == (processo_codice is None):
            raise ValueError(
                "job_liveness: si chiede per `jobnames` OPPURE per "
                "`processo_codice`, mai per entrambi e mai per nessuno"
            )
        if jobnames is not None and not jobnames:
            return {}
        filtro, valore = (
            ("jobname = ANY(%s)", list(jobnames))
            if jobnames is not None
            else ("processo_codice = %s", processo_codice)
        )
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT jobname,
                       MAX(started_at) AS last_run_at,
                       MAX(started_at) > now() - make_interval(mins => %s)
                           AS attivo,
                       (ARRAY_AGG(ok ORDER BY started_at DESC)
                            FILTER (WHERE ended_at IS NOT NULL))[1] AS last_ok
                  FROM maintenance.job_run_log
                 WHERE {filtro}
                 GROUP BY jobname
                """,  # noqa: S608 — due frammenti costanti, il valore è parametro
                [int(soglia_minuti), valore],
            )
            rows = cursor.fetchall()
        return {
            str(r[0]): {
                # ISO-8601 vero (datetime.isoformat: 'T' + offset ±HH:MM), non
                # il ::text di PG ("YYYY-MM-DD ...+02"): quel formato non è
                # parsabile da Date() su tutti i browser (Safari) e da quando
                # il FE lo MOSTRA (CodaWorkerStato) non basta più che sia
                # "abbastanza vero" per un confronto lato server.
                "last_run_at": r[1].isoformat() if r[1] else None,
                "attivo": bool(r[2]),
                "last_ok": r[3],
            }
            for r in rows
        }

    # Scopo: Restituisce la lista dei jobname distinti con conteggio esecuzioni e ultimo esito.
    # Utile per dashboard riepilogativa dei job schedulati.
    #
    # Filtri OPZIONALI (default: nessuno → comportamento storico invariato):
    #  - `jobname_prefix`: tiene solo i job il cui nome inizia col prefisso
    #    (es. 'run_fatturazione_batch' = le corsie di fatturazione, escludendo
    #    i worker di drenaggio code). Filtro SQL e non post-filtro Python:
    #    altrimenti il `LIMIT` taglierebbe PRIMA di scartare i job non voluti.
    #  - `meta_month_equals`: `(chiave, 'YYYY-MM-01')` — tiene i run ATTRIBUITI
    #    a quel mese, applicato PRIMA del GROUP BY (i conteggi risultano quindi
    #    relativi ai soli run che matchano). L'attribuzione è:
    #        COALESCE(meta ->> chiave, mese di `started_at`)
    #    cioè il mese DICHIARATO dal run se c'è, altrimenti quello in cui il run
    #    è stato ESEGUITO.
    #    Il fallback non è una comodità: senza, il filtro non troverebbe MAI
    #    nulla sui run che non valorizzano la chiave (es. tutti i 28 run storici
    #    di `run_fatturazione_batch`, registrati prima che il batch scrivesse
    #    `competenza` — verificato 2026-07-23), e il pannello resterebbe vuoto
    #    per ogni mese. Restare sul solo `meta ->>` sarebbe "corretto" e inutile.
    #    Il valore dichiarato ha comunque la precedenza, così un giro lanciato a
    #    luglio per gli arretrati di giugno resta attribuito a GIUGNO.
    def list_job_summary(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        jobname_prefix: str | None = None,
        meta_month_equals: tuple[str, str] | None = None,
    ) -> tuple[list[dict], int]:
        conditions: list[str] = []
        params: list[Any] = []
        if jobname_prefix is not None:
            conditions.append("jobname LIKE %s")
            params.append(f"{jobname_prefix}%")
        if meta_month_equals is not None:
            # La CHIAVE finisce nell'SQL come letterale quotato (è un nome di
            # campo, non un valore: non parametrizzabile) → validata qui. Il
            # VALORE resta parametro (%s). La chiave arriva dal codice
            # chiamante, mai dal client.
            chiave, mese = meta_month_equals
            if not chiave.replace("_", "").isalnum():
                raise ValueError(f"chiave meta non ammessa: {chiave!r}")
            conditions.append(
                f"COALESCE(meta ->> '{chiave}',"
                " to_char(date_trunc('month', started_at), 'YYYY-MM-DD')) = %s"
            )
            params.append(str(mese))
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        params.extend([limit, offset])

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                WITH summary AS (
                    SELECT jobname,
                           COUNT(*) AS total_runs,
                           COUNT(*) FILTER (WHERE ok = true) AS ok_count,
                           COUNT(*) FILTER (WHERE ok = false) AS fail_count,
                           MAX(started_at) AS last_run_at,
                           -- Ultima corsa CONCLUSA, come in `job_liveness`: una
                           -- riga aperta (ok NULL) non e' un esito.
                           (ARRAY_AGG(ok ORDER BY started_at DESC)
                                FILTER (WHERE ended_at IS NOT NULL))[1] AS last_ok
                      FROM maintenance.job_run_log
                      {where}
                     GROUP BY jobname
                )
                SELECT jobname, total_runs, ok_count, fail_count,
                       last_run_at::text, last_ok,
                       COUNT(*) OVER () AS total_count
                  FROM summary
                 ORDER BY last_run_at DESC NULLS LAST, jobname
                 LIMIT %s OFFSET %s
                """,  # noqa: S608 — `where` da condizioni whitelisted, valori parametrizzati
                params,
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
