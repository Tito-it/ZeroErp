# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per accesso in lettura a maintenance.job_run_log
#        (tracciamento esecuzioni job pgAgent).
# Note: ⭐ LE CORSE DI UN JOB SI RACCONTANO IN UNA FORMA SOLA (2026-09-14, dalla
#        nota del team DB sul giornale delle 11:47): la riga PIU' RECENTE come
#        segno di vita (`last_run_at`, `attivo`, `in_corso`) e l'ultima
#        CONCLUSA come `ultima_conclusa = {started_at, ended_at, ok}` — data ed
#        esito INSIEME, presi dalla stessa riga per costruzione (la factory e'
#        `corsa_conclusa` in `_helpers`, condivisa con la coda lavori).
#        ⛔ Fino a quel giorno `last_run_at` era `MAX(started_at)` (la riga piu'
#        recente, anche aperta) e `last_ok` l'esito dell'ultima conclusa: due
#        corse cucite in una riga. Il digest, componendo la mail dentro la
#        propria corsa, scriveva la data della corsa in esecuzione con l'esito
#        della precedente — «09:47:32 (ok)», dove le 09:47 erano la corsa 122445
#        e l'«ok» quella delle 07:30. Vero per i dati di quel giorno; sul
#        modello, con la precedente fallita, lunedi' si sarebbe letto «<adesso>
#        (FALLITA)» con la mail in mano. `last_ok` non esiste piu': un esito
#        senza la sua data e' esattamente il campo che invita a ricucire.
# ------------------------------------------------------------

from datetime import date, datetime
from typing import Any

from django.db import connection

from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.db._helpers import (
    corsa_conclusa,
    fetch_paged_with_total,
    pattern_contiene,
    predicato_giorno_operativo,
)
from apps.core.types import JobRunLogRow


# Scopo: le due CTE che leggono, per jobname, la riga PIU' RECENTE (`recente`)
#        e l'ultima CONCLUSA (`conclusa`), ciascuna come UNA riga intera con
#        `DISTINCT ON`. E' la forma che rende la cucitura impossibile: tre
#        aggregati con lo stesso `ORDER BY` restano d'accordo finche' nessuno ne
#        tocca uno; una riga intera non ha niente da tenere allineato.
# ⚠️ `conditions` sono frammenti SQL costanti del chiamante (whitelist, mai
#    input libero); i VALORI viaggiano nei parametri, e vanno passati UNA VOLTA
#    PER CTE, nell'ordine in cui le CTE compaiono: `recente`, poi `conclusa`.
# ⭐ Le due sedi di questo file (`job_liveness`, `list_job_summary`) le usano
#    entrambe: e' la ragione per cui il frammento sta qui e non dentro una
#    delle due — prima erano due copie di `MAX` + `ARRAY_AGG … FILTER`, e il
#    difetto stava in tutte e due.
# ⭐ LA CORSA SALTATA (dal 2026-10-10, brief-db-corsa-saltata-non-e-una-corsa
#    §8): la riga che `fn_job_run_start` scrive sul lock occupato nasce CHIUSA,
#    senza esito (`ok` NULL) e con `saltata = true`. Per `recente` e' un segno di
#    vita come le altre — la sveglia e' scattata (D3 di Tid) — e, chiusa, non
#    risulta «in corso». Per `conclusa` NO: non ha fatto il lavoro, e
#    l'ultima conclusa e' l'ultima corsa VERA. Senza il filtro una skip diventava
#    l'ultima conclusa con «esito non scritto», e copriva l'esito di quella vera.
def _cte_corse(conditions: list[str]) -> str:
    where_recente = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    where_conclusa = "WHERE " + " AND ".join([*conditions, "ended_at IS NOT NULL", "NOT saltata"])
    return f"""
        recente AS (
            SELECT DISTINCT ON (jobname) jobname, started_at, ended_at
              FROM maintenance.job_run_log
              {where_recente}
             ORDER BY jobname, started_at DESC, id DESC
        ),
        conclusa AS (
            SELECT DISTINCT ON (jobname) jobname, started_at, ended_at, ok
              FROM maintenance.job_run_log
              {where_conclusa}
             ORDER BY jobname, started_at DESC, id DESC
        )
    """  # noqa: S608 — conditions: frammenti letterali dei chiamanti (chiave meta validata in list_job_summary), valori come parametri


