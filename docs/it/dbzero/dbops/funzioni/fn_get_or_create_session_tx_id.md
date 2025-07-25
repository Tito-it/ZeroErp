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
    v_tx_id UUID;
BEGIN
        -- 0) Assicurati connessione logconn
    PERFORM script.fn_ensure_logconn();
    -- RAISE NOTICE '[DBG] fn_ensure_logconn() invocata';

    -- 1) Provo a leggere dalla sessione
    BEGIN
        v_tx_id := current_setting('dbops.tx_id', TRUE)::UUID;
        -- RAISE NOTICE '[DBG] dbops.tx_id in sessione = %', v_tx_id;
    EXCEPTION WHEN OTHERS THEN
        -- RAISE NOTICE '[DBG] dbops.tx_id non settato: %', SQLERRM;
        v_tx_id := NULL;
    END;

    -- 2) Se non esiste, genero uno nuovo tramite dblink
    IF v_tx_id IS NULL THEN
        -- RAISE NOTICE '[DBG] Entrato ramo generazione nuovo tx_id';
        BEGIN
            SELECT tx_id INTO v_tx_id
              FROM dblink(
                current_setting('myapp.dblink_log_connection', TRUE),
                $gen$
                  SELECT dbops.fn_generate_tx_id(
                    'dbops.fn_get_or_create_session_tx_id',
                    jsonb_build_object('source','fn_get_or_create')
                  )
                $gen$
              ) AS t(tx_id UUID);

            -- RAISE NOTICE '[DBG] dblink ha restituito tx_id = %', v_tx_id;
            PERFORM set_config('dbops.tx_id', v_tx_id::text, TRUE);
            -- RAISE NOTICE '[DBG] set_config dbops.tx_id = %', v_tx_id;
        EXCEPTION WHEN OTHERS THEN
            -- RAISE WARNING '[DBG] Errore in dblink: %', SQLERRM;
            v_tx_id := script.uuid_nil();
        END;
    END IF;

    -- 3) Ritorna
    -- RAISE NOTICE '[DBG] fn_get_or_create_session_tx_id restituisce %', v_tx_id;
    RETURN v_tx_id;

END;
$function$
```
---
{% include-markdown "signature-core.md" %}
