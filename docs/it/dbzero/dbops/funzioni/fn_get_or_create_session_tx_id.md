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
IS 'Restituisce il tx_id di sessione, creandolo se assente. REGOLA: non pubblica mai nella GUC dbops.tx_id un id che non sia registrato in dbops.transaction_ids -- e'' l''invariante su cui si regge dbops.trgfn_tx_id_managed. Percorso nominale: script.fn_ensure_logconn + dblink verso il canale di log, che registra su connessione separata (la registrazione sopravvive al rollback della transazione di business). Ripieghi (canale non configurato / dblink NULL / dblink in errore): ritorna la sentinella script.uuid_nil() SENZA impostare la GUC, cosi'' la sessione non resta avvelenata. La GUC e'' impostata con scope LOCALE alla transazione (set_config ..., TRUE). Ripristina la disciplina della v1 20250707-15; vedi brief-db-coerenza-tx-id-non-registrato.md.';
```

---
{% include-markdown "signature-core.md" %}
