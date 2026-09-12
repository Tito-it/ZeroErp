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
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_tx_id        dbops.transaction_ids.id%TYPE;
    v_dblink_conn  text;
BEGIN
    ----------------------------------------------------------------------
    -- 0) Se esiste gia' un tx_id in sessione, riusalo e basta
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
    -- 1) Assicura la connessione di log (helper canonico, come in v1).
    --    Rispetta myapp.log_with_dblink (default 'on'), la connstring
    --    assente e il too_many_connections: non blocca mai il chiamante.
    ----------------------------------------------------------------------
    PERFORM script.fn_ensure_logconn();

    ----------------------------------------------------------------------
    -- 2) Verifica che il parametro di connessione dblink sia impostato
    ----------------------------------------------------------------------
    BEGIN
        v_dblink_conn := current_setting('myapp.dblink_log_connection', true);
    EXCEPTION WHEN OTHERS THEN
        v_dblink_conn := NULL;
    END;

    IF v_dblink_conn IS NULL OR length(trim(v_dblink_conn)) = 0 THEN
        -- Ripiego (a): nessun canale. Sentinella, e NIENTE set_config:
        -- pubblicare un id non registrato avvelenerebbe la sessione e
        -- farebbe fallire ogni scrittura tx_id-managed successiva.
        RAISE WARNING
            'dbops.fn_get_or_create_session_tx_id: parametro myapp.dblink_log_connection non impostato; uso la sentinella uuid_nil e non pubblico la GUC di sessione. '
            'Impostare il parametro a livello DATABASE/ROLE o ALTER SYSTEM.';

        RETURN script.uuid_nil();
    END IF;

    ----------------------------------------------------------------------
    -- 3) Generazione tx_id tramite dblink verso il DB di log.
    --    E' l'unico percorso che REGISTRA in dbops.transaction_ids, e lo
    --    fa su una connessione separata: la registrazione sopravvive al
    --    rollback della transazione di business (autonomia).
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

        -- Ripiego (b): dblink ha risposto ma con NULL -> niente id
        -- registrato, quindi sentinella e nessuna pubblicazione.
        IF v_tx_id IS NULL THEN
            RAISE WARNING
                'dbops.fn_get_or_create_session_tx_id: dblink ha restituito NULL; uso la sentinella uuid_nil e non pubblico la GUC di sessione.';
            RETURN script.uuid_nil();
        END IF;

        -- Solo qui l'id e' REGISTRATO: si puo' pubblicare.
        -- Scope LOCALE alla transazione (v1): un identificativo di
        -- transazione non deve sopravvivere alla transazione.
        PERFORM set_config('dbops.tx_id', v_tx_id::text, TRUE);

    EXCEPTION WHEN OTHERS THEN
        -- Ripiego (c): errore dblink -> sentinella, nessuna pubblicazione.
        RAISE WARNING
            'dbops.fn_get_or_create_session_tx_id: errore durante la chiamata dblink a dbops.fn_generate_tx_id: %; uso la sentinella uuid_nil e non pubblico la GUC di sessione.',
            SQLERRM;

        RETURN script.uuid_nil();
    END;

    ----------------------------------------------------------------------
    -- 4) Ritorna il tx_id (mai NULL)
    ----------------------------------------------------------------------
    RETURN v_tx_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_get_or_create_session_tx_id()
IS 'Restituisce il tx_id della sessione (GUC dbops.tx_id) o ne genera uno nuovo via dblink verso il canale di log (dbops.fn_generate_tx_id), registrandolo in dbops.transaction_ids fuori dalla transazione di business. Senza canale: sentinella uuid_nil, nessuna GUC pubblicata. SECURITY DEFINER di postgres: dal 2026-09-12 (D6) con search_path pinnato a pg_catalog, public, pg_temp — public e'' necessario perche'' dblink vive li''; il pin sta nella definizione, un CREATE OR REPLACE che lo dimentica lo azzera.';
```

---
{% include-markdown "signature-core.md" %}
