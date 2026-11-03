{% include-markdown "it/dbzero/script/manual/fn_log_error_only.md" %}
# ⚙️ Funzione `fn_log_error_only`

```sql
CREATE FUNCTION fn_log_error_only(p_area text, p_function_name text, p_error_code text, p_context jsonb, p_tx_id uuid, VARIADIC p_valori text[])
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `postgres`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_log_error_only(p_area text, p_function_name text, p_error_code text, p_context jsonb, p_tx_id uuid, VARIADIC p_valori text[])
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
  v_id bigint;
  v_msg text;
  v_detail text;
  v_hint text;
  v_lang text := coalesce(current_setting('myapp.user_language', true), 'it');
  v_ctx jsonb := coalesce(p_context, '{}'::jsonb);
  v_sql text;
  v_dsn text;
  v_has_dblink boolean := false;
  v_has_logconn boolean := false;
  v_vals text[] := coalesce(p_valori, ARRAY[]::text[]);
BEGIN
  -- =========================================================
  -- Scopo:
  --   Registrare errori in modo persistente anche quando la
  --   transazione chiamante viene rollbackata.
  --
  -- Regole:
  --   - usa solo connessione separata via dblink (out-of-tx)
  --   - non solleva eccezioni verso il chiamante
  --   - in caso di failure del canale di log emette WARNING
  --   - cascata lingua: preferisce v_lang, ripiega su 'it'
  --     (2026-08-03: prima era un lookup secco su v_lang e
  --     una sessione non italiana non loggava affatto)
  --   - se il codice non e' a catalogo, il codice originale
  --     viene conservato in context->>'codice_errore_originale'
  -- =========================================================

  IF p_tx_id IS NULL THEN
    p_tx_id := dbops.fn_get_or_create_session_tx_id();
  END IF;

  -- Riga nella lingua di sessione se esiste, altrimenti la
  -- riga italiana: ORDER BY booleano, TRUE prima in DESC.
  SELECT id, messaggio, causa, soluzione
    INTO v_id, v_msg, v_detail, v_hint
  FROM config.messaggi_errore
  WHERE codice = p_error_code
    AND lingua IN (v_lang, 'it')
  ORDER BY (lingua = v_lang) DESC
  LIMIT 1;

  IF NOT FOUND THEN
    -- Il codice originale sopravvive al ripiego: error_log
    -- conserva solo la FK messaggio_errore_id, quindi senza
    -- questa riga la registrazione resta ma il nome
    -- dell'errore si perde per sempre (brief §9.9).
    v_ctx := v_ctx || jsonb_build_object(
               'codice_errore_originale', p_error_code);

    -- Fallback: recupera ANCHE id da E_MESSAGGIO_NON_DEFINITO
    -- (stessa cascata: la riga esiste solo in 'it').
    SELECT id, messaggio || ' ' || p_error_code, causa, soluzione
      INTO v_id, v_msg, v_detail, v_hint
    FROM config.messaggi_errore
    WHERE codice = 'E_MESSAGGIO_NON_DEFINITO'
      AND lingua IN (v_lang, 'it')
    ORDER BY (lingua = v_lang) DESC
    LIMIT 1;

    IF v_msg IS NULL THEN
      v_msg := '[MESSAGGIO NON DEFINITO: ' || p_error_code || ']';
      v_detail := 'Catalogo mancante=' || quote_literal(p_error_code);
      v_hint := 'Aggiungere record in config.messaggi_errore';
      v_id := NULL;
    END IF;
  END IF;

  BEGIN
    IF cardinality(v_vals) > 0 THEN
      v_msg := format(v_msg, VARIADIC v_vals);
    END IF;
  EXCEPTION WHEN OTHERS THEN
    NULL;
  END;

  -- Se non abbiamo un messaggio_errore_id valido, non possiamo
  -- inserire in error_log (colonna NOT NULL). Warn e return.
  IF v_id IS NULL THEN
    RAISE WARNING 'script.fn_log_error_only: messaggio_errore_id non trovato per code=%, log non persistito.',
      p_error_code;
    RETURN;
  END IF;

  v_sql := format(
    'INSERT INTO dbops.error_log(occurred_at, area, function_name, messaggio_errore_id, context, tx_id)
     VALUES (now(), %L, %L, %s, %L::jsonb, %L::uuid)',
    p_area,
    p_function_name,
    v_id::text,
    v_ctx::text,
    p_tx_id::text
  );

  SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'dblink')
    INTO v_has_dblink;

  IF NOT v_has_dblink THEN
    RAISE WARNING 'script.fn_log_error_only: estensione dblink non disponibile, log non persistito (code=%).',
      p_error_code;
    RETURN;
  END IF;

  v_dsn := coalesce(
    nullif(coalesce(current_setting('myapp.logconn', true), ''), ''),
    nullif(coalesce(current_setting('myapp.dblink_log_connection', true), ''), '')
  );

  IF v_dsn IS NOT NULL AND v_dsn <> '' THEN
    BEGIN
      PERFORM dblink_exec(v_dsn, v_sql, true);
      RETURN;
    EXCEPTION WHEN OTHERS THEN
      RAISE WARNING 'script.fn_log_error_only: dblink_exec DSN fallita (code=%): %',
        p_error_code, SQLERRM;
    END;
  END IF;

  BEGIN
    PERFORM script.fn_ensure_logconn();
  EXCEPTION WHEN OTHERS THEN
    NULL;
  END;

  BEGIN
    WITH conns AS (
      SELECT unnest(dblink_get_connections()) AS name
    )
    SELECT EXISTS (SELECT 1 FROM conns WHERE name = 'logconn')
      INTO v_has_logconn;
  EXCEPTION WHEN OTHERS THEN
    v_has_logconn := false;
  END;

  IF v_has_logconn THEN
    BEGIN
      PERFORM dblink_exec('logconn', v_sql, true);
      RETURN;
    EXCEPTION WHEN OTHERS THEN
      RAISE WARNING 'script.fn_log_error_only: dblink_exec logconn fallita (code=%): %',
        p_error_code, SQLERRM;
    END;
  END IF;

  RAISE WARNING 'script.fn_log_error_only: nessuna connessione dblink valida, log non persistito (code=%).',
    p_error_code;
END;
$function$

COMMENT ON FUNCTION script.fn_log_error_only(p_area text, p_function_name text, p_error_code text, p_context jsonb, p_tx_id uuid, VARIADIC p_valori text[])
IS 'Logga su dbops.error_log via connessione dblink separata (out-of-transaction), senza sollevare eccezioni. Post 2026-08-03: cascata lingua con ripiego su ''it'' (come fn_get_messaggio e fn_log_and_raise_error) e, se il codice non e'' a catalogo, conservazione del codice originale in context->>''codice_errore_originale''.';
```

</div>

---
{% include-markdown "signature-core.md" %}
