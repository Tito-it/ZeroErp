{% include-markdown "it/dbzero/script/manual/fn_log_error_only.md" %}
# ⚙️ Funzione `fn_log_error_only`

```sql
CREATE FUNCTION fn_log_error_only(p_area text, p_function_name text, p_error_code text, p_context jsonb, p_tx_id uuid, VARIADIC p_valori text[])
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_log_error_only(p_area text, p_function_name text, p_error_code text, p_context jsonb, p_tx_id uuid, VARIADIC p_valori text[])
 RETURNS void
 LANGUAGE plpgsql
AS $function$
  DECLARE
      v_id     BIGINT;
      v_msg    TEXT;
      v_detail TEXT;
      v_hint   TEXT;
      v_lang   TEXT := coalesce(current_setting('myapp.user_language', TRUE), 'it');
      v_ctx    JSONB := p_context;
      v_sql    TEXT;
  BEGIN
      -- -------------------------------------------------
      -- Input
      -- p_area: area di applicazione (esempio: 'database')
      -- p_function_name: nome della funzione chiamante
      -- p_error_code: codice dell'errore da loggare
      -- p_context: contesto dell'errore (JSONB)
      -- p_tx_id: ID della transazione corrente (se NULL, viene generato automaticamente)
      -- p_valori: valori variabili da inserire nel messaggio di errore
      -- Output
      -- Logga l'errore nel database senza sollevare eccezione
      -- -------------------------------------------------
                          
      IF p_tx_id IS NULL THEN
          p_tx_id := dbops.fn_get_or_create_session_tx_id();
      END IF;

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
            v_hint   := 'Aggiungere record in config.messaggi_errore';
            v_id     := NULL;
        END IF;
      END IF;

      IF array_length(p_valori,1) IS NOT NULL THEN
          v_msg := format(v_msg, VARIADIC p_valori);
      END IF;

      v_sql := format(
        'INSERT INTO dbops.error_log(occurred_at, area, function_name, messaggio_errore_id, context, tx_id)
        VALUES (now(), %L, %L, %s, %L::jsonb, %L::uuid)',
        p_area, p_function_name, coalesce(v_id::text,'NULL'), v_ctx::text, p_tx_id::text
      );
      PERFORM dblink_exec('logconn', v_sql);
  END;
  $function$
```
---
{% include-markdown "signature-core.md" %}
