{% include-markdown "it/dbzero/maintenance/manual/fn_job_run_log_failure.md" %}
# ⚙️ Funzione `fn_job_run_log_failure`

```sql
CREATE FUNCTION fn_job_run_log_failure(p_jobname text, p_stepname text, p_started_at timestamp with time zone, p_run_uuid uuid, p_origine character varying, p_processo_codice text, p_auth_user_id integer, p_message text, p_error_code text, p_error_detail text, p_sqlstate text)
```

**Definizione completa:**

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
        current_setting('cluster_name', true),
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
IS 'Scrive una riga di run FALLITO in maintenance.job_run_log su una connessione SEPARATA (dblink), cosi'' che sopravviva al RAISE che annulla la transazione. ⛔ Esiste perche'' fn_run_and_log scriveva il verbale del fallimento e poi lo distruggeva: il RAISE fa rollback anche di quella riga, quindi NESSUNO dei dodici job poteva lasciare una riga rossa — ed e'' cosi'' che apply_storicizza_weekly e'' morto ogni settimana per sei mesi con l''ultimo verdetto a «done». ⭐ Riusa il canale gia'' in servizio di script.fn_log_error_only (143.000 righe in dbops.error_log lo dimostrano, fra cui 262 di un guard che esiste solo per sollevare eccezioni). ⛔ NON e'' una primitiva di esecuzione SQL arbitraria: prende parametri tipizzati e costruisce da sola il proprio INSERT con format(%L). ⚠️ Ogni via d''uscita e'' un WARNING: la chiama un gestore d''eccezione, e non si fa fallire un lavoro perche'' non si e'' riusciti a scrivere una nota su di lui — il rovescio e'' che quando il canale non c''e'' TACE, quindi va verificato una volta sul percorso vero di un job. ⚠️ SECURITY DEFINER: dblink rifiuta a un non-superuser una connessione senza password. L''owner (postgres) NON lo mette il changeSet — lo allinea dbops.fn_sync_functions_owner() dalla riga in dbops.sec_functions_owner, a ogni migrate. ⭐ Rev 2026-10-15: scrive anche ruolo_sessione = session_user, letto nella sessione del job e non in quella del canale dblink; search_path pg_catalog, public, pg_temp (forma di casa, rubinetto D6-bis 5 -> 4). Brief: brief-db-ruoli-di-sistema D-5. ⭐ Rev 2026-10-16: parametro p_sqlstate in coda (DEFAULT NULL), scritto in job_run_log.sqlstate; p_error_code resta «il codice piu'' preciso che si ha». Firma cambiata con DROP + CREATE nel provision-post, registro dbops.sec_functions_owner allineato. Brief: brief-db-presidio-job-run-a-chi-tocca §4.4.';
```

---
{% include-markdown "signature-core.md" %}
