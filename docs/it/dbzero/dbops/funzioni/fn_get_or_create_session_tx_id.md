{% include-markdown "it/dbzero/dbops/manual/fn_get_or_create_session_tx_id.md" %}
# ⚙️ Funzione `fn_get_or_create_session_tx_id`

```sql
CREATE FUNCTION fn_get_or_create_session_tx_id()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_get_or_create_session_tx_id()
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
DECLARE
    v_tx_id        uuid;
    v_dblink_conn  text;
BEGIN
    ----------------------------------------------------------------------
    -- 0) Se esiste già un tx_id in sessione, riusalo e basta
    ----------------------------------------------------------------------
    BEGIN
        v_tx_id := current_setting('dbops.tx_id', true)::uuid;
    EXCEPTION WHEN OTHERS THEN
        v_tx_id := NULL;
    END;

    IF v_tx_id IS NOT NULL THEN
        RETURN v_tx_id;
    END IF;

    ----------------------------------------------------------------------
    -- 1) Verifica che il parametro di connessione dblink sia impostato
    ----------------------------------------------------------------------
    BEGIN
        v_dblink_conn := current_setting('myapp.dblink_log_connection', true);
    EXCEPTION WHEN OTHERS THEN
        v_dblink_conn := NULL;
    END;

    IF v_dblink_conn IS NULL OR v_dblink_conn = '' THEN
        RAISE WARNING
            'dbops.fn_get_or_create_session_tx_id: parametro myapp.dblink_log_connection non impostato; uso uuidv7() locale come tx_id. '
            'Impostare il parametro a livello DATABASE/ROLE o ALTER SYSTEM.';
        
        v_tx_id := uuidv7();
        PERFORM set_config('dbops.tx_id', v_tx_id::text, false);
        RETURN v_tx_id;
    END IF;

    ----------------------------------------------------------------------
    -- 2) Generazione tx_id tramite dblink verso il DB di log
    ----------------------------------------------------------------------
    BEGIN
        SELECT tx_id
        INTO v_tx_id
        FROM dblink(
            v_dblink_conn,
            $gen$
                SELECT dbops.fn_generate_tx_id(
                    'dbops.fn_get_or_create_session_tx_id',
                    jsonb_build_object('source','fn_get_or_create')
                )
            $gen$
        ) AS t(tx_id uuid);

        -- Se dblink ha risposto ma con NULL, fallback + warning
        IF v_tx_id IS NULL THEN
            RAISE WARNING
                'dbops.fn_get_or_create_session_tx_id: dblink ha restituito NULL; uso uuidv7() locale come tx_id.';
            v_tx_id := uuidv7();
        END IF;

        -- Imposta SEMPRE la GUC di sessione
        PERFORM set_config('dbops.tx_id', v_tx_id::text, false);

    EXCEPTION WHEN OTHERS THEN
        -- Errore dblink: warning + fallback locale
        RAISE WARNING
            'dbops.fn_get_or_create_session_tx_id: errore durante la chiamata dblink a dbops.fn_generate_tx_id: %; uso uuidv7() locale come tx_id.',
            SQLERRM;

        v_tx_id := uuidv7();
        PERFORM set_config('dbops.tx_id', v_tx_id::text, false);
    END;

    ----------------------------------------------------------------------
    -- 3) Ritorna il tx_id (mai NULL)
    ----------------------------------------------------------------------
    RETURN v_tx_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_get_or_create_session_tx_id()
IS 'Funzione helper che restituisce un tx_id univoco per sessione: riusa la GUC dbops.tx_id se presente o ne crea uno nuovo (via dblink verso dbops.fn_generate_tx_id, con fallback locale uuidv7()) e lo memorizza nella GUC di sessione.';
```

---
{% include-markdown "signature-core.md" %}
