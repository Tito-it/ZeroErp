{% include-markdown "it/dbzero/script/manual/fn_ensure_logconn.md" %}
# ⚙️ Funzione `fn_ensure_logconn`

```sql
CREATE FUNCTION fn_ensure_logconn()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `postgres`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_ensure_logconn()
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE v_conn text := current_setting('myapp.dblink_log_connection', true);
BEGIN
  -- spegni via GUC di sessione
  IF coalesce(current_setting('myapp.log_with_dblink', true), 'on') <> 'on' THEN
    RETURN;
  END IF;
  -- -- niente connstring -> esci 
  IF v_conn IS NULL OR length(trim(v_conn))=0 THEN RETURN; END IF;
  
  -- se 'logconn' è già aperta, non riconnettere
  IF 'logconn' = ANY (coalesce(public.dblink_get_connections(), ARRAY[]::text[])) THEN
    RETURN;
  END IF;

  -- tenta la connessione e gestisci eccezioni locali
  BEGIN
    PERFORM public.dblink_connect('logconn'::text, v_conn::text);
  EXCEPTION
    WHEN duplicate_object THEN
      NULL;             -- già aperta (race)
    WHEN SQLSTATE '53300' THEN
      RETURN;           -- too_many_connections: non bloccare il chiamante
  END;
END; 
$function$

COMMENT ON FUNCTION script.fn_ensure_logconn()
IS 'Verifica che la connessione dblink logconn sia attiva. 
      Se non lo è, la crea usando la GUC dblink.log_connection.';
```

</div>

---
{% include-markdown "signature-core.md" %}
