{% include-markdown "it/dbzero/script/manual/fn_log_and_raise_error.md" %}
# Funzione `fn_log_and_raise_error`

```sql
CREATE FUNCTION fn_log_and_raise_error(p_area text, p_function_name text, p_error_code text, p_context jsonb)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_log_and_raise_error(p_area text, p_function_name text, p_error_code text, p_context jsonb DEFAULT '{}'::jsonb)
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
BEGIN
  -- 1) Unica SELECT per id, messaggio, causa, soluzione (tutte NULL se non trovato)
  SELECT id, messaggio, causa, soluzione
    INTO v_id, v_messaggio, v_causa, v_soluzione
    FROM config.messaggi_errore
  WHERE codice = p_error_code
    AND lingua = v_lingua;

  -- 2) Se non trovato, imposto valori di default
  IF NOT FOUND THEN
    v_messaggio := '[MESSAGGIO NON DEFINITO: ' || p_error_code || ']';
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

  -- 3) Single INSERT nel log usando v_id che può essere NULL
  INSERT INTO dbops.error_log(
    occurred_at,
    area,
    function_name,
    messaggio_errore_id,
    context,
    tx_id
  ) VALUES (
    now(),
    p_area,
    p_function_name,
    v_id,
    p_context,
    (md5(txid_current()::text))::uuid
  );

  -- 4) Rialzo l’eccezione con messaggio + detail + hint
  RAISE EXCEPTION '%', coalesce(v_messaggio, '[Errore sconosciuto]')
    USING
      DETAIL = coalesce(v_causa, ''),
      HINT   = coalesce(v_soluzione, '');
END;
$function$
```