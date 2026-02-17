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
        v_msg    TEXT;
        v_detail TEXT;
        v_hint   TEXT;
        v_lang   TEXT := coalesce(current_setting('myapp.user_language', TRUE), 'it');
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
        -- Solleva un'eccezione con il messaggio di errore formattato
        -- e logga l'errore nel database.
        -- -------------------------------------------------
        
        -- -- 1) Solo logging (usiamo funzione esistente)
        PERFORM script.fn_log_error_only(
          p_area, p_function_name, p_error_code, p_context, p_tx_id, VARIADIC p_valori
        );

        -- 2) Recupera il template del messaggio tramite fn_get_messaggio
          v_msg := script.fn_get_messaggio(
            p_error_code,
            NULL,     -- p_valore singolo non usato, useremo format() dopo
            v_lang
          );

        -- 3) Recupera causa e hint
          SELECT causa, soluzione
            INTO v_detail, v_hint
            FROM config.messaggi_errore
          WHERE codice = p_error_code
            AND lingua = v_lang;

        -- 4) Applica il format su tutti i placeholder, se presenti
          IF array_length(p_valori,1) IS NOT NULL THEN
              v_msg := format(v_msg, VARIADIC p_valori);
          END IF;

        -- 5) Solleva l’eccezione con messaggio, detail e hint
          RAISE EXCEPTION '%', v_msg
            USING DETAIL = coalesce(v_detail, ''),
                  HINT   = coalesce(v_hint, '');
       END;
       $function$

COMMENT ON FUNCTION script.fn_log_and_raise_error(p_area text, p_function_name text, p_error_code text, p_context jsonb, p_tx_id uuid, VARIADIC p_valori text[])
IS 'Logga e poi solleva exception con messaggio custom';
```

---
{% include-markdown "signature-core.md" %}
