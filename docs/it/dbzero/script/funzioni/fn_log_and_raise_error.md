{% include-markdown "it/dbzero/script/manual/fn_log_and_raise_error.md" %}
# ⚙️ Funzione `fn_log_and_raise_error`

```sql
CREATE FUNCTION fn_log_and_raise_error(p_area text, p_function_name text, p_error_code text, p_context jsonb, p_tx_id uuid, VARIADIC p_valori text[])
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_log_and_raise_error(p_area text, p_function_name text, p_error_code text, p_context jsonb, p_tx_id uuid, VARIADIC p_valori text[])
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_id        BIGINT;
    v_msg       TEXT;
    v_detail    TEXT;
    v_hint      TEXT;
    v_lang      TEXT := coalesce(current_setting('myapp.user_language', TRUE), 'it');
    v_ctx       JSONB := p_context;
    v_sql       TEXT;
BEGIN
    -- 0) Recupero o genero tx_id coerente
    IF p_tx_id IS NULL  THEN
        p_tx_id := dbops.fn_get_or_create_session_tx_id();
    END IF;

    -- 1) Leggo messaggio di errore
    SELECT id, messaggio, causa, soluzione
      INTO v_id, v_msg, v_detail, v_hint
      FROM config.messaggi_errore
     WHERE codice = p_error_code AND lingua = v_lang;

    IF NOT FOUND THEN
       SELECT messaggio||' '||p_error_code, causa, soluzione
         INTO v_msg, v_detail, v_hint
         FROM config.messaggi_errore
        WHERE codice='MESSAGGIO_NON_DEFINITO' AND lingua=v_lang;
       IF v_msg IS NULL THEN
           v_msg := '[MESSAGGIO NON DEFINITO: '||p_error_code||']';
           v_detail := 'Catalogo mancante='||quote_literal(p_error_code);
           v_hint := 'Aggiungere record in config.messaggi_errore';
           v_id := NULL;
       END IF;
    END IF;

    -- 2) Sostituzioni placeholder
    IF array_length(p_valori,1) IS NOT NULL THEN
        v_msg := format(v_msg, VARIADIC p_valori);
    END IF;

    -- 3) Inserisco su log in connessione separata
    v_sql :=
      'INSERT INTO dbops.error_log(occurred_at,area,function_name,messaggio_errore_id,context,tx_id) VALUES('||
        'now(), '||
        quote_literal(p_area)||', '||
        quote_literal(p_function_name)||', '||
        coalesce(v_id::text,'NULL')||', '||
        quote_literal(v_ctx::text)||'::jsonb, '||
        quote_literal(p_tx_id::text)||'::uuid'||
      ');';
    PERFORM dblink_exec('logconn', v_sql);

    -- 4) Rilancio l’eccezione
    RAISE EXCEPTION '%', coalesce(v_msg,'[Errore sconosciuto]')
      USING DETAIL = coalesce(v_detail,''), HINT = coalesce(v_hint,'');
END;
$function$
```
---
{% include-markdown "signature-core.md" %}
