{% include-markdown "it/dbzero/maintenance/manual/fn_job_run_log_failure.md" %}
# ⚙️ Funzione `fn_job_run_log_failure`

```sql
CREATE FUNCTION fn_job_run_log_failure(p_jobname text, p_stepname text, p_started_at timestamp with time zone, p_run_uuid uuid, p_origine character varying, p_processo_codice text, p_auth_user_id integer, p_message text, p_error_code text, p_error_detail text, p_sqlstate text)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `postgres`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION maintenance.fn_job_run_log_failure(p_jobname text, p_stepname text, p_started_at timestamp with time zone, p_run_uuid uuid, p_origine character varying, p_processo_codice text, p_auth_user_id integer, p_message text, p_error_code text, p_error_detail text, p_sqlstate text DEFAULT NULL::text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_sql  text;
    v_dsn  text;
    v_open boolean := false;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Scrivere il verbale di un run FALLITO dove il rollback
    --   non arriva: su una connessione separata.
    --
    -- ⛔ Chi chiama e' un gestore d'eccezione: qualunque cosa
    --   vada storta qui si risolve in un WARNING. Non si fa
    --   fallire un lavoro perche' non si e' riusciti a scrivere
    --   una nota su di lui.
    -- =========================================================

    -- ⚠️ L'INSERT lo costruisce QUESTA funzione, con %L su ogni
    --   valore. Non esiste un parametro che permetta di farle
    --   scrivere qualcos'altro: e' cio' che la distingue da una
    --   primitiva di esecuzione SQL arbitraria in SECURITY
    --   DEFINER di un superuser.
    v_sql := format(
        'INSERT INTO maintenance.job_run_log '
        '(jobname, stepname, started_at, ended_at, ok, message, '
        ' error_code, error_detail, agent_host, run_uuid, origine, '
        ' meta, processo_codice, auth_user_id, ruolo_sessione, sqlstate) '
        'VALUES (%L, %L, %L, now(), false, %L, %L, %L, %L, %L, %L, '
        '        %L::jsonb, %L, %s, %L, %L)',
        p_jobname, p_stepname, p_started_at,
        p_message, p_error_code, p_error_detail,
        -- ⭐ agent_host = da dove e' partita la corsa, come per le righe
                  --   che nascono col default: inet_client_addr() letto QUI, nella
                  --   sessione del job, non in quella del canale dblink.
                  --   Brief: brief-db-revisione-maintenance M17.
                  inet_client_addr()::text,
        p_run_uuid, p_origine,
        -- ⭐ La riga dice di se stessa come e' arrivata: senza,
        --   sembrerebbe una riga normale scritta da un giro che
        --   invece e' stato annullato.
        jsonb_build_object(
            'scritta_fuori_transazione', true,
            'motivo', 'il RAISE avrebbe annullato il verbale insieme al lavoro'
        )::text,
        p_processo_codice,
        COALESCE(p_auth_user_id::text, 'NULL'),
        -- ⭐ Rev 2026-10-15 (D-5): il ruolo che si e' COLLEGATO per la corsa.
        --   Si legge QUI, nella sessione del job: la INSERT gira via dblink
        --   in un'altra sessione, dove session_user sarebbe il canale di log.
        --   Dentro questa funzione DEFINER session_user resta il chiamante.
        session_user,
        -- ⭐ Rev 2026-10-16: lo SQLSTATE, separato da error_code (che e'
        --   «il codice piu' preciso che si ha»). NULL dai chiamanti di
        --   prima: il parametro e' in coda, con default.
        --   brief-db-presidio-job-run-a-chi-tocca §4.4.
        p_sqlstate);

    BEGIN
        -- 1. la connessione nominata, gestita dal canale esistente
        PERFORM script.fn_ensure_logconn();
        v_open := 'logconn' = ANY (
            COALESCE(public.dblink_get_connections(), ARRAY[]::text[]));

        IF v_open THEN
            PERFORM public.dblink_exec('logconn', v_sql, true);
            RETURN;
        END IF;

        -- 2. altrimenti la DSN diretta, come fa fn_log_error_only
        v_dsn := COALESCE(
            NULLIF(current_setting('myapp.logconn', true), ''),
            NULLIF(current_setting('myapp.dblink_log_connection', true), ''));

        IF v_dsn IS NOT NULL THEN
            PERFORM public.dblink_exec(v_dsn, v_sql, true);
            RETURN;
        END IF;

        -- 3. nessun canale: si dichiara, non si finge
        RAISE WARNING
            'maintenance.fn_job_run_log_failure: nessun canale fuori '
            'transazione configurato, il run fallito di % non lascia '
            'traccia nel giornale', p_jobname;
    EXCEPTION WHEN OTHERS THEN
        RAISE WARNING
            'maintenance.fn_job_run_log_failure: verbale non scritto '
            'per % (%)', p_jobname, SQLERRM;
    END;
END
$function$

COMMENT ON FUNCTION maintenance.fn_job_run_log_failure(p_jobname text, p_stepname text, p_started_at timestamp with time zone, p_run_uuid uuid, p_origine character varying, p_processo_codice text, p_auth_user_id integer, p_message text, p_error_code text, p_error_detail text, p_sqlstate text)
IS 'Scrive la riga di una corsa FALLITA in maintenance.job_run_log su una connessione separata (dblink, il canale logconn di script.fn_log_error_only), cosi'' che sopravviva al RAISE che annulla la transazione del lavoro. La chiama maintenance.fn_run_and_log dal suo gestore d''eccezione, con le coordinate della corsa (run_uuid, started_at, origine), il processo e l''errore (error_code e sqlstate). Costruisce da sola il proprio INSERT con format(%L): non e'' una primitiva di esecuzione SQL arbitraria. ruolo_sessione (session_user) e agent_host (inet_client_addr()) si leggono nella sessione del job, non in quella del canale: agent_host dice da dove e'' partita la corsa, come per le righe che nascono col default della colonna. Ogni via d''uscita e'' un WARNING, mai un errore: non si fa fallire due volte un lavoro gia'' fallito; il rovescio e'' che senza canale tace. SECURITY DEFINER di postgres, perche'' dblink rifiuta a un non-superuser una connessione senza password: la proprieta'' la allinea dbops.fn_sync_functions_owner() da dbops.sec_functions_owner.';
```

</div>

---
{% include-markdown "signature-core.md" %}
