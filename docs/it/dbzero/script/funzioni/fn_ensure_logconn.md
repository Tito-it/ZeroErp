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
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
  -- text: il tipo di current_setting, nessuna colonna lo porta
  v_conn text := script.fn_canale_log_stringa();
BEGIN
  -- canale spento o non configurato: niente da aprire
  IF v_conn IS NULL THEN
    RETURN;
  END IF;

  -- ⛔ Nessun errore risale al chiamante: il canale di log e' un
  --   servizio, non una precondizione della scrittura. Chi deve
  --   sapere se la connessione c'e' guarda dblink_get_connections().
  BEGIN
    -- gia' aperta: non si riconnette
    IF 'logconn' = ANY (coalesce(public.dblink_get_connections(), ARRAY[]::text[])) THEN
      RETURN;
    END IF;

    PERFORM public.dblink_connect('logconn'::text, v_conn);
  EXCEPTION
    WHEN duplicate_object THEN
      NULL;             -- gia' aperta (corsa)
    WHEN OTHERS THEN
      RAISE WARNING
        'script.fn_ensure_logconn: canale di log non raggiungibile (SQLSTATE %): %; si prosegue senza.',
        SQLSTATE, SQLERRM;
  END;
END;
$function$

COMMENT ON FUNCTION script.fn_ensure_logconn()
IS 'Apre la connessione dblink nominata logconn verso il canale di log, se il canale e'' acceso e la connessione non e'' gia'' aperta. Se il canale e'' acceso e con quale stringa lo dice script.fn_canale_log_stringa. Non solleva mai: un canale irraggiungibile (rete, credenziali, troppe connessioni) diventa un WARNING, perche'' il canale di log e'' un servizio e non una precondizione delle scritture. Chi deve sapere se la connessione c''e'' guarda dblink_get_connections(). SECURITY INVOKER, di postgres.';
```

</div>

---
{% include-markdown "signature-core.md" %}
