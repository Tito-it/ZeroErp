{% include-markdown "it/dbzero/script/manual/fn_log_and_raise_error.md" %}
# ⚙️ Funzione `fn_log_and_raise_error`

### 🎯 Scopo Principale
* **Entrypoint unificato** per error handling: evita duplicazioni di log e raise in trigger, procedure e funzioni.
* **Logging remoto sicuro**: usa `dblink_exec` su connessione permanente fornita da `script.fn_ensure_logconn()`, per isolare il log dall’eventuale rollback della sessione principale.
* **Escalation immediata**: rialza l’eccezione con `DETAIL` e `HINT` recuperati dalla tabella dei messaggi.

---

```sql
CREATE FUNCTION fn_log_and_raise_error(p_area text, p_function_name text, p_error_code text, p_context jsonb, VARIADIC p_valori text[])
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_log_and_raise_error(p_area text, p_function_name text, p_error_code text, p_context jsonb, VARIADIC p_valori text[])
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_id          BIGINT;
  v_messaggio   TEXT;
  v_causa       TEXT;
  v_soluzione   TEXT;
  v_lingua      TEXT := coalesce(
                    current_setting('myapp.user_language', TRUE),
                    'it'
                  );
  v_context JSONB := coalesce(p_context, '{}'::jsonb);
  -- Variabili per dblink
  conninfo    TEXT := current_setting('dblink.log_connection', true);
  sql_text    TEXT;
BEGIN
  -- 0) Assicuro la connessione permanente “logconn”
  PERFORM script.fn_ensure_logconn();

  -- 1) Leggo id, template, causa e soluzione (tutti NULL se non trovato)
  SELECT id, messaggio, causa, soluzione
    INTO v_id, v_messaggio, v_causa, v_soluzione
    FROM config.messaggi_errore
  WHERE codice = p_error_code
    AND lingua = v_lingua;

  -- 2) Se non trovato, imposto dei default
  IF NOT FOUND THEN
     -- a) si cerca nella tabella messaggi_errore il messaggio di default
     SELECT messaggio || ' ' || p_error_code, causa, soluzione
      INTO v_messaggio, v_causa, v_soluzione
      FROM config.messaggi_errore
     WHERE codice = 'MESSAGGIO_NON_DEFINITO'
      AND lingua = v_lingua;

     -- b) se non trovato, imposto un messaggio di default 
    IF v_messaggio IS NULL THEN  
        v_messaggio := '[MESSAGGIO NON DEFINITO: ' || p_error_code 
                    || ' - aggiungere inoltre in config.messaggi_errore  il messaggio con codice : MESSAGGIO_NON_DEFINITO  ]';
        v_causa     := 'Catalogo non contiene ' 
                    || quote_literal(p_error_code)
                    || ' per lingua ' 
                    || quote_literal(v_lingua);
        v_soluzione := 'Verificare record in config.messaggi_errore con codice='
                    || quote_literal(p_error_code)
                    || ' e lingua='
                    || quote_literal(v_lingua);
        v_id := NULL;
    END IF;
  END IF;

  -- 3) Se ho placeholder values, applico format()
  IF array_length(p_valori, 1) IS NOT NULL THEN
    v_messaggio := format(v_messaggio, VARIADIC p_valori);
  END IF;

  -- 4) Preparo e invochiamo l’INSERT via dblink_exec su “logconn”
  sql_text :=
    'INSERT INTO dbops.error_log(' ||
      'occurred_at, area, function_name, messaggio_errore_id, context, tx_id' ||
    ') VALUES (' ||
      'now(), ' ||
      quote_literal(p_area)       || ', ' ||
      quote_literal(p_function_name) || ', ' ||
      coalesce(v_id::text,'NULL') || ', ' ||
      quote_literal(v_context::text) || '::jsonb, ' ||
      quote_literal(md5(txid_current()::text)) || '::uuid' ||
    ');';

  -- lo eseguo in un'altra sessione: commit immediato
  PERFORM dblink_exec('logconn', sql_text);

  -- 5) RAISE con DETAIL (causa) e HINT (soluzione)
  RAISE EXCEPTION '%', coalesce(v_messaggio, '[Errore sconosciuto]')
    USING
      DETAIL = coalesce(v_causa, ''),
      HINT   = coalesce(v_soluzione, '');
END;
$function$
```