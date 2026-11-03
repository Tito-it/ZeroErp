{% include-markdown "it/dbzero/maintenance/manual/fn_run_and_log.md" %}
# ⚙️ Funzione `fn_run_and_log`

```sql
CREATE FUNCTION fn_run_and_log(p_jobname text, p_stepname text, p_sql text, p_lock_key bigint, p_processo_codice text, p_auth_user_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION maintenance.fn_run_and_log(p_jobname text, p_stepname text, p_sql text, p_lock_key bigint DEFAULT NULL::bigint, p_processo_codice text DEFAULT NULL::text, p_auth_user_id integer DEFAULT NULL::integer)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
  DECLARE
    v_id         maintenance.job_run_log.id%TYPE;
    v_rows       maintenance.job_run_log.rows_affected%TYPE := 0;
    v_locked     boolean := false;
    -- Attore risolto: passato dal chiamante, oppure derivato dal
    -- jobname (vedi intestazione: qui la derivazione e' completa).
    v_processo   maintenance.job_run_log.processo_codice%TYPE;

    -- ⭐ Le coordinate della corsa, per poterla riscrivere FUORI
    --   dalla transazione quando questa verra' annullata.
    v_run_uuid   maintenance.job_run_log.run_uuid%TYPE;
    v_started_at maintenance.job_run_log.started_at%TYPE;
    v_origine    maintenance.job_run_log.origine%TYPE;

    -- ⭐ L'esito del lavoro, quando p_sql e' una SELECT sola.
    --   v_sql non ha colonna: e' p_sql ripulito.
    v_sql        text;
    v_riga       maintenance.job_run_log.meta%TYPE;
    v_esito      maintenance.job_run_log.meta%TYPE;

    -- diagnosi errori
    v_errmsg     maintenance.job_run_log.message%TYPE;
    v_errdetail  text;
    v_errhint    text;
    v_errcontext text;
    v_sqlstate   maintenance.job_run_log.sqlstate%TYPE;
    -- Il codice di dominio viaggia nel canale CONSTRAINT
    -- dell'eccezione (script.fn_log_and_raise_error).
    v_vincolo    text;
    v_codice     maintenance.job_run_log.error_code%TYPE;
  BEGIN
    -- Sotto-select scalare, non SELECT INTO: senza righe ritorna
    -- NULL senza azzerare nulla di gia' calcolato.
    v_processo := COALESCE(
        p_processo_codice,
        (SELECT pr.codice
           FROM dbops.processi pr
          WHERE pr.codice = p_jobname)
    );

    -- lock opzionale per evitare overlap
    -- ⚠️ Forma a UN argomento, invariata di proposito: e' uno
    --   spazio di lock distinto da quello di
    --   script.fn_job_run_start, e i due canali restano
    --   indipendenti.
    IF p_lock_key IS NOT NULL THEN
      v_locked := pg_try_advisory_lock(p_lock_key);
      IF NOT v_locked THEN
        -- La corsa SALTATA: chiusa e senza esito (ok NULL),
        -- con l'attore, cosi' una sovrapposizione non lascia
        -- un run senza attore e nessun lettore la conta come
        -- corsa vera.
        INSERT INTO maintenance.job_run_log
            (jobname, stepname, saltata, ended_at, message,
             processo_codice, auth_user_id, ruolo_sessione)
        VALUES (p_jobname, p_stepname, TRUE, clock_timestamp(),
                'skip: another run in progress',
                v_processo, p_auth_user_id, session_user);
        RETURN;
      END IF;
    END IF;

    -- ruolo_sessione = chi si e' COLLEGATO. Dentro una procedura
    -- SECURITY DEFINER current_user e' il proprietario;
    -- session_user resta il ruolo della connessione
    -- (zeroerp_job per pgAgent).
    -- ⚠️ D2: il lock e' di SESSIONE. Se l'apertura fallisce (il
    --   CHECK sul processo dichiarato, la FK verso dbops.processi)
    --   va rilasciato qui: il gestore del lavoro, piu' sotto, non
    --   e' ancora in gioco, e il lock resterebbe preso fino alla
    --   fine della connessione. Brief: brief-db-revisione-maintenance D2.
    BEGIN
      INSERT INTO maintenance.job_run_log
          (jobname, stepname, processo_codice, auth_user_id, ruolo_sessione)
      VALUES (p_jobname, p_stepname, v_processo, p_auth_user_id, session_user)
      RETURNING id, run_uuid, started_at, origine
           INTO v_id, v_run_uuid, v_started_at, v_origine;
    EXCEPTION WHEN OTHERS THEN
      IF v_locked THEN
        PERFORM pg_advisory_unlock(p_lock_key);
      END IF;
      RAISE;
    END;

    BEGIN
      -- ⭐ D5: una SELECT sola si legge. La prima riga, intera,
      --   diventa l'esito (il valore della colonna, se e' una);
      --   count(*) tiene rows_affected uguale al numero di righe,
      --   come quando la SELECT girava da sola. Piu' istruzioni
      --   nella stessa stringa, o una CALL, non si leggono:
      --   EXECUTE semplice, come prima.
      v_sql := rtrim(btrim(p_sql), E'; \t\r\n');
      IF v_sql ~* '^select\M' AND strpos(v_sql, ';') = 0 THEN
        -- ⚠️ La finestra conta tutte le righe e se ne tiene UNA: niente
        --   aggregato che le raccolga tutte per usarne la prima. Con zero
        --   righe non arriva niente, e rows_affected resta 0.
        EXECUTE format(
          'SELECT count(*) OVER (), to_jsonb(r) FROM (%s) r LIMIT 1',
          v_sql)
           INTO v_rows, v_riga;
        v_rows := COALESCE(v_rows, 0);
        v_esito := CASE
                     WHEN jsonb_typeof(v_riga) = 'object'
                      AND (SELECT count(*) FROM jsonb_object_keys(v_riga)) = 1
                       THEN (SELECT e.value FROM jsonb_each(v_riga) e)
                     ELSE v_riga
                   END;
        -- ⚠️ Una funzione void restituisce la stringa vuota: non e' un
        --   esito, e non si scrive (le automazioni sono tutte void).
        IF v_esito = '""'::jsonb THEN
          v_esito := NULL;
        END IF;
      ELSE
        EXECUTE p_sql;
        GET DIAGNOSTICS v_rows = ROW_COUNT;
      END IF;

      -- ⭐ D5, il contratto «riuscita con scarti»: un esito con
      --   _falliti > 0 rende la corsa ROSSA senza annullare il
      --   lavoro. Sollevare qui butterebbe via anche le parti
      --   riuscite, che e' cio' che l'isolamento per elemento
      --   protegge. Brief: brief-db-revisione-maintenance D5.
      IF jsonb_typeof(v_esito) = 'object'
         AND jsonb_typeof(v_esito -> '_falliti') = 'number'
         AND (v_esito ->> '_falliti')::numeric > 0 THEN
        UPDATE maintenance.job_run_log
          SET ended_at      = clock_timestamp(),
              ok            = FALSE,
              rows_affected = v_rows,
              message       = format('riuscita con scarti: %s falliti',
                                     v_esito ->> '_falliti'),
              error_code    = 'E_JOB_ESITO_CON_SCARTI',
              meta          = meta || jsonb_build_object('esito', v_esito)
        WHERE id = v_id;
      ELSE
        UPDATE maintenance.job_run_log
          SET ended_at      = clock_timestamp(),
              ok            = TRUE,
              rows_affected = v_rows,
              message       = 'done',
              meta          = CASE
                                WHEN v_esito IS NULL THEN meta
                                ELSE meta || jsonb_build_object('esito', v_esito)
                              END
        WHERE id = v_id;
      END IF;

      IF v_locked THEN
        PERFORM pg_advisory_unlock(p_lock_key);
      END IF;

    EXCEPTION WHEN OTHERS THEN
      -- cattura dettagli dal frame eccezione
      GET STACKED DIAGNOSTICS
        v_errmsg     = MESSAGE_TEXT,
        v_errdetail  = PG_EXCEPTION_DETAIL,
        v_errhint    = PG_EXCEPTION_HINT,
        v_errcontext = PG_EXCEPTION_CONTEXT,
        v_sqlstate   = RETURNED_SQLSTATE,
        v_vincolo    = CONSTRAINT_NAME;

      -- error_code e' «il codice piu' preciso che si ha», lo
      -- SQLSTATE va nella sua colonna. Il codice di dominio vale
      -- SOLO col contratto di fn_log_and_raise_error, «P0001 +
      -- CONSTRAINT valorizzato»: per un 23505 il CONSTRAINT e' il
      -- nome di un vincolo, non un codice d'errore.
      v_codice := CASE
                    WHEN v_sqlstate = 'P0001' AND NULLIF(v_vincolo, '') IS NOT NULL
                      THEN v_vincolo
                    ELSE v_sqlstate
                  END;

      -- ⚠️ Questa UPDATE muore col RAISE qui sotto, e resta
      --   comunque: copre il caso in cui qualcuno chiami
      --   fn_run_and_log dentro un blocco che cattura l'eccezione
      --   senza propagarla. La' la transazione sopravvive, e
      --   restano due righe con lo stesso run_uuid: le viste
      --   contano le corse per run_uuid.
      UPDATE maintenance.job_run_log
        SET ended_at     = clock_timestamp(),
            ok           = FALSE,
            message      = v_errmsg,
            error_code   = v_codice,
            sqlstate     = v_sqlstate,
            error_detail = coalesce(v_errdetail,'') ||
                            CASE WHEN v_errhint IS NOT NULL THEN E'\nHINT: '||v_errhint ELSE '' END ||
                            CASE WHEN v_errcontext IS NOT NULL THEN E'\nCONTEXT: '||v_errcontext ELSE '' END
      WHERE id = v_id;

      -- ⭐ E QUESTA E' LA RIGA CHE SOPRAVVIVE. Va su una
      --   connessione separata, dove il rollback del RAISE non
      --   arriva: senza, il verbale del fallimento verrebbe
      --   scritto e distrutto nello stesso istante.
      -- ⚠️ Non solleva mai: se il canale non c'e' emette un
      --   WARNING. Non si fa fallire due volte un lavoro gia'
      --   fallito.
      PERFORM maintenance.fn_job_run_log_failure(
          p_jobname         => p_jobname,
          p_stepname        => p_stepname,
          p_started_at      => v_started_at,
          p_run_uuid        => v_run_uuid,
          p_origine         => v_origine,
          p_processo_codice => v_processo,
          p_auth_user_id    => p_auth_user_id,
          p_message         => v_errmsg,
          p_error_code      => v_codice,
          p_error_detail    => coalesce(v_errdetail,'') ||
                            CASE WHEN v_errhint IS NOT NULL THEN E'\nHINT: '||v_errhint ELSE '' END ||
                            CASE WHEN v_errcontext IS NOT NULL THEN E'\nCONTEXT: '||v_errcontext ELSE '' END,
          p_sqlstate        => v_sqlstate);

      IF v_locked THEN
        PERFORM pg_advisory_unlock(p_lock_key);
      END IF;

      -- ⚠️ Si continua a propagare, ed e' voluto: smettere
      --   farebbe risultare RIUSCITO a chi l'ha chiesto un lavoro
      --   che non lo e'. Il lavoro si annulla, il verbale no.
      RAISE;
    END;
  END;
$function$

COMMENT ON FUNCTION maintenance.fn_run_and_log(p_jobname text, p_stepname text, p_sql text, p_lock_key bigint, p_processo_codice text, p_auth_user_id integer)
IS 'Esegue il lavoro di un job (p_sql) e ne registra la corsa in maintenance.job_run_log: una riga aperta all''inizio, chiusa con l''esito alla fine. Il processo (processo_codice) e'' quello passato o, se manca, il jobname quando corrisponde a un codice di dbops.processi; una riga senza processo e'' respinta dal CHECK chk_job_run_log_processo_dichiarato. ruolo_sessione e'' session_user, il ruolo che si e'' collegato. Con p_lock_key prende un advisory lock di sessione: se e'' occupato registra una corsa SALTATA (chiusa, ok NULL) ed esce; il lock si rilascia su ogni uscita, anche quando fallisce l''apertura della corsa. Quando p_sql e'' una SELECT sola, il suo risultato si legge: la prima riga va in meta.esito (non quando e'' vuota, come per una funzione void), rows_affected e'' il numero di righe, e un esito con _falliti maggiore di zero rende la corsa rossa con E_JOB_ESITO_CON_SCARTI senza annullare il lavoro fatto (contratto «riuscita con scarti»). In errore: error_code e'' il codice di dominio se l''errore rispetta il contratto «P0001 + CONSTRAINT» di script.fn_log_and_raise_error, altrimenti lo SQLSTATE, che va comunque in sqlstate; il verbale del fallimento lo scrive maintenance.fn_job_run_log_failure su una connessione separata, perche'' il RAISE annulla la transazione, e l''errore si rilancia: smettere di propagarlo farebbe risultare riuscito un lavoro che non lo e''. Se il chiamante cattura l''eccezione restano due righe rosse con lo stesso run_uuid: chi conta i fallimenti conta i run_uuid distinti.';
```

</div>

---
{% include-markdown "signature-core.md" %}