class MaintenanceRepository:
    """Repository per job_run_log e funzioni maintenance."""

    # Scopo: la sveglia del processo deve far partire il lavoro, su questa
    #        installazione? Lo chiede `e_dovuto`, l'`ExecCondition` di ogni
    #        sveglia, PRIMA del periodo aziendale: un processo spento non e'
    #        dovuto (brief-db-processi-accensione-per-ambiente §6.0 punto 2).
    # ⭐ La regola non e' qui: e' `maintenance.fn_sveglia_accesa` (la scelta a
    #    mano, poi il default per ambiente; un non spegnibile e' sempre acceso).
    # ⛔ Mai NULL: la funzione SOLLEVA (`E_CONFIG_MANCANTE` sull'ambiente non
    #    dichiarato, `E_PROCESSO_NON_TROVATO`, `E_PROCESSO_SENZA_SVEGLIA`), e
    #    l'eccezione arriva a `e_dovuto` com'e', che la rende un'unit FALLITA.
    #    Un ripiego a «acceso» o «spento» deciderebbe al posto del DB.
    def sveglia_accesa(self, processo_codice: str) -> bool:
        with connection.cursor() as cur:
            cur.execute("SELECT maintenance.fn_sveglia_accesa(%s)", [processo_codice])
            row = cur.fetchone()
        # ⛔ Non un `assert`: con `python -O` sparirebbe, e `bool(None)` farebbe
        #    uscire 1 («spento», systemd salta in silenzio) invece di 255.
        if row is None or row[0] is None:
            raise RuntimeError(
                f"maintenance.fn_sveglia_accesa({processo_codice!r}) ha risposto NULL: "
                f"il contratto dice mai NULL"
            )
        return bool(row[0])

    # Scopo: vero se la corsia `jobname` ha una corsa RIUSCITA (`ok`) partita
    #        da `dal` in poi: il lavoro del periodo che comincia a `dal` e' fatto.
    #        Lo chiede `e_dovuto`, l'`ExecCondition` delle sveglie calendariali
    #        (brief un-solo-fuso-aziendale T-9).
    # ⚠️ Una corsa FALLITA non conta: il lavoro non e' fatto, e la sveglia dopo
    #    riprova. Una corsa IN CORSO non conta nemmeno: la sovrapposizione la
    #    impedisce il lock del comando, e una riga rimasta aperta da un processo
    #    morto non deve bloccare il periodo. Una corsa SALTATA (lock occupato)
    #    nemmeno: dal 2026-10-10 nasce con `ok` NULL (brief corsa-saltata D2), e
    #    `AND ok` la scarta da solo. Fino a quel giorno aveva `ok = true`, e una
    #    sveglia saltata dietro una corsa poi fallita chiudeva il periodo.
    def corsa_riuscita_dal(self, jobname: str, dal: datetime) -> bool:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM maintenance.job_run_log
                     WHERE jobname = %s AND started_at >= %s AND ok
                )
                """,
                [jobname, dal],
            )
            row = cur.fetchone()
        assert row is not None
        return bool(row[0])

    # Scopo: c'e' una corsa CHIUSA della corsia da `dal`, riuscita o fallita?
    #        Per il `dovuto` con `basta_una_corsa`: l'esito negativo e' un
    #        risultato, non un lavoro da rifare. ⚠️ `ok IS NOT NULL` e non
    #        `ended_at IS NOT NULL`: una corsa SALTATA (lock occupato) ha `ok`
    #        NULL come una aperta, e non ha fatto il lavoro del periodo.
    def corsa_chiusa_dal(self, jobname: str, dal: datetime) -> bool:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM maintenance.job_run_log
                     WHERE jobname = %s AND started_at >= %s AND ok IS NOT NULL
                )
                """,
                [jobname, dal],
            )
            row = cur.fetchone()
        assert row is not None
        return bool(row[0])

    # Scopo: Restituisce la lista delle esecuzioni job con filtri opzionali su
    # jobname, esito (ok), intervallo temporale. Ordinamento cronologico decrescente.
    # Perimetro: sola lettura su maintenance.job_run_log.
    # ⚠️ Ogni riga porta `saltata`: una skip ha `ok` NULL come una corsa APERTA,
    #    e chi la mostra la distingue da `saltata`, non da `ok`. Il filtro `ok`
    #    la esclude in entrambi i versi, ed e' giusto: non e' ne' riuscita ne'
    #    fallita.
    def list_job_runs(
        self,
        *,
        jobname: str | None = None,
        ok: bool | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        search: str | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> tuple[list[JobRunLogRow], int]:
        search_pattern = pattern_contiene(search)
        # Giorni dell'azienda, `date_to` incluso (BB): fino al 2026-10-09 era
        # `<= %s::timestamptz + 1 day`, mezzanotte della sessione e confine
        # alto compreso.
        giorno_sql, giorno_params = predicato_giorno_operativo("started_at", date_from, date_to)
        rows, total_count = fetch_paged_with_total(
            f"""
            SELECT id, jobname, stepname,
                   started_at::text, ended_at::text,
                   ok, rows_affected, message,
                   error_code, error_detail,
                   agent_host, run_uuid::text, saltata,
                   COUNT(*) OVER () AS total_count
              FROM maintenance.job_run_log
             WHERE (%s::text IS NULL OR jobname = %s)
               AND (%s::boolean IS NULL OR ok = %s)
               AND {giorno_sql}
               AND (%s::text IS NULL
                    OR jobname ILIKE %s
                    OR stepname ILIKE %s
                    OR message ILIKE %s)
             ORDER BY started_at DESC, id DESC
             LIMIT %s OFFSET %s
            """,  # noqa: S608 — frammento del BB predicato_giorno_operativo (colonna validata), valori come parametri
            [
                jobname, jobname,
                ok, ok,
                *giorno_params,
                search_pattern, search_pattern, search_pattern, search_pattern,
                limit, offset,
            ],
            offset=offset,
        )
        results: list[JobRunLogRow] = [
            JobRunLogRow(
                id=r["id"], jobname=r["jobname"], stepname=r["stepname"],
                started_at=r["started_at"], ended_at=r["ended_at"],
                ok=r["ok"], rows_affected=r["rows_affected"], message=r["message"],
                error_code=r["error_code"], error_detail=r["error_detail"],
                agent_host=r["agent_host"], run_uuid=r["run_uuid"],
                saltata=bool(r["saltata"]),
            )
            for r in rows
        ]
        return results, total_count

    # Scopo: Liveness dei worker schedulati (badge UI code, BE-4): per ogni
    #        jobname ritorna la riga piu' recente come segno di vita
    #        (`last_run_at`, `attivo` = entro `soglia_minuti` col clock DB —
    #        nessun parsing timestamp in Python, tz-safe — e `in_corso` = quella
    #        riga e' ancora aperta) piu' `ultima_conclusa` (vedi `corsa_conclusa`,
    #        `None` se nessuna corsa e' mai stata chiusa). Jobname MAI girati
    #        non compaiono nel dict (il caller li tratta come "worker giù").
    #        Sola lettura su maintenance.job_run_log.
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
    # ⭐ `ok` ha TRE facce — true, false, NULL = corsa ancora aperta — e una
    #    corsa aperta e' un segno di vita legittimo (`attivo`, `in_corso`) ma
    #    NON un esito: l'esito sta in `ultima_conclusa`, con la SUA data. Storia
    #    del difetto nell'intestazione del modulo.
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
                WITH {_cte_corse([filtro])}
                SELECT r.jobname,
                       r.started_at AS last_run_at,
                       r.started_at > now() - make_interval(mins => %s) AS attivo,
                       r.ended_at IS NULL AS in_corso,
                       c.started_at, c.ended_at, c.ok
                  FROM recente r
                  LEFT JOIN conclusa c USING (jobname)
                """,  # noqa: S608 — frammenti costanti, il valore è parametro
                # ⚠️ Il valore del filtro va UNA volta per CTE (recente, conclusa),
                #    poi la soglia del SELECT: e' l'ordine dei `%s` nel testo.
                [valore, valore, int(soglia_minuti)],
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
                "in_corso": bool(r[3]),
                "ultima_conclusa": corsa_conclusa(r[4], r[5], r[6]),
            }
            for r in rows
        }

    # Scopo: Restituisce la lista dei jobname distinti con conteggio esecuzioni
    #        e le corse nella stessa forma di `job_liveness`: `last_run_at`
    #        (riga piu' recente, `::text` di PG per contratto storico),
    #        `in_corso` e `ultima_conclusa` (date in ISO-8601).
    # Utile per dashboard riepilogativa dei job schedulati.
    # ⚠️ `total_runs` conta le corse VERE: una saltata (lock occupato) non e'
    #    un'esecuzione, e «riuscite sul totale» la leggerebbe come un lavoro
    #    mancato. Le saltate hanno il loro conteggio, `saltate_count`.
    #
    # Filtri OPZIONALI (default: nessuno → comportamento storico invariato):
    #  - `jobname_prefix`: tiene solo i job il cui nome inizia col prefisso
    #    (es. 'run_fatturazione_batch' = le corsie di fatturazione, escludendo
    #    i worker di drenaggio code). Filtro SQL e non post-filtro Python:
    #    altrimenti il `LIMIT` taglierebbe PRIMA di scartare i job non voluti.
    #  - `meta_month_equals`: `(chiave, 'YYYY-MM-01')` — tiene i run ATTRIBUITI
    #    a quel mese, applicato PRIMA del GROUP BY (i conteggi risultano quindi
    #    relativi ai soli run che matchano). L'attribuzione è:
    #        COALESCE(meta ->> chiave, mese di `started_at` nel fuso dell'azienda)
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
        limit: int = DEFAULT_LIMIT,
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
            # Il mese di `started_at` e' quello dell'AZIENDA (BB DB
            # `fn_giorno_operativo`): fino al 2026-10-09 era `date_trunc` nel
            # fuso della sessione, e un run della notte del 1° finiva nel mese prima.
            conditions.append(
                f"COALESCE(meta ->> '{chiave}',"
                " to_char(date_trunc('month', script.fn_giorno_operativo(started_at)::timestamp),"
                " 'YYYY-MM-DD')) = %s"
            )
            params.append(str(mese))
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        rows, total_count = fetch_paged_with_total(
            f"""
            WITH summary AS (
                SELECT jobname,
                       COUNT(*) FILTER (WHERE NOT saltata) AS total_runs,
                       COUNT(*) FILTER (WHERE ok = true) AS ok_count,
                       COUNT(*) FILTER (WHERE ok = false) AS fail_count,
                       COUNT(*) FILTER (WHERE saltata) AS saltate_count
                  FROM maintenance.job_run_log
                  {where}
                 GROUP BY jobname
            ),
            {_cte_corse(conditions)}
            SELECT s.jobname, s.total_runs, s.ok_count, s.fail_count, s.saltate_count,
                   r.started_at::text AS last_run_at,
                   r.ended_at IS NULL AS in_corso,
                   c.started_at, c.ended_at, c.ok,
                   COUNT(*) OVER () AS total_count
              FROM summary s
              JOIN recente r USING (jobname)
              LEFT JOIN conclusa c USING (jobname)
             ORDER BY r.started_at DESC, s.jobname
             LIMIT %s OFFSET %s
            """,  # noqa: S608 — `where` da condizioni whitelisted, valori parametrizzati
            # ⚠️ Le condizioni compaiono TRE volte nel testo (summary,
            #    recente, conclusa): i loro valori, nello stesso ordine.
            [*params, *params, *params, limit, offset],
            offset=offset,
        )
        results = [
            {
                "jobname": r["jobname"],
                "total_runs": r["total_runs"],
                "ok_count": r["ok_count"],
                "fail_count": r["fail_count"],
                "saltate_count": r["saltate_count"],
                "last_run_at": r["last_run_at"],
                "in_corso": bool(r["in_corso"]),
                "ultima_conclusa": corsa_conclusa(r["started_at"], r["ended_at"], r["ok"]),
            }
            for r in rows
        ]
        return results, total_count
